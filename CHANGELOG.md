# Changelog

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
