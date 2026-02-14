
# Feature Request  
**Title:** Add Interactive GUI/Dashboard for Cashflow Drill‑Down & Portfolio Insights  
**Requested by:** risk‑team  
**Date:** 2026‑02‑14  
**Area:** UI/Analytics  
**Priority:** high  

## Problem  
The current valuation engine produces detailed cashflows, amortisation schedules, and loan‑level characteristics, but these outputs are only accessible through logs, raw data structures, or developer tools. Risk, ALM, and Treasury teams need a user‑friendly interface to explore results, validate calculations, and analyse portfolios without relying on engineering support. Without a GUI, transparency is limited, onboarding is slower, and model validation becomes unnecessarily manual.

## Proposed Outcome  
Develop an interactive dashboard that visualises product‑level and portfolio‑level information, enabling users to:  
- Drill down into individual loan or instrument cashflows.  
- Inspect amortisation profiles, prepayment behaviour, and PV decomposition.  
- View aggregate portfolio characteristics (e.g., weighted average maturity, duration, coupon, prepayment rate).  
- Export or snapshot views for reporting and validation.  

The dashboard should integrate seamlessly with the existing product engine and scenario valuation framework.

## Required Features  

### 1. **Instrument‑Level Drill‑Down Views**  
- Detailed cashflow table:  
  - Interest, scheduled amortisation, prepayments, outstanding balance.  
- Visualisations:  
  - Cashflow timeline  
  - Outstanding balance curve  
  - Interest vs. principal split  
- Metadata panel showing:  
  - Notional, rate, maturity, repayment type, frequency  
  - Prepayment parameters  
  - Discount curve used  

### 2. **Portfolio‑Level Analytics**  
- Aggregated metrics:  
  - Total exposure  
  - Weighted average coupon  
  - Weighted average maturity  
  - Duration & convexity (if available)  
  - Prepayment‑adjusted cashflow projections  
- Portfolio‑level charts:  
  - Cashflow waterfall  
  - Maturity ladder  
  - Prepayment distribution  
- Ability to filter by:  
  - Product type  
  - Maturity bucket  
  - Currency  
  - Rating / risk segment (if available)

### 3. **Scenario Comparison Mode**  
- Compare base vs. shocked scenarios side‑by‑side.  
- Show differences in:  
  - PV  
  - Cashflows  
  - Prepayment amounts  
  - Duration metrics  
- Visual diff charts (e.g., delta cashflow bars).

### 4. **User Interaction & Navigation**  
- Search bar for instruments by ID or attributes.  
- Expand/collapse tree view for portfolios → sub‑portfolios → instruments.  
- Click‑through from portfolio metrics to individual instrument details.  
- Responsive layout for desktop screens.

### 5. **Data Integration Layer**  
- Connect to the existing product engine output:  
  - Cashflow objects  
  - PV results  
  - Scenario results  
  - Loan characteristics  
- Standardised API endpoints or data adapters.  
- Caching layer for large portfolios.

### 6. **Export & Reporting**  
- Export tables and charts to CSV/PNG.  
- Snapshot functionality for model validation documentation.  
- Optional: JSON export of full instrument drill‑down.

## Acceptance Criteria  
- [ ] Users can view detailed cashflows for any instrument in the portfolio.  
- [ ] Portfolio‑level metrics and charts load correctly for sample datasets.  
- [ ] Scenario comparison mode displays PV and cashflow deltas.  
- [ ] Navigation between portfolio → instrument → cashflow views is smooth and intuitive.  
- [ ] Export functions work for tables and charts.  
- [ ] Unit tests cover data adapters, UI components, and scenario comparison logic.

## Notes  
- v1 focuses on deterministic scenarios and existing product types (mortgages, bonds, swaps).  
- No editing of product parameters in the GUI (view‑only).  
- Future versions may include:  
  - Interactive scenario creation  
  - Stress testing dashboards  
  - XVA exposure visualisation  
  - Model calibration tools  

