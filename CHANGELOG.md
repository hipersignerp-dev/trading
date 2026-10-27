# Changelog

## 1.3.1 — 27 Oct 2026
**Demo data loader:** works on sites with India Compliance installed (items get an HSN/SAC code from their HS code), and can be
run again after a partly failed load — the second run fills in what is missing (KYC blocks and stock reservations made by the
first run no longer stop the history being created).

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
