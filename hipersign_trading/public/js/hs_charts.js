// Hipersign ERP v1.8.3 (prototype p20) — the chart kit: chart style presets (Hipersign · Soft · Glow · Classic) set by
// the client in Hipersign Settings › Look & menus, a brand colour, light/dark, and a per-user chart type (bars, line,
// area or table) chosen from the small menu on each chart. Also the graph band at the top of every page: 2–3 widgets
// drawn from that page's own records (hipersign_trading.api.band.get_band).
frappe.provide("hipersign.chart");
frappe.provide("hipersign.band");

(function () {
	const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
	const C = hipersign.chart;
	C.COLORS = { blue: "var(--hs-cblue)", violet: "var(--hs-cviolet)", green: "var(--x-green)", amber: "var(--x-amber)", red: "var(--x-red)", teal: "#14b8a6", navy: "var(--hs-navy)", grey: "var(--hs-faint)" };
	C.col = (c) => C.COLORS[c] || c || C.COLORS.blue;
	C.STYLES = [["hip", "Hipersign"], ["soft", "Soft"], ["glow", "Glow"], ["classic", "Classic"]];
	C.look = () => (frappe.boot.hipersign || {}).look || {};
	C.style = () => (document.documentElement.dataset.hsPrint ? "classic" : C.look().chart_style || "hip");
	C.dark = () => document.documentElement.getAttribute("data-theme") === "dark";
	C.gid = 0;

	// ---------------------------------------------------------------- look: style class + brand colour on <html>
	C.apply = function () {
		const root = document.documentElement, st = C.style();
		["hip", "soft", "glow", "classic"].forEach((k) => root.classList.toggle("hs-cs-" + k, k === st));
		root.classList.toggle("hs-ui-white", C.look().erp_theme === "White");  // v1.8.3: the White ERP theme
		const b = C.look().brand_colour;
		if (b) root.style.setProperty("--hs-brand-c", b); else root.style.removeProperty("--hs-brand-c");
	};

	// ---------------------------------------------------------------- per-user chart types
	C.types = () => { const l = frappe.boot.hipersign || {}; l.chart_types = l.chart_types || {}; return l.chart_types; };
	C.set_type = function (key, t) {
		C.types()[key] = t;
		frappe.xcall("hipersign_trading.api.look.set_chart_type", { key, chart_type: t }).catch(() => {});
	};
	C.reset_types = function () {
		(frappe.boot.hipersign || {}).chart_types = {};
		return frappe.xcall("hipersign_trading.api.look.reset_chart_types");
	};
	C.key = function (o, k) {
		const s = (k || "") + (o.key || "") + (o.labels || []).length + "#" + (o.series || []).map((x) => x.name || "").join("|") + "#" + (frappe.get_route_str() || "").split("/")[0];
		let h = 0;
		for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
		return "c" + (h >>> 0).toString(36);
	};

	// ---------------------------------------------------------------- number formats
	C.short = function (v) {
		v = flt(v);
		const a = Math.abs(v);
		if (a >= 1e9) return (v / 1e9).toFixed(a >= 1e10 ? 0 : 1).replace(/\.0$/, "") + "B";
		if (a >= 1e6) return (v / 1e6).toFixed(a >= 1e7 ? 0 : 1).replace(/\.0$/, "") + "M";
		if (a >= 1e3) return (v / 1e3).toFixed(a >= 1e4 ? 0 : 1).replace(/\.0$/, "") + "K";
		return format_number(v, null, v % 1 ? 1 : 0);
	};
	C.fmt = (o) => (v) => (o.money ? hipersign.ui.money(v, o.currency, true) : C.short(v));
	const niceMax = (v) => { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))), n = v / p; return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p; };

	// ---------------------------------------------------------------- svg helpers
	function smooth(pts) {
		if (pts.length < 3) return "M" + pts.map((p) => p.join(",")).join(" L");
		let d = `M${pts[0][0]},${pts[0][1]}`;
		for (let i = 0; i < pts.length - 1; i++) {
			const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2, t = 0.18;
			const c1 = [p1[0] + (p2[0] - p0[0]) * t, p1[1] + (p2[1] - p0[1]) * t], c2 = [p2[0] - (p3[0] - p1[0]) * t, p2[1] - (p3[1] - p1[1]) * t];
			const lo = Math.min(p1[1], p2[1]), hi = Math.max(p1[1], p2[1]);
			c1[1] = Math.max(lo, Math.min(hi, c1[1])); c2[1] = Math.max(lo, Math.min(hi, c2[1]));
			d += ` C${c1[0].toFixed(1)},${c1[1].toFixed(1)} ${c2[0].toFixed(1)},${c2[1].toFixed(1)} ${p2[0]},${p2[1]}`;
		}
		return d;
	}
	function grad(defs, color, top, bottom, dir) {
		const id = "hsg" + ++C.gid;
		defs.push(`<linearGradient id="${id}" x1="0" y1="0" x2="${dir === "h" ? 1 : 0}" y2="${dir === "h" ? 0 : 1}"><stop offset="0" style="stop-color:${color};stop-opacity:${top}"/><stop offset="1" style="stop-color:${color};stop-opacity:${bottom}"/></linearGradient>`);
		return `url(#${id})`;
	}
	function with_defs(svg, defs, glow) {
		if (!defs.length && !glow) return svg;
		const f = glow ? `<filter id="hsglow${C.gid}" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="3.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>` : "";
		return svg.replace(/(<svg[^>]*>)/, `$1<defs>${defs.join("")}${f}</defs>`).replace(/url\(#hsglow\)/g, `url(#hsglow${C.gid})`);
	}
	const ICON = { bar: '<path d="M5 20V10M12 20V4M19 20v-7"/>', line: '<path d="M3 17l6-6 4 4 8-8"/>', area: '<path d="M3 20V14l6-5 4 3 8-7v15z"/>', table: '<path d="M3 5h18v14H3zM3 10h18M3 15h18M9 5v14"/>' };
	const svgI = (p, s) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;
	const NAMES = { bar: __("Bars"), line: __("Line"), area: __("Area"), table: __("Table") };
	function menu(key, types, cur) {
		return `<div class="hs-cmenu" role="group" aria-label="${esc(__("Chart type"))}">${types.map((t) => `<button type="button" class="${t === cur ? "on" : ""}" data-ckey="${key}" data-ctype="${t}" title="${esc(NAMES[t])}" aria-pressed="${t === cur}">${svgI(ICON[t], 14)}</button>`).join("")}</div>`;
	}
	function table(o) {
		const f = C.fmt(o);
		return `<div class="hsx-tw"><table class="hs-ctab"><thead><tr><th></th>${o.series.map((s) => `<th>${esc(s.name || "")}</th>`).join("")}</tr></thead><tbody>${o.labels.map((l, i) => `<tr><td>${esc(l)}</td>${o.series.map((s) => `<td>${s.data[i] == null ? "—" : esc(f(s.data[i]))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
	}

	// column chart (grouped)
	function bars_svg(o) {
		const h = o.h || 240, W = 640, pad = { l: 58, r: 14, t: 14, b: 30 }, ih = h - pad.t - pad.b, iw = W - pad.l - pad.r, f = C.fmt(o);
		const all = o.series.flatMap((s) => s.data.map(flt));
		const mx = niceMax(Math.max(...all, 0)); let mn = Math.min(0, ...all); if (mn < 0) mn = -niceMax(-mn);
		const y = (v) => pad.t + ih - ((v - mn) / (mx - mn)) * ih, n = Math.max(1, o.labels.length), gw = iw / n, bw = Math.min(30, (gw * 0.7) / Math.max(1, o.series.length));
		const st = C.style(), defs = [], glow = st === "glow" && C.dark(), rx = st === "classic" ? 2.5 : st === "soft" ? 7 : 5;
		let s = `<svg class="hs-chart" viewBox="0 0 ${W} ${h}" role="img">`;
		for (let k = 0; k <= 4; k++) { const v = mn + ((mx - mn) * k) / 4; s += `<line class="gl" x1="${pad.l}" x2="${W - pad.r}" y1="${y(v)}" y2="${y(v)}"/><text x="${pad.l - 8}" y="${y(v) + 4}" text-anchor="end">${esc(C.short(v))}</text>`; }
		o.labels.forEach((lb, i) => {
			const gx = pad.l + gw * i + gw / 2;
			s += `<text x="${gx}" y="${h - 9}" text-anchor="middle">${esc(lb)}</text>`;
			o.series.forEach((se, j) => {
				const v = flt(se.data[i]), x = gx - (bw * o.series.length) / 2 + j * bw, y0 = y(Math.max(0, v)), y1 = y(Math.min(0, v)), c = C.col(se.color);
				const fill = st === "glow" ? grad(defs, c, 1, 0.25) : st === "hip" ? grad(defs, c, 1, 0.72) : c;
				s += `<rect x="${x + 1}" y="${y0}" width="${Math.max(1, bw - 2)}" height="${Math.max(1, y1 - y0)}" rx="${rx}" fill="${fill}"${glow ? ' filter="url(#hsglow)"' : ""}><title>${esc(se.name || "")} · ${esc(lb)}: ${esc(f(v))}</title></rect>`;
			});
		});
		if (mn < 0) s += `<line x1="${pad.l}" x2="${W - pad.r}" y1="${y(0)}" y2="${y(0)}" stroke="var(--hs-faint)"/>`;
		return with_defs(s + "</svg>", defs, glow);
	}
	// line / area chart
	function line_svg(o, area) {
		const h = o.h || 240, W = 640, pad = { l: 58, r: 16, t: 14, b: 30 }, ih = h - pad.t - pad.b, iw = W - pad.l - pad.r, f = C.fmt(o);
		const vals = o.series.flatMap((s) => s.data.filter((v) => v != null).map(flt));
		const mx = niceMax(Math.max(...vals, 0)), n = o.labels.length;
		const x = (i) => pad.l + (n === 1 ? iw / 2 : (iw * i) / (n - 1)), y = (v) => pad.t + ih - (v / mx) * ih, base = pad.t + ih;
		const st = C.style(), defs = [], glow = st === "glow" && C.dark();
		let s = `<svg class="hs-chart" viewBox="0 0 ${W} ${h}" role="img">`;
		for (let k = 0; k <= 4; k++) { const v = (mx * k) / 4; s += `<line class="gl" x1="${pad.l}" x2="${W - pad.r}" y1="${y(v)}" y2="${y(v)}"/><text x="${pad.l - 8}" y="${y(v) + 4}" text-anchor="end">${esc(C.short(v))}</text>`; }
		const step = Math.ceil(n / 9);
		o.labels.forEach((lb, i) => { if (i % step === 0 || i === n - 1) s += `<text x="${x(i)}" y="${h - 9}" text-anchor="middle">${esc(lb)}</text>`; });
		o.series.forEach((se, si) => {
			const c = C.col(se.color), P = se.data.map((v, i) => (v == null ? null : [+x(i).toFixed(1), +y(flt(v)).toFixed(1)])).filter(Boolean);
			if (!P.length) return;
			const d = st === "classic" ? "M" + P.map((p) => p.join(",")).join(" L") : smooth(P);
			if ((area || (st !== "classic" && si === 0) || st === "glow") && P.length > 1) {
				const op = area ? (st === "glow" ? 0.45 : 0.28) : st === "glow" ? 0.4 : st === "soft" ? 0.12 : st === "classic" ? 0.1 : 0.22;
				s += `<path d="${d} L${P[P.length - 1][0]},${base} L${P[0][0]},${base} Z" fill="${st === "classic" ? c : grad(defs, c, op, 0)}" ${st === "classic" ? `opacity="${op}"` : ""} stroke="none"/>`;
			}
			s += `<path d="${d}" fill="none" stroke="${c}" stroke-width="${st === "soft" ? 2.2 : st === "classic" ? 2 : 2.8}" stroke-linecap="round" stroke-linejoin="round"${glow ? ' filter="url(#hsglow)"' : ""}/>`;
			const L = P[P.length - 1], li = se.data.length - 1 - [...se.data].reverse().findIndex((v) => v != null);
			s += `<circle cx="${L[0]}" cy="${L[1]}" r="4.5" fill="${c}" stroke="var(--x-surface)" stroke-width="2"><title>${esc(se.name || "")} · ${esc(o.labels[li])}: ${esc(f(se.data[li]))}</title></circle>`;
		});
		return with_defs(s + "</svg>", defs, glow);
	}
	const legend = (series) => (series.length > 1 ? `<div class="hs-legend">${series.map((s) => `<span><i style="background:${C.col(s.color)}"></i>${esc(s.name || "")}</span>`).join("")}</div>` : "");

	// a chart with its type menu: o = {labels, series:[{name,data,color}], money, currency, kind: "bar"|"line", key}
	C.chart = function (o) {
		const kind = o.kind === "bar" ? "bar" : "line", key = C.key(o, kind[0]), types = kind === "bar" ? ["bar", "line", "area", "table"] : ["line", "area", "bar", "table"];
		const t = C.types()[key] || kind;
		const body = t === "table" ? table(o) : t === "bar" ? bars_svg(o) : line_svg(o, t === "area");
		// v1.8.4: the chart keeps its data so a chart outside the band (module cards) can be redrawn in the type picked
		return `<div class="hs-cbox" data-hs-o="${esc(JSON.stringify(o))}">${menu(key, types, t)}${body}${t === "table" ? "" : legend(o.series)}</div>`;
	};

	C.donut = function (rows, center, sub, o) {
		o = o || {};
		const st = C.style(), tot = rows.reduce((a, r) => a + flt(r.value), 0) || 1, R = 52, circ = 2 * Math.PI * R, w = st === "glow" ? 20 : st === "soft" ? 12 : st === "classic" ? 16 : 18, f = C.fmt(o);
		let off = 0, s = `<svg class="hs-chart hs-dn" viewBox="0 0 140 140" width="${o.size || 140}" height="${o.size || 140}" role="img"><circle cx="70" cy="70" r="${R}" fill="none" stroke="var(--x-line-2)" stroke-width="${w}"/>`;
		rows.forEach((r) => { const l = (flt(r.value) / tot) * circ; if (l > 0) s += `<circle cx="70" cy="70" r="${R}" fill="none" stroke="${C.col(r.color)}" stroke-width="${w}" stroke-dasharray="${l} ${circ - l}" stroke-dashoffset="${-off}" transform="rotate(-90 70 70)"${st === "glow" && C.dark() ? ' filter="url(#hsglow)"' : ""}><title>${esc(r.label)}: ${esc(f(r.value))}</title></circle>`; off += l; });
		const cs = String(center == null ? "" : center);
		s += `<text x="70" y="${cs.length > 4 ? 67 : 69}" text-anchor="middle" style="font-size:${cs.length > 6 ? 15 : cs.length > 4 ? 18 : 25}px;font-weight:800;fill:var(--x-ink)">${esc(cs)}</text><text x="70" y="87" text-anchor="middle" style="font-size:10.5px;fill:var(--x-muted)">${esc(sub || "")}</text></svg>`;
		return with_defs(s, [], st === "glow" && C.dark());
	};

	C.hbars = function (rows, o) {
		o = o || {};
		const st = C.style(), mx = Math.max(1, ...rows.map((r) => flt(r.value))), f = C.fmt(o), hgt = st === "soft" ? 12 : 10;
		return `<div class="hs-hbars">${rows.map((r) => {
			const c = C.col(r.color), w = Math.max(2, (flt(r.value) / mx) * 100);
			const bg = st === "glow" ? `linear-gradient(90deg,color-mix(in srgb,${c} 45%,transparent),${c});box-shadow:0 0 12px color-mix(in srgb,${c} 55%,transparent)` : c;
			return `<div class="hs-hbar ${r.open || r.route ? "hs-click" : ""}" ${link_attr(r)}><span title="${esc(r.label)}">${esc(r.label)}</span><div class="hs-hbar-t" style="height:${hgt}px"><i style="width:${w}%;background:${bg};border-radius:${st === "classic" ? 4 : 999}px"></i></div><b>${esc(f(r.value))}</b></div>`;
		}).join("")}</div>`;
	};

	C.gauge = function (pct, big, sub, o) {
		o = o || {};
		const p = Math.max(0, Math.min(1, flt(pct))), L = Math.PI * 90, ang = Math.PI * (1 - p), cx = 120 + 90 * Math.cos(ang), cy = 120 - 90 * Math.sin(ang);
		const st = C.style(), defs = [], col = C.col(o.color), glow = st === "glow" && C.dark(), stroke = st === "glow" ? grad(defs, col, 0.55, 1, "h") : col;
		const s = `<svg class="hs-chart hs-gauge" viewBox="0 0 240 150" role="img" aria-label="${esc(big + " " + (sub || ""))}">
			<path d="M30 120 A90 90 0 0 1 210 120" fill="none" stroke="var(--x-line-2)" stroke-width="18" stroke-linecap="round"${st === "soft" ? ' stroke-dasharray="2 6"' : ""}/>
			<path d="M30 120 A90 90 0 0 1 210 120" fill="none" stroke="${stroke}" stroke-width="18" stroke-linecap="round" stroke-dasharray="${(L * p).toFixed(1)} ${L.toFixed(1)}"${glow ? ' filter="url(#hsglow)"' : ""}/>
			<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="10" fill="var(--x-surface)" stroke="${col}" stroke-width="4"/>
			<text x="120" y="104" text-anchor="middle" style="font-size:34px;font-weight:800;fill:var(--x-ink)">${esc(big)}</text>
			<text x="120" y="126" text-anchor="middle" style="font-size:${String(sub || "").length > 28 ? 9 : 11}px;fill:var(--x-muted)">${esc(String(sub || "").length > 40 ? String(sub).slice(0, 38) + "…" : sub || "")}</text></svg>`;
		return with_defs(s, defs, glow);
	};

	C.spark = function (data, color) {
		const d = (data || []).filter((v) => v != null).map(flt);
		if (d.length < 2) return "";
		const mn = Math.min(...d), mx = Math.max(...d), r = mx - mn || 1, W = 150, H = 30, c = C.col(color);
		const P = d.map((v, i) => [Math.round((i * (W - 4)) / (d.length - 1) + 2), +(H - 3 - ((v - mn) / r) * (H - 8)).toFixed(1)]);
		const defs = [], st = C.style(), path = st === "classic" ? "M" + P.map((p) => p.join(",")).join(" L") : smooth(P);
		const area = st === "classic" ? "" : `<path d="${path} L${P[P.length - 1][0]},${H} L${P[0][0]},${H} Z" fill="${grad(defs, c, st === "glow" ? 0.5 : 0.25, 0)}"/>`;
		return with_defs(`<svg class="hs-spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">${area}<path d="${path}" fill="none" stroke="${c}" stroke-width="2.2" stroke-linecap="round"/><circle cx="${P[P.length - 1][0]}" cy="${P[P.length - 1][1]}" r="2.8" fill="${c}"/></svg>`, defs, false);
	};

	C.heat = function (rows, cols, values, o) {
		o = o || {};
		const f = C.fmt(o), mx = Math.max(1, ...values.flat().map(flt)), st = C.style();
		const base = st === "glow" ? "#8b5cf6" : st === "soft" ? "#3a8dff" : "var(--hs-cblue)";
		const cell = (ri, ci) => {
			const v = flt((values[ri] || [])[ci]), a = v ? 0.12 + (0.88 * v) / mx : 0;
			return `<span class="hs-hc" style="background:${v ? `color-mix(in srgb,${base} ${Math.round(a * 100)}%,transparent)` : "var(--x-line-2)"};color:${a > 0.55 ? "#fff" : "var(--x-ink)"}" title="${esc(rows[ri] + " · " + cols[ci] + (v ? ": " + f(v) : ""))}">${v ? esc(o.money ? C.short(v) : f(v)) : ""}</span>`;
		};
		return `<div class="hs-heat" style="grid-template-columns:minmax(80px,150px) repeat(${cols.length},minmax(0,1fr))"><span></span>${cols.map((c) => `<span class="hs-hl c">${esc(c)}</span>`).join("")}${rows.map((r, ri) => `<span class="hs-hl">${esc(r)}</span>${cols.map((c, ci) => cell(ri, ci)).join("")}`).join("")}</div>`;
	};

	const TONE = { y: "hsb-st-y", n: "hsb-st-n", d: "hsb-st-d", x: "hsb-st-x", g: "hsb-st-g" };
	// stage names that do not fit a narrow column when there are many stages
	const SHORT = { Contacted: __("Contact"), Qualified: __("Qualif."), Negotiation: __("Negot."), Proposal: __("Prop."), Completed: __("Done"), "Waiting approval": __("Approval"),
		"Pending approval": __("Approval"), "Work in progress": __("In progress"), "Not started": __("To start"), "In warehouse": __("In stock"), "Under Customs Clearance": __("Customs") };
	C.stages = function (st) {
		const mx = Math.max(1, ...st.map((s) => cint(s.n))), many = st.length > 5;
		return `<div class="hsb-stages ${many ? "many" : ""} ${st.length > 6 ? "lots" : ""}" style="grid-template-columns:repeat(${st.length},minmax(0,1fr))">${st.map((s) => `<button type="button" class="hsb-stage ${TONE[s.tone] || ""}" ${link_attr(s)} title="${esc(s.label + (s.value ? " · " + s.value : ""))}">
			<span class="hsb-stage-b" style="height:${Math.round(44 + (110 * cint(s.n)) / mx)}px"><b>${cint(s.n)}</b></span><span class="hsb-stage-l">${esc(st.length > 5 ? SHORT[s.label] || s.label : s.label)}${s.value ? `<small>${esc(s.value)}</small>` : ""}</span></button>`).join("")}</div>`;
	};

	// click targets: {open:[doctype, name]} opens the record panel, {route:[...]} a page, {tab, chip} a tab of this module page
	function link_attr(r) {
		if (r.open) return `data-hs-open='${esc(JSON.stringify(r.open))}'`;
		if (r.route) return `data-hs-go='${esc(JSON.stringify([r.route, r.options || null]))}'`;
		if (r.tab) return `data-hs-tab="${esc(r.tab)}" data-hs-chip="${esc(r.chip || "")}"`;
		return "";
	}
	C.link_attr = link_attr;

	// ---------------------------------------------------------------- the band
	const card = (w, body, cls) => `<div class="hsx-card hs-bw ${cls || ""}"><div class="hsx-card-h"><h3>${w.icon ? frappe.utils.icon(w.icon, "sm") : ""} ${esc(w.title)}${w.sub ? ` <small>${esc(w.sub)}</small>` : ""}</h3></div><div class="hsx-card-b">${body}</div></div>`;
	C.widget = function (w) {
		const empty = `<div class="hsx-empty">${esc(w.empty || __("Nothing in this period."))}</div>`;
		if (w.type === "stages") return card(w, (w.stages || []).length ? C.stages(w.stages) + (w.note ? `<p class="hs-bnote">${esc(w.note)}</p>` : "") : empty);
		if (w.type === "trend") return card(w, (w.labels || []).length ? C.chart({ labels: w.labels, series: w.series || [], money: w.money, currency: w.currency, kind: w.kind || "line", key: w.title, h: 250 }) : empty);
		if (w.type === "bars") return card(w, (w.rows || []).length ? C.hbars(w.rows, w) : empty);
		if (w.type === "donut") return card(w, (w.rows || []).filter((r) => flt(r.value)).length ? `<div class="hs-dnw">${C.donut(w.rows, w.center, w.center_label, w)}<div class="hs-dnl">${w.rows.map((r) => `<span ${link_attr(r)} class="${r.open || r.route || r.tab ? "hs-click" : ""}"><span><i style="background:${C.col(r.color)}"></i>${esc(r.label)}</span><b>${esc(C.fmt(w)(r.value))}</b></span>`).join("")}</div></div>` : empty);
		if (w.type === "gauge") return card(w, C.gauge(w.pct, w.big, w.caption, w) + (w.note ? `<p class="hs-bnote c">${esc(w.note)}</p>` : ""));
		if (w.type === "heat") return card(w, (w.rows || []).length ? C.heat(w.rows, w.cols, w.values, w) : empty);
		if (w.type === "dark") return `<div class="hsx-card hs-bw hs-dark"><div class="hsx-card-h"><h3>${w.icon ? frappe.utils.icon(w.icon, "sm") : ""} ${esc(w.title)}${w.sub ? ` <small>${esc(w.sub)}</small>` : ""}</h3></div><div class="hsx-card-b">
			<div class="hs-big">${esc(w.big)}${w.big_sub ? `<small> ${esc(w.big_sub)}</small>` : ""}</div>${(w.rows || []).map((r) => `<button type="button" class="hs-drow" ${link_attr(r)}><span>${esc(r.label)}${r.sub ? `<small>${esc(r.sub)}</small>` : ""}</span><b>${esc(r.value == null ? "" : r.value)}</b></button>`).join("") || `<p class="hs-bnote">${esc(w.empty || __("Nothing needs attention"))}</p>`}</div></div>`;
		return "";
	};

	// mount the band above a page's content. key = the page key in api/band.py
	hipersign.band.mount = function ($host, key) {
		if (!$host || !$host.length || !key) return;
		if ((frappe.boot.hipersign || {}).look && frappe.boot.hipersign.look.bands === 0) return $host.empty().hide();
		const seq = ($host.data("hs-seq") || 0) + 1;
		$host.data("hs-seq", seq).data("hs-key", key).data("hs-at", Date.now());
		if (!$host.children().length) $host.html(`<div class="hs-band-skel"><i></i><i></i><i></i></div>`);
		frappe.xcall("hipersign_trading.api.band.get_band", { key }, "GET").then((ws) => {
			if ($host.data("hs-seq") !== seq) return;
			const html = (ws || []).map((w) => { try { return C.widget(w); } catch (e) { console.warn("Hipersign band widget", e); return ""; } }).filter(Boolean);
			$host.data("hs-band", ws || []);
			if (!html.length) return $host.empty().hide();
			$host.show().css("--bn", Math.min(3, html.length)).html(html.join(""));
		}).catch(() => $host.empty().hide());
	};
	// redraw every band on screen from its last data (chart type or theme changed) without asking the server again
	hipersign.band.redraw = function () {
		$(".hs-band").each(function () {
			const $h = $(this), ws = $h.data("hs-band");
			if (ws && ws.length) $h.html(ws.map((w) => { try { return C.widget(w); } catch (e) { return ""; } }).join(""));
		});
	};

	// ---------------------------------------------------------------- events
	$(document).on("click", ".hs-cmenu button", function (e) {
		e.preventDefault(); e.stopPropagation();
		C.set_type($(this).attr("data-ckey"), $(this).attr("data-ctype"));
		const $box = $(this).closest(".hs-cbox");
		if (!$box.closest(".hs-band").length && $box.attr("data-hs-o")) {
			try { $box.replaceWith(C.chart(JSON.parse($box.attr("data-hs-o")))); } catch (err) { /* keep it */ }
		}
		hipersign.band.redraw();
		$(document).trigger("hs-chart-type");
	});
	$(document).on("click", ".hs-band [data-hs-open]", function (e) {
		e.preventDefault();
		const [dt, name] = JSON.parse($(this).attr("data-hs-open"));
		if (hipersign.panel && hipersign.panel.has && hipersign.panel.has(dt)) hipersign.panel.open(dt, name); else frappe.set_route("Form", dt, name);
	});
	$(document).on("click", ".hs-band [data-hs-go]", function (e) {
		e.preventDefault();
		const [route, opts] = JSON.parse($(this).attr("data-hs-go"));
		hipersign.ui.go(route, opts);
	});
	$(document).on("click", ".hs-band [data-hs-tab]", function (e) {
		e.preventDefault();
		const $w = $(this).closest(".hsx-wrap"), tab = $(this).attr("data-hs-tab"), chip = $(this).attr("data-hs-chip");
		const $t = $w.find(`.hsx-mtabs button[data-tab="${tab}"]`);
		if (!$t.length) return;
		$t.trigger("click");
		if (chip) setTimeout(() => $w.find(`.hsx-chips button[data-chip="${chip}"]`).first().trigger("click"), 30);
		$("html, body").animate({ scrollTop: $w.find(".hsx-mtabs").offset().top - 80 }, 200);
	});

	// print: charts print in Classic so they stay readable on paper
	window.addEventListener("beforeprint", () => { document.documentElement.dataset.hsPrint = "1"; C.apply(); hipersign.band.redraw(); });
	window.addEventListener("afterprint", () => { delete document.documentElement.dataset.hsPrint; C.apply(); hipersign.band.redraw(); });

	// theme changes (Frappe sets data-theme on <html>): redraw so glow and colours follow
	new MutationObserver(() => hipersign.band.redraw()).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
	$(document).on("startup", () => C.apply());

	// ---------------------------------------------------------------- v1.8.3: Frappe / ERPNext pop-ups only for super admins
	// (or everyone when the licence says so). The server already leaves the change log and onboarding tours out of the boot
	// and answers the update check with nothing; these are Frappe's own prompts shown from the desk.
	if (frappe.boot && frappe.boot.hs_popups === 0) {
		frappe.provide("frappe.ui");
		["maybe_show_new_navigation_prompt", "maybe_show_legacy_gravatar_cleanup_prompt"].forEach((fn) => {
			const quiet = () => false;
			try {
				Object.defineProperty(frappe.ui, fn, { configurable: true, get: () => quiet, set: () => {} });
			} catch (e) {
				frappe.ui[fn] = quiet;
			}
		});
		const quiet_desk = () => {
			if (frappe.Application && frappe.Application.prototype) {
				frappe.Application.prototype.show_update_available = () => {};
				frappe.Application.prototype.show_change_log = () => {};
			}
		};
		quiet_desk();
		$(document).on("startup", quiet_desk);
	}
	if (frappe.boot && frappe.boot.hipersign) C.apply();
})();
