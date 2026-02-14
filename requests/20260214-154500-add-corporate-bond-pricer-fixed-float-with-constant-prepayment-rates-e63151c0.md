

# Feature Request  
**Title:** Add Corporate Bond Pricer (Fixed/Float) with Constant Prepayment Rates  
**Requested by:** risk‑team  
**Date:** 2026‑02‑14  
**Area:** products  
**Priority:** medium  

## Problem  
The current product engine lacks support for corporate bonds with amortising structures and behavioural prepayments. Treasury, credit portfolio management, and ALM teams require accurate valuation and cashflow projection for fixed‑rate and floating‑rate company bonds, including structures with scheduled amortisation and optional constant prepayment rates. Without these capabilities, duration, spread risk, and earnings forecasts for the credit portfolio remain incomplete.

## Proposed Outcome  
Implement a corporate bond product supporting:  
- Fixed‑rate and floating‑rate couponing.  
- Multiple amortisation modes (bullet, amortising, custom schedules).  
- Constant prepayment rates applied to outstanding principal.  
- Deterministic scenario valuation under `DeterministicZeroCurve`.  
- Full unit test coverage for cashflow generation, amortisation logic, and prepayment behaviour.

## Required Features  

### 1. **Coupon Types**  
- **Fixed‑rate bonds:**  
  - Constant coupon rate over the life of the bond.  
- **Floating‑rate bonds:**  
  - Coupon = reference index (e.g., EURIBOR) + spread.  
  - Deterministic forward curve lookup for v1.  
  - Support for standard reset frequencies (quarterly, semi‑annual).

### 2. **Amortisation Modes**  
- **Bullet (full repayment at maturity):**  
  - No scheduled principal repayments until final date.  
- **Linear amortisation:**  
  - Equal principal repayments each period.  
- **Custom amortisation schedule:**  
  - User‑provided principal repayment dates and amounts.  
- **Interest‑only periods (optional):**  
  - Pure coupon payments until amortisation start.

### 3. **Constant Prepayment Rate (CPR‑style)**  
- Apply a constant prepayment rate to outstanding principal each period.  
- Prepayments reduce future interest and scheduled amortisation proportionally.  
- Prepayment rate can be expressed as:  
  - **Annual CPR**, converted to SMM (single‑month mortality), or  
  - **Direct periodic rate** (v1 supports both).  
- Prepayments occur before scheduled amortisation in each period.

### 4. **Cashflow Engine**  
- Generate interest, scheduled amortisation, and prepayment cashflows.  
- Support monthly, quarterly, semi‑annual, and annual frequencies.  
- Day count conventions: ACT/360, ACT/365, 30/360.  
- Floating‑rate reset logic:  
  - Reset at period start.  
  - Use deterministic forward curve for v1.

### 5. **Valuation**  
- PV computed under `DeterministicZeroCurve`.  
- Discount all cashflows (interest, scheduled amortisation, prepayments).  
- Support for clean and dirty price outputs.  
- Optional yield‑to‑maturity solver (v2).

### 6. **Configuration & Parameters**  
- Bond parameters: notional, coupon type, fixed rate or spread, index, start date, maturity, frequency, day count.  
- Amortisation parameters: mode, schedule, interest‑only periods.  
- Prepayment parameters: CPR or periodic rate.  
- Curve parameters: discount curve, forward curve (for floaters).

## Acceptance Criteria  
- [ ] Cashflow engine produces correct schedules for bullet, linear, and custom amortisation.  
- [ ] Fixed‑rate and floating‑rate coupon calculations match analytical benchmarks.  
- [ ] Constant prepayment rate reduces principal correctly and consistently across periods.  
- [ ] PV under `DeterministicZeroCurve` matches spreadsheet benchmarks for sample bonds.  
- [ ] Unit tests cover:  
  - [ ] Fixed and floating couponing.  
  - [ ] Bullet, amortising, and custom schedules.  
  - [ ] Bonds with and without prepayments.  
  - [ ] Edge cases (zero coupon, zero prepayment, very short maturities).  

## Notes  
- v1 assumes deterministic discounting and deterministic forward rates (no multi‑curve framework).  
- No credit risk, default modelling, or spread‑based valuation in this version.  
- Prepayment model is intentionally simple (constant rate) to support portfolio‑level stress testing.


## Implementation Progress (2026-02-14)

Completed in code:
- Added `CorporateBond` product supporting fixed/floating coupons.
- Added amortization modes: `bullet`, `linear`, and `custom`.
- Added constant prepayment support via `annual_cpr` or `periodic_prepayment_rate`.
- Added tests for couponing, amortization, and prepayment behavior.

Open:
- Spreadsheet benchmark parity checks for PV.
- Clean/dirty price split outputs (currently PV only).

## Implementation Progress (2026-02-14 update 3)

Completed in code:
- Added clean/dirty valuation outputs for corporate bonds via `valuation_breakdown(...)`.
- Added deterministic benchmark target file `data/benchmarks/deterministic_valuation_targets.json`.
- Added benchmark regression tests (`tests/test_benchmark_targets.py`) including corporate bond targets.

## Implementation Progress (2026-02-14 update 4)

Completed in code:
- Added YTM functionality to `CorporateBond`:
  - `price_from_yield(...)`
  - `yield_to_maturity(...)`
- Added tests for YTM round-trip and yield-price monotonicity.
- Added benchmark target and regression assertion for corporate bond YTM.

## Implementation Progress (2026-02-14 update 8)

Completed in code:
- Added corporate bond edge-case tests covering:
  - zero coupon + zero prepayment
  - very short maturity schedule behavior
- Added explicit German fixed-rate mortgage benchmark regression target and test.

Status impact:
- Advances acceptance coverage for edge cases and benchmark parity requirements.

## Implementation Progress (2026-02-14 update 9)

Completed in code:
- Added explicit edge-case tests for corporate bonds:
  - zero-coupon + zero-prepayment bullet case
  - very short maturity schedule case
  - custom amortization schedule application
- Extended benchmark regression coverage with additional deterministic references.

Status impact:
- Advances required acceptance coverage for edge cases and schedule correctness.

## Implementation Progress (2026-02-14 update 10)

Completed in code:
- Added default clean/dirty valuation breakdown method at base product interface level.
- Added additional corporate edge-case coverage and custom amortization schedule assertion tests.

Status impact:
- Advances required list item on clean/dirty PV outputs and edge-case unit coverage.

## Implementation Progress (2026-02-14 update 11)

Completed in code:
- Floating corporate bonds now support explicit separate forward curve input (`forward_model`) while discounting with base curve.
- Added dedicated test for forward/discount curve decoupling.

Status impact:
- Advances required feature for separate discount and forward curve parameters.
