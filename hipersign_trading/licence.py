"""v1.8.3: the licence and the super admins.

Super admins are Hipersign's own logins: the users listed in the site config key `hipersign_super_admins`
(or Administrator when the key is not set) (set in Press › Site › Config — the client cannot change it from the ERP). Only they can open the
Super Admin page and change the Hipersign Licence: how many desk users and companies the client may have and which
modules may be switched on. The limits are checked on the server when a user is enabled or given a role, when a company is
created and when a feature is switched on. Portal customers, driver-only logins, Administrator and super admins are not
counted. Super admins also decide whether Frappe and ERPNext pop-ups (update notices, What's new, onboarding tours) reach
the client's admins; errors and validation messages always show."""

import json

import frappe
from frappe import _

LICENCE = "Hipersign Licence"
EXEMPT = {"Administrator", "Guest"}
# roles that do not make a paid desk user on their own (a driver who only uses the driver app)
NOT_COUNTED_ROLES = {"Driver", "All", "Guest", "Desk User", "Employee", "Employee Self Service"}


def super_admins():
	v = frappe.conf.get("hipersign_super_admins") or []
	if isinstance(v, str):
		v = [x.strip() for x in v.split(",")]
	v = {x for x in v if x}
	# v1.8.4: when the site config names super admins, only they are super admins — Administrator too is then an
	# ordinary (client) admin. With no list, Administrator stays the super admin so nobody is locked out.
	return v or {"Administrator"}


def is_super_admin(user=None):
	return (user or frappe.session.user) in super_admins()


def get_licence():
	"""The licence as a dict; no licence document (or no DocType yet) = no limits."""
	try:
		if not frappe.db.exists("DocType", LICENCE):
			return frappe._dict()
		return frappe.get_cached_doc(LICENCE).as_dict()
	except Exception:
		return frappe._dict()


def licensed_features(lic=None):
	"""None = every module allowed; otherwise the set of feature keys the licence allows."""
	lic = lic or get_licence()
	if not lic.get("limit_features"):
		return None
	raw = lic.get("licensed_features") or ""
	try:
		keys = json.loads(raw) if raw.strip().startswith("[") else [k.strip() for k in raw.split(",")]
	except Exception:
		keys = []
	return {k for k in keys if k}


def feature_licensed(key):
	allowed = licensed_features()
	return allowed is None or key in allowed


# ---------------------------------------------------------------- users
def counted_users(exclude=None):
	"""Enabled desk users that count towards the licence."""
	skip = EXEMPT | super_admins() | ({exclude} if exclude else set())
	rows = frappe.db.sql(
		"""select distinct u.name from `tabUser` u join `tabHas Role` r on r.parent = u.name and r.parenttype = 'User'
		where u.enabled = 1 and u.user_type = 'System User' and r.role not in %(nc)s""",
		{"nc": tuple(NOT_COUNTED_ROLES)},
	)
	return [r[0] for r in rows if r[0] not in skip]


def _counts(doc):
	if doc.name in EXEMPT or doc.name in super_admins() or not doc.enabled:
		return False
	if (doc.user_type or "System User") != "System User":
		return False
	return any(r.role not in NOT_COUNTED_ROLES for r in doc.get("roles") or [])


def check_user(doc, method=None):
	"""User.validate: refuse a new paid desk user beyond the licence."""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_setup_wizard:
		return
	limit = frappe.utils.cint(get_licence().get("max_users"))
	if not limit or not _counts(doc):
		return
	others = counted_users(exclude=doc.name)
	if doc.name in counted_users():
		return  # already counted: editing an existing user is always fine
	if len(others) >= limit:
		frappe.throw(
			_("Your licence allows {0} users and {1} are in use. Disable a user or ask Hipersign to extend the licence.").format(limit, len(others)),
			title=_("User limit reached"),
		)


def check_company(doc, method=None):
	"""Company.before_insert: refuse a company beyond the licence."""
	if frappe.flags.in_install or frappe.flags.in_setup_wizard:
		return
	limit = frappe.utils.cint(get_licence().get("max_companies"))
	if limit and frappe.db.count("Company") >= limit:
		frappe.throw(_("Your licence allows {0} companies. Ask Hipersign to extend the licence.").format(limit), title=_("Company limit reached"))


def usage():
	lic = get_licence()
	return {
		"users": len(counted_users()),
		"max_users": frappe.utils.cint(lic.get("max_users")),
		"companies": frappe.db.count("Company"),
		"max_companies": frappe.utils.cint(lic.get("max_companies")),
		"features": sorted(licensed_features(lic)) if licensed_features(lic) is not None else None,
		"licensee": lic.get("licensee"),
		"valid_until": str(lic.get("valid_until") or "") or None,
	}


@frappe.whitelist()
def licence_summary():
	"""For the client's admins: what the licence allows and what is used (read-only)."""
	frappe.only_for(("System Manager",))
	return usage()


# ---------------------------------------------------------------- Frappe / ERPNext pop-ups
def popups_allowed(user=None):
	return is_super_admin(user) or bool(get_licence().get("show_frappe_popups_to_all"))


def boot_popups(bootinfo):
	"""Called from boot_session: take Frappe's own notices out of the boot for everyone but super admins."""
	allowed = popups_allowed()
	bootinfo.hs_popups = 1 if allowed else 0
	bootinfo.hs_super_admin = 1 if is_super_admin() else 0
	if allowed:
		return
	bootinfo.change_log = []
	bootinfo.onboarding_tours = []
	bootinfo.setup_wizard_requires = None


@frappe.whitelist()
def show_update_popup():
	"""Replaces frappe.utils.change_log.show_update_popup: the "new version available" notice only for super admins."""
	if not popups_allowed():
		return
	from frappe.utils.change_log import show_update_popup as frappe_popup

	return frappe_popup()
