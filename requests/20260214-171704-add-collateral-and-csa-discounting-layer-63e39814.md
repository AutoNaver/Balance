# Feature Request

- Title: Add collateral and CSA discounting layer
- Requested by: unknown
- Date: 2026-02-14
- Area: engine
- Priority: medium

## Problem
Current valuation assumes a single discounting setup. Secured derivatives valuation requires CSA-aware discounting, collateral remuneration, and netting-set level treatment.

## Proposed Outcome
Introduce a collateral/CSA layer that enables:
- Netting-set configuration and product-to-netting-set mapping
- CSA parameters (eligible collateral currency, remuneration rate, thresholds, MTA)
- OIS-style discount curve selection per collateral agreement
- Collateral-adjusted PV reporting alongside uncollateralized PV

## Acceptance Criteria
- [ ] Engine can value the same trade under unsecured vs CSA discounting and report both results.
- [ ] Netting-set aggregation is implemented and test-covered.
- [ ] CSA configuration is loadable from input files and validated.
- [ ] Integration tests demonstrate collateral impact on at least IRS and CCS sample portfolios.

## Notes
- Initial release can assume deterministic collateral balances (no margin period-of-risk simulation).
- Design should be extensible for future XVA and funding adjustments.


## Implementation Progress (2026-02-14 update 1)

Completed in code:
- Added deterministic CSA discounting module `engine.collateral` with:
  - `CSAConfig`
  - `CSAScenarioResult`
  - `CSADiscountingEngine`
- Implemented product-to-netting-set mapping and per-netting-set secured PV aggregation.
- Added side-by-side unsecured vs secured scenario valuation outputs.
- Added summary analytics for mean unsecured/secured PV and average collateral impact.
- Added unit tests validating:
  - secured and unsecured PV are both reported
  - netting-set aggregation output
  - summary metric structure.

Open:
- Input-loader wiring for CSA configuration files.
- Integration coverage using IRS/CCS portfolio files with externalized netting-set metadata.
- Optional collateral threshold/MTA cash-collateral balance dynamics beyond deterministic discount switching.


## Implementation Progress (2026-02-14 update 2)

Completed in code:
- Added CSA loader utilities in `src/io_layer/loaders.py`:
  - `load_product_netting_set_map_csv(...)`
  - `load_csa_configs_csv(...)`
- Added validations for:
  - missing/unknown `discount_model_key`
  - empty netting-set identifiers
- Added unit tests for CSA loader parsing and validation paths.

Status impact:
- Advances required feature item: "CSA configuration is loadable from input files and validated."
