import frappe
def run():
    print(frappe.db.exists("Supplier","Gulf Electrical Trading LLC"))
    r = frappe.get_doc({"doctype": "Post Dated Cheque", "direction": "Issued", "company": "Hipersign Demo Trading LLC", "party": "Gulf Electrical Trading LLC", "cheque_no": "X1","cheque_date": "2026-11-20", "amount": 10})
    print(type(r).__mro__[:2], r.party_type)
    r.run_method("before_insert"); print(r.party_type)
    import inspect; print(inspect.getsourcefile(type(r)))
def run2():
    import traceback
    r = frappe.get_doc({"doctype": "Post Dated Cheque", "direction": "Issued", "company": "Hipersign Demo Trading LLC", "party": "Gulf Electrical Trading LLC", "cheque_no": "X1","cheque_date": "2026-11-20", "amount": 10})
    try: r.insert(ignore_permissions=True); print("ok", r.name, r.party_type)
    except Exception: traceback.print_exc()
    frappe.db.rollback()
