// Hipersign ERP v1.3 — the Documents box on records with document rules: what is needed, attach with a type, ask for an exception.
frappe.provide("hipersign.docs");

hipersign.docs.DEFAULT = ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Purchase Order", "Purchase Receipt", "Purchase Invoice",
	"Payment Entry", "Journal Entry", "Letter of Credit", "Import Shipment", "Export Shipment"];

hipersign.docs.render = function (frm) {
	if (frm.is_new() || !frm.dashboard) return;
	frappe.xcall("hipersign_trading.api.docs.doc_info", { doctype: frm.doctype, name: frm.docname }).then((r) => {
		frm.dashboard.wrapper.find(".hs-docs-section").remove();
		if (!r || r.level === "Off" || !(r.rules || []).length) return;
		const badge = (lv) => `<span class="indicator-pill ${{ Block: "red", Required: "orange", Optional: "gray" }[lv] || "gray"}">${__(lv === "Block" ? "Blocks next step" : lv === "Required" && r.level === "Recommended" ? "Recommended" : lv)}</span>`;
		const rows = r.rules.map((x) => {
			const st = x.attached ? `<span class="text-success">${frappe.utils.icon("check", "sm")} ${__("On file")}</span>`
				: x.waiver ? `<a href="${frappe.utils.get_form_link("Document Waiver", x.waiver.name)}">${__("Exception")} ${x.waiver.name} · ${__(x.waiver.status)}</a>`
				: `<span class="${x.level === "Optional" ? "text-muted" : "text-danger"}">${__("Missing")}</span>`;
			const when = x.event === "When status changes to" ? ` <span class="text-muted small">${__("when {0}", [__(x.when_value)])}</span>` : "";
			const btns = x.attached ? "" : `<button class="btn btn-xs btn-default hs-attach" data-type="${frappe.utils.escape_html(x.document_type)}">${__("Attach")}</button>`
				+ (!x.waiver && (x.level !== "Optional" || ["Customer KYC documents", "Advance payment"].includes(x.document_type)) && r.level === "Full" ? ` <button class="btn btn-xs btn-default hs-waive" data-type="${frappe.utils.escape_html(x.document_type)}" data-role="${frappe.utils.escape_html(x.approver_role || "")}">${__("Request exception")}</button>` : "");
			return `<tr><td><b>${__(x.document_type)}</b>${when}${x.note ? `<div class="text-muted small">${frappe.utils.escape_html(__(x.note))}</div>` : ""}</td><td>${badge(x.level)}</td><td>${st}</td><td class="text-right">${btns}</td></tr>`;
		}).join("");
		const other = (r.files || []).filter((f) => !f.hs_document_type);
		const typed = `<table class="table table-sm" style="margin:0">${rows}</table>`
			+ (other.length ? `<div class="small text-muted" style="margin-top:6px">${__("Attachments without a type")}: ${other.map((f) =>
				`<a class="hs-settype" data-file="${f.name}">${frappe.utils.escape_html(f.file_name || f.name)}</a>`).join(", ")} — ${__("click one to give it a type")}</div>` : "");
		const sec = frm.dashboard.add_section(typed, __("Documents"));
		sec.addClass("hs-docs-section");
		sec.find(".hs-attach").on("click", (e) => hipersign.docs.attach(frm, $(e.currentTarget).data("type")));
		sec.find(".hs-waive").on("click", (e) => hipersign.docs.waive(frm, $(e.currentTarget).data("type"), $(e.currentTarget).data("role")));
		sec.find(".hs-settype").on("click", (e) => hipersign.docs.set_type(frm, $(e.currentTarget).data("file")));
	});
};

hipersign.docs.attach = function (frm, document_type) {
	new frappe.ui.FileUploader({
		doctype: frm.doctype, docname: frm.docname, frm, folder: "Home/Attachments", allow_multiple: false,
		on_success(file) {
			frappe.xcall("hipersign_trading.api.docs.set_file_type", { file: file.name, document_type }).then(() => {
				frappe.show_alert({ message: __("{0} attached — you can carry on", [__(document_type)]), indicator: "green" });
				frm.reload_doc();
			});
		},
	});
};

hipersign.docs.set_type = function (frm, file) {
	frappe.xcall("hipersign_trading.api.docs.document_types").then((types) => frappe.prompt(
		{ fieldtype: "Select", fieldname: "t", label: __("Document type"), options: [""].concat(types), reqd: 1 },
		(v) => frappe.xcall("hipersign_trading.api.docs.set_file_type", { file, document_type: v.t }).then(() => frm.reload_doc()), __("Document type")));
};

hipersign.docs.waive = function (frm, document_type, role) {
	frappe.prompt([
		{ fieldtype: "HTML", options: `<p>${__("Carry on without the {0} for now. The {1} approves the exception; the document stays due until it is attached.", [__(document_type), __(role || "approver")])}</p>` },
		{ fieldtype: "Small Text", fieldname: "reason", label: __("Reason"), reqd: 1 },
		{ fieldtype: "Date", fieldname: "due_date", label: __("Document expected by"), reqd: 1, default: frappe.datetime.add_days(frappe.datetime.get_today(), 7) },
	], (v) => frappe.xcall("hipersign_trading.api.docs.request_waiver", { doctype: frm.doctype, name: frm.docname, document_type, reason: v.reason, due_date: v.due_date })
		.then((name) => frappe.db.get_value("Document Waiver", name, "status").then(({ message }) => {
			frappe.show_alert({ message: message.status === "Approved" ? __("Exception {0} approved — you can carry on", [name]) : __("Exception {0} sent for approval", [name]),
				indicator: message.status === "Approved" ? "green" : "orange" });
			frm.reload_doc();
		})), __("Request exception"), __("Send"));
};

(function () {
	const list = new Set(hipersign.docs.DEFAULT.concat((frappe.boot && frappe.boot.hipersign && frappe.boot.hipersign.ruled_doctypes) || []));
	list.forEach((dt) => frappe.ui.form.on(dt, {
		refresh(frm) {
			const info = hipersign.info();
			if ((info.ruled_doctypes || []).includes(frm.doctype)) hipersign.docs.render(frm);
		},
	}));
})();
