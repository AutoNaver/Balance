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

### Run a simple valuation (example to be added)
```
python examples/run_pv.py
```

---


