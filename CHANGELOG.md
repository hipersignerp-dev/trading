# Changelog

## 1.8.4 — Fixes from the audit: every open issue, every menu entry in the Hipersign theme (7 Nov 2026)
**Serious issues (#21–#27 and more)**
- Transfer to WIP uses the warehouses picked (#21); the Nairobi USD invoice shows its AED outstanding as AED (#22).
- Variation approval (#23) and subcontract claim billing/payment (#24) work for MD, project managers and accounts users.
- HR › Request advance opens the Employee Advance window (#25); Finance › Receive advance is a new window, filled from the
  sales order when started from one (#26); Bank Reconciliation Tool opens without errors and accounts users get it (#27).
- Stock: free quantity never below 0, with a red "Short N" status (#36). Landed costs and the site page load for users
  without import shipments (chen.hao).
- Demo step v184: Golden Dragon Interiors and Hipersign Lighting Industries are group members (#40); Temporary Opening
  closed, so the balance sheet has no negative current assets. Cash-flow total leaves out the forecast row; depreciation
  line added. New records follow the demo's naming series per company.
**Go-live findings (#28–#35)**
- Menu builder loads for every scope and shows the reason on an error (#28).
- Only the Hipersign app on /apps and the app switcher (super admins see all); everyone lands on Hipersign Home (#29); the
  six old workspaces are hidden and their links open Hipersign Home (#30); square app logo, title "Hipersign" (#31).
- Messages: one "New message" button — pick people, record optional (private direct conversations); new record and people
  pickers in the Hipersign style (#32, #33).
- "+ New item" on Warehouse & Inventory (#35).
**Every menu entry in the Hipersign theme (#34, #37)**
- All 146 sidebar entries open a Hipersign page or tab (new tabs for opportunities, payments, pick lists, warranty claims,
  routings & operations, inspection templates, step logs); lists opened from search land on the matching page and tab.
- New pages: Reports (about 90 reports by area, search, favourites; report views restyled), Document Centre, Workflows &
  Settings, Data Migration (8 import steps).
**Smaller findings**
- Create windows: job card offers the work order's operations; production plan keeps warehouse and options; quotation
  keeps the sales person; debit/credit notes start empty; bank guarantee keeps its end date; clear message for negative
  quantities; contact/address "For" is a picker.
- Shop floor: paused cards refuse quantities and scrap; scrap matches the job card; tablet-size buttons.
- Projects/Manufacturing: currency once in the column header, compact KPI lines, pop-ups stay on screen, BOQ "From tender to
  contract" stepper, charts with axes. Home Projects card and lifecycle row fit at 1280 px; Order Tracker pop-over steady.
- Prints: BOM and certificate on one page; Arabic text no longer overlaps (22 formats); receipt voucher shows bank charges
  so words match figures.
- About 37 more record types open the record panel; Arabic keeps numbers in order; Chinese month names; phone top bar
  keeps company and period.
**Super admins** only from the site config `hipersign_super_admins` (Administrator only when it is not set).
Arabic and Chinese 100%.

## 1.8.3 — The p20 look on every page, Super Admin and licence, White theme (6 Nov 2026)
- **Graphs on every page:** each menu page opens with 2–3 graphs drawn from that page's own records — stage columns,
  trend, gauge, donut, ranked bars, a dark "needs attention" card or a heatmap (hipersign_trading.api.band). Bars, rows
  and stages open the record, the page or the matching tab. The KPI cards, tabs and lists below are unchanged.
- **Chart styles:** Hipersign, Soft, Glow or Classic, plus an optional brand colour — Hipersign Settings › Look & menus.
  Printing always uses Classic. The graphs can be switched off there too.
- **Chart type per user:** a small menu on each chart shows it as bars, line, area or table; kept for that user
  ("Reset my chart types" in the avatar menu).
- **Light / dark switch** in the top bar.
- **View as** (#39): demo users in a top-bar drop-down (demo sites; System Manager or the view-only demo login), with a
  bar under the top bar and Back to the original login — no new login.
- **Super Admin** (new page, avatar menu): only Hipersign's super admins — Administrator and the logins in the site config
  key `hipersign_super_admins` (Press › Site › Config; the client cannot change it). The Hipersign Licence sets the users
  allowed (portal customers, driver-only logins, Administrator and super admins are not counted), the companies allowed and
  which modules may be switched on; the server refuses a user or company beyond the licence and keeps unlicensed modules
  off. Shows what is in use today.
- **Frappe and ERPNext pop-ups only for super admins:** update notices, What's new, onboarding tours and Frappe's prompts are
  hidden from everyone else (the licence can show them to the client's admins too). Errors and validation messages,
  approvals, messages and alerts are unchanged.
- **ERP theme:** Classic (navy menu) or White (white menu on a light page, as on the Solar ERP) — the site's default in
  Hipersign Settings › Look & menus, and each user can switch in the avatar menu. Works with dark mode.
- **Top bar fits** at 1024–1440 px (it scrolled sideways on narrower screens): the name under the avatar, the search box
  and View as give way.
- **Style B:** rounder cards and KPI cards (no colour strip), pill tabs and chips; the sidebar group guide line is visible
  on navy and the active item is marked in brand blue (#38).

## 1.8.2 — Fixes from the full site audit (3 Nov 2026)
- **Trackers** laid out as the prototype: phases wrap two or three to a row, step names in full — the Manufacturing
  "Make" phase was squeezed into the narrowest column.
- **Money:** compact amounts keep whole-number zeros (AED 110,300 showed as "AED 11K"); foreign-currency outstanding is
  counted once in the company currency (ERPNext keeps it in the party account's currency) — Finance receivables, Home
  receivables and payables, credit exposure, supplier panel; the Order Tracker's "Paid" is no longer negative on USD orders.
- **Customer portal:** /orders, /invoices and /quotations open the Hipersign portal (they crashed with a server error).
- **Shop floor:** an operation cannot run ahead of the one before it.
- **Create windows:** a typed rate with a line discount saves as shown; quotations and orders are in the party's currency
  (credit exposure converted); stock transfer To starts on another warehouse and same-store or negative transfers are
  refused; site transfers only from the project company's stores; company documents default to the current company; a
  draft BOM is not made the default; tick boxes visible; nothing shows under the sticky buttons; dark-theme colours.
- **Roles:** Driver App only for drivers and dispatch; Planning works without Sales Order read; Trade Journey lists only
  permitted orders; role labels for the Projects and Manufacturing roles and the view-only demo; + New screen entries and
  "All" only when the user may open them; page roles as the prototype's role matrix; demo users each in their own
  company (demo step v182).
- **Frappe 16.54:** list columns line up with their headings; phone sidebar is a closed drawer with the menu; Escape
  closes + New; sidebar search and user block hidden under the top bar; collapsed rail shows the square mark and icons;
  deep links (/app/sales-order) no longer jump to Home.
- **Company Compliance** panel no longer crashes on a reminder stage.
- **Arabic** UI translation at 100% ("Excel" kept); Chinese for every new message.

## 1.8.1 — The Hipersign menu on Frappe 16.30+ (the "Sidebar" model)
- **Frappe 16.30 and later** replaced *Workspace Sidebar* with per-module **Sidebar** documents. Until now the app stopped
  managing the menu there, so a site upgraded to 16.30+ kept the sidebar Frappe had converted on the day of its upgrade
  (named *Hipersign Trading*, merged from our seven old sidebars): no Projects or Manufacturing groups, no Menu builder,
  no feature switches, no brand block, sub-lists or count badges.
- The app now writes **one Sidebar, "Hipersign ERP"** (module Hipersign Trading, not standard) from the same menu as
  before — feature switches, the sites' own lists and pages, the same order — on install, every migrate and every
  settings save, and only when its rows changed. Frappe's converted *Hipersign Trading* sidebar is replaced by it; rows
  of that sidebar that are not in the Hipersign menu are listed once in the Error Log (*Hipersign menu: converted sidebar
  replaced*) and stay in Frappe's Workspace Sidebar archive.
- The **Hipersign ERP desktop tile** opens it again (Desktop Icons mode); on the Apps screen the Hipersign app opens the
  Hipersign Trading workspace inside it.
- **Menu builder** changes (hide, rename, reorder, custom links; role > company > site) apply on 16.30+ too: the boot
  payload's `module_sidebars` entry is rewritten per user, as `workspace_sidebar_item` is on 16.29. Changes a site makes
  with Frappe's own *Customize sidebar* (Custom Sidebar layers) are kept: what a layer hides stays hidden, links it adds
  follow the Hipersign entries.
- The **Home** link stays at the top of the menu when the builder moves another group above Overview.
- A list that has a prototype page opens the page only for users who may open that page (others keep the list instead
  of a *not permitted* error) — on 16.29 too.
- Desk script: works with both sidebars (`module_sidebars` / `current_module` on 16.30+); theme covers 16.30+'s user button.
- Frappe 16.29 (Workspace Sidebar) works as before.

## 1.8.0 — Projects (prototype p19): contracting and fit-out from enquiry to profit report
- **Projects menu** (switch *Projects & contracting*, Settings → Features → Industries) with eight pages: **Projects**
  (portfolio, How it works, red flags), **Estimating & BOQ** (BOQ by section, cost build-up, tenders & quotations),
  **Site & procurement** (material requests against BOQ lines, project POs, deliveries to site, site stock, returns),
  **Progress & billing** (certificates, measurement typed per BOQ line, progress / advance / retention invoices, retention,
  advance recovery, variations), **Subcontractors** (orders, claims, retention, back-charges), **Timesheets & labour**,
  **Project costing** (budget vs committed vs actual vs forecast per cost head) and the **Project Tracker** (every project
  through 26 steps in 6 phases with status, % and date per step and its red flags).
- **The 26-step process** is defined once (api/projects.py). The project panel shows the stepper with what happens, who,
  documents, approval and trigger per step, the money, terms, bonds, red flags and prints; *Complete step N* checks the
  step's approval role and is logged (Project Step Log: who and when). Contract signed creates the contract sales order.
- **Money that posts**: advance invoice (Cr Advances from Customers + VAT); progress certificate → progress invoice = work
  this period less advance recovery and retention, plus 5% VAT on the net (deductions as tax-table rows, so no negative
  rates); retention release invoice; approved variations raise the revised contract (and add a line to the contract order);
  subcontract claim → certified → supplier bill less retention (Retention Payable) and agreed back-charges, plus VAT;
  project material request → PO → receipt at the project's site store; cost by head from the GL and approved timesheets.
- **New records**: Project BOQ (lines with cost build-up and progress), Progress Certificate, Variation Order, Subcontract
  Order, Subcontract Claim, Back Charge, Daily Site Report, Project Step Log; contract fields on Project, bond type and
  status on Bank Guarantee, project on material requests and purchase orders.
- **Nine create windows** (Quick / Standard / Detailed) from + New → Projects and the pages: project, BOQ lines, task,
  timesheet, progress certificate, variation, subcontract order, material request to site, site transfer.
- **Six prints** (English + Arabic): BOQ / tender, interim payment certificate, progress invoice, retention invoice,
  variation order, subcontract order.
- **Contractor pack** (Standard without exports, plus projects, LCs, advances, HR, assets, company compliance); Enterprise
  includes Projects. Roles **Project Manager**, **Quantity Surveyor**, **Site Engineer**; the Demo Viewer reads the pages.
  Tour chapter *Projects*, Test Centre scripts PRJ-01…12, Arabic labels.
- **Demo**: Golden Dragon Interiors LLC (Business Bay, AED) joins the demo group with the prototype's five projects — the
  AED 4.2M Business Bay hotel in execution, villas mobilising, DIFC office in handover, a clinic tender and a closed
  restaurant — all posted as real documents.
- Fix: a group company's sales orders keep their own VAT template (the main company's was forced on them).

## 1.8.0 — Manufacturing (prototype p19): assemblers and factories from sales order to closed work order
- **Manufacturing menu** (switch *Manufacturing*, Settings → Features → Industries) with seven pages: **Production**
  (today on the floor, work orders, workstation load, stock entries, How it works), **Planning** (demand incl. forecast,
  production plans, MRP shortages with *Raise PO*, material requests, component purchase orders), **BOMs & routings** (BOM
  tree with sub-assemblies and the standard cost roll-up, versions, where used, workstations), **Shop floor** (a tablet view:
  start / pause a job card, +10 / +50, scrap, operator, complete), **Quality** (incoming, in-process, final, rejects &
  rework, test certificates), **Costing** (actual against standard per work order with material, labour and overhead
  variances, margin per product) and the **Production Tracker** (every sales order through 22 steps in 5 phases).
- **The 22-step process** is defined once (api/manufacturing.py), with the approval role per step and the red flags (late
  work order, held for a component shortage, open rework, a material request waiting, an invoice not paid). *Complete step
  N* on the sales order or work order panel makes what the step needs — production plan and work orders, approved material
  requests, release, issue to WIP, finished goods receipt, delivery, invoice, close — and is logged in the **Manufacturing
  Step Log**.
- **Built on ERPNext's own documents**: BOM (with operations and routing), Workstation (labour and overhead as operating
  components), Operation, Production Plan, Work Order, Job Card, Material Request, Purchase Order / Receipt, Stock Entry
  (Material Transfer for Manufacture, Manufacture), Quality Inspection (+ templates), Batch. Finished goods are valued at
  the materials consumed plus labour and overhead from the job cards' actual hours (credited to *Manufacturing Labour /
  Overhead Absorbed*); WIP gets its own account on a new factory. Scrap is recorded per operation and booked as process
  loss, also across partial receipts (the shop floor splits job cards when finished goods are received part-way).
- Custom fields: Chinese item and workstation names, the sales order's step and forecast flag, operator and scrap on the
  job card, stage / result / lot / rework / certificate on the quality inspection, the BOM change note, serials and picker
  on the stock entry, the company's Chinese name. Work orders, job cards, inspections and plans number WO-, JC-, QI-, PP-.
- **Seven create windows** (Quick / Standard / Detailed) from + New → Manufacturing and the pages: BOM, work order,
  production plan, job card, quality inspection, manufacture entry, material transfer to WIP.
- **Four prints in English + Chinese**: job ticket (barcodes per job card), bill of materials, QC test certificate and the
  finished-goods label (batch, serials, QR code and barcode).
- **Manufacturer pack** (Standard plus manufacturing, serial numbers, HR, assets); Enterprise includes Manufacturing.
  Roles **Production Manager** and **QC Inspector**; the Demo Viewer reads the pages. Tour chapter *Manufacturing*, Test
  Centre scripts MFG-01…11, Arabic labels and Simplified Chinese for every new string.
- **Demo**: Hipersign Lighting Industries FZE (KEZAD, AED) joins the demo group — LED panels, high-bays and drivers from
  Chinese components, seven orders from closed to forecast, a rejected heat-sink lot, work orders running on the shop floor
  now, test certificates and the costing — all posted as real documents.
- Fix: a group company's export invoices keep their own zero-rated VAT template (the main company's was forced on them).
- **Closing the p19 gaps**: Home shows a **Projects** and a **Manufacturing** card (four figures that open their page, the
  open projects / work orders below, Tracker) when the feature is on and the user may open the page; the QC Inspector gets
  a **Quality** card first and *inspections to record* under Work for today. The top-bar search finds projects,
  variations, subcontract orders and work orders (permissions, feature switches and menu-builder hidden screens apply).
  **Daily site report** window (Quick / Standard / Detailed) from + New, Site & procurement and Timesheets. Site material
  requests: approve all or **line by line** (approve, reduce or reject each line with a reason; all rejected = Rejected),
  and **Create PO** opens the app's purchase order window with the lines still to order, linked to the request. Role
  matrix as p19: the Quantity Surveyor no longer opens Site & procurement or Timesheets (Projects User dropped from those
  pages) and now has Home; the project panel's *Open screen* shows only screens the user may open.

## 1.8.0 — Chinese & menu builder
- **Simplified Chinese (中文)**: every string the app shows — pages, menus, buttons, messages, doctype and workspace labels,
  reports, number cards, the guided tour and the Test Centre sections — in `translations/zh.csv` and `locale/zh.po`
  (language code `zh`, alongside ERPNext's own Chinese). 3,715 strings, 100% of what `tools/i18n_extract.py` finds:
  1,043 from the approved prototype (p19), 2,672 translated for this release. The print formats stay English + Arabic.
- **Language switch** in the top bar: English / العربية / 中文. It sets the user's language and reloads; Arabic keeps the
  right-to-left layout, Chinese uses a CJK font stack (PingFang SC, Microsoft YaHei, Noto Sans SC) only when chosen.
  Migrate makes sure the Language records `ar` and `zh` exist and are enabled.
- **Menu builder** (Admin → Menu builder, System Manager and Managing Director): show or hide, rename in English, Arabic
  and Chinese, and reorder every menu group and screen, and add custom links (web address, /app/… or #page) — for the
  whole site, one company or one role. Role beats company beats site, field by field. Live preview, Save, Reset to
  standard per scope and a change log (who, when, what). Stored in **Hipersign Menu Override**, logged in
  **Hipersign Menu Log**. Applied when the desk loads, on top of the feature packs; a hidden screen also leaves + New and
  the top-bar search. A menu never grants access — role permissions still decide.
- NAV groups and items have stable keys (`g:<group>`, the target's slug), so groups added later (Projects, Manufacturing)
  appear in the builder with no other change.
- Test Centre: ZH-01…07 and MENU-01…12. Arabic labels for the builder and the language switch.
- Tools (no bench needed): `tools/i18n_extract.py`, `tools/i18n_build.py check zh`, `tools/test_menu.py`.

## 1.7.3 — the 2 Nov review: every New in the new window, prints as on the prototype
- **Every "New" opens the create window** with Quick / Standard / Detailed — from + New and from each list's Add: supplier bill
  (match to the order or goods receipt, lines and VAT), debit note, receive payment (oldest invoices first, bank charges),
  credit limit request (limit, exposure, overdue), warranty claim (serial look-up), delivery trip (delivery notes as stops,
  driver and vehicle), employee advance, currency rate and user. Stock transfer and stock count open their windows from + New.
  Detailed mode now holds every field a user fills on each document.
- **Print formats** follow the prototype: quotation, order confirmation, proforma, packing list, tax invoice / credit note,
  delivery note, purchase order reworked; new goods receipt note, payment / receipt voucher, delivery trip sheet, payslip,
  debit note, RFQ and pick list (defaults set).
- **Supplier quotation comparison** page (Purchasing → Quotation Comparison): offers per item side by side in their currency
  and in AED, lead time and terms, best price marked, award per item → purchase orders. Replaces ERPNext's prepared report.
- **Quotations tab overview** (prototype p18): open value and count, expiring in 7 days, past validity, accepted this month,
  conversion, average. **Totals** under every money table on the module pages (one line per currency when mixed).
- **Credit note** window (sales return against a tax invoice, quantities returned, reason) and **Export order** opens the order
  window flagged as export; Trade Journey and Landed Cost no longer offered to Sales Managers (no purchase access), comparison page
  not offered to Finance.
- New message works again (the editor could not start in the dialog). Collapsed menu shows the square Hipersign mark; it is
  also the browser-tab icon. The guided tour points at the 1.7 pages and tabs. Live deal demo button removed.

## 1.7.2 — VAT on quick quotations and orders
- Quotations, sales orders and purchase orders made from the create modal (Quick, Standard or Detailed) now carry the
  company's VAT: Hipersign Settings' local template, the company's default, or its standard VAT template.
- Export customers get the company's zero-rated / export template; overseas suppliers get no VAT on the order.
- The modal's totals show the same rate as the saved document (it follows the picked customer / supplier).
- **Attach documents** on the create modals, as on the prototype: the record's document rules (Blocks next step / Required /
  Optional) with an Attach button each; files are saved with their document type and a blocking rule is met in the same
  Submit / Post (save → attach → submit). Purchase order, journal entry, import / export shipment, LC and more.
- **New lead** in the prototype's order and widths, with its starting values (source Website enquiry, Dubai, close in 30 days,
  owner = you, follow-up tomorrow, "First call — understand the requirement").
- The create modal shows its full height (totals, credit and documents visible); the buttons stay at the bottom of the screen.
- Picking the source fills the form: export order → destination, mode, incoterm and the payment / currency / 0% VAT note;
  purchase order → import shipment's mode and ports; LC amount and terms note from the order.
- Journal entry: Empty / Balanced / Difference badge by the totals. Purchase request: "In stock" beside each item.
- Lists that have a prototype page (Export Shipment, Journal Entry, Company Document / Deadline, Asset, Employee, Leave,
  Expense Claim, Payroll Entry, Attendance, Tax Return) open the page on the matching tab when opened from search or the
  sidebar; lists opened with filters stay lists, and each page's ⋯ menu has "Classic list".

## 1.7.1 — every "New" opens the prototype modal
- The lists' **Add …** button and the + New menu now open the prototype's create modal for quotations, sales and purchase
  orders and the other covered forms on every load (the list button was sometimes left as ERPNext's "Add …" → full form).
- **New delivery note / goods receipt / tax invoice** ask which order (or delivery) it is for, then open Pick & deliver,
  Receive goods or the invoice modal — as on the prototype. "Open full form" stays for anything else
  (invoice without a delivery, services).
- A dashboard's "+ Quotation / + Sales order" carries the customer into the modal.

## 1.7.0 — the prototype's create forms, remaining pages and record views
**Create forms (prototype modal):** every "New …" opens one modal — title and subtitle, the Quick / Standard / Detailed switch
in the header, two-column fields — instead of ERPNext's quick entry or full form ("Open full form ↗" is still there).
- Quotation, Sales order, Purchase order: the line table inside the modal (item · qty · rate · disc · available · margin · net),
  totals with VAT, the customer group's discount in Disc %, and for sales orders the credit limit / exposure / after this order;
  Save draft, Submit (through the approval workflow), Save & send on WhatsApp; "+ Add new prospect / client…" on the quotation
  makes the prospect (lead) or customer from the same modal.
- Lead, Customer, Supplier, Item, Service, Warehouse, Driver, Employee, Fixed asset, Contact, Address, Customer group, Payment
  terms, Bank account: the quick cards drawn in the same modal.
- "From a document" modals, as on the prototype: Pick & deliver (sales order → delivery note, quantity and warehouse per line),
  Receive goods (purchase order → receipt: scan, accepted / rejected, warehouse; blocked before customs clearance), Receive
  payment, Pay supplier and Create invoice — from the panels' and pages' buttons.
- New import shipment, export shipment, purchase request, stock transfer, stock count (to the Warehouse Manager), journal entry
  (debits = credits), cheque received / issued (party and invoice from the invoice picked), expense claim, leave request, LC
  application (supplier, currency and amount from the order; cash margin), bank guarantee (amount from contract value × %),
  company document — the prototype's fields, in the same modal (api/create.save_doc).

**Pages in the prototype's design** (KPI row, tabs, chips, lists and boards; rows open the record panel):
- Exports & Re-exports — shipment board (Booked & packed · Customs · On the way · Documents complete) with all shipments
  below, export orders, documents & VAT proof, costs & margin, re-exports.
- Accounting — trial balance, balance sheet, general ledger, journal entries, cost centres, currency revaluation, chart of
  accounts, period closing.
- Company Compliance — register with company chips, calendar, deadlines, renewals, reminders & ToDos, document types.
- Fixed Assets — register by category, maintenance & renewals (service, Mulkiya, insurance), depreciation.
- HR & Payroll — employees, attendance, leave (approve from the panel), payroll & WPS file, expenses & advances,
  documents & end-of-service gratuity.
- KYC & Compliance — customer and supplier files (licence, TRN, exposure, status), rules.
- UAE Corporate Tax — full-year forecast / year to date, the computation, approval steps, tax adjustments, prepare the return.
- Group & Countries — structure by country, dashboard per company, inter-company, consolidated P&L and balance sheet,
  company books. (ERPNext's "Unable to find exchange rate" pop-ups no longer appear when the nearest rate is used.)
- Customer Portal — /portal in the prototype's design (orders with the order journey, quotations, invoices, statement,
  deliveries, warranty); the desk page previews it for any customer.
- Finance — new tabs Customer advances, Collections, Bank reconciliation, Cash flow, Profit & loss and a VAT payable KPI.

**Record panels** for export shipment, payment, journal entry, supplier bill / debit note, employee, payroll run (WPS file),
expense claim (approve / reject / pay), employee advance, leave (approve / reject), bank guarantee, fixed asset, purchase
request (request quotations / order directly), RFQ, post-dated cheque (deposit / clear), tax return, stock entry, pick list,
delivery trip, warranty claim, company document (start renewal) and deadline (mark done).

**Demo data:** service, Mulkiya and insurance dates on the vans and forklift, a custodian per asset, today's attendance; the
view-only login also sees HR and fixed assets.

## 1.6.1 — 30 Oct 2026 — fixes from the 1.6.0 Test Centre re-run on tradingdemo
- Finance → To bill and the *Delivered, not invoiced* KPI count what is left to invoice from the non-return invoice lines; a
  credit note no longer puts a fully invoiced delivery back on the list (FIN-02). Dispatch's *Not invoiced* flag and the
  delivery notes' *To bill* chip use the same rule.
- Dispatch board: no empty second line on cards without driver, vehicle or trip.
- Test Centre wording: DSP-01 (Delivery note button sits on *To deliver*), FX-01 (a month locked by a VAT return refuses the
  revaluation entry), FIN-02.

## 1.6.0 — 30 Oct 2026 — record panel, CRM and sales pages, guided tour, Live deal demo, Test Centre fixes
**Record panel:** leads, quotations, sales orders, customers, tax invoices, delivery notes and items open in the prototype's side
panel — header facts, progress line, sections and tables (Excel), documents box, history and next-step buttons (Make sales order,
Create delivery note, Receive advance, Record payment, Lost with a reason, Message, Email, WhatsApp, Print); links inside open the
linked record's panel with Back; ↗ opens the full form.
**Module pages:** CRM & Leads (5 KPIs, pipeline board with drag-and-drop stages, owner and source filters, all leads, follow-ups,
sources & performance) and Quotations & Orders (6 KPIs, orders / quotations / customers & credit / price lists tabs with status chips).
**Operations pages:** Supplier Purchasing, Imports & Shipments (shipment board), Goods Receiving, LCs & Guarantees, Dispatch &
Delivery (dispatch board), Finance (receivables ageing; Receive / Pay / Invoice buttons), Warehouse & Inventory (stock items, movements,
transfers, counts, reservations, warehouses, ageing) and UAE VAT & E-invoicing (live VAT 201 boxes split by emirate from the customer's
address, return history, sales and purchase VAT, e-invoicing readiness); the sidebar opens these pages.
**More record panels:** purchase orders, suppliers, import shipments (status steps, documents, landed charges, Mark next status,
Receive, Create landed cost), letters of credit (Mark next status, Block / Release margin, Book trust receipt) and goods receipts
(Create supplier bill, Return to supplier).
**Guided tour:** the prototype's 13 chapters (79 steps) from Home or the user menu, following the pack and the user's access.
**Live deal demo** (demo sites, Hipersign Settings): one deal from enquiry to the customer's cheque, step by step on real records,
with revenue, landed cost, gross profit and cash at the end; Reset removes the run.
**Demo data:** sales delivered and invoiced this month; the Oman subsidiary's figures (OMR), so the group consolidation shows LLC, FZE
and Oman with the 30% minority (GRP-03). **Test Centre:** 114 scripts (TOUR-01, DEAL-01, CRM-02, SAL-04, PANEL-02, PUR-03, IMP-03,
LC-05, RCV-01, STK-02, DSP-01, FIN-02, VAT-03).
**Group consolidation:** a member without a stored rate on the year start translates equity at the nearest stored rate, not 1 (GRP-03).
**Settings:** changing the desktop tiles, theme or menu options reloads the page once, so the desktop shows the change at once.
**Fixes from the Test Centre run on the demo site (29 Oct 2026):**
- Sales: a sales person's extra discount is kept on save (the customer-group rule is the floor), so a 15% order goes to the Sales
  Manager (SAL-02); the Finance Manager (Accounts Manager) can approve sales and purchase orders (SAL-03, PUR-01); sales staff can
  draft credit notes and the Sales Manager submits them, ordinary invoices stay with Accounts (RET-01/02); the Order Tracker's
  Statement of Account opens the customer statement for sales staff instead of the General Ledger they cannot open (TRK-01).
- Top bar: the company chosen in the scope drop-down now sticks (it was overruled by the site's default company) and quick documents
  use it (TOP-01); the top bar stays while viewing as another user and on phones (USR-01); quick quotations and orders use the
  customer's own price list (PL-01); Hipersign print formats are the default for quotations, orders, invoices, delivery notes and
  purchase orders, so Print and the WhatsApp link send the bilingual layout (QTN-01).
- Home: Work for today shows a line only when the user can open its records, counts follow permissions, and switched-off features
  (CRM, cheques, reconciliation, imports, warranty, HR, compliance) are hidden; leave requests only for HR and the leave approver
  (HOM-02, SET-05); the New panel hides Lead when CRM is off.
- Lists no longer scroll sideways at 1366 px and wider: columns shrink, headings stay over their values, the last column stays
  readable (UI-01).
- Permissions: storekeepers can make receipts and delivery notes from orders (read on Address, Contact, Account — IMP-02); the
  warehouse team can log warranty claims (SER-02); any desk user can record Test Centre results (TST-01).
- Smart reorder makes purchase orders for foreign-currency suppliers (CNY) — the currency and rate are set before ERPNext fills the
  order (RO-01). Portal logins linked through their contact find their customer (PRT-01). Post-dated cheque holding accounts are
  created when set-up finishes, so cheques post on receipt on new sites (PDC-04).
- Demo data: exchange gain/loss and round-off accounts (FX-01); the advance order's stock reserved (ADV-03); portal user in the
  customer's Portal Users; the orders waiting for approval carry their LPO and the LPO exception sits on its own draft (SAL-03,
  KYC-02, DOC-03); an overdue Horizon invoice for the collections hold (COL-02). Re-running Load demo data repairs existing demo sites.

## 1.5.6 — 29 Oct 2026 — the prototype's shell, quick cards and the audit fixes
**Top bar** (Hipersign desk theme): ☰ shrinks the menu to an icon rail (slides in on narrow screens); real search as you type
(customers, suppliers, items, orders, quotations, invoices, shipments, serials) with keyboard control and "/" to focus; one scope
drop-down (whole group, a country or one company) and one period drop-down that Home and new documents follow; **+ New** opens the
prototype's 13 groups with a Quick / Standard / Detailed chip, and All opens a new list-style Create New page; the bell groups
mentions, emails, documents to review, WhatsApp, approvals, lead follow-ups and alerts, with Mark all read; the user menu has Switch
user (demo sites), Add / Manage users, Presentation mode, My settings, Toggle theme and Log out. Demo and view-only banners, and a
Book a demo dialog (WhatsApp or email to sales@hipersignerp.com).
**Menu:** the prototype's 32 entries in 8 sections, list sub-items under each module (open sections remembered), count badges on
Messages, Approvals, Insights & Alerts and CRM & Leads, a Book a demo box; Add Sidebar Item only for administrators; pages opened from
the top bar keep the Hipersign menu. Customer Portal opens the customer pages (/statement, /warranty) as a preview of any customer.
**Quick cards** for 13 masters with the prototype's fields — Lead, Customer (with contact, address and credit-limit request),
Supplier (contact, address, bank IBAN), Item / Service (Arabic name, HS code, origin, standard buying and selling prices, reorder level,
default warehouse), Address, Contact, Warehouse, Employee (salary parts, WPS IBAN, document expiries, salary assignment), Fixed asset,
Customer group (discount pricing rule), Payment terms, Bank account and Driver & vehicle. They replace Frappe's quick entry (also from
a Link field's "Create a new …") and hand typed values to the full form and back.
**Form modes** on 26 more forms (Supplier … Company Document): Standard hides only rarely used fields, never a mandatory one or one
that holds a value; the lists' New buttons carry the mode.
**Choice lists:** Emirate on leads, customers, addresses and warehouses; supplier type and usual Incoterm; vehicle type; quotation
delivery period and warranty; Delivery and Site address types; lead source shown on leads and a link on customers; lead owner limited
to sales users. Emirate, supplier type, vehicle type and delivery period are editable Hipersign lists.
**View-only demo account** ("Demo Viewer" role): opens every page and can switch user, but every change is refused on the server.
**Fixes from the audit:** smart reorder purchase orders in foreign currency carry the exchange rate; the approval reason is kept on a
sales order in approval; VAT returns fall back to invoice totals and cannot be sent empty; Log activity on a lead saves note, stage,
follow-up and next action together; an export shipment links an invoice made from its delivery note; return invoices no longer
reduce the original's outstanding twice; group consolidation splits inter-company balances and rounds; Home follows the top-bar scope
and period, hides features that are off and opens stock at the live stock view; post-dated cheque wording; quick invoice re-reads its
list; quick receipt nets credit notes; quick rates use ERPNext pricing rules; stock reservation warehouse filtered by company; advance
receipts from on-hold orders; LC margin release uses the margin account; Order Tracker totals in base currency; the Feature pack
field applies its switches; a driver-only login opens /driver (Administrator no longer lands there); the Home chart no longer redraws
while hidden; Create menus without Work Order, Production Plan, Project and other non-trading documents; the user name never wraps in
the top bar; Gulf currencies shown as AED / SAR / OMR; serial look-up explains itself before a scan; no sideways scrollbar in the
Arabic menu; Arabic for the new top bar, cards and menu.
**Access:** Sales User and Sales Manager may read, print and report sales invoices (ERPNext 16 refused them every Customer form);
users who may read customers or suppliers but not invoices (stores, logistics, HR) open those forms without the invoice totals;
every user opens Hipersign Home after login (the older per-role workspaces are cleared — a buyer was sent to one he could not open);
the demo Managing Director, Purchase Manager, Sales Manager and Warehouse Manager may add suppliers, items and customers.
**Demo loader:** service invoices from January, opening capital and monthly overheads (positive year-to-date figures); VAT settings;
import charge bills; inter-company VAT; a bank statement to reconcile; payroll, leave, attendance, expense claims and an advance;
fixed assets; delivery trips with vehicles; credit-limit requests; messages with mentions; the view-only demo user.
**Test Centre:** 20 new scripts (101 in all).

## 1.5.5 — 28 Oct 2026 — top bar off the app launcher
The top bar no longer shows on the app launcher (/desk), which has its own header.

## 1.5.4 — 28 Oct 2026 — the prototype's top bar; demo data fixes
**Top bar** (Hipersign desk theme): search (Frappe's own search, Ctrl+K), the user's company for new documents, **+ New** (Create New),
the ع / EN language switch, notifications with an unread count, and the user menu (My Settings, Toggle Theme, Log out). The menu's
Search and Notification rows are hidden while the top bar is on. The "…" menus on number cards show on hover only.
**Document rules:** journals the app makes itself (post-dated cheques, LC margins and trust receipts) no longer need a supporting
document — recording a received cheque of AED 10,000+ was refused — and they are left out of the Missing Documents report.
**Demo loader:** the purchase request is in pieces, not cartons; serialised opening stock lands on the opening account; the stock
reservation stays and the draft pick list goes on another order; an invoice 72 days overdue (Horizon Trading, collections hold) and one
25 days overdue (Elite Systems); an open EUR supplier invoice so the month-end revaluation has something to revalue; the lead's
quotation has prices and VAT; customer and supplier cheques are created independently; the company's own TRN on its registration
documents; every item on the Wholesale price list; shipment arrival and clearance dates follow the ETA.

## 1.5.3 — 28 Oct 2026 — new looks reach every browser
The app's stylesheets and scripts are now loaded with the app version in their address (`…/hipersign_theme.css?v=1.5.3`). They are
served as "immutable" for a year and the site's service worker caches them, so until now a browser that had opened the site kept the
old look and old scripts after an update. `app_version` in hooks follows `__version__`.

## 1.5.2 — 27 Oct 2026 — closer to the prototype's look
Theme additions (Hipersign desk theme only): 24 px page margin on the Hipersign pages and the Order Tracker; workspaces use the full
width instead of a 900 px centred column; page title 21 px / 800; menu group headings 11 px bold, a light-blue bar beside the active
item; Approve green and Reject outlined red on Hipersign pages; document numbers in blue; list rows without likes, comment counts and
modified time; number-card values in dark ink with the menu on hover; kanban columns and cards as in the prototype; the Order
Tracker's stages as a numbered stepper.

## 1.5.1 — 27 Oct 2026 — the prototype's company on the demo
**Company name in Arabic** field on Company (printed on the bilingual tax invoice and quotation). The demo loader gives the demo
company the prototype's details when they are empty: TRN 100384927150003, *هايبرساين ديمو للتجارة ذ.م.م*, Office 1204, Al Quoz
Business Tower, Dubai. A new demo site set up as *Hipersign Demo Trading LLC* (abbreviation HDT) matches the prototype throughout.

## 1.5.0 — 27 Oct 2026 — the prototype's screens
Built and tested on **Frappe 16.29 / ERPNext 16.30**. The screens of the prototype that ERPNext has no counterpart for, as desk
pages in the Hipersign menu. Every figure is computed from the live records and opens the records behind it.

**Hipersign Home** (users land here after login): the group block with each company translated to the group currency, the
connected trading lifecycle (7 stages), work for today, management priority actions, the KPI cards, profit for the period and
monthly sales vs purchases — this month, last month or year to date, for all companies or one. Each user sees only the figures
for records they may open; the group block and P&L are for finance roles.
**Approvals:** every document waiting for a decision — workflow documents, document exceptions, VAT/CT returns, leave and
expense claims — with the rule that routed it and who must act. Approve / Reject here moves the source document exactly as its
own form would (KYC, credit and other rules still apply).
**Insights & Alerts:** 13 deterministic rules (customs documents, stock, slow-moving stock, receivables, cheques, VAT, margin,
employee and company documents, LCs, guarantees, KYC, exceptions) with evidence, consequence and recommended action; Mark
actioned / Dismiss sticks until the situation changes. No AI model is involved.
**Messages:** one inbox for the comments, @mentions, emails and WhatsApp sends kept on orders, shipments, invoices and leads;
replying adds a comment to the record and notifies anyone mentioned.
**Trade Journey:** one purchase order followed through shipment, receipt, landed cost, the sales that used the stock, delivery
and payment. **Landed Cost & Margin:** each shipment's charges by type, the landed cost stack, item margins after landed cost
and a price helper. **Test Centre:** the demo test scripts with Pass / Fail / Blocked and notes kept on the site.
**Add-ons & Pricing:** the prototype's add-on catalogue with hours, dependencies, rate, contingency and a printable estimate.
**Also:** amounts on the new screens are written AED 1,234.50 as in the prototype; the Hipersign menu and desktop tile are
rebuilt after every migrate (Frappe removed the tile as an orphan during migrate); the demo loader adds sample conversations.

## 1.4.0 — 27 Oct 2026 — the prototype's look and menu
Built and tested on **Frappe 16.29 / ERPNext 16.30** (the versions on the Hipersign servers) with ERPNext's UAE chart of accounts.

**Hipersign theme:** the prototype's colours, fonts (Plus Jakarta Sans, Lexend, IBM Plex Sans Arabic — bundled, no outside
calls), navy menu, white cards on a soft background, blue buttons and tinted status pills on every ERPNext screen, in light and
dark mode and right-to-left Arabic. Hipersign Settings → *Look & menus* → Desk theme switches it off.
**The prototype's menu:** one sidebar, *Hipersign ERP*, with the prototype's groups — Overview, Sales, Purchasing, Inventory &
Delivery, Finance & Tax, People & Assets, Admin — and the logo on top. It stays on screen on every page it lists; entries of
switched-off features are left out; groups a user has nothing to open in are hidden.
**Desktop:** one *Hipersign ERP* tile; the other app tiles (Selling, Buying, Manufacturing, GST India…) are hidden and come back
when the option is switched off or the app is uninstalled. Users land on Hipersign Home after login, and ERPNext's
“Getting Started” panels are switched off (both optional).
**Demo data:** on ERPNext's UAE chart the demo company now banks with Emirates NBD and invoices on *Trade Receivable* (the chart
sets a credit-card account as the bank and “Trade in Opening Fees” as the receivable).
**Fix:** the Quick / Standard / Detailed *New* button waits for the list to finish loading on Frappe 16.29.
**Note:** later Frappe 16 releases replace the sidebar system (per-module “Sidebar” documents). There the theme still applies but
the menu is left to Frappe; the menu will be moved to the new system in a later version.

## 1.3.1 — 27 Oct 2026
**Demo data loader:** works on sites with India Compliance installed (items get an HSN/SAC code from their HS code), and can be
run again after a partly failed load — the second run fills in what is missing (KYC blocks and stock reservations made by the
first run no longer stop the history being created). Charts of accounts without a *Temporary Opening* account (e.g. ERPNext's
UAE chart) get one for the opening stock.

## 1.3.0 — 26 Oct 2026
Built and tested on **Frappe 16 / ERPNext 16**. Brings the app in line with the prototype's set-up, document and form-mode work.

**Set-up wizard:** on first login the System Manager answers two questions — single company or group, and which pack
(Starter, Standard, Enterprise). 21 feature switches in Hipersign Settings → *Setup & features* follow the pack; switching a feature
off hides its menus and workspaces and turns its approval workflow off, and nothing is deleted. **Load demo data** is now a button
(Hipersign Settings → Set-up), allowed only on a new or demo site.
**Form modes:** Quick (a small dialog with a smart item finder, *Repeat last order*, *Save & send on WhatsApp*), Standard (the essential
fields) and Detailed (every field) for Quotation, Sales Order, Purchase Order, Sales Invoice (Quick invoice from deliveries), Payment
Entry (Receive payment, oldest invoices first), Customer, Item and Lead. Each user's choice is remembered; defaults per role in settings.
**External documents:** typed attachments, **Hipersign Document Rule** (Block / Required / Optional, on submit or on a status change,
from an amount), a Documents box at the top of each form, **Document Waiver** (exception approved by the right role, then due by a date,
overdue alerts) and the **Missing Documents** report. Document level Off / Recommended / Full follows the pack.
**Company compliance:** **Company Document** (licences and certificates with expiry, renewal and reminders at 60/30/7/0 days) and
**Company Deadline** (VAT, corporate tax, WPS, ESR… repeating), with calendars.
**Group consolidation:** **Hipersign Group Member** (a company on this site or on another site through an API key),
**Group Trial Balance** sync (daily), and the **Hipersign Group Consolidation** report — P&L at the average rate, balance sheet at the
closing rate, equity at the historical rate, translation reserve, inter-company eliminations and minority interests.
**Money:** post-dated cheques post when received / issued (cheques in hand / cheques issued accounts) and clear, bounce and replace
through journal entries; a supplier payment on top of issued cheques is stopped; **Book the difference as bank charges** on payments
with a limit per role; the LC cash margin release is drafted when an LC is paid, expires or is cancelled, and the paid date cannot be in
the future; price lists can limit the item list (tick *All items* to override).
**Editable lists:** payment methods, shipment modes, lost reasons and return reasons in **Hipersign List Value**.
**New workspace:** Hipersign Documents. **Uninstall** now keeps a JSON copy of the app's records and removes its fields, workflows and roles.
**Fixes for ERPNext 16:** workflow conditions, desk links (`/desk`), number cards on all Hipersign workspaces (they did not show before),
cheque party type, LC bank account fallback, serial-number setting, payment schedules, revaluation rounding.
**Upgrade:** `bench migrate` — patch `v1_3.upgrade_from_v12` keeps upgraded sites on the Enterprise pack with every feature on and
cheques posting only when cleared, as in 1.2. Arabic added for all new labels and messages.

## 1.2.0 — 24 Oct 2026
Brings the app in line with the prototype's newer modules.

**New record types:** Letter of Credit (with cash margin and trust receipt), Tax Return (VAT 201 / Corporate Tax, approved and filed by hand on EmaraTax).
**New report:** Hipersign Smart Reorder, with one-click draft purchase orders per supplier.
**New rules:** advance before delivery (Delivery Note, Pick List); KYC block on confirming sales orders; collections hold on new orders;
VAT period lock on approval (Accounting Period).
**New fields:** Item model; Supplier lead time and KYC; Customer KYC; Payment Term *Advance*; Sales Order advance required / status;
Sales Invoice collection stage, promise to pay; Company ownership %, minority partner, role, licence.
**Daily tasks:** collection stages, KYC expiry, LC expiry and trust receipt due, advances not received, tax return due. **Monthly:** revaluation reminder.
**Workspaces:** new cards for advances & collections, trade finance, tax & period end, group companies, purchasing, reservations & picking, expenses.
**Demo data:** item/customer/supplier details, advance orders (received and on hold), dunning types and a promise to pay, a purchase request
with two supplier quotations, a stock reservation and pick list, two LCs and a bank guarantee, last month's VAT return waiting for approval,
month-end exchange rates and a draft revaluation, and the group (holding, FZE, Oman 70%) with an inter-company invoice.
**Upgrade:** `bench migrate` — patch `v1_2.settings_defaults` gives the new settings their defaults. Arabic labels added for all new items.

## 1.1.0 — 22 Oct 2026
Role-based home workspaces, returns with approval, post-dated cheques, serial numbers & warranty, driver app, customer portal pages,
HR documents & WPS, bank reconciliation, fixed assets, Arabic labels.

## 1.0.0 — 21 Oct 2026
First release: workflows and thresholds, import & export shipments, CRM pipeline, credit limit requests, bilingual print formats,
sending by email / WhatsApp, Hipersign Trading workspace and branding.
