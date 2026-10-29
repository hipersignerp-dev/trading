# Copyright (c) 2026, Hipersign
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class HipersignSettings(Document):
	def validate(self):
		from hipersign_trading.features import enforce_dependencies, pack_of

		from hipersign_trading.features import PACKS, set_switches

		if self.company_mode == "Group":
			self.feat_group = 1
		# v1.5.6 (SET-04): choosing a pack in the field applies it, as the Pack menu does; changing a single switch
		# afterwards shows "Custom" (the field used to be recalculated and silently overwrite the choice)
		prev = self.get_doc_before_save()
		chose = prev and self.feature_pack != prev.feature_pack and self.feature_pack in PACKS
		if chose:
			set_switches(self, self.feature_pack)
			self.flags.hs_pack_applied = self.feature_pack
		enforce_dependencies(self)
		if self.setup_done and not chose:
			self.feature_pack = pack_of(self)
		if flt(self.sp_auto_pct) < 0 or flt(self.sp_auto_pct) > 20:
			frappe.throw(_("The short-payment percentage must be between 0 and 20."))
		seen = set()
		for r in self.form_modes or []:
			k = (r.document_type, r.role or "")
			if k in seen:
				frappe.throw(_("Row {0}: {1} already has a form mode{2}.").format(r.idx, r.document_type, " " + _("for {0}").format(r.role) if r.role else ""))
			seen.add(k)

	def on_update(self):
		frappe.clear_cache(doctype="Hipersign Settings")
		if self.flags.get("hs_pack_applied"):
			# the pack's form mode (Starter Quick, Standard Standard, Enterprise Detailed) applies to everyone again
			from hipersign_trading.api.quick import clear_all_form_modes

			clear_all_form_modes()
		if not frappe.flags.in_install and not frappe.flags.hs_no_effects:
			from hipersign_trading.features import apply_effects

			frappe.flags.hs_no_effects = True
			try:
				apply_effects(self)
			finally:
				frappe.flags.hs_no_effects = False

	@frappe.whitelist()
	def set_pack(self, pack):
		from hipersign_trading.features import apply_pack

		frappe.only_for("System Manager")
		apply_pack(pack)
		return pack
