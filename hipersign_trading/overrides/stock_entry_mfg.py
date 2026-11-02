"""v1.8.0 (Manufacturing): a manufacture entry booked from the shop floor keeps the process loss it was given.

ERPNext resets the process loss of every manufacture entry to the largest loss recorded on the work order's operations,
which counts the same scrap again on each partial entry (400 panels made today, 400 tomorrow …). Entries made by
hipersign_trading.api.manufacturing.manufacture carry flags.hs_keep_loss: their loss is the scrap not yet booked by the
earlier entries of the work order, so the work order's process loss adds up to the scrap recorded on the job cards."""

from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry


class HipersignStockEntry(StockEntry):
	def set_process_loss_qty(self):
		if self.flags.get("hs_keep_loss"):
			return
		return super().set_process_loss_qty()
