"""v1.8.0 (prototype p19): the Manufacturing engine — assemblers and factories from sales order to closed work order.

One place for
  · the 22 process steps in 5 phases (who, documents, approval, trigger) and "Complete step N" with its approvals and the
    Manufacturing Step Log,
  · the flows on ERPNext's own documents: sales order → production plan → work orders and material requests for the
    shortages → purchase order → receipt (incoming inspection) → work order released → material transfer to WIP → job
    cards per operation on the shop floor (start, pause, quantity, scrap, complete) → in-process and final inspection →
    manufacture entry (finished goods valued at material + labour and overhead from the job cards' time) → batch → delivery
    → invoice → costing of actual against standard → work order closed,
  · the figures the pages show (standard cost roll-up, work order progress and scrap, shortages, workstation load, actual
    against standard with variances), the step states and the red flags.

Built on ERPNext: Item, BOM (with operations), Workstation (labour and overhead as operating components), Operation,
Work Order, Job Card, Production Plan, Material Request, Purchase Order / Receipt, Stock Entry (Material Transfer for
Manufacture, Manufacture), Quality Inspection (+ template), Batch, Delivery Note, Sales Invoice. The app adds custom fields
(step on the sales order, operator and scrap on the job card, stage / result / rework / certificate on the inspection) and
the Manufacturing Step Log.

Posting:
  transfer to WIP     Dr Work In Progress (stock) · Cr Components store (stock), at valuation
  manufacture entry   Dr Finished Goods (material consumed + labour + overhead) · Cr Work In Progress (material)
                      · Cr Manufacturing Labour Absorbed · Cr Manufacturing Overhead Absorbed (the job cards' actual hours ×
                      the workstation's labour and overhead rates, ERPNext's operating components)
  delivery / invoice  the trading postings (cost of goods sold at the finished goods' value; VAT 5% local, 0% export)
"""

import math

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, cint, date_diff, flt, get_datetime, getdate, now_datetime, today

# ---------------------------------------------------------------- the process
# (name, short, what happens, who, documents, approval, next trigger)
STEPS = [
	("Sales order / forecast", "Sales order", "A confirmed sales order (local or export) or a sales forecast creates the demand for a finished product.", "Sales Executive", "Sales order, forecast", "Sales Manager (price and credit)", "Order confirmed → production planning"),
	("Production planning (MRP: demand, stock, open WOs)", "Planning", "MRP nets demand against finished stock and open work orders and proposes work orders and material requests.", "Production Planner", "Production plan", "Production Manager", "Plan submitted → BOM check"),
	("BOM & routing check (version, alternates)", "BOM check", "The active BOM version and routing are confirmed; alternate components are allowed only where approved.", "Production Engineer", "BOM, routing", "Production Manager for a new version", "BOM confirmed → availability check"),
	("Material availability & shortages", "Availability", "Components required vs stock, reserved and on order; shortages are listed with suggested purchase orders.", "Production Planner", "Shortage report", "None", "Shortages found → material requests"),
	("Material requests", "Material req.", "Material requests for the shortages, with the date needed on the line.", "Production Planner", "Material request", "Production Manager", "Approved → purchasing"),
	("Purchase / import of components", "Purchase", "Purchasing orders from the Shenzhen suppliers (sea or air) through Trading purchasing, imports and landed cost.", "Buyer", "Purchase order, import shipment", "Purchase Manager / Finance Manager by amount", "Goods received → incoming QC"),
	("Incoming quality inspection", "Incoming QC", "Each component lot is sampled (AQL) and accepted, rejected or accepted with deviation before it goes to stores.", "QC Inspector", "Incoming inspection report", "QC Manager for deviations", "Lot accepted → available for issue"),
	("Work order released (qty, due date, workstation)", "WO released", "The work order is released with quantity, due date, BOM, routing and the planned workstations.", "Production Manager", "Work order", "Production Manager", "Released → material issue"),
	("Material issue to WIP (pick from stores)", "Issue to WIP", "Stores pick the components and transfer them to the work-in-progress warehouse.", "Storekeeper", "Material transfer to WIP", "None", "Issued → job cards start"),
	("Job cards per operation (cutting, SMT/assembly, wiring, testing, packing)", "Job cards", "One job card per operation and workstation, printed with a barcode for the shop floor.", "Production Supervisor", "Job cards, job ticket", "None", "Job card started on the tablet"),
	("Operation start/stop, operator, time", "Operations", "Operators start and stop each job card on the tablet; quantity, time and operator are recorded.", "Operator", "Job card time logs", "Supervisor", "Quantity done → next operation"),
	("In-process QC", "In-process QC", "Patrol inspections at wiring and burn-in; failures go to rework.", "QC Inspector", "In-process inspection", "None", "Passed → next operation"),
	("Scrap & rework recorded", "Scrap & rework", "Scrap and rework quantities with the reason are recorded on the job card and costed.", "Production Supervisor", "Scrap note, rework order", "Production Manager above 2% scrap", "Recorded → final QC"),
	("Final QC & test certificate", "Final QC", "Final inspection (AQL 1.0), photometric and safety tests; the test certificate is issued per batch.", "QC Inspector", "Final inspection, QC certificate", "QC Manager", "Accepted → finished goods receipt"),
	("Finished goods receipt to warehouse (manufacture entry)", "FG receipt", "The manufacture entry consumes WIP and receives finished goods at standard cost.", "Storekeeper", "Manufacture entry", "None", "Received → batch and serials"),
	("Batch / serial numbers & labels", "Batch & serials", "Batch and serial numbers are allocated and printed on the product labels for warranty tracking.", "Storekeeper", "Batch, serial numbers, labels", "None", "Labelled → packing"),
	("Packing & carton labels", "Packing", "Products are packed, cartons labelled with item, quantity, batch and barcode.", "Packer", "Carton labels, packing list", "None", "Packed → delivery"),
	("Delivery / export shipment", "Delivery", "Local delivery note or export shipment to the GCC with certificate of origin.", "Logistics Coordinator", "Delivery note, export documents", "None", "Delivered → invoice"),
	("Invoice", "Invoice", "Tax invoice (5% VAT locally, 0% for exports with proof of export).", "Accountant", "Tax invoice", "Finance Manager", "Invoiced → costing"),
	("Production costing (actual vs standard)", "Costing", "Actual material, labour and overhead from the work order compared with the standard cost.", "Cost Accountant", "Work order cost sheet", "Finance Manager", "Costed → variance analysis"),
	("Variance & margin analysis", "Variance", "Material, labour and overhead variances explained; margin per product and order reviewed.", "Finance Manager · Production Manager", "Variance report", "Finance Manager", "Reviewed → close work order"),
	("Work order closed", "Closed", "The work order is closed and variances are posted to the accounts.", "Production Manager", "Closed work order", "Production Manager", "Done"),
]
PHASES = [("Demand & plan", 0, 4), ("Materials", 4, 7), ("Make", 7, 13), ("Finish & ship", 13, 18), ("Bill & close", 18, 22)]
N = len(STEPS)

PM, QCI, MD = "Production Manager", "QC Inspector", "Managing Director"
MM, MU = "Manufacturing Manager", "Manufacturing User"
SM, SU, STM, STU = "Sales Manager", "Sales User", "Stock Manager", "Stock User"
PUM, PUU, FM, AU, LC, QM = "Purchase Manager", "Purchase User", "Accounts Manager", "Accounts User", "Logistics Coordinator", "Quality Manager"
# who may complete each step (System Manager always may); the approval column of STEPS in roles
STEP_ROLES = {0: [SM, SU, MD], 1: [PM, MM, MD], 2: [PM, MM, MD], 3: [PM, MM, MU, MD], 4: [PM, MM, MD], 5: [PUM, PUU, FM, PM, MD], 6: [QCI, QM, PM, MD],
	7: [PM, MM, MD], 8: [STU, STM, PM, MD], 9: [PM, MM, MU, MD], 10: [MU, PM, MM, MD], 11: [QCI, QM, PM, MD], 12: [PM, MM, MU, MD], 13: [QCI, QM, MD],
	14: [STU, STM, PM, MD], 15: [STU, STM, PM, MD], 16: [STU, PM, MU, MD], 17: [LC, STU, STM, MD], 18: [FM, AU, MD], 19: [FM, AU, MD], 20: [FM, PM, MD],
	21: [PM, MM, MD]}
SCRAP_LIMIT = 2.0  # % — step 13 above it needs the Production Manager
STATE_TONE = {"Closed": "grey", "Completed": "green", "Final QC": "violet", "In process": "blue", "Not started": "orange", "Draft": "grey", "Stopped": "red",
	"Cancelled": "red"}
COMPONENTS = ("Labour", "Overhead")  # the workstation's operating components (ERPNext 16)
WH = {"components": "Components Store", "wip": "Work In Progress", "fg": "Finished Goods", "export": "Export Staging", "rejected": "Rejected Stock"}


def _has(*roles):
	have = set(frappe.get_roles())
	return "System Manager" in have or bool(have & set(roles))


def _need(roles, what):
	if not _has(*roles):
		frappe.throw(_("{0} needs the {1}.").format(what, " / ".join(_(r) for r in roles)), frappe.PermissionError)


# ---------------------------------------------------------------- per-request cache
def _c():
	v = getattr(frappe.local, "hs_mf", None)
	if v is None:
		v = frappe.local.hs_mf = {}
	return v


def clear_cache():
	frappe.local.hs_mf = None


def _money(v, cur="AED"):
	return f"{cur} {flt(v):,.2f}"


def _fd(d):
	return getdate(d).strftime("%d %b %Y") if d else "—"


def _fds(d):
	return getdate(d).strftime("%d %b") if d else "—"


def _nf(v, p=0):
	return f"{flt(v):,.{p}f}"


# ---------------------------------------------------------------- set-up of a manufacturing company (idempotent)
def _account(company, name, parent):
	got = frappe.db.get_value("Account", {"company": company, "account_name": name, "is_group": 0})
	if got:
		return got
	a = frappe.get_doc({"doctype": "Account", "account_name": name, "company": company, "parent_account": parent, "root_type": "Expense",
		"report_type": "Profit and Loss", "account_type": "Expense Account"})
	a.flags.ignore_permissions = True
	a.insert()
	return a.name


def accounts(company):
	"""Where the labour and overhead absorbed by finished goods are credited (the job cards' hours × the workstation rates)."""
	c = _c().setdefault("acc", {})
	if company in c:
		return c[company]
	exp = frappe.db.get_value("Account", {"company": company, "account_name": "Direct Expenses", "is_group": 1}) \
		or frappe.db.get_value("Account", {"company": company, "root_type": "Expense", "is_group": 1}, "name", order_by="lft desc")
	r = frappe._dict(labour=_account(company, "Manufacturing Labour Absorbed", exp), overhead=_account(company, "Manufacturing Overhead Absorbed", exp))
	c[company] = r
	return r


def whs(company):
	"""The company's manufacturing warehouses (created the first time): components, WIP, finished goods, export staging, rejects."""
	c = _c().setdefault("wh", {})
	if company in c:
		return c[company]
	abbr = frappe.get_cached_value("Company", company, "abbr")
	parent = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1}, "name", order_by="lft asc")
	out = frappe._dict()
	co = frappe.db.get_value("Company", company, ["default_wip_warehouse", "default_fg_warehouse"], as_dict=True) or {}
	for k, n in WH.items():
		name = f"{n} - {abbr}"
		if k == "wip" and co.get("default_wip_warehouse"):
			name = co.default_wip_warehouse
		elif k == "fg" and co.get("default_fg_warehouse"):
			name = co.default_fg_warehouse
		if not frappe.db.exists("Warehouse", name):
			frappe.get_doc({"doctype": "Warehouse", "warehouse_name": n, "company": company, "parent_warehouse": parent}).insert(ignore_permissions=True)
			name = f"{n} - {abbr}"
		out[k] = name
	c[company] = out
	return out


def ensure_setup(company):
	"""Everything the flows need on a company: warehouses (WIP and finished goods as the company defaults), the labour and
	overhead components with their accounts, and the manufacturing settings the shop floor relies on."""
	w = whs(company)
	acc = accounts(company)
	co = frappe.db.get_value("Company", company, ["default_wip_warehouse", "default_fg_warehouse", "default_operating_cost_account"], as_dict=True)
	upd = {}
	if not co.default_wip_warehouse:
		upd["default_wip_warehouse"] = w.wip
	if not co.default_fg_warehouse:
		upd["default_fg_warehouse"] = w.fg
	if not co.default_operating_cost_account:
		upd["default_operating_cost_account"] = acc.overhead
	if upd:
		frappe.db.set_value("Company", company, upd)
	_wip_account(company, w.wip)
	for comp in COMPONENTS:
		if not frappe.db.exists("Workstation Operating Component", comp):
			frappe.get_doc({"doctype": "Workstation Operating Component", "component_name": comp}).insert(ignore_permissions=True)
		if not frappe.db.exists("Workstation Operating Component Account", {"parent": comp, "company": company}):
			d = frappe.get_doc("Workstation Operating Component", comp)
			d.append("accounts", {"company": company, "expense_account": acc.labour if comp == "Labour" else acc.overhead})
			d.save(ignore_permissions=True)
	# the shop floor books real time on the job cards: no automatic slot planning (it would block overlapping shifts)
	if not cint(frappe.db.get_single_value("Manufacturing Settings", "disable_capacity_planning")):
		frappe.db.set_single_value("Manufacturing Settings", "disable_capacity_planning", 1)
	# incoming inspection is recorded against the goods receipt after it is posted (the lot is sampled in stores)
	if not cint(frappe.db.get_single_value("Stock Settings", "allow_to_make_quality_inspection_after_purchase_or_delivery")):
		frappe.db.set_single_value("Stock Settings", "allow_to_make_quality_inspection_after_purchase_or_delivery", 1)
	return w


def _wip_account(company, wip):
	"""Work in progress on its own balance-sheet account (Dr WIP · Cr components store on the transfer), set while the WIP
	store is still empty so stock and accounts stay in step."""
	if frappe.db.get_value("Warehouse", wip, "account") or frappe.db.exists("Stock Ledger Entry", {"warehouse": wip}):
		return
	if not cint(frappe.get_cached_value("Company", company, "enable_perpetual_inventory")):
		return
	stock_in_hand = frappe.get_cached_value("Company", company, "default_inventory_account")
	parent = frappe.db.get_value("Account", stock_in_hand, "parent_account") if stock_in_hand else None
	if not parent:
		return
	acc = frappe.db.get_value("Account", {"company": company, "account_name": "Work In Progress", "is_group": 0})
	if not acc:
		a = frappe.get_doc({"doctype": "Account", "account_name": "Work In Progress", "company": company, "parent_account": parent, "root_type": "Asset",
			"report_type": "Balance Sheet", "account_type": "Stock"})
		a.flags.ignore_permissions = True
		acc = a.insert().name
	frappe.db.set_value("Warehouse", wip, "account", acc)


def companies(cos=None):
	"""The manufacturing companies of the scope (those with a BOM); when the scope has none, every one the user may read
	(so the Manufacturing pages of a trading company in a group still show the factory)."""
	key = ("cos", tuple(cos or ()))
	c = _c()
	if key in c:
		return c[key]
	have = {r.company for r in frappe.get_all("BOM", filters={"docstatus": 1}, fields=["company"], distinct=True)}
	out = [x for x in (cos or []) if x in have]
	if not out:
		readable = set(frappe.get_list("Company", pluck="name", limit_page_length=0)) if frappe.session.user != "Administrator" else None
		out = sorted(x for x in have if readable is None or x in readable)
	c[key] = out
	return out


def currency(cos):
	return frappe.get_cached_value("Company", cos[0], "default_currency") if cos else "AED"


# ---------------------------------------------------------------- items, BOMs and the standard cost roll-up
def item_info(code):
	c = _c().setdefault("it", {})
	if code not in c:
		c[code] = frappe.db.get_value("Item", code, ["name", "item_name", "item_group", "stock_uom", "valuation_rate", "last_purchase_rate", "default_bom",
			"hs_item_name_zh", "has_batch_no", "description"], as_dict=True) or frappe._dict(name=code, item_name=code)
	return c[code]


def bom_of(code):
	"""The active default BOM of an item (None for a bought-in component)."""
	c = _c().setdefault("bomof", {})
	if code not in c:
		b = frappe.db.get_value("BOM", {"item": code, "is_default": 1, "is_active": 1, "docstatus": 1}) \
			or frappe.db.get_value("BOM", {"item": code, "is_active": 1, "docstatus": 1}, order_by="creation desc")
		c[code] = b
	return c[code]


def bom(name):
	c = _c().setdefault("bom", {})
	if name not in c:
		c[name] = frappe.get_doc("BOM", name)
	return c[name]


def ws_rates(ws):
	"""Labour and overhead per hour of a workstation (its operating components), its capacity in hours a day."""
	c = _c().setdefault("ws", {})
	if ws not in c:
		w = frappe.db.get_value("Workstation", ws, ["name", "workstation_name", "hour_rate", "total_working_hours", "hs_name_zh", "production_capacity"], as_dict=True) \
			or frappe._dict(name=ws, workstation_name=ws, hour_rate=0, total_working_hours=0)
		rows = {r.operating_component: flt(r.operating_cost) for r in frappe.get_all("Workstation Cost", filters={"parent": ws, "parenttype": "Workstation"},
			fields=["operating_component", "operating_cost"])}
		lab = rows.get("Labour", 0)
		ovh = rows.get("Overhead", 0) if rows else flt(w.hour_rate)
		if not rows and flt(w.hour_rate):
			lab, ovh = 0, flt(w.hour_rate)
		w.lab, w.ovh = lab, ovh + sum(v for k, v in rows.items() if k not in COMPONENTS)
		w.cap = flt(w.total_working_hours) or 8
		c[ws] = w
	return c[ws]


def leaf_cost(code):
	it = item_info(code)
	return flt(it.valuation_rate) or flt(it.last_purchase_rate)


def std_of_bom(bname, seen=()):
	"""Standard cost per unit of a BOM: material (sub-assemblies at their own standard), labour and overhead from the routing."""
	c = _c().setdefault("stdb", {})
	if bname in c:
		return c[bname]
	b = bom(bname)
	q = flt(b.quantity) or 1
	mat = 0.0
	for r in b.items:
		sub = bom_of(r.item_code)
		unit = std(r.item_code, seen + (b.item,)).total if sub and r.item_code not in seen else (flt(r.rate) or leaf_cost(r.item_code))
		mat += flt(r.stock_qty or r.qty) / q * unit
	lab = ovh = 0.0
	for o in b.operations or []:
		w = ws_rates(o.workstation)
		lab += flt(o.time_in_mins) / 60 * w.lab / q
		ovh += flt(o.time_in_mins) / 60 * w.ovh / q
	r = frappe._dict(mat=flt(mat, 2), lab=flt(lab, 2), ovh=flt(ovh, 2), total=flt(mat + lab + ovh, 2), bom=bname)
	c[bname] = r
	return r


def std(code, seen=()):
	b = bom_of(code)
	if not b:
		v = leaf_cost(code)
		return frappe._dict(mat=v, lab=0, ovh=0, total=v, bom=None)
	return std_of_bom(b, seen)


def bom_tree(bname, qty=1, depth=0, out=None):
	"""The BOM exploded: every line with its depth, quantity per finished unit, unit cost and cost (sub-assemblies expanded)."""
	out = [] if out is None else out
	b = bom(bname)
	q = flt(b.quantity) or 1
	for r in b.items:
		sub = bom_of(r.item_code)
		unit = std(r.item_code).total if sub else (flt(r.rate) or leaf_cost(r.item_code))
		per = flt(r.stock_qty or r.qty) / q * qty
		out.append(frappe._dict(d=depth, item=r.item_code, qty=per, unit=unit, ext=flt(per * unit, 2), sub=bool(sub), uom=r.stock_uom or r.uom))
		if sub and depth < 4:
			bom_tree(sub, per, depth + 1, out)
	return out


def default_supplier(code, company):
	return frappe.db.get_value("Item Default", {"parent": code, "company": company}, "default_supplier") \
		or frappe.db.get_value("Item Supplier", {"parent": code}, "supplier")


# ---------------------------------------------------------------- work orders, job cards and their figures
JC_STATE = {"Open": "Open", "Work In Progress": "Work in progress", "On Hold": "On hold", "Completed": "Completed", "Submitted": "Completed",
	"Material Transferred": "Open", "Partially Transferred": "Open"}


def job_cards(wo):
	c = _c().setdefault("jcs", {})
	if wo not in c:
		c[wo] = frappe.get_all("Job Card", filters={"work_order": wo, "docstatus": ["<", 2], "is_corrective_job_card": 0},
			fields=["name", "operation", "operation_id", "workstation", "for_quantity", "total_completed_qty", "process_loss_qty", "total_time_in_mins", "status",
				"docstatus", "is_paused", "hs_operator", "hs_scrap_qty", "creation", "actual_start_date", "actual_end_date"], order_by="creation asc")
	return c[wo]


def open_log(jc):
	return frappe.db.get_value("Job Card Time Log", {"parent": jc, "parenttype": "Job Card", "parentfield": "time_logs", "from_time": ["is", "set"], "to_time": ["is", "not set"]},
		["name", "from_time"], as_dict=True)


def op_rows(w):
	"""Per operation of a work order: done (submitted and live job cards), scrap, minutes, the live job card and its state."""
	jcs = job_cards(w.name)
	out = []
	up = 0.0
	for o in w.operations:
		js = [j for j in jcs if j.operation_id == o.name]
		live = next((j for j in reversed(js) if j.docstatus == 0), None)
		done = sum(flt(j.total_completed_qty) for j in js)
		scrap = sum(flt(j.hs_scrap_qty) for j in js)  # scrapped on this operation (the shop floor's Scrap +1)
		mins = sum(flt(j.total_time_in_mins) for j in js)
		state = "Completed" if js and not live else JC_STATE.get(live.status, "Open") if live else "—"
		if live and live.is_paused:
			state = "On hold"
		out.append(frappe._dict(id=o.name, op=o.operation, idx=o.idx, ws=o.workstation, mins_unit=flt(o.time_in_mins) / (flt(w.qty) or 1), done=done, scrap=scrap,
			loss=up + scrap, mins=mins, live=live, jc=(live or (js[-1] if js else None)), state=state, cards=js))
		up += scrap
	return out


def wo_doc(name):
	c = _c().setdefault("wo", {})
	if name not in c:
		c[name] = frappe.get_doc("Work Order", name)
	return c[name]


def so_step(so):
	return cint(frappe.db.get_value("Sales Order", so, "hs_mfg_step")) if so else 0


def wo_state(w, ops=None):
	if w.docstatus == 0:
		return "Draft"
	if w.docstatus == 2:
		return "Cancelled"
	if w.status == "Closed":
		return "Closed"
	if w.status == "Stopped":
		return "Stopped"
	if w.status == "Completed":
		return "Completed"
	if w.status == "Not Started":
		return "Not started"
	ops = ops if ops is not None else op_rows(w)
	if w.sales_order and so_step(w.sales_order) >= 13 or ops and all(o.done + o.loss >= flt(w.qty) - 0.0001 for o in ops):
		return "Final QC"
	return "In process"


def wo_fig(name):
	"""Everything a page shows about a work order — the prototype's work order row."""
	c = _c().setdefault("wof", {})
	if name in c:
		return c[name]
	w = wo_doc(name)
	ops = op_rows(w)
	state = wo_state(w, ops)
	scrap = sum(o.scrap for o in ops)
	last = ops[-1].done if ops else 0
	done = max(flt(w.produced_qty), last) if state not in ("Completed", "Closed") else flt(w.produced_qty)
	due = w.expected_delivery_date or (getdate(w.planned_end_date) if w.planned_end_date else None)
	late = state not in ("Completed", "Closed", "Stopped", "Cancelled") and due and getdate(due) < getdate(today())
	hold = w.get("hs_hold_reason") or None
	if not hold and state == "Not started" and not flt(w.material_transferred_for_manufacturing):
		sh = [x for x in wo_shortages(w) if x.short_now > 0]
		if sh:
			hold = _("Short of {0} ({1})").format(", ".join(item_info(x.item).item_name for x in sh[:2]), ", ".join(x.item for x in sh[:2]))
	s = std(w.production_item)
	r = frappe._dict(name=w.name, item=w.production_item, item_name=w.item_name or item_info(w.production_item).item_name, qty=flt(w.qty), done=done,
		good=flt(w.produced_qty), scrap=scrap, state=state, tone=STATE_TONE.get(state, "grey"), start=getdate(w.planned_start_date) if w.planned_start_date else None,
		due=getdate(due) if due else None, late=bool(late), hold=hold, so=w.sales_order, bom=w.bom_no, company=w.company, ops=ops, std=s,
		issued=flt(w.material_transferred_for_manufacturing) > 0, customer=frappe.db.get_value("Sales Order", w.sales_order, "customer") if w.sales_order else None,
		pct=min(100, done / flt(w.qty) * 100) if flt(w.qty) else 0)
	c[name] = r
	return r


def wo_names(cos, states=None, include_drafts=True):
	f = {"company": ["in", cos or [""]], "docstatus": ["<", 2]}
	if not include_drafts:
		f["docstatus"] = 1
	rows = frappe.get_list("Work Order", filters=f, fields=["name", "status", "docstatus"], order_by="name desc", limit_page_length=0)
	out = [r.name for r in rows]
	if states:
		out = [n for n in out if wo_fig(n).state in states]
	return out


# ---------------------------------------------------------------- shortages (MRP), load, actual cost
def _bin(item, wh, field="actual_qty"):
	return flt(frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh}, field))


def wo_shortages(w, from_warehouse=None):
	"""The components a work order still needs against usable stock in the components store (not yet issued).
	v1.8.4: against the store the components are picked from, when one is chosen."""
	W = whs(w.company)
	out = []
	for r in w.required_items:
		if bom_of(r.item_code):
			continue
		need = max(0, flt(r.required_qty) - flt(r.transferred_qty))
		have = _bin(r.item_code, from_warehouse or W.components)
		out.append(frappe._dict(item=r.item_code, need=need, stock=have, short_now=max(0, need - have)))
	return out


def shortages(cos):
	"""MRP: components needed by the work orders not yet issued, against usable stock, open purchase orders and requests."""
	key = ("short", tuple(cos))
	c = _c()
	if key in c:
		return c[key]
	need, co_of = {}, {}
	for n in frappe.get_all("Work Order", filters={"company": ["in", cos or [""]], "docstatus": ["<", 2], "status": ["in", ["Draft", "Not Started"]],
			"material_transferred_for_manufacturing": 0}, pluck="name"):
		w = wo_doc(n)
		for r in w.required_items:
			if bom_of(r.item_code):
				continue
			need[r.item_code] = need.get(r.item_code, 0) + max(0, flt(r.required_qty) - flt(r.transferred_qty))
			co_of[r.item_code] = w.company
	out = []
	for it, q in sorted(need.items()):
		co = co_of[it]
		W = whs(co)
		stock = _bin(it, W.components)
		on_order = _bin(it, W.components, "ordered_qty")
		requested = _bin(it, W.components, "indented_qty")
		short_now = max(0, q - stock)
		short = max(0, q - stock - on_order)
		cost = leaf_cost(it)
		sug = math.ceil(short / 100) * 100 if short else 0
		pos = frappe.db.sql("""select po.name, po.schedule_date from `tabPurchase Order` po join `tabPurchase Order Item` pi on pi.parent = po.name
			where po.docstatus = 1 and po.company = %s and pi.item_code = %s and pi.received_qty < pi.qty and po.status not in ('Closed', 'Completed')
			order by po.schedule_date asc limit 1""", (co, it), as_dict=True)
		out.append(frappe._dict(item=it, company=co, need=flt(q, 2), stock=stock, on_order=on_order, requested=requested, short_now=flt(short_now, 2), short=flt(short, 2),
			sug=sug, cost=cost, supplier=default_supplier(it, co), po=pos[0].name if pos else None, eta=pos[0].schedule_date if pos else None))
	c[key] = out
	return out


def load(cos, days=3):
	"""Workstation load over the next working days: remaining quantity × routing minutes of open work orders starting by then."""
	horizon = getdate(add_days(today(), days))
	hrs = {}
	for n in wo_names(cos, include_drafts=False):
		f = wo_fig(n)
		if f.state not in ("In process", "Not started", "Final QC"):
			continue
		if f.start and f.start > horizon:
			continue
		for o in f.ops:
			left = max(0, f.qty - o.done - o.loss)
			hrs[o.ws] = hrs.get(o.ws, 0) + left * o.mins_unit / 60
	out = []
	for ws in frappe.get_all("Workstation", filters={"disabled": 0}, fields=["name"], order_by="name asc"):
		if not frappe.db.exists("BOM Operation", {"workstation": ws.name, "docstatus": 1}):
			continue
		w = ws_rates(ws.name)
		h = flt(hrs.get(ws.name), 1)
		out.append(frappe._dict(ws=ws.name, name=w.workstation_name, cap=w.cap, hrs=h, pct=h / (w.cap * days) * 100 if w.cap else 0, lab=w.lab, ovh=w.ovh))
	return out


def actual(name):
	"""Actual cost of a work order from its manufacture entries: material consumed (at valuation), labour and overhead (the
	operating components booked from the job cards' hours); the standard for the same output."""
	c = _c().setdefault("act", {})
	if name in c:
		return c[name]
	w = wo_doc(name)
	ses = frappe.get_all("Stock Entry", filters={"work_order": name, "purpose": "Manufacture", "docstatus": 1}, pluck="name")
	mat = lab = ovh = 0.0
	good = 0.0
	if ses:
		for r in frappe.get_all("Stock Entry Detail", filters={"parent": ["in", ses]}, fields=["s_warehouse", "t_warehouse", "basic_amount", "is_finished_item", "transfer_qty"]):
			if r.is_finished_item:
				good += flt(r.transfer_qty)
			elif r.s_warehouse and not r.t_warehouse:
				mat += flt(r.basic_amount)
		for r in frappe.get_all("Landed Cost Taxes and Charges", filters={"parent": ["in", ses], "parenttype": "Stock Entry"},
				fields=["amount", "description", "operating_component"]):
			comp = r.get("operating_component") or ("Labour" if "labour" in (r.description or "").lower() else "Overhead")
			if comp == "Labour":
				lab += flt(r.amount)
			else:
				ovh += flt(r.amount)
	s = std(w.production_item)
	q = good or flt(w.produced_qty)
	r = frappe._dict(mat=flt(mat, 2), lab=flt(lab, 2), ovh=flt(ovh, 2), total=flt(mat + lab + ovh, 2), qty=q, std=flt(s.total * q, 2), std_mat=flt(s.mat * q, 2),
		std_lab=flt(s.lab * q, 2), std_ovh=flt(s.ovh * q, 2))
	r.var = flt(r.total - r.std, 2)
	c[name] = r
	return r


# ---------------------------------------------------------------- sales orders of the factory, step states and red flags
def so_names(cos, include_forecast=True):
	"""The factory's sales orders (their first item has a BOM) — confirmed ones and the forecasts kept as drafts."""
	rows = frappe.get_list("Sales Order", filters={"company": ["in", cos or [""]], "docstatus": ["<", 2]}, fields=["name", "docstatus", "hs_mfg_forecast",
		"transaction_date"], order_by="transaction_date desc, name desc", limit_page_length=0)
	out = []
	for r in rows:
		if r.docstatus == 0 and not (include_forecast and r.hs_mfg_forecast):
			continue
		it = frappe.db.get_value("Sales Order Item", {"parent": r.name}, "item_code", order_by="idx asc")
		if it and bom_of(it):
			out.append(r.name)
	return out


def so_doc(name):
	c = _c().setdefault("so", {})
	if name not in c:
		c[name] = frappe.get_doc("Sales Order", name)
	return c[name]


def main_wo(so):
	"""The work order making the sales order's product (sub-assembly work orders of the same order are not it)."""
	c = _c().setdefault("mwo", {})
	if so not in c:
		s = so_doc(so)
		items = [i.item_code for i in s.items]
		c[so] = frappe.db.get_value("Work Order", {"sales_order": so, "docstatus": ["<", 2], "production_item": ["in", items or [""]]}, "name", order_by="creation asc")
	return c[so]


def so_fig(name):
	s = so_doc(name)
	it = s.items[0] if s.items else frappe._dict()
	export = bool(s.get("hs_is_export")) or frappe.db.get_value("Customer", s.customer, "hs_market") == "Export"
	return frappe._dict(name=name, customer=s.customer, customer_name=s.customer_name, item=it.get("item_code"), item_name=it.get("item_name"), qty=flt(it.get("qty")),
		rate=flt(it.get("rate")), value=flt(s.base_net_total), date=s.transaction_date, due=s.delivery_date, step=cint(s.get("hs_mfg_step")),
		forecast=bool(s.get("hs_mfg_forecast")) and s.docstatus == 0, wo=main_wo(name), export=export, docstatus=s.docstatus,
		city=frappe.db.get_value("Address", s.customer_address, "city") if s.customer_address else "")


def so_status(step, forecast=False):
	return _("Forecast") if forecast else _("Closed") if step >= 22 else _("Delivered") if step >= 18 else _("Finishing") if step >= 13 else _("In production") if step >= 7 \
		else _("Materials") if step >= 4 else _("Planning")


def _mrs_of(w):
	if not w or not w.production_plan:
		return []
	return frappe.db.sql("""select distinct mr.name, mr.docstatus, mr.status, mr.per_ordered, mr.transaction_date, mri.item_code, mri.qty from `tabMaterial Request` mr
		join `tabMaterial Request Item` mri on mri.parent = mr.name where mri.production_plan = %s and mr.docstatus < 2 order by mr.name""", w.production_plan, as_dict=True)


def _plan_date(s, i):
	d0, d1 = getdate(s.transaction_date), getdate(s.delivery_date or add_days(s.transaction_date, 30))
	span = max(1, date_diff(d1, d0))
	return add_days(d0, round(i * span / 18))


def states(name):
	"""Each of the 22 steps for a sales order: done / current / waiting / red flag, %, date, tag and the facts behind it."""
	s = so_doc(name)
	F = so_fig(name)
	step = F.step
	cur = frappe.get_cached_value("Company", s.company, "default_currency")
	logs = {r.step: r for r in frappe.get_all("Manufacturing Step Log", filters={"sales_order": name}, fields=["step", "completed_on", "completed_by"], order_by="completed_on asc")}
	out = []
	for i in range(N):
		lg = logs.get(i + 1)
		out.append(frappe._dict(st="done" if i < step else "cur" if i == step else "wait", pct=100 if i < step else 30 if i == step else 0,
			date=(lg.completed_on if lg else _plan_date(s, i)) if i < step else None, tag=_("Done") if i < step else _("In progress") if i == step else _("Pending"),
			info=[], by=frappe.utils.get_fullname(lg.completed_by) if lg else None))

	def put(i, **kw):
		out[i].update(kw)

	out[0].info = [[_("Customer"), F.customer_name], [_("Quantity"), f"{_nf(F.qty)} × {F.item_name}"], [_("Due"), _fd(F.due)]]
	if F.forecast:
		put(1, pct=20, tag=_("Forecast — in the next MRP run"))
	w = wo_doc(F.wo) if F.wo else None
	if w:
		f = wo_fig(w.name)
		out[1].info = [[_("Production plan"), w.production_plan or "—"]]
		out[2].info = [[_("BOM"), w.bom_no], [_("Routing"), _("{0} operations").format(len(w.operations))]]
		out[7].info = [[_("Work order"), w.name], [_("Due"), _fd(f.due)], [_("Status"), _(f.state)]]
		mrs = _mrs_of(w)
		if mrs:
			pend = [m for m in mrs if m.docstatus == 0]
			out[4].info = [[m.name, f"{item_info(m.item_code).item_name} {_nf(m.qty)} — {_('pending') if m.docstatus == 0 else _(m.status)}"] for m in mrs]
			if step == 4:
				put(4, pct=(len(mrs) - len(pend)) / len(mrs) * 100, tag=_("{0} of {1} requests approved").format(len(mrs) - len(pend), len(mrs)))
		sh = [x for x in wo_shortages(w) if x.short_now > 0] if not f.issued else []
		if sh and step <= 6:
			out[3].info = [[x.item, _("{0} short").format(_nf(x.short_now)), "neg"] for x in sh]
			if step >= 5:
				pos = [p for x in sh for p in [_open_po(x.item, w.company)] if p]
				put(5, st="late", pct=40, tag=_("Waiting for {0}").format(item_info(sh[0].item).item_name),
					info=[[p.name, _("{0} × {1} · ETA {2}").format(_nf(p.qty), item_info(p.item_code).item_name, _fds(p.schedule_date))] for p in pos]
					+ [[_("Hold"), _("Work order cannot start before the components arrive"), "neg"]])
		if f.issued:
			tr = frappe.get_all("Stock Entry", filters={"work_order": w.name, "purpose": "Material Transfer for Manufacture", "docstatus": 1}, pluck="name")
			out[8].info = [[_("Transfer"), ", ".join(tr) or "—"]]
		if w.docstatus == 1 and f.ops:
			out[9].info = [[o.jc.name if o.jc else "—", f"{_('op')} {o.idx * 10} · {_(o.state)}"] for o in f.ops]
			out[10].info = [[f"{o.idx * 10} {o.op.split(' ')[0]}", f"{_nf(o.done)} / {_nf(f.qty)}"] for o in f.ops]
			if 8 <= step <= 12:
				put(8, st="done", pct=100) if f.issued else None
				put(9, st="done", pct=100, tag=_("{0} job cards").format(len([o for o in f.ops if o.jc])))
				put(10, st="cur", pct=f.pct, tag=f"{_nf(f.done)} {_('of')} {_nf(f.qty)}")
		qis = frappe.get_all("Quality Inspection", filters={"hs_work_order": w.name, "docstatus": ["<", 2]}, fields=["name", "hs_qc_stage", "hs_result", "status", "docstatus",
			"hs_rework_qty", "hs_rework_done", "hs_certificate_no", "sample_size", "hs_fails"], order_by="report_date asc")
		ip = [q for q in qis if q.hs_qc_stage == "In-process"]
		if ip:
			out[11].info = [[q.name, _(q.hs_result or q.status or "Pending")] for q in ip]
			if 8 <= step <= 12:
				put(11, st="cur", pct=60, tag=_("{0} patrol checks").format(len(ip)))
		rw = sum(flt(q.hs_rework_qty) - flt(q.hs_rework_done) for q in qis)
		out[12].info = [[_("Scrap"), _("{0} units ({1}%)").format(_nf(f.scrap), f"{f.scrap / f.qty * 100:.1f}" if f.qty else "0")], [_("Rework open"), _nf(rw)]]
		if 8 <= step <= 12:
			rq = sum(flt(q.hs_rework_qty) for q in qis)
			put(12, st="cur", pct=(rq - rw) / rq * 100 if rq else 0, tag=_("{0} scrap · {1} rework").format(_nf(f.scrap), _nf(rw)))
		fin = [q for q in qis if q.hs_qc_stage == "Final"]
		if fin:
			q = fin[-1]
			out[13].info = [[_("Sample"), _("{0} · {1} fails").format(_nf(q.sample_size), cint(q.hs_fails))], [_("Result"), _(q.hs_result or q.status or "Pending")],
				[_("Certificate"), q.hs_certificate_no or "—"]]
			if step == 13:
				put(13, pct=80, tag=_("{0} · cert {1}").format(_(q.hs_result or "Pending"), q.hs_certificate_no or "—"))
		mfe = frappe.get_all("Stock Entry", filters={"work_order": w.name, "purpose": "Manufacture", "docstatus": 1}, fields=["name", "fg_completed_qty", "process_loss_qty",
			"posting_date"], order_by="posting_date asc")
		if mfe:
			out[14].info = [[m.name, f"{_nf(flt(m.fg_completed_qty) - flt(m.process_loss_qty))} · {_fds(m.posting_date)}"] for m in mfe]
			b = frappe.db.sql("""select distinct sed.batch_no from `tabStock Entry Detail` sed where sed.parent in %s and sed.is_finished_item = 1 and ifnull(sed.batch_no, '') != ''""",
				(tuple(m.name for m in mfe),))
			out[15].info = [[_("Batch"), ", ".join(x[0] for x in b) or "—"]]
		if step >= 19 and f.state in ("Completed", "Closed"):
			A = actual(w.name)
			out[19].info = [[_("Standard"), _money(A.std, cur)], [_("Actual"), _money(A.total, cur)], [_("Variance"), _money(A.var, cur), "neg" if A.var > 0 else "pos"]]
			out[20].info = [[_("Material variance"), f"{(A.mat - A.std_mat) / A.std_mat * 100 if A.std_mat else 0:+.1f}%"],
				[_("Labour variance"), f"{(A.lab - A.std_lab) / A.std_lab * 100 if A.std_lab else 0:+.1f}%"],
				[_("Overhead variance"), f"{(A.ovh - A.std_ovh) / A.std_ovh * 100 if A.std_ovh else 0:+.1f}%"]]
	dns = frappe.db.sql("""select distinct dn.name, dn.posting_date from `tabDelivery Note` dn join `tabDelivery Note Item` dni on dni.parent = dn.name
		where dni.against_sales_order = %s and dn.docstatus = 1""", name, as_dict=True)
	if dns:
		out[17].info = [[_("Delivery"), ", ".join(d.name for d in dns)]]
	sis = invoices(name)
	if sis:
		out[18].info = [[_("Invoice"), ", ".join(i.name for i in sis)], [_("Paid"), _("Yes") if all(flt(i.outstanding_amount) <= 0.5 for i in sis) else _("Not yet"),
			"" if all(flt(i.outstanding_amount) <= 0.5 for i in sis) else "neg"]]
	for fl in flags(name):
		if out[fl["step"]].st != "done":
			out[fl["step"]].st = "late"
	return out


def _open_po(item, company):
	r = frappe.db.sql("""select po.name, pi.item_code, pi.qty - pi.received_qty as qty, po.schedule_date from `tabPurchase Order` po join `tabPurchase Order Item` pi
		on pi.parent = po.name where po.company = %s and pi.item_code = %s and po.docstatus = 1 and pi.received_qty < pi.qty and po.status not in ('Closed', 'Completed')
		order by po.schedule_date asc limit 1""", (company, item), as_dict=True)
	return r[0] if r else None


def invoices(so):
	return frappe.db.sql("""select distinct si.name, si.outstanding_amount, si.grand_total, si.due_date from `tabSales Invoice` si join `tabSales Invoice Item` sii
		on sii.parent = si.name where sii.sales_order = %s and si.docstatus = 1 and si.is_return = 0""", so, as_dict=True)


def flags(name):
	"""The red flags of a sales order and its work order (the prototype's mfFlags): late, held for a shortage, open rework,
	a material request waiting for approval, an invoice not paid."""
	c = _c().setdefault("flags", {})
	if name in c:
		return c[name]
	F = so_fig(name)
	fl = []

	def add(lvl, t, step, open_=None):
		fl.append({"lvl": lvl, "text": t, "step": step, "open": open_})

	if F.wo:
		f = wo_fig(F.wo)
		if f.late:
			add("High", _("{0} late — due {1}, {2} still to finish").format(f.name, _fd(f.due), _nf(max(0, f.qty - f.done - f.scrap))), 13, ["Work Order", f.name])
		if f.hold and f.state in ("Draft", "Not started"):
			w = wo_doc(F.wo)
			sh = [x for x in wo_shortages(w) if x.short_now > 0]
			po = _open_po(sh[0].item, w.company) if sh else None
			add("High", _("{0} — {1} short").format(f.hold, _nf(sh[0].short_now)) + (_(", {0} ETA {1}").format(po.name, _fds(po.schedule_date)) if po else "") if sh else f.hold,
				5, ["Work Order", f.name])
		for q in frappe.get_all("Quality Inspection", filters={"hs_work_order": F.wo, "docstatus": ["<", 2], "hs_rework_qty": [">", 0]},
				fields=["name", "hs_rework_qty", "hs_rework_done", "remarks"]):
			if flt(q.hs_rework_done) < flt(q.hs_rework_qty):
				add("Medium", _("Rework open on {0} — {1} of {2} units still to rework").format(F.wo, _nf(flt(q.hs_rework_qty) - flt(q.hs_rework_done)), _nf(q.hs_rework_qty)),
					12, ["Quality Inspection", q.name])
		if F.step == 4:
			for m in _mrs_of(wo_doc(F.wo)):
				if m.docstatus == 0:
					add("Medium", _("Material request {0} ({1}) waiting for approval").format(m.name, item_info(m.item_code).item_name), 4, ["Material Request", m.name])
	if 18 <= F.step < 22:
		for i in invoices(name):
			if flt(i.outstanding_amount) > 0.5:
				add("Medium", _("{0} not yet paid — {1} outstanding").format(i.name, _money(i.outstanding_amount)), 18, ["Sales Invoice", i.name])
	c[name] = fl
	return fl


# ---------------------------------------------------------------- documents the flows make
def _wo_dates(start=None, due=None):
	start = getdate(start or add_days(today(), 1))
	return f"{start} 07:00:00", getdate(due) if due else add_days(start, 7)


def make_work_order(item, qty, company=None, sales_order=None, sales_order_item=None, bom_no=None, start=None, due=None, fg_warehouse=None, production_plan=None,
		pp_item=None, pp_sub=None, submit=False, hold=None, name=None):
	"""A work order with the active BOM and routing, the company's WIP and finished-goods stores and the due date."""
	company = company or frappe.db.get_value("Sales Order", sales_order, "company") or frappe.defaults.get_user_default("company")
	W = ensure_setup(company)
	bom_no = bom_no or bom_of(item)
	if not bom_no:
		frappe.throw(_("{0} has no active BOM.").format(item))
	st, dd = _wo_dates(start, due)
	wo = frappe.get_doc({"doctype": "Work Order", "production_item": item, "bom_no": bom_no, "qty": flt(qty), "company": company, "sales_order": sales_order,
		"sales_order_item": sales_order_item, "production_plan": production_plan, "production_plan_item": pp_item, "production_plan_sub_assembly_item": pp_sub,
		"source_warehouse": W.components, "wip_warehouse": W.wip, "fg_warehouse": fg_warehouse or W.fg, "planned_start_date": st, "expected_delivery_date": dd,
		"use_multi_level_bom": 0, "transfer_material_against": "Work Order", "hs_hold_reason": hold})
	wo.set_work_order_operations()
	wo.set_required_items()
	if name:
		wo.insert(set_name=name)
	else:
		wo.insert()
	if submit:
		wo.submit()
		_clear_msgs()
		flow_line(wo.name)
	clear_cache()
	return wo


def _clear_msgs():
	frappe.local.message_log = [m for m in (frappe.local.message_log or []) if "created" not in str(m)]


def make_plan(sales_orders, company=None, include_sub=True, name=None, posting_date=None, mrs=True, for_warehouse=None, safety_stock=0):
	"""Sales orders → production plan (submitted) → draft work orders (finished goods and sub-assemblies) and material
	requests for the components short in stock."""
	sos = [so_doc(s) for s in sales_orders]
	if not sos:
		frappe.throw(_("No sales orders to plan — every open order already has a work order."))
	for s in sos:
		if s.docstatus != 1:
			frappe.throw(_("{0} is not confirmed yet — a forecast is planned once it is a sales order.").format(s.name))
	company = company or sos[0].company
	W = ensure_setup(company)
	pp = frappe.get_doc({"doctype": "Production Plan", "company": company, "get_items_from": "Sales Order", "posting_date": posting_date or today(),
		# v1.8.4: the window's raw material warehouse and "keep safety stock" are used (they were ignored)
		"for_warehouse": for_warehouse or W.components, "sub_assembly_warehouse": W.wip, "include_safety_stock": 1 if safety_stock else 0,
		"skip_available_sub_assembly_item": 1})
	for s in sos:
		pp.append("sales_orders", {"sales_order": s.name, "sales_order_date": s.transaction_date, "customer": s.customer, "grand_total": s.grand_total})
	pp.get_items()
	for r in pp.po_items:
		r.warehouse = W.fg
		r.planned_start_date = r.planned_start_date or f"{add_days(today(), 1)} 07:00:00"
	if include_sub:
		try:
			pp.get_sub_assembly_items()
		except Exception:
			frappe.clear_last_message()
			pp.set("sub_assembly_items", [])
	if name:
		pp.insert(set_name=name)
	else:
		pp.insert()
	pp.submit()
	wos = []
	for r in [x for x in pp.po_items if flt(x.planned_qty) > 0]:
		s = next((x for x in sos if x.name == r.sales_order), sos[0])
		wos.append(make_work_order(r.item_code, r.planned_qty, company, s.name, r.sales_order_item, r.bom_no, start=add_days(today(), 1),
			due=add_days(s.delivery_date, -3) if s.delivery_date else None, production_plan=pp.name, pp_item=r.name).name)
	for r in [x for x in pp.sub_assembly_items if flt(x.qty) > 0]:
		parent_so = sos[0].name
		wos.append(make_work_order(r.production_item, r.qty, company, parent_so, None, r.bom_no, start=add_days(today(), 1), due=add_days(today(), 6),
			fg_warehouse=W.components, production_plan=pp.name, pp_sub=r.name).name)
	made = []
	if mrs:
		clear_cache()
		for x in shortages([company]):
			if x.short <= 0:
				continue
			used = [n for n in wos if any(r.item_code == x.item for r in wo_doc(n).required_items)]
			if not used:
				continue
			made.append(make_mr(x.item, x.sug or x.short, company, production_plan=pp.name).name)
	for s in sos:
		if cint(s.get("hs_mfg_step")) < 1:
			frappe.db.set_value("Sales Order", s.name, "hs_mfg_step", 1, update_modified=False)
	clear_cache()
	return frappe._dict(plan=pp.name, wos=wos, mrs=made)


def make_mr(item, qty, company, need=None, production_plan=None, name=None):
	W = whs(company)
	need = need or add_days(today(), 10)
	mr = frappe.get_doc({"doctype": "Material Request", "material_request_type": "Purchase", "company": company, "transaction_date": today(), "schedule_date": need,
		"items": [{"item_code": item, "qty": flt(qty), "schedule_date": need, "warehouse": W.components, "production_plan": production_plan}]})
	if name:
		mr.insert(set_name=name)
	else:
		mr.insert()
	return mr


def make_po(item, qty, company, supplier=None, rate=None, eta=None, material_request=None, mr_item=None, name=None, transaction_date=None, submit=None):
	"""A purchase order for a component, to the components store — submitted, or sent for approval where the purchase
	approval workflow is on."""
	from hipersign_trading.api.create import _tax_template

	W = whs(company)
	supplier = supplier or default_supplier(item, company)
	if not supplier:
		frappe.throw(_("Set a default supplier on {0} first.").format(item))
	eta = eta or add_days(today(), 7)
	tpl = _tax_template(company, True, supplier)
	po = frappe.get_doc({"doctype": "Purchase Order", "supplier": supplier, "company": company, "transaction_date": transaction_date or today(), "schedule_date": eta,
		"set_warehouse": W.components, "taxes_and_charges": tpl, "items": [{"item_code": item, "qty": flt(qty), "rate": flt(rate) or leaf_cost(item), "schedule_date": eta,
		"warehouse": W.components, "material_request": material_request, "material_request_item": mr_item}]})
	po.set_missing_values()
	if tpl:
		po.set("taxes", [])
		po.append_taxes_from_master()
	for i in po.items:
		i.rate = flt(rate) or leaf_cost(item) or i.rate
	if name:
		po.insert(set_name=name)
	else:
		po.insert()
	wf = frappe.db.get_value("Workflow", {"document_type": "Purchase Order", "is_active": 1})
	if submit is False:
		return po
	if not wf or submit:
		po.submit()
	else:
		from frappe.model.workflow import apply_workflow, get_transitions

		acts = [t.action for t in get_transitions(po)]
		if acts:
			po = apply_workflow(po, acts[0])
	clear_cache()
	return po


def receive_po(po_name, posting_date=None, rejected=0, name=None):
	"""Goods received into the components store (rejected units into the rejects store)."""
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	po = frappe.get_doc("Purchase Order", po_name)
	W = whs(po.company)
	pr = make_purchase_receipt(po_name)
	pr.posting_date = posting_date or today()
	pr.set_posting_time = 1
	for i in pr.items:
		i.warehouse = W.components
		if rejected:
			i.rejected_qty = flt(rejected)
			i.received_qty = flt(i.qty)
			i.qty = flt(i.qty) - flt(rejected)
			i.rejected_warehouse = W.rejected
	if rejected:
		pr.rejected_warehouse = W.rejected
	if name:
		pr.insert(set_name=name)
	else:
		pr.insert()
	pr.submit()
	clear_cache()
	return pr


def make_qi(stage, item, sample, fails=0, lot=None, reference_type=None, reference_name=None, work_order=None, operation=None, result=None, reason=None,
		rework=0, rejected=0, inspected_by=None, report_date=None, submit=True, name=None, readings=None):
	"""A quality inspection (incoming lot, in-process patrol or final batch) with the AQL result; a final inspection that
	passes gets its test certificate number."""
	if not reference_type:
		if work_order:
			jc = frappe.db.get_value("Job Card", {"work_order": work_order, "docstatus": ["<", 2]}, "name", order_by="creation desc")
			reference_type, reference_name = ("Job Card", jc) if jc else (None, None)
	if not reference_type or not reference_name:
		frappe.throw(_("Choose the goods receipt or the work order the inspection is for."))
	company = frappe.db.get_value(reference_type, reference_name, "company")
	acc = cint(fails) <= max(0, math.floor(flt(sample) / 50))  # the prototype's acceptance number (AQL 1.0, sample code letters)
	res = result or ("Rework" if flt(rework) else "Accepted" if acc else "Rejected")
	qi = frappe.get_doc({"doctype": "Quality Inspection", "inspection_type": "Incoming" if stage == "Incoming" else "In Process", "reference_type": reference_type,
		"reference_name": reference_name, "item_code": item, "sample_size": flt(sample), "inspected_by": inspected_by or frappe.session.user, "report_date": report_date or today(),
		"company": company, "manual_inspection": 1, "status": "Rejected" if res == "Rejected" else "Accepted", "remarks": reason,
		"hs_qc_stage": stage, "hs_work_order": work_order, "hs_operation": operation, "hs_result": res if submit else "Pending", "hs_lot_qty": flt(lot), "hs_fails": cint(fails),
		"hs_rework_qty": flt(rework), "hs_rejected_qty": flt(rejected), "quality_inspection_template": frappe.db.get_value("Item", item, "quality_inspection_template")})
	if readings:
		for spec, value, reading in readings:
			_param(spec)
			qi.append("readings", {"specification": spec, "value": value, "reading_value": reading, "numeric": 0, "manual_inspection": 1, "status": "Accepted"})
	elif qi.quality_inspection_template:
		qi.get_item_specification_details()
		for r in qi.readings:
			r.manual_inspection = 1
			r.status = "Accepted"
	if name:
		qi.insert(set_name=name)
	else:
		qi.insert()
	if submit:
		_finish_qi(qi)
	clear_cache()
	return qi


def _param(spec):
	if not frappe.db.exists("Quality Inspection Parameter", spec):
		frappe.get_doc({"doctype": "Quality Inspection Parameter", "parameter": spec}).insert(ignore_permissions=True)


def _finish_qi(qi):
	if qi.hs_qc_stage == "Final" and qi.hs_result in ("Accepted", "Accepted with deviation") and not qi.hs_certificate_no:
		wo = qi.hs_work_order or ""
		qi.hs_certificate_no = f"QC-CERT-{getdate(qi.report_date).year}-{wo[-4:] if wo else qi.name[-4:]}"
	qi.status = "Rejected" if qi.hs_result == "Rejected" else "Accepted"
	for r in qi.readings:
		r.status = r.status or "Accepted"
	qi.submit()


# ---------------------------------------------------------------- the shop floor: job cards
def _jc(name):
	jc = frappe.get_doc("Job Card", name)
	if jc.docstatus != 0:
		frappe.throw(_("{0} is already completed.").format(name))
	return jc


def loss_left(jc):
	"""The units this job card loses: the scrap of the operations before it and its own, less what the operation's
	completed job cards already booked as process loss (ERPNext carries the loss down the routing: the last operation's
	loss is the work order's)."""
	ops = frappe.get_all("Work Order Operation", filters={"parent": jc.work_order}, fields=["name", "idx"], order_by="idx asc")
	idx = next((o.idx for o in ops if o.name == jc.operation_id), 0)
	pos = {o.name: o.idx for o in ops}
	up = own = booked = 0.0
	for c in frappe.get_all("Job Card", filters={"work_order": jc.work_order, "docstatus": ["<", 2], "is_corrective_job_card": 0, "name": ["!=", jc.name or ""]},
			fields=["operation_id", "hs_scrap_qty", "process_loss_qty", "docstatus"]):
		if pos.get(c.operation_id, 0) < idx:
			up += flt(c.hs_scrap_qty)
		elif c.operation_id == jc.operation_id:
			own += flt(c.hs_scrap_qty)
			if c.docstatus == 1:
				booked += flt(c.process_loss_qty)
	return max(0, up + own + flt(jc.hs_scrap_qty) - booked)


def flow_line(wo):
	"""The shop floor runs the routing as a flow line — the next operation starts on the first units while the one before
	is still running — so the work order's job cards carry no sequence (the job ticket keeps the order)."""
	frappe.db.sql("update `tabJob Card` set sequence_id = 0 where work_order = %s and docstatus = 0", wo)


def _keep(jc):
	"""ERPNext books everything not completed as process loss: the pending quantity keeps the loss at the scrap recorded."""
	done = sum(flt(r.completed_qty) for r in jc.time_logs)
	jc.sequence_id = 0
	jc.pending_qty = max(0, flt(jc.for_quantity) - done - loss_left(jc))


def _close_open(jc, when=None):
	when = get_datetime(when or now_datetime())
	for r in jc.time_logs:
		if r.from_time and not r.to_time:
			r.to_time = max(when, get_datetime(r.from_time))
			r.time_in_mins = (get_datetime(r.to_time) - get_datetime(r.from_time)).total_seconds() / 60


def _upstream(jc):
	"""v1.8.2: the operation before this one on the work order (routing order) and the units it has done so far — a flow
	line lets the next operation start on the first units, but never run ahead of the one before. None for the first."""
	ops = frappe.get_all("Work Order Operation", filters={"parent": jc.work_order}, fields=["name", "operation", "idx"], order_by="idx asc")
	pos = next((i for i, o in enumerate(ops) if o.name == jc.operation_id), 0)
	if pos == 0:
		return None
	prev = ops[pos - 1]
	done = frappe.db.sql("""select coalesce(sum(tl.completed_qty), 0) from `tabJob Card Time Log` tl join `tabJob Card` j on j.name = tl.parent
		where j.operation_id = %s and j.docstatus < 2""", prev.name)[0][0]
	return prev.operation, flt(done)


def jc_start(name, employee=None, when=None):
	jc = _jc(name)
	if any(r.from_time and not r.to_time for r in jc.time_logs):
		return jc
	if employee:
		jc.hs_operator = employee
	jc.is_paused = 0
	jc.append("time_logs", {"from_time": get_datetime(when or now_datetime()), "completed_qty": 0})
	_keep(jc)
	jc.save()
	_wo_in_process(jc.work_order)
	clear_cache()
	return jc


def _wo_in_process(wo):
	"""The first job card started moves a released work order to In Process (as ERPNext does when time is booked)."""
	st = frappe.db.get_value("Work Order", wo, "status")
	if st == "Not Started":
		frappe.db.set_value("Work Order", wo, "status", "In Process", update_modified=False)


def jc_pause(name, when=None):
	jc = _jc(name)
	_close_open(jc, when)
	jc.is_paused = 1
	_keep(jc)
	jc.save()
	clear_cache()
	return jc


def jc_qty(name, n, when=None):
	"""Quantity done on the operation: on the running time log, or — when the card is not running — a time log of the
	routing minutes for that quantity ending now."""
	jc = _jc(name)
	if jc.is_paused:  # v1.8.4: a paused card took quantities — resume it first
		frappe.throw(_("{0} is paused — tap Start to resume it, then record the quantity.").format(name), title=_("Job card paused"))
	n = flt(n)
	done = sum(flt(r.completed_qty) for r in jc.time_logs)
	room = flt(jc.for_quantity) - done - loss_left(jc)
	if room <= 0:
		frappe.throw(_("{0}: all {1} units are done or scrapped.").format(name, _nf(jc.for_quantity)))
	up = _upstream(jc)
	if up and done + min(n, room) > up[1]:
		if up[1] - done <= 0:
			frappe.throw(_("{0} has done {1} units — this operation cannot run ahead of it.").format(_(up[0]), _nf(up[1])))
		room = up[1] - done
	n = min(n, room)
	run = next((r for r in jc.time_logs if r.from_time and not r.to_time), None)
	if run:
		run.completed_qty = flt(run.completed_qty) + n
	else:
		mins = flt(frappe.db.get_value("Work Order Operation", jc.operation_id, "time_in_mins")) / (flt(frappe.db.get_value("Work Order", jc.work_order, "qty")) or 1) * n
		end = get_datetime(when or now_datetime())
		jc.append("time_logs", {"from_time": add_to_date(end, minutes=-max(1, mins)), "to_time": end, "time_in_mins": max(1, mins), "completed_qty": n})
	_keep(jc)
	jc.save()
	_wo_in_process(jc.work_order)
	clear_cache()
	return jc


def jc_scrap(name, n=1):
	jc = _jc(name)
	if jc.is_paused:  # v1.8.4: no scrap on a paused card
		frappe.throw(_("{0} is paused — tap Start to resume it, then record the scrap.").format(name), title=_("Job card paused"))
	jc.hs_scrap_qty = flt(jc.hs_scrap_qty) + flt(n or 1)
	done = sum(flt(r.completed_qty) for r in jc.time_logs)
	if done + loss_left(jc) > flt(jc.for_quantity):
		frappe.throw(_("{0}: done and scrap cannot pass the {1} units of the operation.").format(name, _nf(jc.for_quantity)))
	_keep(jc)
	jc.save()
	clear_cache()
	return jc


def jc_operator(name, employee):
	jc = frappe.get_doc("Job Card", name)
	jc.check_permission("write")
	jc.db_set("hs_operator", employee or None)
	clear_cache()
	return jc


def jc_complete(name, when=None):
	"""Complete the operation: the remaining units are done (less the scrap) and the job card is submitted — the work order's
	operation shows the quantity, the process loss and the actual time (labour and overhead for the finished goods)."""
	jc = _jc(name)
	_close_open(jc, when)
	done = sum(flt(r.completed_qty) for r in jc.time_logs)
	rest = flt(jc.for_quantity) - done - loss_left(jc)
	if rest < -0.0001:
		frappe.throw(_("{0}: {1} done and {2} lost is more than the {3} units of the job card.").format(name, _nf(done), _nf(loss_left(jc)), _nf(jc.for_quantity)))
	up = _upstream(jc)
	if rest > 0 and up and done + rest > up[1] + 0.0001:
		frappe.throw(_("{0} has done {1} of {2} units — complete it first, then this operation.").format(_(up[0]), _nf(up[1]), _nf(jc.for_quantity)))
	if rest > 0:
		mins = flt(frappe.db.get_value("Work Order Operation", jc.operation_id, "time_in_mins")) / (flt(frappe.db.get_value("Work Order", jc.work_order, "qty")) or 1) * rest
		end = get_datetime(when or now_datetime())
		if not jc.time_logs or mins >= 1:
			jc.append("time_logs", {"from_time": add_to_date(end, minutes=-max(1, mins)), "to_time": end, "time_in_mins": max(1, mins), "completed_qty": rest})
		else:
			jc.time_logs[-1].completed_qty = flt(jc.time_logs[-1].completed_qty) + rest
	jc.is_paused = 0
	jc.pending_qty = 0
	jc.sequence_id = 0
	jc.save()
	jc.submit()
	clear_cache()
	return jc


def book(w, qty):
	"""Before finished goods are received, every operation must show the quantity done: a live job card with enough done is
	split — the done part is submitted for the quantity received, a new job card carries the rest (ERPNext's batches)."""
	from erpnext.manufacturing.doctype.work_order.work_order import make_job_card

	target = flt(w.produced_qty) + flt(w.process_loss_qty) + flt(qty)
	for o in w.operations:
		have = flt(frappe.db.get_value("Work Order Operation", o.name, "completed_qty")) + flt(frappe.db.get_value("Work Order Operation", o.name, "process_loss_qty"))
		if have >= target - 0.0001:
			continue
		live = frappe.db.get_value("Job Card", {"operation_id": o.name, "docstatus": 0, "is_corrective_job_card": 0}, "name", order_by="creation asc")
		if not live:
			frappe.throw(_("Operation {0} ({1}) has only {2} done — {3} needed.").format(o.idx * 10, o.operation, _nf(have), _nf(target)))
		jc = frappe.get_doc("Job Card", live)
		done = sum(flt(r.completed_qty) for r in jc.time_logs)
		need = target - have
		if done + loss_left(jc) >= flt(jc.for_quantity) - 0.0001:
			jc_complete(jc.name)
			continue
		if done < need - 0.0001:
			frappe.throw(_("Operation {0} ({1}) has {2} done on {3} — {4} needed before the finished goods are received.").format(
				o.idx * 10, o.operation, _nf(have + done), jc.name, _nf(target)))
		_split(jc, need, make_job_card)
	clear_cache()


def _split(jc, q, make_job_card):
	"""Submit q done units of a live job card (its time pro rata) and carry the rest on a new job card for the operation."""
	running = any(r.from_time and not r.to_time for r in jc.time_logs)
	_close_open(jc)
	logs = [r for r in jc.time_logs if r.from_time and r.to_time]
	mins = sum((get_datetime(r.to_time) - get_datetime(r.from_time)).total_seconds() / 60 for r in logs)
	done = sum(flt(r.completed_qty) for r in jc.time_logs)
	start = min((get_datetime(r.from_time) for r in logs), default=now_datetime())
	share = mins * q / done if done else 0
	rest_qty = flt(jc.for_quantity) - q
	scrap = flt(jc.hs_scrap_qty)
	op = frappe._dict(jc.as_dict())
	# the booked part: this job card, for q
	jc.set("time_logs", [])
	jc.append("time_logs", {"from_time": start, "to_time": add_to_date(start, minutes=max(1, share)), "time_in_mins": max(1, share), "completed_qty": q})
	jc.for_quantity = q
	jc.hs_scrap_qty = 0
	jc.pending_qty = 0
	jc.is_paused = 0
	jc.sequence_id = 0
	jc.save()
	jc.submit()
	# the rest: a new job card for the operation with what was already done beyond q, the scrap and the operator
	make_job_card(jc.work_order, [{"name": jc.operation_id, "operation": jc.operation, "idx": jc.operation_row_id, "qty": rest_qty, "pending_qty": rest_qty}])
	_clear_msgs()
	flow_line(jc.work_order)
	new = frappe.get_doc("Job Card", frappe.db.get_value("Job Card", {"operation_id": jc.operation_id, "docstatus": 0, "name": ["!=", jc.name]}, "name",
		order_by="creation desc"))
	new.hs_operator = op.hs_operator
	new.hs_scrap_qty = scrap
	left = done - q
	if left > 0:
		s2 = add_to_date(start, minutes=max(1, share))
		m2 = max(1, mins - share)
		new.append("time_logs", {"from_time": s2, "to_time": add_to_date(s2, minutes=m2), "time_in_mins": m2, "completed_qty": left})
	if running:
		new.append("time_logs", {"from_time": now_datetime(), "completed_qty": 0})
	_keep(new)
	new.save()
	return new


# ---------------------------------------------------------------- material transfer, manufacture, delivery, invoice, close
def transfer(wo_name, pct=100, picked_by=None, posting_date=None, name=None, extra=None, from_warehouse=None, to_warehouse=None):
	"""Stores pick the components of the work order and transfer them to WIP (Material Transfer for Manufacture).
	v1.8.4: the stores picked in the window (from / to) are used; blank = the work order's own stores."""
	from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

	w = frappe.get_doc("Work Order", wo_name)
	if w.docstatus != 1:
		frappe.throw(_("Release {0} first (it is a draft).").format(wo_name))
	for wh in (from_warehouse, to_warehouse):
		if wh and frappe.db.get_value("Warehouse", wh, "company") != w.company:
			frappe.throw(_("{0} is not a store of {1}.").format(wh, w.company))
	if from_warehouse and to_warehouse and from_warehouse == to_warehouse:
		frappe.throw(_("From and To must be different stores."))
	left = flt(w.qty) - flt(w.material_transferred_for_manufacturing)
	q = min(left, flt(w.qty) * flt(pct or 100) / 100)
	if q <= 0:
		frappe.throw(_("{0}: every component is already issued to WIP.").format(wo_name))
	sh = wo_shortages(w, from_warehouse)
	sh = [x for x in sh if x.need and x.stock < x.need * q / max(left, 1) - 0.0001]
	if sh:
		frappe.throw(_("Cannot issue {0} — short of {1}.").format(wo_name, ", ".join(x.item for x in sh)))
	se = frappe.get_doc(make_stock_entry(wo_name, "Material Transfer for Manufacture", q))
	se.naming_series = "MTW-.YYYY.-.####"
	if from_warehouse:
		se.from_warehouse = from_warehouse
		for r in se.items:
			r.s_warehouse = from_warehouse
	if to_warehouse:
		se.to_warehouse = to_warehouse
		for r in se.items:
			r.t_warehouse = to_warehouse
	if posting_date:
		se.posting_date, se.set_posting_time = posting_date, 1
	se.hs_picked_by = picked_by
	if extra:
		for r in se.items:
			r.qty = flt(r.qty * extra, 3)
	if name:
		se.insert(set_name=name)
	else:
		se.insert()
	se.submit()
	frappe.db.set_value("Work Order", wo_name, "hs_hold_reason", None, update_modified=False)
	clear_cache()
	return se


def manufacture(wo_name, qty=None, batch=None, serial_from=None, posting_date=None, name=None, fg_warehouse=None):
	"""Finished goods into the store: WIP materials consumed, labour and overhead from the job cards' time added, the batch
	allocated. qty is the good units received; the scrap recorded on the job cards is booked as process loss on the entry
	that completes the work order."""
	w = frappe.get_doc("Work Order", wo_name)
	if w.docstatus != 1 or w.status in ("Completed", "Closed", "Stopped"):
		frappe.throw(_("{0} is {1}.").format(wo_name, _(w.status if w.docstatus else "Draft")))
	scrap = sum(flt(j.hs_scrap_qty) for j in job_cards(wo_name))
	booked_loss = flt(w.process_loss_qty)
	room = flt(w.qty) - flt(w.produced_qty) - booked_loss  # units still to come through (good + scrap)
	pending_loss = min(max(0, scrap - booked_loss), room)
	q = min(flt(qty), room - pending_loss) if qty else room - pending_loss
	if q <= 0:
		frappe.throw(_("{0} is already fully produced.").format(wo_name))
	# the entry that completes the work order books the scrap not yet booked as process loss
	loss = pending_loss if q + pending_loss >= room - 0.0001 else 0
	book(w, q + loss)
	w.reload()
	se = frappe.new_doc("Stock Entry")
	se.update({"purpose": "Manufacture", "stock_entry_type": "Manufacture", "work_order": wo_name, "company": w.company, "from_bom": 1, "bom_no": w.bom_no,
		"use_multi_level_bom": w.use_multi_level_bom, "fg_completed_qty": q + loss, "process_loss_qty": loss, "from_warehouse": w.wip_warehouse,
		"to_warehouse": fg_warehouse or w.fg_warehouse, "naming_series": "MFE-.YYYY.-.####", "hs_serial_from": serial_from})
	if posting_date:
		se.posting_date, se.set_posting_time = posting_date, 1
	se.flags.hs_keep_loss = True
	se.get_items()
	if loss:
		for r in se.items:
			if r.is_finished_item or (r.t_warehouse and not r.s_warehouse and r.item_code == w.production_item):
				r.qty = r.transfer_qty = q
	b = None
	if frappe.get_cached_value("Item", w.production_item, "has_batch_no"):
		b = batch or f"B{getdate(posting_date or today()).strftime('%y%m')}-{batch_code(w.production_item)}-{frappe.db.count('Batch', {'item': w.production_item}) + 1:02d}"
		if not frappe.db.exists("Batch", b):
			frappe.get_doc({"doctype": "Batch", "batch_id": b, "item": w.production_item, "manufacturing_date": posting_date or today(),
				"reference_doctype": "Work Order", "reference_name": wo_name}).insert(ignore_permissions=True)
		for r in se.items:
			if r.item_code == w.production_item and r.t_warehouse:
				r.batch_no = b
				r.use_serial_batch_fields = 1
	if name:
		se.insert(set_name=name)
	else:
		se.insert()
	se.submit()
	clear_cache()
	return se


def batch_code(item):
	"""The product part of a batch number, as on the prototype: FG-P6060 → P60, FG-HB150 → HB, SA-DRV40 → DR."""
	import re

	m = re.match(r"([A-Z]+)(\d*)", item.split("-")[-1].upper())
	if not m:
		return item[-3:].upper()
	letters, digits = m.groups()
	return letters + digits[:2] if len(letters) == 1 else letters[:2]


def deliver(so_name, posting_date=None, name=None, warehouse=None):
	"""Delivery note for what is still to deliver on the order, from the finished goods store (batches picked FIFO)."""
	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

	s = frappe.get_doc("Sales Order", so_name)
	W = whs(s.company)
	dn = make_delivery_note(so_name)
	dn.posting_date = posting_date or today()
	dn.set_posting_time = 1
	for i in dn.items:
		i.warehouse = warehouse or W.fg
	_split_batches(dn)
	if name:
		dn.insert(set_name=name)
	else:
		dn.insert()
	dn.submit()
	clear_cache()
	return dn


def _split_batches(dn):
	"""A delivery line of a batch item becomes one line per batch, oldest first (one batch may not cover the order)."""
	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import get_auto_batch_nos

	rows = []
	for i in dn.items:
		if not frappe.get_cached_value("Item", i.item_code, "has_batch_no"):
			rows.append(i.as_dict())
			continue
		left = flt(i.stock_qty or i.qty)
		picks = get_auto_batch_nos(frappe._dict(item_code=i.item_code, warehouse=i.warehouse, posting_date=dn.posting_date, posting_time=dn.posting_time or "23:59:00",
			qty=left))
		for p in picks:
			q = min(left, flt(p.qty))
			if q <= 0:
				continue
			r = i.as_dict()
			r.update({"name": None, "idx": None, "qty": q, "stock_qty": q, "batch_no": p.batch_no, "use_serial_batch_fields": 1, "serial_and_batch_bundle": None})
			rows.append(r)
			left -= q
		if left > 0.0001:
			frappe.throw(_("Only {0} of {1} in stock in {2}.").format(_nf(flt(i.qty) - left), i.item_code, i.warehouse))
	dn.set("items", [])
	for r in rows:
		dn.append("items", {k: v for k, v in r.items() if k not in ("name", "idx", "parent", "parentfield", "parenttype", "doctype", "creation", "modified")})


def invoice(so_name, posting_date=None, name=None):
	from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

	dn = frappe.db.sql("""select distinct dn.name from `tabDelivery Note` dn join `tabDelivery Note Item` i on i.parent = dn.name where i.against_sales_order = %s
		and dn.docstatus = 1 and dn.per_billed < 100 order by dn.posting_date asc limit 1""", so_name)
	if not dn:
		frappe.throw(_("Nothing delivered on {0} is waiting for its invoice.").format(so_name))
	si = make_sales_invoice(dn[0][0])
	si.posting_date = posting_date or today()
	si.set_posting_time = 1
	si.due_date = add_days(si.posting_date, 30)
	if si.get("payment_schedule"):
		si.set("payment_schedule", [])
	if name:
		si.insert(set_name=name)
	else:
		si.insert()
	si.submit()
	clear_cache()
	return si


def close_wo(wo_name):
	w = frappe.get_doc("Work Order", wo_name)
	if w.status == "Closed":
		return w
	if w.status != "Completed":
		frappe.throw(_("{0} is {1} — receive the finished goods first.").format(wo_name, _(w.status)))
	w.update_status("Closed")
	w.on_close_or_cancel() if hasattr(w, "on_close_or_cancel") else None
	clear_cache()
	return w


# ---------------------------------------------------------------- "Complete step N"
def _log(so, i, note=None, user=None, when=None):
	s = so_doc(so)
	frappe.get_doc({"doctype": "Manufacturing Step Log", "sales_order": so, "work_order": main_wo(so), "company": s.company, "step": i + 1, "step_name": STEPS[i][0],
		"completed_by": user or frappe.session.user, "completed_on": when or now_datetime(), "note": note}).insert(ignore_permissions=True)


def complete_step(so, note=None):
	"""Complete the sales order's current step: the role check, then the document the step needs (plan, approval, release,
	issue, finished goods, delivery, invoice, close), the step log and a comment."""
	s = frappe.get_doc("Sales Order", so)
	s.check_permission("read")
	i = cint(s.get("hs_mfg_step"))
	if i >= N:
		frappe.throw(_("{0} is closed — all {1} steps are done.").format(so, N))
	roles = list(STEP_ROLES.get(i, [MD]))
	wo = main_wo(so)
	w = frappe.get_doc("Work Order", wo) if wo else None
	if i == 12 and w:
		f = wo_fig(wo)
		if f.qty and f.scrap / f.qty * 100 > SCRAP_LIMIT:
			roles = [PM, MD]
	_need(roles, _("Step {0} ({1})").format(i + 1, _(STEPS[i][1])))
	msg = ""
	if i == 0 and s.docstatus != 1:
		frappe.throw(_("{0} is a forecast — confirm it as a sales order first.").format(so))
	if i == 1 and not wo:
		r = make_plan([so])
		msg = _("{0} — work orders {1}").format(r.plan, ", ".join(r.wos)) + (_(" · material requests {0}").format(", ".join(r.mrs)) if r.mrs else "")
		wo = main_wo(so)
	if i >= 2 and not wo:
		frappe.throw(_("{0} has no work order yet — complete the planning step.").format(so))
	if i == 2 and w and w.bom_no != bom_of(w.production_item):
		_need([PM, MD], _("A BOM that is not the default version"))
	if i == 4:
		pend = [m for m in _mrs_of(w) if m.docstatus == 0]
		for m in {m.name for m in pend}:
			frappe.get_doc("Material Request", m).submit()
		if pend:
			msg = _("{0} material request(s) approved").format(len({m.name for m in pend}))
	if i == 5 and w and w.docstatus < 2 and not flt(w.material_transferred_for_manufacturing):
		sh = [x for x in wo_shortages(w) if x.short_now > 0]
		if sh:
			frappe.throw(_("Still short of {0} — receive the purchase order first.").format(", ".join(f"{x.item} ({_nf(x.short_now)})" for x in sh)))
	if i == 6 and w:
		pend = frappe.get_all("Quality Inspection", filters={"docstatus": 0, "hs_qc_stage": "Incoming", "item_code": ["in", [r.item_code for r in w.required_items] or [""]]}, pluck="name")
		if pend:
			frappe.throw(_("Incoming inspection {0} is still pending.").format(", ".join(pend)))
	if i == 7 and w.docstatus == 0:
		w.hs_hold_reason = None
		w.save()
		w.submit()
		_clear_msgs()
		flow_line(w.name)
		msg = _("{0} released — {1} job cards").format(w.name, frappe.db.count("Job Card", {"work_order": w.name}))
	if i == 8 and w and flt(w.material_transferred_for_manufacturing) < flt(w.qty):
		se = transfer(w.name)
		msg = _("{0} — components issued to WIP").format(se.name)
	if i == 9 and w and not frappe.db.exists("Job Card", {"work_order": w.name}):
		from erpnext.manufacturing.doctype.work_order.work_order import make_job_card

		make_job_card(w.name, [{"name": o.name, "operation": o.operation, "idx": o.idx, "qty": w.qty, "pending_qty": w.qty} for o in w.operations])
		_clear_msgs()
		flow_line(w.name)
	if i == 13 and w:
		ok = frappe.db.exists("Quality Inspection", {"hs_work_order": w.name, "hs_qc_stage": "Final", "docstatus": 1, "hs_result": ["in", ["Accepted", "Accepted with deviation"]]})
		if not ok:
			frappe.throw(_("Record the final inspection of {0} first (Quality → New quality inspection, Final).").format(w.name))
	if i == 14 and w:
		w.reload()
		if flt(w.produced_qty) + flt(w.process_loss_qty) < flt(w.qty):
			se = manufacture(w.name)
			msg = _("{0} — {1} received to finished goods").format(se.name, _nf(next((r.qty for r in se.items if r.is_finished_item), 0)))
	if i == 17:
		s.reload()
		if s.docstatus == 1 and flt(s.per_delivered) < 100:
			dn = deliver(so)
			msg = _("Delivery note {0}").format(dn.name)
	if i == 18:
		s.reload()
		if flt(s.per_billed) < 100:
			si = invoice(so)
			msg = _("Invoice {0} — {1}").format(si.name, _money(si.grand_total, si.currency))
	if i == 21 and w:
		w.reload()
		close_wo(w.name)
	frappe.db.set_value("Sales Order", so, "hs_mfg_step", i + 1, update_modified=False)
	clear_cache()
	_log(so, i, note)
	frappe.get_doc("Sales Order", so).add_comment("Info", _("Manufacturing step {0} completed — {1}").format(i + 1, _(STEPS[i][0])))
	clear_cache()
	nxt = _(STEPS[i + 1][0]) if i + 1 < N else None
	return {"message": (_("{0} — work order closed").format(so) if not nxt else _("Done: {0} → next: {1}").format(_(STEPS[i][1]), nxt)) + (f" · {msg}" if msg else ""),
		"step": i + 1}


# ---------------------------------------------------------------- the actions (buttons on the pages, the shop floor and the panels)
@frappe.whitelist(methods=["POST"])
def act(action, name, args=None):
	"""Every Manufacturing button: one entry point (the view-only demo refuses it as a write)."""
	args = frappe._dict(frappe.parse_json(args) if isinstance(args, str) else (args or {}))
	fn = ACTIONS.get(action)
	if not fn:
		frappe.throw(_("Unknown action"))
	r = fn(name, args) or {}
	clear_cache()
	return r


def _wo_from(name):
	if frappe.db.exists("Work Order", name):
		return name
	return main_wo(name) if frappe.db.exists("Sales Order", name) else None


def _a_step(name, a):
	so = name if frappe.db.exists("Sales Order", name) else frappe.db.get_value("Work Order", name, "sales_order")
	if not so:
		frappe.throw(_("{0} is made to stock — its steps follow the work order's own status.").format(name))
	return complete_step(so, a.get("note"))


def _a_plan(name, a):
	_need([PM, MM, MD], _("A production plan"))
	sos = [name] if name and name != "open" else [x for x in so_names(companies(), include_forecast=False) if not main_wo(x) and so_doc(x).docstatus == 1]
	r = make_plan(sos)
	return {"message": _("{0} — {1} work order(s) proposed ({2})").format(r.plan, len(r.wos), ", ".join(r.wos)) + (_(" · {0} material request(s)").format(len(r.mrs)) if r.mrs else "")}


def _a_mrp(name, a):
	cos = companies()
	sh = [x for x in shortages(cos) if x.short_now > 0]
	n = frappe.db.count("Work Order", {"company": ["in", cos or [""]], "docstatus": ["<", 2], "status": ["in", ["Draft", "Not Started"]]})
	return {"message": _("MRP run — {0} work orders netted · {1} shortage(s){2}").format(n, len(sh), (": " + ", ".join(x.item for x in sh)) if sh else "")}


def _a_raise_po(name, a):
	frappe.has_permission("Purchase Order", "create", throw=True)
	co = a.get("company") or next((x.company for x in shortages(companies()) if x.item == name), None) or companies()[0]
	po = make_po(name, a.get("qty"), co, eta=add_days(today(), cint(a.get("days") or 7)))
	return {"message": _("{0} — {1} × {2} from {3} ({4})").format(po.name, _nf(a.get("qty")), item_info(name).item_name, po.supplier,
		_(po.get("workflow_state") or ("Submitted" if po.docstatus == 1 else "Draft"))), "open": ["Purchase Order", po.name]}


def _a_mr_approve(name, a):
	m = frappe.get_doc("Material Request", name)
	m.check_permission("submit")
	_need([PM, MM, MD, PUM], _("Approving a material request"))
	m.submit()
	return {"message": _("{0} approved — the buyer orders it next").format(name)}


def _a_mr_po(name, a):
	m = frappe.get_doc("Material Request", name)
	if m.docstatus != 1:
		m.check_permission("submit")
		m.submit()
	r = m.items[0]
	po = make_po(r.item_code, flt(r.qty) - flt(r.ordered_qty), m.company, material_request=m.name, mr_item=r.name, eta=r.schedule_date)
	return {"message": _("{0} approved · {1} sent to {2}").format(name, po.name, po.supplier), "open": ["Purchase Order", po.name]}


def _a_po_receive(name, a):
	frappe.has_permission("Purchase Receipt", "create", throw=True)
	pr = receive_po(name, rejected=a.get("rejected"))
	return {"message": _("{0} — received into {1}").format(pr.name, pr.items[0].warehouse if pr.items else ""), "open": ["Purchase Receipt", pr.name]}


def _a_release(name, a):
	w = frappe.get_doc("Work Order", name)
	w.check_permission("submit")
	_need([PM, MM, MD], _("Releasing a work order"))
	if w.docstatus == 0:
		w.hs_hold_reason = None
		w.save()
		w.submit()
		_clear_msgs()
		flow_line(name)
	return {"message": _("{0} released — {1} job cards for the shop floor").format(name, frappe.db.count("Job Card", {"work_order": name}))}


def _a_transfer(name, a):
	frappe.has_permission("Stock Entry", "create", throw=True)
	se = transfer(_wo_from(name), a.get("pct") or 100, a.get("by"))
	return {"message": _("{0} — {1} components issued to WIP for {2}").format(se.name, len(se.items), se.work_order), "open": ["Stock Entry", se.name]}


def _a_manufacture(name, a):
	frappe.has_permission("Stock Entry", "create", throw=True)
	wo = _wo_from(name)
	se = manufacture(wo, a.get("qty"), a.get("batch"), a.get("serial_from"))
	fg = next((r for r in se.items if r.is_finished_item), None)
	return {"message": _("{0} — {1} × {2} to finished goods · {3}").format(se.name, _nf(fg.qty if fg else 0), fg.item_name if fg else "",
		_money(fg.amount if fg else 0, frappe.get_cached_value("Company", se.company, "default_currency"))), "open": ["Stock Entry", se.name]}


def _jc_check(name):
	frappe.get_doc("Job Card", name).check_permission("write")


def _a_jc_start(name, a):
	_jc_check(name)
	jc = jc_start(name, a.get("employee"))
	return {"message": _("{0} started{1}").format(name, (" — " + frappe.db.get_value("Employee", jc.hs_operator, "employee_name")) if jc.hs_operator else "")}


def _a_jc_pause(name, a):
	_jc_check(name)
	jc_pause(name)
	return {"message": _("{0} paused — time logged").format(name)}


def _a_jc_qty(name, a):
	_jc_check(name)
	jc = jc_qty(name, a.get("n") or a.get("qty") or 10)
	return {"message": _("{0} · {1} of {2} done").format(name, _nf(jc.total_completed_qty), _nf(jc.for_quantity))}


def _a_jc_scrap(name, a):
	_jc_check(name)
	jc = jc_scrap(name, a.get("n") or 1)
	return {"message": _("Scrap recorded on {0} — {1} on this operation").format(name, _nf(jc.hs_scrap_qty))}


def _a_jc_done(name, a):
	_jc_check(name)
	jc = jc_complete(name)
	return {"message": _("{0} completed — {1} good · {2} scrap").format(name, _nf(jc.total_completed_qty), _nf(jc.process_loss_qty))}


def _a_jc_operator(name, a):
	jc_operator(name, a.get("employee"))
	return {"message": _("Operator on {0}: {1}").format(name, frappe.db.get_value("Employee", a.get("employee"), "employee_name") or "—")}


def _a_qi_accept(name, a):
	q = frappe.get_doc("Quality Inspection", name)
	q.check_permission("submit")
	_need([QCI, QM, MD], _("Accepting an inspection"))
	if q.docstatus != 0:
		frappe.throw(_("{0} is already decided.").format(name))
	q.hs_result = a.get("result") or "Accepted"
	if not q.remarks:
		q.remarks = _("Sample {0} — no defects").format(_nf(q.sample_size))
	_finish_qi(q)
	if q.hs_result == "Rejected":
		return {"message": _("{0} rejected").format(name)}
	return {"message": _("{0} accepted — lot released to stores").format(name)}


def _a_qi_reject(name, a):
	return _a_qi_accept(name, frappe._dict(a, result="Rejected"))


def _a_qi_rework(name, a):
	q = frappe.get_doc("Quality Inspection", name)
	_need([QCI, QM, PM, MD], _("Recording rework"))
	done = min(flt(q.hs_rework_qty), flt(q.hs_rework_done) + flt(a.get("n") or 4))
	q.db_set("hs_rework_done", done)
	return {"message": _("Rework: {0} of {1} done").format(_nf(done), _nf(q.hs_rework_qty))}


def _a_deliver(name, a):
	frappe.has_permission("Delivery Note", "create", throw=True)
	dn = deliver(name)
	return {"message": _("Delivery note {0}").format(dn.name), "open": ["Delivery Note", dn.name]}


def _a_invoice(name, a):
	frappe.has_permission("Sales Invoice", "create", throw=True)
	si = invoice(name)
	return {"message": _("Invoice {0} — {1}").format(si.name, _money(si.grand_total, si.currency)), "open": ["Sales Invoice", si.name]}


def _a_close(name, a):
	_need([PM, MM, MD], _("Closing a work order"))
	close_wo(name)
	return {"message": _("{0} closed").format(name)}


ACTIONS = {
	"step": _a_step, "plan": _a_plan, "mrp": _a_mrp, "raise_po": _a_raise_po, "mr_approve": _a_mr_approve, "mr_po": _a_mr_po, "po_receive": _a_po_receive,
	"release": _a_release, "transfer": _a_transfer, "manufacture": _a_manufacture, "jc_start": _a_jc_start, "jc_pause": _a_jc_pause, "jc_qty": _a_jc_qty,
	"jc_scrap": _a_jc_scrap, "jc_done": _a_jc_done, "jc_operator": _a_jc_operator, "qi_accept": _a_qi_accept, "qi_reject": _a_qi_reject, "qi_rework": _a_qi_rework,
	"deliver": _a_deliver, "invoice": _a_invoice, "close": _a_close,
}
