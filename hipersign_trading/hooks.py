app_name = "hipersign_trading"
app_title = "Hipersign Trading"
app_publisher = "Hipersign"
app_description = "Trading, Distribution & Import/Export ERP built on ERPNext"
app_email = "sales@hipersignerp.com"
app_license = "Proprietary"
from hipersign_trading import __version__ as app_version

# every release gets new asset addresses: the files are served "immutable" for a year and the site's service worker caches them
_v = f"?v={app_version}"

required_apps = ["erpnext"]

# ---------------------------------------------------------------- branding
app_logo_url = "/assets/hipersign_trading/images/hipersign-logo.png"

add_to_apps_screen = [
	{
		"name": "hipersign_trading",
		# v1.8.4 (#31, #30): a square icon like the other tiles, a name that fits, and Hipersign Home (not the old
		# "Hipersign Trading" workspace) as the landing page
		"logo": "/assets/hipersign_trading/images/hipersign-app.svg",
		"title": "Hipersign",
		"route": "/app/hipersign-home",
		"sequence_id": 0.5,
	}
]

# v1.8.4 (#29): only the Hipersign app on the apps screen for everyone but super admins
extend_bootinfo = "hipersign_trading.boot.only_hipersign_app"

app_include_css = [
	"/assets/hipersign_trading/css/hipersign.css" + _v,
	"/assets/hipersign_trading/css/hipersign_theme.css" + _v,
	"/assets/hipersign_trading/css/hs_shell.css" + _v,
	"/assets/hipersign_trading/css/hs_pages.css" + _v,
	"/assets/hipersign_trading/css/hs_create.css" + _v,
	"/assets/hipersign_trading/css/hs_projects.css" + _v,
	"/assets/hipersign_trading/css/hs_manufacturing.css" + _v,
	"/assets/hipersign_trading/css/hs_p20.css" + _v,
	"/assets/hipersign_trading/css/hs_reports.css" + _v,  # v1.8.4: Reports, Workflows & Settings, Data Migration, report views
]
app_include_js = [
	"/assets/hipersign_trading/js/hipersign.js" + _v,
	"/assets/hipersign_trading/js/doc_send.js" + _v,
	"/assets/hipersign_trading/js/trading_forms.js" + _v,
	"/assets/hipersign_trading/js/returns_forms.js" + _v,
	"/assets/hipersign_trading/js/hr_forms.js" + _v,
	"/assets/hipersign_trading/js/hs_setup.js" + _v,
	"/assets/hipersign_trading/js/hs_docs.js" + _v,
	"/assets/hipersign_trading/js/hs_form_modes.js" + _v,
	"/assets/hipersign_trading/js/hs_quick_cards.js" + _v,
	"/assets/hipersign_trading/js/hs_create.js" + _v,
	"/assets/hipersign_trading/js/hs_money.js" + _v,
	"/assets/hipersign_trading/js/hs_nav.js" + _v,
	"/assets/hipersign_trading/js/hs_ui.js" + _v,
	"/assets/hipersign_trading/js/hs_charts.js" + _v,
	"/assets/hipersign_trading/js/hs_topbar.js" + _v,
	"/assets/hipersign_trading/js/hs_panel.js" + _v,
	"/assets/hipersign_trading/js/hs_module.js" + _v,
	"/assets/hipersign_trading/js/hs_tour.js" + _v,
	"/assets/hipersign_trading/js/hs_deal.js" + _v,
	"/assets/hipersign_trading/js/hs_projects.js" + _v,
	"/assets/hipersign_trading/js/hs_manufacturing.js" + _v,
]

website_context = {
	"favicon": "/assets/hipersign_trading/images/hipersign-mark.png",
	"splash_image": "/assets/hipersign_trading/images/hipersign-logo.png",
}

# ---------------------------------------------------------------- install / migrate
before_install = "hipersign_trading.setup.before_install"
after_install = "hipersign_trading.setup.after_install"
before_migrate = "hipersign_trading.setup.before_migrate"
after_migrate = "hipersign_trading.setup.after_migrate"
before_uninstall = "hipersign_trading.setup.before_uninstall"

boot_session = "hipersign_trading.boot.boot_session"
# v1.5.6: Customer / Supplier forms open for users without invoice access (overrides/party_dashboard.py)
override_doctype_class = {
	"Customer": "hipersign_trading.overrides.party_dashboard.HipersignCustomer",
	"Supplier": "hipersign_trading.overrides.party_dashboard.HipersignSupplier",
	# v1.8.0: a partial manufacture entry keeps its own process loss (overrides/stock_entry_mfg.py)
	"Stock Entry": "hipersign_trading.overrides.stock_entry_mfg.HipersignStockEntry",
}

before_request = ["hipersign_trading.demo_access.before_request", "hipersign_trading.overrides.user.driver_redirect"]

# ---------------------------------------------------------------- fixtures
# Custom fields, property setters, workflows and the CRM kanban board ship with the app.
# Workflow states, action masters and roles are created in setup.py (before fixtures load).
fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Hipersign Trading"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Hipersign Trading"]]},
	{
		"dt": "Workflow",
		"filters": [
			[
				"name",
				"in",
				[
					"Hipersign Purchase Order Approval",
					"Hipersign Sales Order Approval",
					"Hipersign Supplier Payment Approval",
					"Hipersign Stock Count Approval",
					"Hipersign Credit Limit Approval",
				],
			]
		],
	},
	{"dt": "Kanban Board", "filters": [["name", "in", ["Hipersign Lead Pipeline"]]]},
]

# ---------------------------------------------------------------- document events
# v1.6.0: sales staff may change only credit notes among sales invoices (overrides/returns.py)
has_permission = {"Sales Invoice": "hipersign_trading.overrides.returns.sales_invoice_permission",
	# v1.8.4 (#32): a conversation without a record is private to its people
	"Hipersign Conversation": "hipersign_trading.hipersign_trading.doctype.hipersign_conversation.hipersign_conversation.has_permission"}
permission_query_conditions = {
	"Hipersign Conversation": "hipersign_trading.hipersign_trading.doctype.hipersign_conversation.hipersign_conversation.query_conditions",
}

doc_events = {
	# external documents: blocking rules on submit and on status changes (Hipersign Document Rule)
	"*": {
		# v1.5.6: the view-only demo account changes nothing (demo_access.py)
		"before_insert": "hipersign_trading.demo_access.doc_guard",
		"before_submit": ["hipersign_trading.demo_access.doc_guard", "hipersign_trading.doc_rules.before_submit"],
		"validate": ["hipersign_trading.demo_access.doc_guard", "hipersign_trading.doc_rules.validate"],
		"before_cancel": "hipersign_trading.demo_access.doc_guard",
		"on_trash": "hipersign_trading.demo_access.doc_guard",
		"before_rename": "hipersign_trading.demo_access.doc_guard",
	},
	"File": {
		"after_insert": "hipersign_trading.doc_rules.file_after_insert",
		"on_update": "hipersign_trading.doc_rules.file_on_update",
	},
	"Customer": {
		"before_save": [
			"hipersign_trading.overrides.customer.before_save",
			"hipersign_trading.overrides.kyc.party_before_save",
		],
		"on_update": "hipersign_trading.overrides.customer.on_update",
	},
	"Sales Order": {
		"before_validate": "hipersign_trading.overrides.pricing.remember",
		"validate": "hipersign_trading.overrides.sales_order.validate",
		"before_submit": "hipersign_trading.overrides.kyc.sales_order_before_submit",
		"on_submit": "hipersign_trading.overrides.sales_order.on_submit",
	},
	"Supplier": {"before_save": "hipersign_trading.overrides.kyc.party_before_save"},
	"Pick List": {"before_submit": "hipersign_trading.overrides.advances.pick_list_before_submit"},
	"Payment Entry": {
		"before_validate": "hipersign_trading.overrides.payment_entry.before_validate",
		"validate": "hipersign_trading.overrides.payment_entry.validate",
		"on_submit": "hipersign_trading.overrides.advances.payment_entry_changed",
		"on_cancel": "hipersign_trading.overrides.advances.payment_entry_changed",
	},
	"Sales Invoice": {
		"before_validate": "hipersign_trading.overrides.returns.sales_staff_only_returns",
		"validate": ["hipersign_trading.overrides.sales_invoice.validate", "hipersign_trading.overrides.returns.unlink_outstanding"],
		"before_submit": "hipersign_trading.overrides.returns.sales_return_before_submit",
		"on_update": "hipersign_trading.overrides.sales_invoice.link_export_shipment",
	},
	"Purchase Invoice": {
		"validate": "hipersign_trading.overrides.returns.unlink_outstanding",
		"before_submit": "hipersign_trading.overrides.returns.purchase_return_before_submit",
	},
	"Delivery Note": {
		"validate": "hipersign_trading.overrides.delivery_note.validate",
		"before_submit": "hipersign_trading.overrides.advances.dn_before_submit",
		"on_submit": "hipersign_trading.overrides.delivery_note.on_submit",
	},
	"Warranty Claim": {"validate": "hipersign_trading.overrides.warranty_claim.validate"},
	"Purchase Receipt": {
		"validate": "hipersign_trading.overrides.purchase_receipt.validate",
		"on_submit": "hipersign_trading.overrides.purchase_receipt.on_submit",
	},
	"Quotation": {"before_validate": "hipersign_trading.overrides.pricing.remember", "validate": "hipersign_trading.overrides.quotation.validate"},
	"Lead": {"validate": "hipersign_trading.overrides.lead.validate"},
	# v1.8.0: project purchase orders and material requests carry the project on the header (Projects pages, cost heads)
	"Purchase Order": {"validate": "hipersign_trading.api.projects.po_project"},
	"Material Request": {"validate": "hipersign_trading.api.projects.mr_project"},
	"User": {"before_insert": "hipersign_trading.overrides.user.before_insert",
		"validate": "hipersign_trading.licence.check_user"},  # v1.8.3: the licence's user limit
	"Company": {"before_insert": "hipersign_trading.licence.check_company"},  # v1.8.3: the licence's company limit
}

# v1.8.4: each company's own document series (MSO-, PO-LI-, MMR-, PJPO-, PMR- …) — merged into the events above
for _dt in ("Sales Order", "Purchase Order", "Material Request", "Purchase Receipt", "Delivery Note", "Sales Invoice"):
	_ev = doc_events.setdefault(_dt, {}).get("before_insert")
	_ev = [_ev] if isinstance(_ev, str) else list(_ev or [])
	doc_events[_dt]["before_insert"] = _ev + ["hipersign_trading.naming.company_series"]

# v1.8.3: Frappe's "new version available" notice only for super admins (or when the licence allows it)
override_whitelisted_methods = {
	"frappe.utils.change_log.show_update_popup": "hipersign_trading.licence.show_update_popup",
	"frappe.apps.get_apps": "hipersign_trading.boot.get_apps",  # v1.8.4 (#29)
}

# ---------------------------------------------------------------- scheduler
scheduler_events = {
	"daily": [
		"hipersign_trading.tasks.lead_follow_up_reminders",
		"hipersign_trading.tasks.proof_of_export_alerts",
		"hipersign_trading.tasks.late_import_shipment_alerts",
		"hipersign_trading.tasks.cheque_alerts",
		"hipersign_trading.tasks.employee_document_alerts",
		"hipersign_trading.tasks.collection_reminders",
		"hipersign_trading.tasks.kyc_alerts",
		"hipersign_trading.tasks.letter_of_credit_alerts",
		"hipersign_trading.tasks.advance_due_alerts",
		"hipersign_trading.tasks.tax_return_alerts",
		"hipersign_trading.compliance.company_document_alerts",
		"hipersign_trading.compliance.deadline_alerts",
		"hipersign_trading.doc_rules.waiver_alerts",
		"hipersign_trading.group.sync_all",
	],
	"monthly": [
		"hipersign_trading.tasks.revaluation_reminder",
	],
}

# ---------------------------------------------------------------- customer portal (/me)
# v1.8.2: ERPNext's own portal lists (/orders and /invoices crashed on our portal template) lead to the Hipersign portal
website_redirects = [
	{"source": "/orders", "target": "/portal?tab=orders"},
	{"source": "/invoices", "target": "/portal?tab=invoices"},
	{"source": "/quotations", "target": "/portal?tab=quotations"},
]

portal_menu_items = [
	{"title": "Statement of account", "route": "/statement", "role": "Customer"},
	{"title": "Warranty", "route": "/warranty", "role": "Customer"},
]

# ---------------------------------------------------------------- driver web app (/driver)
# v1.5.6: only a driver-only login opens /driver (role_home_page sent every login holding the Driver role there,
# Administrator included)
get_website_user_home_page = "hipersign_trading.overrides.user.home_page"

# ---------------------------------------------------------------- jinja helpers for print formats
jinja = {
	"methods": [
		"hipersign_trading.print_helpers.hs_company",
		"hipersign_trading.print_helpers.hs_arabic_name",
		"hipersign_trading.print_helpers.hs_party_contact",
		"hipersign_trading.print_helpers.hs_default_bank",
		"hipersign_trading.print_helpers.hs_is_export",
		"hipersign_trading.print_helpers.hs_serials",
		"hipersign_trading.print_helpers.hs_warranty_months",
		# v1.8.0: the project prints (BOQ, certificate, progress / retention invoice, variation, subcontract order)
		"hipersign_trading.print_helpers.hs_project_info",
		"hipersign_trading.print_helpers.hs_boq_sections",
		# v1.8.0: the manufacturing prints (job ticket, BOM, QC certificate, finished-goods label — English + Chinese)
		"hipersign_trading.print_helpers.hs_barcode",
		"hipersign_trading.print_helpers.hs_qr",
		"hipersign_trading.print_helpers.hs_company_zh",
		"hipersign_trading.print_helpers.hs_job_ticket",
		"hipersign_trading.print_helpers.hs_bom_print",
		"hipersign_trading.print_helpers.hs_qc_print",
		"hipersign_trading.print_helpers.hs_fg_label",
	]
}
