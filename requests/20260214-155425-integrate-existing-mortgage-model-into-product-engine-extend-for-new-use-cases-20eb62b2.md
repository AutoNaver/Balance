# Feature Request  
**Title:** Integrate Existing Mortgage Model into Product Engine & Extend for New Use Cases  
**Requested by:** risk‑team  
**Date:** 2026‑02‑14  
**Area:** products  
**Priority:** high  

## Problem  
A mortgage model implementation already exists in the local codebase (`C:\Users\naver\OneDrive\Desktop\Zipper`). However, it is not yet integrated into the unified product engine and cannot be reused by other valuation modules. Treasury, ALM, and retail‑risk teams require consistent access to mortgage‑style amortisation, cashflow generation, and prepayment logic across multiple product types. Without integration, the model remains siloed, duplicated logic may emerge, and enhancements cannot be shared across products.

## Proposed Outcome  
Integrate the existing mortgage model into the central product framework and expose its amortisation, cashflow, and prepayment components as reusable modules. This enables other products (e.g., retail loans, structured notes, covered bond pools) to leverage the same logic. The integration should preserve the existing implementation while standardising interfaces, configuration, and scenario valuation.

## Required Features  

### 1. **Model Integration**
- Import the existing mortgage model from the local implementation directory.  
- Wrap core components (amortisation engine, interest calculation, prepayment logic) into reusable service classes.  
- Ensure compatibility with the product engine’s standard interfaces:  
  - `CashflowGenerator`  
  - `ScenarioValuation`  
  - `DeterministicZeroCurve`  

### 2. **Standardised Cashflow Engine**
- Expose the following capabilities from the existing model:  
  - Contractual interest calculation  
  - Scheduled amortisation  
  - Dynamic outstanding balance updates  
  - Prepayment adjustments  
- Ensure output matches the product engine’s cashflow schema.

### 3. **Prepayment Logic Reuse**
- Convert the existing prepayment logic into a pluggable module.  
- Support:  
  - Constant prepayment rates  
  - Behavioural prepayment extensions (future versions)  
- Allow other products to call the prepayment module without duplicating code.

### 4. **Configuration Layer**
- Add a configuration wrapper so mortgage parameters can be passed through the product engine:  
  - Notional  
  - Fixed rate  
  - Maturity  
  - Repayment type  
  - Frequency  
  - Prepayment rate  
- Ensure backward compatibility with the original implementation.

### 5. **Valuation Integration**
- Enable deterministic PV calculation using the existing discounting framework.  
- Ensure mortgage cashflows can be valued under:  
  - `DeterministicZeroCurve`  
  - Scenario‑based rate shocks (v2)

### 6. **Testing & Validation**
- Create unit tests verifying that the integrated model produces identical results to the standalone implementation.  
- Add regression tests for:  
  - Annuity repayment  
  - Constant repayment  
  - Interest‑only periods  
  - Prepayment scenarios  
- Validate PV outputs against benchmark spreadsheets.

## Acceptance Criteria  
- [ ] Existing mortgage model is callable through the unified product engine.  
- [ ] Cashflow outputs match the standalone implementation for all repayment types.  
- [ ] Prepayment logic is modular and reusable by other products.  
- [ ] PV under `DeterministicZeroCurve` matches benchmark values.  
- [ ] Unit tests cover integration, edge cases, and regression scenarios.


## Implementation Progress (2026-02-14)

Completed in code:
- Added reusable mortgage service layer in `src/products/mortgage_integration.py`:
  - `MortgageConfig`
  - `MortgageCashflowGenerator`
  - `IntegratedMortgageLoan`
  - pluggable prepayment models (`ConstantCPRPrepayment`, `BehaviouralPrepaymentAdapter`)
- Added optional bridge function `load_zipper_mortgage_module(...)` for loading `main_mortgage.py` from the external `Zipper` repository.
- Added loader support for new `integrated_mortgage` product rows.
- Added regression tests comparing integrated mortgage PV to existing mortgage product for common cases.

Open:
- Full parity harness against standalone `Zipper` production outputs (requires environment-specific dependencies and input files).

## Implementation Progress (2026-02-14 update 2)

Completed in code:
- Added deterministic benchmark targets and regression test coverage for integrated mortgage PV.
- Added direct integration test confirming local `Zipper/main_mortgage.py` module can be dynamically loaded when present.

Open:
- Full production parity run with Zipper-specific runtime pipeline and input sheets.

## Implementation Progress (2026-02-14 update 5)

Completed in code:
- Added stress scenario support (parallel + twist) in core engine scenario layer.
- Added deterministic expected shortfall reporting in valuation outputs.
- Added contribution breakdown to support risk decomposition across products.

## Implementation Progress (2026-02-14 update 6)

Completed in code:
- Added grouped product contribution reporting for deterministic stress scenarios.
- Added multi-confidence risk profile support to facilitate governance/risk reporting.

## Implementation Progress (2026-02-14 update 7)

Completed in code:
- Added stronger integration parity coverage for mortgage model:
  - cashflow + PV parity tests across repayment types (`annuity`, `constant_repayment`, `interest_only_then_amortizing`) between `GermanFixedRateMortgageLoan` and `IntegratedMortgageLoan`.
- Added standalone compatibility test confirming dynamic import of local `Zipper/main_mortgage.py` when present.

Status impact:
- Substantially improves coverage for "cashflow outputs match standalone implementation" and regression scope across repayment structures.

## Implementation Progress (2026-02-14 update 8)

Completed in code:
- Removed direct external bridge dependency from integrated mortgage tooling.
- Implemented clean-room behavioural prepayment model inside `src/products/mortgage_integration.py` (`CleanRoomBehaviouralPrepayment`).
- Updated integrated mortgage loader path to use the clean-room prepayment model for behavioural mode.
- Extended integration tests to verify clean-room behavioural parity vs existing mortgage product outputs.

Rationalization impact:
- Integrated mortgage path is now self-contained and reusable without dynamic imports from external repositories.

## Implementation Progress (2026-02-14 update 9)

Completed in code:
- Removed remaining external-model adapter hook from `mortgage_integration` to prevent direct foreign model reuse in the integrated path.
- Added `IntegratedGermanFixedRateMortgageLoan` as a migration-friendly replicated feature wrapper over clean-room components.
- Added loader support for `integrated_german_fixed_rate_mortgage`.
- Added parity and loader tests for the replicated integrated mortgage wrapper.

Rationalization impact:
- New-tool mortgage path is explicitly clean-room and self-contained while retaining old feature coverage through replicated behavior.

## Implementation Progress (2026-02-14 update 10)

Completed in code:
- Decoupled dashboard mortgage drill-down logic from legacy mortgage concrete class typing by using mortgage-like clean-room decomposition.
- Added dashboard adapter test coverage for `IntegratedGermanFixedRateMortgageLoan`.
- Added migration guide `docs/MORTGAGE_CLEANROOM_MIGRATION.md` documenting clean-room path and parameter mapping.

Rationalization impact:
- Clean-room mortgage path is now supported end-to-end (loader -> valuation -> analytics UI) without direct dependency on legacy mortgage internals.
