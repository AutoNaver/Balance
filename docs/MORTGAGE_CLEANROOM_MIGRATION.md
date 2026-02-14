# Mortgage Clean-Room Migration

This repo now supports a clean-room integrated mortgage path that replicates legacy behavior without directly importing external mortgage code.

## New primary integrated types

- `IntegratedGermanFixedRateMortgageLoan`
- `MortgageCashflowGenerator`
- `CleanRoomBehaviouralPrepayment`
- `ConstantCPRPrepayment`
- `MortgagePeriodBreakdown` (period-level schedule row)

## Loader product types

- Legacy: `german_fixed_rate_mortgage`
- Integrated service-style: `integrated_mortgage`
- Integrated replicated wrapper: `integrated_german_fixed_rate_mortgage`

## Parameter mapping

- `coupon_or_fixed_rate` -> `fixed_rate`
- `maturity_years` -> `maturity_years`
- `repayment_type` -> `repayment_type`
- `payment_frequency` -> `payment_frequency`
- `interest_only_years` -> `interest_only_years`
- `day_count` -> `day_count`
- `start_month` -> `start_month`
- behavioural prepayment config fields map 1:1 to `CleanRoomBehaviouralPrepayment`

## Rationale

- The integrated toolchain is self-contained in `src/products/mortgage_integration.py`.
- No dynamic import bridge to external mortgage repositories is used.
- Legacy mortgage implementation remains available for parity/regression tests and phased migration.

## Schedule API

- `IntegratedMortgageLoan.detailed_schedule(...)`
- `IntegratedGermanFixedRateMortgageLoan.detailed_schedule(...)`

Both return `MortgagePeriodBreakdown` rows with:
- period index and timing (`t0`, `t1`)
- beginning/ending outstanding balance
- interest cashflow, scheduled principal, prepayment, total cashflow
- CPR/SMM values used per period
