"""v1.8.0 — the menu builder (Admin → Menu builder) applied to the Hipersign ERP sidebar.

Overrides live in **Hipersign Menu Override**, one record per menu entry and scope:
  · scope Site, Company (+ company) or Role (+ role)
  · item_key: the stable key of a NAV group ("g:sales") or item ("hipersign-crm") — navigation.group_key / item_key —
    or "link-…" for a custom link
  · visibility (Standard / Hidden / Shown), label_en / label_ar / label_zh, sort_order (0 = standard position)
  · custom links (item_type "Custom Link"): link_url, icon, parent_group

Precedence: role > company > site. Each field is taken from the most specific scope that sets it; with several roles,
their records are applied in role-name order (the last one wins). Overrides are applied per user at boot, on top of
feature-pack filtering (navigation.nav_groups), so a NAV group added later (Projects, Manufacturing …) is covered with
no code change. A menu never grants access: the desk still drops links the user may not open.

The merge functions below are pure (no frappe) so they can be unit-tested without a bench (tools/test_menu.py).
"""

import re

DOCTYPE = "Hipersign Menu Override"
LOG_DOCTYPE = "Hipersign Menu Log"
BUILDER_ROLES = ("System Manager", "Managing Director")
SCOPES = ("Site", "Company", "Role")
LANGS = ("en", "ar", "zh")
FIELDS = ("item_type", "visibility", "label_en", "label_ar", "label_zh", "sort_order", "parent_group", "link_url", "icon")
CACHE_KEY = "hs_menu_overrides"


# ---------------------------------------------------------------- pure functions
def lang_code(lang):
	"""The builder's three label columns: "zh", "zh-CN", "zh-TW" → "zh"; "ar…" → "ar"; anything else → "en"."""
	lang = (lang or "en").lower()
	if lang.startswith("zh"):
		return "zh"
	if lang.startswith("ar"):
		return "ar"
	return "en"


def chain(records, company=None, roles=()):
	"""The records that apply, least specific first: site, then the company's, then each role's (by role name)."""
	roles = set(roles or ())
	site = [r for r in records if r.get("scope") == "Site"]
	co = [r for r in records if r.get("scope") == "Company" and company and r.get("company") == company]
	ro = sorted((r for r in records if r.get("scope") == "Role" and r.get("role") in roles), key=lambda r: r.get("role") or "")
	return site + co + ro


def effective(records, company=None, roles=()):
	"""Merge the records for one user: {"items": {key: {"hidden", "labels", "sort"}}, "links": {key: link}}.
	hidden/sort are None when no scope sets them; labels only holds the languages some scope renamed."""
	items, links = {}, {}
	for r in chain(records, company, roles):
		key = r.get("item_key")
		if not key:
			continue
		e = items.setdefault(key, {"hidden": None, "labels": {}, "sort": None})
		vis = r.get("visibility") or "Standard"
		if vis == "Hidden":
			e["hidden"] = True
		elif vis == "Shown":
			e["hidden"] = False
		for lg in LANGS:
			v = (r.get("label_" + lg) or "").strip()
			if v:
				e["labels"][lg] = v
		if r.get("sort_order"):
			e["sort"] = int(r["sort_order"])
		if r.get("item_type") == "Custom Link" and r.get("link_url"):
			links[key] = {"key": key, "url": r["link_url"], "icon": r.get("icon") or "link", "parent_group": r.get("parent_group") or "",
				"label": (r.get("label_en") or "").strip() or key, "scope": r.get("scope")}
	return {"items": items, "links": links}


def pick_label(e, lang):
	"""The renamed label in the user's language, else the English rename, else None (the standard, translated label)."""
	if not e:
		return None
	labels = e.get("labels") or {}
	return labels.get(lang_code(lang)) or labels.get("en") or None


def link_route(url):
	"""Custom-link targets: https://…, /app/… or #page (a desk page) — returned as a URL the sidebar can open."""
	url = (url or "").strip()
	if url.startswith("#"):
		return "/app/" + url[1:].lstrip("/")
	return url


def valid_link(url):
	return bool(re.match(r"^(https?://\S+|/\S*|#[\w\-/]+)$", (url or "").strip()))


def apply(groups, eff, lang="en", keep_hidden=False):
	"""The menu for one user. groups: navigation.nav_groups(). Returns new groups, each item with "display" (the
	renamed label or None), "hidden" and "custom"; ordered by sort_order (standard position = (index + 1) × 10).
	Hidden groups and items are dropped unless keep_hidden (the builder's preview keeps them, flagged)."""
	items_eff = (eff or {}).get("items", {})
	links = (eff or {}).get("links", {})
	out = []
	for gi, g in enumerate(groups):
		ge = items_eff.get(g["key"], {})
		ng = dict(g, display=pick_label(ge, lang), hidden=bool(ge.get("hidden")), sort=ge.get("sort") or (gi + 1) * 10, items=[])
		for ii, it in enumerate(g["items"]):
			ie = items_eff.get(it["key"], {})
			ng["items"].append(dict(it, display=pick_label(ie, lang), hidden=bool(ie.get("hidden")), custom=False,
				sort=ie.get("sort") or (ii + 1) * 10))
		out.append(ng)
	by_key = {g["key"]: g for g in out}
	for n, (key, ln) in enumerate(sorted(links.items())):
		g = by_key.get(ln["parent_group"]) or (out[-1] if out else None)
		if g is None:
			continue
		ie = items_eff.get(key, {})
		g["items"].append({"key": key, "label": ln["label"], "link_type": "URL", "target": link_route(ln["url"]), "icon": ln["icon"],
			"feature": None, "extra": {}, "display": pick_label(ie, lang), "hidden": bool(ie.get("hidden")), "custom": True,
			"sort": ie.get("sort") or 10000 + n})
	for g in out:
		g["items"].sort(key=lambda it: it["sort"])
	out.sort(key=lambda g: g["sort"])
	if keep_hidden:
		return out
	res = []
	for g in out:
		if g["hidden"]:
			continue
		res.append(dict(g, items=[it for it in g["items"] if not it["hidden"]]))
	return res


def hidden_doctypes(groups_all, nav_sub):
	"""Doctypes reached only through hidden menu entries — left out of + New and the top-bar search.
	groups_all: apply(..., keep_hidden=True); nav_sub: navigation.NAV_SUB."""
	hid, vis = set(), set()
	for g in groups_all:
		for it in g["items"]:
			dts = {r[2] for r in nav_sub.get(it["label"], []) if r[1] == "DocType"}
			if it.get("link_type") == "DocType":
				dts.add(it["target"])
			(hid if g["hidden"] or it["hidden"] else vis).update(dts)
	return sorted(hid - vis)


def _row_std(row):
	"""True when a builder row changes nothing (it need not be stored)."""
	if row.get("item_type") == "Custom Link":
		return False
	return (row.get("visibility") or "Standard") == "Standard" and not any((row.get("label_" + lg) or "").strip() for lg in LANGS) \
		and not int(row.get("sort_order") or 0)


def clean_config(config):
	"""Normalise the builder's rows for one scope: {key: {field: value}}, dropping rows that change nothing."""
	out = {}
	for key, row in (config or {}).items():
		if not key or not isinstance(row, dict):
			continue
		r = {
			"item_type": row.get("item_type") if row.get("item_type") in ("Group", "Item", "Custom Link") else ("Group" if key.startswith("g:") else "Item"),
			"visibility": row.get("visibility") if row.get("visibility") in ("Standard", "Hidden", "Shown") else "Standard",
			"sort_order": int(row.get("sort_order") or 0),
			"parent_group": (row.get("parent_group") or "").strip(),
			"link_url": (row.get("link_url") or "").strip(),
			"icon": (row.get("icon") or "").strip(),
		}
		for lg in LANGS:
			r["label_" + lg] = (row.get("label_" + lg) or "").strip()
		if not _row_std(r):
			out[key] = r
	return out


def describe(old, new, names=None):
	"""Change-log lines between two configs of one scope (old/new: clean_config output)."""
	names = names or {}
	nm = lambda k: names.get(k) or (new.get(k) or old.get(k) or {}).get("label_en") or k
	lang_name = {"en": "English", "ar": "Arabic", "zh": "Chinese"}
	lines = []
	moved = []
	for key in sorted(set(old) | set(new), key=lambda k: (k not in new, k)):
		a, b = old.get(key, {}), new.get(key, {})
		if b.get("item_type") == "Custom Link" and a.get("item_type") != "Custom Link":
			lines.append(f"Add link “{nm(key)}” → {b.get('link_url')}")
			continue
		if a.get("item_type") == "Custom Link" and b.get("item_type") != "Custom Link":
			lines.append(f"Remove link “{nm(key)}”")
			continue
		if (a.get("visibility") or "Standard") != (b.get("visibility") or "Standard"):
			v = b.get("visibility") or "Standard"
			lines.append({"Hidden": "Hide", "Shown": "Show"}.get(v, "Standard visibility for") + f" “{nm(key)}”")
		for lg in LANGS:
			x, y = a.get("label_" + lg) or "", b.get("label_" + lg) or ""
			if x != y:
				lines.append(f"Rename “{nm(key)}” ({lang_name[lg]}) → {y}" if y else f"Standard {lang_name[lg]} name for “{nm(key)}”")
		if int(a.get("sort_order") or 0) != int(b.get("sort_order") or 0):
			moved.append(nm(key))
		if b.get("item_type") == "Custom Link" and a and (a.get("link_url") != b.get("link_url") or a.get("parent_group") != b.get("parent_group")
				or a.get("icon") != b.get("icon")):
			lines.append(f"Change link “{nm(key)}” → {b.get('link_url')}")
	if moved:
		lines.append("Reorder: " + ", ".join(moved[:8]) + (f" (+{len(moved) - 8})" if len(moved) > 8 else ""))
	return lines


# ---------------------------------------------------------------- frappe
def _frappe():
	import frappe

	return frappe


def records():
	"""Every override on the site (cached until the builder saves)."""
	frappe = _frappe()
	cached = frappe.cache.get_value(CACHE_KEY)
	if cached is not None:
		return cached
	rows = []
	if frappe.db.table_exists(DOCTYPE):
		rows = frappe.get_all(DOCTYPE, fields=["name", "scope", "company", "role", "item_key", *FIELDS], order_by="creation asc")
		rows = [dict(r) for r in rows]
	frappe.cache.set_value(CACHE_KEY, rows)
	return rows


def clear_cache():
	frappe = _frappe()
	frappe.cache.delete_value(CACHE_KEY)
	frappe.cache.delete_key("bootinfo")


def for_user(user=None):
	"""Effective overrides for a user: their company (top-bar scope / default) and roles."""
	frappe = _frappe()
	from hipersign_trading.utils import user_company

	recs = records()
	if not recs:
		return {"items": {}, "links": {}}
	user = user or frappe.session.user
	return effective(recs, company=user_company(user), roles=frappe.get_roles(user))


def hidden_dts_for_user():
	"""Doctypes this user's menu hides (for the top-bar search). Empty when the site has no menu changes."""
	eff = for_user()
	if not eff["items"]:
		return []
	from hipersign_trading import navigation

	return hidden_doctypes(apply(navigation.nav_groups(), eff, keep_hidden=True), navigation.NAV_SUB)


def _sidebar_payload(bootinfo):
	"""v1.8.1: this user's copy of the Hipersign ERP sidebar in the boot info, and how to put a changed one back.
	Frappe 16.30+ sends `module_sidebars` (keyed by the Sidebar's name); up to 16.29 `workspace_sidebar_item`
	(keyed by the lowercased title)."""
	from hipersign_trading import navigation

	get = bootinfo.get if hasattr(bootinfo, "get") else (lambda k: None)
	for attr, key in (("module_sidebars", navigation.SIDEBAR), ("workspace_sidebar_item", navigation.SIDEBAR.lower())):
		sbs = get(attr)
		if isinstance(sbs, dict) and isinstance(sbs.get(key), dict):
			return attr, key, sbs
	return None, None, None


def _row_id(it):
	return (it.get("link_type"), it.get("link_to") or it.get("url"))


def rebuild_items(orig, shown, lang="en", alias=None, translate=None):
	"""The sidebar rows for one user from Frappe's resolved rows (orig: already filtered by permission and, on
	16.30+, by the site's and the user's Custom Sidebar layers) and the menu builder's groups (shown: apply()).
	· our entries come in the builder's order with their new labels; one Frappe dropped (not permitted, or hidden
	  by a Custom Sidebar layer) stays out — a menu never grants access;
	· a section is kept as Frappe sent it (its key, so Frappe's sidebar editor still finds it), relabelled;
	· custom links are added; rows that are not ours (added by a Custom Sidebar layer, private pages) follow at the end.
	Pure apart from `translate` (frappe._)."""
	from hipersign_trading import navigation

	tr = translate or (lambda x: x)
	alias = alias if alias is not None else {}
	by_target, sections, ours = {}, {}, set()
	section_tpl = None
	for it in orig:
		if it.get("type") == "Section Break":
			section_tpl = section_tpl or it
			sections.setdefault(it.get("label"), it)
			continue
		if it.get("type") == "Link":
			by_target.setdefault(_row_id(it), it)
	for g in shown:
		for it in g["items"]:
			if it.get("display"):
				alias[it["display"]] = it["label"]
		if g.get("display"):
			alias[g["display"]] = g["label"]
	std_targets = {(i["link_type"], i["target"]) for grp in navigation.nav_groups(check=False) for i in grp["items"]}
	new_items = []
	pending_section = None
	for row in navigation.rows_from_groups(shown):
		if row["type"] == "Section Break":
			g = next(x for x in shown if x["key"] == row["hs_key"])
			found = sections.get(tr(g["label"])) or sections.get(g["label"])
			sec = dict(found) if found else dict(section_tpl or {}, **{k: v for k, v in row.items() if k != "hs_key"})
			if found:
				ours.add(id(found))
			sec["label"] = g.get("display") or tr(g["label"])
			pending_section = sec
			continue
		it = next((i for grp in shown for i in grp["items"] if i["key"] == row["hs_key"]), None)
		if it and it.get("custom"):
			url = it["target"]
			base = {"type": "Link", "link_type": "URL", "url": url, "link_to": None, "icon": it["icon"], "child": row.get("child", 1),
				"indent": 0, "collapsible": 1, "keep_closed": 0, "show_arrow": 0, "filters": None, "route_options": None, "tab": None,
				"open_in_new_tab": 0 if url.startswith("/") else 1, "is_default_module": 0, "key": "|".join(("Link", "URL", "", url, ""))}
			base["label"] = it.get("display") or it["label"]
		else:
			found = by_target.get((row["link_type"], row.get("link_to") or row.get("url")))
			if not found:
				continue  # not permitted for this user, or hidden by a Custom Sidebar layer
			ours.add(id(found))
			base = dict(found, child=row.get("child", 1))
			if it and it.get("display"):
				base["label"] = it["display"]
		if pending_section and base.get("child", 1):
			new_items.append(pending_section)
			pending_section = None
		new_items.append(base)
	# rows that are not in the Hipersign menu at all (a Custom Sidebar layer's own links, private pages): kept, at the end
	for it in orig:
		if id(it) in ours or it.get("type") == "Section Break":
			continue
		if it.get("type") == "Link" and _row_id(it) in std_targets:
			continue  # ours, hidden or moved by the builder
		new_items.append(dict(it, child=0))
	return new_items


# v1.8.2: URL rows get no permission filter from Frappe — the roles each one needs (the Driver App: drivers and dispatch)
URL_ROLES = {"/driver": ("Stock User", "Stock Manager", "Delivery Manager", "Logistics Coordinator", "System Manager")}


def _drop_url_rows(bootinfo):
	"""Take URL entries this user cannot open out of their copy of the sidebar (a driver is linked by Driver › Hipersign user)."""
	frappe = _frappe()
	attr, key, sbs = _sidebar_payload(bootinfo)
	if not attr:
		return
	roles = set(frappe.get_roles())
	is_driver = None
	items = list(sbs[key].get("items") or [])
	keep = []
	for it in items:
		need = URL_ROLES.get(it.get("url") or "")
		if need and not roles.intersection(need):
			if is_driver is None:
				is_driver = bool(frappe.db.exists("Driver", {"hs_user": frappe.session.user})) if frappe.db.has_column("Driver", "hs_user") else False
			if not is_driver:
				continue
		keep.append(it)
	if len(keep) == len(items):
		return
	sb = dict(sbs[key])
	sb["items"] = keep
	sbs = dict(sbs)
	sbs[key] = sb
	if isinstance(bootinfo, dict):
		bootinfo[attr] = sbs
	else:
		setattr(bootinfo, attr, sbs)


def boot(bootinfo, info):
	"""Rewrite this user's copy of the Hipersign ERP sidebar in the boot info: hidden entries out, renamed labels,
	builder order, custom links. Also sends nav_alias (shown label → NAV label, for sub-items and badges) and
	menu_hidden_dts (for + New). v1.8.1: on Frappe 16.30+ (module_sidebars) as on 16.29 (workspace_sidebar_item)."""
	frappe = _frappe()
	from frappe import _

	from hipersign_trading import navigation

	lang = frappe.local.lang or "en"
	info["nav_alias"] = {}
	info["menu_hidden_dts"] = []
	eff = for_user()
	alias = info["nav_alias"]
	for group, _icon, links in navigation.NAV:
		for link in links:
			if _(link[0]) != link[0]:
				alias[_(link[0])] = link[0]
	_drop_url_rows(bootinfo)
	if not eff["items"] and not eff["links"]:
		return
	groups = navigation.nav_groups()
	full = apply(groups, eff, lang, keep_hidden=True)
	info["menu_hidden_dts"] = hidden_doctypes(full, navigation.NAV_SUB)
	attr, key, sbs = _sidebar_payload(bootinfo)
	if not attr:
		return
	sb = dict(sbs[key])
	sb["items"] = rebuild_items(list(sb.get("items") or []), apply(groups, eff, lang), lang, alias, _)
	sbs = dict(sbs)
	sbs[key] = sb
	if isinstance(bootinfo, dict):
		bootinfo[attr] = sbs
	else:
		setattr(bootinfo, attr, sbs)
