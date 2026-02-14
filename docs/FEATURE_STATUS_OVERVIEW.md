# Feature Implementation Overview (Continuously Updated)

This document provides a high-level view of requested features and current delivery status.

**Update policy:**
- Update this file whenever a feature request is added, materially advanced, paused, or completed.
- Keep statuses aligned with each request file in `requests/` (especially its latest `Implementation Progress` section).
- If acceptance checkboxes are not yet maintained in a request file, use the latest implementation notes as the source of truth and mention known open items explicitly.

**Status legend:**
- `Planned` — Request created, implementation not started.
- `In Progress` — Some deliverables implemented; open items remain.
- `Completed` — Acceptance intent delivered for current scope (or v1 scope) with tests.
- `Blocked` — Cannot proceed due to external dependencies.

## Portfolio View

| Feature | Request File | Area | Status | High-Level Notes |
|---|---|---|---|---|
| Fixed-float swap pricer demo | `20260214-120000-add-fixed-float-swap-pricer-demo.md` | products | **Completed** | Core fixed-float swap and tests were delivered; acceptance items are checked in request file. |
| German fixed-rate mortgage with behavioural prepayment | `20260214-153429-add-german-fixed-rate-mortgage-loan-pricer-behavioural-prepayment-model-c9f2b41e.md` | products | **In Progress** | Mortgage product, prepayment model, and benchmark-style tests were added; external spreadsheet parity/sign-off remains open. |
| Corporate bond pricer (fixed/float + prepayment) | `20260214-154500-add-corporate-bond-pricer-fixed-float-with-constant-prepayment-rates-e63151c0.md` | products | **In Progress** | Product, amortization modes, prepayment, clean/dirty, YTM, and edge-case tests exist; some benchmark parity/sign-off notes remain open. |
| Retail-bank derivatives suite (IRS, swaptions, CDS, CCS, FX) | `20260214-154935-add-retail-bank-derivatives-suite-irs-swaptions-cds-ccs-fx-swaps-etc-1ccb229f.md` | products | **In Progress** | Major v1 subset implemented (FX, swaptions, CDS, float-float swap, CCS incl. MTM/reset logic, leg decomposition); external benchmark sign-off still open. |
| Integrate existing mortgage model into product engine | `20260214-155425-integrate-existing-mortgage-model-into-product-engine-extend-for-new-use-cases-20eb62b2.md` | products | **In Progress** | Integration layer and parity tests were added; full production parity run with external runtime/pipelines remains open. |
| Risk sensitivities engine (DV01, CS01, FX Delta) | `20260214-171701-add-risk-sensitivities-engine-dv01-cs01-fx-delta-184e81cb.md` | engine | **In Progress** | Deterministic bump-and-revalue engine and initial unit tests are in place; config-driven bumps/export and broader integration coverage remain open. |
| Deterministic curve calibration/interpolation framework | `20260214-171702-add-deterministic-curve-calibration-and-interpolation-framework-e170013e.md` | models | **Planned** | New high-priority request; no implementation progress updates yet. |
| Callable bond pricing with short-rate lattice | `20260214-171703-add-callable-bond-pricing-with-short-rate-lattice-d9a34f9b.md` | products | **Planned** | New request; no implementation progress updates yet. |
| Collateral and CSA discounting layer | `20260214-171704-add-collateral-and-csa-discounting-layer-63e39814.md` | engine | **Planned** | New request; no implementation progress updates yet. |

## Next Prioritized Build Sequence

1. **Risk sensitivities engine (DV01/CS01/FX Delta)**
   - Unlocks hedging/risk reporting value across already-implemented products.
2. **Deterministic curve calibration/interpolation**
   - Strengthens market-data realism and improves valuation/risk consistency.
3. **Collateral & CSA discounting**
   - Adds secured valuation realism for derivatives books.
4. **Callable bond lattice pricing**
   - Expands product complexity once calibration/sensitivity foundations mature.

## Maintenance Checklist (Per Feature Update)

When any feature changes status:
1. Update the feature's request file (`requests/*.md`) with a new `Implementation Progress` entry.
2. Update the status row in this overview.
3. If scope changed materially, add/adjust acceptance criteria in the request file.
4. Keep terminology consistent (`Planned`, `In Progress`, `Completed`, `Blocked`).
