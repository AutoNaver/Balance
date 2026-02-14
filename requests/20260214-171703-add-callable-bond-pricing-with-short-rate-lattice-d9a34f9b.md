# Feature Request

- Title: Add callable bond pricing with short-rate lattice
- Requested by: unknown
- Date: 2026-02-14
- Area: products
- Priority: medium

## Problem
The engine prices non-callable bonds, but many bank holdings include callable structures whose embedded optionality materially affects PV, duration, and spread measures.

## Proposed Outcome
Implement a callable fixed-rate bond product with:
- Issuer call schedule support (Bermudan exercise dates)
- Hull-White short-rate lattice valuation (backward induction)
- Clean/dirty price outputs and option-adjusted spread (OAS) solver
- Exercise-boundary diagnostics for validation

## Acceptance Criteria
- [ ] Callable bond product supports standard schedule conventions and call protection periods.
- [ ] Lattice implementation reproduces non-callable bond price when callability is disabled.
- [ ] OAS solver converges for benchmark examples and is monotonic with price.
- [ ] Unit tests and benchmark tests cover at least one deep ITM call and one out-of-the-money case.

## Notes
- Reuse existing Hull-White model components where possible.
- Keep lattice implementation deterministic and configurable (time-step granularity).
