# Advanced Platform — Phase 5: persistence + familial risk

Two additions.

## 1. Enrolled users now persist (demo mode)

Previously, running with `--demo` kept users in memory, so anyone you enrolled
vanished on restart. The demo store now writes enrolled (non-seed) users to a
small JSON file (`advanced/meditech_users.json`, override with
`MEDITECH_USERS_FILE`) and reloads them on startup — including the password
hash, so they can log in after a restart. The three seed accounts
(admin / dr.sharma / rajan) are always recreated and are not duplicated.

Nothing to do — just run as usual:
```cmd
python run_api.py --demo
```
Enroll a doctor/patient as admin, restart the gateway, and they're still there.
(For full multi-table persistence — audit, etc. — Postgres mode, by dropping
`--demo`, remains available.)

## 2. Familial Risk Calculator

A genuine, transparent family-history risk tool — no fabricated ML, no genome
data required. It appears as a card in both the doctor and patient views:
choose a condition, tap the affected relatives, and get an animated risk gauge.

Two models, picked automatically by condition:

- **Liability-threshold model** (complex/polygenic: Type 2 Diabetes, Coronary
  Heart Disease, Hypertension, Breast/Colorectal Cancer, Alzheimer's). The
  Falconer–Reich quantitative-genetics method: disease liability is a continuous
  normal trait; those past a threshold are affected. From population prevalence
  K and heritability h², a relative of an affected proband has an upward-shifted
  liability giving recurrence risk
  `K_R = 1 − Φ((T − r·h²·a)/√(1 − (r·h²)²·a·(a−T)))`, with relatedness r = 0.5 /
  0.25 / 0.125 for first/second/third-degree. This reproduces published
  benchmarks — e.g. schizophrenia (K≈1%, h²≈0.8) gives ~8.7% first-degree
  recurrence vs the observed ~9–10%.
- **Mendelian** (single-gene: Huntington's = autosomal dominant; Cystic Fibrosis
  and Sickle Cell = autosomal recessive): exact transmission probabilities
  (affected parent + dominant ⇒ 50%; affected sibling + recessive ⇒ 25%).

Heritabilities are representative twin-study values (Polderman et al., Nat Genet
2015; Mucci et al., JAMA 2016 for cancers; Gatz et al., 2006 for Alzheimer's);
the model and references are returned with every result. The normal-distribution
math (Φ, Φ⁻¹ via Acklam's approximation) is implemented in pure Python — no
scipy dependency.

Endpoints:
- `GET  /api/familial-risk/conditions` — conditions + supported relations.
- `POST /api/familial-risk` — `{condition, relatives:[...]}` → estimated lifetime
  risk %, baseline, risk ratio, category (average/moderate/high), the
  per-relative factors, an explanation, and a disclaimer.

Every result carries a clear disclaimer that it is an educational estimate using
published relative-risk / inheritance models — **not** a validated clinical tool
or a substitute for genetic counselling. (This is deliberate: a "predict disease
from genetics" black box on synthetic data would be misleading; this is the
honest, defensible version and is exactly how genetic counsellors reason.)

## Tests

```cmd
python -m pytest tests\ -q
```
69 tests. Phase 5 adds the familial-risk engine (liability-threshold math
validated against the schizophrenia recurrence benchmark, degree attenuation,
risk ceiling, realistic first-degree ranges, Mendelian dominant/recessive
probabilities) — all pure and runnable without any services.
