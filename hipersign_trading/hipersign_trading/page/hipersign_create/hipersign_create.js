// Create New — one place to add any record or document (v1.5.6: the prototype's groups, as a list; documents with
// form modes open in the user's mode, or in the one clicked on the row).
frappe.pages["hipersign-create"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Create New"), single_column: true });
	const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
	const $root = $(`<div class="hs-create-list"></div>`).appendTo(page.main);
	let entries = [];

	function render() {
		entries = [];
		const groups = hipersign.create.visible();
		if (!groups.length) {
			$root.html(`<p class="text-muted">${esc(__("Nothing you can create here — ask your administrator for access."))}</p>`);
			return;
		}
		$root.html(groups.map(([g, items]) => `<section class="hs-cl-group"><h5>${esc(g)}</h5>${items.map(([label, icon, a]) => {
			const k = entries.push(a) - 1;
			const modes = !a.full && hipersign.create.has_modes(a.dt);
			const cur = modes ? hipersign.fm.mode(a.dt) : null;
			const quick_ok = modes && (hipersign.fm.quick_kinds || []).includes(a.dt);
			const chips = modes
				? `<span class="hs-cl-modes">${hipersign.fm.MODES.filter((m) => m !== "Quick" || quick_ok).map((m) =>
					`<button type="button" class="hsx-chip ${m === cur ? "on" : ""}" data-k="${k}" data-mode="${m}" title="${esc(__("Open in {0} and remember it", [__(m)]))}">${esc(__(m))}</button>`).join("")}</span>`
				: "";
			return `<div class="hs-cl-row" data-k="${k}" tabindex="0">${frappe.utils.icon(icon, "md")}<span class="hs-cl-label">${esc(label)}</span>
				<span class="hs-cl-sub text-muted">${esc(a.route ? __("Opens a page") : modes ? __("Opens in {0}", [__(cur)]) : __("Opens the form"))}</span>${chips}</div>`;
		}).join("")}</section>`).join(""));
	}

	$root.on("click", ".hs-cl-row", function (e) {
		const $chip = $(e.target).closest("[data-mode]");
		const a = entries[+$(this).attr("data-k")];
		if (!a) return;
		hipersign.create.open(a, $chip.length ? $chip.attr("data-mode") : undefined);
		if ($chip.length) setTimeout(render, 300);
	});
	$root.on("keydown", ".hs-cl-row", function (e) {
		if (e.key === "Enter") $(this).trigger("click");
	});
	render();
	$(wrapper).on("show", render);
};
