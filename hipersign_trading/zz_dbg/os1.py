import frappe, traceback
def run():
    from hipersign_trading.demo import context as ctx, opening_stock
    c = ctx()
    try:
        opening_stock(c)
        print("OK")
    except Exception:
        traceback.print_exc()
    frappe.db.rollback()
