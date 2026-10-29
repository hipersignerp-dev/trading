"""Sample data — the same records as the Hipersign Trading prototype."""

ITEMS = [
	# code, name, arabic, group, uom, hs, origin, reorder, sell, cost, warehouse, opening qty
	("ITM-001", 'LED Panel 55"', "شاشة LED مقاس 55 بوصة", "Electronics", "Nos", "8528.72", "China", 200, 1100, 820, "Main Warehouse", 1250),
	("ITM-002", "HDMI Cable 10m", "كابل HDMI بطول 10 م", "Accessories", "Nos", "8544.42", "China", 500, 25, 18, "Main Warehouse", 2450),
	("ITM-003", "Surveillance Camera 4MP", "كاميرا مراقبة 4 ميجابكسل", "Security", "Nos", "8525.89", "China", 250, 290, 210, "Warehouse 2", 860),
	("ITM-004", "Network Switch 24-port PoE", "محول شبكة 24 منفذ", "Networking", "Nos", "8517.62", "China", 100, 860, 640, "Main Warehouse", 520),
	("ITM-005", "Fire Alarm Panel 8-zone", "لوحة إنذار حريق 8 مناطق", "Fire Safety", "Nos", "8531.10", "Germany", 60, 1950, 1450, "Warehouse 2", 340),
	("ITM-006", "Ceiling Speaker 6W", "مكبر صوت سقفي 6 واط", "Audio", "Nos", "8518.22", "China", 300, 78, 58, "Main Warehouse", 1120),
	("ITM-007", "Control Module", "وحدة تحكم", "Automation", "Nos", "8537.10", "China", 150, 880, 650, "Warehouse 3", 780),
	("ITM-008", "Cable Tray 300mm (3m)", "حامل كابلات 300 مم", "Electrical", "Nos", "7308.90", "United Arab Emirates", 400, 62, 46, "Main Warehouse", 2200),
	("ITM-009", "PVC Conduit 25mm (3m)", "أنبوب PVC قطر 25 مم", "Electrical", "Nos", "3917.23", "United Arab Emirates", 1000, 8.8, 6.5, "Warehouse 3", 4550),
	("ITM-010", "Junction Box IP65", "صندوق توصيل IP65", "Electrical", "Nos", "8538.90", "United Arab Emirates", 500, 19, 14, "Main Warehouse", 2760),
	("ITM-011", "Access Control Reader", "قارئ التحكم بالدخول", "Security", "Nos", "8471.90", "China", 50, 420, 310, "Warehouse 2", 140),
	("ITM-012", "Installation Kit", "طقم تركيب", "Accessories", "Set", "8536.90", "China", 100, 165, 120, "Main Warehouse", 60),
	("ITM-013", "Video Wall Controller", "وحدة تحكم جدار الفيديو", "Electronics", "Nos", "8543.70", "Germany", 5, 5600, 4200, "Warehouse 3", 24),
]

SERVICES = [
	("SRV-001", "Installation & commissioning", "التركيب والتشغيل", "Job", 450, 260),
	("SRV-002", "Annual maintenance contract (AMC)", "عقد صيانة سنوي", "Year", 6500, 3900),
	("SRV-003", "Delivery & handling", "التوصيل والمناولة", "Trip", 250, 140),
	("SRV-004", "Site survey & system design", "مسح الموقع وتصميم النظام", "Visit", 750, 380),
	("SRV-005", "Programming & configuration", "البرمجة والإعداد", "Hour", 180, 90),
	("SRV-006", "User training", "تدريب المستخدمين", "Session", 600, 300),
]

WAREHOUSES = [
	("Main Warehouse", "Jebel Ali Free Zone"),
	("Warehouse 2", "Al Quoz Industrial 3"),
	("Warehouse 3", "Sharjah Industrial Area 13"),
	("Rejected Warehouse", "Jebel Ali Free Zone"),
]

GROUP_DISCOUNT = {"Contractor": 5, "Project": 4, "Wholesale": 8, "Retail": 0, "Government": 3, "Export": 6}

PAYMENT_TERMS = [
	# template, [(term, invoice portion, credit days, due date based on)]
	("Cash on delivery", [("COD", 100, 0)]),
	("Net 30 days", [("Net 30", 100, 30)]),
	("Net 45 days", [("Net 45", 100, 45)]),
	("Net 60 days", [("Net 60", 100, 60)]),
	("Net 90 days", [("Net 90", 100, 90)]),
	("30% advance, balance net 30", [("Advance 30%", 30, 0), ("Balance net 30", 70, 30)]),
	("50% advance, 50% on delivery", [("Advance 50%", 50, 0), ("On delivery 50%", 50, 7)]),
]

CUSTOMERS = [
	# name, group, limit, terms, emirate, trn, contact, mobile, email
	("Al Noor LLC", "Contractor", 500000, "Net 60 days", "Dubai", "100245781600003", "Hamad Al Noor", "+971 50 131 9110", "hamad@alnoorllc.ae"),
	("Gulf Projects", "Project", 300000, "Net 45 days", "Abu Dhabi", "100398120400003", "Ravi Shankar", "+971 55 862 7820", "ravi@gulfprojects.ae"),
	("Star Vision", "Retail", 150000, "Net 30 days", "Sharjah", "100512667900003", "Nadia Farouk", "+971 56 595 7330", "nadia@starvision.ae"),
	("Horizon Trading", "Wholesale", 400000, "Net 60 days", "Dubai", "100623914500003", "Sameer Qureshi", "+971 52 328 4640", "sameer@horizontrading.ae"),
	("Elite Systems", "Retail", 100000, "Net 30 days", "Ajman", "", "Marco Rossi", "+971 50 118 7742", "marco@elitesystems.ae"),
	("Future Build", "Contractor", 350000, "Net 60 days", "Dubai", "100781230600003", "Aisha Rahman", "+971 54 791 1460", "aisha@futurebuild.ae"),
	("Gulf Trading LLC", "Wholesale", 600000, "Net 45 days", "Dubai", "100854419700003", "Yousef Karim", "+971 58 524 3380", "yousef@gulftrading.ae"),
	("Dubai Municipality Projects", "Government", 800000, "Net 90 days", "Dubai", "100900012300003", "Eng. Mariam Saeed", "+971 50 257 5300", "mariam@dmprojects.ae"),
]

EXPORT_CUSTOMERS = [
	# name, country (city), country master, currency, contact, mobile, email, incoterm, named place, payment, mode
	("Muscat Integrated Systems LLC", "Oman (Muscat)", "Oman", "OMR", "Salim Al Harthy", "+968 9123 4567", "salim@muscatintegrated.om", "DAP", "Muscat", "Advance TT", "Land"),
	("Riyadh Smart Buildings Co.", "Saudi Arabia (Riyadh)", "Saudi Arabia", "SAR", "Fahad Al Otaibi", "+966 55 210 3344", "fahad@riyadhsmart.sa", "DAP", "Riyadh", "Open account 30 days", "Land"),
	("Nairobi Secure Tech Ltd", "Kenya (Nairobi)", "Kenya", "USD", "Grace Wanjiru", "+254 722 410 118", "grace@nairobisecure.co.ke", "CIF", "Mombasa", "LC at sight", "Sea"),
]

SUPPLIERS = [
	# name, group, country, currency, terms, contact, mobile, email
	("Global Supplies Co. Ltd", "Goods Suppliers", "China", "USD", "Net 60 days", "Kevin Zhang", "+86 138 0755 2210", "kevin@globalsupplies.com"),
	("Shenzhen Brightway Electronics", "Goods Suppliers", "China", "CNY", "Net 45 days", "Lily Chen", "+86 139 2861 4475", "lily@brightway.cn"),
	("EuroSafe Systems GmbH", "Goods Suppliers", "Germany", "EUR", "Net 30 days", "Markus Weber", "+49 69 4005 1180", "markus@eurosafe.de"),
	("Gulf Electrical Trading LLC", "Goods Suppliers", "United Arab Emirates", "AED", "Net 30 days", "Rashid Al Marri", "+971 4 339 5521", "rashid@gulfelectrical.ae"),
	("Oceanic Freight Forwarders", "Logistics & Customs", "United Arab Emirates", "AED", "Net 30 days", "Operations desk", "+971 4 881 2200", "ops@oceanicfreight.ae"),
	("Al Bahar Customs Clearing", "Logistics & Customs", "United Arab Emirates", "AED", "Net 30 days", "Clearance desk", "+971 4 883 4410", "clearing@albahar.ae"),
	("Emirates Cargo Insurance", "Logistics & Customs", "United Arab Emirates", "AED", "Net 30 days", "Marine cargo team", "+971 4 445 9012", "cargo@emiratesins.ae"),
	("Swift Port Handling", "Logistics & Customs", "United Arab Emirates", "AED", "Net 30 days", "Port operations", "+971 4 881 7733", "ops@swiftport.ae"),
]

FX = {"USD": 3.6725, "EUR": 4.28, "CNY": 0.515, "OMR": 9.553, "SAR": 0.9793}

LEADS = [
	# company, contact, mobile, email, emirate, source, interest, value, days to close, owner key, stage, follow-up offset, next action
	("Gulf Hospitality Group", "Reem Al Suwaidi", "+971 50 418 2270", "reem@gulfhospitality.ae", "Dubai", "Website enquiry", "Hotel CCTV upgrade — 120 cameras", 185000, 40, "sm", "Qualified", 1, "Site survey with IT manager"),
	("Palm Crest Facilities", "Daniel Mathew", "+971 55 230 9184", "daniel@palmcrest.ae", "Dubai", "WhatsApp enquiry", "Access control for 3 residential towers", 96000, 25, "sales", "Proposal", -2, "Follow up on the proposal"),
	("Desert Rose Schools", "Hanan Khalil", "+971 56 771 0325", "hanan@desertroseschools.ae", "Sharjah", "Exhibition", "PA system & ceiling speakers — 2 campuses", 42000, 50, "sales", "Contacted", 0, "Send speaker datasheets"),
	("Blue Lagoon Interiors", "Sameera Iqbal", "+971 52 660 4419", "sameera@bluelagoon.ae", "Dubai", "Referral", "LED panels for a showroom fit-out", 28000, 30, "sales", "New", 2, "First call — understand the scope"),
	("Al Waha Contracting", "Eng. Tariq Nasser", "+971 50 902 6631", "tariq@alwahacontracting.ae", "Abu Dhabi", "Cold call", "Cable trays & conduit — warehouse project", 64000, 11, "sm", "Negotiation", 3, "Agree final price and delivery"),
	("Northstar Logistics", "Vikram Rao", "+971 54 318 7720", "vikram@northstarlog.ae", "Dubai", "Website enquiry", "Network switches & Wi-Fi for a new DC", 37000, 35, "sm", "Qualified", -3, "Confirm port count with IT"),
	("Mirage Events", "Joel Fernandes", "+971 55 870 3312", "joel@mirageevents.ae", "Dubai", "WhatsApp enquiry", "HDMI cables & screens for events", 9500, 10, "sales", "New", 0, "Call back with availability"),
	("Falcon Tech Park", "Ahmed Bin Rashid", "+971 50 655 1908", "ahmed@falcontechpark.ae", "Abu Dhabi", "Exhibition", "Surveillance system with 3-year AMC", 118000, 55, "sm", "Proposal", 5, "Present the proposal to the board"),
	("Oasis Residences", "Maria Santos", "+971 52 349 6670", "maria@oasisresidences.ae", "Dubai", "Walk-in", "Intercom & access readers — 60 units", 22000, 20, "sales", "Contacted", -1, "Arrange a site visit"),
	("Coral Bay Clinics", "Dr. Asma Rahim", "+971 56 114 2096", "asma@coralbayclinics.ae", "Ajman", "Social media", "Fire alarm panels for 4 clinics", 31000, -5, "sales", "Lost", None, ""),
]

LEAD_SOURCES = ["Website enquiry", "WhatsApp enquiry", "Referral", "Walk-in", "Exhibition", "Cold call", "Social media"]

DEMO_USERS = [
	# key, first, last, roles
	("md", "Khalid", "Al Mansoori", ["Managing Director", "Sales Manager", "Purchase Manager", "Accounts Manager", "Stock Manager", "Sales Master Manager", "Purchase Master Manager", "Item Manager"]),
	("buyer", "Rahul", "Nair", ["Purchase User"]),
	("pm", "Fatima", "Al Zaabi", ["Purchase Manager", "Purchase User", "Purchase Master Manager", "Item Manager"]),
	("logi", "Imran", "Sheikh", ["Logistics Coordinator", "Stock User", "Purchase User"]),
	("store", "Joseph", "D'Souza", ["Stock User"]),
	("whm", "Ahmed", "Hassan", ["Stock Manager", "Stock User", "Item Manager"]),
	("sales", "Priya", "Menon", ["Sales User"]),
	("sm", "Omar", "Haddad", ["Sales Manager", "Sales User", "Sales Master Manager"]),
	("acc", "Anil", "Kumar", ["Accounts User"]),
	("fin", "Sara", "Al Hashimi", ["Accounts Manager", "Accounts User"]),
	("hr", "Lina", "Farah", ["HR Manager", "HR User"]),
	("driver", "Rashid", "Khan", ["Driver"]),
]

# Home workspace for each demo user
DEFAULT_WORKSPACE = {
	"md": "Hipersign Trading", "buyer": "Hipersign Warehouse", "pm": "Hipersign Trading", "logi": "Hipersign Warehouse",
	"store": "Hipersign Warehouse", "whm": "Hipersign Warehouse", "sales": "Hipersign Sales", "sm": "Hipersign Sales",
	"acc": "Hipersign Finance", "fin": "Hipersign Finance", "hr": "Hipersign HR",
}

DRIVERS = [
	# name, mobile, vehicle, demo user key
	("Rashid Khan", "+971 50 441 7781", "DXB 4471", "driver"),
	("Sunil Perera", "+971 55 902 3318", "DXB 8820", None),
	("Faisal Ahmed", "+971 52 117 6604", "SHJ 3315", None),
]

EMPLOYEES = [
	# first, last, gender, designation, department, joined (days ago), passport expiry, visa expiry, Emirates ID expiry, labour card expiry (days from today)
	("Priya", "Menon", "Female", "Sales Executive", "Sales", 900, 1200, 21, 21, 400),
	("Omar", "Haddad", "Male", "Sales Manager", "Sales", 2100, 900, 300, 300, 300),
	("Ahmed", "Hassan", "Male", "Warehouse Manager", "Operations", 1800, 50, 410, 410, 410),
	("Imran", "Sheikh", "Male", "Logistics Coordinator", "Operations", 700, 1500, 640, 640, -12),
	("Anil", "Kumar", "Male", "Accountant", "Accounts", 1200, 700, 45, 45, 500),
	("Rashid", "Khan", "Male", "Driver", "Operations", 400, 1100, 330, 330, 330),
]

DEMO_EMAIL_DOMAIN = "demo.hipersignerp.com"

# ---------------------------------------------------------------- v1.2 master-record details
SALES_PERSONS = ["Priya Menon", "Omar Haddad"]
TERRITORIES = ["Dubai", "Abu Dhabi & Al Ain", "Northern Emirates", "GCC", "Africa", "Rest of World"]
EMIRATE_TERRITORY = {"Dubai": "Dubai", "Abu Dhabi": "Abu Dhabi & Al Ain", "Al Ain": "Abu Dhabi & Al Ain"}

ITEM_MASTER = {
	# code: brand, model, purchase uom, sales units per purchase unit, kg per unit, warranty months, minimum order, lead days (0 = supplier), default supplier
	"ITM-001": ("Hipersign Vision", "HV-55UHD", "Nos", 1, 18.5, 12, 1, 0, "Global Supplies Co. Ltd"),
	"ITM-002": ("CablePro", "HD-10M-2.0", "Carton", 100, 0.09, 0, 100, 0, "Shenzhen Brightway Electronics"),
	"ITM-003": ("SecuView", "SV-IPC4MP-B", "Carton", 10, 0.65, 12, 10, 0, "Global Supplies Co. Ltd"),
	"ITM-004": ("NetCore", "NC-S24P-370", "Carton", 5, 4.2, 24, 5, 0, "Shenzhen Brightway Electronics"),
	"ITM-005": ("EuroSafe", "ES-FAP8", "Carton", 2, 12, 36, 2, 0, "EuroSafe Systems GmbH"),
	"ITM-006": ("SoundLine", "SL-CS6", "Carton", 20, 0.8, 12, 20, 0, "Shenzhen Brightway Electronics"),
	"ITM-007": ("AutoLink", "AL-CM16", "Carton", 10, 1.2, 24, 10, 0, "Shenzhen Brightway Electronics"),
	"ITM-008": ("GulfTray", "GT-300-3", "Bundle", 20, 2.4, 0, 20, 0, "Gulf Electrical Trading LLC"),
	"ITM-009": ("Emirates Conduit", "EC-25-3", "Bundle", 50, 0.44, 0, 50, 0, "Gulf Electrical Trading LLC"),
	"ITM-010": ("GulfTray", "GT-JB65", "Carton", 50, 0.3, 0, 50, 0, "Gulf Electrical Trading LLC"),
	"ITM-011": ("SecuView", "SV-ACR200", "Carton", 10, 0.5, 24, 10, 0, "Global Supplies Co. Ltd"),
	"ITM-012": ("Hipersign", "HS-IK01", "Carton", 10, 0.9, 0, 10, 0, "Global Supplies Co. Ltd"),
	"ITM-013": ("EuroSafe", "ES-VWC9", "Nos", 1, 14, 36, 1, 0, "EuroSafe Systems GmbH"),
}

CUSTOMER_MASTER = {
	# name: website, sales person, trade licence no., issued by, licence expiry (days from today), KYC status
	"Al Noor LLC": ("alnoor.ae", "Priya Menon", "DED-845120", "DED Dubai", 210, "Verified"),
	"Gulf Projects": ("gulfprojects.ae", "Omar Haddad", "ADDED-CN-1120934", "ADDED Abu Dhabi", -9, "Blocked"),
	"Star Vision": ("", "Priya Menon", "SEDD-664102", "SEDD Sharjah", 18, "Verified"),
	"Horizon Trading": ("horizontrading.ae", "Omar Haddad", "DED-790331", "DED Dubai", 300, "Verified"),
	"Elite Systems": ("", "Priya Menon", "AJM-41208", "Ajman DED", 120, "Pending"),
	"Future Build": ("futurebuild.ae", "Omar Haddad", "DED-912774", "DED Dubai", 400, "Verified"),
	"Gulf Trading LLC": ("gulftrading.ae", "Omar Haddad", "DED-503318", "DED Dubai", 260, "Verified"),
	"Dubai Municipality Projects": ("dm.gov.ae", "Omar Haddad", "GOV-DM-001", "Government of Dubai", 900, "Verified"),
	"Muscat Integrated Systems LLC": ("muscatintegrated.om", "Omar Haddad", "CR-1290044", "Oman Ministry of Commerce", 330, "Verified"),
	"Riyadh Smart Buildings Co.": ("riyadhsmart.sa", "Omar Haddad", "CR-1010773410", "Saudi Ministry of Commerce", 180, "Verified"),
	"Nairobi Secure Tech Ltd": ("nairobisecure.co.ke", "Omar Haddad", "PVT-7YUQ2B", "Kenya Business Registration", 365, "Verified"),
}
EXPORT_TERRITORY = {"Oman": "GCC", "Saudi Arabia": "GCC", "Kenya": "Africa"}

SUPPLIER_MASTER = {
	# name: lead time days, website, registration no., expiry (days from today)
	"Global Supplies Co. Ltd": (45, "globalsupplies.cn", "91440300MA5F2K", 400),
	"Shenzhen Brightway Electronics": (45, "brightway-elec.cn", "91440300MA5G7R", 280),
	"EuroSafe Systems GmbH": (35, "eurosafe.de", "HRB 118223", 900),
	"Gulf Electrical Trading LLC": (5, "gulfelectrical.ae", "DED-331208", 22),
}

DUNNING_TYPES = [
	# name, days, text
	("Friendly reminder", 7, "This is a friendly reminder that invoice {{ doc.sales_invoice }} is overdue. Please arrange payment or let us know the date we can expect it."),
	("Second reminder", 21, "Invoice {{ doc.sales_invoice }} is now three weeks overdue. Please settle it this week to keep your account in good standing."),
	("Final notice", 45, "Final notice: invoice {{ doc.sales_invoice }} is more than 45 days overdue. New orders will be held until the account is settled."),
]

GROUP = {
	"holding": ("Hipersign Demo Group", "HDG"),
	"companies": [
		# name, abbr, currency, country, ownership %, minority partner, role, licence
		("Hipersign Demo Trading FZE", "HFZE", "AED", "United Arab Emirates", 100, "", "Bonded stock and re-export hub — Jebel Ali Free Zone", "JAFZA 182664"),
		("Hipersign Demo Trading Oman LLC", "HOM", "OMR", "Oman", 70, "Al Harthy Investments (local partner)", "Oman distribution — Muscat", "CR 1478803"),
	],
}

# Exchange rates for the month-end revaluation demo (EUR and CNY move; USD, OMR, SAR are pegged)
FX_MONTH_END = {"EUR": 4.241, "CNY": 0.5106}
FX_TODAY = {"EUR": 4.315, "CNY": 0.518}
