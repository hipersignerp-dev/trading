#!/usr/bin/env python3
"""Unit tests for the menu builder's merge logic (hipersign_trading/menu.py) — plain Python, no bench.

	python3 tools/test_menu.py

navigation.py is loaded with a stub `frappe` module so its NAV / NAV_SUB and nav_groups(check=False) are real.
"""

import os
import sys
import types
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

# a stub frappe: navigation.py imports frappe and hipersign_trading.features at module level
frappe_stub = types.ModuleType("frappe")
frappe_stub._ = lambda s: s
sys.modules.setdefault("frappe", frappe_stub)

from hipersign_trading import menu  # noqa: E402
from hipersign_trading import navigation  # noqa: E402


def R(scope, key, **kw):
	r = {"scope": scope, "item_key": key, "company": None, "role": None, "item_type": "Group" if key.startswith("g:") else "Item",
		"visibility": "Standard", "sort_order": 0, "label_en": "", "label_ar": "", "label_zh": "", "parent_group": "", "link_url": "", "icon": ""}
	r.update(kw)
	return r


_nav_groups = navigation.nav_groups


def groups():
	return _nav_groups(check=False)


def keys(gs):
	return [g["key"] for g in gs]


def item_keys(gs, gkey):
	return [i["key"] for i in next(g for g in gs if g["key"] == gkey)["items"]]


class TestKeys(unittest.TestCase):
	def test_keys_unique_and_stable(self):
		gs = groups()
		ks = [g["key"] for g in gs] + [i["key"] for g in gs for i in g["items"]]
		self.assertEqual(len(ks), len(set(ks)))
		self.assertIn("g:finance-tax", ks)
		self.assertIn("hipersign-crm", ks)
		self.assertIn("driver", ks)  # URL item
		self.assertIn("hipersign-menu", ks)  # the builder itself, under Admin
		self.assertIn("hipersign-menu", item_keys(gs, "g:admin"))

	def test_new_group_needs_no_code(self):
		# a NAV group added later (Projects, Manufacturing …) gets keys from its label and targets
		# (v1.8.1: a group name NAV does not have — Projects is a real group since 1.8.0)
		saved = list(navigation.NAV)
		try:
			navigation.NAV.append(("Field Service", "folder", [("Service Tracker", "Page", "hipersign-field", "folder", None, {})]))
			gs = groups()
			self.assertEqual(gs[-1]["key"], "g:field-service")
			eff = menu.effective([R("Site", "hipersign-field", visibility="Hidden"), R("Site", "g:field-service", label_zh="现场服务")])
			out = menu.apply(gs, eff, "zh")
			proj = next(g for g in out if g["key"] == "g:field-service")
			self.assertEqual(proj["display"], "现场服务")
			self.assertEqual(proj["items"], [])  # its only item is hidden; rows_from_groups() then drops the empty group
		finally:
			navigation.NAV[:] = saved

	def test_explicit_key(self):
		self.assertEqual(navigation.item_key("Page", "x-y", {"key": "custom"}), "custom")
		self.assertEqual(navigation.group_key("Finance & Tax"), "g:finance-tax")


class TestMerge(unittest.TestCase):
	def test_precedence_role_company_site(self):
		recs = [
			R("Site", "hipersign-crm", visibility="Hidden", label_en="Site CRM"),
			R("Company", "hipersign-crm", company="ACME", label_en="ACME CRM"),
			R("Role", "hipersign-crm", role="Sales User", visibility="Shown", label_en="My CRM"),
		]
		e = menu.effective(recs, company="ACME", roles=["Sales User"])["items"]["hipersign-crm"]
		self.assertFalse(e["hidden"])
		self.assertEqual(e["labels"]["en"], "My CRM")
		e = menu.effective(recs, company="ACME", roles=["Stock User"])["items"]["hipersign-crm"]
		self.assertTrue(e["hidden"])  # rename at company level does not unhide
		self.assertEqual(e["labels"]["en"], "ACME CRM")
		e = menu.effective(recs, company="Other", roles=[])["items"]["hipersign-crm"]
		self.assertEqual(e["labels"]["en"], "Site CRM")

	def test_role_order_is_deterministic(self):
		recs = [R("Role", "hipersign-crm", role="Zeta", label_en="Z"), R("Role", "hipersign-crm", role="Alpha", label_en="A")]
		self.assertEqual(menu.effective(recs, roles=["Zeta", "Alpha"])["items"]["hipersign-crm"]["labels"]["en"], "Z")

	def test_fields_merge_independently(self):
		recs = [R("Site", "hipersign-crm", label_ar="عملاء", sort_order=50), R("Role", "hipersign-crm", role="X", label_zh="客户")]
		e = menu.effective(recs, roles=["X"])["items"]["hipersign-crm"]
		self.assertEqual(e["labels"], {"ar": "عملاء", "zh": "客户"})
		self.assertEqual(e["sort"], 50)
		self.assertIsNone(e["hidden"])

	def test_other_company_ignored(self):
		recs = [R("Company", "hipersign-crm", company="B", visibility="Hidden")]
		self.assertEqual(menu.effective(recs, company="A")["items"], {})


class TestApply(unittest.TestCase):
	def test_no_overrides_is_standard(self):
		gs = groups()
		out = menu.apply(gs, {"items": {}, "links": {}})
		self.assertEqual(keys(out), keys(gs))
		self.assertEqual(item_keys(out, "g:sales"), [i["key"] for i in gs[1]["items"]])

	def test_hide_item_and_group(self):
		eff = menu.effective([R("Site", "hipersign-crm", visibility="Hidden"), R("Site", "g:add-ons", visibility="Hidden")])
		out = menu.apply(groups(), eff)
		self.assertNotIn("hipersign-crm", item_keys(out, "g:sales"))
		self.assertNotIn("g:add-ons", keys(out))
		full = menu.apply(groups(), eff, keep_hidden=True)
		self.assertIn("g:add-ons", keys(full))

	def test_labels_by_language(self):
		eff = menu.effective([R("Site", "hipersign-crm", label_en="Leads", label_zh="线索")])
		crm = lambda out: next(i for i in out[1]["items"] if i["key"] == "hipersign-crm")
		self.assertEqual(crm(menu.apply(groups(), eff, "zh"))["display"], "线索")
		self.assertEqual(crm(menu.apply(groups(), eff, "zh-CN"))["display"], "线索")
		self.assertEqual(crm(menu.apply(groups(), eff, "ar"))["display"], "Leads")  # no Arabic rename: English rename
		self.assertIsNone(next(i for i in menu.apply(groups(), eff)[1]["items"] if i["key"] == "hipersign-orders")["display"])

	def test_reorder_groups_and_items(self):
		eff = menu.effective([R("Site", "g:admin", sort_order=5), R("Site", "sales-order-tracker", sort_order=1)])
		out = menu.apply(groups(), eff)
		self.assertEqual(keys(out)[0], "g:admin")
		self.assertEqual(item_keys(out, "g:sales")[0], "sales-order-tracker")

	def test_custom_link(self):
		recs = [R("Site", "link-abc", item_type="Custom Link", label_en="Supplier portal", label_zh="供应商门户", link_url="#hipersign-home",
			parent_group="g:purchasing", icon="share")]
		eff = menu.effective(recs)
		out = menu.apply(groups(), eff, "zh")
		it = next(i for i in out[2]["items"] if i["key"] == "link-abc")
		self.assertTrue(it["custom"])
		self.assertEqual(it["target"], "/app/hipersign-home")
		self.assertEqual(it["display"], "供应商门户")
		self.assertEqual(item_keys(out, "g:purchasing")[-1], "link-abc")
		# a role can hide a site link
		eff = menu.effective(recs + [R("Role", "link-abc", role="X", visibility="Hidden")], roles=["X"])
		self.assertNotIn("link-abc", item_keys(menu.apply(groups(), eff), "g:purchasing"))
		# unknown group → the last group
		eff = menu.effective([dict(recs[0], parent_group="g:gone")])
		self.assertEqual(menu.apply(groups(), eff)[-1]["items"][-1]["key"], "link-abc")

	def test_hidden_doctypes(self):
		eff = menu.effective([R("Site", "hipersign-crm", visibility="Hidden"), R("Site", "g:people-assets", visibility="Hidden")])
		dts = menu.hidden_doctypes(menu.apply(groups(), eff, keep_hidden=True), navigation.NAV_SUB)
		self.assertIn("Lead", dts)
		self.assertIn("Employee", dts)
		self.assertIn("Asset", dts)
		self.assertNotIn("Customer", dts)
		# a doctype still reachable from a visible entry is not hidden
		sub = dict(navigation.NAV_SUB, **{"Quotations & Orders": navigation.NAV_SUB["Quotations & Orders"] + [("Leads", "DocType", "Lead", None)]})
		self.assertNotIn("Lead", menu.hidden_doctypes(menu.apply(groups(), eff, keep_hidden=True), sub))


class TestBoot(unittest.TestCase):
	"""menu.boot() rewrites the user's copy of the Workspace Sidebar in the boot info."""

	def setUp(self):
		self.saved = (menu.for_user, navigation.nav_groups, getattr(frappe_stub, "local", None), frappe_stub._)
		frappe_stub.local = types.SimpleNamespace(lang="zh")
		frappe_stub._ = lambda s: {"Sales": "销售", "CRM & Leads": "客户关系与线索"}.get(s, s)
		navigation.nav_groups = lambda s=None, check=True: groups()

	def tearDown(self):
		menu.for_user, navigation.nav_groups, frappe_stub.local, frappe_stub._ = self.saved

	def boot_with(self, eff, drop=(), modern=False, extra=()):
		"""modern: Frappe 16.30+ boot (module_sidebars, keyed by the Sidebar's name, rows with a "key");
		extra: rows a Custom Sidebar layer added."""
		menu.for_user = lambda user=None: eff
		rows = navigation.rows_from_groups(groups())
		items = []
		for r in rows:
			if r.get("link_to") in drop:
				continue  # the desk left out what the user may not open
			d = {k: v for k, v in r.items() if k != "hs_key"}
			d["label"] = frappe_stub._(d["label"])
			d.setdefault("url", None)
			d.setdefault("link_to", None)
			if modern:
				d["key"] = "|".join((d["type"], d.get("link_type") or "", d.get("link_to") or "", d.get("url") or "", "")) \
					if d["type"] == "Link" else "sec-" + d["label"]
			items.append(d)
		items.extend(extra)
		if modern:
			bootinfo = types.SimpleNamespace(module_sidebars={"Hipersign ERP": {"name": "Hipersign ERP", "label": "Hipersign ERP", "items": items},
				"Selling": {"name": "Selling", "items": []}})
		else:
			bootinfo = types.SimpleNamespace(workspace_sidebar_item={"hipersign erp": {"label": "Hipersign ERP", "items": items}})
		bootinfo.get = lambda k, default=None: getattr(bootinfo, k, default)
		info = {}
		menu.boot(bootinfo, info)
		if modern:
			return bootinfo.module_sidebars["Hipersign ERP"]["items"], info
		return bootinfo.workspace_sidebar_item["hipersign erp"]["items"], info

	def test_no_overrides_untouched(self):
		items, info = self.boot_with({"items": {}, "links": {}})
		self.assertEqual(info["menu_hidden_dts"], [])
		self.assertEqual(info["nav_alias"]["客户关系与线索"], "CRM & Leads")

	def test_rewrite(self):
		eff = menu.effective([R("Site", "hipersign-crm", label_zh="线索"), R("Site", "sales-order-tracker", visibility="Hidden"),
			R("Site", "g:add-ons", visibility="Hidden"),
			R("Site", "link-x", item_type="Custom Link", label_en="Portal", label_zh="门户", link_url="https://p.example", parent_group="g:sales")])
		items, info = self.boot_with(eff, drop=("hipersign-exports",))
		labels = [i["label"] for i in items]
		self.assertEqual(items[0]["link_to"], "hipersign-home")  # Home stays on top, outside a section
		self.assertIn("线索", labels)
		self.assertEqual(info["nav_alias"]["线索"], "CRM & Leads")
		self.assertNotIn("sales-order-tracker", [i.get("link_to") for i in items])
		self.assertNotIn("hipersign-exports", [i.get("link_to") for i in items])  # still not permitted
		self.assertNotIn("Add-ons", labels)  # hidden group: no empty section either
		self.assertNotIn("hipersign-addons", [i.get("link_to") for i in items])
		link = next(i for i in items if i.get("url") == "https://p.example")
		self.assertEqual(link["label"], "门户")
		self.assertEqual(link["link_type"], "URL")
		sales = labels.index("销售")
		self.assertLess(sales, labels.index("门户"))
		# every section is followed by at least one item
		for n, i in enumerate(items):
			if i["type"] == "Section Break":
				self.assertTrue(n + 1 < len(items) and items[n + 1]["type"] != "Section Break", i["label"])


	def test_rewrite_frappe_16_30(self):
		"""v1.8.1: the same rewrite on Frappe 16.30+ (module_sidebars); sections keep Frappe's key; a Custom Sidebar
		layer's own link is kept at the end."""
		eff = menu.effective([R("Site", "hipersign-crm", label_zh="线索"), R("Site", "g:projects", visibility="Hidden"),
			R("Site", "link-x", item_type="Custom Link", label_en="Portal", link_url="/app/todo", parent_group="g:sales")])
		layer = {"type": "Link", "label": "ToDo list", "link_type": "DocType", "link_to": "ToDo", "url": None, "child": 1, "added": 1,
			"key": "Link|DocType|ToDo||"}
		items, info = self.boot_with(eff, drop=("hipersign-exports",), modern=True, extra=[layer])
		labels = [i["label"] for i in items]
		self.assertEqual(items[0]["link_to"], "hipersign-home")
		self.assertIn("线索", labels)
		self.assertNotIn("hipersign-projects", [i.get("link_to") for i in items])
		self.assertNotIn("hipersign-exports", [i.get("link_to") for i in items])
		sales = next(i for i in items if i["type"] == "Section Break" and i["label"] == "销售")
		self.assertEqual(sales["key"], "sec-销售")  # Frappe's own section row, relabelled
		link = next(i for i in items if i.get("url") == "/app/todo")
		self.assertEqual(link["open_in_new_tab"], 0)
		self.assertTrue(link["key"])
		self.assertEqual(items[-1]["link_to"], "ToDo")
		self.assertEqual(items[-1]["child"], 0)

	def test_hidden_by_layer_stays_hidden(self):
		"""An entry Frappe left out (hidden by a Custom Sidebar layer, or not permitted) is not brought back."""
		eff = menu.effective([R("Site", "hipersign-crm", label_zh="线索")])
		items, info = self.boot_with(eff, drop=("hipersign-orders",), modern=True)
		self.assertNotIn("hipersign-orders", [i.get("link_to") for i in items])


class TestConfig(unittest.TestCase):
	def test_clean_drops_standard_rows(self):
		c = menu.clean_config({"hipersign-crm": {"visibility": "Standard"}, "g:sales": {"visibility": "Hidden"}, "": {"x": 1},
			"link-1": {"item_type": "Custom Link", "label_en": "A", "link_url": "https://a.b"}})
		self.assertEqual(set(c), {"g:sales", "link-1"})
		self.assertEqual(c["g:sales"]["item_type"], "Group")

	def test_describe(self):
		old = menu.clean_config({"hipersign-crm": {"visibility": "Hidden"}})
		new = menu.clean_config({"hipersign-crm": {"label_zh": "线索"}, "link-1": {"item_type": "Custom Link", "label_en": "Portal", "link_url": "https://x.y"},
			"g:sales": {"sort_order": 20}})
		lines = menu.describe(old, new, {"hipersign-crm": "CRM & Leads", "g:sales": "Sales"})
		self.assertIn("Standard visibility for “CRM & Leads”", lines)
		self.assertIn("Rename “CRM & Leads” (Chinese) → 线索", lines)
		self.assertIn("Add link “Portal” → https://x.y", lines)
		self.assertTrue(any(x.startswith("Reorder: Sales") for x in lines))
		self.assertEqual(menu.describe(new, new), [])

	def test_valid_link(self):
		for ok in ("https://a.com/x", "/app/hipersign-home", "#hipersign-home"):
			self.assertTrue(menu.valid_link(ok), ok)
		for bad in ("javascript:alert(1)", "", "ftp://x", "hello world"):
			self.assertFalse(menu.valid_link(bad), bad)


if __name__ == "__main__":
	unittest.main(verbosity=1)
