"""v1.5.6: the dark theme is the default for new users (each user can still change it with Toggle theme)."""


def before_insert(doc, method=None):
	if doc.meta.has_field("desk_theme") and (not doc.get("desk_theme") or doc.get("desk_theme") == "Light") and not doc.flags.get("hs_keep_theme"):
		doc.desk_theme = "Dark"



# roles every driver login also has; anything beyond these means the user works in the desk
_DRIVER_ONLY = {"Driver", "All", "Guest", "Desk User", "Employee", "Employee Self Service"}


def home_page(user):
	"""v1.5.6: a driver-only login opens the driver app (/driver); everyone else opens the desk.

	Replaces role_home_page {"Driver": "driver"}, which sent every login holding the Driver role —
	Administrator and managers included — to /driver."""
	import frappe

	if not user or user in ("Administrator", "Guest"):
		return None
	roles = set(frappe.get_roles(user))
	if "Driver" in roles and not (roles - _DRIVER_ONLY):
		return "driver"
	return None


def driver_redirect():
	"""before_request: a driver-only website login that lands on the desk (Frappe's default after login) is sent to
	the driver app instead of "Not permitted"."""
	import frappe

	try:
		req = getattr(frappe.local, "request", None)
		if not req or req.method != "GET":
			return
		path = req.path or ""
		if not (path in ("/app", "/desk") or path.startswith(("/app/", "/desk/"))):
			return
		user = frappe.session.user
		if user in ("Guest", "Administrator") or frappe.session.data.get("user_type") != "Website User":
			return
		if home_page(user) != "driver":
			return
	except Exception:
		return
	from werkzeug.routing import RequestRedirect

	raise RequestRedirect("/driver")
