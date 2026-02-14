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
