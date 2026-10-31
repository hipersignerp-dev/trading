# Changelog

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
