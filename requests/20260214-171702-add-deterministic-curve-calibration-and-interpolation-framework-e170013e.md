# Feature Request

- Title: Add deterministic curve calibration and interpolation framework
- Requested by: unknown
- Date: 2026-02-14
- Area: models
- Priority: high

## Problem
The engine currently assumes prebuilt zero/forward curves. In production, market quotes must be converted into arbitrage-consistent curves with transparent interpolation choices.

## Proposed Outcome
Add a deterministic curve build module that:
- Calibrates discount curves from deposits, FRAs, and swaps (v1 can start with deposits + swaps)
- Supports pluggable interpolation/extrapolation policies (linear zero, log-DF, cubic options)
- Produces diagnostics (fit error, monotonic discount factors, negative forward checks)
- Emits reusable calibrated curve objects for valuation and risk modules

## Acceptance Criteria
- [ ] Calibration routines accept instrument quote sets and generate curves consumed by existing pricing APIs.
- [ ] Interpolation policy is configurable and test-covered.
- [ ] No-arbitrage sanity checks run automatically and fail with clear validation messages.
- [ ] Regression tests verify calibration against known benchmark term structures.

## Notes
- Keep calibration deterministic and dependency-light for reproducibility.
- Add sample market-data input files under `data/market/` for examples and tests.
