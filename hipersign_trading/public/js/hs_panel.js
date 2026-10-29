// Hipersign ERP v1.6.0 — the record panel: the prototype's side panel that opens over the page instead of the full form.
// The server describes the panel (hipersign_trading.api.panel.get_panel); this file draws it and runs its buttons.
// Links inside a panel open the linked record's panel; Back returns to the previous one; Close returns to the page.
frappe.provide("hipersign.panel");

hipersign.panel.TYPES = ["Lead", "Quotation", "Sales Order", "Customer", "Sales Invoice", "Delivery Note", "Item"];
hipersign.panel.has = (dt) => hipersign.panel.TYPES.includes(dt) && !((frappe.boot.hipersign || {}).no_panels);
hipersign.panel.stack = [];

const hp_esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));

hipersign.panel.value = function (v) {
	if (v === null || v === undefined || v === "") return "—";
	if (typeof v !== "object") return hp_esc(typeof v === "number" ? format_number(v, null, v % 1 ? 2 : 0) : v);
	if (v.link) return `<a class="hp-link" data-dt="${hp_esc(v.link[0])}" data-name="${hp_esc(v.link[1])}">${hp_esc(v.label || v.link[1])}</a>`;
	if (v.pill !== undefined) return `<span class="hsx-pill ${hp_esc(v.tone || "grey")}">${hp_esc(v.pill)}</span>`;
	if (v.bar !== undefined) return `<span class="hp-bar"><span style="width:${Math.max(0, Math.min(100, v.bar))}%"></span></span><b>${format_number(v.bar, null, 0)}%</b>`;
	if (v.money !== undefined) return hp_esc(hipersign.ui ? hipersign.ui.money(v.money, v.currency) : format_currency(v.money, v.currency));
	return hp_esc(JSON.stringify(v));
};

hipersign.panel.plain = function (v) {
	if (v === null || v === undefined) return "";
	if (typeof v !== "object") return v;
	if (v.link) return v.label || v.link[1];
	if (v.pill !== undefined) return v.pill;
	if (v.bar !== undefined) return v.bar + "%";
	if (v.money !== undefined) return v.money;
	return "";
};

hipersign.panel.$el = function () {
	let $p = $(".hp-panel");
	if (!$p.length) {
		$p = $(`<div class="hp-backdrop"></div><aside class="hp-panel" role="dialog" aria-modal="true"><div class="hp-inner"></div></aside>`).appendTo("body").filter(".hp-panel");
		$(".hp-backdrop").on("click", () => hipersign.panel.close());
		$(document).on("keydown.hp", (e) => { if (e.key === "Escape" && $("body").hasClass("hp-open") && !$(".modal.show").length) hipersign.panel.close(); });
	}
	return $p;
};

hipersign.panel.open = function (dt, name, opts) {
	opts = opts || {};
	if (!hipersign.panel.has(dt)) return frappe.set_route("Form", dt, name);
	if (!opts.back) {
		if (!opts.keep) hipersign.panel.stack = [];
		hipersign.panel.stack.push([dt, name]);
	}
	const $p = hipersign.panel.$el();
	$("body").addClass("hp-open");
	$p.find(".hp-inner").html(`<div class="hp-head"><div><h2>${hp_esc(name)}</h2><div class="hp-sub">${hp_esc(__(dt))}</div></div>
		<button class="btn btn-default btn-sm hp-close" title="${__("Close")}">${frappe.utils.icon("close", "sm")}</button></div><div class="hsx-loading">${__("Loading…")}</div>`);
	$p.find(".hp-close").on("click", () => hipersign.panel.close());
	return frappe.xcall("hipersign_trading.api.panel.get_panel", { doctype: dt, name })
		.then((p) => { hipersign.panel.current = p; hipersign.panel.render(p); })
		.catch(() => hipersign.panel.close());
};

hipersign.panel.refresh = function () {
	const c = hipersign.panel.current;
	if (c) hipersign.panel.open(c.doctype, c.name, { back: true });
};

hipersign.panel.close = function () {
	$("body").removeClass("hp-open");
	hipersign.panel.current = null;
	hipersign.panel.stack = [];
};

hipersign.panel.render = function (p) {
	const $p = hipersign.panel.$el();
	const back = hipersign.panel.stack.length > 1;
	const facts = (p.facts || []).length ? `<div class="hp-card hp-facts">${p.facts.map(([l, v]) => `<div class="hp-fact"><span>${hp_esc(l)}</span><b>${hipersign.panel.value(v)}</b></div>`).join("")}</div>` : "";
	const prog = p.progress ? `<div class="hp-progress">${p.progress.steps.map((s, i) => {
		const st = i < p.progress.current ? "done" : i === p.progress.current ? "cur" : "";
		return `<div class="hp-step ${st}"><span class="hp-dot">${st === "done" ? frappe.utils.icon("check", "xs") : i + 1}</span><span class="hp-sl">${hp_esc(s)}</span></div>`;
	}).join("")}</div>` : "";
	const approval = p.approval ? `<div class="hp-card hp-approval"><div class="hp-ch"><h4>${frappe.utils.icon("inbox", "sm")} ${__("Approval")}</h4>${hipersign.panel.pill(p.approval.state, "orange")}</div>
		<p>${__("Waiting for the {0}", [hp_esc(p.approval.waiting_for)])}${p.approval.reason ? ` — ${hp_esc(p.approval.reason)}` : ""}</p>
		${(p.approval.actions || []).length ? `<div class="hp-btns">${p.approval.actions.map((a) => `<button class="btn btn-sm ${/reject/i.test(a) ? "btn-default hp-danger" : "btn-primary"} hp-wf" data-a="${hp_esc(a)}">${hp_esc(__(a))}</button>`).join("")}</div>` : ""}</div>` : "";
	const sections = (p.sections || []).map((s, k) => hipersign.panel.section(s, k)).join("");
	const docs = hipersign.panel.docs(p);
	const hist = (p.history || []).length ? `<div class="hp-card"><div class="hp-ch"><h4>${frappe.utils.icon("clock", "sm")} ${__("History")}</h4></div>
		<ul class="hp-hist">${p.history.map(([w, t]) => `<li><span>${hp_esc(w)}</span>${hp_esc(t)}</li>`).join("")}</ul></div>` : "";
	const acts = p.actions || [];
	const primary = acts.filter((a) => a.kind === "primary");
	const others = acts.filter((a) => a.kind !== "primary");
	$p.find(".hp-inner").html(`
		<div class="hp-head"><div>${back ? `<a class="hp-back">${frappe.utils.icon("left", "xs")} ${__("Back")}</a>` : ""}<h2>${hp_esc(p.title)}</h2>
			<div class="hp-sub">${hp_esc(p.subtitle)} ${hipersign.panel.value(p.status)}</div></div>
			<div class="hp-hbtn"><button class="btn btn-default btn-sm hp-full" title="${__("Open the full form")}">${frappe.utils.icon("external-link", "sm")}</button>
			<button class="btn btn-default btn-sm hp-close" title="${__("Close")}">${frappe.utils.icon("close", "sm")}</button></div></div>
		<div class="hp-body">${prog}${facts}${approval}${sections}${docs}${hist}</div>
		<div class="hp-foot"><div class="hp-btns">
			<button class="btn btn-default btn-sm hp-msg">${frappe.utils.icon("message-square", "sm")} ${__("Message")}${p.unread ? ` <span class="hp-n">${p.unread}</span>` : ""}</button>
			<button class="btn btn-default btn-sm hp-email">${frappe.utils.icon("mail", "sm")} ${__("Email")}</button>
			<button class="btn btn-default btn-sm hp-wa">${__("WhatsApp")}</button>
			<button class="btn btn-default btn-sm hp-print" title="${__("Print")}">${frappe.utils.icon("printer", "sm")}</button>
			${others.map((a, i) => `<button class="btn btn-default btn-sm hp-act" data-i="${acts.indexOf(a)}">${hp_esc(a.label)}</button>`).join("")}</div>
			${primary.length ? `<div class="hp-btns hp-prim">${primary.map((a) => `<button class="btn btn-primary btn-sm hp-act" data-i="${acts.indexOf(a)}">${hp_esc(a.label)}</button>`).join("")}</div>` : ""}
		</div>`);
	hipersign.panel.bind($p, p);
};

hipersign.panel.pill = (t, tone) => `<span class="hsx-pill ${tone || "grey"}">${hp_esc(t)}</span>`;

hipersign.panel.section = function (s, k) {
	const acts = (s.actions || []).map((a, i) => `<button class="btn btn-default btn-xs hp-sact" data-k="${k}" data-i="${i}">${hp_esc(a.label)}</button>`).join(" ");
	let body;
	if (s.kind === "kv") {
		body = s.rows.length ? `<div class="hp-kv">${s.rows.map(([l, v]) => `<div class="hp-fact"><span>${hp_esc(l)}</span><b>${hipersign.panel.value(v)}</b></div>`).join("")}</div>`
			: s.sub ? "" : `<div class="text-muted small">${__("Nothing yet.")}</div>`;
	} else {
		body = s.rows.length ? `<div class="hp-tw"><table class="hp-t"><thead><tr>${s.cols.map((c) => `<th>${hp_esc(c)}</th>`).join("")}</tr></thead>
			<tbody>${s.rows.map((r) => `<tr>${r.map((c) => `<td>${hipersign.panel.value(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
			: `<div class="text-muted small">${__("Nothing yet.")}</div>`;
	}
	const xl = s.kind === "table" && s.rows.length ? `<button class="btn btn-default btn-xs hp-xl" data-k="${k}" title="${__("Download for Excel")}">${frappe.utils.icon("file", "xs")} ${__("Excel")}</button>` : "";
	return `<div class="hp-card"><div class="hp-ch"><h4>${hp_esc(s.title)}${s.sub ? ` <small>${hp_esc(s.sub)}</small>` : ""}</h4><div>${acts} ${xl}</div></div>${body}</div>`;
};

hipersign.panel.docs = function (p) {
	if (!p.documents || !p.documents.length) return "";
	const missing = p.documents.filter((x) => !x.attached && !x.waiver && x.level !== "Optional").length;
	return `<div class="hp-card"><div class="hp-ch"><h4>${frappe.utils.icon("file", "sm")} ${__("Documents")}${missing ? ` ${hipersign.panel.pill(__("{0} missing", [missing]), "red")}` : ""}</h4>
		<div><button class="btn btn-default btn-xs hp-attach" data-type="">${__("Attach other file")}</button></div></div>
		${p.documents.map((x) => `<div class="hp-doc ${!x.attached && !x.waiver && x.level !== "Optional" ? "miss" : ""}"><div><b>${hp_esc(x.type)}</b>${x.note ? `<div class="small text-muted">${hp_esc(x.note)}</div>` : ""}</div>
			<div>${x.attached ? `<span class="text-success">${frappe.utils.icon("check", "xs")} ${__("On file")}</span>` : x.waiver ? hipersign.panel.pill(__("Exception {0}", [x.waiver]), "orange")
				: `<span class="${x.level === "Optional" ? "text-muted" : "text-danger"}">${x.level === "Optional" ? __("Optional") : __("Required — missing")}</span> <button class="btn btn-default btn-xs hp-attach" data-type="${hp_esc(x.raw)}">${__("Attach")}</button>`}</div></div>`).join("")}</div>`;
};

hipersign.panel.bind = function ($p, p) {
	const dt = p.doctype, name = p.name;
	$p.find(".hp-close").on("click", () => hipersign.panel.close());
	$p.find(".hp-full").on("click", () => { hipersign.panel.close(); frappe.set_route("Form", dt, name); });
	$p.find(".hp-back").on("click", () => {
		hipersign.panel.stack.pop();
		const prev = hipersign.panel.stack[hipersign.panel.stack.length - 1];
		if (prev) hipersign.panel.open(prev[0], prev[1], { back: true });
	});
	$p.find(".hp-link").on("click", function () {
		const ldt = $(this).attr("data-dt"), ln = $(this).attr("data-name");
		if (hipersign.panel.has(ldt)) hipersign.panel.open(ldt, ln, { keep: true });
		else { hipersign.panel.close(); frappe.set_route("Form", ldt, ln); }
	});
	$p.find(".hp-xl").on("click", function () {
		const s = p.sections[+$(this).attr("data-k")];
		frappe.tools.downloadify([s.cols].concat(s.rows.map((r) => r.map(hipersign.panel.plain))), null, `${name} ${s.title}`);
	});
	$p.find(".hp-act").on("click", function () { hipersign.panel.run(p, p.actions[+$(this).attr("data-i")], $(this)); });
	$p.find(".hp-sact").on("click", function () { hipersign.panel.run(p, p.sections[+$(this).attr("data-k")].actions[+$(this).attr("data-i")], $(this)); });
	$p.find(".hp-wf").on("click", function () {
		const a = $(this).attr("data-a");
		$(this).prop("disabled", true);
		frappe.db.get_doc(dt, name).then((doc) => frappe.xcall("frappe.model.workflow.apply_workflow", { doc, action: a }))
			.then(() => { frappe.show_alert({ message: __("{0}: {1}", [name, __(a)]), indicator: "green" }); $(document).trigger("hp-changed"); hipersign.panel.refresh(); })
			.catch(() => $(this).prop("disabled", false));
	});
	$p.find(".hp-attach").on("click", function () {
		const type = $(this).attr("data-type");
		new frappe.ui.FileUploader({ doctype: dt, docname: name, folder: "Home/Attachments", allow_multiple: false,
			on_success(file) {
				(type ? frappe.xcall("hipersign_trading.api.docs.set_file_type", { file: file.name, document_type: type }) : Promise.resolve())
					.then(() => { frappe.show_alert({ message: __("Attached"), indicator: "green" }); hipersign.panel.refresh(); });
			} });
	});
	$p.find(".hp-msg").on("click", () => hipersign.panel.messages(dt, name));
	$p.find(".hp-email").on("click", () => frappe.db.get_doc(dt, name).then((doc) => new frappe.views.CommunicationComposer({
		doc, frm: null, subject: `${__(dt)}: ${name}`, recipients: doc.contact_email || doc.email_id || "", attach_document_print: true,
		real_name: doc.customer_name || doc.lead_name || "" })));
	$p.find(".hp-wa").on("click", () => hipersign.send_whatsapp(dt, name));
	$p.find(".hp-print").on("click", () => window.open(frappe.urllib.get_full_url(`/printview?doctype=${encodeURIComponent(dt)}&name=${encodeURIComponent(name)}&trigger_print=1`)));
};

hipersign.panel.run = function (p, a, $btn) {
	if (!a) return;
	const dt = p.doctype, name = p.name;
	const done = (r) => {
		if (r && r.message) frappe.show_alert({ message: r.message, indicator: "green" }, 5);
		$(document).trigger("hp-changed");
		if (r && r.route) { hipersign.panel.close(); frappe.set_route(...r.route); } else hipersign.panel.refresh();
	};
	if (a.route) { hipersign.panel.close(); if (a.options) frappe.route_options = a.options; return frappe.set_route(...a.route); }
	if (a.print_format) return window.open(frappe.urllib.get_full_url(`/printview?doctype=${encodeURIComponent(dt)}&name=${encodeURIComponent(name)}&format=${encodeURIComponent(a.print_format)}`));
	if (a.make) {
		$btn && $btn.prop("disabled", true);
		return frappe.xcall("hipersign_trading.api.panel.make", { method: a.make, source_name: name }).then((doc) => {
			const d = frappe.model.sync(doc)[0];
			hipersign.panel.close();
			frappe.set_route("Form", d.doctype, d.name);
		}).finally(() => $btn && $btn.prop("disabled", false));
	}
	if (a.action) {
		const go = () => frappe.xcall("hipersign_trading.api.panel.action", { doctype: dt, name, action: a.action, args: a.args || {} }).then(done);
		return a.confirm ? frappe.confirm(a.confirm, go) : go();
	}
	if (a.client && hipersign.panel.clients[a.client]) return hipersign.panel.clients[a.client](p, a.args || {}, done);
};

// ---------------------------------------------------------------- buttons that need a small dialog
hipersign.panel.clients = {
	log_activity(p) {
		frappe.xcall("frappe.client.get_value", { doctype: "Lead", filters: { name: p.name }, fieldname: ["hs_pipeline_stage", "hs_next_follow_up", "hs_next_action"] }).then((cur) => {
			const d = new frappe.ui.Dialog({ title: __("Log activity"), fields: [
				{ fieldtype: "Select", fieldname: "activity", label: __("Activity"), options: ["Call", "Meeting", "Site visit", "WhatsApp", "Email", "Note"].map((x) => ({ value: x, label: __(x) })), default: "Call" },
				{ fieldtype: "Select", fieldname: "stage", label: __("Stage after this"), options: ["New", "Contacted", "Qualified", "Proposal", "Negotiation"].map((x) => ({ value: x, label: __(x) })), default: cur.hs_pipeline_stage },
				{ fieldtype: "Small Text", fieldname: "text", label: __("What happened"), reqd: 1 },
				{ fieldtype: "Column Break" },
				{ fieldtype: "Date", fieldname: "next_follow_up", label: __("Next follow-up"), default: cur.hs_next_follow_up },
				{ fieldtype: "Data", fieldname: "next_action", label: __("Next action"), default: cur.hs_next_action },
			], primary_action_label: __("Save"), primary_action(v) {
				frappe.xcall("hipersign_trading.api.crm.log_activity", Object.assign({ lead: p.name }, v)).then(() => { d.hide(); hipersign.panel.refresh(); });
			} });
			d.show();
		});
	},
	lead_lost(p, args, done) {
		const opts = ((frappe.meta.get_docfield("Lead", "hs_lost_reason") || {}).options || "").split("\n").filter(Boolean);
		frappe.prompt([{ fieldtype: opts.length ? "Select" : "Data", fieldname: "reason", label: __("Reason"), options: opts.join("\n"), reqd: 1 },
			{ fieldtype: "Small Text", fieldname: "note", label: __("Details") }],
		(v) => frappe.xcall("hipersign_trading.api.panel.action", { doctype: "Lead", name: p.name, action: "lead_stage", args: { stage: "Lost", reason: v.reason, note: v.note } }).then(done),
		__("Lead lost"), __("Mark as lost"));
	},
	quote_lost(p, args, done) {
		frappe.prompt([{ fieldtype: "Link", fieldname: "reason", label: __("Reason"), options: "Quotation Lost Reason", reqd: 1 },
			{ fieldtype: "Small Text", fieldname: "note", label: __("Details") }],
		(v) => frappe.xcall("hipersign_trading.api.panel.action", { doctype: "Quotation", name: p.name, action: "quote_lost", args: v }).then(done),
		__("Quotation lost"), __("Mark as lost"));
	},
	receive_advance(p) {
		frappe.xcall("hipersign_trading.overrides.advances.advance_payment_entry", { sales_order: p.name }).then((doc) => {
			const d = frappe.model.sync(doc)[0];
			hipersign.panel.close();
			frappe.set_route("Form", d.doctype, d.name);
		});
	},
	record_payment(p) {
		if (hipersign.fm && hipersign.fm.quick_receive) {
			frappe.db.get_value("Sales Invoice", p.name, "customer").then(({ message }) => { hipersign.panel.close(); hipersign.fm.quick_receive({ party: message.customer }); });
			return;
		}
		frappe.xcall("erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry", { dt: "Sales Invoice", dn: p.name }).then((doc) => {
			const d = frappe.model.sync(doc)[0];
			hipersign.panel.close();
			frappe.set_route("Form", d.doctype, d.name);
		});
	},
	credit_limit(p) {
		hipersign.panel.close();
		frappe.new_doc("Credit Limit Request", { customer: p.name });
	},
	new_contact(p) {
		hipersign.qc.open("Contact", { values: { link_doctype: p.doctype, link_name: p.name }, open: false }).then(() => setTimeout(() => {
			if (cur_dialog) cur_dialog.$wrapper.one("hidden.bs.modal", () => hipersign.panel.refresh());
		}, 300));
	},
	new_address(p) {
		hipersign.qc.open("Address", { values: { link_doctype: p.doctype, link_name: p.name }, open: false }).then(() => setTimeout(() => {
			if (cur_dialog) cur_dialog.$wrapper.one("hidden.bs.modal", () => hipersign.panel.refresh());
		}, 300));
	},
	quick_doc(p, args) {
		const dt = args.doctype;
		hipersign.panel.close();
		const v = dt === "Purchase Order" ? { items: [{ item_code: args.item, qty: 1 }] } : { party: p.name };
		if (hipersign.fm && hipersign.fm.quick_doc) hipersign.fm.quick_doc(dt, v);
		else frappe.new_doc(dt);
	},
};

// ---------------------------------------------------------------- Message: the record's conversation
hipersign.panel.messages = function (dt, name) {
	const d = new frappe.ui.Dialog({ title: __("Messages — {0}", [name]), size: "large", fields: [
		{ fieldtype: "HTML", fieldname: "thread" },
		{ fieldtype: "Comment", fieldname: "text", label: __("Message"), enable_mentions: 1 },
	], primary_action_label: __("Send"), primary_action(v) {
		if (!v.text || !strip_html(v.text).trim()) return;
		frappe.xcall("hipersign_trading.api.messages.post", { doctype: dt, name, text: v.text }).then((t) => { show(t); d.set_value("text", ""); });
	} });
	const show = (t) => d.fields_dict.thread.$wrapper.html(`<div class="hp-thread">${(t.items || []).map((i) =>
		`<div class="hp-m ${i.kind}"><div class="small text-muted">${hp_esc(i.who)} · ${hp_esc(frappe.datetime.str_to_user(i.when))}${i.meta ? " · " + hp_esc(i.meta) : ""}</div><div>${i.html}</div></div>`).join("")
		|| `<p class="text-muted">${__("No messages yet — write the first one below; @mention a colleague to notify them.")}</p>`}</div>`);
	frappe.xcall("hipersign_trading.api.messages.thread", { doctype: dt, name }).then(show);
	d.show();
};

// ---------------------------------------------------------------- open panels in place
// Hipersign pages route records through hipersign.ui.go; a record with a panel opens it there.
(function () {
	const wrap = () => {
		if (!hipersign.ui || !hipersign.ui.go || hipersign.ui.go.__hp) return;
		const orig = hipersign.ui.go;
		hipersign.ui.go = function (route, options) {
			if (route && route[0] === "Form" && route.length === 3 && hipersign.panel.has(route[1]) && !String(route[2]).startsWith("new-")) return hipersign.panel.open(route[1], route[2]);
			return orig(route, options);
		};
		hipersign.ui.go.__hp = true;
	};
	wrap();
	$(document).on("page-change", () => { wrap(); if ($("body").hasClass("hp-open")) hipersign.panel.close(); });
})();

// ERPNext lists of these record types open the panel too (the arrow at the top of the panel opens the full form)
document.addEventListener("click", function (e) {
	if (!document.documentElement.classList.contains("hs-theme") || e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
	const row = e.target.closest && e.target.closest(".frappe-list .list-row-container");
	if (!row || e.target.closest("input, .list-row-checkbox, .like-action, .comment-count, .avatar, .btn, .dropdown, .list-row-like, .filterable")) return;
	const lv = window.cur_list;
	if (!lv || !hipersign.panel.has(lv.doctype) || lv.view_name !== "List") return;
	const a = row.querySelector("a[data-name]") || row.querySelector("[data-name]");
	const name = a && (a.getAttribute("data-name") || "");
	if (!name) return;
	e.preventDefault();
	e.stopPropagation();
	hipersign.panel.open(lv.doctype, decodeURIComponent(name));
}, true);

// links to these records on Hipersign pages (Order Tracker, Approvals, Alerts, Trade Journey …) open the panel in place
document.addEventListener("click", function (e) {
	if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0 || !e.target.closest) return;
	const a = e.target.closest("a[href]");
	if (!a || a.closest(".hp-panel") || a.target === "_blank") return;
	const route = frappe.get_route() || [];
	if (!route.length || ["Form", "List", "Tree", "query-report", "Workspaces", "print"].includes(route[0])) return;
	const m = (a.getAttribute("href") || "").match(/^\/(?:app|desk)\/([a-z0-9-]+)\/([^/?#]+)$/);
	if (!m) return;
	const dt = hipersign.panel.TYPES.find((t) => frappe.router.slug(t) === m[1]);
	if (!dt || !hipersign.panel.has(dt) || m[2].startsWith("new-")) return;
	e.preventDefault();
	e.stopPropagation();
	hipersign.panel.open(dt, decodeURIComponent(m[2]));
}, true);
