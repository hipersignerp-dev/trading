# Changelog

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
