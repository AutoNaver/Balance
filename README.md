---

# **Balance Sheet PV & PVatRisk Engine**  
### *Python • NumPy • Hull–White Interest Rate Model*

This repository contains a modular valuation and risk engine for bank balance sheets. It computes:

- **Present Value (PV)** of all balance sheet items  
- **PV at Risk (PVatRisk)** across deterministic and stochastic interest rate scenarios  
- Using a **Hull–White one‑factor short‑rate model** for simulation and discounting  

The system is designed for **multiple agents** working in parallel on different modules (models, products, engine, IO, tests). The architecture emphasizes extensibility, reproducibility, and clean separation of responsibilities.

---

## **1. Features**

### **Interest Rate & Scenario Layer**
- Zero‑curve bootstrapping and discount factor generation  
- Hull–White model with parameters \(a\), \(\sigma\), and initial term structure  
- Monte‑Carlo short‑rate simulation using NumPy  
- Deterministic scenario sets (parallel shifts, twists, stress scenarios)  

### **Product Layer**
Supports heterogeneous balance sheet items via a shared interface:

- **Bonds**  
  - Fixed, floating, zero‑coupon  
- **Derivatives**  
  - Interest rate swaps (fixed–float, float–float)  
  - (Phase 2) Caps, floors, swaptions  
- **Non‑Maturing Deposits (NMDs)**  
  - Behavioral maturity models  
  - Repricing models  

Each product implements:
```python
get_cashflows(scenario, as_of_date)
present_value(scenario, as_of_date)
```

### **Valuation & Risk Engine**
- Full revaluation under each scenario  
- Portfolio aggregation by product, desk, or currency  
- PVatRisk at configurable confidence levels  
- Exportable results (CSV/JSON)  

### **Testing & Validation**
- Unit tests for each product and model  
- Integration tests for end‑to‑end valuation  
- Performance benchmarks for large portfolios  

---

## **2. Repository Structure**

```
.
├── README.md
├── config/               # Curves, model parameters, scenario configs
├── data/                 # Sample portfolios and market data
├── docs/                 # Model documentation, usage examples
├── src/
│   ├── engine/           # Valuation engine, scenario orchestration
│   ├── models/           # Hull–White model, curve objects
│   ├── products/         # Bonds, swaps, NMDs, etc.
│   ├── io/               # Input/output parsers
│   └── utils/            # Date utils, math helpers
└── tests/                # Unit & integration tests
```

---

## **3. Technology Stack**

- **Python 3.10+**  
- **NumPy** for vectorized math  
- **Optional:** Pandas for data handling (future)  
- **PyTest** for testing  

---

## **4. Agent Collaboration Guidelines**

This project is designed for **multiple agents** working concurrently. To avoid conflicts:

### **Branching Model**
- `main` → stable, production‑ready  
- `develop` → integration branch  
- Feature branches:  
  ```
  feature/<area>-<short-description>
  ```
  Example: `feature/model-hullwhite`

### **Agent Roles**
| Agent Type | Responsibilities |
|-----------|------------------|
| **Model Agent** | Hull–White model, curve objects, discounting APIs |
| **Product Agents** | Implement product pricing logic under model APIs |
| **Engine Agent** | Scenario generation, PV/PVatRisk aggregation |
| **IO Agent** | Input formats, config management, validation |
| **Testing/Docs Agent** | Tests, documentation, examples |

### **Rules**
- Each PR must address **one feature** only  
- All public interfaces must be documented  
- Tests must accompany new features  
- Breaking changes require discussion via issues  

---

## **5. Implementation Roadmap**

### **Phase 1 — Skeleton & Interfaces**
- Define base classes:
  - `Product`
  - `InterestRateModel`
  - `ScenarioGenerator`
  - `ValuationEngine`
- Implement deterministic curve model  
- Set up CI and testing framework  

### **Phase 2 — Hull–White & Basic Products**
- Implement Hull–White model (closed‑form ZCB + simulation)  
- Implement fixed‑rate bond pricer  
- Portfolio PV computation  

### **Phase 3 — PVatRisk & Scenario Engine**
- Monte‑Carlo scenario generation  
- PV distribution and PVatRisk  
- Reporting layer  

### **Phase 4 — Advanced Products & NMDs**
- Swaps, caps/floors  
- Behavioral NMD models  
- Extended reporting and calibration tools  

---

## **6. Example: Hull–White Zero‑Coupon Bond Pricing**

```python
import numpy as np

class HullWhiteModel:
    def __init__(self, a, sigma, curve):
        self.a = a
        self.sigma = sigma
        self.curve = curve

    def zcb_price(self, t, T):
        """Closed-form Hull–White zero-coupon bond price."""
        B = (1 - np.exp(-self.a * (T - t))) / self.a
        A = (
            self.curve.df(T) / self.curve.df(t)
            * np.exp(
                B * self.curve.fwd_rate(t)
                - 0.5 * self.sigma**2 * B**2 / (2 * self.a)
            )
        )
        return A * np.exp(-B * self.curve.short_rate(t))
```

(This is a simplified placeholder; the full implementation belongs in `/src/models/hullwhite.py`.)

---

## **7. Getting Started**

### Install dependencies
```
pip install numpy pytest
```

### Run tests
```
pytest
```

### Run a simple valuation
```
python examples/run_pv.py
```

---

## **8. Parallel Work Safety**

- See `docs/PARALLEL_AGENT_WORKFLOW.md` for collaboration rules that reduce merge conflicts.
- Prefer additive changes and unique filenames when adding data/docs/requests.

## **9. Feature Request Intake**

Use the in-repo request workflow:

```
python scripts/new_feature_request.py --title "Add floating rate bond"
```

This creates a uniquely named file under `requests/` so multiple agents can submit requests in parallel without editing the same file.



## **10. Current Implementation Status (2026-02-14)**

Implemented features:
- Deterministic zero-curve discounting (`DeterministicZeroCurve`)
- Hull-White one-factor model with closed-form ZCB pricing and short-rate path simulation (`HullWhiteModel`)
- Deterministic parallel-shift scenario generation and Hull-White Monte-Carlo scenario generation
- Products: `FixedRateBond`, `FixedFloatSwap` (vanilla fixed-float IRS)
- Engine exports: `ValuationResult.to_csv(...)` and `ValuationResult.to_json(...)`

Example run:
- `python examples/run_pv.py`
- Loads `data/portfolio/sample_mixed_portfolio.csv`
- Writes outputs to `data/results/`
- Added German fixed-rate mortgage support (`GermanFixedRateMortgageLoan`) with behavioural prepayments in `src/products/mortgage.py`.
- Added extended mixed portfolio sample including a mortgage row: `data/portfolio/sample_mixed_portfolio_extended.csv`.
- Added `CorporateBond` with fixed/floating coupons, amortization modes, and constant prepayment support (`src/products/corporate_bond.py`).
- Added derivatives v1 subset: `FXForward`, `FXSwap`, `EuropeanSwaption`, `CreditDefaultSwap` (`src/products/derivatives.py`).
- Added deterministic market helper curves for FX and hazard (`src/models/market.py`).
- Added derivatives example run: `python examples/run_derivatives.py`.
- Added float-float IRS support (`FloatFloatSwap`) and cross-currency swap support (`CrossCurrencySwap`).
- Added reusable mortgage integration layer (`src/products/mortgage_integration.py`) with pluggable prepayment models.
- Added optional external bridge to load `Zipper/main_mortgage.py`.
- Added cap/floor product (`InterestRateCapFloor`) and benchmark regression fixtures under `data/benchmarks/` with tests in `tests/test_benchmark_targets.py`.
- Added corporate bond YTM solver utilities and CCS mark-to-market option.
- Added deterministic stress scenarios (twists), expected-shortfall analytics, and per-product contribution reporting.
- Added grouped contribution analytics and multi-confidence risk profiles in valuation reporting.
- Added fuller MTM CCS reset-exchange mechanics and extended mortgage integration parity tests across repayment types.
- Added FX swap covered-interest-parity far-rate support, corporate edge-case tests, and German mortgage benchmark regression coverage.
- Added FX swap curve-implied forward-point support, CDS leg benchmark checks, and expanded corporate/mortgage benchmark-edge coverage.

## **11. Agent Git Operating Mode**

To avoid multi-agent conflicts, every agent must use a dedicated git worktree and feature branch.

Start a worktree:
```powershell
pwsh scripts/agent_worktree_start.ps1 -Agent agentA -Feature engine-twist-scenarios
```

Publish completed feature to `main` (fast-forward only):
```powershell
pwsh scripts/agent_publish_feature.ps1
```

Remove finished worktree:
```powershell
pwsh scripts/agent_worktree_finish.ps1 -WorktreePath "..\agent-worktrees\agentA\engine-twist-scenarios"
```

See `docs/PARALLEL_AGENT_WORKFLOW.md` for policy details.
- Added CDS leg-decomposition benchmarks, broken-date FX swap forward-point support, and expanded mortgage repayment-type benchmark regression tests.

Agent enforcement add-ons:
- Enable hooks once per clone: `pwsh scripts/enable_agent_hooks.ps1`
- One-command complete+publish: `pwsh scripts/agent_complete_feature.ps1 -CommitMessage "feat: ..."`
- Pre-push hook blocks pushes to refs other than `main`.
