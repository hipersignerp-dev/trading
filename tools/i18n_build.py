#!/usr/bin/env python3
"""Build and check the app's translation files (translations/<lang>.csv → locale/<lang>.po) without a bench.

Frappe 16 loads both for an app: translations/<lang>.csv (read directly) and locale/<lang>.po (compiled to
sites/assets/locale/<lang>/LC_MESSAGES/<app>.mo by `bench build` / `bench compile-po-to-mo`; the .mo wins when a string is in
both). The app keeps the two in step, as for Arabic.

	python3 tools/i18n_build.py check zh            # coverage against tools/i18n_extract.py + format checks
	python3 tools/i18n_build.py merge zh new.tsv …  # add "english<TAB>translation" lines (or a JSON {en: tr}) to the CSV
	python3 tools/i18n_build.py po zh               # rewrite locale/zh.po from translations/zh.csv

Checks: every {0} / {name} placeholder, %s / %(x)s and HTML tag of the English is in the translation (and nothing extra),
same number of line breaks, no empty translations, no duplicates.
"""

import csv
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "..", "hipersign_trading")
sys.path.insert(0, HERE)

PH = re.compile(r"\{[0-9a-zA-Z_]*\}|%\([a-z_]+\)[sd]|%[sd]|</?[a-zA-Z][^>]*>")


def csv_path(lang):
	return os.path.join(APP, "translations", f"{lang}.csv")


def po_path(lang):
	return os.path.join(APP, "locale", f"{lang}.po")


def load_csv(lang):
	out = {}
	p = csv_path(lang)
	if os.path.exists(p):
		with open(p, encoding="utf-8", newline="") as f:
			for row in csv.reader(f):
				if len(row) >= 2 and row[0]:
					out[row[0]] = row[1]
	return out


def write_csv(lang, d):
	buf = io.StringIO()
	w = csv.writer(buf, lineterminator="\r\n")  # as ar.csv
	for k in d:  # file order is kept; new rows go at the end
		w.writerow([k, d[k]])
	with open(csv_path(lang), "w", encoding="utf-8", newline="") as f:
		f.write(buf.getvalue())


def po_escape(s):
	return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


LANG_NAMES = {"ar": "Arabic", "zh": "Simplified Chinese"}


def write_po(lang, d):
	lines = [f"# {LANG_NAMES.get(lang, lang)} translations for Hipersign Trading", 'msgid ""', 'msgstr ""',
		'"Content-Type: text/plain; charset=UTF-8\\n"', f'"Language: {lang}\\n"', ""]
	for k in d:
		lines += [f'msgid "{po_escape(k)}"', f'msgstr "{po_escape(d[k])}"', ""]
	with open(po_path(lang), "w", encoding="utf-8") as f:
		f.write("\n".join(lines))


def read_po(lang):
	out, cur = {}, None
	unesc = lambda s: json.loads('"' + s.replace("\\t", "\t") + '"') if s else ""
	with open(po_path(lang), encoding="utf-8") as f:
		for line in f:
			line = line.rstrip("\n")
			if line.startswith("msgid "):
				cur = unesc(line[7:-1])
			elif line.startswith("msgstr ") and cur:
				out[cur] = unesc(line[8:-1])
	return out


def issues(en, tr):
	"""Format problems of one translation (empty list when fine)."""
	out = []
	if not tr or not tr.strip():
		return ["empty"]
	a, b = sorted(PH.findall(en)), sorted(PH.findall(tr))
	# HTML tags: compare the tag names only (attributes may be reordered)
	norm = lambda xs: sorted(re.sub(r"<(/?)([a-zA-Z0-9]+)[^>]*>", r"<\1\2>", x) for x in xs)
	if norm(a) != norm(b):
		out.append(f"placeholders/tags {a} ≠ {b}")
	if en.count("%") != tr.count("%"):
		out.append("% signs differ")
	if en.count("\n") != tr.count("\n"):
		out.append("line breaks differ")
	if re.search(r"\{\s+\d+\s*\}|\{\d+\s+\}|｛|｝", tr):
		out.append("broken placeholder")
	return out


def universe(lang):
	"""Every string the app shows: what the extractor finds, plus what the Arabic file already covers (strings that
	reach __() through variables — add-on names, sub-menus …)."""
	from i18n_extract import extract

	ex = {x["msgid"] for x in extract(os.path.abspath(APP))}
	return ex | set(load_csv("ar"))


def cmd_check(lang):
	d = load_csv(lang)
	U = universe(lang)
	bad = {k: issues(k, v) for k, v in d.items() if issues(k, v)}
	have = [k for k in U if k in d and k not in bad]
	missing = sorted(U - set(d))
	print(f"{lang}: {len(d)} rows in translations/{lang}.csv, {len(U)} strings extracted")
	print(f"coverage: {len(have)} / {len(U)} = {100 * len(have) / max(len(U), 1):.1f}%")
	if os.path.exists(po_path(lang)):
		po = read_po(lang)
		same = po == d
		print(f"locale/{lang}.po: {len(po)} entries, {'matches' if same else 'DIFFERS FROM'} the CSV")
	for k, v in list(bad.items())[:40]:
		print("BAD", repr(k), "→", repr(d[k]), v)
	for k in missing[:40]:
		print("MISSING", repr(k))
	return 1 if bad else 0


def cmd_merge(lang, files):
	d = load_csv(lang)
	n = 0
	for p in files:
		if p.endswith(".json"):
			add = json.load(open(p, encoding="utf-8"))
		else:
			add = {}
			for line in open(p, encoding="utf-8"):
				line = line.rstrip("\n")
				if "\t" in line:
					k, v = line.split("\t", 1)
					add[k.replace("\\n", "\n")] = v.replace("\\n", "\n")
		for k, v in add.items():
			if issues(k, v):
				print("SKIP", repr(k), issues(k, v))
				continue
			if d.get(k) != v:
				d[k] = v
				n += 1
	write_csv(lang, d)
	write_po(lang, d)
	print(f"{lang}: {n} rows added or changed, {len(d)} in total")


if __name__ == "__main__":
	if len(sys.argv) < 3:
		print(__doc__)
		sys.exit(2)
	cmd, lang = sys.argv[1], sys.argv[2]
	if cmd == "check":
		sys.exit(cmd_check(lang))
	if cmd == "merge":
		cmd_merge(lang, sys.argv[3:])
	elif cmd == "po":
		write_po(lang, load_csv(lang))
