# Hipersign Trading — ERPNext app

The Hipersign Trading, Distribution & Import/Export ERP, packaged as a Frappe app for **ERPNext v16** (1.3 is built and tested on Frappe 16 / ERPNext 16; 1.2 and earlier on v15).
It turns the clickable prototype into real ERPNext behaviour, and the app is self-contained:
everything it adds lives in its own module (**Hipersign Trading**) and can be installed on one site
without touching any other site on the same server.

| Prototype section | In ERPNext |
|---|---|
| Hipersign Home dashboard, gross & net profit | Workspace **Hipersign Trading** + number cards + charts |
| Create New | Page `/desk/hipersign-create` |
| Sales Order Tracker (stages, popups, reports, email/WhatsApp) | Page `/desk/sales-order-tracker` |
| CRM & Leads pipeline, follow-ups | Lead + custom fields + Kanban **Hipersign Lead Pipeline** + daily follow-up ToDos |
| Approvals (PO, SO discount / below cost / credit, supplier payment, stock count, credit limit) | 5 workflows + settings thresholds |
| Import & Shipment, customs clearance, landed cost | DocType **Import Shipment** → Purchase Receipt (blocked before clearance) → Landed Cost Voucher |
| Export & Re-export, 0% VAT, proof of export, duty refund | DocType **Export Shipment** → Delivery Note → zero-rated Sales Invoice |
| Credit limit approval | DocType **Credit Limit Request** (customer limit raises go here automatically) |
| Bilingual documents | Print formats: Quotation, Order Confirmation, Proforma Invoice, Tax Invoice (local/export), Delivery Note, Purchase Order, Packing List |
| Print / Email / WhatsApp icons | **Send** menu on Quotation, Sales Order, Sales Invoice, Delivery Note, Purchase Order, Export Shipment, Lead |
| Customisation (thresholds, rules) | **Hipersign Settings** |
| Branding (no ERPNext wording) | Logo, app name, favicon, login splash |
| **v1.1** Role-based home | Workspaces **Hipersign Finance / Sales / Warehouse / HR** (each user's home is set by role) |
| **v1.1** Returns & credit / debit notes | Sales / Purchase Invoice *Is Return* + **Return reason**; only the Sales / Purchase Manager can submit; bilingual **Tax Credit Note** print |
| **v1.1** Post-dated cheques | DocType **Post Dated Cheque**: in hand → deposit → cleared (creates the Payment Entry) / bounced (bank charges + alert) / replaced; issued cheques to suppliers |
| **v1.1** Serial numbers & warranty | Serial no. series + warranty on items; page **Serial & Warranty Look-up**; Warranty Claim with resolution & replacement serial; serials on the delivery note print |
| **v1.1** Bank reconciliation | ERPNext **Bank Reconciliation Tool** + Bank Statement Import (in the Finance workspace) |
| **v1.1** Driver app (signature, photo, GPS) | Web page **`/driver`** for the *Driver* role; proof of delivery saved on the Delivery Note |
| **v1.1** Customer portal | ERPNext portal (orders, invoices, quotations) + **`/statement`** and **`/warranty`** pages |
| **v1.1** HR, documents & WPS | Employee UAE documents with expiry alerts; **WPS salary file (SIF)** button on Payroll Entry (needs the Frappe HR app) |
| **v1.1** Fixed assets | ERPNext Asset, depreciation and maintenance (in the HR workspace) |
| **v1.1** Arabic interface | Arabic labels for everything the app adds (`locale/ar.po`); set *Language = Arabic* on a user for right-to-left |
| **v1.2** Master records | Item: brand, **model** (new field), purchase unit with conversion (e.g. 1 Carton = 100 Nos), weight per unit, warranty, minimum order, lead time, default supplier. Customer: type, territory, currency, price list, sales person (sales team), website. Supplier: group, **lead time** (new field), website, address — mostly ERPNext's own fields, filled by the demo loader |
| **v1.2** Customer advances & payment schedules | Payment terms with an **Advance** line (Payment Term → *Advance — to be received before delivery*); the sales order shows *Advance required* and *Advance status*; **Delivery Note and Pick List are blocked until the advance is received** (Payment Entry against the order); advances applied to the invoice with ERPNext's *Get advances* |
| **v1.2** Collections | Overdue invoices move through Friendly reminder → Second reminder → Final notice → Hold new orders (days in Hipersign Settings) with a ToDo at each stage; **Promise to pay** on the invoice pauses reminders; past the hold limit new orders need the Finance Manager; ERPNext **Dunning** letters |
| **v1.2** KYC & compliance | Trade licence no., issuer, expiry and **KYC status** on customers and suppliers; expiring-licence ToDos; **a sales order cannot be confirmed when the licence has expired or KYC is Blocked** (drafts and quotations allowed) |
| **v1.2** Purchase requests & supplier quotations | ERPNext Material Request → Request for Quotation → Supplier Quotations → **Supplier Quotation Comparison** |
| **v1.2** Smart reorder | Report **Hipersign Smart Reorder**: sales trend, lead time (item → supplier → country), safety stock, reorder point, projected stock; suggestions rounded to full purchase units and never below the minimum order; **Create purchase orders** makes one draft PO per supplier |
| **v1.2** Reservations & picking | ERPNext **Stock Reservation** (switched on by the loader) and **Pick List** from the sales order |
| **v1.2** Letters of credit & trust receipts | DocType **Letter of Credit**: applied → issued → documents presented → accepted (maturity from the tenor) → paid; cash margin and trust-receipt loan with interest and due date; draft journal entries for the margin and the trust receipt; expiry and loan-due ToDos. Guarantees use ERPNext **Bank Guarantee** |
| **v1.2** VAT & corporate tax filing | DocType **Tax Return** (VAT 201 / Corporate Tax): figures from ERPNext's UAE VAT 201 → Finance Manager **approves and locks the period** (an ERPNext Accounting Period closes invoices, payments and journals) → filed by hand on **EmaraTax** with the reference → paid. Due-date reminders |
| **v1.2** Currency revaluation | ERPNext **Exchange Rate Revaluation** (month-end unrealised gain/loss, reversed next month) and realised gain/loss on Payment Entries; a monthly reminder to the Finance Manager |
| **v1.2** Group companies | Group company *Hipersign Demo Group* with the LLC, an FZE and a 70%-owned Oman company (ownership %, minority partner and licence on Company); inter-company customer/supplier (*Represents Company*), an inter-company invoice mirrored as a purchase invoice, and ERPNext's **Consolidated Financial Statement** |
| **v1.4** Look & menus | The prototype's theme (colours, fonts, navy menu, cards; light, dark, Arabic) and its menu as one *Hipersign ERP* sidebar; one desktop tile, Home after login — Hipersign Settings → **Look & menus** |
| **v1.5** Prototype screens | Hipersign Home (group, lifecycle, today's work, alerts, KPIs, P&L), Approvals, Insights & Alerts, Messages, Trade Journey, Landed Cost & Margin, Test Centre, Add-ons & Pricing — all in the Hipersign menu |
| **v1.3** Set-up & packs | First-login wizard: single company or group, Starter / Standard / Enterprise; 21 feature switches in **Hipersign Settings → Setup & features** hide menus and switch workflows off without deleting anything; **Load demo data** button |
| **v1.3** Quick / Standard / Detailed forms | **New · Quick** on the lists; Quick dialogs for quotation, sales order, purchase order, quick invoice, receive payment; Standard hides the rarely used fields; **Form mode** button on each draft; choices remembered per user, defaults per role |
| **v1.3** Documents & exceptions | Typed attachments, **Hipersign Document Rule**, Documents box on forms, **Document Waiver**, report **Missing Documents**, workspace **Hipersign Documents** |
| **v1.3** Company compliance | **Company Document** (licences, certificates, renewals, reminders) and **Company Deadline** (statutory dates, repeating) |
| **v1.3** Group consolidation | **Hipersign Group Member** (this site or another site by API key) → **Group Trial Balance** → report **Hipersign Group Consolidation** (translation, eliminations, minority interests) |
| **v1.3** Money | Cheques posted when received / issued; overpayment guard; **Book the difference as bank charges** with limits; LC margin release; price-list item filter; editable lists (**Hipersign List Value**) |
| **v1.2** Expenses & advances, cost centres, period closing | ERPNext / Frappe HR **Expense Claim**, **Employee Advance**, **Cost Center**, **Period Closing Voucher** — added to the workspaces |

## 1. Install on a separate demo site (live site untouched)

```bash
cd ~/frappe-bench
bench get-app https://github.com/<your-org>/hipersign_trading.git      # or: bench get-app /path/to/hipersign_trading
bench new-site hipersign-demo.yourdomain.com
bench --site hipersign-demo.yourdomain.com install-app erpnext
```

Open the demo site and complete the **ERPNext setup wizard**: company *Hipersign Demo Trading LLC*, country
*United Arab Emirates*, currency *AED*. Then:

```bash
bench --site hipersign-demo.yourdomain.com install-app hipersign_trading
bench build --app hipersign_trading && bench restart
```

Installing creates everything the app needs (fields, roles, workflows, workspaces, rules, lists, cheque accounts) and loads **no**
sample data. Log in as Administrator: the **Set up Hipersign ERP** dialog asks *single company or group* and *which pack*.
For a demo site, then open **Hipersign Settings → Set-up → Load demo data** and type `DEMO` (it runs in the background and
sends a notification when done; the site switches to the Enterprise pack so every feature has data). The button is refused on a
site that already has submitted invoices, unless `hipersign_demo_site` is set in its site config. From the command line:

```bash
bench --site hipersign-demo.yourdomain.com set-config -p hipersign_demo_site true
bench --site hipersign-demo.yourdomain.com execute hipersign_trading.demo.load
bench --site hipersign-demo.yourdomain.com backup --with-files        # keep this as the "clean demo" backup
```

The command-line loader refuses to run unless `hipersign_demo_site` is set, so it can never write sample data into a live site.

**Separate sites per country plus a group site:** install the app on each country's site (single company) and on a group site
(*Group*). On the group site add a **Hipersign Group Member** for each country site with its URL, company name and an API key/secret of a
user with the Accounts Manager role on that site; **Sync all members** (or the daily job) brings their trial balances in for the
**Hipersign Group Consolidation** report.

**Uninstall:** `bench --site … uninstall-app hipersign_trading` saves a JSON copy of the app's own records in the site's private
files, removes the app's custom fields, property setters, workflows and roles, and leaves ERPNext's documents in place.

**Frappe Cloud:** add the GitHub repo as a custom app on your bench group, create a new site, install ERPNext +
this app, then run the loader from the site's console (`frappe.flags.hs_force_demo = True; from hipersign_trading.demo import load; load()`).

**Optional — HR & payroll:** install the Frappe HR app *before* the loader if you want leave, payroll and the WPS file:
`bench get-app hrms --branch version-15 && bench --site hipersign-demo.yourdomain.com install-app hrms`.
Everything else works without it.

**Serial numbers:** the loader makes items ITM-004/005/007/011/013 serialised (ERPNext numbers each unit and picks them
first-in-first-out on delivery). If your ERPNext version refuses, run
`bench --site … set-config -p hipersign_demo_no_serials true` and load again on a fresh site.

### Demo users
The loader creates users for every prototype role (no passwords, no emails sent):
`priya.menon@demo.hipersignerp.com` (Sales Executive), `omar.haddad@…` (Sales Manager), `fatima.alzaabi@…` (Purchase Manager),
`sara.alhashimi@…` (Finance Manager), `ahmed.hassan@…` (Warehouse Manager), `imran.sheikh@…` (Logistics), etc.
`lina.farah@…` (HR Manager) and `rashid.khan@…` (Driver — opens `/driver` on the phone).
Customer portal: `portal.gulftrading@demo.hipersignerp.com` (Gulf Trading LLC).
Log in as Administrator and use **Impersonate** on a user to test their screens and approvals.

### Reset the demo before a client meeting
```bash
bench --site hipersign-demo.yourdomain.com restore <clean-demo-backup>.sql.gz --with-public-files … --with-private-files …
```

## 2. Update the ERP when the prototype changes

1. Change the prototype.
2. Turn the change into an **ERPNext change list** (DocType / field / workflow / print format / page) — see `docs/CHANGE_PROCESS.md`.
3. Implement it in this app, bump `__version__` in `hipersign_trading/__init__.py`, commit, tag (e.g. `v1.2.0`).
4. Deploy to the demo site:
   ```bash
   cd ~/frappe-bench/apps/hipersign_trading && git pull
   cd ~/frappe-bench
   bench --site hipersign-demo.yourdomain.com migrate
   bench build --app hipersign_trading
   bench restart
   ```
   (Frappe Cloud: push to GitHub → **Deploy**.)
5. Re-run the Test Centre scripts on the demo site.
6. When signed off, back up the live site (`bench --site <live> backup --with-files`) and run the same update there.

If you change a field, workflow or print format **in the ERPNext screens**, save it into the app before the next deploy:
```bash
bench --site hipersign-demo.yourdomain.com export-fixtures --app hipersign_trading
```
(Custom fields must have **Module = Hipersign Trading** to be exported.)

### Upgrading an existing site from 1.4 to 1.5
`bench migrate` (or update the site on Press). The Hipersign menu is rebuilt on every migrate, so Home, Approvals, Insights &
Alerts, Messages and Trade Journey (Overview), Landed Cost & Margin (Purchasing) and Test Centre, Add-ons & Pricing (Admin)
appear by themselves. Demo sites: `bench --site <site> execute hipersign_trading.demo.load` again adds the sample conversations.

### Upgrading an existing site from 1.3 to 1.4
`bench migrate` (or deploy on Frappe Cloud / Press and update the site). Patch `v1_4.look_and_menus` switches the Hipersign theme,
the Hipersign ERP menu and desktop on; change any of it in Hipersign Settings → *Look & menus*. Users may need to reload the page
once (Ctrl/Cmd + Shift + R) to pick up the new look.

### Upgrading an existing site from 1.2 to 1.3
```bash
cd ~/frappe-bench
bench update --apps hipersign_trading --no-backup      # or: cd apps/hipersign_trading && git pull
bench --site hipersign-demo.yourdomain.com migrate      # new doctypes, rules, lists, workspace; set-up marked done
bench build --app hipersign_trading && bench restart
bench --site hipersign-demo.yourdomain.com execute hipersign_trading.demo.load   # demo sites only: adds the v1.3 sample data
```
An upgraded site keeps working as before: Enterprise pack, every feature on, document level Full, and post-dated cheques still
post only when they clear (tick *Post cheques when received / issued* in Hipersign Settings → Payments & pricing to change).
The setup wizard does not appear on upgraded sites.

### Upgrading an existing demo site from 1.1 to 1.2
```bash
cd ~/frappe-bench
bench update --apps hipersign_trading --no-backup      # or: cd apps/hipersign_trading && git pull
bench --site hipersign-demo.yourdomain.com migrate      # new doctypes, fields, report, cards, workspaces; settings get their defaults
bench build --app hipersign_trading && bench restart
bench --site hipersign-demo.yourdomain.com execute hipersign_trading.demo.load   # adds the v1.2 sample data only
```
The v1.2 loader adds two companies (an FZE and an Oman LLC) under a new group company and makes the demo company a member of
that group. Do **not** run the loader on a live site (it refuses unless `hipersign_demo_site` is set).

### Upgrading an existing demo site from 1.0 to 1.1
```bash
cd ~/frappe-bench
bench update --apps hipersign_trading --no-backup      # or: cd apps/hipersign_trading && git pull
bench --site hipersign-demo.yourdomain.com migrate      # adds the new doctype, fields, workspaces, translations
bench build --app hipersign_trading && bench restart
bench --site hipersign-demo.yourdomain.com execute hipersign_trading.demo.load   # adds the new sample data only
```
ERPNext cannot switch an item to serial numbers once it has stock, so on a site loaded with 1.0 the five items stay
un-serialised. For the full serial / warranty demo, create a fresh demo site and load it with 1.1.

## 3. Before installing on a live site
- The app installs **active workflows** on Purchase Order, Sales Order, Payment Entry and Stock Reconciliation. If the live
  site already has workflows on those documents, review them first (only one workflow per document can be active).
- Set the tax templates and thresholds in **Hipersign Settings**.
- Do **not** set `hipersign_demo_site` on a live site.
- v1.1 adds a *before submit* check on Sales / Purchase Invoices: **returns** (credit / debit notes) need a reason and
  the Sales / Purchase Manager (or Accounts Manager). Normal invoices are not affected.
- The `/driver` page and the portal pages only show data to logged-in users with the right role or customer link.

### New in 1.2 — check before a live install
- **Advance before delivery** blocks Delivery Notes and Pick Lists for orders whose payment terms include an *Advance* line until
  the advance is received. Only Payment Terms you tick as *Advance* are affected; switch the rule off in Hipersign Settings if needed.
- **KYC** blocks confirming a sales order when the customer's trade licence has expired or KYC is *Blocked* (internal customers excluded).
  Existing customers start as *Pending*, which does not block. Switch off in Hipersign Settings if needed.
- **Collections hold**: customers with an invoice overdue more than *Hold new orders after* days (default 60) need the Finance
  Manager on new orders (through the existing sales order approval). Set it to 0 to switch off.
- **Approving a VAT return locks the period** with an Accounting Period. Untick *Lock the period* in Hipersign Settings if you lock periods another way.

### New in 1.3 — check before a live install
- **Document rules** at level *Full* block some steps until the document is attached or an exception is approved — e.g. sales
  orders from AED 50,000 without the customer's LPO, purchase invoices without the supplier's invoice, journal entries from
  AED 10,000 without a supporting document, LC *Issued* without the bank's copy, shipment *Cleared* without the bill of entry.
  Review them in **Hipersign Document Rule** (or set the document level to *Recommended*, which only warns) before going live.
- **Post-dated cheques** post a journal entry when received / issued on new sites (cheques in hand / issued accounts are created on install).
- **Bank charges**: a difference above AED 100 or 2% of the invoices, whichever is lower (Hipersign Settings), needs the Accounts Manager.
- **Price lists** limit the item list on quotations, orders and invoices to items with a price; tick *All items* on the document to override.

## Requirements
Frappe 16 / ERPNext 16. 1.5 and 1.4 are tested on Frappe 16.29 / ERPNext 16.30 (the Hipersign servers) and on Frappe 16.53 / ERPNext 16.52,
Python 3.14. On Frappe releases after the sidebar rework (16.4x+) the theme works but the Hipersign menu is not created yet.
Frappe HR is optional. WhatsApp uses click-to-chat (wa.me) with an expiring PDF link; a WhatsApp Business API
provider can be plugged into `hipersign_trading/api/share.py` later.
