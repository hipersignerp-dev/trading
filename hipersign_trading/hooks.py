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
		"logo": "/assets/hipersign_trading/images/hipersign-logo.png",
		"title": "Hipersign ERP",
		"route": "/app/hipersign-trading",
	}
]

app_include_css = ["/assets/hipersign_trading/css/hipersign.css" + _v, "/assets/hipersign_trading/css/hipersign_theme.css" + _v]
app_include_js = [
	"/assets/hipersign_trading/js/hipersign.js" + _v,
	"/assets/hipersign_trading/js/doc_send.js" + _v,
	"/assets/hipersign_trading/js/trading_forms.js" + _v,
	"/assets/hipersign_trading/js/returns_forms.js" + _v,
	"/assets/hipersign_trading/js/hr_forms.js" + _v,
	"/assets/hipersign_trading/js/hs_setup.js" + _v,
	"/assets/hipersign_trading/js/hs_docs.js" + _v,
	"/assets/hipersign_trading/js/hs_form_modes.js" + _v,
	"/assets/hipersign_trading/js/hs_money.js" + _v,
	"/assets/hipersign_trading/js/hs_nav.js" + _v,
	"/assets/hipersign_trading/js/hs_ui.js" + _v,
	"/assets/hipersign_trading/js/hs_topbar.js" + _v,
]

website_context = {
	"favicon": "/assets/hipersign_trading/images/hipersign-logo.png",
	"splash_image": "/assets/hipersign_trading/images/hipersign-logo.png",
}

# ---------------------------------------------------------------- install / migrate
before_install = "hipersign_trading.setup.before_install"
after_install = "hipersign_trading.setup.after_install"
before_migrate = "hipersign_trading.setup.before_migrate"
after_migrate = "hipersign_trading.setup.after_migrate"
before_uninstall = "hipersign_trading.setup.before_uninstall"

boot_session = "hipersign_trading.boot.boot_session"

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
doc_events = {
	# external documents: blocking rules on submit and on status changes (Hipersign Document Rule)
	"*": {
		"before_submit": "hipersign_trading.doc_rules.before_submit",
		"validate": "hipersign_trading.doc_rules.validate",
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
		"validate": "hipersign_trading.overrides.sales_order.validate",
		"before_submit": "hipersign_trading.overrides.kyc.sales_order_before_submit",
		"on_submit": "hipersign_trading.overrides.sales_order.on_submit",
	},
	"Supplier": {"before_save": "hipersign_trading.overrides.kyc.party_before_save"},
	"Pick List": {"before_submit": "hipersign_trading.overrides.advances.pick_list_before_submit"},
	"Payment Entry": {
		"validate": "hipersign_trading.overrides.payment_entry.validate",
		"on_submit": "hipersign_trading.overrides.advances.payment_entry_changed",
		"on_cancel": "hipersign_trading.overrides.advances.payment_entry_changed",
	},
	"Sales Invoice": {
		"validate": "hipersign_trading.overrides.sales_invoice.validate",
		"before_submit": "hipersign_trading.overrides.returns.sales_return_before_submit",
	},
	"Purchase Invoice": {"before_submit": "hipersign_trading.overrides.returns.purchase_return_before_submit"},
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
	"Quotation": {"validate": "hipersign_trading.overrides.quotation.validate"},
	"Lead": {"validate": "hipersign_trading.overrides.lead.validate"},
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
portal_menu_items = [
	{"title": "Statement of account", "route": "/statement", "role": "Customer"},
	{"title": "Warranty", "route": "/warranty", "role": "Customer"},
]

# ---------------------------------------------------------------- driver web app (/driver)
role_home_page = {"Driver": "driver"}

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
	]
}
