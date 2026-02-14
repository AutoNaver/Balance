# Feature Request

- Title: Add risk sensitivities engine (DV01, CS01, FX Delta)
- Requested by: unknown
- Date: 2026-02-14
- Area: engine
- Priority: high

## Problem
Current valuation outputs provide PV and scenario risk summaries, but not standardized first-order sensitivities required by risk reporting and hedging workflows.

## Proposed Outcome
Implement a deterministic bump-and-revalue sensitivity engine that computes:
- IR DV01 by tenor bucket and aggregate portfolio DV01
- Credit spread CS01 for credit-sensitive products
- FX Delta for multi-currency products
- Product-level and portfolio-level decompositions
- Export of sensitivity tables to CSV/JSON alongside PV outputs

## Acceptance Criteria
- [ ] Valuation engine exposes an API to run configurable bumps (absolute/relative, one-sided/two-sided).
- [ ] Output includes per-product and aggregated DV01/CS01/FX Delta with consistent sign conventions.
- [ ] Sensitivities reconcile against finite-difference PV changes in regression tests.
- [ ] Unit and integration tests cover at least bonds, swaps, CDS, and FX products.

## Notes
- Start with deterministic curves only; stochastic-path Greeks can be a later phase.
- Keep bump configuration externalized via config files for governance/auditability.
