# Feature Request

- Title: Add German Fixed‑Rate Mortgage Loan Pricer & Behavioural Prepayment Model
- Requested by: risk‑team
- Date: 2026-02-14
- Area: products
- Priority: medium

## Problem
The current product engine supports only bonds and simple swaps. Treasury, ALM, and retail‑risk teams require accurate valuation and cashflow projection for German fixed‑rate mortgage loans (“Festzinsdarlehen”). These loans exhibit heterogeneous repayment structures (annuity, constant‑repayment, interest‑only with later amortisation) and significant behavioural prepayment activity. Without these models, duration, convexity, and earnings forecasts for the retail book remain incomplete.

## Proposed Outcome
- upport for standard repayment types (annuity, constant‑repayment, interest‑only → amortising).
- Deterministic scenario valuation under DeterministicZeroCurve.
- A behavioural prepayment model driven by incentive, loan age, and seasonality.
- Full unit test coverage for cashflow generation, amortisation logic, and prepayment behaviour.

### 1. **Repayment Types**  
- **Annuity loans (Annuitätendarlehen):**  
  - Constant periodic payment; interest + amortisation split evolves over time.  
- **Constant‑repayment loans (Tilgungsdarlehen):**  
  - Fixed amortisation amount; declining interest portion.  
- **Interest‑only phase (optional):**  
  - Pure interest payments until amortisation start date.  

### 2. **Cashflow Engine**  
- Generate contractual cashflows for interest and principal.  
- Support monthly, quarterly, and annual payment frequencies (monthly is default).  
- Correct handling of German conventions:  
  - 30/360 or ACT/365 depending on product definition.  
  - Fixed‑rate couponing.  
- Amortisation schedule must update dynamically after prepayments.

### 3. **Behavioural Prepayment Model**  
A deterministic prepayment rate (CPR‑style or absolute amount) combining three drivers:

#### a) **Rate Incentive Component**  
- Incentive = client fixed rate − refinancing rate for remaining tenor.  
- Prepayment intensity increases monotonically with incentive.  
- Simple functional form (e.g., linear or logistic) acceptable for v1.

#### b) **Loan Age Component**  
- Prepayment increases linearly with loan age.  
- Zero at origination, max at contractual maturity.

#### c) **Seasonality Component**  
- Monthly dummy factors (12 values).  
- Higher prepayments in January/February and November/December (dummy values provided by risk).

Final prepayment rate = weighted combination of the three components.

### 4. **Valuation**  
- PV computed under `DeterministicZeroCurve` using discounted expected cashflows.  
- Prepayments reduce outstanding principal and future interest accordingly.  
- Support for both **lender PV** and **economic value PV** (optional for v1).

### 5. **Configuration & Parameters**  
- Loan contract parameters: notional, fixed rate, start date, maturity, repayment type, frequency.  
- Prepayment model parameters: incentive weights, age slope, monthly seasonal multipliers.  
- Optional caps/floors on prepayment rates.


## Acceptance Criteria
- [ ] Contractual cashflows match analytical schedules for all repayment types.  
- [ ] Prepayment model produces expected behaviour for incentive, age, and seasonality tests.  
- [ ] PV under `DeterministicZeroCurve` matches benchmark spreadsheets for sample loans.  
- [ ] Unit tests cover:  
  - [ ] Annuity, constant‑repayment, and interest‑only cases.  
  - [ ] Edge cases (zero incentive, zero age, extreme seasonality).  
  - [ ] Loans with and without prepayments.  

## Notes
- v1 assumes deterministic discounting and no credit risk, no embedded caps/floors, and no regulatory early‑repayment compensation (“Vorfälligkeitsentschädigung”).  
- Behavioural model should be modular to allow later calibration to historical data.


## Implementation Progress (2026-02-14)

Completed in code:
- Mortgage product with repayment types: annuity, constant_repayment, interest_only_then_amortizing
- Behavioural prepayment model with incentive, age, and monthly seasonality drivers
- Deterministic PV under `DeterministicZeroCurve`
- Unit tests for repayment schedules, prepayment behaviour, and with/without prepayments

Open:
- Spreadsheet benchmark parity checks for sample loans

## Implementation Progress (2026-02-14 update 8)

Completed in code:
- Added broader parity coverage and benchmark assertions for German mortgage valuation under deterministic curves.

Status impact:
- Strengthens evidence for acceptance criteria around deterministic PV benchmark alignment.

## Implementation Progress (2026-02-14 update 9)

Completed in code:
- Added explicit deterministic benchmark regression target for `GermanFixedRateMortgageLoan` with behavioural prepayment.
- Added regression assertion in benchmark suite.

Status impact:
- Advances acceptance criterion around deterministic benchmark parity for sample loans.

## Implementation Progress (2026-02-14 update 10)

Completed in code:
- Added deterministic benchmark regression targets/tests for additional repayment types:
  - `constant_repayment`
  - `interest_only_then_amortizing`

Status impact:
- Further advances acceptance coverage for repayment-type analytical schedule/PV consistency.
