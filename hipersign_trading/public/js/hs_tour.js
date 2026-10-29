// Hipersign ERP v1.6.0 — the guided tour: the prototype's 13 chapters (steps in tour/tour.json, served by
// hipersign_trading.api.tour.get_tour). Each step opens a page, highlights one part and explains it. It only reads and
// points, so it is safe on any site. Chapters and steps follow the user's permissions and the feature pack.
frappe.provide("hipersign.tour");

const ht_esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));

hipersign.tour.start = function (chapter) {
	frappe.xcall("hipersign_trading.api.tour.get_tour").then((t) => {
		if (!t.steps.length) return frappe.msgprint(__("There is nothing to show for your role yet."));
		hipersign.tour.data = t;
		let i = 0;
		if (chapter !== undefined) i = Math.max(0, t.steps.findIndex((s) => s.chapter === chapter));
		hipersign.tour.go(i);
	});
};

hipersign.tour.end = function () {
	$(".ht-box, .ht-card").remove();
	hipersign.tour.i = null;
	$(window).off("resize.ht scroll.ht");
};

hipersign.tour.go = function (i) {
	const t = hipersign.tour.data;
	if (!t || i < 0 || i >= t.steps.length) return hipersign.tour.end();
	hipersign.tour.i = i;
	const s = t.steps[i];
	if (hipersign.panel && hipersign.panel.close) hipersign.panel.close();
	const here = (frappe.get_route() || []).join("/").toLowerCase() === s.route.join("/").toLowerCase();
	const show = () => hipersign.tour.wait(s).then((el) => hipersign.tour.draw(s, el));
	if (here) return show();
	frappe.set_route(...s.route).then(() => setTimeout(show, 600));
};

// wait (up to 8 s) for the step's element; open the step's tab on a module page
hipersign.tour.wait = function (s) {
	return new Promise((resolve) => {
		let n = 0, tabbed = false;
		const tick = () => {
			if (s.tab && !tabbed) {
				const $tab = $(`.hsx-mtabs:visible button[data-tab="${s.tab}"]`);
				if ($tab.length) { if (!$tab.hasClass("on")) $tab.trigger("click"); tabbed = true; }
			}
			const el = (s.selector || "").split(",").map((x) => $(x.trim()).filter(":visible").first()).find(($x) => $x.length);
			if (el && (!s.tab || tabbed)) return resolve(el);
			if (++n > 40) return resolve($(".layout-main-section:visible, .page-container:visible").first());
			setTimeout(tick, 200);
		};
		tick();
	});
};

hipersign.tour.draw = function (s, $el) {
	const t = hipersign.tour.data, i = hipersign.tour.i;
	$(".ht-box, .ht-card").remove();
	const inCh = t.steps.filter((x) => x.chapter === s.chapter);
	const pos = inCh.indexOf(s) + 1;
	const next = t.steps[i + 1];
	const chLabel = (n) => (t.chapters.find((c) => c.n === n) || {}).label || "";
	const $box = $(`<div class="ht-box"></div>`).appendTo("body");
	const $card = $(`<div class="ht-card" role="dialog" aria-live="polite">
		<div class="ht-top"><select class="form-control input-xs ht-ch">${t.chapters.map((c) => `<option value="${c.n}" ${c.n === s.chapter ? "selected" : ""}>${c.n + 1}. ${ht_esc(c.label)}</option>`).join("")}</select>
			<span class="small text-muted">${__("{0} of {1} in this chapter", [pos, inCh.length])}</span><a class="ht-x" title="${__("End the tour")}">${frappe.utils.icon("close", "sm")}</a></div>
		<b>${ht_esc(s.title)}</b><p>${ht_esc(s.text)}</p>
		<div class="ht-bar"><i style="width:${((i + 1) / t.steps.length) * 100}%"></i></div>
		<div class="ht-btns">${i ? `<button class="btn btn-default btn-sm ht-back">${__("Back")}</button>` : ""}
			${next ? `<button class="btn btn-primary btn-sm ht-next">${next.chapter !== s.chapter ? __("Next: {0}", [ht_esc(chLabel(next.chapter))]) : __("Next")} →</button>`
				: `${(frappe.boot.hipersign || {}).demo_site ? `<button class="btn btn-primary btn-sm ht-demo">${__("Book a demo")}</button>` : ""}<button class="btn btn-default btn-sm ht-x2">${__("Finish")}</button>`}</div></div>`).appendTo("body");
	const place = () => {
		if (!$el || !$el.length || !$el[0].getBoundingClientRect) return;
		const r = $el[0].getBoundingClientRect();
		const top = Math.max(r.top, 64), h = Math.min(r.height, window.innerHeight - top - 12);
		$box.css({ top: top - 6, left: r.left - 6, width: r.width + 12, height: Math.max(h, 40) + 12 });
		const cw = Math.min(380, window.innerWidth - 24);
		let left = r.right + 16, ctop = top;
		if (left + cw > window.innerWidth - 12) { left = Math.max(12, Math.min(r.left, window.innerWidth - cw - 12)); ctop = Math.min(top + Math.max(h, 40) + 20, window.innerHeight - 260); }
		if (ctop > window.innerHeight - 260) ctop = Math.max(70, window.innerHeight - 280);
		$card.css({ left, top: ctop, width: cw });
	};
	if ($el && $el.length && $el[0].scrollIntoView) $el[0].scrollIntoView({ block: "center" });
	setTimeout(place, 50);
	$(window).off("resize.ht scroll.ht").on("resize.ht scroll.ht", frappe.utils.debounce(place, 50));
	$card.find(".ht-next").on("click", () => hipersign.tour.go(i + 1));
	$card.find(".ht-back").on("click", () => hipersign.tour.go(i - 1));
	$card.find(".ht-x, .ht-x2").on("click", () => hipersign.tour.end());
	$card.find(".ht-demo").on("click", () => { hipersign.tour.end(); if (hipersign.topbar && hipersign.topbar.book_demo) hipersign.topbar.book_demo(); });
	$card.find(".ht-ch").on("change", function () { const n = +$(this).val(); hipersign.tour.go(t.steps.findIndex((x) => x.chapter === n)); });
};

$(document).on("keydown", (e) => {
	if (hipersign.tour.i == null || $(".modal.show").length) return;
	if (e.key === "Escape") hipersign.tour.end();
	else if (e.key === "ArrowRight" && !$(e.target).is("input, textarea, select")) hipersign.tour.go(hipersign.tour.i + 1);
	else if (e.key === "ArrowLeft" && !$(e.target).is("input, textarea, select")) hipersign.tour.go(hipersign.tour.i - 1);
});
