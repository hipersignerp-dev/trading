"""v1.8.0: the menu builder page (Admin → Menu builder) — read, preview, save and reset one scope's menu changes.

Only System Manager and Managing Director. The rules of the merge are in hipersign_trading/menu.py.
"""

import json

import frappe
from frappe import _
from frappe.translate import get_all_translations

from hipersign_trading import menu, navigation


def _guard():
	if not set(frappe.get_roles()) & set(menu.BUILDER_ROLES):
		frappe.throw(_("Only a System Manager or the Managing Director can change the menu"), frappe.PermissionError)


def _scope(scope, company=None, role=None):
	if scope not in menu.SCOPES:
		frappe.throw(_("Unknown scope {0}").format(scope))
	company = company if scope == "Company" else None
	role = role if scope == "Role" else None
	if scope == "Company" and not (company and frappe.db.exists("Company", company)):
		frappe.throw(_("Choose a company"))
	if scope == "Role" and not (role and frappe.db.exists("Role", role)):
		frappe.throw(_("Choose a role"))
	return scope, company, role


def scope_label(scope, company=None, role=None):
	if scope == "Company":
		return _("Company — {0}").format(company)
	if scope == "Role":
		return _("Role — {0}").format(_(role))
	return _("Whole site")


def _own(scope, company, role):
	"""This scope's records as {key: row}."""
	out = {}
	for r in menu.records():
		if r.get("scope") == scope and (r.get("company") or None) == company and (r.get("role") or None) == role:
			out[r["item_key"]] = {k: r.get(k) for k in menu.FIELDS}
	return menu.clean_config(out)


def _inherited(scope, company, role):
	"""What the less specific scopes already set (the builder shows it as the starting point): nothing for the whole
	site, the site's changes for a company or a role."""
	if scope == "Site":
		return {"items": {}, "links": {}}
	recs = [r for r in menu.records() if r.get("scope") == "Site"]
	return menu.effective(recs)


def _std_labels(groups):
	ar, zh = get_all_translations("ar") or {}, get_all_translations("zh") or {}
	out = {}
	for g in groups:
		for x in [g] + g["items"]:
			out[x["key"]] = {"en": x["label"], "ar": ar.get(x["label"], ""), "zh": zh.get(x["label"], "")}
	return out


@frappe.whitelist()
def get_builder(scope="Site", company=None, role=None):
	_guard()
	# v1.8.4 (#28): switching to the Company or Role scope used to send no company / role yet — the server refused and
	# the page stayed on "Loading…". Start on the user's default company (else the first) and the first role instead.
	if scope == "Company" and not (company and frappe.db.exists("Company", company)):
		company = frappe.defaults.get_user_default("Company")
		if not (company and frappe.db.exists("Company", company)):
			company = (frappe.get_all("Company", pluck="name", order_by="name", limit=1) or [None])[0]
	if scope == "Role" and not (role and frappe.db.exists("Role", role)):
		role = (frappe.get_all("Role", filters={"disabled": 0, "desk_access": 1, "name": ["not in", ["Administrator", "Guest", "All", "Desk User"]]},
			pluck="name", order_by="name", limit=1) or [None])[0]
	scope, company, role = _scope(scope, company, role)
	groups = navigation.nav_groups(check=False)
	return {
		"groups": [{"key": g["key"], "label": g["label"], "icon": g["icon"],
			"items": [{"key": i["key"], "label": i["label"], "icon": i["icon"], "link_type": i["link_type"], "target": i["target"]} for i in g["items"]]}
			for g in groups],
		"std": _std_labels(groups),
		"own": _own(scope, company, role),
		"inherited": _inherited(scope, company, role),
		"scope_label": scope_label(scope, company, role),
		"company": company,
		"role": role,
		"companies": frappe.get_all("Company", pluck="name", order_by="name"),
		"roles": frappe.get_all("Role", filters={"disabled": 0, "desk_access": 1, "name": ["not in", ["Administrator", "Guest", "All", "Desk User"]]},
			pluck="name", order_by="name"),
		"log": log(),
		"lang": menu.lang_code(frappe.local.lang),
	}


@frappe.whitelist()
def log(limit=40):
	_guard()
	return frappe.get_all(menu.LOG_DOCTYPE, fields=["scope_label", "change", "owner", "creation"], order_by="creation desc",
		limit_page_length=min(int(limit or 40), 200))


def _records_with(scope, company, role, config):
	"""All site records with this scope's set replaced by config (for the preview)."""
	others = [r for r in menu.records() if not (r.get("scope") == scope and (r.get("company") or None) == company and (r.get("role") or None) == role)]
	mine = [dict(v, scope=scope, company=company, role=role, item_key=k) for k, v in config.items()]
	return others + mine


@frappe.whitelist()
def preview(scope="Site", company=None, role=None, config=None, lang=None):
	"""The sidebar this scope would get with the unsaved changes: site → company → role, as in menu.chain()."""
	_guard()
	scope, company, role = _scope(scope, company, role)
	config = menu.clean_config(json.loads(config) if isinstance(config, str) else config or {})
	recs = _records_with(scope, company, role, config)
	eff = menu.effective(recs, company=company, roles=[role] if role else [])
	lang = menu.lang_code(lang or frappe.local.lang)
	groups = menu.apply(navigation.nav_groups(), eff, lang)
	tr = get_all_translations(lang) if lang != "en" else {}
	return [{"label": g.get("display") or tr.get(g["label"], g["label"]), "icon": g["icon"],
		"items": [{"label": i.get("display") or tr.get(i["label"], i["label"]), "icon": i["icon"], "custom": i.get("custom")} for i in g["items"]]}
		for g in groups if g["items"]]


@frappe.whitelist(methods=["POST"])
def save(scope="Site", company=None, role=None, config=None):
	"""Replace this scope's changes with config ({key: row}); log every difference."""
	_guard()
	scope, company, role = _scope(scope, company, role)
	new = menu.clean_config(json.loads(config) if isinstance(config, str) else config or {})
	for key, row in new.items():
		if row["item_type"] == "Custom Link" and not menu.valid_link(row["link_url"]):
			frappe.throw(_("Use a web address (https://…), a desk path (/app/…) or #page for {0}").format(row.get("label_en") or key))
	old = _own(scope, company, role)
	names = {k: v["en"] for k, v in _std_labels(navigation.nav_groups(check=False)).items()}
	lines = menu.describe(old, new, names)
	existing = {r["item_key"]: r["name"] for r in menu.records()
		if r.get("scope") == scope and (r.get("company") or None) == company and (r.get("role") or None) == role}
	for key, name in existing.items():
		if key not in new:
			frappe.delete_doc(menu.DOCTYPE, name, ignore_permissions=True)
	for key, row in new.items():
		if key in existing:
			if old.get(key) == row:
				continue
			doc = frappe.get_doc(menu.DOCTYPE, existing[key])
		else:
			doc = frappe.new_doc(menu.DOCTYPE)
			doc.update({"scope": scope, "company": company, "role": role, "item_key": key})
		doc.update(row)
		doc.save(ignore_permissions=True)
	_log(scope, company, role, lines)
	menu.clear_cache()
	return {"changes": len(lines), "own": _own(scope, company, role), "log": log()}


@frappe.whitelist(methods=["POST"])
def reset(scope="Site", company=None, role=None):
	"""Reset to standard: remove every change of this scope (other scopes keep theirs)."""
	_guard()
	scope, company, role = _scope(scope, company, role)
	n = 0
	for r in menu.records():
		if r.get("scope") == scope and (r.get("company") or None) == company and (r.get("role") or None) == role:
			frappe.delete_doc(menu.DOCTYPE, r["name"], ignore_permissions=True)
			n += 1
	_log(scope, company, role, ["Reset to standard"])
	menu.clear_cache()
	return {"removed": n, "log": log()}


def _log(scope, company, role, lines):
	if not lines:
		return
	label = scope_label(scope, company, role)
	for line in lines:
		frappe.get_doc({"doctype": menu.LOG_DOCTYPE, "scope_label": label, "change": line}).insert(ignore_permissions=True)
