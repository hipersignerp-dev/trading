"""v1.8.0 (prototype p19): the Manufacturing create windows (hs_manufacturing.js → api.create.save_doc): BOM, work order,
production plan, job card, quality inspection, manufacture entry and material transfer to WIP. Each hook makes the real
ERPNext documents through api.manufacturing (the same rules as the pages) and hands the record back to save_doc."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, today

from hipersign_trading.api import manufacturing as M

DOCTYPES = {"BOM", "Work Order", "Production Plan", "Job Card", "Quality Inspection"}


def _done(doc, made, msg):
	doc.flags.hs_done = made
	frappe.flags.hs_create_msg = msg
	return doc


def _company(v, fallback=None):
	co = v.get("company") or fallback
	if co:
		return co
	cos = M.companies()
	return cos[0] if cos else frappe.defaults.get_user_default("company")


def pre_bom(doc, v, rows):
	"""A new BOM version: the components typed, the routing of the active version (or a routing master), made the default."""
	item = v.get("item")
	if not item:
		frappe.throw(_("Choose the product"))
	lines = [r for r in rows if r.get("item_code") and flt(r.get("qty")) > 0]
	if not lines:
		frappe.throw(_("Add at least one component"))
	cur = M.bom_of(item)
	company = frappe.db.get_value("BOM", cur, "company") if cur else _company(v)
	b = frappe.new_doc("BOM")
	b.update({"item": item, "company": company, "quantity": 1, "with_operations": 1, "rm_cost_as_per": "Valuation Rate",
		"is_active": 1, "is_default": 1 if v._action == "submit" else 0,  # v1.8.2: a draft version is not the default yet
		"hs_change_note": v.get("hs_change_note"), "currency": frappe.get_cached_value("Company", company, "default_currency")})
	for r in lines:
		b.append("items", {"item_code": r["item_code"], "qty": flt(r["qty"]), "bom_no": M.bom_of(r["item_code"]) or None})
	if v.get("routing"):
		b.routing = v.routing
		for o in frappe.get_doc("Routing", v.routing).operations:
			b.append("operations", {"operation": o.operation, "workstation": o.workstation, "time_in_mins": o.time_in_mins})
	elif cur:
		for o in M.bom(cur).operations:
			b.append("operations", {"operation": o.operation, "workstation": o.workstation, "time_in_mins": o.time_in_mins})
	if not b.operations:
		b.with_operations = 0
	b.insert()
	if v._action == "submit":
		b.submit()
		frappe.db.set_value("Item", item, "default_bom", b.name)
		if cur and cur != b.name:
			frappe.db.set_value("BOM", cur, "is_default", 0)
			try:
				frappe.db.savepoint("hs_bom_old")
				old = frappe.get_doc("BOM", cur)
				old.is_active = 0
				old.save()
			except Exception:
				frappe.db.rollback(save_point="hs_bom_old")
				frappe.clear_last_message()
		M.clear_cache()
		return _done(doc, b, _("{0} active — standard cost now {1}").format(b.name, M._money(M.std(item).total, b.currency)))
	return _done(doc, b, _("{0} saved as a draft").format(b.name))


def pre_work_order(doc, v, rows):
	item = v.get("production_item")
	if not item or not flt(v.get("qty")):
		frappe.throw(_("Choose the product and the quantity"))
	so = v.get("sales_order") or None
	so_item = frappe.db.get_value("Sales Order Item", {"parent": so, "item_code": item}, "name") if so else None
	company = frappe.db.get_value("Sales Order", so, "company") if so else _company(v, frappe.db.get_value("BOM", M.bom_of(item), "company"))
	w = M.make_work_order(item, v.qty, company, so if so_item else None, so_item, v.get("bom_no") or None, start=v.get("planned_start_date") or add_days(today(), 1),
		due=v.get("expected_delivery_date"), fg_warehouse=v.get("fg_warehouse") or None, submit=v._action == "submit")
	if so and not so_item:
		frappe.db.set_value("Work Order", w.name, "sales_order", so, update_modified=False)
	return _done(doc, w, _("{0} {1} — {2} × {3}").format(w.name, _("released") if w.docstatus == 1 else _("saved as a draft"), f"{flt(v.qty):,.0f}", w.item_name))


def pre_production_plan(doc, v, rows):
	pick = v.get("_orders") or "open"
	cos = M.companies()
	if pick == "open":
		sos = [s for s in M.so_names(cos, include_forecast=False) if not M.main_wo(s) and M.so_doc(s).docstatus == 1]
		if v.get("to_date"):
			sos = [s for s in sos if not M.so_doc(s).delivery_date or getdate(M.so_doc(s).delivery_date) <= getdate(v.to_date)]
	else:
		sos = [pick]
		if M.so_doc(pick).docstatus == 0:
			frappe.throw(_("{0} is a forecast — confirm it as a sales order first, then plan it.").format(pick))
	# v1.8.4: forecast orders (drafts) are counted when "Include forecast orders" is ticked — ERPNext plans only confirmed
	# orders, so they are named in the result instead of being silently left out
	fc = []
	if pick == "open" and cint(v.get("_fc", 1)):
		fc = [s for s in M.so_names(cos, include_forecast=True) if M.so_doc(s).docstatus == 0 and not M.main_wo(s)]
	if not sos:
		frappe.throw(_("Every open order already has a work order.") + (" " + _("Forecasts waiting to be confirmed: {0}").format(", ".join(fc)) if fc else ""))
	wh = v.get("for_warehouse") or None
	if wh and not frappe.db.exists("Warehouse", wh):
		frappe.throw(_("Warehouse {0} not found").format(wh))
	r = M.make_plan(sos, include_sub=cint(v.get("_sub", 1)), mrs=True, for_warehouse=wh, safety_stock=cint(v.get("_ss", 0)))
	return _done(doc, frappe.get_doc("Production Plan", r.plan), _("{0} — {1} work order(s) proposed ({2})").format(r.plan, len(r.wos), ", ".join(r.wos))
		+ (_(" · {0} material request(s)").format(len(r.mrs)) if r.mrs else "")
		+ (_(" · forecasts planned once confirmed: {0}").format(", ".join(fc)) if fc else ""))


def pre_job_card(doc, v, rows):
	from erpnext.manufacturing.doctype.work_order.work_order import make_job_card

	w = frappe.get_doc("Work Order", v.get("work_order"))
	if w.docstatus != 1:
		frappe.throw(_("Release {0} first.").format(w.name))
	op = next((o for o in w.operations if o.operation == v.get("operation") or str(o.idx * 10) == str(v.get("operation"))), None)
	if not op:
		frappe.throw(_("Operation {0} is not in the routing of {1}").format(v.get("operation"), w.name))
	planned = sum(flt(j.for_quantity) for j in frappe.get_all("Job Card", filters={"operation_id": op.name, "docstatus": ["<", 2]}, fields=["for_quantity"]))
	qty = flt(v.get("_qty")) or max(0, flt(w.qty) - planned)
	if qty <= 0 or planned + qty > flt(w.qty):
		# ERPNext makes the job cards when the work order is released: the window then hands out the open one of the operation
		live = frappe.db.get_value("Job Card", {"operation_id": op.name, "docstatus": 0}, "name", order_by="creation desc")
		if not live:
			frappe.throw(_("Operation {0} of {1} is completed — every unit has its job card.").format(op.idx * 10, w.name))
		jc = frappe.get_doc("Job Card", live)
		if v.get("hs_operator"):
			jc.db_set("hs_operator", v.hs_operator)
		if v.get("remarks"):
			jc.add_comment("Comment", v.remarks)
		opr = frappe.db.get_value("Employee", jc.hs_operator, "employee_name") if jc.hs_operator else _("no operator yet")
		return _done(doc, jc, _("{0} is the open job card of {1} op {2} — {3}").format(jc.name, w.name, op.idx * 10, opr))
	make_job_card(w.name, [{"name": op.name, "operation": op.operation, "idx": op.idx, "qty": qty, "pending_qty": qty}])
	M._clear_msgs()
	M.flow_line(w.name)
	jc = frappe.get_doc("Job Card", frappe.db.get_value("Job Card", {"operation_id": op.name, "docstatus": 0}, "name", order_by="creation desc"))
	if v.get("hs_operator"):
		jc.db_set("hs_operator", v.hs_operator)
	if v.get("remarks"):
		jc.add_comment("Comment", v.remarks)
	return _done(doc, jc, _("{0} created for {1} op {2}").format(jc.name, w.name, op.idx * 10))


def pre_quality_inspection(doc, v, rows):
	stage = v.get("hs_qc_stage") or "In-process"
	wo = v.get("hs_work_order") if stage != "Incoming" else None
	pr = v.get("_receipt") if stage == "Incoming" else None
	if stage == "Incoming" and not pr:
		frappe.throw(_("Choose the goods receipt of the lot"))
	if stage != "Incoming" and not wo:
		frappe.throw(_("Choose the work order"))
	item = v.get("item_code") or (frappe.db.get_value("Purchase Receipt Item", {"parent": pr}, "item_code") if pr else frappe.db.get_value("Work Order", wo, "production_item"))
	lot = flt(v.get("hs_lot_qty")) or (flt(frappe.db.get_value("Purchase Receipt Item", {"parent": pr, "item_code": item}, "received_qty")) if pr else 0)
	ref_type, ref_name, op = ("Purchase Receipt", pr, None) if pr else ("Job Card", None, None)
	if wo:
		w = frappe.get_doc("Work Order", wo)
		o = w.operations[-1] if stage == "Final" else next((x for x in w.operations if str(x.idx * 10) == str(v.get("_op")) or x.operation == v.get("_op")), None) or w.operations[-1]
		op = f"{o.idx * 10} · {o.operation}"
		ref_name = frappe.db.get_value("Job Card", {"operation_id": o.name, "docstatus": ["<", 2]}, "name", order_by="creation desc")
		if not ref_name:
			frappe.throw(_("{0} has no job card for operation {1} yet — release it first.").format(wo, o.idx * 10))
		lot = lot or flt(w.qty)
	readings = None
	tpl = frappe.db.get_value("Item", item, "quality_inspection_template")
	if stage == "Final" and tpl:
		readings = [(r.specification, r.value, r.value) for r in frappe.get_all("Item Quality Inspection Parameter", filters={"parent": tpl}, fields=["specification", "value"],
			order_by="idx asc")]
	q = M.make_qi(stage, item, flt(v.get("sample_size") or 50), cint(v.get("hs_fails")), lot, ref_type, ref_name, work_order=wo, operation=op, reason=v.get("remarks"),
		rework=flt(v.get("hs_rework_qty")), rejected=flt(v.get("hs_rejected_qty")), submit=v._action == "submit", readings=readings)
	res = q.hs_result if q.docstatus == 1 else _("Pending")
	return _done(doc, q, _("{0} — {1} (sample {2}, {3} fails)").format(q.name, _(res), f"{flt(q.sample_size):,.0f}", cint(q.hs_fails)))


def pre_stock_entry_manufacture(doc, v, rows):
	wo = v.get("work_order")
	if not wo:
		frappe.throw(_("Choose the work order"))
	se = M.manufacture(wo, flt(v.get("_qty")) or None, v.get("_batch") or None, v.get("hs_serial_from") or None, posting_date=v.get("posting_date") or None,
		fg_warehouse=v.get("to_warehouse") or None)
	fg = next((r for r in se.items if r.is_finished_item), None)
	return _done(doc, se, _("{0} — {1} × {2} to finished goods · {3}").format(se.name, f"{flt(fg.qty if fg else 0):,.0f}", fg.item_name if fg else "",
		M._money(fg.amount if fg else 0, frappe.get_cached_value("Company", se.company, "default_currency"))))


def pre_stock_entry_wip(doc, v, rows):
	wo = v.get("work_order")
	if not wo:
		frappe.throw(_("Choose the work order"))
	se = M.transfer(wo, flt(v.get("_pct")) or 100, v.get("hs_picked_by") or None,  # v1.8.4: the stores picked are used
		from_warehouse=v.get("from_warehouse") or None, to_warehouse=v.get("to_warehouse") or None)
	return _done(doc, se, _("{0} — {1} components issued to WIP for {2}").format(se.name, len(se.items), wo))


def work_order_choices(kind=None):
	"""Work orders for the windows: open ones (job card, inspection), released and not issued (transfer), in process (manufacture)."""
	cos = M.companies()
	out = []
	for n in M.wo_names(cos):
		f = M.wo_fig(n)
		ok = {"transfer": f.state in ("Not started", "In process") and not f.issued, "manufacture": f.state in ("In process", "Final QC"),
			"released": f.state not in ("Draft", "Closed", "Cancelled", "Completed")}.get(kind or "", f.state not in ("Closed", "Cancelled"))
		if ok:
			out.append({"name": n, "label": f"{n} — {f.item_name} · {f.qty:,.0f}"})
	return out


def choices(query):
	"""The lists of the Manufacturing windows (api.create.link_options, query "mfg:<what>")."""
	what = query.split(":", 1)[1] if ":" in query else ""
	if what.startswith("wo"):
		return work_order_choices(what.split("_", 1)[1] if "_" in what else None)
	cos = M.companies()
	if what == "products":
		return [{"name": r.item, "label": f"{r.item} — {r.item_name}"} for r in frappe.get_all("BOM", filters={"company": ["in", cos or [""]], "is_default": 1, "is_active": 1,
			"docstatus": 1}, fields=["item", "item_name"], order_by="item asc")]
	if what == "components":
		return [{"name": r.name, "label": f"{r.name} — {r.item_name}"} for r in frappe.get_all("Item", filters={"disabled": 0, "is_stock_item": 1,
			"include_item_in_manufacturing": 1}, fields=["name", "item_name"], order_by="name asc")]
	if what == "orders":
		return [{"name": s, "label": f"{s} — {M.so_fig(s).customer_name} · {M.so_fig(s).qty:,.0f} × {M.so_fig(s).item_name}" + (f" ({_('forecast')})" if M.so_fig(s).forecast else "")}
			for s in M.so_names(cos)]
	if what == "receipts":
		return [{"name": r.name, "label": f"{r.name} — {r.supplier} · {frappe.utils.formatdate(r.posting_date)}"} for r in frappe.get_all("Purchase Receipt",
			filters={"company": ["in", cos or [""]], "docstatus": 1}, fields=["name", "supplier", "posting_date"], order_by="posting_date desc", limit=40)]
	if what == "operators":
		return [{"name": r.name, "label": r.employee_name} for r in frappe.get_all("Employee", filters={"company": ["in", cos or [""]], "status": "Active"},
			fields=["name", "employee_name"], order_by="employee_name asc")]
	if what == "warehouses":
		return [{"name": w, "label": w} for c in cos for w in M.whs(c).values()]
	if what == "operations":
		return [{"name": r.name, "label": r.name} for r in frappe.get_all("Operation", fields=["name"], order_by="name asc")]
	return []


def fill_bom(item, values=None):
	cur = M.bom_of(item)
	if not cur:
		return {"values": {}, "rows": [], "note": _("{0} has no BOM yet — add its components.").format(item)}
	b = M.bom(cur)
	q = flt(b.quantity) or 1
	return {"values": {}, "rows": [{"item_code": r.item_code, "qty": flt(r.qty) / q} for r in b.items],
		"note": _("Components of {0} (the active version) — change what differs; the routing is copied.").format(cur)}


def fill_wo_ops(wo, values=None):
	"""v1.8.4: the job card window's Operation list = the operations of this work order (its routing), the first one with
	quantity still to do picked; before, every operation in the system was offered."""
	if not frappe.has_permission("Work Order", "read", wo):
		return {"values": {}, "opts": {"operation": []}}
	w = frappe.get_doc("Work Order", wo)
	opts, first = [], None
	for o in w.operations:
		done = sum(flt(j.for_quantity) for j in frappe.get_all("Job Card", filters={"operation_id": o.name, "docstatus": ["<", 2]}, fields=["for_quantity"]))
		left = max(0, flt(w.qty) - done)
		opts.append({"name": o.operation, "label": f"{o.idx * 10} · {o.operation}" + (f" — {_('{0} to do').format(f'{left:,.0f}')}" if left else f" — {_('fully planned')}")})
		if first is None and left:
			first = o.operation
	note = "" if opts else _("{0} has no routing operations — release it with a BOM that has a routing.").format(wo)
	return {"values": {"operation": first or (opts[0]["name"] if opts else "")}, "force": ["operation"], "opts": {"operation": opts}, "note": note}
