# THINKING_FIRST.md

## 1. The problem in my words
Supplier quotations arrive through different channels like email, WhatsApp, PDF and phone calls, and use inconsistent formats, units, currencies and tax treatments. Freight, payment terms, delivery time and validity also vary, while some details are missing or contradictory.

The director currently has to manually organize and analyze this information before comparing suppliers. This is tedious and important risks might get overlooked.

A useful tool should bring the information into one consistent comparison, calculate the total cost for the requirement, flag risks and missing information, and help the director make an informed decision with a clear recommendation and questions to ask suppliers before ordering. It should also have a clear main screen that the director can understand in about one minute.

---

## 2. What I see in the data

### Purchase Requisition:
1. Yeast Extract Powder, microbiology grade, 25 kg
2. Certificate of Analysis (CoA) mandatory
3. Need on site (USP Lab, Tamot plant (near Bhopal)) by 5 December 2026
4. Approved Budget: Rs 2,00,000
5. Note from lab head: Please don't go for unknown brands. Last time we had contamination issues with a cheap lot.

### Overall Observations after looking at data:
Quotations need to be compared using total cost for required quantity, not just the given rate. Delivery, CoA, Minimum Order Quantity, Brand Info, Payment terms and quote validity all need to be compared and considered.

Contradictory or missing details need to be shown as questions or risks rather than treating it as confirmed info.

---

## 3. One quote by hand (Quote A - Narmada Lab Supplies)

**Narmada Lab Supplies, Bhopal | Email**
- Brand: BioPure, Microbilogy grade, CoA provided with every batch
- Cost: Rs 3,850 per 500 g pack
- Required: 25 kg = 50 packs since 1 pack = 500 g
- GST @18% extra
- Freight/Delivery Cost: Rs 0 (since order value above Rs 50,000 threshold)
- Total Goods Cost (excl. GST): Rs 1,92,500
- Total Goods Cost (incl. GST): Rs 2,27,150
- Cost per kg (excl. GST): Rs 7,700 per kg
- Cost per kg (incl. GST): Rs 9,086 per kg
- Freight: Free Delivery to Tamot Plant
- Delivery: 3 working days from PO
- Payment: 30 days credit
- Validity: 30-Nov-2026
- Budget Variance: Rs 2,27,150 - Rs 2,00,000 = Rs 27,150 over budget (note: pre-GST cost of Rs 1,92,500 is within budget if StrainX claims GST input credit, though cash outflow is over Rs 2L).
- Concern: Cost is Rs 27,150 over budget and need to confirm delivery date and whether BioPure is a approved/known brand.

---

## 4. First view and plan

### Initial View:
Investigate the various quotations, first Quote D since after GST also total cost is Rs 1,60,125 before transport, which is within budget and the given delivery timeline also fits the required date.

But, I won't recommend going for it until the supplier confirms the brand, CoA with every batch, transport cost, delivery date and various other missing info.

Quote A has clear quality and payment terms, but over budget.

Quote B has expired and contradictory GST info.

Quote C has 50 kg MOQ and lead time that misses required date.

### What I plan to build:
1. A proper well structured requisition form for item, quantity, unit, need-by-date, budget and mandatory requirements.
2. A quote-entry section for multiple suppliers and their different pricing, tax, freight, and payment terms.
3. A analysis tool to compare total cost, cost per unit and other things.
4. Automatic risk flagging for expired quotations, delivery time, MOQ, missing CoA, payment, terms and budgets.
5. A recommendation with short reason in plain english and questions to ask suppliers.
6. A one screen summary, with options to print or share.