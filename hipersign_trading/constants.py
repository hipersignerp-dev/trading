"""Shared names used across the app."""

MODULE = "Hipersign Trading"
SETTINGS = "Hipersign Settings"

# Prototype role → ERPNext role
ROLE_MAP = {
	"Administrator": "System Manager",
	"Managing Director": "Managing Director",
	"Buyer": "Purchase User",
	"Purchase Manager": "Purchase Manager",
	"Logistics Coordinator": "Logistics Coordinator",
	"Storekeeper": "Stock User",
	"Warehouse Manager": "Stock Manager",
	"Sales Executive": "Sales User",
	"Sales Manager": "Sales Manager",
	"Accountant": "Accounts User",
	"Finance Manager": "Accounts Manager",
	"HR Manager": "HR Manager",
	"Driver": "Driver",
}

NEW_ROLES = ["Managing Director", "Logistics Coordinator", "HR Manager", "HR User"]

# Roles without desk access (they only use the mobile web pages)
WEB_ROLES = ["Driver"]

WORKFLOW_STATES = {
	"Draft": "",
	"Pending Purchase Manager": "Warning",
	"Pending Sales Manager": "Warning",
	"Pending Finance Manager": "Warning",
	"Pending Warehouse Manager": "Warning",
	"Approved": "Success",
	"Rejected": "Danger",
	"Paid": "Success",
	"Cancelled": "Inverse",
}

WORKFLOW_ACTIONS = ["Submit for Approval", "Approve", "Reject", "Submit", "Cancel"]

IMPORT_STATUSES = [
	"Booked",
	"Shipped",
	"In Transit",
	"Arrived at Port",
	"Under Customs Clearance",
	"Cleared",
	"Received at Warehouse",
]

EXPORT_STATUSES = [
	"Booked",
	"Packed",
	"Export Declaration",
	"Customs Cleared",
	"Shipped",
	"Delivered",
	"Documents Complete",
]

IMPORT_DOCUMENTS = ["Commercial Invoice", "Packing List", "Certificate of Origin", "Bill of Lading / AWB"]

EXPORT_DOCUMENTS = [
	"Commercial Invoice",
	"Packing List",
	"Export / Re-export Declaration",
	"Certificate of Origin",
	"Bill of Lading / AWB / Truck CMR",
	"Insurance Certificate",
	"LC Documents",
]

LEAD_STAGES = ["New", "Contacted", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]
LEAD_PROBABILITY = {"New": 10, "Contacted": 20, "Qualified": 40, "Proposal": 60, "Negotiation": 80, "Won": 100, "Lost": 0}

# Returns
RETURN_REASONS = [
	"Damaged in transit",
	"Wrong item supplied",
	"Defective — under warranty",
	"Customer cancelled",
	"Excess quantity",
	"Pricing correction",
]

# Post-dated cheques
PDC_RECEIVED_STATES = ["In Hand", "Deposited", "Cleared", "Bounced", "Replaced", "Cancelled"]
PDC_ISSUED_STATES = ["Issued", "Cleared", "Cancelled"]

# Serialised items in the demo: item code → (serial prefix, warranty months)
SERIAL_ITEMS = {
	"ITM-004": ("NSW24P", 24),
	"ITM-005": ("FAP8Z", 36),
	"ITM-007": ("CTM", 24),
	"ITM-011": ("ACR", 24),
	"ITM-013": ("VWC", 36),
}

DELIVERY_STATES = ["Ready to Dispatch", "Out for Delivery", "Delivered", "Failed"]

# Employee documents tracked for expiry alerts: fieldname → label
EMPLOYEE_DOCS = {
	"valid_upto": "Passport",
	"hs_visa_expiry": "Residence visa",
	"hs_emirates_id_expiry": "Emirates ID",
	"hs_labour_card_expiry": "Labour card",
}

# ---------------------------------------------------------------- v1.2
# Collections: stage name by days past due (the thresholds are in Hipersign Settings)
COLLECTION_STAGES = ["Friendly reminder", "Second reminder", "Final notice", "Hold new orders"]

# KYC on customers and suppliers
KYC_STATUSES = ["Pending", "Verified", "Expired", "Blocked"]

# Letters of credit
LC_STATUSES = ["Applied", "Issued", "Documents Presented", "Accepted", "Paid", "Expired", "Cancelled"]
LC_OPEN = ["Applied", "Issued", "Documents Presented", "Accepted"]
LC_TENORS = {"At sight": 0, "Usance 30 days": 30, "Usance 60 days": 60, "Usance 90 days": 90, "Usance 120 days": 120, "Usance 180 days": 180}

# VAT / corporate tax return filing (filed by hand on EmaraTax)
TAX_RETURN_TYPES = ["VAT 201", "Corporate Tax"]
TAX_RETURN_STATES = ["Prepared", "Pending Finance Manager", "Approved", "Submitted", "Paid", "Rejected"]
LOCKED_DOCTYPES = ["Sales Invoice", "Purchase Invoice", "Journal Entry", "Payment Entry"]

# Smart reorder: lead time by country of origin when neither the item nor the supplier has one
LEAD_DAYS_BY_ORIGIN = {"China": 45, "Germany": 35, "United Arab Emirates": 5}
LEAD_DAYS_DEFAULT = 30

# Advance statuses shown on the sales order
ADVANCE_STATES = ["Not required", "Waiting", "Part received", "Received"]
