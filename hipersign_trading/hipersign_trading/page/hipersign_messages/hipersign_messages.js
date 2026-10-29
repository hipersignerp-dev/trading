// Messages — the conversations kept on orders, shipments, invoices and leads, in one inbox.
frappe.pages["hipersign-messages"].on_page_load = function (wrapper) {
	const ui = hipersign.ui;
	const v = ui.page(wrapper, {
		title: __("Messages"),
		desc: __("Comments, @mentions, emails and WhatsApp sends kept on each record — in one inbox. Writing here adds a comment to the record, as on the form."),
	});
	const st = { box: "all", doctype: "", list: [], types: [], current: null };
	v.$actions.html(
		`<button class="btn btn-sm btn-primary hsx-newmsg">${frappe.utils.icon("add", "sm")} ${__("New message on a record")}</button> ` +
		ui.seg("box", [["all", __("All")], ["mentions", __("Mentions")], ["mine", __("I'm in")], ["email", __("Email")], ["whatsapp", "WhatsApp"]], st.box) +
			`<select class="hsx-select hsx-dt"><option value="">${__("All records")}</option></select>`
	);
	v.$body.html(`<div class="hsx-card"><div class="hsx-msg"><div class="hsx-msg-list"></div><div class="hsx-thread"></div></div></div>`);
	const $list = v.$body.find(".hsx-msg-list");
	const $thread = v.$body.find(".hsx-thread");
	let control = null;

	const ago = (d) => frappe.datetime.prettyDate ? frappe.datetime.prettyDate(d, true) : comment_when(d, true);
	const kindPill = (k) => ({ email: ui.pill(__("Email"), "blue"), whatsapp: ui.pill("WhatsApp", "green"), note: ui.pill(__("Comment"), "grey") }[k] || "");

	function render_list() {
		if (!st.list.length) {
			$list.html(`<div class="hsx-empty">${__("No conversations in the last 60 days.")}</div>`);
			return;
		}
		$list.html(
			st.list
				.map((c, i) => `<button class="hsx-conv ${st.current && st.current.doctype === c.doctype && st.current.name === c.name ? "on" : ""}" data-i="${i}">
				<div class="h"><b>${c.mention ? "● " : ""}${ui.esc(c.title)}</b><span>${ui.esc(ago(c.last.when))}</span></div>
				<p><b>${ui.esc(c.last.who)}:</b> ${ui.esc(c.last.text)}</p>
				<div style="display:flex;gap:4px;flex-wrap:wrap">${ui.pill(__(c.doctype), "violet")} ${c.kinds.map(kindPill).join(" ")} <span class="text-muted small">${c.count}</span></div></button>`)
				.join("")
		);
	}

	function render_thread(t) {
		st.current = { doctype: t.doctype, name: t.name };
		const me = frappe.session.user;
		const items = t.items.length
			? t.items
					.map((m) => `<div class="hsx-bubble ${m.kind === "system" ? "system" : m.user === me && m.kind !== "email" ? "me" : ""}">
					${m.kind === "system" ? "" : `<div class="who"><b>${ui.esc(m.who)}</b> · ${ui.esc(ago(m.when))} ${m.kind === "email" ? ui.pill(__("Email"), "blue") : ""} ${m.meta ? ui.esc(m.meta) : ""}</div>`}
					<div>${m.html}</div>${m.kind === "system" ? `<div class="small">${ui.esc(ago(m.when))}</div>` : ""}</div>`)
					.join("")
			: `<div class="hsx-empty">${__("No messages yet — write the first one.")}</div>`;
		$thread.html(`<div class="hsx-thread-h"><div><b>${ui.esc(t.title)}</b><div class="text-muted small">${ui.esc(__(t.doctype))} · ${ui.esc(t.name)}</div></div>
			<button class="btn btn-xs btn-default" data-hs-route='${ui.esc(JSON.stringify(["Form", t.doctype, t.name]))}'>${__("Open record")} →</button></div>
			<div class="hsx-thread-b">${items}</div>
			<div class="hsx-thread-f"><div class="hsx-box"></div><div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px">
			<span class="text-muted small">${__("Type @ to mention a colleague — they get a notification.")}</span><button class="btn btn-sm btn-primary hsx-send">${__("Send")}</button></div></div>`);
		control = frappe.ui.form.make_control({
			parent: $thread.find(".hsx-box"),
			// v1.5.6 (MSG-01): Frappe offers the @ people picker only when enable_mentions is set
			df: { fieldtype: "Comment", fieldname: "hs_msg", placeholder: __("Write a message…"), enable_mentions: 1 },
			render_input: true,
			only_input: true,
		});
		const $b = $thread.find(".hsx-thread-b");
		$b.scrollTop($b[0].scrollHeight);
		render_list();
	}

	function open(c) {
		$thread.html(`<div class="hsx-loading">${__("Loading…")}</div>`);
		frappe.xcall("hipersign_trading.api.messages.thread", { doctype: c.doctype, name: c.name }).then((t) => {
			c.mention = 0;
			render_thread(t);
		});
	}

	$list.on("click", ".hsx-conv", function () {
		open(st.list[cint($(this).attr("data-i"))]);
	});
	$thread.on("click", ".hsx-send", function () {
		const text = control && control.get_value ? control.get_value() : "";
		if (!text || !strip_html(text).trim()) return;
		const $btn = $(this).prop("disabled", true);
		frappe
			.xcall("hipersign_trading.api.messages.post", { doctype: st.current.doctype, name: st.current.name, text })
			.then((t) => {
				render_thread(t);
				load(true);
			})
			.finally(() => $btn.prop("disabled", false));
	});
	// v1.5.6 (MSG-03): start a conversation on any record
	v.$actions.on("click", ".hsx-newmsg", function () {
		const d = new frappe.ui.Dialog({
			title: __("New message on a record"),
			fields: [
				{ fieldtype: "Link", fieldname: "doctype", label: __("Record type"), options: "DocType", reqd: 1,
					get_query: () => ({ filters: { istable: 0, issingle: 0, name: ["in", ["Sales Order", "Quotation", "Lead", "Customer", "Supplier", "Purchase Order",
						"Import Shipment", "Export Shipment", "Delivery Note", "Sales Invoice", "Purchase Invoice", "Payment Entry", "Letter of Credit", "Item",
						"Post Dated Cheque", "Material Request", "Purchase Receipt", "Employee", "Asset", "Tax Return", "Warranty Claim"]] } }) },
				{ fieldtype: "Dynamic Link", fieldname: "name", label: __("Record"), options: "doctype", reqd: 1 },
				{ fieldtype: "Comment", fieldname: "text", label: __("Message"), enable_mentions: 1, reqd: 1 },
			],
			primary_action_label: __("Send"),
			primary_action(val) {
				if (!val.text || !strip_html(val.text).trim()) return;
				frappe.xcall("hipersign_trading.api.messages.post", { doctype: val.doctype, name: val.name, text: val.text }).then((t) => {
					d.hide();
					render_thread(t);
					load(true);
				});
			},
		});
		d.show();
	});
	v.$actions.on("click", "[data-seg=box] button", function () {
		st.box = $(this).attr("data-v");
		$(this).addClass("on").siblings().removeClass("on");
		load();
	});
	v.$actions.on("change", ".hsx-dt", function () {
		st.doctype = $(this).val();
		load();
	});

	function load(keep) {
		if (!keep) $list.html(`<div class="hsx-loading">${__("Loading…")}</div>`);
		frappe.xcall("hipersign_trading.api.messages.conversations", { box: st.box, doctype: st.doctype || null }).then((r) => {
			st.list = r.conversations;
			const $dt = v.$actions.find(".hsx-dt");
			if ($dt.find("option").length === 1) r.types.forEach((t) => $dt.append(`<option value="${ui.esc(t)}">${ui.esc(__(t))}</option>`));
			render_list();
			if (!keep) {
				if (st.list.length) open(st.list[0]);
				else $thread.html(`<div class="hsx-empty" style="margin:auto">${__("Pick a conversation.")}</div>`);
			}
		});
	}
	wrapper.hs_load = load;
	load();
};

frappe.pages["hipersign-messages"].on_page_show = function (wrapper) {
	if (wrapper.hs_shown && wrapper.hs_load) wrapper.hs_load(true);
	wrapper.hs_shown = 1;
};
