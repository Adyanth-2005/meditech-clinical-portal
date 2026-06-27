"""
generate_mock_data.py — generate realistic synthetic patients and load them into
the lab's Elasticsearch EHR indices (ehr-patients / ehr-observations /
ehr-conditions), so the Kibana charts look full.

  python generate_mock_data.py                 # add 60 patients (PT-100xx)
  python generate_mock_data.py --count 150     # add 150
  python generate_mock_data.py --dry-run       # print sample, don't touch ES
  python generate_mock_data.py --reset         # delete generated (PT-1xxxx) then reload

The original 8 demo patients (PT-001..PT-008) are never touched — generated ids
start at PT-10001 so the two sets coexist. This writes only to Elasticsearch
(for the dashboards); the RAG/portal demo data is separate.
"""

import sys
import json
import random
import datetime as dt

import requests

ES = "http://localhost:9200"
SEED_START = 10001          # generated patient_id = PT-10001, PT-10002, ...
random.seed(42)

FIRST_M = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna",
           "Ishaan", "Rohan", "Karthik", "Ramesh", "Manoj", "Suresh", "Vikram", "Rajan"]
FIRST_F = ["Ananya", "Diya", "Saanvi", "Aadhya", "Pari", "Anika", "Navya", "Kavya",
           "Riya", "Meera", "Lakshmi", "Priya", "Deepa", "Nisha", "Sunita", "Geeta"]
LAST = ["Menon", "Nair", "Patel", "Iyer", "Krishnan", "Reddy", "Singh", "Das",
        "Sharma", "Rao", "Gupta", "Bose", "Pillai", "Shetty", "Hegde", "Kulkarni",
        "Banerjee", "Mukherjee", "Verma", "Naidu", "Bhat", "Kamath", "Pai"]
CITIES = ["Bangalore", "Mysuru", "Hubli", "Hyderabad", "Delhi", "Kolkata",
          "Chennai", "Pune", "Mumbai", "Kochi", "Mangaluru"]
BLOOD = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]

# department -> conditions [(name, icd10, chapter, desc)] and observation generators
def _obs(loinc, name, unit, lo, hi, hflag, lflag):
    """observation spec: value range [lo,hi]; flag thresholds."""
    return {"loinc": loinc, "name": name, "unit": unit, "lo": lo, "hi": hi,
            "hflag": hflag, "lflag": lflag}

DEPTS = {
    "Endocrinology": {
        "conditions": [("T2DM with Hyperglycaemia", "E11.65", "E"),
                       ("Essential Hypertension", "I10", "I")],
        "obs": [_obs("4548-4", "HbA1c", "%", 5.4, 11.0, 6.5, 4.0),
                _obs("2345-7", "Blood Glucose", "mg/dL", 90, 280, 140, 70),
                _obs("8480-6", "Systolic BP", "mmHg", 110, 180, 140, 90)],
    },
    "Cardiology": {
        "conditions": [("Heart Failure", "I50.9", "I"),
                       ("Atherosclerotic Heart Disease", "I25.10", "I"),
                       ("Essential Hypertension", "I10", "I")],
        "obs": [_obs("8806-2", "Echo EF", "%", 28, 62, 999, 40),
                _obs("30934-4", "BNP", "pg/mL", 40, 900, 100, -1),
                _obs("8867-4", "Heart Rate", "bpm", 55, 130, 100, 50),
                _obs("8480-6", "Systolic BP", "mmHg", 95, 175, 140, 100)],
    },
    "Nephrology": {
        "conditions": [("Chronic Kidney Disease Stage 3", "N18.3", "N"),
                       ("Essential Hypertension", "I10", "I")],
        "obs": [_obs("2160-0", "Creatinine", "mg/dL", 0.9, 4.0, 1.3, -1),
                _obs("33914-3", "eGFR", "mL/min", 20, 95, 999, 60),
                _obs("2823-3", "Potassium", "mEq/L", 3.6, 6.2, 5.0, 3.5)],
    },
    "Pulmonology": {
        "conditions": [("COPD with Acute Exacerbation", "J44.1", "J"),
                       ("Community-acquired Pneumonia", "J18.9", "J")],
        "obs": [_obs("2708-6", "SpO2", "%", 84, 99, 999, 94),
                _obs("9279-1", "Resp Rate", "/min", 12, 28, 20, -1),
                _obs("8310-5", "Body Temp", "C", 36.2, 39.6, 37.6, -1)],
    },
    "Orthopedics": {
        "conditions": [("Low Back Pain", "M54.5", "M"),
                       ("Osteoarthritis of Knee", "M17.9", "M")],
        "obs": [_obs("1988-5", "CRP", "mg/L", 1, 40, 10, -1)],
    },
    "General Medicine": {
        "conditions": [("Community-acquired Pneumonia", "J18.9", "J"),
                       ("Viral Fever", "B34.9", "B")],
        "obs": [_obs("8310-5", "Body Temp", "C", 36.4, 40.0, 37.6, -1),
                _obs("6690-2", "WBC", "10^9/L", 3.5, 18.0, 11.0, 4.0)],
    },
}
DEPT_WEIGHTS = [("Endocrinology", 0.22), ("Cardiology", 0.22), ("Nephrology", 0.16),
                ("Pulmonology", 0.16), ("General Medicine", 0.14), ("Orthopedics", 0.10)]


def _pick_dept():
    r = random.random(); c = 0
    for d, w in DEPT_WEIGHTS:
        c += w
        if r <= c:
            return d
    return DEPT_WEIGHTS[-1][0]


def _flag(value, spec):
    if spec["hflag"] != 999 and value >= spec["hflag"]:
        return "H"
    if spec["lflag"] != -1 and value <= spec["lflag"]:
        return "L"
    return "N"


def _rand_date(y0=2019, y1=2025):
    start = dt.date(y0, 1, 1)
    end = dt.date(y1, 6, 1)
    return (start + dt.timedelta(days=random.randint(0, (end - start).days))).isoformat()


def build_docs(n: int):
    patients, observations, conditions = [], [], []
    for i in range(n):
        pid = f"PT-{SEED_START + i}"
        dept = _pick_dept()
        gender = random.choice(["M", "F"])
        first = random.choice(FIRST_M if gender == "M" else FIRST_F)
        last = random.choice(LAST)
        name = f"{first} {last}"
        age = random.randint(28, 84)
        dob = dt.date(2025 - age, random.randint(1, 12), random.randint(1, 28)).isoformat()

        spec = DEPTS[dept]
        conds = random.sample(spec["conditions"], k=random.randint(1, len(spec["conditions"])))
        patients.append({
            "patient_id": pid, "mrn": f"MRN-{SEED_START + i}", "full_name": name,
            "dob": dob, "gender": gender, "blood_type": random.choice(BLOOD),
            "city": random.choice(CITIES), "age": age, "dept": dept,
            "conditions": [c[0].split(" with")[0].split(" of")[0] for c in conds],
        })
        for (desc, icd, chap) in conds:
            conditions.append({
                "patient_id": pid, "patient_name": name, "icd10": icd,
                "description": desc, "icd10_chapter": chap,
                "status": random.choice(["active", "chronic", "resolved"]),
                "onset": _rand_date(),
            })
        # 2–4 observations, drawn so chronic patients trend abnormal
        n_obs_specs = len(spec["obs"])
        lo_k = 1 if n_obs_specs < 2 else 2
        chosen = random.sample(spec["obs"], k=random.randint(lo_k, n_obs_specs))
        for ospec in chosen:
            for _ in range(random.randint(1, 2)):   # a couple over time
                val = round(random.uniform(ospec["lo"], ospec["hi"]), 1)
                observations.append({
                    "patient_id": pid, "patient_name": name, "loinc": ospec["loinc"],
                    "display_name": ospec["name"], "value": val, "unit": ospec["unit"],
                    "flag": _flag(val, ospec), "obs_date": _rand_date(), "dept": dept,
                })
    return patients, observations, conditions


def _bulk(index, docs):
    lines = []
    for d in docs:
        lines.append(json.dumps({"index": {"_index": index}}))
        lines.append(json.dumps(d))
    body = "\n".join(lines) + "\n"
    r = requests.post(f"{ES}/_bulk", data=body,
                      headers={"Content-Type": "application/x-ndjson"}, timeout=60)
    r.raise_for_status()
    errs = r.json().get("errors")
    print(f"  {'!' if errs else '✓'} {index}: loaded {len(docs)} docs"
          + (" (with errors)" if errs else ""))


def reset_generated():
    q = {"query": {"prefix": {"patient_id": "PT-1"}}}
    for idx in ("ehr-patients", "ehr-observations", "ehr-conditions"):
        try:
            requests.post(f"{ES}/{idx}/_delete_by_query", json=q, timeout=60)
        except Exception:
            pass
    print("  ✓ removed previously generated PT-1xxxx docs")


def main():
    n = 60
    if "--count" in sys.argv:
        n = int(sys.argv[sys.argv.index("--count") + 1])

    patients, observations, conditions = build_docs(n)
    print(f"Generated {len(patients)} patients, {len(observations)} observations, "
          f"{len(conditions)} conditions")
    flags = {}
    for o in observations:
        flags[o["flag"]] = flags.get(o["flag"], 0) + 1
    print("  observation flags:", flags)
    print("  sample patient:", json.dumps(patients[0]))
    print("  sample obs:    ", json.dumps(observations[0]))

    if "--dry-run" in sys.argv:
        print("\n(dry run — nothing loaded)"); return

    try:
        requests.get(f"{ES}", timeout=5)
    except Exception:
        print(f"\n✗ Elasticsearch not reachable at {ES}. Start the lab stack first."); sys.exit(1)

    if "--reset" in sys.argv:
        reset_generated()

    print("\nLoading into Elasticsearch…")
    _bulk("ehr-patients", patients)
    _bulk("ehr-observations", observations)
    _bulk("ehr-conditions", conditions)
    for idx in ("ehr-patients", "ehr-observations", "ehr-conditions"):
        requests.post(f"{ES}/{idx}/_refresh", timeout=30)
    print("\n✓ Done. In Kibana set the time range to Last 10 years and refresh your charts.")


if __name__ == "__main__":
    main()
