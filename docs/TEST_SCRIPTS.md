# Test scripts on the demo site (mirrors the prototype Test Centre)

| ID | Log in as | Steps | Expected |
|---|---|---|---|
| PUR-01 | Buyer | New Purchase Order for Global Supplies (USD) above AED 100,000 → Submit for Approval | Goes to Purchase Manager, then Finance Manager |
| IMP-01 | Logistics | Open the shipment *Under Customs Clearance* → Move to Cleared | Blocked until Bill of Entry and all documents are on file |
| IMP-02 | Storekeeper | Try a Purchase Receipt for the PO of a shipment not yet cleared | Blocked: "Goods can be received only after customs clearance" |
| LC-01 | Accountant | Cleared shipment → Landed cost voucher → Submit | Charges spread over received items; valuation rises |
| SAL-01 | Sales Executive | Sales Order for Al Noor at list rate → Submit | Approved directly (Contractor −5%) |
| SAL-02 | Sales Executive | Sales Order with a 15% discount → Submit for Approval | Pending Sales Manager |
| SAL-03 | Finance Manager | Approve the Elite Systems order | Credit check explained in *Approval reason*; order released |
| CRD-01 | Sales Executive | Raise a customer credit limit | Limit stays; Credit Limit Request pending Finance Manager |
| QTN-01 | Sales Executive | Quotation with items, a service and printed terms → Send → WhatsApp | Bilingual quotation; wa.me opens with an expiring PDF link |
| TRK-01 | Sales Manager | Sales Order Tracker → hover each stage → Reports → Statement of Account | Stage popups and party ledger |
| CRM-01 | Sales Executive | Lead → Log activity, move stage on Hipersign Lead Pipeline board | Stage, probability and next follow-up saved; ToDo created when due |
| EXP-01 | Sales Executive | Export Sales Order for Muscat Integrated Systems | Zero-rated export tax template; Proforma print |
| EXP-02 | Logistics | Export Shipment → Pack → export invoice → declaration → Shipped | Steps blocked until invoice, declaration, BL/CMR and CoO exist |
| EXP-03 | Accountant | Kenya shipment → tick LC documents → Documents Complete | Proof of export recorded; daily alert stops |
| DSH-01 | Managing Director | Hipersign Trading workspace | Gross and net profit cards, sales/purchases charts |
| HOME-01 | Accountant, Sales Manager, Warehouse Manager | Log in | Each lands on their own workspace with their own cards |
| RET-01 | Sales Executive | Sales Invoice → Create → Return / Credit Note, pick a reason → Submit | Blocked: "must be approved by the Sales Manager" |
| RET-02 | Sales Manager | Submit the pending Al Noor credit note → Print (Hipersign Tax Invoice) | Prints as **TAX CREDIT NOTE** with the original invoice and reason; outstanding falls |
| PDC-01 | Accountant | Post Dated Cheque 000418 (date reached) → Deposit → Cleared | Payment Entry (mode Cheque) created; Horizon's invoice outstanding falls |
| PDC-02 | Accountant | Cheque 553019 (deposited) → Bounced | Bank charges journal posted; customer's *Bounced cheques* +1; invoice stays open |
| PDC-03 | Accountant | Bounced cheque → Replacement cheque | New cheque in hand; old one marked Replaced |
| SER-01 | Warehouse Manager | Serial & Warranty Look-up → scan an ACR-… serial | Customer, delivery note and warranty end date shown |
| SER-02 | Warehouse Manager | Look-up → Register warranty claim → Resolution Replace + replacement serial | Claim saved with warranty status filled in |
| DRV-01 | Driver (phone) | `/driver` → open stop → tick items → sign → photo → Confirm | Delivery Note shows Delivered, receiver, signature, photo, GPS; print shows the signature |
| PRT-01 | Customer (portal user) | `/me` → Statement of account, Warranty, Invoices | Own ledger with cheques; own serialised units with warranty |
| HR-01 | HR Manager | Employee → UAE documents → set visa expiry in 30 days; run `bench execute hipersign_trading.tasks.employee_document_alerts` | ToDo for HR Manager |
| WPS-01 | HR Manager | Submitted Payroll Entry → Hipersign → WPS salary file (SIF) | .SIF file with EDR lines per employee and the SCR total line |
| BNK-01 | Accountant | Bank Statement Import → Bank Reconciliation Tool | Statement lines matched to payments |
| MST-07 | Sales Manager | Open item ITM-002, customer Al Noor LLC, supplier EuroSafe | Brand/model, Carton = 100 Nos, weight, minimum order, default supplier; territory, sales person, website; supplier lead time |
| ADV-01 | Warehouse Manager | Al Noor order **ANL/PO/7802** (50% advance terms) → Create → Delivery Note / Pick List → Submit | Blocked: "Advance before delivery … has not been received" |
| ADV-02 | Accountant | Same order → Create → Receive advance → Submit the Payment Entry; try the delivery again | Advance status *Received*; delivery allowed; on the invoice *Get advances* applies it |
| ADV-03 | Finance Manager | Future Build order **FB/PO/0951**; then order **FB/PO/0932** | FB/PO/0951: advance *Received*, stock reserved. FB/PO/0932: a draft Pick List (ERPNext 16 allows no pick list while stock is reserved) |
| COL-01 | Accountant | Gulf Projects invoice → Collection → Promise to pay; run `bench execute hipersign_trading.tasks.collection_reminders` | Promised invoices are skipped; other overdue invoices get their stage and a ToDo |
| COL-02 | Sales Executive | New Sales Order for **Horizon Trading** (invoice for HT-5101 is more than 60 days overdue) | *Approval needed: … collections hold* → goes to the Finance Manager |
| KYC-01 | Sales Manager | Approve the pending Gulf Projects order (GP-2026-344) | Blocked: trade licence expired / KYC blocked; drafts and quotations still allowed |
| KYC-02 | Sales Manager | Customer Gulf Projects → KYC: new expiry date next year, status Verified → approve the order again | Order confirmed |
| PUR-02 | Buyer | Request for Quotation from *Ceiling speakers restock* → Supplier Quotation Comparison | Both supplier offers side by side in AED with lead times |
| RO-01 | Buyer | Report **Hipersign Smart Reorder** → Create purchase orders | Suggestions rounded to cartons, not below minimum order, grouped by default supplier into draft POs |
| LC-02 | Accountant | Letter of Credit MSQ-ILC-26-1107 (accepted, usance 90) | Maturity date and trust receipt due/interest shown; Create → Trust receipt journal entry (draft) |
| LC-03 | Purchase Manager | Letter of Credit ENBD-ILC-26-0418 | Expiry warning on the form; ToDo from `letter_of_credit_alerts` |
| VAT-01 | Finance Manager | Tax Return for last month (Pending Finance Manager) → Approve & lock → Filed on EmaraTax (reference) → Record payment | Status Approved → Submitted → Paid; an Accounting Period now refuses invoices dated in that month |
| FX-01 | Finance Manager | Exchange Rate Revaluation (draft, last month end) → Submit → Make journal entries | Unrealised gain/loss on EUR/CNY balances; reversal journal on the 1st |
| GRP-01 | Finance Manager | Consolidated Financial Statement → company *Hipersign Demo Group* | LLC, FZE and Oman figures with the group total |
| GRP-02 | Accountant | Sales Invoice to *Hipersign Demo Trading FZE* → Create → Inter-company purchase invoice | Purchase invoice in the FZE's books linked to the sales invoice |
| SET-01 | Administrator (new site) | Log in → *Set up Hipersign ERP* → Single company, Starter → Finish | Menus for CRM, LCs, HR, assets hidden; approval workflows off; forms open in Quick mode |
| SET-02 | Administrator | Hipersign Settings → Pack → Enterprise, Group | Everything back; workflows on; nothing was deleted |
| SET-03 | Administrator (new site) | Hipersign Settings → Set-up → Load demo data → type DEMO | Notification *Hipersign demo data loaded* after a few minutes |
| FM-01 | Sales Executive | Quotations → **New · Quick** → customer, type `3 cam` + Enter → Save | Quotation saved with list price; opens the form |
| FM-02 | Sales Executive | Sales Orders → New · Quick → Gulf Trading LLC → *Repeat last order* → Submit order | Lines copied at today's prices; over AED 50,000 without LPO it is kept as a draft with the Documents box showing what is missing |
| FM-03 | Accountant | Sales Invoices → New · Quick → Create invoice on a delivery | Tax invoice created and submitted from the delivery note |
| FM-04 | Accountant | Payment Entries → New · Quick → customer, amount → Record receipt | One payment applied to the oldest invoices first |
| FM-05 | Any | Draft form → **Form mode** → Detailed / Standard | Rare fields shown / hidden; choice remembered |
| DOC-01 | Sales Executive | Draft sales order ≥ AED 50,000 → Submit | Blocked: *Document needed — Customer LPO* |
| DOC-02 | Sales Executive | Documents box → Request exception → reason, date → Send | Waiver pending; Sales Manager gets a ToDo |
| DOC-03 | Sales Manager | Document Waiver → Decide → Approve; Sales Executive submits the order | Order goes on; waiver *Used*; overdue alert if the LPO is not attached by the date |
| DOC-04 | Accountant | Report **Missing Documents** | Every record missing a required document, with level and exceptions |
| CMP-01 | Managing Director | Company Document *Establishment card* (expired) → Record renewal | New expiry; status Valid; reminders restart |
| CMP-02 | Accountant | Company Deadline *VAT return* → Mark done | Next month's deadline created |
| GRP-03 | Finance Manager | Report **Hipersign Group Consolidation** → Sync all members | Columns per company, eliminations, group total; balance sheet balances; Oman 30% minority shown |
| PDC-04 | Accountant (new site) | Post Dated Cheque received against an invoice | Journal entry: cheques in hand / customer; invoice outstanding falls at once; clearing moves it to the bank |
| PDC-05 | Accountant | Supplier invoice with an issued cheque → Payment Entry for the full amount | Blocked: only the remaining amount can be paid |
| BC-01 | Accountant | Customer paid AED 25 less → Payment Entry → *Book the difference as bank charges* | Invoice settled in full; above the limit only the Accounts Manager can save it |
| LC-04 | Accountant | Letter of Credit with margin → status Paid (date today) | Draft margin release journal created; a future paid date is refused |
| PL-01 | Sales Executive | Quotation for a Wholesale customer → item list | Only items in the Wholesale price list; tick *All items* to see the rest |
| LOOK-01 | Any user | Log in | Lands on Hipersign Home; navy Hipersign menu with the logo; prototype fonts and colours |
| LOOK-02 | Any user | Avatar menu → Toggle theme → Dark | Dark navy look as in the prototype's dark mode |
| LOOK-03 | Sales Executive (Arabic) | Language Arabic → Sales Orders | Right-to-left; menu on the right; Arabic menu labels |
| NAV-01 | Administrator | Open Sales Orders, then General Ledger, then Hipersign Settings | The Hipersign menu stays; the current page is highlighted |
| NAV-02 | Administrator | Desktop (logo → Desktop) | Only the Hipersign ERP tile; Hipersign Settings → Look & menus → untick *Show only Hipersign ERP* → the other tiles return |
| NAV-03 | Administrator | Hipersign Settings → Pack → Starter | LCs, imports, CRM disappear from the menu; Enterprise brings them back |
| HOM-01 | Managing Director | Hipersign Home → This month / Last month / Year to date; click a lifecycle stage and a KPI card | Group block, 7-stage lifecycle, work for today, priority alerts, KPI cards, P&L and the 12-month chart; every figure opens its records |
| HOM-02 | Sales Executive | Log in → Hipersign Home | Only the figures the user can open (no group block, P&L or purchase figures) |
| APR-01 | Sales Manager | Approvals → Only items I can approve → Approve the 15% discount order | The order moves to its next workflow state, exactly as from the form; KYC and credit rules still apply |
| APR-02 | Finance Manager | Approvals → VAT return → Approve | Return approved and locked; it leaves the queue |
| ALR-01 | Managing Director | Insights & Alerts → open the customs-documents alert → Mark actioned with a note | Alert moves to Actioned with the note; it stays actioned until the situation changes |
| ALR-02 | Warehouse Manager | Insights & Alerts | Only alerts on records the user may open (stock, slow-moving, shipments) |
| MSG-01 | Logistics | Messages → the shipment under customs clearance → reply with @Omar Haddad | Comment added on the shipment; Omar gets a mention notification; the thread shows on the shipment form too |
| TJ-01 | Purchase Manager | Trade Journey → pick the received import PO | Seven stages from supplier order to customer payment, each linked to its documents |
| LCM-01 | Finance Manager | Landed Cost & Margin → pick a shipment; Price helper → item, 25% | Goods + freight + duty + insurance = landed cost per unit; lowest price for the margin and the list-price margin |
| TST-01 | Any user | Test Centre → mark a test Pass with a note | Result, note, who and when kept on the site for everyone |
| ADD-01 | Sales Executive | Add-ons & Pricing → tick Automatic WhatsApp alerts → Print / PDF estimate | WhatsApp Business integration added automatically; hours, cost and third-party fees on a printable estimate |
