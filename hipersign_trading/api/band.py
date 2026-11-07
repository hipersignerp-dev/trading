"""v1.8.3 (prototype p20): the graph band — two or three graphs at the top of every page, drawn from that page's own
records (stage columns, trend, gauge, donut, ranked bars, a dark "needs attention" card or a heatmap).

get_band(key) returns a list of widget dicts; hs_charts.js draws them. Every widget is read with the user's own
permissions and built on its own: a missing doctype or field, or no read permission, drops only that widget.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, date_diff, flt, get_first_day, get_last_day, getdate, today

from hipersign_trading.api.home import period_range
from hipersign_trading.api.ui import get_period, scope_companies

OPEN_PO = ["To Receive and Bill", "To Receive", "To Bill"]


# ---------------------------------------------------------------- helpers
def _exists(dt):
	try:
		return bool(frappe.db.exists("DocType", dt))
	except Exception:
		return False


def _can(dt):
	return _exists(dt) and bool(frappe.has_permission(dt, "read"))


def _fields(dt, fields):
	meta = frappe.get_meta(dt)
	std = {"name", "docstatus", "owner", "creation", "modified", "modified_by"}
	out = []
	for f in fields:
		base = f.split(" as ")[0].strip()
		if base in std or meta.has_field(base):
			out.append(f)
	return out


def _rows(dt, filters=None, fields=("name",), limit=500, order_by=None):
	"""Records the user may read; filters on fields the doctype lacks are dropped (older sites), [] without permission."""
	if not _can(dt):
		return []
	meta = frappe.get_meta(dt)
	f = {}
	for k, v in (filters or {}).items():
		if k in ("name", "docstatus", "owner", "creation", "modified") or meta.has_field(k):
			f[k] = v
	kw = {"filters": f, "fields": _fields(dt, list(fields)), "limit_page_length": limit}
	if order_by:
		kw["order_by"] = order_by
	return frappe.get_list(dt, **kw)


def _co(dt, cos, extra=None):
	f = dict(extra or {})
	if cos and frappe.get_meta(dt).has_field("company"):
		f["company"] = ["in", cos]
	return f


def _scope():
	cos = scope_companies()
	start, end, label = period_range(get_period())
	cur = frappe.get_cached_value("Company", cos[0], "default_currency") if cos else "AED"
	return cos, getdate(start), getdate(end), label, cur or "AED"


def _pscope():
	"""Projects pages: the scope's companies when they have projects, else every project the user may read (as module_prj)."""
	cos, start, end, label, cur = _scope()
	if cos and _can("Project") and not frappe.get_list("Project", filters={"company": ["in", cos]}, fields=["name"], limit_page_length=1):
		pr = frappe.get_list("Project", fields=["company"], limit_page_length=1)
		cur = frappe.get_cached_value("Company", pr[0].company, "default_currency") if pr and pr[0].company else cur
		cos = []
	return cos, start, end, label, cur or "AED"


def _mscope():
	"""Manufacturing pages: the manufacturing companies of the scope (as module_mfg)."""
	from hipersign_trading.api import manufacturing as M

	cos, start, end, label, cur = _scope()
	mc = M.companies(cos) or []
	try:
		cur = M.currency(mc) or cur
	except Exception:
		pass
	return mc or [""], start, end, label, cur or "AED"


def _months(n=6):
	t = getdate(today())
	out = []
	for i in range(n - 1, -1, -1):
		s = get_first_day(add_months(t, -i))
		out.append((s, get_last_day(s), _(s.strftime("%b"))))
	return out


def _monthly(rows, date_field, val=None, n=6):
	ms = _months(n)
	data = [0] * n
	for r in rows:
		d = r.get(date_field)
		if not d:
			continue
		d = getdate(d)
		for i, (s, e, _l) in enumerate(ms):
			if s <= d <= e:
				data[i] += flt(val(r)) if val else 1
				break
	return [m[2] for m in ms], data


def _cnt(rows, key):
	out = {}
	for r in rows:
		k = key(r) if callable(key) else r.get(key)
		k = k or _("Not set")
		out[k] = out.get(k, 0) + 1
	return out


def _sum_by(rows, key, val):
	out = {}
	for r in rows:
		k = key(r) if callable(key) else r.get(key)
		k = k or _("Not set")
		out[k] = out.get(k, 0) + flt(val(r) if callable(val) else r.get(val))
	return out


def _k(v, cur=None):
	v = flt(v)
	a = abs(v)
	s = f"{v / 1e6:.1f}M" if a >= 1e6 else f"{v / 1e3:.1f}K" if a >= 1e3 else f"{v:,.0f}"
	return f"{cur} {s}" if cur else s


def _pc(x):
	return f"{round(flt(x) * 100)}%"


def _fd(d):
	return getdate(d).strftime("%d %b") if d else ""


COLORS = ["blue", "violet", "amber", "green", "teal", "red", "navy", "grey"]


def _top(d, n=6):
	return sorted(d.items(), key=lambda x: -x[1])[:n]


# widget builders
def W_stages(title, sub, stages, icon="git-merge", note=None):
	return {"type": "stages", "title": title, "sub": sub, "icon": icon, "stages": stages, "note": note}


def S(label, n, tone="", value=None, **kw):
	d = {"label": label, "n": cint(n), "tone": tone, "value": value}
	d.update(kw)
	return d


def W_trend(title, sub, labels, series, money=False, cur=None, icon="trending-up"):
	return {"type": "trend", "title": title, "sub": sub, "icon": icon, "labels": labels, "series": series, "money": money, "currency": cur}


def W_bars(title, sub, rows, money=False, cur=None, icon="chart-column"):
	return {"type": "bars", "title": title, "sub": sub, "icon": icon, "rows": rows, "money": money, "currency": cur}


def W_donut(title, sub, rows, center, center_label, money=False, cur=None, icon="chart-pie"):
	rows = [r for r in rows if flt(r["value"])]
	for i, r in enumerate(rows):
		r.setdefault("color", COLORS[i % len(COLORS)])
	return {"type": "donut", "title": title, "sub": sub, "icon": icon, "rows": rows, "center": str(center), "center_label": center_label, "money": money, "currency": cur}


def W_gauge(title, sub, pct, big, caption, note="", color="blue", icon="gauge"):
	return {"type": "gauge", "title": title, "sub": sub, "icon": icon, "pct": max(0, min(1, flt(pct))), "big": big, "caption": caption, "note": note, "color": color}


def W_dark(title, sub, big, big_sub, rows, empty=None, icon="triangle-alert"):
	return {"type": "dark", "title": title, "sub": sub, "icon": icon, "big": str(big), "big_sub": big_sub, "rows": rows[:3], "empty": empty or _("Nothing needs attention")}


def W_heat(title, sub, rows, cols, values, money=False, cur=None, icon="calendar"):
	return {"type": "heat", "title": title, "sub": sub, "icon": icon, "rows": rows, "cols": cols, "values": values, "money": money, "currency": cur}


def _bars_rows(d, n=6, color="blue", route=None):
	return [{"label": str(k), "value": round(flt(v), 2), "color": color, **({"route": route} if route else {})} for k, v in _top(d, n) if flt(v)]


# ---------------------------------------------------------------- Home
def b_home():
	cos, start, end, label, cur = _scope()
	ms = _months()
	si = _rows("Sales Invoice", _co("Sales Invoice", cos, {"docstatus": 1, "posting_date": [">=", ms[0][0]]}), ["posting_date", "base_net_total", "customer", "customer_name", "outstanding_amount", "base_grand_total", "conversion_rate"], 2000)
	pi = _rows("Purchase Invoice", _co("Purchase Invoice", cos, {"docstatus": 1, "posting_date": [">=", ms[0][0]]}), ["posting_date", "base_net_total"], 2000)
	out = []
	if si or pi:
		lb, s = _monthly(si, "posting_date", lambda r: r.base_net_total)
		_l, p = _monthly(pi, "posting_date", lambda r: r.base_net_total)
		ser = []
		if _can("Sales Invoice"):
			ser.append({"name": _("Sales"), "data": s, "color": "blue"})
		if _can("Purchase Invoice"):
			ser.append({"name": _("Purchases"), "data": p, "color": "violet"})
		out.append(lambda: W_trend(_("Sales and purchases"), _("Last 6 months · net · {0}").format(cur), lb, ser, True, cur))
	if _can("Sales Invoice"):
		def gauge():
			billed = sum(flt(r.base_grand_total) for r in si)
			os_ = sum(flt(r.outstanding_amount) * (flt(r.conversion_rate) or 1) for r in si)
			pct = (billed - os_) / billed if billed else 0
			return W_gauge(_("Collected"), _("Invoices of the last 6 months"), pct, _pc(pct), _("{0} still to collect").format(_k(os_, cur)),
				color="green" if pct >= 0.7 else "amber", icon="wallet")
		out.append(gauge)

		def heat():
			by = _sum_by(si, lambda r: r.customer_name or r.customer, "base_net_total")
			top = [k for k, _v in _top(by, 5)]
			vals = []
			for c in top:
				_lb, d = _monthly([r for r in si if (r.customer_name or r.customer) == c], "posting_date", lambda r: r.base_net_total)
				vals.append([round(x) for x in d])
			return W_heat(_("Who buys when"), _("Top customers · net sales by month"), top, [m[2] for m in ms], vals, True, cur, icon="users")
		out.append(heat)
	return out


# ---------------------------------------------------------------- Overview pages
def b_messages():
	since = add_days(today(), -30)
	cm = frappe.get_all("Comment", filters={"comment_type": ["in", ["Comment", "Info"]], "creation": [">=", since]}, fields=["comment_type", "content", "creation"], limit=1000)
	em = frappe.get_all("Communication", filters={"communication_type": "Communication", "creation": [">=", since]}, fields=["creation"], limit=1000)
	wa = [c for c in cm if c.comment_type == "Info" and "whatsapp" in (c.content or "").lower()]
	notes = [c for c in cm if c.comment_type == "Comment"]
	out = [lambda: W_donut(_("Conversations by kind"), _("Last 30 days"), [{"label": _("Notes on records"), "value": len(notes), "color": "blue"},
		{"label": _("Email"), "value": len(em), "color": "violet"}, {"label": _("WhatsApp"), "value": len(wa), "color": "green"}], len(notes) + len(em) + len(wa), _("messages"), icon="message-square")]

	def per_day():
		days = [add_days(today(), -i) for i in range(6, -1, -1)]
		f = lambda rows: [len([r for r in rows if str(r.creation)[:10] == str(d)]) for d in days]
		return W_trend(_("Messages per day"), _("Last 7 days"), [_fd(d) for d in days], [{"name": _("Team notes"), "data": f(notes), "color": "blue"},
			{"name": _("Email & WhatsApp"), "data": f(em + wa), "color": "violet"}])
	out.append(per_day)

	def mentions():
		ns = frappe.get_all("Notification Log", filters={"for_user": frappe.session.user, "read": 0}, fields=["subject", "document_type", "document_name", "creation", "type"],
			order_by="creation desc", limit=50)
		return W_dark(_("Waiting for you"), _("Unread notifications"), len(ns), _("unread"), [{"label": frappe.utils.strip_html_tags(n.subject or "")[:70] or n.document_name,
			"sub": f"{_(n.document_type or '')} · {_fd(n.creation)}", "value": "", **({"open": [n.document_type, n.document_name]} if n.document_type and n.document_name else {})} for n in ns], icon="bell")
	out.append(mentions)
	return out


def b_approvals():
	from hipersign_trading.api.approvals import pending

	items = pending()
	if not items:
		return [lambda: W_gauge(_("Approvals"), _("Nothing waiting"), 1, "0", _("waiting"), color="green", icon="inbox")]
	by_type = _cnt(items, "type")
	buckets = {_("Today"): 0, _("1–2 days"): 0, _("3–7 days"): 0, _("Over a week"): 0}
	for i in items:
		d = cint(i.get("days"))
		buckets[_("Today") if d < 1 else _("1–2 days") if d <= 2 else _("3–7 days") if d <= 7 else _("Over a week")] += 1
	old = sorted(items, key=lambda i: -cint(i.get("days")))
	return [
		lambda: W_bars(_("Waiting by type"), _("{0} approvals").format(len(items)), _bars_rows(by_type), icon="inbox"),
		lambda: W_donut(_("How long they wait"), _("Days since submitted"), [{"label": k, "value": v, "color": c} for (k, v), c in zip(buckets.items(), ["green", "blue", "amber", "red"])],
			len(items), _("waiting"), icon="clock"),
		lambda: W_dark(_("Oldest first"), _("{0} waiting over 2 days").format(len([i for i in items if cint(i.get("days")) > 2])), len(items), _("to approve"),
			[{"label": f"{i['type']} · {i['name']}", "sub": (i.get("description") or "")[:70] + (f" · {cint(i.get('days'))}d" if i.get("days") else ""),
				"value": _k(i["value"]) if flt(i.get("value")) else "", "open": [i["doctype"], i["name"]]} for i in old], icon="inbox"),
	]


def b_alerts():
	from hipersign_trading.alerts import can_see, evaluate

	al = [a for a in evaluate() if can_see(a) and a.get("status", "Open") == "Open"]
	sev = _cnt(al, "severity")
	return [
		lambda: W_donut(_("Alerts by level"), _("Open"), [{"label": _("High"), "value": sev.get("High", 0), "color": "red"}, {"label": _("Medium"), "value": sev.get("Medium", 0), "color": "amber"},
			{"label": _("Low"), "value": sev.get("Low", 0), "color": "blue"}], len(al), _("open"), icon="bell"),
		lambda: W_bars(_("Alerts by area"), _("Open insights"), _bars_rows(_cnt(al, "category")), icon="sparkles"),
		lambda: W_dark(_("Act on these"), _("Highest first"), sev.get("High", 0), _("high"), [{"label": a["title"], "sub": _(a.get("category") or ""), "value": "",
			**({"open": [a["doctype"], a["name"]]} if a.get("doctype") and a.get("name") else {})} for a in al if a.get("severity") == "High"] or
			[{"label": a["title"], "sub": _(a.get("category") or ""), "value": "", **({"open": [a["doctype"], a["name"]]} if a.get("doctype") and a.get("name") else {})} for a in al]),
	]


def b_journey():
	cos, start, end, label, cur = _scope()
	pos = _rows("Purchase Order", _co("Purchase Order", cos, {"docstatus": 1, "transaction_date": [">=", add_months(today(), -6)]}), ["name", "status", "per_received", "per_billed", "base_grand_total", "supplier_name"], 300)
	shp = _rows("Import Shipment", _co("Import Shipment", cos, {"docstatus": ["<", 2]}), ["name", "status"], 300)
	out = []
	if pos:
		out.append(lambda: W_stages(_("From order to stock"), _("Purchase orders · last 6 months"), [
			S(_("Ordered"), len([p for p in pos if flt(p.per_received) == 0]), "d"),
			S(_("In transit"), len([s for s in shp if s.status in ("Shipped", "In Transit")]), "n"),
			S(_("At port"), len([s for s in shp if s.status in ("Arrived at Port", "Under Customs Clearance")]), "y"),
			S(_("Received"), len([p for p in pos if flt(p.per_received) >= 100]), "g"),
			S(_("Billed"), len([p for p in pos if flt(p.per_billed) >= 100]), ""),
		]))
		out.append(lambda: W_bars(_("Ordered by supplier"), _("Last 6 months · {0}").format(cur), _bars_rows(_sum_by(pos, "supplier_name", "base_grand_total")), True, cur, icon="building"))
	return out


def b_landed():
	from hipersign_trading.api.landed import shipments

	cos = scope_companies()
	shp = [s for s in shipments() if not cos or s.get("company") in cos][:10]
	if not shp:
		return []
	tot = {k: sum(s[k] for s in shp) for k in ("freight", "insurance", "duty", "clearing", "handling", "other")}
	names = {"freight": _("Freight"), "insurance": _("Insurance"), "duty": _("Customs duty"), "clearing": _("Clearing"), "handling": _("Handling"), "other": _("Other")}
	goods = sum(s["goods"] for s in shp)
	ch = sum(tot.values())
	cur = _scope()[4]
	return [
		lambda: W_donut(_("Where landing costs go"), _("Last {0} shipments").format(len(shp)), [{"label": names[k], "value": round(v)} for k, v in tot.items()], _k(ch), cur, True, cur, icon="ship"),
		lambda: W_bars(_("Cost uplift per shipment"), _("Charges as % of goods value"), [{"label": s["name"], "value": s["uplift"], "color": "violet", "open": ["Import Shipment", s["name"]]} for s in shp[:6]], icon="percent"),
		lambda: W_gauge(_("Average uplift"), _("Charges ÷ goods value"), (ch / goods) if goods else 0, f"{round(ch / goods * 100, 1) if goods else 0}%", _("on {0} goods").format(_k(goods, cur)), color="amber", icon="scale"),
	]


def b_tests():
	from hipersign_trading.api.centre import get_tests

	ts = get_tests()
	c = _cnt(ts, "result")
	n = len(ts) or 1
	by_mod = {}
	for t in ts:
		m = t.get("section") or _("Other")
		by_mod.setdefault(m, [0, 0])
		by_mod[m][1] += 1
		if t["result"] == "Pass":
			by_mod[m][0] += 1
	return [
		lambda: W_donut(_("Test results"), _("{0} scripts").format(len(ts)), [{"label": _("Pass"), "value": c.get("Pass", 0), "color": "green"}, {"label": _("Fail"), "value": c.get("Fail", 0), "color": "red"},
			{"label": _("Blocked"), "value": c.get("Blocked", 0), "color": "amber"}, {"label": _("Not run"), "value": c.get("Not run", 0), "color": "grey"}], len(ts), _("scripts"), icon="check-square"),
		lambda: W_gauge(_("Pass rate"), _("Of all scripts"), c.get("Pass", 0) / n, _pc(c.get("Pass", 0) / n), _("{0} passed").format(c.get("Pass", 0)), color="green", icon="check"),
		lambda: W_bars(_("Passed by area"), _("Scripts passed"), [{"label": str(k), "value": v[0], "color": "green"} for k, v in sorted(by_mod.items(), key=lambda x: -x[1][1])[:6]], icon="list"),
	]


def b_addons():
	from hipersign_trading.features import FEATURES, feature_on

	keys = list(FEATURES.keys()) if isinstance(FEATURES, dict) else [f[0] if isinstance(f, (list, tuple)) else f.get("key") for f in FEATURES]
	on = [k for k in keys if feature_on(k)]
	n = len(keys) or 1
	return [
		lambda: W_gauge(_("Switched on"), _("Features in use"), len(on) / n, f"{len(on)} / {len(keys)}", _("features on"), color="blue", icon="toggle-right"),
		lambda: W_donut(_("Features"), _("On and off"), [{"label": _("On"), "value": len(on), "color": "blue"}, {"label": _("Off"), "value": len(keys) - len(on), "color": "grey"}], len(keys), _("features"), icon="layers"),
	]


def b_menu():
	logs = _rows("Hipersign Menu Log", {}, ["creation", "owner"], 500) if _exists("Hipersign Menu Log") else []
	out = []
	if logs:
		def per_month():
			lb, d = _monthly(logs, "creation")
			return W_trend(_("Menu changes"), _("Saved per month"), lb, [{"name": _("Changes"), "data": d, "color": "violet"}])
		out.append(per_month)
		out.append(lambda: W_bars(_("Changed by"), _("Saved changes"), _bars_rows(_cnt(logs, lambda r: frappe.utils.get_fullname(r.owner))), icon="users"))
	def groups():
		from hipersign_trading.navigation import nav_groups

		g = nav_groups()
		return W_bars(_("Menu items per group"), _("Switched on for this site"), [{"label": _(x["label"]), "value": len(x["items"]), "color": "blue"} for x in g if x["items"]][:8], icon="menu")
	out.append(groups)
	ov = _rows("Hipersign Menu Override", {}, ["scope", "visibility"], 2000) if _exists("Hipersign Menu Override") else []
	if ov:
		out.append(lambda: W_donut(_("Menu changes saved"), _("By scope"), [{"label": _(k), "value": v} for k, v in _cnt(ov, "scope").items()], len(ov), _("changes"), icon="sliders"))
	else:
		out.append(lambda: W_gauge(_("Custom menus"), _("Site, company and role menus"), 0, "0", _("changes saved — every menu is the standard one"), icon="menu"))
	return out


def b_portal():
	cos, start, end, label, cur = _scope()
	si = _rows("Sales Invoice", _co("Sales Invoice", cos, {"docstatus": 1, "outstanding_amount": [">", 0]}), ["customer_name", "outstanding_amount", "conversion_rate", "due_date"], 1000)
	so = _rows("Sales Order", _co("Sales Order", cos, {"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver", "To Bill"]]}), ["customer_name", "status"], 1000)
	out = []
	if si:
		out.append(lambda: W_bars(_("What customers owe"), _("Visible to them in the portal · {0}").format(cur), _bars_rows(_sum_by(si, "customer_name", lambda r: flt(r.outstanding_amount) * (flt(r.conversion_rate) or 1))), True, cur, icon="share"))
	if so:
		out.append(lambda: W_donut(_("Open orders customers can track"), _("By status"), [{"label": _(k), "value": v} for k, v in _cnt(so, "status").items()], len(so), _("orders"), icon="list"))
	return out


# ---------------------------------------------------------------- Sales
def b_sales():
	cos, start, end, label, cur = _scope()
	sos = _rows("Sales Order", _co("Sales Order", cos, {"docstatus": ["<", 2], "transaction_date": [">=", add_months(today(), -6)]}), ["name", "status", "docstatus", "workflow_state", "transaction_date", "base_grand_total"], 2000)
	qts = _rows("Quotation", _co("Quotation", cos, {"docstatus": 1, "transaction_date": [">=", add_days(today(), -90)]}), ["status"], 2000)
	out = []
	if sos or qts:
		st = _cnt([s for s in sos if s.docstatus == 1], "status")
		out.append(lambda: W_stages(_("From quotation to completed order"), _("Count by status"), [
			S(_("Quotes open"), len([q for q in qts if q.status in ("Open", "Replied", "Partially Ordered")]), "", tab="quotes", chip="open"),
			S(_("Waiting approval"), len([s for s in sos if s.docstatus == 0]), "d", tab="orders", chip="approval"),
			S(_("To deliver"), st.get("To Deliver and Bill", 0) + st.get("To Deliver", 0), "y", tab="orders", chip="deliver"),
			S(_("To bill"), st.get("To Bill", 0), "n", tab="orders", chip="bill"),
			S(_("Completed"), st.get("Completed", 0), "g", tab="orders", chip="completed"),
		]))
	if sos:
		def booked():
			lb, d = _monthly([s for s in sos if s.docstatus == 1], "transaction_date", lambda r: r.base_grand_total)
			return W_trend(_("Orders booked"), _("Approved sales orders · {0}").format(cur), lb, [{"name": _("Orders"), "data": d, "color": "blue"}], True, cur, icon="chart-column")
		out.append(booked)
	if qts:
		won = len([q for q in qts if q.status == "Ordered"])
		lost = len([q for q in qts if q.status in ("Lost", "Expired")])
		pct = won / (won + lost) if won + lost else 0
		out.append(lambda: W_gauge(_("Quotation win rate"), _("Decided quotations · 90 days"), pct, _pc(pct), _("{0} won of {1}").format(won, won + lost), color="blue", icon="tag"))
	return out


def b_crm():
	from hipersign_trading.api.crm import STAGES

	cos, start, end, label, cur = _scope()
	src = "utm_source" if frappe.get_meta("Lead").has_field("utm_source") else "source"
	leads = _rows("Lead", {}, ["name", "company_name", "lead_name", "lead_owner", f"{src} as source", "hs_pipeline_stage as stage", "hs_estimated_value as value",
		"hs_next_follow_up as follow", "hs_interested_in as interest"], 500, "modified desc")
	if not leads:
		return []
	t = getdate(today())
	stg = list(STAGES) + ["Won", "Lost"]
	tones = {"Won": "g", "Lost": "x", "Proposal": "n", "Negotiation": "y"}
	opn = [l for l in leads if (l.get("stage") or "New") in STAGES]
	due = sorted([l for l in opn if l.get("follow") and getdate(l.follow) <= t], key=lambda l: getdate(l.follow))
	won = len([l for l in leads if l.get("stage") == "Won"])
	lost = len([l for l in leads if l.get("stage") == "Lost"])
	return [
		lambda: W_stages(_("Pipeline by stage"), _("Leads · {0} value").format(cur), [S(_(s), len([l for l in leads if (l.get("stage") or "New") == s]), tones.get(s, ""),
			_k(sum(flt(l.get("value")) for l in leads if (l.get("stage") or "New") == s)), tab="pipeline") for s in stg], icon="git-merge"),
		lambda: W_bars(_("Where leads come from"), _("{0} leads · pipeline {1}").format(len(opn), cur), _bars_rows(_sum_by(opn, lambda l: _(l.get("source") or "Other"), "value"), 7, "violet"), True, cur, icon="sparkles"),
		lambda: W_dark(_("Follow up today"), _("Win rate {0}").format(_pc(won / (won + lost)) if won + lost else "—"), len(due), _("due · {0} open").format(_k(sum(flt(l.get("value")) for l in opn), cur)),
			[{"label": l.get("company_name") or l.get("lead_name") or l.name, "sub": " · ".join(x for x in [l.get("interest"), frappe.utils.get_fullname(l.lead_owner) if l.get("lead_owner") else ""] if x)[:80],
				"value": _k(l.get("value"), cur) if flt(l.get("value")) else "", "open": ["Lead", l.name]} for l in due], _("No follow-ups due"), icon="users"),
	]


def b_so_tracker():
	cos, start, end, label, cur = _scope()
	sos = _rows("Sales Order", _co("Sales Order", cos, {"docstatus": 1, "status": ["not in", ["Closed", "Cancelled"]], "transaction_date": [">=", add_months(today(), -6)]}),
		["name", "customer_name", "status", "delivery_date", "per_delivered", "base_grand_total"], 1000)
	if not sos:
		return []
	t = getdate(today())
	late = [s for s in sos if s.delivery_date and getdate(s.delivery_date) < t and s.status in ("To Deliver and Bill", "To Deliver")]
	pct = 1 - (len(late) / len(sos))
	return [
		lambda: W_donut(_("Orders by status"), _("{0} approved orders").format(len(sos)), [{"label": _(k), "value": v, "color": "green" if k == "Completed" else "violet" if k == "To Bill" else "amber" if "Deliver" in k else "blue"}
			for k, v in _cnt(sos, "status").items()], len(sos), _("orders"), icon="list"),
		lambda: W_gauge(_("On time"), _("Not past the delivery date"), pct, _pc(pct), _("{0} running late").format(len(late)), color="green" if pct > 0.8 else "amber", icon="truck"),
		lambda: W_dark(_("Running late"), _("Past the delivery date"), len(late), _("orders"), [{"label": f"{s.name} · {s.customer_name}", "sub": _("Due {0} · {1}% delivered").format(_fd(s.delivery_date), round(flt(s.per_delivered))),
			"value": "", "open": ["Sales Order", s.name]} for s in sorted(late, key=lambda s: getdate(s.delivery_date))], _("Nothing running late"), icon="clock"),
	]


def b_exports():
	cos, start, end, label, cur = _scope()
	ex = _rows("Export Shipment", _co("Export Shipment", cos, {"docstatus": ["<", 2]}), ["name", "status", "customer_name", "destination", "net_sales", "gross_profit", "proof_due_on", "proof_of_export_on", "etd"], 500)
	if not ex:
		return []
	steps = ["Booked", "Packed", "Export Declaration", "Customs Cleared", "Shipped", "Delivered", "Documents Complete"]
	short = {"Export Declaration": _("Declared"), "Customs Cleared": _("Cleared"), "Documents Complete": _("Docs done")}
	tone = {"Shipped": "n", "Customs Cleared": "y", "Documents Complete": "g"}
	t = getdate(today())
	proof = [e for e in ex if e.proof_due_on and not e.proof_of_export_on]
	return [
		lambda: W_stages(_("Export shipments"), _("{0} shipments").format(len(ex)), [S(short.get(s, _(s)), len([e for e in ex if e.status == s]), tone.get(s, "")) for s in steps], icon="globe"),
		lambda: W_bars(_("Sales by destination"), _("Net sales · {0}").format(cur), _bars_rows(_sum_by(ex, "destination", "net_sales"), 6, "teal"), True, cur, icon="map-pin"),
		lambda: W_dark(_("Proof of export due"), _("Needed for zero-rated VAT"), len(proof), _("shipments"), [{"label": f"{e.name} · {e.customer_name or ''}", "sub": _("Due {0}").format(_fd(e.proof_due_on)) + (" · " + _("late") if getdate(e.proof_due_on) < t else ""),
			"value": "", "open": ["Export Shipment", e.name]} for e in sorted(proof, key=lambda e: getdate(e.proof_due_on))], _("All proofs on file"), icon="file"),
	]


# ---------------------------------------------------------------- Purchasing
def b_purchasing():
	cos, start, end, label, cur = _scope()
	pos = _rows("Purchase Order", _co("Purchase Order", cos, {"docstatus": ["<", 2], "transaction_date": [">=", add_months(today(), -6)]}),
		["name", "status", "docstatus", "supplier_name", "currency", "base_grand_total", "per_received", "schedule_date", "transaction_date"], 2000)
	mr = _rows("Material Request", _co("Material Request", cos, {"docstatus": ["<", 2], "material_request_type": "Purchase", "status": ["not in", ["Ordered", "Stopped", "Cancelled"]]}), ["name"], 500)
	if not pos:
		return []
	sub = [p for p in pos if p.docstatus == 1]
	st = _cnt(sub, "status")
	t = getdate(today())
	late = [p for p in sub if p.status in OPEN_PO and p.schedule_date and getdate(p.schedule_date) < t and flt(p.per_received) < 100]
	return [
		lambda: W_stages(_("From request to received"), _("Count by status"), [S(_("Requests"), len(mr), "d"), S(_("Waiting approval"), len([p for p in pos if p.docstatus == 0]), "d"),
			S(_("To receive"), st.get("To Receive and Bill", 0) + st.get("To Receive", 0), "y"), S(_("To bill"), st.get("To Bill", 0), "n"), S(_("Completed"), st.get("Completed", 0), "g")], icon="shopping-cart"),
		lambda: W_donut(_("Spend by currency"), _("Last 6 months · in {0}").format(cur), [{"label": k, "value": round(v)} for k, v in _top(_sum_by(sub, "currency", "base_grand_total"), 6)],
			_k(sum(flt(p.base_grand_total) for p in sub)), cur, True, cur, icon="coins"),
		lambda: W_dark(_("Late from suppliers"), _("Past the required date"), len(late), _("orders"), [{"label": f"{p.name} · {p.supplier_name}", "sub": _("Required {0} · {1}% received").format(_fd(p.schedule_date), round(flt(p.per_received))),
			"value": _k(p.base_grand_total, cur), "open": ["Purchase Order", p.name]} for p in sorted(late, key=lambda p: getdate(p.schedule_date))], _("No late orders"), icon="clock"),
	]


def b_imports():
	cos, start, end, label, cur = _scope()
	sh = _rows("Import Shipment", _co("Import Shipment", cos, {"docstatus": ["<", 2]}), ["name", "status", "port_of_loading", "port_of_discharge", "eta", "total_charges", "goods_value", "vessel_flight", "creation"], 500, "creation desc")
	if not sh:
		return []
	steps = ["Booked", "Shipped", "In Transit", "Arrived at Port", "Under Customs Clearance", "Cleared", "Received at Warehouse"]
	short = {"Arrived at Port": _("At port"), "Under Customs Clearance": _("Customs"), "Received at Warehouse": _("In stock")}
	tone = {"In Transit": "n", "Arrived at Port": "y", "Under Customs Clearance": "y", "Received at Warehouse": "g"}
	port = [s for s in sh if s.status in ("Arrived at Port", "Under Customs Clearance", "Cleared")]
	return [
		lambda: W_stages(_("Where the containers are"), _("{0} shipments").format(len(sh)), [S(short.get(s, _(s)), len([x for x in sh if x.status == s]), tone.get(s, "")) for s in steps], icon="ship"),
		lambda: W_bars(_("Landing charges per shipment"), _("Freight, duty and clearing · {0}").format(cur), [{"label": s.name, "value": flt(s.total_charges), "color": "blue", "open": ["Import Shipment", s.name]}
			for s in sh[:6] if flt(s.total_charges)], True, cur, icon="receipt"),
		lambda: W_dark(_("At port or customs"), _("Demurrage risk"), len([s for s in port if s.status != "Cleared"]), _("containers"), [{"label": f"{s.name} · {s.port_of_loading or ''}", "sub": " · ".join(x for x in [s.vessel_flight, _("ETA {0}").format(_fd(s.eta)) if s.eta else ""] if x),
			"value": _(short.get(s.status, s.status)), "open": ["Import Shipment", s.name]} for s in port], _("Nothing at port"), icon="anchor"),
	]


def b_receiving():
	cos, start, end, label, cur = _scope()
	pr = _rows("Purchase Receipt", _co("Purchase Receipt", cos, {"docstatus": ["<", 2], "posting_date": [">=", add_months(today(), -6)]}), ["name", "docstatus", "posting_date", "supplier_name", "base_grand_total", "status"], 1000)
	pos = _rows("Purchase Order", _co("Purchase Order", cos, {"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]]}), ["name", "supplier_name", "schedule_date", "per_received"], 500)
	out = []
	if pr:
		def tr():
			lb, d = _monthly([p for p in pr if p.docstatus == 1], "posting_date")
			return W_trend(_("Receipts per month"), _("Goods received notes"), lb, [{"name": _("Receipts"), "data": d, "color": "green"}], icon="package")
		out.append(tr)
		out.append(lambda: W_bars(_("Received by supplier"), _("Last 6 months · {0}").format(cur), _bars_rows(_sum_by([p for p in pr if p.docstatus == 1], "supplier_name", "base_grand_total")), True, cur, icon="building"))
	if pos:
		out.append(lambda: W_dark(_("Expected next"), _("Orders still to receive"), len(pos), _("orders"), [{"label": f"{p.name} · {p.supplier_name}", "sub": _("Required {0} · {1}% received").format(_fd(p.schedule_date), round(flt(p.per_received))),
			"value": "", "open": ["Purchase Order", p.name]} for p in sorted(pos, key=lambda p: getdate(p.schedule_date or "2999-12-31"))], icon="truck"))
	return out


def b_lc():
	cos, start, end, label, cur = _scope()
	lcs = _rows("Letter of Credit", _co("Letter of Credit", cos, {"docstatus": ["<", 2]}), ["name", "status", "base_amount", "issuing_bank", "expiry_date", "party_name", "lc_type"], 500)
	bgs = _rows("Bank Guarantee", _co("Bank Guarantee", cos, {"docstatus": 1}), ["name", "amount", "bank", "end_date"], 500)
	out = []
	t = getdate(today())
	if lcs:
		steps = ["Applied", "Issued", "Documents Presented", "Accepted", "Paid"]
		out.append(lambda: W_stages(_("Letters of credit"), _("{0} LCs").format(len(lcs)), [S({"Documents Presented": _("Docs presented")}.get(s, _(s)), len([l for l in lcs if l.status == s]),
			{"Issued": "n", "Documents Presented": "y", "Paid": "g"}.get(s, "")) for s in steps], icon="landmark"))
		out.append(lambda: W_bars(_("Exposure by bank"), _("Open LCs · {0}").format(cur), _bars_rows(_sum_by([l for l in lcs if l.status not in ("Paid", "Expired", "Cancelled")], "issuing_bank", "base_amount"), 6, "violet"), True, cur, icon="building"))
	exp = sorted([("Letter of Credit", l.name, l.party_name, l.expiry_date) for l in lcs if l.expiry_date and l.status not in ("Paid", "Expired", "Cancelled") and getdate(l.expiry_date) <= add_days(t, 60)]
		+ [("Bank Guarantee", b.name, b.bank, b.end_date) for b in bgs if b.end_date and t <= getdate(b.end_date) <= add_days(t, 60)], key=lambda x: getdate(x[3]))
	if lcs or bgs:
		out.append(lambda: W_dark(_("Expiring in 60 days"), _("LCs and guarantees"), len(exp), _("to act on"), [{"label": f"{n} · {p or ''}", "sub": _("{0} · expires {1}").format(_(dt), _fd(d)), "value": "", "open": [dt, n]} for dt, n, p, d in exp], _("Nothing expiring"), icon="clock"))
	return out


# ---------------------------------------------------------------- Inventory & delivery
def b_stock():
	cos, start, end, label, cur = _scope()
	whs = [w.name for w in frappe.get_all("Warehouse", filters={"company": ["in", cos], "is_group": 0}, fields=["name"])] if cos else []
	bins = _rows("Bin", {"warehouse": ["in", whs or [""]]}, ["item_code", "warehouse", "actual_qty", "stock_value", "projected_qty", "reserved_qty", "reserved_stock"], 5000)
	if not bins:
		return []
	by_wh = _sum_by(bins, "warehouse", "stock_value")
	per = {}
	for b in bins:
		per.setdefault(b.item_code, [0, 0])
		per[b.item_code][0] += flt(b.actual_qty)
		per[b.item_code][1] += flt(b.get("reserved_stock")) or flt(b.get("reserved_qty"))  # v1.8.4 (#36): reserved, as on the page
	reorder = {r.parent: flt(r.warehouse_reorder_level) for r in frappe.get_all("Item Reorder", fields=["parent", "warehouse_reorder_level"], limit=5000)}
	neg = [c for c, (q, rs) in per.items() if q > 0 and rs > q]
	low = [c for c, (q, rs) in per.items() if q > 0 and c not in neg and reorder.get(c) and q - rs <= reorder[c]]
	out_ = [c for c, (q, rs) in per.items() if q <= 0]
	ok = len(per) - len(low) - len(out_) - len(neg)
	names = {i.name: i.item_name for i in frappe.get_all("Item", filters={"name": ["in", (neg + low)[:6] or [""]]}, fields=["name", "item_name"])}
	return [
		lambda: W_donut(_("Stock health"), _("{0} items").format(len(per)), [{"label": _("In stock"), "value": ok, "color": "green"}, {"label": _("Low"), "value": len(low), "color": "amber"},
			{"label": _("Short"), "value": len(neg), "color": "red"}, {"label": _("Out of stock"), "value": len(out_), "color": "grey"}], len(per), _("items"), icon="package"),
		lambda: W_bars(_("Stock value by warehouse"), cur, _bars_rows(by_wh, 6, "blue"), True, cur, icon="warehouse"),
		lambda: W_dark(_("Short against orders"), _("Ordered more than in stock"), len(neg), _("items"), [{"label": names.get(c, c), "sub": _("On hand {0} · reserved {1}").format(round(per[c][0]), round(per[c][1])), "value": _("Short {0}").format(round(per[c][1] - per[c][0])),
			"open": ["Item", c]} for c in neg] or [{"label": names.get(c, c), "sub": _("Low stock · {0} on hand").format(round(per[c][0])), "value": "", "open": ["Item", c]} for c in low], _("Nothing short"), icon="triangle-alert"),
	]


def b_dispatch():
	cos, start, end, label, cur = _scope()
	dns = _rows("Delivery Note", _co("Delivery Note", cos, {"docstatus": 1, "posting_date": [">=", add_months(today(), -6)]}), ["name", "customer_name", "posting_date", "hs_delivery_status", "base_grand_total", "is_return"], 2000)
	so = _rows("Sales Order", _co("Sales Order", cos, {"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]]}), ["name"], 1000)
	picks = _rows("Pick List", _co("Pick List", cos, {"docstatus": ["<", 2], "status": ["not in", ["Completed", "Cancelled"]]}), ["name"], 500)
	if not (dns or so):
		return []
	dns = [d for d in dns if not d.get("is_return")]
	st = lambda s: len([d for d in dns if (d.get("hs_delivery_status") or "Ready to Dispatch") == s])
	out = [lambda: W_stages(_("Dispatch board"), _("Orders and delivery notes"), [S(_("To deliver"), len(so), "d"), S(_("Picking"), len(picks), ""), S(_("Ready"), st("Ready to Dispatch"), "y"),
		S(_("Out"), st("Out for Delivery"), "n"), S(_("Delivered"), st("Delivered"), "g"), S(_("Failed"), st("Failed"), "x")], icon="truck")]
	if dns:
		def tr():
			lb, d = _monthly(dns, "posting_date")
			return W_trend(_("Deliveries per month"), _("Delivery notes"), lb, [{"name": _("Deliveries"), "data": d, "color": "teal"}], icon="truck")
		out.append(tr)
		out.append(lambda: W_bars(_("Delivered to"), _("Last 6 months · {0}").format(cur), _bars_rows(_sum_by(dns, "customer_name", "base_grand_total"), 6, "violet"), True, cur, icon="users"))
	return out


# ---------------------------------------------------------------- Finance
def _ar(cos):
	return _rows("Sales Invoice", _co("Sales Invoice", cos, {"docstatus": 1, "outstanding_amount": [">", 0]}), ["name", "customer_name", "outstanding_amount", "conversion_rate", "due_date"], 2000)


def b_finance():
	cos, start, end, label, cur = _scope()
	ar = _ar(cos)
	ap = _rows("Purchase Invoice", _co("Purchase Invoice", cos, {"docstatus": 1, "outstanding_amount": [">", 0]}), ["outstanding_amount", "conversion_rate"], 2000)
	pe = _rows("Payment Entry", _co("Payment Entry", cos, {"docstatus": 1, "posting_date": [">=", _months()[0][0]]}), ["posting_date", "payment_type", "base_received_amount", "base_paid_amount"], 3000)
	out = []
	t = getdate(today())
	base = lambda r: flt(r.outstanding_amount) * (flt(r.conversion_rate) or 1)
	if ar:
		buckets = [(_("Not due"), None, 0), (_("1–30"), 1, 30), (_("31–60"), 31, 60), (_("61–90"), 61, 90), (_("90+"), 91, 99999)]
		rows = []
		for lab, a, b in buckets:
			v = sum(base(r) for r in ar if (date_diff(t, r.due_date) if r.due_date else 0) <= 0) if a is None else sum(base(r) for r in ar if r.due_date and a <= date_diff(t, r.due_date) <= b)
			rows.append({"label": lab, "value": round(v), "color": "green" if a is None else "amber" if b <= 60 else "red"})
		out.append(lambda: W_bars(_("Receivables ageing"), _("Days past due · {0}").format(cur), rows, True, cur, icon="clock"))
	if pe:
		def cash():
			lb, inn = _monthly([p for p in pe if p.payment_type == "Receive"], "posting_date", lambda r: r.base_received_amount)
			_l, outg = _monthly([p for p in pe if p.payment_type == "Pay"], "posting_date", lambda r: r.base_paid_amount)
			return W_trend(_("Cash in and out"), _("Payments · last 6 months"), lb, [{"name": _("Received"), "data": inn, "color": "green"}, {"name": _("Paid"), "data": outg, "color": "red"}], True, cur, icon="wallet")
		out.append(cash)
	if ar or ap:
		recv, pay = sum(base(r) for r in ar), sum(base(r) for r in ap)
		over = sorted([r for r in ar if r.due_date and getdate(r.due_date) < t], key=lambda r: -base(r))
		out.append(lambda: W_dark(_("Customers owe"), _("{0} overdue").format(_k(sum(base(r) for r in over), cur)), _k(recv, cur), _("· we owe {0}").format(_k(pay, cur)),
			[{"label": f"{r.customer_name} · {r.name}", "sub": _("Due {0}").format(_fd(r.due_date)), "value": _k(base(r)), "open": ["Sales Invoice", r.name]} for r in over], _("Nothing overdue"), icon="banknote"))
	return out


def b_accounts():
	cos, start, end, label, cur = _scope()
	ms = _months()
	si = _rows("Sales Invoice", _co("Sales Invoice", cos, {"docstatus": 1, "posting_date": [">=", ms[0][0]]}), ["posting_date", "base_net_total"], 3000)
	pi = _rows("Purchase Invoice", _co("Purchase Invoice", cos, {"docstatus": 1, "posting_date": [">=", ms[0][0]]}), ["posting_date", "base_net_total"], 3000)
	je = _rows("Journal Entry", _co("Journal Entry", cos, {"docstatus": ["<", 2], "posting_date": [">=", ms[0][0]]}), ["posting_date", "voucher_type", "docstatus"], 3000)
	out = []
	if si or pi:
		def pl():
			lb, s = _monthly(si, "posting_date", lambda r: r.base_net_total)
			_l, p = _monthly(pi, "posting_date", lambda r: r.base_net_total)
			return W_trend(_("Income and purchases"), _("Net · last 6 months · {0}").format(cur), lb, [{"name": _("Income"), "data": s, "color": "blue"}, {"name": _("Purchases & expenses"), "data": p, "color": "violet"}], True, cur, icon="book-open")
		out.append(pl)
		tot_s, tot_p = sum(flt(r.base_net_total) for r in si), sum(flt(r.base_net_total) for r in pi)
		m = (tot_s - tot_p) / tot_s if tot_s else 0
		out.append(lambda: W_gauge(_("Margin after purchases"), _("Last 6 months"), m, _pc(m), _("{0} income").format(_k(tot_s, cur)), color="green" if m > 0.2 else "amber", icon="percent"))
	if je:
		out.append(lambda: W_donut(_("Journal entries"), _("By type · 6 months"), [{"label": _(k), "value": v} for k, v in _top(_cnt(je, "voucher_type"), 6)], len(je), _("entries"), icon="book"))
	return out


def b_vat():
	cos, start, end, label, cur = _scope()
	tr = _rows("Tax Return", _co("Tax Return", cos, {"tax_type": "VAT 201"}), ["name", "status", "period_to", "output_vat", "input_vat", "net_vat", "due_date"], 50, "period_to desc")
	si = _rows("Sales Invoice", _co("Sales Invoice", cos, {"docstatus": 1, "posting_date": [">=", _months()[0][0]]}), ["posting_date", "base_total_taxes_and_charges"], 3000)
	pi = _rows("Purchase Invoice", _co("Purchase Invoice", cos, {"docstatus": 1, "posting_date": [">=", _months()[0][0]]}), ["posting_date", "base_total_taxes_and_charges"], 3000)
	out = []
	if si or pi:
		def tr_():
			lb, o = _monthly(si, "posting_date", lambda r: r.base_total_taxes_and_charges)
			_l, i = _monthly(pi, "posting_date", lambda r: r.base_total_taxes_and_charges)
			return W_trend(_("Output and input VAT"), _("By month · {0}").format(cur), lb, [{"name": _("Output VAT"), "data": o, "color": "blue"}, {"name": _("Input VAT"), "data": i, "color": "green"}], True, cur, icon="receipt")
		out.append(tr_)
	if tr:
		rs = list(reversed(tr[:6]))
		out.append(lambda: W_bars(_("Net VAT per return"), _("Payable · {0}").format(cur), [{"label": _fd(r.period_to), "value": flt(r.net_vat), "color": "violet", "open": ["Tax Return", r.name]} for r in rs], True, cur, icon="file-text"))
		nxt = [r for r in tr if r.status not in ("Submitted", "Paid")]
		out.append(lambda: W_dark(_("Returns to file"), _("Not yet submitted"), len(nxt), _("returns"), [{"label": r.name, "sub": _("{0} · due {1}").format(_(r.status), _fd(r.due_date)), "value": _k(r.net_vat, cur), "open": ["Tax Return", r.name]} for r in nxt], _("All filed"), icon="calendar"))
	return out


def b_tax():
	cos, start, end, label, cur = _scope()
	tr = _rows("Tax Return", _co("Tax Return", cos, {"tax_type": "Corporate Tax"}), ["name", "status", "period_to", "accounting_profit", "taxable_income", "tax_payable", "company"], 50, "period_to desc")
	si = _rows("Sales Invoice", _co("Sales Invoice", cos, {"docstatus": 1, "posting_date": [">=", getdate(today()).replace(month=1, day=1)]}), ["base_net_total", "company"], 5000)
	out = []
	if si:
		out.append(lambda: W_bars(_("Revenue this year by company"), _("Net sales · {0}").format(cur), _bars_rows(_sum_by(si, "company", "base_net_total"), 6, "blue"), True, cur, icon="building"))
		rev = sum(flt(r.base_net_total) for r in si)
		lim = 3000000
		out.append(lambda: W_gauge(_("Small business relief"), _("Revenue against AED 3M"), rev / lim, _pc(rev / lim), _("{0} so far this year").format(_k(rev, cur)), color="green" if rev < lim else "red", icon="scale"))
	if tr:
		out.append(lambda: W_dark(_("Corporate tax returns"), _("Latest first"), len(tr), _("returns"), [{"label": r.name, "sub": _("{0} · period to {1}").format(_(r.status), _fd(r.period_to)), "value": _k(r.tax_payable, cur), "open": ["Tax Return", r.name]} for r in tr], icon="landmark"))
	return out


def b_group():
	cos, start, end, label, cur = _scope()
	ms = _months()
	si = _rows("Sales Invoice", {"docstatus": 1, "posting_date": [">=", ms[0][0]], "company": ["in", cos]}, ["company", "posting_date", "base_net_total"], 5000)
	comps = frappe.get_all("Company", filters={"name": ["in", cos]}, fields=["name", "country", "default_currency"])
	out = []
	if si:
		by = _sum_by(si, "company", "base_net_total")
		out.append(lambda: W_bars(_("Sales by company"), _("Last 6 months · each in its own currency"), _bars_rows(by, 8, "blue"), icon="building"))
		top = [k for k, _v in _top(by, 6)]
		out.append(lambda: W_heat(_("Sales by month"), _("Company × month"), top, [m[2] for m in ms], [[round(x) for x in _monthly([r for r in si if r.company == c], "posting_date", lambda r: r.base_net_total)[1]] for c in top], icon="calendar"))
	if comps:
		out.append(lambda: W_donut(_("Companies by country"), _("{0} companies").format(len(comps)), [{"label": _(k), "value": v} for k, v in _cnt(comps, "country").items()], len(comps), _("companies"), icon="globe"))
	return out


def b_kyc():
	out = []
	t = getdate(today())
	cs = _rows("Customer", {"disabled": 0}, ["name", "customer_name", "hs_kyc_status", "hs_trade_licence_expiry"], 2000)
	ss = _rows("Supplier", {"disabled": 0}, ["name", "supplier_name", "hs_kyc_status", "hs_trade_licence_expiry"], 2000)
	allp = [("Customer", c.name, c.customer_name, c) for c in cs] + [("Supplier", s.name, s.supplier_name, s) for s in ss]
	if not allp:
		return []
	st = _cnt([p[3] for p in allp], lambda r: r.get("hs_kyc_status") or "Pending")
	exp = sorted([p for p in allp if p[3].get("hs_trade_licence_expiry") and getdate(p[3].hs_trade_licence_expiry) <= add_days(t, 30)], key=lambda p: getdate(p[3].hs_trade_licence_expiry))
	ver = st.get("Verified", 0)
	out.append(lambda: W_donut(_("KYC status"), _("Customers and suppliers"), [{"label": _("Verified"), "value": ver, "color": "green"}, {"label": _("Pending"), "value": st.get("Pending", 0), "color": "amber"},
		{"label": _("Expired"), "value": st.get("Expired", 0), "color": "red"}, {"label": _("Blocked"), "value": st.get("Blocked", 0), "color": "navy"}], len(allp), _("parties"), icon="shield"))
	out.append(lambda: W_gauge(_("Verified"), _("Of all active parties"), ver / len(allp), _pc(ver / len(allp)), _("{0} of {1}").format(ver, len(allp)), color="green", icon="check"))
	out.append(lambda: W_dark(_("Licences expiring"), _("Within 30 days or expired"), len(exp), _("parties"), [{"label": n, "sub": _("{0} · licence {1}").format(_(dt), _fd(r.hs_trade_licence_expiry)), "value": "", "open": [dt, name]} for dt, name, n, r in exp], _("No licences expiring"), icon="id-card"))
	return out


def b_codocs():
	cos, start, end, label, cur = _scope()
	docs = _rows("Company Document", _co("Company Document", cos), ["name", "company", "document_type", "status", "expiry_date"], 1000)
	dl = _rows("Company Deadline", _co("Company Deadline", cos, {"status": "Open"}), ["name", "title", "category", "due_date", "company"], 500, "due_date asc")
	out = []
	t = getdate(today())
	if docs:
		out.append(lambda: W_donut(_("Company documents"), _("{0} on file").format(len(docs)), [{"label": _(k), "value": v, "color": {"Valid": "green", "Due for renewal": "amber", "Expired": "red", "No expiry": "grey"}.get(k, "blue")}
			for k, v in _cnt(docs, "status").items()], len(docs), _("documents"), icon="file"))
		out.append(lambda: W_bars(_("Documents by company"), _("On file"), _bars_rows(_cnt(docs, "company"), 6, "violet"), icon="building"))
	if dl:
		out.append(lambda: W_dark(_("Next deadlines"), _("Open"), len([d for d in dl if d.due_date and getdate(d.due_date) <= add_days(t, 30)]), _("in 30 days"), [{"label": d.title or d.name, "sub": f"{_(d.category or '')} · {_fd(d.due_date)}",
			"value": "", "open": ["Company Deadline", d.name]} for d in dl], icon="calendar"))
	return out


def b_hr():
	cos, start, end, label, cur = _scope()
	emp = _rows("Employee", _co("Employee", cos, {"status": "Active"}), ["name", "employee_name", "department", "hs_visa_expiry", "hs_emirates_id_expiry", "hs_labour_card_expiry", "date_of_joining"], 2000)
	out = []
	t = getdate(today())
	if emp:
		out.append(lambda: W_bars(_("People by department"), _("{0} active").format(len(emp)), _bars_rows(_cnt(emp, lambda e: e.get("department") or _("Not set")), 7, "blue"), icon="users"))
		exp = []
		for e in emp:
			for f, lab in (("hs_visa_expiry", _("Visa")), ("hs_emirates_id_expiry", _("Emirates ID")), ("hs_labour_card_expiry", _("Labour card"))):
				if e.get(f) and getdate(e.get(f)) <= add_days(t, 60):
					exp.append((e, lab, e.get(f)))
		exp.sort(key=lambda x: getdate(x[2]))
		out.append(lambda: W_dark(_("Documents expiring"), _("Within 60 days"), len(exp), _("to renew"), [{"label": e.employee_name, "sub": f"{lab} · {_fd(d)}", "value": "", "open": ["Employee", e.name]} for e, lab, d in exp], _("Nothing expiring"), icon="id-card"))
	ss = _rows("Salary Slip", _co("Salary Slip", cos, {"docstatus": 1, "posting_date": [">=", _months()[0][0]]}), ["posting_date", "base_net_pay", "net_pay"], 5000)
	if ss:
		def pay():
			lb, d = _monthly(ss, "posting_date", lambda r: r.get("base_net_pay") or r.get("net_pay"))
			return W_trend(_("Payroll"), _("Net pay · {0}").format(cur), lb, [{"name": _("Net pay"), "data": d, "color": "violet"}], True, cur, icon="wallet")
		out.insert(1, pay)
	else:
		la = _rows("Leave Application", _co("Leave Application", cos, {"docstatus": ["<", 2], "from_date": [">=", _months()[0][0]]}), ["leave_type", "total_leave_days"], 2000)
		if la:
			out.insert(1, lambda: W_donut(_("Leave taken"), _("Days by type · 6 months"), [{"label": _(k), "value": round(v, 1)} for k, v in _top(_sum_by(la, "leave_type", "total_leave_days"), 6)], round(sum(flt(r.total_leave_days) for r in la)), _("days"), icon="calendar"))
	return out


def b_assets():
	cos, start, end, label, cur = _scope()
	a = _rows("Asset", _co("Asset", cos, {"docstatus": 1}), ["name", "asset_name", "asset_category", "status", "gross_purchase_amount", "value_after_depreciation", "hs_registration_expiry"], 2000)
	if not a:
		return []
	g = sum(flt(r.gross_purchase_amount) for r in a)
	nv = sum(flt(r.get("value_after_depreciation") or r.gross_purchase_amount) for r in a)
	t = getdate(today())
	reg = sorted([r for r in a if r.get("hs_registration_expiry") and getdate(r.hs_registration_expiry) <= add_days(t, 60)], key=lambda r: getdate(r.hs_registration_expiry))
	return [
		lambda: W_donut(_("Assets by category"), _("Cost · {0}").format(cur), [{"label": _(k), "value": round(v)} for k, v in _top(_sum_by(a, "asset_category", "gross_purchase_amount"), 6)], _k(g), cur, True, cur, icon="box"),
		lambda: W_gauge(_("Value remaining"), _("Book value ÷ cost"), nv / g if g else 0, _pc(nv / g if g else 0), _("{0} book value").format(_k(nv, cur)), color="blue", icon="trending-down"),
		(lambda: W_dark(_("Registrations due"), _("Vehicles and equipment · 60 days"), len(reg), _("to renew"), [{"label": r.asset_name, "sub": _fd(r.hs_registration_expiry), "value": "", "open": ["Asset", r.name]} for r in reg], _("Nothing due"), icon="calendar"))
		if any(r.get("hs_registration_expiry") for r in a) else
		(lambda: W_bars(_("Assets by status"), _("Count"), _bars_rows(_cnt(a, "status"), 6, "violet"), icon="list")),
	]


# ---------------------------------------------------------------- Projects
def _projects(cos):
	return _rows("Project", _co("Project", cos, {"status": ["!=", "Cancelled"]}), ["name", "project_name", "status", "percent_complete", "expected_end_date", "estimated_costing",
		"total_costing_amount", "total_billed_amount", "hs_contract_value", "customer"], 500)


def b_pj_home():
	cos, start, end, label, cur = _pscope()
	p = _projects(cos)
	if not p:
		return []
	act = [x for x in p if x.status == "Open"]
	t = getdate(today())
	late = [x for x in act if x.expected_end_date and getdate(x.expected_end_date) < t and flt(x.percent_complete) < 100]
	return [
		lambda: W_stages(_("Projects by status"), _("{0} projects").format(len(p)), [S(_(k), v, {"Completed": "g", "Open": "n"}.get(k, "")) for k, v in _cnt(p, "status").items()], icon="folder"),
		lambda: W_bars(_("Progress"), _("Active projects · % complete"), [{"label": x.project_name or x.name, "value": round(flt(x.percent_complete)), "color": "green", "open": ["Project", x.name]} for x in sorted(act, key=lambda x: -flt(x.percent_complete))[:6]], icon="bar-chart"),
		lambda: W_dark(_("Behind programme"), _("Past the planned end"), len(late), _("projects"), [{"label": x.project_name or x.name, "sub": _("Planned end {0} · {1}% done").format(_fd(x.expected_end_date), round(flt(x.percent_complete))), "value": "", "open": ["Project", x.name]} for x in late], _("All on programme"), icon="clock"),
	]


def b_prj_tracker():
	return b_pj_home()


def b_pj_boq():
	cos, start, end, label, cur = _pscope()
	b = _rows("Project BOQ", _co("Project BOQ", cos), ["name", "title", "status", "tender_value", "margin_pct", "due_date", "client_name"], 500)
	if not b:
		return []
	won = len([x for x in b if x.status == "Awarded"])
	lost = len([x for x in b if (x.status or "").startswith("Lost")])
	t = getdate(today())
	due = sorted([x for x in b if x.status == "Being priced" and x.due_date], key=lambda x: getdate(x.due_date))
	return [
		lambda: W_stages(_("Tenders"), _("{0} BOQs").format(len(b)), [S(_("Pricing"), len([x for x in b if x.status == "Being priced"]), "d"), S(_("Submitted"), len([x for x in b if x.status == "Submitted"]), "y"),
			S(_("Awarded"), won, "g"), S(_("Lost"), lost, "x")], icon="clipboard"),
		lambda: W_gauge(_("Hit rate"), _("Awarded of decided"), won / (won + lost) if won + lost else 0, _pc(won / (won + lost)) if won + lost else "—", _("{0} won of {1}").format(won, won + lost), color="blue", icon="target"),
		lambda: W_dark(_("Tenders due"), _("Being priced"), len(due), _("open"), [{"label": x.title or x.name, "sub": _("Due {0}").format(_fd(x.due_date)) + (" · " + _("late") if getdate(x.due_date) < t else ""), "value": _k(x.tender_value, cur) if flt(x.tender_value) else "", "open": ["Project BOQ", x.name]} for x in due], _("Nothing due"), icon="calendar"),
	]


def b_pj_site():
	cos, start, end, label, cur = _pscope()
	ds = _rows("Daily Site Report", _co("Daily Site Report", cos, {"report_date": [">=", add_days(today(), -13)]}), ["project", "report_date", "manpower_own", "manpower_sub"], 1000)
	mr = _rows("Material Request", _co("Material Request", cos, {"docstatus": ["<", 2], "creation": [">=", add_months(today(), -6)]}), ["name", "status", "schedule_date", "project"], 1000)
	mr = [m for m in mr if m.get("project")]  # v1.8.4: site requests only (a factory's material requests are not site requests), as on the page
	out = []
	if ds:
		days = [add_days(today(), -i) for i in range(13, -1, -1)]
		f = lambda key: [sum(cint(r.get(key)) for r in ds if str(r.report_date) == str(d)) for d in days]
		out.append(lambda: W_trend(_("Manpower on site"), _("Last 14 days"), [_fd(d) for d in days], [{"name": _("Own"), "data": f("manpower_own"), "color": "blue"}, {"name": _("Subcontractors"), "data": f("manpower_sub"), "color": "amber"}], icon="hard-hat"))
	if mr:
		out.append(lambda: W_donut(_("Site material requests"), _("Last 6 months"), [{"label": _(k), "value": v} for k, v in _cnt(mr, "status").items()], len(mr), _("requests"), icon="package"))
		pend = sorted([m for m in mr if m.status in ("Pending", "Draft", "Partially Ordered")], key=lambda m: getdate(m.schedule_date or "2999-12-31"))
		out.append(lambda: W_dark(_("Waiting for material"), _("Not yet ordered"), len(pend), _("requests"), [{"label": f"{m.name} · {m.project or ''}", "sub": _("Needed {0}").format(_fd(m.schedule_date)), "value": "", "open": ["Material Request", m.name]} for m in pend], _("Nothing waiting"), icon="clock"))
	return out


def b_pj_bill():
	cos, start, end, label, cur = _pscope()
	pc = _rows("Progress Certificate", _co("Progress Certificate", cos), ["name", "project", "status", "net_amount", "total_due", "retention", "period_to", "certified_on"], 500, "period_to desc")
	vo = _rows("Variation Order", _co("Variation Order", cos), ["name", "project", "status", "amount", "title"], 500)
	out = []
	if pc:
		out.append(lambda: W_stages(_("Interim payment certificates"), _("{0} IPCs").format(len(pc)), [S(_(s), len([x for x in pc if x.status == s]), {"Certified": "y", "Invoiced": "g", "Submitted to consultant": "n"}.get(s, ""))
			for s in ("Draft", "Submitted to consultant", "Certified", "Invoiced")], icon="file-check"))

		def tr():
			lb, d = _monthly(pc, "period_to", lambda r: r.net_amount)
			return W_trend(_("Certified per month"), _("Net of retention · {0}").format(cur), lb, [{"name": _("Certified"), "data": d, "color": "green"}], True, cur, icon="trending-up")
		out.append(tr)
	if vo:
		out.append(lambda: W_donut(_("Variations"), _("Value by status · {0}").format(cur), [{"label": _(k), "value": round(v), "color": {"Approved": "green", "Pending client": "amber", "Rejected": "red"}.get(k, "grey")}
			for k, v in _sum_by(vo, "status", "amount").items()], len(vo), _("variations"), True, cur, icon="git-pull-request"))
	return out[:3]


def b_pj_sub():
	cos, start, end, label, cur = _pscope()
	so = _rows("Subcontract Order", _co("Subcontract Order", cos, {"status": ["!=", "Cancelled"]}), ["name", "supplier", "package", "order_value", "status", "behind_programme"], 500)
	cl = _rows("Subcontract Claim", _co("Subcontract Claim", cos), ["name", "supplier", "status", "net_amount", "claim_date"], 500)
	out = []
	if so:
		out.append(lambda: W_bars(_("Order value by subcontractor"), cur, _bars_rows(_sum_by(so, "supplier", "order_value"), 6, "blue"), True, cur, icon="hard-hat"))
	if cl:
		out.append(lambda: W_stages(_("Claims"), _("{0} claims").format(len(cl)), [S(_(s), len([c for c in cl if c.status == s]), {"Certified": "y", "Paid": "g", "Rejected": "x"}.get(s, "")) for s in ("Submitted", "Certified", "Paid", "Rejected")], icon="file-text"))
	if so:
		beh = [s for s in so if s.get("behind_programme")]
		out.append(lambda: W_dark(_("Behind programme"), _("Active subcontracts"), len(beh), _("subcontractors"), [{"label": s.supplier, "sub": s.package or s.name, "value": _k(s.order_value, cur), "open": ["Subcontract Order", s.name]} for s in beh], _("All on programme"), icon="clock"))
	return out


def b_pj_time():
	cos, start, end, label, cur = _pscope()
	ts = _rows("Timesheet", _co("Timesheet", cos, {"docstatus": ["<", 2], "start_date": [">=", add_days(today(), -60)]}), ["name", "employee_name", "total_hours", "start_date", "docstatus", "parent_project", "total_costing_amount"], 2000)
	if not ts:
		return []
	draft = [t for t in ts if t.docstatus == 0]
	return [
		lambda: W_bars(_("Hours by project"), _("Last 60 days"), _bars_rows(_sum_by(ts, lambda r: r.get("parent_project") or _("No project"), "total_hours"), 6, "blue"), icon="clock"),
		lambda: W_bars(_("Hours by person"), _("Last 60 days"), _bars_rows(_sum_by(ts, "employee_name", "total_hours"), 6, "violet"), icon="users"),
		lambda: W_dark(_("To approve"), _("Draft timesheets"), len(draft), _("timesheets"), [{"label": t.employee_name or t.name, "sub": _("{0} h · from {1}").format(round(flt(t.total_hours), 1), _fd(t.start_date)), "value": "", "open": ["Timesheet", t.name]} for t in draft], _("Nothing to approve"), icon="check"),
	]


def b_pj_cost():
	cos, start, end, label, cur = _pscope()
	p = [x for x in _projects(cos) if x.status == "Open"]
	if not p:
		return []
	budget = lambda x: flt(x.estimated_costing)
	spent = lambda x: flt(x.total_costing_amount)
	over = sorted([x for x in p if budget(x) and spent(x) > budget(x) * flt(x.percent_complete or 0) / 100 * 1.05], key=lambda x: -(spent(x) - budget(x)))
	tb, ts_ = sum(budget(x) for x in p), sum(spent(x) for x in p)
	return [
		lambda: W_bars(_("Cost to date"), _("Active projects · {0}").format(cur), [{"label": x.project_name or x.name, "value": spent(x), "color": "violet", "open": ["Project", x.name]} for x in sorted(p, key=lambda x: -spent(x))[:6]], True, cur, icon="receipt"),
		lambda: W_gauge(_("Budget used"), _("All active projects"), ts_ / tb if tb else 0, _pc(ts_ / tb) if tb else "—", _("{0} of {1}").format(_k(ts_, cur), _k(tb, cur)), color="amber" if tb and ts_ / tb > 0.8 else "blue", icon="gauge"),
		lambda: W_dark(_("Spending ahead of progress"), _("Cost above budget × % done"), len(over), _("projects"), [{"label": x.project_name or x.name, "sub": _("{0}% done · {1} spent").format(round(flt(x.percent_complete)), _k(spent(x), cur)), "value": "", "open": ["Project", x.name]} for x in over], _("All within budget"), icon="triangle-alert"),
	]


# ---------------------------------------------------------------- Manufacturing
def _wos(cos):
	return _rows("Work Order", _co("Work Order", cos, {"docstatus": ["<", 2], "creation": [">=", add_months(today(), -6)]}), ["name", "status", "production_item", "item_name", "qty", "produced_qty",
		"planned_end_date", "planned_start_date", "docstatus", "process_loss_qty"], 1000)


def b_mf_prod():
	cos, start, end, label, cur = _mscope()
	w = _wos(cos)
	if not w:
		return []
	t = getdate(today())
	steps = [("Draft", "d"), ("Not Started", ""), ("In Process", "y"), ("Completed", "g"), ("Stopped", "x")]
	done = [x for x in w if x.status == "Completed"]
	qi = _rows("Quality Inspection", _co("Quality Inspection", cos, {"docstatus": 1, "report_date": [">=", add_months(today(), -2)]}), ["status", "sample_size"], 2000)
	acc = len([q for q in qi if q.status == "Accepted"])
	late = sorted([x for x in w if x.status in ("Not Started", "In Process") and x.planned_end_date and getdate(x.planned_end_date) < t], key=lambda x: getdate(x.planned_end_date))
	out = [lambda: W_stages(_("Work orders"), _("{0} orders").format(len(w)), [S(_(s), len([x for x in w if x.status == s]), tone) for s, tone in steps], icon="factory")]
	if qi:
		out.append(lambda: W_gauge(_("First-pass yield"), _("Inspections · 60 days"), acc / len(qi), _pc(acc / len(qi)), _("{0} accepted of {1}").format(acc, len(qi)), color="green", icon="check-circle"))
	else:
		q, pq = sum(flt(x.qty) for x in done), sum(flt(x.produced_qty) for x in done)
		out.append(lambda: W_gauge(_("Output against plan"), _("Completed orders"), pq / q if q else 0, _pc(pq / q) if q else "—", _("{0} of {1} units").format(round(pq), round(q)), color="green", icon="check-circle"))
	out.append(lambda: W_dark(_("Late or at risk"), _("Past due date"), len(late), _("orders"), [{"label": f"{x.name} · {x.production_item}", "sub": _("Due {0} · {1} / {2}").format(_fd(x.planned_end_date), round(flt(x.produced_qty)), round(flt(x.qty))),
		"value": _(x.status), "open": ["Work Order", x.name]} for x in late], _("Nothing late"), icon="clock"))
	return out


def b_prod_tracker():
	return b_mf_prod()


def b_mf_plan():
	cos, start, end, label, cur = _mscope()
	w = [x for x in _wos(cos) if x.status in ("Draft", "Not Started", "In Process")]
	pp = _rows("Production Plan", _co("Production Plan", cos, {"docstatus": ["<", 2]}), ["name", "status"], 200)
	out = []
	if w:
		days = [add_days(today(), i) for i in range(0, 14)]
		out.append(lambda: W_trend(_("Planned load"), _("Units due · next 14 days"), [_fd(d) for d in days], [{"name": _("Units"), "data": [sum(flt(x.qty) - flt(x.produced_qty) for x in w if x.planned_end_date and str(getdate(x.planned_end_date)) == str(d)) for d in days], "color": "blue"}], icon="calendar"))
		out.append(lambda: W_bars(_("Open quantity by item"), _("Units still to make"), _bars_rows(_sum_by(w, lambda x: x.item_name or x.production_item, lambda x: flt(x.qty) - flt(x.produced_qty)), 6, "violet"), icon="package"))
	if pp:
		out.append(lambda: W_donut(_("Production plans"), _("By status"), [{"label": _(k), "value": v} for k, v in _cnt(pp, "status").items()], len(pp), _("plans"), icon="clipboard"))
	return out


def b_mf_bom():
	cos, start, end, label, cur = _mscope()
	b = _rows("BOM", _co("BOM", cos, {"docstatus": ["<", 2]}), ["name", "item", "item_name", "is_active", "is_default", "total_cost", "docstatus", "with_operations"], 500)
	if not b:
		return []
	act = [x for x in b if x.is_active and x.docstatus == 1]
	return [
		lambda: W_donut(_("BOMs"), _("{0} in total").format(len(b)), [{"label": _("Active default"), "value": len([x for x in act if x.is_default]), "color": "green"}, {"label": _("Active"), "value": len([x for x in act if not x.is_default]), "color": "blue"},
			{"label": _("Draft"), "value": len([x for x in b if x.docstatus == 0]), "color": "amber"}, {"label": _("Inactive"), "value": len([x for x in b if x.docstatus == 1 and not x.is_active]), "color": "grey"}], len(b), _("BOMs"), icon="layers"),
		lambda: W_bars(_("Cost per unit"), _("Active default BOMs · {0}").format(cur), [{"label": x.item_name or x.item, "value": flt(x.total_cost), "color": "violet", "open": ["BOM", x.name]} for x in sorted([x for x in act if x.is_default], key=lambda x: -flt(x.total_cost))[:6]], True, cur, icon="receipt"),
		lambda: W_gauge(_("With routings"), _("Active BOMs with operations"), len([x for x in act if x.with_operations]) / len(act) if act else 0, f"{len([x for x in act if x.with_operations])} / {len(act)}", _("have a routing"), icon="git-branch"),
	]


def b_mf_floor():
	cos, start, end, label, cur = _mscope()
	jc = _rows("Job Card", _co("Job Card", cos, {"docstatus": ["<", 2], "creation": [">=", add_days(today(), -30)]}), ["name", "workstation", "status", "for_quantity", "total_completed_qty", "operation", "work_order"], 2000)
	if not jc:
		return []
	open_ = [j for j in jc if j.status in ("Open", "Work In Progress", "Material Transferred", "On Hold")]
	return [
		lambda: W_bars(_("Load by workstation"), _("Open job cards · units"), _bars_rows(_sum_by(open_, "workstation", lambda j: flt(j.for_quantity) - flt(j.total_completed_qty)), 6, "blue"), icon="cpu"),
		lambda: W_donut(_("Job cards"), _("Last 30 days"), [{"label": _(k), "value": v} for k, v in _cnt(jc, "status").items()], len(jc), _("cards"), icon="list"),
		lambda: W_dark(_("On the floor now"), _("Work in progress"), len([j for j in jc if j.status == "Work In Progress"]), _("in progress"), [{"label": f"{j.operation or ''} · {j.workstation or ''}", "sub": f"{j.work_order} · {round(flt(j.total_completed_qty))} / {round(flt(j.for_quantity))}",
			"value": "", "open": ["Job Card", j.name]} for j in jc if j.status == "Work In Progress"], _("Nothing in progress"), icon="activity"),
	]


def b_mf_qc():
	cos, start, end, label, cur = _mscope()
	qi = _rows("Quality Inspection", _co("Quality Inspection", cos, {"docstatus": ["<", 2], "report_date": [">=", add_months(today(), -6)]}), ["name", "status", "report_date", "item_name", "item_code", "inspection_type", "docstatus", "reference_name"], 2000)
	if not qi:
		return []
	sub = [q for q in qi if q.docstatus == 1]
	acc = len([q for q in sub if q.status == "Accepted"])
	rej = sorted([q for q in sub if q.status == "Rejected"], key=lambda q: str(q.report_date), reverse=True)

	def tr():
		lb, a = _monthly([q for q in sub if q.status == "Accepted"], "report_date")
		_l, r = _monthly(rej, "report_date")
		return W_trend(_("Inspections per month"), _("Accepted and rejected"), lb, [{"name": _("Accepted"), "data": a, "color": "green"}, {"name": _("Rejected"), "data": r, "color": "red"}], icon="check-circle")
	return [
		lambda: W_gauge(_("Pass rate"), _("Submitted inspections · 6 months"), acc / len(sub) if sub else 0, _pc(acc / len(sub)) if sub else "—", _("{0} accepted of {1}").format(acc, len(sub)), color="green", icon="shield-check"),
		tr,
		lambda: W_dark(_("Rejected lately"), _("Latest first"), len(rej), _("rejected"), [{"label": q.item_name or q.item_code, "sub": f"{_(q.inspection_type or '')} · {_fd(q.report_date)}", "value": "", "open": ["Quality Inspection", q.name]} for q in rej], _("No rejections"), icon="x-circle"),
	]


def b_mf_cost():
	cos, start, end, label, cur = _mscope()
	se = _rows("Stock Entry", _co("Stock Entry", cos, {"docstatus": 1, "purpose": "Manufacture", "posting_date": [">=", _months()[0][0]]}), ["name", "posting_date", "total_outgoing_value", "total_incoming_value", "work_order", "total_additional_costs"], 2000)
	if not se:
		return []

	def tr():
		lb, d = _monthly(se, "posting_date", lambda r: r.total_incoming_value)
		return W_trend(_("Value produced"), _("Finished goods · {0}").format(cur), lb, [{"name": _("Produced"), "data": d, "color": "blue"}], True, cur, icon="factory")
	mat = sum(flt(r.total_outgoing_value) for r in se)
	add = sum(flt(r.get("total_additional_costs")) for r in se)
	return [
		tr,
		lambda: W_donut(_("Where production cost goes"), _("Last 6 months · {0}").format(cur), [{"label": _("Materials"), "value": round(mat), "color": "blue"}, {"label": _("Labour & overheads"), "value": round(add), "color": "amber"}], _k(mat + add), cur, True, cur, icon="chart-pie"),
		lambda: W_bars(_("Cost per work order"), _("Latest · {0}").format(cur), [{"label": r.work_order or r.name, "value": flt(r.total_incoming_value), "color": "violet", "open": ["Stock Entry", r.name]} for r in sorted(se, key=lambda r: str(r.posting_date), reverse=True)[:6]], True, cur, icon="receipt"),
	]


# ---------------------------------------------------------------- dispatcher
BANDS = {
	"home": b_home, "messages": b_messages, "approvals": b_approvals, "alerts": b_alerts, "journey": b_journey, "landed": b_landed, "tests": b_tests,
	"addons": b_addons, "menu": b_menu, "portal": b_portal,
	"sales": b_sales, "crm": b_crm, "so_tracker": b_so_tracker, "exports": b_exports,
	"purchasing": b_purchasing, "imports": b_imports, "receiving": b_receiving, "lc": b_lc,
	"stock": b_stock, "dispatch": b_dispatch,
	"finance": b_finance, "accounts": b_accounts, "vat": b_vat, "tax": b_tax, "group": b_group, "kyc": b_kyc, "codocs": b_codocs,
	"hr": b_hr, "assets": b_assets,
	"pj_home": b_pj_home, "prj_tracker": b_prj_tracker, "pj_boq": b_pj_boq, "pj_site": b_pj_site, "pj_bill": b_pj_bill, "pj_sub": b_pj_sub, "pj_time": b_pj_time, "pj_cost": b_pj_cost,
	"mf_prod": b_mf_prod, "prod_tracker": b_prod_tracker, "mf_plan": b_mf_plan, "mf_bom": b_mf_bom, "mf_floor": b_mf_floor, "shopfloor": b_mf_floor, "mf_qc": b_mf_qc, "mf_cost": b_mf_cost,
}


def _empty(w):
	t = w.get("type")
	if t == "stages":
		return not any(cint(s.get("n")) for s in w.get("stages") or [])
	if t in ("bars", "donut"):
		return not any(flt(r.get("value")) for r in w.get("rows") or [])
	if t == "trend":
		return not any(flt(x) for s in w.get("series") or [] for x in s.get("data") or [])
	if t == "heat":
		return not any(flt(x) for r in w.get("values") or [] for x in r)
	return False


@frappe.whitelist()
def get_band(key):
	f = BANDS.get(key)
	if not f:
		return []
	try:
		makers = f() or []
	except Exception:
		frappe.log_error(title=f"Hipersign band {key}")
		return []
	out = []
	for m in makers:
		try:
			w = m() if callable(m) else m
		except Exception:
			frappe.log_error(title=f"Hipersign band {key} widget")
			continue
		if w and not _empty(w):
			out.append(w)
	return out[:3]
