# Feature Request  
**Title:** Add Retail‑Bank Derivatives Suite (IRS, Swaptions, CDS, CCS, FX Swaps, etc.)  
**Requested by:** risk‑team  
**Date:** 2026‑02‑14  
**Area:** products  
**Priority:** medium  

## Problem  
The current product engine supports only a limited set of interest‑rate instruments. Retail and commercial banks typically hold a broad range of derivatives for hedging interest‑rate, FX, and credit exposures. Without support for these products, the risk engine cannot produce accurate PVs, sensitivities, or scenario‑based risk metrics for the bank’s trading and banking books. This limits ALM, treasury, and regulatory reporting capabilities.

## Proposed Outcome  
Implement a modular derivatives framework covering the most common retail‑bank instruments:  
- Interest Rate Swaps (IRS)  
- Swaptions  
- Credit Default Swaps (CDS)  
- Cross‑Currency Swaps (CCS)  
- FX Swaps  
- Simple FX Forwards  
- Optional extension: Caps/Floors (v2)  

All products should support deterministic scenario valuation under `DeterministicZeroCurve` and `DeterministicFXCurve` (where applicable), with full unit test coverage.

## Required Features  

### 1. **Interest Rate Swaps (IRS)**  
- Fixed‑float and float‑float structures.  
- Standard payment frequencies and day‑count conventions.  
- Support for single‑curve discounting (v1).  
- PV = discounted fixed leg − discounted floating leg.  
- Support for pay‑fixed and receive‑fixed.

### 2. **Swaptions (European, v1)**  
- Payer and receiver swaptions.  
- Underlying IRS defined via existing swap engine.  
- Deterministic valuation using:  
  - Black‑76 model (v1),  
  - Deterministic forward swap rate.  
- Exercise produces an IRS position.

### 3. **Credit Default Swaps (CDS)**  
- Standard running‑spread CDS.  
- Premium leg: periodic spread payments.  
- Protection leg: deterministic hazard‑rate curve (v1).  
- Support for:  
  - Recovery rate parameter,  
  - Standard maturities (1Y–10Y).  
- PV = PV(protection) − PV(premium).

### 4. **Cross‑Currency Swaps (CCS)**  
- Fixed‑float, float‑float, and fixed‑fixed structures.  
- Notional exchanges at start and maturity.  
- Couponing in two currencies with independent curves.  
- Deterministic FX curve for discounting and conversion.  
- Support for mark‑to‑market CCS (v2).

### 5. **FX Swaps**  
- Spot + forward legs.  
- Forward points derived from deterministic interest‑rate curves.  
- PV computed in base currency.  
- Support for broken‑date forwards (v2).

### 6. **FX Forwards**  
- Simple forward contract with deterministic forward FX rate.  
- PV = discounted forward payoff.

### 7. **Common Framework Requirements**  
- Unified cashflow engine for all legs (fixed, floating, FX, credit).  
- Deterministic scenario valuation:  
  - `DeterministicZeroCurve`  
  - `DeterministicForwardCurve`  
  - `DeterministicFXCurve`  
  - `DeterministicHazardCurve` (for CDS)  
- Modular leg definitions:  
  - Fixed leg  
  - Floating leg  
  - FX leg  
  - Credit premium leg  
  - Protection leg  
- Clean and dirty PV outputs.  
- Exposure‑ready cashflow outputs for future XVA integration.

## Acceptance Criteria  
- [ ] IRS PV matches analytical benchmarks for fixed‑float and float‑float cases.  
- [ ] Swaption PV matches Black‑76 reference values for sample strikes and maturities.  
- [ ] CDS premium and protection legs match deterministic hazard‑rate spreadsheet benchmarks.  
- [ ] CCS valuation correctly handles multi‑currency discounting and notional exchanges.  
- [ ] FX Swap and FX Forward PVs match deterministic forward‑rate calculations.  
- [ ] Unit tests cover:  
  - [ ] All product types and payoff structures.  
  - [ ] Edge cases (zero rates, zero spreads, short maturities).  
  - [ ] Pay/receive variants.  
  - [ ] Multi‑currency consistency checks.  

## Notes  
- v1 focuses on deterministic valuation; no stochastic models, no calibration, no volatility surfaces.  
- CSA/discounting frameworks, OIS curves, and multi‑curve bootstrapping are out of scope for v1.  
- The architecture should allow seamless extension to:  
  - Bermudan swaptions,  
  - Caps/floors,  
  - Inflation swaps,  
  - XVA engines.

---


## Implementation Progress (2026-02-14)

Completed in code (v1 subset):
- Added `FXForward`, `FXSwap`, `EuropeanSwaption` (Black-76), and `CreditDefaultSwap`.
- Added deterministic market helpers: `DeterministicFXCurve`, `DeterministicHazardCurve`.
- Extended scenario context (`Scenario.data`) so products can consume extra curves (`fx_curve`, `hazard_curve`).
- Added derivatives sample portfolio and runnable example (`examples/run_derivatives.py`).
- Added unit tests for all implemented derivative types.

Open:
- Cross-currency swaps (CCS).
- Float-float IRS variant.
- Full benchmark spreadsheet parity for every derivative class.

## Implementation Progress (2026-02-14 update 2)

Completed in code:
- Added `FloatFloatSwap` in `src/products/swap.py`.
- Added `CrossCurrencySwap` in `src/products/derivatives.py`.
- Extended loader support for `float_float_swap` and `ccs` product types.
- Added tests for float-float swap and CCS behavior.
- Updated derivatives sample portfolio and example to include new products.

Open:
- Benchmark spreadsheet parity for CCS/float-float variants.

## Implementation Progress (2026-02-14 update 3)

Completed in code:
- Added optional `InterestRateCapFloor` product (cap/floor) as practical extension.
- Added benchmark regression targets/tests for swap, float-float swap, CDS, and cap.
- Extended derivatives sample portfolio to include cap/floor.

Open:
- Cross-check against external spreadsheet references for production sign-off.

## Implementation Progress (2026-02-14 update 4)

Completed in code:
- Added mark-to-market mode for CCS via `mark_to_market` flag.
- Added tests validating MTM CCS produces different PV vs static-notional CCS.
- Added loader/data field support for `mark_to_market` in CSV portfolios.

Open:
- Dynamic notional-reset exchange cashflow mechanics (full operational MTM implementation) for advanced use cases.

## Implementation Progress (2026-02-14 update 5)

Completed in code:
- Added deterministic stress scenario generator with curve twists (`DeterministicStressScenarioGenerator`).
- Added risk analytics to valuation results:
  - expected shortfall
  - summary metrics
- Added per-scenario product contribution reporting (`value_with_contributions`).
- Updated `examples/run_pv.py` to report twist scenarios, expected shortfall, and top product contributors.

## Implementation Progress (2026-02-14 update 6)

Completed in code:
- Added grouped contribution analytics by product type in valuation engine.
- Added multi-confidence risk profile output (VaR + Expected Shortfall pairs).
- Updated `run_pv.py` to display grouped contributions and risk profiles.

## Implementation Progress (2026-02-14 update 7)

Completed in code:
- Implemented fuller MTM CCS notional-reset mechanics:
  - intermediate reset exchange cashflows added at reset dates
  - final notional exchange uses current reset notional
- Added tests for MTM CCS reset-flow behavior and PV differentiation.

Status impact:
- Advances the previously open item on dynamic notional-reset handling for MTM CCS.

## Implementation Progress (2026-02-14 update 8)

Completed in code:
- Added FX swap forward-point support from deterministic interest-rate curves when `far_rate` is omitted.
- Added tests validating covered-interest-parity implied far rate and missing-curve guards.

Status impact:
- Directly addresses required feature: "Forward points derived from deterministic interest-rate curves" for FX swaps.

## Implementation Progress (2026-02-14 update 9)

Completed in code:
- Added FX swap far-rate inference from deterministic domestic/foreign curves when `far_rate` is omitted.
- Added tests for covered-interest-parity forward-point behavior.
- Added benchmark regression references for swaptions and CDS leg decomposition (premium/protection legs).

Status impact:
- Directly advances required list items for FX swap forward-point logic and CDS/swaptions benchmark alignment.

## Implementation Progress (2026-02-14 update 10)

Completed in code:
- Added CDS leg decomposition API (`premium_leg_pv`, `protection_leg_pv`) and reconciliation tests.
- Added deterministic benchmark references for payer/receiver swaptions and CDS legs.
- Added broken-date FX swap forward-point support and tests for curve-implied far rates.

Status impact:
- Strengthens required-list alignment for swaptions/CDS benchmark validation and FX swap deterministic forward-point logic.

## Implementation Progress (2026-02-14 update 11)

Completed in code:
- Added explicit pay/receive symmetry tests for:
  - FX Forwards
  - FX Swaps
  - CCS (non-MTM)
- Added separate deterministic forward-curve support for floating corporate bond couponing (`forward_model`).

Status impact:
- Strengthens required acceptance coverage for pay/receive variants and deterministic forward-curve integration.
