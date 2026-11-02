"""v1.8.0 demo data (prototype p19): Hipersign Lighting Industries FZE — a Chinese-owned LED assembler in KEZAD, Abu Dhabi —
joins the demo group. It assembles LED panels, high-bays and drivers from components bought in Shenzhen, Dongguan,
Zhongshan and Ningbo, sells locally and exports to the GCC, so a fresh demo load shows the Manufacturing pages as on the
prototype:

  MSO-2026-0201  Gulf Lighting Distributors   1,500 panels     WO-2026-0141 closed — delivered, invoiced and paid
  MSO-2026-0209  Riyadh Facility Projects       250 high-bays  WO-2026-0145 completed — exported, invoice open (costing)
  MSO-2026-0215  Gulf Lighting Distributors   2,000 panels     WO-2026-0147 late, in final QC, packing still running
  MSO-2026-0218  Golden Dragon Interiors      1,200 panels     WO-2026-0149 in process (400 received), drivers WO-2026-0148 done
  MSO-2026-0221  Doha Electrical Supplies       400 high-bays  WO-2026-0150 on hold — short of heat sinks, air shipment due
  MSO-2026-0224  Muscat Lighting Trading      3,000 drivers    WO-2026-0151 draft, driver PCBs waiting for approval
  MSO-2026-0226  Gulf Lighting Distributors     120 high-bays  forecast — in the next MRP run

Every figure is posted as a real ERPNext document: items with Chinese names, workstations with labour and overhead rates,
operations, routings and BOMs (with a superseded version), opening stock, sales orders, production plans, material requests,
component purchase orders and receipts (a rejected lot of heat sinks), work orders, material transfers to WIP, job cards
with their time, quantities and scrap (some running on the shop floor now), incoming / in-process / final inspections with
test certificates, manufacture entries with batches (finished goods at material + labour + overhead), deliveries,
invoices and a receipt, and the step log of each order. Every step skips what is already there."""

import frappe
from frappe.utils import add_days, add_to_date, cint, flt, get_datetime, getdate, now_datetime, today

CO, ABBR = "Hipersign Lighting Industries FZE", "HLI"
SB, DG, ZS = "Shenzhen Brightway Electronics Co., Ltd.", "Dongguan Lightguide Optics Co., Ltd.", "Zhongshan Guzhen Lighting Parts Factory"
MR, NB, EC = "Shenzhen Mingrui Power Technology Co., Ltd.", "Ningbo Alutech Heatsink Co., Ltd.", "Emirates Carton Industries LLC"
SUPPLIERS = [(SB, "China"), (DG, "China"), (ZS, "China"), (MR, "China"), (NB, "China"), (EC, "United Arab Emirates")]


def D(n):
	return add_days(today(), n)


# code, name, Chinese name, group, uom, cost (None = made in-house), supplier, stock today
ITEMS = [
	("FG-P6060", "LED panel 60×60 cm 40 W", "LED平板灯 60×60厘米 40瓦", "LED Luminaires", "Nos", None, None, 1860),
	("FG-HB150", "LED high-bay 150 W IP65", "LED工矿灯 150瓦 IP65", "LED Luminaires", "Nos", None, None, 95),
	("SA-DRV40", "LED driver unit 40 W", "LED驱动电源 40瓦", "Sub Assemblies", "Nos", None, None, 840),
	("RM-FRM60", "Aluminium frame 60×60 (profiles + corners)", "铝边框 60×60", "LED Components", "Set", 6.8, ZS, 2600),
	("RM-LGP60", "Light guide plate 595×595 PMMA", "导光板 595×595 PMMA", "LED Components", "Nos", 7.9, DG, 2350),
	("RM-DIF60", "Diffuser sheet 595×595", "扩散板 595×595", "LED Components", "Nos", 2.1, DG, 3100),
	("RM-REF60", "Reflector sheet 595×595", "反光纸 595×595", "LED Components", "Nos", 0.9, DG, 3400),
	("RM-LED28", "LED strip SMD2835 600 mm", "LED灯条 SMD2835 600毫米", "LED Components", "Nos", 1.85, SB, 9600),
	("RM-BCV60", "Back cover — galvanised steel", "镀锌钢背板", "LED Components", "Nos", 4.2, ZS, 2480),
	("RM-CBL", "Cable & connector set", "线缆及接插件", "LED Components", "Cable set", 1.1, ZS, 2600),
	("RM-SCR", "Screw & clip kit", "螺丝卡扣包", "LED Components", "Kit", 0.4, ZS, 9000),
	("RM-CTN4", "Carton — 4 panels", "纸箱（4片装）", "Packing Materials", "Carton", 6.4, EC, 900),
	("RM-PCB40", "Driver PCB assembly 40 W", "驱动PCB板 40瓦", "LED Components", "Nos", 4.6, MR, 1800),
	("RM-IND", "Inductor & transformer set", "电感变压器套件", "LED Components", "Set", 1.7, MR, 3400),
	("RM-CAP", "Capacitor kit", "电容套件", "LED Components", "Kit", 1.2, MR, 2100),
	("RM-DHS", "Driver housing PC V0", "驱动外壳 PC V0", "LED Components", "Nos", 0.95, ZS, 4000),
	("RM-HSK150", "Heat sink 150 W die-cast aluminium", "压铸铝散热器 150瓦", "LED Components", "Nos", 38.5, NB, 240),
	("RM-LEDB150", "LED board 150 W SMD3030", "LED灯板 150瓦 SMD3030", "LED Components", "Nos", 29.8, SB, 520),
	("RM-LENS90", "PC lens 90°", "PC透镜 90°", "LED Components", "Nos", 6.2, DG, 610),
	("RM-DRV150", "Driver 150 W IP67 (bought-in)", "驱动电源 150瓦 IP67（外购）", "LED Components", "Nos", 41, MR, 380),
	("RM-HOOK", "Hanging hook & safety rope", "吊钩及安全绳", "LED Components", "Set", 3.1, ZS, 900),
	("RM-CTN1", "Carton — high-bay", "纸箱（工矿灯）", "Packing Materials", "Carton", 4.2, EC, 450),
]
PRICE = {"FG-P6060": 92, "FG-HB150": 265, "SA-DRV40": 24}
# id, name, Chinese, hours a day, labour / h, overhead / h
WORKSTATIONS = [("WS-CUT", "Cutting & profile", "切割及型材", 16, 28, 24), ("WS-SMT", "SMT line", "SMT贴片线", 16, 35, 85), ("WS-ASM", "Assembly line 1", "装配线 1", 16, 28, 20),
	("WS-ASM2", "Assembly line 2 (drivers)", "装配线 2（驱动）", 8, 26, 20), ("WS-WIR", "Wiring bench", "接线工位", 16, 24, 20), ("WS-TST", "Burn-in & test", "老化及测试", 20, 25, 35),
	("WS-PCK", "Packing", "包装", 16, 22, 14)]
# BOM name, item, version, active, default, lines, operations (op, name, workstation, minutes), days ago, change note
BOMS = [
	("BOM-SA-DRV40-003", "SA-DRV40", 3, 1, 1, [("RM-PCB40", 1), ("RM-IND", 1), ("RM-CAP", 1), ("RM-DHS", 1), ("RM-CBL", 0.5)],
		[("SMT & reflow", "WS-SMT", 1.2), ("Assembly & potting", "WS-ASM2", 2), ("Hi-pot & load test", "WS-TST", 1), ("Packing", "WS-PCK", 0.3)], -95,
		"v3: flicker-free IC, potting added for humidity"),
	("BOM-FG-P6060-001", "FG-P6060", 1, 0, 0, [("RM-FRM60", 1), ("RM-LGP60", 1), ("RM-DIF60", 1), ("RM-REF60", 1), ("RM-LED28", 5), ("RM-BCV60", 1), ("SA-DRV40", 1),
		("RM-CBL", 1), ("RM-SCR", 1), ("RM-CTN4", 0.25)], [("Cutting & frame assembly", "WS-CUT", 3), ("LED strip & light-guide assembly", "WS-ASM", 5),
		("Wiring & driver fitting", "WS-WIR", 2.5), ("Burn-in & photometric test", "WS-TST", 1.5), ("Packing & labelling", "WS-PCK", 1)], -420, "First production version"),
	("BOM-FG-P6060-002", "FG-P6060", 2, 1, 1, [("RM-FRM60", 1), ("RM-LGP60", 1), ("RM-DIF60", 1), ("RM-REF60", 1), ("RM-LED28", 4), ("RM-BCV60", 1), ("SA-DRV40", 1),
		("RM-CBL", 1), ("RM-SCR", 1), ("RM-CTN4", 0.25)], [("Cutting & frame assembly", "WS-CUT", 3), ("LED strip & light-guide assembly", "WS-ASM", 4.5),
		("Wiring & driver fitting", "WS-WIR", 2.5), ("Burn-in & photometric test", "WS-TST", 1.5), ("Packing & labelling", "WS-PCK", 1)], -140,
		"v2: 4 LED strips instead of 5 (higher-efficacy SMD2835), same 4,000 lm"),
	("BOM-FG-HB150-001", "FG-HB150", 1, 1, 1, [("RM-HSK150", 1), ("RM-LEDB150", 1), ("RM-LENS90", 1), ("RM-DRV150", 1), ("RM-HOOK", 1), ("RM-CBL", 1), ("RM-SCR", 1),
		("RM-CTN1", 1)], [("Heat sink & LED board assembly", "WS-ASM", 6), ("Wiring & driver fitting", "WS-WIR", 4), ("Burn-in & IP65 test", "WS-TST", 3),
		("Packing & labelling", "WS-PCK", 1.5)], -300, "Alternate: lens 60° (RM-LENS60) approved for warehouses with high racking"),
]
# customer, city, country, export
CUSTOMERS = [("Gulf Lighting Distributors LLC", "Dubai", "United Arab Emirates", 0), ("Doha Electrical Supplies WLL", "Doha", "Qatar", 1),
	("Riyadh Facility Projects Co.", "Riyadh", "Saudi Arabia", 1), ("Muscat Lighting Trading LLC", "Muscat", "Oman", 1), ("Golden Dragon Interiors LLC", "Dubai", "United Arab Emirates", 0)]
# SO, customer, item, qty, ordered, due, step, forecast, note
SOS = [("MSO-2026-0201", 0, "FG-P6060", 1500, -75, -40, 22, 0, None), ("MSO-2026-0209", 2, "FG-HB150", 250, -55, -20, 20, 0, None),
	("MSO-2026-0215", 0, "FG-P6060", 2000, -32, -2, 13, 0, None),
	("MSO-2026-0218", 4, "FG-P6060", 1200, -18, 10, 10, 0, "LED panels for the Business Bay hotel back-of-house — inter-company at cost + 8%"),
	("MSO-2026-0221", 1, "FG-HB150", 400, -9, 18, 5, 0, None), ("MSO-2026-0224", 3, "SA-DRV40", 3000, -4, 25, 4, 0, None),
	("MSO-2026-0226", 0, "FG-HB150", 120, -1, 40, 1, 1, "Forecast — Q1 warehouse retrofit, to confirm")]
# WO, item, qty, start, due, SO, plan, labour factor (actual minutes vs routing)
WOS = [("WO-2026-0141", "FG-P6060", 1500, -68, -45, "MSO-2026-0201", None, 1.06), ("WO-2026-0145", "FG-HB150", 250, -48, -25, "MSO-2026-0209", "PP-2026-010", 0.97),
	("WO-2026-0147", "FG-P6060", 2000, -24, -2, "MSO-2026-0215", "PP-2026-010", 1.05), ("WO-2026-0148", "SA-DRV40", 1200, -20, -8, "MSO-2026-0218", "PP-2026-010", 1.04),
	("WO-2026-0149", "FG-P6060", 1200, -6, 8, "MSO-2026-0218", "PP-2026-011", 1.05), ("WO-2026-0150", "FG-HB150", 400, 6, 16, "MSO-2026-0221", "PP-2026-011", 1),
	("WO-2026-0151", "SA-DRV40", 3000, 10, 22, "MSO-2026-0224", "PP-2026-011", 1)]
OPERATORS = [("Ravi Shankar", "Male"), ("Huang Mei", "Female"), ("Abdul Kareem", "Male"), ("Sanjay Patil", "Male"), ("Maria Santos", "Female"), ("Kumar Velu", "Male"),
	("Zhao Ting", "Female"), ("Joel Fernandes", "Male")]
USERS = [("Chen", "Hao", ["Production Manager", "Manufacturing Manager", "Manufacturing User", "Stock User", "Purchase User"]),
	("Li", "Na", ["QC Inspector", "Quality Manager"])]
# tests printed on the QC certificates (specification, requirement, result)
TESTS = {
	"FG-HB150": [("Luminous flux", "≥ 21,000 lm", "21,640 lm"), ("Power factor", "≥ 0.95", "0.97"), ("IP65 water jet test", "No ingress", "Pass"),
		("Insulation (hi-pot)", "1.5 kV · 60 s", "Pass"), ("Burn-in", "4 h at 45 °C", "Pass")],
	"SA-DRV40": [("Output current", "900 mA ± 3%", "903 mA"), ("Hi-pot", "3.75 kV · 60 s", "Pass"), ("Flicker", "< 3%", "1.2%"), ("Full-load test", "40 W · 2 h", "Pass")],
	"FG-P6060": [("Luminous flux", "≥ 4,000 lm", "4,120 lm"), ("Colour temperature", "4,000 K ± 150", "4,030 K"), ("CRI", "≥ 80", "83"), ("Power factor", "≥ 0.9", "0.95"),
		("Burn-in", "2 h at 40 °C", "Pass"), ("Hi-pot", "1.5 kV · 60 s", "Pass")],
}


def _demo():
	from hipersign_trading import demo

	return demo


def _email(first, last):
	from hipersign_trading.demo.data import DEMO_EMAIL_DOMAIN

	return f"{first.lower()}.{last.lower()}@{DEMO_EMAIL_DOMAIN}"


def _M():
	from hipersign_trading.api import manufacturing as M

	return M


def _series(prefix, cur):
	frappe.db.sql("insert into `tabSeries` (name, current) values (%s, %s) on duplicate key update current = %s", (prefix, cur, cur))


def _bank():
	return frappe.db.get_value("Account", {"company": CO, "account_type": "Bank", "is_group": 0}) or frappe.db.get_value("Account", {"company": CO, "account_type": "Cash", "is_group": 0})


def _cc():
	return frappe.get_cached_value("Company", CO, "cost_center")


# ---------------------------------------------------------------- 1. the company and its people
def mfg_company(c):
	from hipersign_trading.demo.v12 import _company

	_demo().ensure_fiscal_years([D(-200), today()], c.company)
	holding = frappe.db.get_value("Company", c.company, "parent_company")
	co = _company(CO, ABBR, "AED", "United Arab Emirates", parent=holding)
	vals = {"tax_id": "100398452700003"}
	for f, v in (("company_name_in_arabic", "هايبرساين لصناعات الإضاءة م.م.ح"), ("hs_company_name_zh", "海泊信照明工业有限公司（自贸区）"), ("hs_ownership_pct", 100),
			("hs_group_role", "LED lighting assembly — panels, high-bays and drivers from Chinese components"), ("hs_licence_no", "KEZAD 0098214")):
		if co.meta.has_field(f):
			vals[f] = v
	frappe.db.set_value("Company", CO, vals)
	if not frappe.db.exists("Dynamic Link", {"link_doctype": "Company", "link_name": CO, "parenttype": "Address"}):
		frappe.get_doc({"doctype": "Address", "address_title": CO, "address_type": "Office", "address_line1": "Plot KHIA2-03, Khalifa Industrial Zone (KEZAD)",
			"city": "Abu Dhabi", "country": "United Arab Emirates", "is_your_company_address": 1, "links": [{"link_doctype": "Company", "link_name": CO}]}).insert(ignore_permissions=True)
	M = _M()
	M.ensure_setup(CO)
	bank = _bank()
	eq = frappe.db.get_value("Account", {"company": CO, "root_type": "Equity", "is_group": 0, "account_name": ["like", "%Capital%"]}) \
		or frappe.db.get_value("Account", {"company": CO, "root_type": "Equity", "is_group": 0})
	if bank and eq and not frappe.db.exists("Journal Entry", {"company": CO, "user_remark": "Hipersign demo — HLI opening capital"}):
		je = frappe.get_doc({"doctype": "Journal Entry", "company": CO, "posting_date": D(-180), "voucher_type": "Journal Entry", "user_remark": "Hipersign demo — HLI opening capital",
			"accounts": [{"account": bank, "debit_in_account_currency": 2500000, "cost_center": _cc()}, {"account": eq, "credit_in_account_currency": 2500000, "cost_center": _cc()}]})
		je.flags.hs_system_entry = True
		je.insert(ignore_permissions=True)
		je.submit()
	if frappe.get_meta("Hipersign Settings").has_field("feat_manufacturing"):
		frappe.db.set_single_value("Hipersign Settings", "feat_manufacturing", 1)
	# the operators on the shop floor and the two demo users of the prototype (Production Manager, QC Inspector)
	if not frappe.db.exists("Designation", "Operator"):
		frappe.get_doc({"doctype": "Designation", "designation_name": "Operator"}).insert(ignore_permissions=True)
	for i, (n, g) in enumerate(OPERATORS):
		if frappe.db.exists("Employee", {"employee_name": n, "company": CO}):
			continue
		first, last = n.split(" ", 1)
		frappe.get_doc({"doctype": "Employee", "first_name": first, "last_name": last, "gender": g if frappe.db.exists("Gender", g) else None,
			"date_of_birth": f"{1985 + i % 12}-0{1 + i % 9}-1{i % 9}", "date_of_joining": D(-700), "company": CO, "status": "Active", "designation": "Operator"}).insert(ignore_permissions=True)
	for first, last, roles in USERS:
		email = _email(first, last)
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": first, "last_name": last, "send_welcome_email": 0, "user_type": "System User",
				"roles": [{"role": r} for r in roles if frappe.db.exists("Role", r)]}).insert(ignore_permissions=True)
		frappe.defaults.set_user_default("company", CO, email)
		frappe.defaults.set_user_default("hs_scope", f"company:{CO}", email)


# ---------------------------------------------------------------- 2. items, workstations, operations, routings, BOMs, QC templates
def mfg_masters(c):
	for g, parent in (("LED Luminaires", "All Item Groups"), ("Sub Assemblies", "All Item Groups"), ("LED Components", "All Item Groups"), ("Packing Materials", "All Item Groups")):
		if not frappe.db.exists("Item Group", g):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": g, "parent_item_group": parent}).insert(ignore_permissions=True)
	for u, whole in (("Nos", 1), ("Set", 1), ("Kit", 1), ("Carton", 0), ("Cable set", 0)):  # a panel takes a quarter carton, a driver half a cable set
		if not frappe.db.exists("UOM", u):
			frappe.get_doc({"doctype": "UOM", "uom_name": u, "must_be_whole_number": whole}).insert(ignore_permissions=True)
	smeta = frappe.get_meta("Supplier")
	for n, country in SUPPLIERS:
		if frappe.db.exists("Supplier", n):
			continue
		d = {"doctype": "Supplier", "supplier_name": n, "country": country, "supplier_group": "Raw Material" if frappe.db.exists("Supplier Group", "Raw Material")
			else frappe.db.get_value("Supplier Group", {"is_group": 0})}
		for f, v in (("hs_kyc_status", "Verified"), ("hs_trade_licence_expiry", D(300))):
			if smeta.has_field(f):
				d[f] = v
		frappe.get_doc(d).insert(ignore_permissions=True)
	M = _M()
	W = M.whs(CO)
	for code, name, zh, grp, uom, cost, sup, _stock in ITEMS:
		if frappe.db.exists("Item", code):
			continue
		fg = cost is None
		d = {"doctype": "Item", "item_code": code, "item_name": name, "hs_item_name_zh": zh, "item_group": grp, "stock_uom": uom, "is_stock_item": 1,
			"include_item_in_manufacturing": 1, "is_purchase_item": 0 if fg else 1, "is_sales_item": 1 if code in PRICE else 0, "valuation_rate": cost or 0,
			"valuation_method": "Moving Average", "has_batch_no": 1 if code.startswith("FG-") else 0, "create_new_batch": 0, "standard_rate": PRICE.get(code, 0),
			"description": name, "item_defaults": [{"company": CO, "default_warehouse": W.fg if code.startswith("FG-") else W.components, "default_supplier": sup}]}
		frappe.get_doc(d).insert(ignore_permissions=True)
		if code in PRICE and not frappe.db.exists("Item Price", {"item_code": code, "price_list": "Standard Selling"}):
			frappe.get_doc({"doctype": "Item Price", "item_code": code, "price_list": "Standard Selling", "price_list_rate": PRICE[code], "currency": "AED"}).insert(ignore_permissions=True)
	for wid, name, zh, hrs, lab, ovh in WORKSTATIONS:
		if frappe.db.exists("Workstation", name):
			continue
		start = "06:00:00" if hrs >= 16 else "07:00:00"
		end = {16: "22:00:00", 8: "15:00:00", 20: "23:59:00"}[hrs]
		frappe.get_doc({"doctype": "Workstation", "workstation_name": name, "hs_name_zh": zh, "production_capacity": 50, "description": f"{wid} · {name}",
			"working_hours": [{"start_time": start, "end_time": end, "enabled": 1}],
			"workstation_costs": [{"operating_component": "Labour", "operating_cost": lab}, {"operating_component": "Overhead", "operating_cost": ovh}]}).insert(ignore_permissions=True)
	wsname = {w[0]: w[1] for w in WORKSTATIONS}
	for b in BOMS:
		for op, ws, _m in b[6]:
			if not frappe.db.exists("Operation", op):
				frappe.get_doc({"doctype": "Operation", "name": op, "workstation": wsname[ws], "description": op}).insert(ignore_permissions=True, set_name=op)
	for bname, item, ver, active, default, lines, ops, days, note in BOMS:
		if frappe.db.exists("BOM", bname):
			continue
		routing = f"{frappe.db.get_value('Item', item, 'item_name')} — v{ver}"
		if not frappe.db.exists("Routing", routing):
			frappe.get_doc({"doctype": "Routing", "routing_name": routing, "operations": [{"operation": op, "workstation": wsname[ws], "time_in_mins": m, "sequence_id": 0}
				for op, ws, m in ops]}).insert(ignore_permissions=True)
		bom = frappe.get_doc({"doctype": "BOM", "item": item, "company": CO, "quantity": 1, "is_active": 1, "is_default": 0, "with_operations": 1, "routing": routing,
			"rm_cost_as_per": "Valuation Rate", "currency": "AED", "hs_change_note": note,
			"items": [{"item_code": i, "qty": q, "bom_no": frappe.db.get_value("BOM", {"item": i, "is_default": 1, "docstatus": 1}) or None} for i, q in lines],
			"operations": [{"operation": op, "workstation": wsname[ws], "time_in_mins": m} for op, ws, m in ops]})
		bom.insert(ignore_permissions=True, set_name=bname)
		bom.submit()
		frappe.db.set_value("BOM", bname, {"creation": f"{D(days)} 10:00:00"}, update_modified=False)
		if not active:
			frappe.db.set_value("BOM", bname, {"is_active": 0, "is_default": 0})
		if default:
			frappe.db.set_value("BOM", bname, "is_default", 1)
			frappe.db.set_value("Item", item, "default_bom", bname)
	# the final tests per product: a quality inspection template on the item
	for item, tests in TESTS.items():
		tpl = f"{frappe.db.get_value('Item', item, 'item_name')} — final test"
		for spec, _req, _res in tests:
			M._param(spec)
		if not frappe.db.exists("Quality Inspection Template", tpl):
			frappe.get_doc({"doctype": "Quality Inspection Template", "quality_inspection_template_name": tpl,
				"item_quality_inspection_parameter": [{"specification": s, "value": req, "numeric": 0} for s, req, _r in tests]}).insert(ignore_permissions=True)
		frappe.db.set_value("Item", item, "quality_inspection_template", tpl)
	cmeta = frappe.get_meta("Customer")
	for n, city, country, export in CUSTOMERS:
		if frappe.db.exists("Customer", n):
			continue
		d = {"doctype": "Customer", "customer_name": n, "customer_type": "Company", "customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}),
			"territory": frappe.db.get_value("Territory", {"is_group": 0}), "default_currency": "AED"}
		for f, v in (("hs_market", "Export" if export else "Local"), ("hs_kyc_status", "Verified"), ("hs_trade_licence_expiry", D(300)), ("hs_emirate", "Dubai" if not export else None)):
			if cmeta.has_field(f) and v:
				d[f] = v
		cu = frappe.get_doc(d).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Address", "address_title": n, "address_type": "Billing", "address_line1": "P.O. Box " + str(1000 + len(n) * 37), "city": city, "country": country,
			"is_primary_address": 1, "links": [{"link_doctype": "Customer", "link_name": cu.name}]}).insert(ignore_permissions=True)
	M.clear_cache()


# ---------------------------------------------------------------- 3. stock, orders and plans, purchasing — then the shop floor, day by day
def _consumption():
	"""What the demo's work orders take from stock and give to it, per item (so the opening stock lands on today's figures)."""
	M = _M()
	used, made = {}, {}
	for wo, item, qty, start, due, so, pp, lab in WOS:
		if wo in ("WO-2026-0150", "WO-2026-0151"):
			continue
		b = M.bom(M.bom_of(item))
		for r in b.items:
			used[r.item_code] = used.get(r.item_code, 0) + flt(r.qty) * qty
		good = {"WO-2026-0141": 1486, "WO-2026-0145": 247, "WO-2026-0148": 1191, "WO-2026-0149": 400}.get(wo, 0)
		made[item] = made.get(item, 0) + good
	return used, made


RECEIPTS = {"RM-HSK150": 250 + 240, "RM-LGP60": 2000, "RM-LED28": 8000}  # receipts in the demo (accepted units)
DELIVERED = {"FG-P6060": 1500, "FG-HB150": 250}


def mfg_stock(c):
	if frappe.db.exists("Stock Entry", {"company": CO, "remarks": "Hipersign demo — HLI opening stock"}):
		return
	M = _M()
	W = M.whs(CO)
	used, made = _consumption()
	lines = []
	for code, name, zh, grp, uom, cost, sup, stock in ITEMS:
		q = stock + used.get(code, 0) - made.get(code, 0) - RECEIPTS.get(code, 0) + DELIVERED.get(code, 0)
		if code == "RM-HSK150":
			q = 0  # the heat sinks all came in this year (the price increase shows on the high-bay costing)
		if q <= 0:
			continue
		rate = cost if cost is not None else M.std(code).total
		wh = W.fg if code.startswith("FG-") else W.components
		row = {"item_code": code, "qty": q, "t_warehouse": wh, "basic_rate": rate, "set_basic_rate_manually": 1, "cost_center": _cc()}
		if code.startswith("FG-"):
			b = f"B2606-{code.split('-')[1][:3]}-00"
			if not frappe.db.exists("Batch", b):
				frappe.get_doc({"doctype": "Batch", "batch_id": b, "item": code, "manufacturing_date": D(-130)}).insert(ignore_permissions=True)
			row.update({"batch_no": b, "use_serial_batch_fields": 1})
		lines.append(row)
	temp = frappe.db.get_value("Account", {"company": CO, "account_name": ["like", "Temporary Opening%"], "is_group": 0}) \
		or frappe.db.get_value("Account", {"company": CO, "root_type": "Equity", "is_group": 0})
	se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "purpose": "Material Receipt", "company": CO, "posting_date": D(-120),
		"set_posting_time": 1, "remarks": "Hipersign demo — HLI opening stock", "items": lines})
	for r in se.items:
		r.expense_account = temp
	se.insert(ignore_permissions=True, set_name="MAT-OPEN-HLI-001")
	se.submit()


def _so(sid, ci, item, qty, d, due, forecast, note):
	from hipersign_trading.api.create import _tax_template

	cust = CUSTOMERS[ci][0]
	so = frappe.get_doc({"doctype": "Sales Order", "customer": cust, "company": CO, "transaction_date": D(d), "delivery_date": D(due), "po_no": f"PO/{sid[-4:]}",
		"set_warehouse": _M().whs(CO).fg, "hs_mfg_forecast": forecast, "items": [{"item_code": item, "qty": qty, "rate": PRICE[item], "delivery_date": D(due)}],
		"terms": note})
	so.taxes_and_charges = _tax_template(CO, False, cust)
	so.set_missing_values()
	so.set("taxes", [])
	if so.taxes_and_charges:
		so.append_taxes_from_master()
	for i in so.items:
		i.rate = PRICE[item]
	so.insert(ignore_permissions=True, set_name=sid)
	if not forecast:
		so.submit()
	return so


def _plan(name, sos, date):
	M = _M()
	W = M.whs(CO)
	pp = frappe.get_doc({"doctype": "Production Plan", "company": CO, "get_items_from": "Sales Order", "posting_date": D(date), "for_warehouse": W.components})
	for s in sos:
		d = frappe.get_doc("Sales Order", s)
		pp.append("sales_orders", {"sales_order": s, "sales_order_date": d.transaction_date, "customer": d.customer, "grand_total": d.grand_total})
	pp.get_items()
	for r in pp.po_items:
		r.warehouse = W.fg
	pp.insert(ignore_permissions=True, set_name=name)
	pp.submit()
	return pp


def _wo(wo, item, qty, start, due, so, pp, submit, jc_from=None, hold=None):
	M = _M()
	so_item = frappe.db.get_value("Sales Order Item", {"parent": so, "item_code": item}, "name") if so else None
	pp_item = frappe.db.get_value("Production Plan Item", {"parent": pp, "item_code": item, "sales_order": so}) if pp and so_item else None
	if jc_from:
		_series("JC-2026-", jc_from)
	w = M.make_work_order(item, qty, CO, so if so_item else None, so_item, start=D(start), due=D(due), production_plan=pp if pp_item else None, pp_item=pp_item,
		fg_warehouse=M.whs(CO).components if item.startswith("SA-") else None, submit=submit, hold=hold, name=wo)
	if not so_item and so:
		frappe.db.set_value("Work Order", wo, "sales_order", so, update_modified=False)  # the drivers for the panel order (sub-assembly)
	return w


def _ops_done(wo, lab, upto=None, scrap=None, end_day=None, start_day=None, partial=None):
	"""Book the operations of a work order: the time (routing minutes × qty × the labour factor), the quantity and scrap."""
	M = _M()
	w = frappe.get_doc("Work Order", wo)
	scrap = scrap or {}
	start = get_datetime(f"{D(start_day)} 07:00:00")
	n = len(w.operations)
	for k, o in enumerate(w.operations):
		if upto is not None and k >= upto:
			break
		jc = frappe.get_doc("Job Card", frappe.db.get_value("Job Card", {"operation_id": o.name, "docstatus": 0}, "name", order_by="creation asc"))
		jc.hs_scrap_qty = flt(scrap.get(k))
		qty = flt(jc.for_quantity) - M.loss_left(jc)  # the scrap of this operation and the ones before it is lost
		mins = flt(o.time_in_mins) / flt(w.qty) * qty * lab
		t0 = add_to_date(start, hours=k * 20)
		jc.append("time_logs", {"from_time": t0, "to_time": add_to_date(t0, minutes=mins), "time_in_mins": mins, "completed_qty": qty})
		jc.hs_operator = _op(k)
		jc.pending_qty = 0
		jc.sequence_id = 0
		jc.save(ignore_permissions=True)
		jc.submit()
	M.clear_cache()


def _op(k):
	n = OPERATORS[k % len(OPERATORS)][0]
	return frappe.db.get_value("Employee", {"employee_name": n, "company": CO})


def _live(wo, k, done, operator, running_from=None, paused=False, scrap=0, day=-1):
	"""A job card on the shop floor now: done so far (its time at the routing rate), running since a time today, or on hold."""
	M = _M()
	w = frappe.get_doc("Work Order", wo)
	o = w.operations[k]
	jc = frappe.get_doc("Job Card", frappe.db.get_value("Job Card", {"operation_id": o.name, "docstatus": 0}, "name", order_by="creation desc"))
	have = sum(flt(r.completed_qty) for r in jc.time_logs)
	add = flt(done) - have
	if add > 0:
		mins = flt(o.time_in_mins) / flt(w.qty) * add * 1.05
		end = get_datetime(f"{D(day)} 17:00:00")
		jc.append("time_logs", {"from_time": add_to_date(end, minutes=-mins), "to_time": end, "time_in_mins": mins, "completed_qty": add})
	jc.hs_operator = frappe.db.get_value("Employee", {"employee_name": operator, "company": CO})
	jc.hs_scrap_qty = flt(scrap)
	if running_from:
		jc.append("time_logs", {"from_time": get_datetime(f"{today()} {running_from}:00"), "completed_qty": 0})
	jc.is_paused = 1 if paused else 0
	M._keep(jc)
	jc.save(ignore_permissions=True)
	M.clear_cache()
	return jc


def mfg_orders(c):
	if frappe.db.exists("Sales Order", "MSO-2026-0201"):
		return
	M = _M()
	for (sid, ci, item, qty, d, due, step, forecast, note) in SOS:
		if not frappe.db.exists("Sales Order", sid):
			_so(sid, ci, item, qty, d, due, forecast, note)
	_plan("PP-2026-010", ["MSO-2026-0209", "MSO-2026-0215"], -26)
	_plan("PP-2026-011", ["MSO-2026-0218", "MSO-2026-0221", "MSO-2026-0224"], -3)
	M.clear_cache()


def _po(name, item, qty, rate, d, eta, mr=None):
	M = _M()
	mr_item = frappe.db.get_value("Material Request Item", {"parent": mr}, "name") if mr else None
	return M.make_po(item, qty, CO, rate=rate, eta=D(eta), material_request=mr, mr_item=mr_item, name=name, transaction_date=D(d), submit=True)


def mfg_purchasing(c):
	"""Component purchases before production: the heat sinks at the new price (used by the high-bay order)."""
	if frappe.db.exists("Purchase Order", "PO-LI-2026-0101"):
		return
	M = _M()
	_po("PO-LI-2026-0101", "RM-HSK150", 250, 41.0, -62, -52)
	M.receive_po("PO-LI-2026-0101", posting_date=D(-52), name="GRN-LI-0083")


def mfg_production(c):
	"""The work orders day by day — closed, completed, late in final QC, in process, on hold, draft."""
	if frappe.db.exists("Work Order", "WO-2026-0141"):
		return
	M = _M()
	M.ensure_setup(CO)
	# WO-0141: 1,500 panels — transferred, five operations done (14 scrap at burn-in), received, final QC, delivered, invoiced, paid, closed
	_wo("WO-2026-0141", "FG-P6060", 1500, -68, -45, "MSO-2026-0201", None, True, jc_from=569)
	M.transfer("WO-2026-0141", posting_date=D(-67), name="MTW-2026-0498", picked_by="Kumar Velu")
	_ops_done("WO-2026-0141", 1.06, scrap={3: 14}, start_day=-66)
	_final_qi("QI-2026-0298", "WO-2026-0141", "FG-P6060", 1500, 125, 1, -46)
	M.manufacture("WO-2026-0141", posting_date=D(-46), batch="B2609-P60-01", serial_from="HLI-P60-2609120001", name="MFE-2026-0412")
	# WO-0145: 250 high-bays — the heat sinks at the new price; 3 scrap
	_wo("WO-2026-0145", "FG-HB150", 250, -48, -25, "MSO-2026-0209", "PP-2026-010", True, jc_from=579)
	M.transfer("WO-2026-0145", posting_date=D(-47), name="MTW-2026-0507", picked_by="Kumar Velu")
	_ops_done("WO-2026-0145", 0.97, scrap={2: 3}, start_day=-45)
	_final_qi("QI-2026-0305", "WO-2026-0145", "FG-HB150", 250, 32, 0, -27)
	M.manufacture("WO-2026-0145", posting_date=D(-26), batch="B2610-HB-01", serial_from="HLI-HB1-2610070001", name="MFE-2026-0431")
	# incoming inspection of the light-guide plates
	_po("PO-LI-2026-0105", "RM-LGP60", 2000, 7.9, -40, -26)
	M.receive_po("PO-LI-2026-0105", posting_date=D(-26), name="GRN-LI-0087")
	M.make_qi("Incoming", "RM-LGP60", 80, 0, 2000, "Purchase Receipt", "GRN-LI-0087", report_date=D(-26), inspected_by=_li(), name="QI-2026-0301")
	# WO-0147: 2,000 panels — late: four operations done (18 scrap at burn-in), packing running, final QC accepted today
	_wo("WO-2026-0147", "FG-P6060", 2000, -24, -2, "MSO-2026-0215", "PP-2026-010", True, jc_from=593)
	M.transfer("WO-2026-0147", posting_date=D(-23), name="MTW-2026-0520", picked_by="Kumar Velu")
	_ops_done("WO-2026-0147", 1.05, upto=4, scrap={3: 18}, start_day=-22)
	_live("WO-2026-0147", 4, 1940, "Maria Santos", running_from="07:40")
	# WO-0148: 1,200 drivers for the Golden Dragon panels — 9 scrap at the hi-pot test
	_wo("WO-2026-0148", "SA-DRV40", 1200, -20, -8, "MSO-2026-0218", "PP-2026-010", True, jc_from=588)
	M.transfer("WO-2026-0148", posting_date=D(-19), name="MTW-2026-0528", picked_by="Joel Fernandes")
	_ops_done("WO-2026-0148", 1.04, scrap={2: 9}, start_day=-18)
	_final_qi("QI-2026-0299", "WO-2026-0148", "SA-DRV40", 1200, 80, 0, -9, reason="Hi-pot 3.75 kV, 100% load test")
	M.manufacture("WO-2026-0148", posting_date=D(-9), serial_from="HLI-DR4-2610230001", name="MFE-2026-0436")
	# the rejected heat-sink lot (casting porosity): 12 units to the rejects store, debit note to Ningbo Alutech
	_po("PO-LI-2026-0109", "RM-HSK150", 252, 41.0, -30, -12)
	M.receive_po("PO-LI-2026-0109", posting_date=D(-12), rejected=12, name="GRN-LI-0091")
	M.make_qi("Incoming", "RM-HSK150", 20, 3, 252, "Purchase Receipt", "GRN-LI-0091", result="Rejected", rejected=12, report_date=D(-12), inspected_by=_li(),
		reason="Casting porosity on 3 of 20 samples — 12 units rejected, debit note to Ningbo Alutech", name="QI-2026-0302")
	# WO-0149: 1,200 panels for Golden Dragon — 400 received yesterday, the line running today
	_wo("WO-2026-0149", "FG-P6060", 1200, -6, 8, "MSO-2026-0218", "PP-2026-011", True, jc_from=600)
	M.transfer("WO-2026-0149", posting_date=D(-6), name="MTW-2026-0533", picked_by="Kumar Velu")
	_ops_done("WO-2026-0149", 1.04, upto=1, scrap={0: 4}, start_day=-5)
	for k, op in ((1, "Huang Mei"), (2, "Abdul Kareem"), (3, "Sanjay Patil"), (4, "Maria Santos")):
		_live("WO-2026-0149", k, 400, op, day=-2)
	_series("JC-2026-", 610)
	M.manufacture("WO-2026-0149", 400, posting_date=D(-1), batch="B2611-P60-01", serial_from="HLI-P60-2611010001", name="MFE-2026-0440")
	_live("WO-2026-0149", 1, 360, "Huang Mei", running_from="07:30", scrap=2, day=-1)
	_live("WO-2026-0149", 2, 120, "Abdul Kareem", running_from="08:05", day=-1)
	_live("WO-2026-0149", 3, 80, "Sanjay Patil", paused=True, day=-1)
	_live("WO-2026-0149", 4, 0, "Maria Santos", day=-1)
	M.make_qi("In-process", "FG-P6060", 50, 1, 520, work_order="WO-2026-0149", operation="30 · Wiring & driver fitting", rework=12, report_date=D(-1),
		reference_type="Job Card", reference_name=_jc_of("WO-2026-0149", 2), inspected_by=_li(), reason="Loose driver connector — 12 units to rework", name="QI-2026-0303")
	frappe.db.set_value("Quality Inspection", "QI-2026-0303", "hs_rework_done", 4)
	M.make_qi("In-process", "FG-P6060", 80, 0, 480, work_order="WO-2026-0149", operation="40 · Burn-in & photometric test", report_date=today(),
		reference_type="Job Card", reference_name=_jc_of("WO-2026-0149", 3), inspected_by=_li(), name="QI-2026-0306")
	_final_qi("QI-2026-0304", "WO-2026-0147", "FG-P6060", 1960, 125, 2, 0, reason="Within AQL 1.0 (accept ≤ 3)")
	# WO-0150: 400 high-bays released, on hold for heat sinks · WO-0151: 3,000 drivers, draft
	_series("JC-2026-", 605)
	_wo("WO-2026-0150", "FG-HB150", 400, 6, 16, "MSO-2026-0221", "PP-2026-011", True, hold="Short of heat sinks (RM-HSK150)")
	_wo("WO-2026-0151", "SA-DRV40", 3000, 10, 22, "MSO-2026-0224", "PP-2026-011", False)
	_continue_series()
	M.clear_cache()


def _li():
	e = _email("Li", "Na")
	return e if frappe.db.exists("User", e) else "Administrator"


def _jc_of(wo, k):
	op = frappe.get_doc("Work Order", wo).operations[k].name
	return frappe.db.get_value("Job Card", {"operation_id": op}, "name", order_by="creation desc")


def _final_qi(name, wo, item, lot, sample, fails, day, reason=None):
	M = _M()
	w = frappe.get_doc("Work Order", wo)
	last = w.operations[-1].name
	jc = frappe.db.get_value("Job Card", {"operation_id": last}, "name", order_by="creation asc")
	return M.make_qi("Final", item, sample, fails, lot, "Job Card", jc, work_order=wo, report_date=D(day), inspected_by=_li(), reason=reason or "",
		readings=TESTS.get(item), name=name)


def mfg_supply(c):
	"""Material requests from the latest plan and the component purchase orders on the water and in the air."""
	if frappe.db.exists("Material Request", "MMR-2026-071"):
		return
	M = _M()
	for (name, item, qty, need, state, po, mode, d, pp) in (
			("MMR-2026-069", "RM-DRV150", 200, 10, "Ordered", "PO-LI-2026-0114", "Sea", -30, "PP-2026-010"),
			("MMR-2026-073", "RM-CAP", 1000, 9, "Ordered", "PO-LI-2026-0116", "Air", -12, "PP-2026-011"),
			("MMR-2026-071", "RM-HSK150", 200, 5, "Ordered", "PO-LI-2026-0118", "Air", -8, "PP-2026-011"),
			("MMR-2026-072", "RM-PCB40", 1500, 9, "Pending approval", None, "Air", -3, "PP-2026-011")):
		mr = frappe.get_doc({"doctype": "Material Request", "material_request_type": "Purchase", "company": CO, "transaction_date": D(d), "schedule_date": D(need),
			"terms": f"{mode} freight", "items": [{"item_code": item, "qty": qty, "schedule_date": D(need), "warehouse": M.whs(CO).components, "production_plan": pp}]})
		mr.insert(ignore_permissions=True, set_name=name)
		if state != "Pending approval":
			mr.submit()
			eta = {"PO-LI-2026-0114": 6, "PO-LI-2026-0116": 6, "PO-LI-2026-0118": 4}[po]
			_po(po, item, qty, M.leaf_cost(item), d + 2, eta, mr=name)
	# the LED strips that arrived today — the lot is being sampled
	_po("PO-LI-2026-0112", "RM-LED28", 8000, 1.85, -20, 0)
	M.receive_po("PO-LI-2026-0112", posting_date=today(), name="GRN-LI-0094")
	M.make_qi("Incoming", "RM-LED28", 200, 0, 8000, "Purchase Receipt", "GRN-LI-0094", report_date=today(), inspected_by=_li(), submit=False,
		reason="Lot arrived today — sampling", name="QI-2026-0307")


def mfg_sales(c):
	"""Deliveries and invoices: the closed panel order paid, the export high-bays invoiced at 0% and not yet paid."""
	if frappe.db.exists("Delivery Note", "DN-LI-0412"):
		return
	M = _M()
	M.deliver("MSO-2026-0201", posting_date=D(-44), name="DN-LI-0412")
	si = M.invoice("MSO-2026-0201", posting_date=D(-44), name="INV-LI-0388")
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	pe = get_payment_entry("Sales Invoice", si.name)
	pe.posting_date, pe.reference_no, pe.reference_date = D(-14), f"TT/{si.name}", D(-14)
	pe.insert(ignore_permissions=True)
	pe.submit()
	M.deliver("MSO-2026-0209", posting_date=D(-25), name="EXP-LI-0061")
	M.invoice("MSO-2026-0209", posting_date=D(-25), name="INV-LI-0401")
	M.close_wo("WO-2026-0141")


def mfg_steps(c):
	if frappe.db.exists("Manufacturing Step Log", {"sales_order": "MSO-2026-0201"}):
		return
	M = _M()
	from hipersign_trading.demo import user_email

	who = {"Sales Manager": user_email("sm"), "Production Manager": _email("Chen", "Hao"), "QC Inspector": _email("Li", "Na"), "Purchase Manager": user_email("pm"),
		"Stock User": user_email("store"), "Accounts Manager": user_email("fin"), "Logistics Coordinator": user_email("logi")}
	for (sid, ci, item, qty, d, due, step, forecast, note) in SOS:
		frappe.db.set_value("Sales Order", sid, "hs_mfg_step", step, update_modified=False)
		s = frappe.get_doc("Sales Order", sid)
		for i in range(step):
			role = M.STEP_ROLES.get(i, [M.PM])[0]
			u = who.get(role)
			u = u if u and frappe.db.exists("User", u) else "Administrator"
			frappe.get_doc({"doctype": "Manufacturing Step Log", "sales_order": sid, "work_order": M.main_wo(sid), "company": CO, "step": i + 1, "step_name": M.STEPS[i][0],
				"completed_by": u, "completed_on": f"{M._plan_date(s, i)} 10:00:00"}).insert(ignore_permissions=True)
		M.clear_cache()
	_continue_series()
	from hipersign_trading import navigation

	navigation.apply()


def _continue_series():
	"""New records continue after the demo's own numbers (WO-2026-0152, JC-2026-0615, QI-2026-0309 …)."""
	for prefix, dt in (("WO-2026-", "Work Order"), ("JC-2026-", "Job Card"), ("QI-2026-", "Quality Inspection"), ("PP-2026-", "Production Plan"), ("MFE-2026-", "Stock Entry"),
			("MTW-2026-", "Stock Entry")):
		cur = max([cint(n.rsplit("-", 1)[-1]) for n in frappe.get_all(dt, filters={"name": ["like", prefix + "%"]}, pluck="name")] or [0])
		frappe.db.sql("insert into `tabSeries` (name, current) values (%s, %s) on duplicate key update current = greatest(current, %s)", (prefix, cur, cur))


STEPS = [mfg_company, mfg_masters, mfg_stock, mfg_orders, mfg_purchasing, mfg_production, mfg_supply, mfg_sales, mfg_steps]
