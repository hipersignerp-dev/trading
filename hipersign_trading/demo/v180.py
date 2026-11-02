"""v1.8.0 demo data (prototype p19): Golden Dragon Interiors LLC — a Chinese fit-out contractor in Business Bay, Dubai — joins
the demo group with five projects at different stages, so a fresh demo load shows the Projects pages as on the prototype:

  PRJ-2026-014  Business Bay hotel fit-out — 120 rooms   AED 4.2M  step 15 (execution, IPC-08 with the consultant)
  PRJ-2026-016  Jumeirah villa interiors — 6 villas       AED 1.35M step 8  (mobilising, advance received)
  PRJ-2025-009  DIFC office fit-out — Level 14            AED 2.15M step 22 (handover, snags, retention invoice)
  PRJ-2026-019  Al Barsha clinic fit-out                  AED 980K  step 3  (tender being priced, due in 6 days)
  PRJ-2025-004  Marina restaurant fit-out                 AED 760K  step 26 (closed, retention fully released)

Every figure is posted as a real document: contract sales orders, advance / progress / retention invoices with their receipts,
certificates, variations, subcontract orders, claims with their supplier bills and payments, back-charges, material requests,
project POs, receipts and transfers to site, site stock used on the job, bonds (bank guarantees), tasks, crew timesheets, daily
site reports and the cost brought forward per cost head. Every step skips what is already there."""

import frappe
from frappe.utils import add_days, cint, date_diff, flt, getdate, today

CO, ABBR = "Golden Dragon Interiors LLC", "GDI"
H, V, O, C, R = "PRJ-2026-014", "PRJ-2026-016", "PRJ-2025-009", "PRJ-2026-019", "PRJ-2025-004"
SHARE = {"mat": "mat_share", "lab": "lab_share", "sub": "sub_share", "plant": "plant_share", "ovh": "ovh_share"}
HEAD = {"mat": "Materials", "lab": "Labour", "sub": "Subcontract", "plant": "Plant & equipment", "ovh": "Site overheads"}


def D(n):
	return add_days(today(), n)


# id, name, client, consultant, location, contract, ret, adv, dlp, step, enq, award, start, finish, ipcs, cost factors, terms, tender due
PROJECTS = [
	(H, "Business Bay hotel fit-out — 120 rooms", "Bay Crest Hotels LLC", "Meridian Design Consultants", "Business Bay, Dubai", 4200000, 10, 20, 12, 15, -330, -275, -245, 95, 7,
		{"mat": 1.05, "lab": 1.09, "sub": 1, "plant": 1, "ovh": 1.02}, "Monthly progress payments on consultant certificates, 30 days · 20% advance against APG · 10% retention, half at completion, half after 12-month DLP", None),
	(V, "Jumeirah villa interiors — 6 villas", "Palm Vista Developments LLC", "Arcadia Architects", "Jumeirah 2, Dubai", 1350000, 10, 15, 12, 8, -95, -35, -6, 170, 0,
		{}, "15% advance against APG · monthly progress payments, 45 days · 10% retention", None),
	(O, "DIFC office fit-out — Level 14", "Northgate Capital Advisors Ltd", "Studio Lumen Interiors", "DIFC, Dubai", 2150000, 10, 10, 12, 22, -420, -370, -345, -20, 11,
		{"mat": 0.98, "lab": 1.03, "sub": 1.01, "plant": 1, "ovh": 1}, "10% advance · monthly progress payments, 30 days · 10% retention, 5% at completion, 5% after DLP", None),
	(C, "Al Barsha clinic fit-out", "CareWell Medical Centres LLC", "Helix Healthcare Design", "Al Barsha 1, Dubai", 980000, 10, 10, 12, 3, -24, 20, 40, 190, 0,
		{}, "Proposed: 10% advance · monthly progress payments · 10% retention", 6),
	(R, "Marina restaurant fit-out", "Seaside Dining Group LLC", "Meridian Design Consultants", "Dubai Marina", 760000, 10, 20, 12, 26, -760, -720, -700, -480, 7,
		{"mat": 1.02, "lab": 1.04, "sub": 1, "plant": 1, "ovh": 1}, "20% advance · monthly progress payments · 10% retention", None),
]

# project, item, section, section name, description, unit, qty, rate, certified %, shares, measured % (None = certified)
BOQ = [
	(H, "A1", "A", "Preliminaries & general", "Site establishment, CAR insurance & permits", "LS", 1, 145000, 100, {"ovh": .78}, None),
	(H, "A2", "A", "Preliminaries & general", "Site supervision, HSE & cleaning (10 months)", "Month", 10, 38000, 60, {"ovh": .82}, 70),
	(H, "B1", "B", "Guest rooms — 120 keys", "Gypsum ceilings with cove lighting", "m²", 3600, 95, 70, {"mat": .42, "lab": .36}, 78),
	(H, "B2", "B", "Guest rooms — 120 keys", "Vinyl wallcovering & paint", "m²", 9800, 42, 52, {"mat": .45, "lab": .33}, 60),
	(H, "B3", "B", "Guest rooms — 120 keys", "Engineered oak flooring 15 mm", "m²", 3100, 165, 38, {"mat": .62, "lab": .18}, 44),
	(H, "B4", "B", "Guest rooms — 120 keys", "Bathroom porcelain tiling", "m²", 2880, 120, 64, {"mat": .48, "lab": .32}, 71),
	(H, "B5", "B", "Guest rooms — 120 keys", "Joinery — wardrobes, headboards, vanities", "Set", 120, 6850, 35, {"sub": .74}, 41),
	(H, "C1", "C", "Corridors, lobby & public areas", "Feature ceiling & lighting troughs", "m²", 1250, 160, 45, {"mat": .44, "lab": .34}, 55),
	(H, "C2", "C", "Corridors, lobby & public areas", "Marble flooring — lobby", "m²", 620, 410, 20, {"mat": .6, "lab": .2}, 28),
	(H, "C3", "C", "Corridors, lobby & public areas", "Decorative wall panelling", "m²", 540, 290, 10, {"mat": .5, "lab": .3}, 18),
	(H, "D1", "D", "MEP modifications (subcontract)", "Electrical & lighting modifications", "LS", 1, 285000, 55, {"sub": .82}, 62),
	(H, "D2", "D", "MEP modifications (subcontract)", "HVAC grilles, diffusers & re-balancing", "LS", 1, 196000, 48, {"sub": .8}, 55),
	(H, "D3", "D", "MEP modifications (subcontract)", "Fire alarm & sprinkler modifications", "LS", 1, 150500, 40, {"sub": .81}, 46),
	(V, "A1", "A", "Preliminaries", "Mobilisation, site office & insurance", "LS", 1, 60000, 0, {"ovh": .8}, 15),
	(V, "B1", "B", "Joinery", "Kitchens — lacquer & quartz tops", "Set", 6, 68000, 0, {"sub": .76}, None),
	(V, "B2", "B", "Joinery", "Wardrobes & internal doors", "Set", 6, 52000, 0, {"sub": .76}, None),
	(V, "C1", "C", "Finishes", "Marble & oak flooring", "m²", 2100, 175, 0, {"mat": .6, "lab": .2}, None),
	(V, "C2", "C", "Finishes", "Gypsum ceilings & lighting", "m²", 1800, 88, 0, {"mat": .42, "lab": .36}, None),
	(V, "C3", "C", "Finishes", "Painting & wall finishes", "LS", 1, 44100, 0, {"mat": .35, "lab": .45}, None),
	(O, "A1", "A", "Preliminaries", "Preliminaries & site management", "LS", 1, 120000, 100, {"ovh": .8}, None),
	(O, "B1", "B", "Partitions & glazing", "Glass partitions & doors", "m²", 1400, 520, 100, {"sub": .78}, None),
	(O, "C1", "C", "Floors", "Raised floor & carpet tiles", "m²", 2600, 145, 100, {"mat": .58, "lab": .2}, None),
	(O, "D1", "D", "Ceilings & lighting", "Metal ceilings & LED lighting", "m²", 2600, 118, 96, {"mat": .5, "lab": .3}, 100),
	(O, "E1", "E", "Joinery", "Reception desk & pantry joinery", "LS", 1, 286200, 90, {"sub": .75}, 100),
	(O, "F1", "F", "MEP", "MEP modifications & BMS", "LS", 1, 332000, 95, {"sub": .82}, 100),
	(C, "A1", "A", "Preliminaries", "Preliminaries, permits & DHA approvals", "LS", 1, 58000, 0, {"ovh": .8}, None),
	(C, "B1", "B", "Partitions", "Partitions incl. lead-lined X-ray room", "m²", 820, 340, 0, {"mat": .46, "lab": .3}, None),
	(C, "C1", "C", "Floors & ceilings", "Medical-grade vinyl flooring", "m²", 1150, 128, 0, {"mat": .6, "lab": .2}, None),
	(C, "C2", "C", "Floors & ceilings", "Hygienic ceilings", "m²", 1150, 96, 0, {"mat": .48, "lab": .3}, None),
	(C, "D1", "D", "Joinery", "Reception & nurse station joinery", "LS", 1, 165600, 0, {"sub": .74}, None),
	(C, "E1", "E", "MEP", "MEP & medical gas modifications", "LS", 1, 220000, 0, {"sub": .8}, None),
	(R, "A1", "A", "Preliminaries", "Preliminaries", "LS", 1, 45000, 100, {"ovh": .8}, None),
	(R, "B1", "B", "Joinery", "Bar counter, banquettes & joinery", "LS", 1, 248000, 100, {"sub": .76}, None),
	(R, "C1", "C", "Finishes", "Terrazzo flooring", "m²", 480, 310, 100, {"mat": .55, "lab": .24}, None),
	(R, "C2", "C", "Finishes", "Ceilings & feature lighting", "LS", 1, 126200, 100, {"mat": .48, "lab": .3}, None),
	(R, "D1", "D", "MEP", "Kitchen MEP & extract", "LS", 1, 192000, 100, {"sub": .8}, None),
]

# tender no., project, title, client, revision, received, due, value, margin %, status
TENDERS = [
	("TND-2026-031", C, "Al Barsha clinic fit-out", "CareWell Medical Centres LLC", 0, -24, 6, 980000, 17.8, "Being priced"),
	("TND-2026-027", V, "Jumeirah villa interiors — 6 villas", "Palm Vista Developments LLC", 2, -95, -70, 1350000, 16.4, "Awarded"),
	("TND-2026-022", None, "Downtown boutique hotel — lobby & F&B", "Burj Vista Hospitality LLC", 1, -140, -112, 2860000, 15.0, "Lost — price"),
	("TND-2026-029", None, "Silicon Oasis school — science labs", "Oasis Learning Group", 0, -40, -12, 1240000, 16.0, "Submitted"),
	("TND-2026-018", None, "JLT co-working floor", "Lakeside Workspaces FZCO", 1, -180, -160, 690000, 14.2, "Lost — programme"),
	("TND-2025-044", H, "Business Bay hotel fit-out — 120 rooms", "Bay Crest Hotels LLC", 3, -330, -300, 4200000, 17.5, "Awarded"),
	("TND-2025-031", O, "DIFC office fit-out — Level 14", "Northgate Capital Advisors Ltd", 1, -420, -395, 2150000, 16.9, "Awarded"),
	("TND-2024-012", R, "Marina restaurant fit-out", "Seaside Dining Group LLC", 1, -760, -745, 760000, 16.1, "Awarded"),
]

# name, project, description, amount, raised (days), status
VOS = [
	("VO-014-01", H, "Upgrade lobby feature lighting to tunable white", 68500, -150, "Approved"),
	("VO-014-02", H, "Additional minibar joinery units (120 rooms)", 42000, -90, "Approved"),
	("VO-014-03", H, "Guest bathrooms — change to 600×1200 porcelain", 96000, -38, "Pending client"),
	("VO-014-04", H, "Omit wallcovering — level 2 corridors", -18400, -60, "Approved"),
	("VO-014-05", H, "Acoustic insulation to connecting-room walls", 54000, -6, "Draft"),
	("VO-009-01", O, "Glass manifestation & privacy film", 12800, -240, "Approved"),
	("VO-009-02", O, "Additional data points (48 nos)", 21600, -150, "Approved"),
	("VO-004-01", R, "Additional bar back-lighting & shelving", 21400, -560, "Approved"),
]

SUPPLIERS = [
	("Emirates Coolair MEP Contracting LLC", "United Arab Emirates", "Services"), ("Al Noor Woodcraft Joinery LLC", "United Arab Emirates", "Services"),
	("Cedar Glass & Partitions LLC", "United Arab Emirates", "Services"), ("Gulf Gypsum Trading LLC", "United Arab Emirates", "Local"),
	("Guangzhou Huacheng Ceramics Co., Ltd.", "China", "Goods Suppliers"), ("Dubai Marble & Granite LLC", "United Arab Emirates", "Local"),
	("Foshan Lingyun Flooring Co., Ltd.", "China", "Goods Suppliers"), ("Emirates Lighting Profiles LLC", "United Arab Emirates", "Local"),
	("Shanghai Decor Wallcoverings Co., Ltd.", "China", "Goods Suppliers"), ("Gulf Site Cabins LLC", "United Arab Emirates", "Local"),
]
CUSTOMERS = ["Bay Crest Hotels LLC", "Palm Vista Developments LLC", "Northgate Capital Advisors Ltd", "CareWell Medical Centres LLC", "Seaside Dining Group LLC",
	"Burj Vista Hospitality LLC", "Oasis Learning Group", "Lakeside Workspaces FZCO"]

# code, name, uom, valuation rate
ITEMS = [
	("GDI-GYP-125", "Gypsum board 12.5 mm", "Sheet", 24), ("GDI-TILE-T2", "Porcelain tiles 600×600 — Type T-2", "m²", 38),
	("GDI-MARBLE-CAL", "Calacatta marble slabs 20 mm", "m²", 260), ("GDI-OAK-15", "Engineered oak flooring 15 mm", "m²", 96),
	("GDI-LED-24", "LED linear profile 24 V with diffuser", "m", 58), ("GDI-WC-1", "Vinyl wallcovering — Type WC-1", "m²", 19.5),
	("GDI-WC-2", "Vinyl wallcovering — Type WC-2", "m²", 21), ("GDI-CABIN", "Site office cabin & stores racking", "Lot", 18500),
	("GDI-ADH-25", "Tile adhesive 25 kg", "Bag", 21), ("GDI-JNT", "Gypsum jointing compound", "Bag", 16), ("GDI-CTILE", "Replacement ceiling tiles (snags)", "Nos", 60),
]

# PO, project, supplier, item, qty, rate, ordered, state, eta, receive into ("site" / "store" / None), cost head
POS = [
	("PJPO-2026-027", H, "Gulf Gypsum Trading LLC", "GDI-GYP-125", 4000, 24, -118, "Received", -96, "site", "Materials"),
	("PJPO-2026-029", H, "Guangzhou Huacheng Ceramics Co., Ltd.", "GDI-TILE-T2", 3000, 38, -92, "Received", -62, "store", "Materials"),
	("PJPO-2026-030", H, "Dubai Marble & Granite LLC", "GDI-MARBLE-CAL", 320, 260, -26, "Approved", 14, None, "Materials"),
	("PJPO-2026-031", H, "Foshan Lingyun Flooring Co., Ltd.", "GDI-OAK-15", 2200, 96, -38, "Shipped", -2, None, "Materials"),
	("PJPO-2026-033", H, "Emirates Lighting Profiles LLC", "GDI-LED-24", 600, 58, -2, "Pending approval", 16, None, "Materials"),
	("PJPO-2026-034", H, "Shanghai Decor Wallcoverings Co., Ltd.", "GDI-WC-1", 6200, 19.5, -150, "Received", -112, "store", "Materials"),
	("PJPO-2026-036", V, "Gulf Site Cabins LLC", "GDI-CABIN", 1, 18500, -4, "Approved", 3, None, "Site overheads"),
]
# MR, project, BOQ line, item, qty, requested, needed, state, PO
MRS = [
	("PMR-2026-031", H, "B3", "GDI-OAK-15", 900, -40, 12, "Ordered", "PJPO-2026-031"),
	("PMR-2026-032", H, "B4", "GDI-TILE-T2", 1800, -95, -60, "Delivered", "PJPO-2026-029"),
	("PMR-2026-033", H, "B1", "GDI-GYP-125", 4000, -120, -90, "Delivered", "PJPO-2026-027"),
	("PMR-2026-034", H, "B2", "GDI-WC-2", 1800, -3, 20, "Pending approval", None),
	("PMR-2026-035", H, "C2", "GDI-MARBLE-CAL", 320, -30, 15, "Ordered", "PJPO-2026-030"),
	("PMR-2026-036", H, "C1", "GDI-LED-24", 600, -9, 18, "Approved", None),
	("PMR-2026-041", V, "A1", "GDI-CABIN", 1, -5, 3, "Ordered", "PJPO-2026-036"),
]

SCOS = [
	("SCO-2026-007", H, "Emirates Coolair MEP Contracting LLC", "MEP modifications — electrical, HVAC, fire", 520000, -200, "Active", 0),
	("SCO-2026-008", H, "Al Noor Woodcraft Joinery LLC", "Joinery — wardrobes, headboards, vanities (120 rooms)", 610000, -185, "Active", 1),
	("SCO-2025-021", O, "Cedar Glass & Partitions LLC", "Glass partitions & doors", 545000, -330, "Completed", 0),
	("SCO-2026-011", V, "Al Noor Woodcraft Joinery LLC", "Kitchens, wardrobes & doors — 6 villas", 545000, -4, "Pending signature", 0),
]
# order: (claim no, days, claimed to date, certified to date, paid)
CLAIMS = {
	"SCO-2026-007": [(1, -150, 82000, 78000, 1), (2, -120, 168000, 160000, 1), (3, -90, 244000, 236000, 1), (4, -60, 305000, 296000, 1), (5, -30, 356000, 344000, 0), (6, -1, 401000, 0, 0)],
	"SCO-2026-008": [(1, -110, 78000, 74000, 1), (2, -75, 165000, 152000, 1), (3, -40, 222000, 214000, 0)],
	"SCO-2025-021": [(1, -300, 160000, 155000, 1), (2, -270, 330000, 322000, 1), (3, -240, 470000, 462000, 1), (4, -200, 545000, 545000, 1)],
}
BACKS = [("BC-2026-012", "SCO-2026-007", -48, "Repair of gypsum ceiling damaged during re-routing (rooms 512–518)", 4500, "Agreed"),
	("BC-2026-015", "SCO-2026-007", -19, "Site cleaning not done — 3 days, by our labour", 2400, "Disputed"),
	("BC-2026-016", "SCO-2026-008", -12, "Replacement of two damaged wardrobe doors (room 708)", 2800, "Agreed")]

TASKS = [("TSK-1401", H, "Ceilings — guest floors 3–10", -210, 30, 74, "Liu Yang", "B1"), ("TSK-1402", H, "Wallcovering & paint — guest floors", -170, 60, 56, "Liu Yang", "B2"),
	("TSK-1403", H, "Oak flooring — guest floors", -120, 75, 41, "Zhang Wei", "B3"), ("TSK-1404", H, "Bathroom tiling — floors 3–10", -180, 40, 68, "Zhang Wei", "B4"),
	("TSK-1405", H, "Joinery installation (subcontract)", -150, 80, 38, "Wang Lei", "B5"), ("TSK-1406", H, "Lobby feature ceiling & marble", -90, 85, 30, "Liu Yang", "C1"),
	("TSK-1407", H, "MEP modifications (subcontract)", -200, 70, 55, "Wang Lei", "D1"), ("TSK-1408", H, "Snagging — floors 3–4", -10, 20, 15, "Liu Yang", "A2"),
	("TSK-1601", V, "Mobilisation & site set-up", -6, 6, 55, "Liu Yang", "A1"), ("TSK-1602", V, "Kitchen shop drawings & approval", -3, 25, 10, "Wang Lei", "B1"),
	("TSK-0901", O, "Snag closure & as-built drawings", -25, 10, 62, "Zhou Min", "A1")]
SNAGS = [("Scratched glass partition — meeting room 4", "Cedar Glass & Partitions LLC", "Open"), ("Carpet tile lifting near pantry", "Our team", "Completed"),
	("Two downlights flickering — reception", "Our team", "Open"), ("Pantry cabinet door alignment", "Our team", "Completed"), ("BMS sensor not reporting — zone 3", "MEP subcontractor", "Open")]
CREW = [("Zhang Wei", "Foreman", 38, H), ("Li Qiang", "Carpenter", 24, H), ("Huang Jun", "Gypsum fixer", 20, H), ("Ramesh Kumar", "Tiler", 22, H), ("Suresh Babu", "Tiler", 22, H),
	("Mohammed Arif", "Painter", 18, H), ("Imran Khan", "Gypsum fixer", 20, H), ("Joseph Mathew", "Electrician helper", 19, H), ("Chen Bo", "Carpenter", 24, H),
	("Rajesh Nair", "Labourer", 14, H), ("Abdul Rahim", "Labourer", 14, V), ("Wu Gang", "Foreman", 38, V), ("Zhou Min", "Site engineer", 45, O), ("Sunil Thomas", "Painter", 18, O)]
TRADE_TASK = {"Tiler": "TSK-1404", "Carpenter": "TSK-1403", "Gypsum fixer": "TSK-1401", "Painter": "TSK-1402", "Electrician helper": "TSK-1407"}
USERS = [("pjm", "Wang", "Lei", ["Project Manager", "Projects Manager", "Projects User", "Purchase User", "Stock User"]),
	("qs", "Ahmed", "Raza", ["Quantity Surveyor", "Projects User"]), ("site", "Liu", "Yang", ["Site Engineer", "Projects User", "Stock User"])]


def _demo():
	from hipersign_trading import demo

	return demo


def _email(first, last):
	from hipersign_trading.demo.data import DEMO_EMAIL_DOMAIN

	return f"{first.lower()}.{last.lower()}@{DEMO_EMAIL_DOMAIN}"


def _done(doctype, name):
	return frappe.db.exists(doctype, name)


def _bank():
	return frappe.db.get_value("Account", {"company": CO, "account_type": "Bank", "is_group": 0}) or frappe.db.get_value("Account", {"company": CO, "account_type": "Cash", "is_group": 0})


def _cc():
	return frappe.get_cached_value("Company", CO, "cost_center")


# ---------------------------------------------------------------- 1. the company, its taxes, masters and people
def v180_company(c):
	from hipersign_trading.demo.v12 import _company

	_demo().ensure_fiscal_years([D(-800), D(-400), today()], c.company)
	holding = frappe.db.get_value("Company", c.company, "parent_company")
	co = _company(CO, ABBR, "AED", "United Arab Emirates", parent=holding)
	vals = {"tax_id": "100562298400003"}
	for f, v in (("company_name_in_arabic", "التنين الذهبي للديكور الداخلي ذ.م.م"), ("hs_ownership_pct", 100), ("hs_group_role", "Fit-out contractor — hotels, offices, villas and clinics"),
			("hs_licence_no", "DED 1092847")):
		if co.meta.has_field(f):
			vals[f] = v
	frappe.db.set_value("Company", CO, vals)
	if not frappe.db.exists("Dynamic Link", {"link_doctype": "Company", "link_name": CO, "parenttype": "Address"}):
		frappe.get_doc({"doctype": "Address", "address_title": CO, "address_type": "Office", "address_line1": "Bay Square, Building 7", "address_line2": "Business Bay", "city": "Dubai",
			"country": "United Arab Emirates", "is_your_company_address": 1, "links": [{"link_doctype": "Company", "link_name": CO}]}).insert(ignore_permissions=True)
	_vat_templates()
	from hipersign_trading.api.projects import accounts, item

	accounts(CO)
	for k in ("works", "advance", "retention", "variation", "subcontract"):
		item(k)
	abbr = ABBR
	for w in ("Main Store",):
		if not frappe.db.exists("Warehouse", f"{w} - {abbr}"):
			parent = frappe.db.get_value("Warehouse", {"company": CO, "is_group": 1}, "name", order_by="lft asc")
			frappe.get_doc({"doctype": "Warehouse", "warehouse_name": w, "company": CO, "parent_warehouse": parent}).insert(ignore_permissions=True)
	# opening capital in the bank
	bank = _bank()
	eq = frappe.db.get_value("Account", {"company": CO, "root_type": "Equity", "is_group": 0, "account_name": ["like", "%Capital%"]}) \
		or frappe.db.get_value("Account", {"company": CO, "root_type": "Equity", "is_group": 0})
	if bank and eq and not frappe.db.exists("Journal Entry", {"company": CO, "user_remark": "Hipersign demo — GDI opening capital"}):
		je = frappe.get_doc({"doctype": "Journal Entry", "company": CO, "posting_date": D(-790), "voucher_type": "Journal Entry", "user_remark": "Hipersign demo — GDI opening capital",
			"accounts": [{"account": bank, "debit_in_account_currency": 3000000, "cost_center": _cc()}, {"account": eq, "credit_in_account_currency": 3000000, "cost_center": _cc()}]})
		je.flags.hs_system_entry = True
		je.insert(ignore_permissions=True)
		je.submit()
	# the Projects switch is on for the demo (Enterprise has every feature)
	if frappe.get_meta("Hipersign Settings").has_field("feat_projects"):
		frappe.db.set_single_value("Hipersign Settings", "feat_projects", 1)


def _vat_templates():
	for dt, tax_dt, ctype in (("Sales Taxes and Charges Template", "Sales Taxes and Charges", "On Net Total"), ("Purchase Taxes and Charges Template", "Purchase Taxes and Charges", "On Net Total")):
		if frappe.db.exists(dt, {"company": CO, "title": ["like", "%VAT 5%"]}):
			continue
		acc = frappe.db.get_value("Account", {"company": CO, "account_name": ["like", "VAT 5%"], "is_group": 0})
		if not acc:
			parent = frappe.db.get_value("Account", {"company": CO, "account_type": "Tax", "is_group": 1}) or frappe.db.get_value("Account", {"company": CO, "account_name": "Duties and Taxes", "is_group": 1})
			acc = frappe.get_doc({"doctype": "Account", "account_name": "VAT 5%", "company": CO, "parent_account": parent, "account_type": "Tax", "tax_rate": 5}).insert(ignore_permissions=True).name
		frappe.get_doc({"doctype": dt, "title": "UAE VAT 5%", "company": CO, "is_default": 1,
			"taxes": [{"charge_type": ctype, "account_head": acc, "rate": 5, "description": "VAT 5%", "category": "Total", "add_deduct_tax": "Add"}]}).insert(ignore_permissions=True)


def v180_masters(c):
	grp = "Commercial" if frappe.db.exists("Customer Group", "Commercial") else frappe.db.get_value("Customer Group", {"is_group": 0})
	terr = "Dubai" if frappe.db.exists("Territory", "Dubai") else frappe.db.get_value("Territory", {"is_group": 0})
	meta = frappe.get_meta("Customer")
	for n in CUSTOMERS:
		if frappe.db.exists("Customer", n):
			continue
		d = {"doctype": "Customer", "customer_name": n, "customer_type": "Company", "customer_group": grp, "territory": terr}
		for f, v in (("hs_market", "Local"), ("hs_kyc_status", "Verified"), ("hs_trade_licence_expiry", D(300)), ("hs_emirate", "Dubai")):
			if meta.has_field(f):
				d[f] = v
		frappe.get_doc(d).insert(ignore_permissions=True)
	smeta = frappe.get_meta("Supplier")
	for n, country, g in SUPPLIERS:
		if frappe.db.exists("Supplier", n):
			continue
		d = {"doctype": "Supplier", "supplier_name": n, "country": country, "supplier_group": g if frappe.db.exists("Supplier Group", g) else frappe.db.get_value("Supplier Group", {"is_group": 0})}
		for f, v in (("hs_kyc_status", "Verified"), ("hs_trade_licence_expiry", D(300))):
			if smeta.has_field(f):
				d[f] = v
		frappe.get_doc(d).insert(ignore_permissions=True)
	for u in ("m²", "Sheet", "Bag", "Lot", "m", "Set", "LS", "Month"):
		if not frappe.db.exists("UOM", u):
			frappe.get_doc({"doctype": "UOM", "uom_name": u, "must_be_whole_number": 0}).insert(ignore_permissions=True)
	if not frappe.db.exists("Item Group", "Project Materials"):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": "Project Materials", "parent_item_group": "All Item Groups"}).insert(ignore_permissions=True)
	for code, name, uom, rate in ITEMS:
		if not frappe.db.exists("Item", code):
			frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": name, "item_group": "Project Materials", "stock_uom": uom, "is_stock_item": 1, "is_purchase_item": 1,
				"is_sales_item": 0, "valuation_rate": rate, "include_item_in_manufacturing": 0}).insert(ignore_permissions=True)
	if not frappe.db.exists("Task Type", "Snag"):
		frappe.get_doc({"doctype": "Task Type", "name": "Snag", "description": "Snag list item at practical completion"}).insert(ignore_permissions=True, set_name="Snag")
	for a, r in (("Site work", 20), ("Overtime", 25)):
		if not frappe.db.exists("Activity Type", a):
			frappe.get_doc({"doctype": "Activity Type", "activity_type": a, "costing_rate": r, "billing_rate": 0}).insert(ignore_permissions=True)
	# the project team as demo users (roles from the prototype); they see the Golden Dragon company first
	for key, first, last, roles in USERS:
		email = _email(first, last)
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": first, "last_name": last, "send_welcome_email": 0, "user_type": "System User",
				"roles": [{"role": r} for r in roles if frappe.db.exists("Role", r)]}).insert(ignore_permissions=True)
		frappe.defaults.set_user_default("company", CO, email)
		frappe.defaults.set_user_default("hs_scope", f"company:{CO}", email)


def v180_crew(c):
	if frappe.db.exists("Employee", {"company": CO}):
		return
	g = "Male" if frappe.db.exists("Gender", "Male") else None
	for i, (n, trade, rate, pj) in enumerate(CREW):
		if not frappe.db.exists("Designation", trade):
			frappe.get_doc({"doctype": "Designation", "designation_name": trade}).insert(ignore_permissions=True)
		first, last = n.split(" ", 1)
		e = frappe.get_doc({"doctype": "Employee", "first_name": first, "last_name": last, "gender": g, "date_of_birth": f"{1980 + i % 15}-0{1 + i % 9}-1{i % 9}",
			"date_of_joining": D(-900), "company": CO, "status": "Active", "designation": trade})
		e.insert(ignore_permissions=True)
		for act, r in (("Site work", rate), ("Overtime", flt(rate * 1.25, 2))):
			frappe.get_doc({"doctype": "Activity Cost", "activity_type": act, "employee": e.name, "costing_rate": r, "billing_rate": 0}).insert(ignore_permissions=True)


# ---------------------------------------------------------------- 2. projects, BOQs, variations, contracts and bonds
def v180_projects(c):
	from hipersign_trading.api import projects as P

	for (pid, name, client, cons, loc, cv, ret, adv, dlp, step, enq, award, start, finish, ipcs, f, terms, due) in PROJECTS:
		if frappe.db.exists("Project", pid):
			continue
		p = frappe.get_doc({"doctype": "Project", "project_name": name, "company": CO, "customer": client, "status": "Completed" if step >= 26 else "Open",
			"expected_start_date": D(start), "expected_end_date": D(finish), "percent_complete_method": "Manual", "cost_center": _cc(),
			"hs_contract_value": cv, "hs_retention_pct": ret, "hs_advance_pct": adv, "hs_dlp_months": dlp, "hs_step": step, "hs_consultant": cons, "hs_location": loc,
			"hs_project_manager": "Wang Lei", "hs_quantity_surveyor": "Ahmed Raza", "hs_site_engineer": "Zhou Min" if pid in (O, R) else "Liu Yang",
			"hs_enquiry_date": D(enq), "hs_tender_due": D(due) if due is not None else None, "hs_award_date": D(award) if step >= 5 else None, "hs_payment_terms": terms})
		p.insert(ignore_permissions=True, set_name=pid)
	for (tno, pj, title, client, rev, recv, due, value, margin, status) in TENDERS:
		if frappe.db.exists("Project BOQ", tno):
			continue
		ls = [b for b in BOQ if b[0] == pj] if pj else []
		b = frappe.get_doc({"doctype": "Project BOQ", "title": title, "project": pj, "customer": client if frappe.db.exists("Customer", client) else None, "client_name": client, "company": CO,
			"status": status, "revision": rev, "received_on": D(recv), "due_date": D(due), "tender_value": value, "margin_pct": margin, "target_margin": 17, "overhead_pct": 4,
			"notes": "Excludes authority fees, loose furniture and artwork. Validity 60 days.",
			"items": [{"section": sec, "section_name": sn, "item_no": no, "description": desc, "unit": unit, "qty": qty, "rate": rate, "certified_pct": pct,
				"measured_pct": pct if now is None else now, **{SHARE[k]: v * 100 for k, v in sh.items()}} for (_p, no, sec, sn, desc, unit, qty, rate, pct, sh, now) in ls]})
		b.insert(ignore_permissions=True, set_name=tno)
		if not ls:
			frappe.db.set_value("Project BOQ", tno, {"tender_value": value, "margin_pct": margin})
	for (vo, pj, title, amt, d, status) in VOS:
		if frappe.db.exists("Variation Order", vo):
			continue
		v = frappe.get_doc({"doctype": "Variation Order", "project": pj, "company": CO, "title": title, "amount": amt, "status": status, "raised_on": D(d), "raised_by": "Ahmed Raza",
			"reason": "Omission" if amt < 0 else "Client instruction", "instruction_ref": f"SI-{vo[-6:]}", "sent_on": D(d) if status in ("Pending client", "Approved") else None,
			"approved_on": D(d + 9) if status == "Approved" else None})
		v.insert(ignore_permissions=True, set_name=vo)
	for pj in (H, V, O, C, R):
		P.update_revised_contract(pj)
	_series()
	# contract sales orders (step 6 done)
	from hipersign_trading.api.projects import item

	for (pid, name, client, *_r) in PROJECTS:
		p = frappe.get_doc("Project", pid)
		if cint(p.hs_step) < 6 or p.sales_order:
			continue
		award = getdate(p.hs_award_date)
		so = frappe.get_doc({"doctype": "Sales Order", "customer": client, "company": CO, "project": pid, "transaction_date": add_days(award, 6), "po_no": f"LOA/{pid}",
			"delivery_date": p.expected_end_date, "items": [{"item_code": item("works"), "qty": 1, "rate": flt(p.hs_contract_value), "delivery_date": p.expected_end_date, "project": pid,
				"description": f"{p.project_name} — contract works as per the contract BOQ"}]})
		so.taxes_and_charges = P._vat_template(CO)[0]
		so.set_missing_values()
		so.set("taxes", [])
		if so.taxes_and_charges:
			so.append_taxes_from_master()
		so.insert(ignore_permissions=True)
		so.submit()
		frappe.db.set_value("Project", pid, "sales_order", so.name, update_modified=False)


def _series():
	"""New records continue after the demo's own numbers (PRJ-2026-020, TND-2026-032, SCO-2026-012, BC-2026-017)."""
	for prefix, cur in (("PRJ-2026-", 19), ("PRJ-2025-", 9), ("TND-2026-", 31), ("TND-2025-", 44), ("TND-2024-", 12), ("SCO-2026-", 11), ("SCO-2025-", 21), ("BC-2026-", 16)):
		frappe.db.sql("insert into `tabSeries` (name, current) values (%s, %s) on duplicate key update current = greatest(current, %s)", (prefix, cur, cur))


def v180_bonds(c):
	if not frappe.db.exists("DocType", "Bank Guarantee") or frappe.db.exists("Bank Guarantee", {"project": H}):
		return
	bank = "Emirates NBD" if frappe.db.exists("Bank", "Emirates NBD") else frappe.db.get_value("Bank", {}) or frappe.get_doc({"doctype": "Bank", "bank_name": "Emirates NBD"}).insert().name
	for (pid, name, client, cons, loc, cv, ret, adv, dlp, step, enq, award, start, finish, *_r) in PROJECTS:
		if step < 7:
			continue
		apg_exp = D(21) if pid == H else add_days(D(finish), -30) if step >= 21 else D(240)
		for kind, no, amt, exp, state in (("Advance payment guarantee", f"APG-{pid[-3:]}-ENBD", cv * adv / 100, apg_exp, "Returned" if step >= 21 else "Active"),
				("Performance bond", f"PB-{pid[-3:]}-ENBD", cv * 0.1, D(-60) if step >= 26 else add_days(D(finish), 400), "Returned" if step >= 26 else "Active")):
			start_d = D(award + 10)
			bg = frappe.get_doc({"doctype": "Bank Guarantee", "bg_type": "Providing", "customer": client, "project": pid, "amount": amt, "start_date": start_d,
				"validity": date_diff(exp, start_d), "end_date": exp, "bank": bank, "bank_guarantee_number": no, "name_of_beneficiary": client,
				"hs_bond_type": kind, "hs_bond_status": state, "more_information": f"{kind} for {pid} — {name}"})
			bg.insert(ignore_permissions=True)
			bg.submit()
			frappe.db.set_value("Bank Guarantee", bg.name, "end_date", exp, update_modified=False)


# ---------------------------------------------------------------- 3. billing: advance, certificates, progress invoices, receipts, retention
def _work(pid, now=False):
	"""BOQ work done: certified % (now=False) or measured % (now=True)."""
	return sum(b[6] * b[7] * (b[10] if now and b[10] is not None else b[8]) / 100 for b in BOQ if b[0] == pid)


def v180_billing(c):
	from hipersign_trading.api import projects as P

	if frappe.db.exists("Sales Invoice", {"project": H, "hs_project_bill": "Advance", "docstatus": 1}):
		return
	for (pid, name, client, cons, loc, cv, ret, adv, dlp, step, enq, award, start, finish, n, f, terms, due) in PROJECTS:
		if step < 8:
			continue
		P.clear_cache()
		si = P.make_advance_invoice(pid, posting_date=D(award + 12))
		P.receive(si.name, posting_date=D(award + 18), reference=f"TT/ADV/{pid[-3:]}")
		work = _work(pid)
		vo = sum(v[3] for v in VOS if v[1] == pid and v[5] == "Approved")
		frac = work / cv
		top = min(date_diff(today(), D(start)) - 30, (finish - start) + 20)
		boq = frappe.get_doc("Project BOQ", frappe.db.get_value("Project BOQ", {"project": pid, "status": "Awarded"}))
		prev_ratio = 0
		for k in range(1, n + 1):
			ratio = (k / n) ** 1.12
			cum = flt((work + vo * frac) * ratio, 2)
			off = round(35 + (k - 1) * ((top - 35) / max(1, n - 1)))
			date = D(-30) if k == n and step < 21 else add_days(D(start), off)
			ipc = frappe.get_doc({"doctype": "Progress Certificate", "project": pid, "company": CO, "certificate_no": k, "status": "Certified", "period_to": add_days(date, -2),
				"measured_on": add_days(date, -6), "certified_on": date, "consultant": cons, "basis": "% complete", "work_to_date": cum,
				"items": [{"item_no": r.item_no, "description": r.description, "amount": r.amount, "previous_pct": flt(r.certified_pct * prev_ratio, 1), "cumulative_pct": flt(r.certified_pct * ratio, 1),
					"this_period_amount": flt(r.amount * r.certified_pct * (ratio - prev_ratio) / 100, 2), "to_date_amount": flt(r.amount * r.certified_pct * ratio / 100, 2)} for r in boq.items]})
			ipc.boq_work_to_date = flt(sum(x["to_date_amount"] for x in ipc.as_dict()["items"]), 2)
			ipc.variations_to_date = flt(cum - ipc.boq_work_to_date, 2)
			ipc.flags.hs_keep = True
			ipc.insert(ignore_permissions=True, set_name=f"IPC-{pid[-3:]}-{k:02d}")
			inv_date = add_days(date, 4)
			due_days = 30 if not (pid == H and k == 6) else date_diff(D(-12), inv_date)
			P.clear_cache()
			# the invoice from the certificate (the same function as the Create invoice button)
			si = _progress_invoice(P, ipc.name, inv_date, due_days)
			if pid == H and k == 6:
				P.receive(si.name, posting_date=add_days(inv_date, 40), amount=flt(si.grand_total * 0.6, 2), reference=f"TT/{si.name}/P1")
			elif date_diff(today(), inv_date) >= 38:
				P.receive(si.name, posting_date=add_days(inv_date, 36), reference=f"TT/{si.name}")
			prev_ratio = ratio
		# the next certificate is measured and with the consultant (from the BOQ measurement)
		if 14 <= step < 21:
			ipc = frappe.get_doc({"doctype": "Progress Certificate", "project": pid, "company": CO, "certificate_no": n + 1, "status": "Submitted to consultant", "period_to": D(-2),
				"measured_on": D(-3), "consultant": cons, "basis": "% complete"})
			ipc.insert(ignore_permissions=True, set_name=f"IPC-{pid[-3:]}-{n + 1:02d}")
		P.clear_cache()
		if step >= 22:
			held = P.fig(pid).ret_held
			half = flt(held / 2, 2)
			if step >= 26:
				r1 = P.make_retention_invoice(pid, half, posting_date=D(finish + 20), label="Retention released — 50% on practical completion")
				P.receive(r1.name, posting_date=D(finish + 48), reference=f"TT/{r1.name}")
				P.clear_cache()
				r2 = P.make_retention_invoice(pid, flt(held - half, 2), posting_date=D(-115), label="Retention released — balance after the defects liability period")
				P.receive(r2.name, posting_date=D(-60), reference=f"TT/{r2.name}")
			else:
				P.make_retention_invoice(pid, half, posting_date=D(-10), label="Retention released — 50% on practical completion")


def _progress_invoice(P, ipc_name, posting_date, due_days):
	"""make_progress_invoice with the demo's own due date (the hotel's sixth invoice is overdue)."""
	orig = P._si

	def si(*a, **kw):
		kw["due_days"] = due_days
		return orig(*a, **kw)

	P._si = si
	try:
		return P.make_progress_invoice(ipc_name, posting_date=posting_date)
	finally:
		P._si = orig


# ---------------------------------------------------------------- 4. subcontractors: orders, back-charges, claims, bills, payments
def v180_subcontracts(c):
	from hipersign_trading.api import projects as P

	if frappe.db.exists("Subcontract Order", "SCO-2026-007"):
		return
	for (sid, pj, sup, pkg, value, d, status, behind) in SCOS:
		frappe.get_doc({"doctype": "Subcontract Order", "project": pj, "company": CO, "supplier": sup, "package": pkg, "order_value": value, "retention_pct": 10, "order_date": D(d),
			"start_date": D(d + 10), "status": status, "behind_programme": behind, "programme_note": "Joinery doors for floor 8 delayed; recovery plan requested." if behind else None,
			"terms": "Monthly claims, certified by our QS within 7 days, paid 30 days after certification · 10% retention"}).insert(ignore_permissions=True, set_name=sid)
	for (bid, sco, d, reason, amt, st) in BACKS:
		frappe.get_doc({"doctype": "Back Charge", "subcontract_order": sco, "company": CO, "date": D(d), "reason": reason, "amount": amt, "status": st}).insert(ignore_permissions=True, set_name=bid)
	for sco, rows in CLAIMS.items():
		for (no, d, claimed, cert, paid) in rows:
			name = f"{sco.replace('SCO', 'SCC')}-{no:02d}"
			cl = frappe.get_doc({"doctype": "Subcontract Claim", "subcontract_order": sco, "company": CO, "claim_no": no, "claim_date": D(d), "claimed_to_date": claimed,
				"certified_to_date": cert or 0, "status": "Submitted"})
			cl.flags.hs_no_bc = True
			cl.insert(ignore_permissions=True, set_name=name)
			if not cert:
				continue
			for b in frappe.get_all("Back Charge", filters={"subcontract_order": sco, "status": "Agreed", "deducted_in": ["is", "not set"], "date": ["<=", D(d)]}, pluck="name"):
				frappe.db.set_value("Back Charge", b, {"status": "Deducted", "deducted_in": name})
			cl.reload()
			cl.status = "Certified"
			cl.save(ignore_permissions=True)
			pi = P.make_claim_bill(name, posting_date=D(d + 5))
			if paid:
				P.pay(pi.name, posting_date=D(d + 32), reference=f"PAY/{name}")
				frappe.db.set_value("Subcontract Claim", name, {"status": "Paid", "paid_on": D(d + 32)})


# ---------------------------------------------------------------- 5. site: material requests, POs, receipts, transfers, use and returns
def _se(purpose, lines, date, project, name, remarks=None, mr=None):
	se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": purpose, "purpose": purpose, "company": CO, "posting_date": D(date), "set_posting_time": 1, "project": project,
		"remarks": remarks, "items": []})
	from hipersign_trading.api.projects import accounts

	acc = accounts(CO)
	for (item, qty, s, t, rate) in lines:
		row = {"item_code": item, "qty": qty, "s_warehouse": s, "t_warehouse": t, "project": project, "cost_center": _cc()}
		if purpose == "Material Receipt":
			row["basic_rate"] = rate
			row["set_basic_rate_manually"] = 1
		if purpose == "Material Issue":
			row["expense_account"] = acc.heads["Materials"]
		if mr:
			row["material_request"] = mr[0]
			row["material_request_item"] = mr[1]
		se.append("items", row)
	se.insert(ignore_permissions=True, set_name=name)
	se.submit()
	return se


def v180_site(c):
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	from hipersign_trading.api import projects as P

	if frappe.db.exists("Purchase Order", "PJPO-2026-027"):
		return
	store = P.main_store(CO)
	site = {pj: P.site_warehouse(pj) for pj in (H, V, O)}
	mr_item = {}
	for (mid, pj, line, item, qty, d, need, state, po) in MRS:
		mr = frappe.get_doc({"doctype": "Material Request", "material_request_type": "Purchase", "company": CO, "transaction_date": D(d), "schedule_date": D(need), "hs_project": pj,
			"items": [{"item_code": item, "qty": qty, "schedule_date": D(need), "warehouse": site[pj], "project": pj, "hs_boq_item": line}]})
		mr.insert(ignore_permissions=True, set_name=mid)
		if state != "Pending approval":
			mr.submit()
		mr_item[mid] = mr.items[0].name
	for (po_name, pj, sup, item, qty, rate, d, state, eta, into, head) in POS:
		mr = next((m for m in MRS if m[8] == po_name), None)
		wh = site[pj] if into != "store" else store
		lines = []
		if mr:
			lines.append({"item_code": item, "qty": min(qty, mr[4]), "rate": rate, "schedule_date": D(eta), "warehouse": wh, "project": pj, "material_request": mr[0], "material_request_item": mr_item[mr[0]]})
		if not mr or qty > mr[4]:
			lines.append({"item_code": item, "qty": qty - (mr[4] if mr else 0), "rate": rate, "schedule_date": D(eta), "warehouse": wh, "project": pj})
		po = frappe.get_doc({"doctype": "Purchase Order", "supplier": sup, "company": CO, "transaction_date": D(d), "schedule_date": D(eta), "hs_project": pj, "hs_cost_head": head,
			"set_warehouse": wh, "items": lines})
		po.set_missing_values()
		po.insert(ignore_permissions=True, set_name=po_name)
		if state == "Pending approval":
			continue
		po.submit()
		if state == "Received":
			pr = make_purchase_receipt(po.name)
			pr.posting_date, pr.set_posting_time, pr.project = D(eta), 1, pj
			for i in pr.items:
				i.warehouse = wh
				i.project = pj
			pr.insert(ignore_permissions=True, set_name={"PJPO-2026-027": "SDN-2026-101", "PJPO-2026-029": "GRN-2026-0129", "PJPO-2026-034": "GRN-2026-0134"}[po_name])
			pr.submit()
	# from the main store to site, materials from stock, the job using them, returns
	_se("Material Transfer", [("GDI-WC-1", 6200, store, site[H], 0)], -110, H, "SDN-2026-114", "Delivery to site — main store (Al Quoz)")
	_se("Material Transfer", [("GDI-TILE-T2", 1800, store, site[H], 0)], -60, H, "SDN-2026-122", "Delivery to site — main store (Al Quoz)")
	_se("Material Transfer", [("GDI-TILE-T2", 1200, store, site[H], 0)], -45, H, "SDN-2026-131", "Delivery to site — main store (Al Quoz)")
	_se("Material Receipt", [("GDI-ADH-25", 900, None, site[H], 21), ("GDI-JNT", 520, None, site[H], 16)], -100, H, "SRC-2026-021", "Site consumables bought locally")
	_se("Material Issue", [("GDI-GYP-125", 2860, site[H], None, 0), ("GDI-WC-1", 5100, site[H], None, 0), ("GDI-TILE-T2", 1830, site[H], None, 0),
		("GDI-ADH-25", 610, site[H], None, 0), ("GDI-JNT", 455, site[H], None, 0)], -16, H, "SIS-2026-044", "Issued to installation (daily site reports)")
	_se("Material Transfer", [("GDI-TILE-T2", 42, site[H], store, 0)], -41, H, "SRT-2026-007", "Chipped edges — returned to Guangzhou Huacheng Ceramics (credit note received)")
	_se("Material Transfer", [("GDI-GYP-125", 120, site[H], store, 0)], -14, H, "SRT-2026-009", "Surplus after floors 3–6 — back to the main store")
	# DIFC snag tiles from the main store (material transfer request)
	_se("Material Receipt", [("GDI-CTILE", 40, None, store, 60)], -8, None, "SRC-2026-022", "Replacement ceiling tiles — stock")
	mr = frappe.get_doc({"doctype": "Material Request", "material_request_type": "Material Transfer", "company": CO, "transaction_date": D(-7), "schedule_date": D(2), "hs_project": O,
		"set_from_warehouse": store, "items": [{"item_code": "GDI-CTILE", "qty": 40, "schedule_date": D(2), "warehouse": site[O], "from_warehouse": store, "project": O, "hs_boq_item": "D1"}]})
	mr.insert(ignore_permissions=True, set_name="PMR-2026-038")
	mr.submit()
	_se("Material Transfer", [("GDI-CTILE", 40, store, site[O], 0)], -6, O, "SDN-2026-140", "Snag materials to site — main store (Al Quoz)", mr=(mr.name, mr.items[0].name))
	_se("Material Issue", [("GDI-CTILE", 26, site[O], None, 0)], -3, O, "SIS-2026-047", "Snag repairs")


# ---------------------------------------------------------------- 6. tasks, snags, crew timesheets, daily site reports
def v180_tasks(c):
	if frappe.db.exists("Task", {"project": H}):
		return
	for (tid, pj, name, s, e, pct, owner, line) in TASKS:
		t = frappe.get_doc({"doctype": "Task", "subject": name, "project": pj, "exp_start_date": D(s), "exp_end_date": min(getdate(D(e)), getdate(frappe.db.get_value("Project", pj, "expected_end_date"))),
			"progress": pct, "status": "Working", "hs_task_owner": owner, "hs_boq_item": line, "company": CO})
		t.insert(ignore_permissions=True, set_name=tid)
	for i, (t, by, st) in enumerate(SNAGS, 1):
		frappe.get_doc({"doctype": "Task", "subject": t, "project": O, "type": "Snag", "status": "Open", "hs_task_owner": by, "company": CO}).insert(ignore_permissions=True, set_name=f"SNG-090{i}")
		if st == "Completed":
			frappe.db.set_value("Task", f"SNG-090{i}", {"status": "Completed", "progress": 100, "completed_on": D(-5)}, update_modified=False)
	for (pj, d, man, sub, done, issues, by) in [
			(H, -1, 46, 22, "Floor 7 ceilings boarded; floor 5 flooring 60% laid; lobby marble setting-out", f"Marble slabs delivery confirmed for {getdate(D(14)).strftime('%d %b')}; joinery doors for floor 8 delayed by subcontractor", "Liu Yang"),
			(H, -2, 44, 20, "Floor 6 wallcovering complete; bathroom tiling floor 9 started", "Water leak from level 9 riser — reported to building management", "Liu Yang"),
			(V, -1, 6, 0, "Site office cabin delivered; protection to existing floors", "Community access permit for villa 4 awaited", "Wu Gang")]:
		frappe.get_doc({"doctype": "Daily Site Report", "project": pj, "company": CO, "report_date": D(d), "manpower_own": man, "manpower_sub": sub, "work_done": done, "issues": issues,
			"reported_by": by}).insert(ignore_permissions=True)


def v180_timesheets(c):
	if frappe.db.exists("Timesheet", {"parent_project": H}) or not frappe.db.exists("Employee", {"company": CO}):
		return
	emps = {frappe.db.get_value("Employee", {"employee_name": n, "company": CO}): (n, trade, rate, pj) for (n, trade, rate, pj) in CREW}
	tasks = {pj: [t[0] for t in TASKS if t[1] == pj] for pj in (H, V, O)}
	for k, (emp, (n, trade, rate, pj)) in enumerate(emps.items()):
		for submitted, days in ((True, range(-20, -2)), (False, range(-2, 0))):
			logs = []
			for d in days:
				dt = getdate(D(d))
				if dt.weekday() == 6 or (pj == V and d < -6):
					continue
				# DIFC is past its completion date: snag hours go to the project (a task there cannot run past the project end)
				task = None if pj == O else TRADE_TASK.get(trade) if pj == H and trade in TRADE_TASK else tasks[pj][(k + d) % len(tasks[pj])]
				logs.append({"activity_type": "Site work", "from_time": f"{dt} 07:00:00", "to_time": f"{dt} 15:00:00", "hours": 8, "project": pj, "task": task, "costing_rate": rate,
					"is_billable": 0})
				if (k + d) % 4 == 0:
					logs.append({"activity_type": "Overtime", "from_time": f"{dt} 15:00:00", "to_time": f"{dt} 17:00:00", "hours": 2, "project": pj, "task": task,
						"costing_rate": flt(rate * 1.25, 2), "is_billable": 0})
			if not logs:
				continue
			ts = frappe.get_doc({"doctype": "Timesheet", "employee": emp, "company": CO, "parent_project": pj, "time_logs": logs,
				"note": "Site timesheet — " + ("approved by the project manager" if submitted else "submitted for approval")})
			ts.insert(ignore_permissions=True)
			if submitted:
				ts.submit()


# ---------------------------------------------------------------- 7. cost brought forward per cost head, the step log
def v180_costs(c):
	"""The cost booked before the documents above (earlier months): per project and cost head, what the prototype's forecast
	figures need on top of what the receipts, issues, bills and timesheets already booked."""
	from hipersign_trading.api import projects as P

	if frappe.db.exists("Journal Entry", {"company": CO, "user_remark": ["like", "Hipersign demo — cost brought forward%"]}):
		return
	acc = P.accounts(CO)
	bank = _bank()
	for (pid, name, client, cons, loc, cv, ret, adv, dlp, step, enq, award, start, finish, n, f, terms, due) in PROJECTS:
		if step < 8:
			continue
		target = {k: 0.0 for k in HEAD}
		for b in [x for x in BOQ if x[0] == pid]:
			pct = 1 if step >= 26 else (b[8] if b[10] is None else b[10]) / 100
			for k, s in b[9].items():
				target[k] += b[6] * b[7] * s * pct * f.get(k, 1)
		if step >= 10:
			target["plant"] += cv * P.PLANT_PCT / 100 * (1 if step >= 26 else _work(pid, True) / cv)
		P.clear_cache()
		have = P._gl_by_head(pid, CO)
		have["Labour"] += P.timesheet_cost(pid)
		end = min(getdate(today()), getdate(D(finish)))
		mid = add_days(D(start), max(1, int(date_diff(end, D(start)) * 0.55))) if step >= 10 else D(-3)
		rows = []
		for k, h in HEAD.items():
			amt = flt(target[k] - have[h], 2)
			if amt > 1:
				rows.append({"account": acc.heads[h], "debit_in_account_currency": amt, "project": pid, "cost_center": _cc(), "user_remark": h})
		if not rows:
			continue
		total = flt(sum(r["debit_in_account_currency"] for r in rows), 2)
		rows.append({"account": bank, "credit_in_account_currency": total, "cost_center": _cc()})
		je = frappe.get_doc({"doctype": "Journal Entry", "company": CO, "posting_date": mid, "voucher_type": "Journal Entry", "accounts": rows,
			"user_remark": f"Hipersign demo — cost brought forward {pid}: materials, labour (payroll allocation), plant hire and site overheads booked to the project"})
		je.flags.hs_system_entry = True
		je.insert(ignore_permissions=True)
		je.submit()


def v180_steps(c):
	from hipersign_trading.api import projects as P

	if frappe.db.exists("Project Step Log", {"project": H}):
		return
	from hipersign_trading.demo import user_email

	who = {P.MD: user_email("md"), P.FM: user_email("fin"), "Accounts User": user_email("acc"), P.PM: _email("Wang", "Lei"), P.QS: _email("Ahmed", "Raza"),
		P.SE: _email("Liu", "Yang"), P.BUY: user_email("pm")}
	for (pid, *_r) in PROJECTS:
		p = frappe.get_doc("Project", pid)
		for i in range(cint(p.hs_step)):
			role = P.STEP_ROLES.get(i, [P.MD])[0]
			u = who.get(role) or "Administrator"
			frappe.get_doc({"doctype": "Project Step Log", "project": pid, "step": i + 1, "step_name": P.STEPS[i][0], "completed_by": u if frappe.db.exists("User", u) else "Administrator",
				"completed_on": f"{P.plan_date(p, i)} 10:00:00"}).insert(ignore_permissions=True)
		pct = 100 if cint(p.hs_step) >= 26 else round(P.fig(pid).pct)
		frappe.db.set_value("Project", pid, "percent_complete", pct, update_modified=False)
	from hipersign_trading import navigation

	navigation.apply()


STEPS = [v180_company, v180_masters, v180_crew, v180_projects, v180_bonds, v180_billing, v180_subcontracts, v180_site, v180_tasks, v180_timesheets, v180_costs, v180_steps]
