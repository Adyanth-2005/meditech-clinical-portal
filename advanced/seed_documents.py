"""
seed_documents.py — populate MinIO with extra patient documents (lab reports,
prescriptions, discharge summaries) so the buckets look full for a demo.

  python seed_documents.py                # seed for the core 8 patients
  python seed_documents.py --patients PT-001 PT-003 PT-007

Uses the same per-patient-prefix layout as the app: lab-exports/PT-xxx/,
prescriptions/PT-xxx/, discharge-reports/PT-xxx/. Safe to re-run (overwrites).
"""
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "api"))
import minio_store as M

random.seed(7)

CORE = [f"PT-00{i}" for i in range(1, 9)]

LAB_PANELS = [
    ("CBC", "Hemoglobin 13.2 g/dL; WBC 7.8 10^9/L; Platelets 240 10^9/L"),
    ("Renal", "Creatinine 1.1 mg/dL; eGFR 78 mL/min; Potassium 4.4 mEq/L"),
    ("Lipid", "Total chol 192 mg/dL; LDL 118 mg/dL; HDL 44 mg/dL; TG 160 mg/dL"),
    ("HbA1c", "HbA1c 7.6 % (elevated); fasting glucose 142 mg/dL"),
    ("LFT", "ALT 28 U/L; AST 24 U/L; Bilirubin 0.8 mg/dL"),
]
RX = [
    "Metformin 1000mg BD; Ramipril 2.5mg OD; review in 6 weeks.",
    "Atorvastatin 20mg HS; Aspirin 75mg OD; lifestyle advice given.",
    "Amlodipine 5mg OD; titrate per home BP log.",
    "Salbutamol inhaler PRN; Budesonide BD; spacer technique reviewed.",
    "Furosemide 40mg OD; daily weights; low-salt diet.",
]
DIAGS = ["T2DM + Hypertension", "Chronic Kidney Disease Stage 3", "Heart Failure (HFrEF)",
         "COPD with exacerbation", "Community-acquired pneumonia"]


def seed(pid: str):
    n = 0
    # 1–2 lab reports
    for _ in range(random.randint(1, 2)):
        name, body = random.choice(LAB_PANELS)
        key = M.build_key(pid, "lab", f"{name}_{random.randint(1000,9999)}.txt")
        M.put_text("lab-exports", key, f"LAB REPORT — {name}\nPatient {pid}\n\n{body}\n")
        n += 1
    # a prescription
    key = M.build_key(pid, "prescription", f"rx_{random.randint(1000,9999)}.txt")
    M.put_text("prescriptions", key, f"PRESCRIPTION\nPatient {pid}\n\n{random.choice(RX)}\n")
    n += 1
    # a discharge summary
    body = M.render_discharge({"patient_id": pid, "full_name": pid},
                              random.choice(DIAGS), random.choice(RX), "Review in 4 weeks.")
    M.put_text("discharge-reports", M.build_key(pid, "discharge"), body)
    n += 1
    return n


def main():
    pids = CORE
    if "--patients" in sys.argv:
        pids = sys.argv[sys.argv.index("--patients") + 1:]
    try:
        M._client().list_buckets()
    except Exception as e:
        print(f"✗ MinIO not reachable: {e}"); sys.exit(1)
    for b in ("lab-exports", "prescriptions", "discharge-reports"):
        M.ensure_bucket(b)
    total = sum(seed(p) for p in pids)
    print(f"✓ Seeded {total} documents across {len(pids)} patients "
          f"(lab-exports / prescriptions / discharge-reports).")


if __name__ == "__main__":
    main()
