# Feature Request

- Title: Add fixed-float swap pricer
- Requested by: risk-team
- Date: 2026-02-14
- Area: products
- Priority: high

## Problem
Current portfolio support is bond-only. Treasury and ALM desks need swap valuation to hedge duration and repricing gaps.

## Proposed Outcome
Implement a vanilla fixed-float interest rate swap product with deterministic scenario PV support and unit tests.

## Acceptance Criteria
- [x] Fixed and floating legs generate cashflows correctly for standard frequencies.
- [x] Swap PV can be computed under `DeterministicZeroCurve` scenarios.
- [x] Tests cover pay-fixed and receive-fixed cases.

## Notes
Initial version can assume single-curve discounting and no CSA adjustments.
