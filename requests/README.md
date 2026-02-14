# Feature Requests

Add new feature requests as individual markdown files in this folder.

Why individual files:
- Minimizes merge conflicts when many agents add requests in parallel.
- Makes review and triage easier.

## Quick Add

Run:

```bash
python scripts/new_feature_request.py --title "Add floating rate bond"
```

Optional fields:

```bash
python scripts/new_feature_request.py --title "Add swap pricer" --area products --priority high --details "Need fixed-float IRS PV under deterministic curve"
```

The script writes a uniquely named file like:
`requests/20260214-121530-add-swap-pricer-a1b2c3d4.md`
