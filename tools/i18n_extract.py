#!/usr/bin/env python3
"""Extract the user-facing strings of hipersign_trading without a bench.

Frappe's own extractor (`bench get-untranslated` / `frappe.translate.get_messages_for_app`) needs a running site.
This script reads the same places with plain Python:

  · JS     __("…"), __('…'), __(`…`) (template literals without ${…})
  · Python _("…"), _('…')
  · Jinja  {{ _("…") }} in www/ and templates/
  · JSON   DocType names, field labels, descriptions, Select options, section/tab labels; Page titles;
           Workspace labels, cards, links and shortcuts; Report names; Number Card and Dashboard Chart labels;
           the guided tour (tour/tour.json); Test Centre sections and roles (test_scripts.json)
  · navigation.py  NAV group / item labels and NAV_SUB labels (rendered through __() by the desk)
  · features.py    feature labels, groups and descriptions
  · hooks.py       portal menu titles

Usage:  python3 tools/i18n_extract.py [app_dir] > strings.json
Prints a JSON list of {"msgid": str, "sources": [path, …]} sorted by msgid.
"""

import ast
import json
import os
import re
import sys

JS_CALL = re.compile(r"""\b__\(\s*(?:"((?:[^"\\\n]|\\.)*)"|'((?:[^'\\\n]|\\.)*)'|`((?:[^`\\$]|\\.|\$(?!\{))*)`)\s*[,)]""")
PY_CALL = re.compile(r"""(?<![\w.])_\(\s*(?:"((?:[^"\\\n]|\\.)*)"|'((?:[^'\\\n]|\\.)*)')\s*[,)]""")
SKIP_DIRS = {"node_modules", "__pycache__", ".git", "dist"}


def unescape_js(s):
	return re.sub(r"\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)", lambda m: _js_esc(m.group(1)), s)


def _js_esc(e):
	if e[0] == "u" and len(e) == 5:
		return chr(int(e[1:], 16))
	if e[0] == "x" and len(e) == 3:
		return chr(int(e[1:], 16))
	return {"n": "\n", "t": "\t", "r": "\r"}.get(e, e)


def unescape_py(s, q):
	try:
		return ast.literal_eval(q + s + q)
	except Exception:
		return s


class Bag:
	def __init__(self, root):
		self.root = root
		self.d = {}

	def add(self, s, path):
		if not isinstance(s, str):
			return
		s = s.strip("\n")
		if not s.strip() or not re.search(r"[A-Za-z]", s):
			return
		self.d.setdefault(s, set()).add(os.path.relpath(path, self.root))


def walk(root, exts):
	for dp, dns, fns in os.walk(root):
		dns[:] = [d for d in dns if d not in SKIP_DIRS]
		for fn in fns:
			if fn.endswith(exts):
				yield os.path.join(dp, fn)


def from_js(bag, path):
	src = open(path, encoding="utf-8").read()
	for m in JS_CALL.finditer(src):
		s = m.group(1) if m.group(1) is not None else m.group(2) if m.group(2) is not None else m.group(3)
		bag.add(unescape_js(s), path)


def from_py(bag, path):
	src = open(path, encoding="utf-8").read()
	for m in PY_CALL.finditer(src):
		if m.group(1) is not None:
			bag.add(unescape_py(m.group(1), '"'), path)
		else:
			bag.add(unescape_py(m.group(2), "'"), path)


def from_json(bag, path):
	try:
		d = json.load(open(path, encoding="utf-8"))
	except Exception:
		return
	if not isinstance(d, dict):
		return
	dt = d.get("doctype")
	if dt == "DocType":
		bag.add(d.get("name"), path)
		bag.add(d.get("description"), path)
		for f in d.get("fields", []):
			bag.add(f.get("label"), path)
			bag.add(f.get("description"), path)
			if f.get("fieldtype") == "Select" and f.get("options"):
				for o in f["options"].split("\n"):
					bag.add(o, path)
	elif dt == "Page":
		bag.add(d.get("title"), path)
	elif dt == "Workspace":
		bag.add(d.get("label"), path)
		bag.add(d.get("title"), path)
		for ln in d.get("links", []):
			bag.add(ln.get("label"), path)
			bag.add(ln.get("description"), path)
		for sc in d.get("shortcuts", []):
			bag.add(sc.get("label"), path)
		for nc in d.get("number_cards", []):
			bag.add(nc.get("label"), path)
		for ch in d.get("charts", []):
			bag.add(ch.get("label"), path)
		try:
			for blk in json.loads(d.get("content") or "[]"):
				txt = (blk.get("data") or {}).get("text")
				if txt and blk.get("type") in ("header", "paragraph"):
					bag.add(re.sub(r"<[^>]+>", "", txt).strip(), path)
		except Exception:
			pass
	elif dt == "Report":
		bag.add(d.get("name"), path)
		for c in d.get("columns", []):
			bag.add(c.get("label"), path)
	elif dt == "Number Card":
		bag.add(d.get("label"), path)
	elif dt == "Dashboard Chart":
		bag.add(d.get("chart_name"), path)


def from_tour(bag, path):
	d = json.load(open(path, encoding="utf-8"))
	for c in d.get("chapters", []):
		bag.add(c, path)
	for s in d.get("steps", []):
		bag.add(s.get("title"), path)
		bag.add(s.get("text"), path)


def from_tests(bag, path):
	d = json.load(open(path, encoding="utf-8"))
	rows = d if isinstance(d, list) else d.get("tests", [])
	for t in rows:
		bag.add(t.get("section"), path)
		bag.add(t.get("role"), path)


def _assign(tree, name):
	for node in tree.body:
		if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
			return ast.literal_eval(node.value)
	return None


def from_navigation(bag, path):
	tree = ast.parse(open(path, encoding="utf-8").read())
	for group, _icon, links in _assign(tree, "NAV") or []:
		bag.add(group, path)
		for link in links:
			bag.add(link[0], path)
	for _entry, rows in (_assign(tree, "NAV_SUB") or {}).items():
		for r in rows:
			bag.add(r[0], path)


def from_features(bag, path):
	tree = ast.parse(open(path, encoding="utf-8").read())
	for f in (_assign(tree, "FEATURES") or {}).values():
		bag.add(f[0], path)
		bag.add(f[1], path)
		bag.add(f[2], path)
	for g in _assign(tree, "GROUPS") or []:
		bag.add(g, path)


def from_hooks(bag, path):
	tree = ast.parse(open(path, encoding="utf-8").read())
	for m in _assign(tree, "portal_menu_items") or []:
		bag.add(m.get("title"), path)


def extract(app):
	pkg = os.path.join(app, "hipersign_trading") if os.path.isdir(os.path.join(app, "hipersign_trading", "hipersign_trading")) else app
	bag = Bag(pkg)
	for p in walk(pkg, (".js",)):
		if "/public/dist/" not in p:
			from_js(bag, p)
	for p in walk(pkg, (".py",)):
		from_py(bag, p)
	for p in walk(pkg, (".html",)):
		from_py(bag, p)  # {{ _("…") }}
		from_js(bag, p)  # inline <script> __("…")
	for p in walk(os.path.join(pkg, "hipersign_trading"), (".json",)):
		from_json(bag, p)
	if os.path.exists(os.path.join(pkg, "tour", "tour.json")):
		from_tour(bag, os.path.join(pkg, "tour", "tour.json"))
	if os.path.exists(os.path.join(pkg, "test_scripts.json")):
		from_tests(bag, os.path.join(pkg, "test_scripts.json"))
	from_navigation(bag, os.path.join(pkg, "navigation.py"))
	from_features(bag, os.path.join(pkg, "features.py"))
	from_hooks(bag, os.path.join(pkg, "hooks.py"))
	return [{"msgid": k, "sources": sorted(v)} for k, v in sorted(bag.d.items())]


if __name__ == "__main__":
	app = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hipersign_trading")
	json.dump(extract(os.path.abspath(app)), sys.stdout, ensure_ascii=False, indent=0)
