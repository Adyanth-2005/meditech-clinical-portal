"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║   MODULE 2 — Clinical Data Models & EHR Systems                                ║
║   Hands-On Lab Exercise                                                        ║
║   Medical Informatics · UE26MT324 · PES University                             ║
╚══════════════════════════════════════════════════════════════════════════════════╝

OVERVIEW
--------
Three self-contained exercises covering the core topics in Module 2:
  Exercise 1 — Structured vs Unstructured Data (NLP Classification)
  Exercise 2 — EHR Data Schemas & Longitudinal Records (SQLite)
  Exercise 3 — Clinical Coding: ICD-10 & SNOMED CT

HOW TO RUN
----------
  python module2_hands_on_exercise.py             # run all exercises
  python module2_hands_on_exercise.py --ex 1      # run one exercise only

DEPENDENCIES
------------
  pip install pandas tabulate colorama

INSTRUCTOR NOTES
----------------
- Each exercise has clearly marked TODO blocks for students.
- The DEMO blocks run automatically; students only edit inside TODO markers.
- Expected outputs are shown as comments where space allows.
- Timing: ~40 min total (≈13 min per exercise).
- Debrief prompts are printed at the end of each exercise.
"""

import sys
import re
import sqlite3
import json
import textwrap
from datetime import datetime, timedelta
import random

try:
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False
    print("[WARN] pandas not installed — some display steps will be skipped.")

try:
    from tabulate import tabulate
    TABULATE_OK = True
except ImportError:
    TABULATE_OK = False

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    GREEN  = Fore.GREEN
    YELLOW = Fore.YELLOW
    CYAN   = Fore.CYAN
    RED    = Fore.RED
    RESET  = Style.RESET_ALL
    BOLD   = Style.BRIGHT
except ImportError:
    GREEN = YELLOW = CYAN = RED = RESET = BOLD = ""


# ─── Utility helpers ─────────────────────────────────────────────────────────

def banner(title, color=CYAN):
    width = 72
    print(f"\n{color}{BOLD}{'═' * width}")
    print(f"  {title}")
    print(f"{'═' * width}{RESET}\n")

def section(title, color=YELLOW):
    print(f"\n{color}{BOLD}── {title} {'─' * (65 - len(title))}{RESET}")

def success(msg):   print(f"{GREEN}  ✓ {msg}{RESET}")
def warn(msg):      print(f"{YELLOW}  ⚠ {msg}{RESET}")
def info(msg):      print(f"{CYAN}  ℹ {msg}{RESET}")
def question(msg):  print(f"\n{RED}{BOLD}  ❓ DEBRIEF: {msg}{RESET}")

def separator(): print(f"\n{'─' * 72}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# EXERCISE 1 — Structured vs Unstructured Clinical Data
# ═══════════════════════════════════════════════════════════════════════════════

def exercise_1():
    banner("EXERCISE 1 — Structured vs Unstructured Clinical Data", CYAN)
    print(textwrap.dedent("""
    Scenario: You are a medical informatics engineer at Bangalore City Hospital.
    The EHR team has dumped all patient data into a single text file.
    Your job: classify data elements and extract structured facts from notes.
    """))

    # ── DEMO: Pre-classified structured data ─────────────────────────────────
    section("DEMO — Structured Data (already in rows and columns)")

    structured_data = [
        {"field": "patient_id",     "value": "PT-2024-001",    "type": "identifier"},
        {"field": "age",            "value": "54",             "type": "numeric"},
        {"field": "gender",         "value": "Male",           "type": "categorical"},
        {"field": "blood_glucose",  "value": "182 mg/dL",      "type": "measurement"},
        {"field": "bp_systolic",    "value": "148",            "type": "numeric"},
        {"field": "bp_diastolic",   "value": "92",             "type": "numeric"},
        {"field": "icd10_code",     "value": "E11.65",         "type": "code"},
        {"field": "hba1c",          "value": "8.9%",           "type": "measurement"},
        {"field": "medication",     "value": "Metformin 500mg","type": "order"},
    ]

    print("  Structured fields from EHR database:")
    for row in structured_data:
        flag = "  [code]" if row["type"] == "code" else ""
        print(f"    {GREEN}{row['field']:20}{RESET} = {row['value']:25} [{row['type']}]{flag}")

    # ── DEMO: A realistic clinical note ──────────────────────────────────────
    section("DEMO — Raw Clinical Discharge Note (Unstructured)")

    discharge_note = """
    DISCHARGE SUMMARY — Bangalore City Hospital
    Patient: Rajan Menon, 54M   |  MRN: PT-2024-001   |  Date: 2024-06-03
    Attending: Dr. Priya Sharma, MD Endocrinology

    PRESENTING COMPLAINT:
    Patient presented with a 4-day history of polydipsia, polyuria, and blurred
    vision. He also reported fatigue and mild lower-limb tingling over 3 weeks.
    Known case of Type 2 Diabetes Mellitus, poorly controlled.

    EXAMINATION:
    BP: 148/92 mmHg. HR: 88 bpm. SpO2: 98% on room air. Weight: 84 kg.
    Bilateral pedal oedema (1+). Fundoscopy shows early background retinopathy.

    INVESTIGATIONS:
    Fasting glucose: 182 mg/dL (ref: 70–99). HbA1c: 8.9% (ref: <5.7%).
    Urine microalbumin: 42 mg/g creatinine (borderline elevated).
    CBC: WBC 7.8, Hb 13.2, platelets 215K — all within normal limits.
    Creatinine: 1.1 mg/dL. eGFR: 68 mL/min/1.73m² (G2 — mildly decreased).

    ASSESSMENT & PLAN:
    1. Type 2 Diabetes Mellitus (E11.65) — hyperglycaemia with hyperlipidaemia.
       Increased Metformin to 1000mg BD. Added Glipizide 5mg OD.
    2. Diabetic nephropathy — early stage (N08). Monitor eGFR quarterly.
    3. Hypertension (I10): continue Amlodipine 5mg OD, add Ramipril 2.5mg.

    FOLLOW-UP: 4 weeks with Dr. Sharma. Repeat HbA1c in 3 months.
    DIET: Low glycaemic index diet. Avoid processed foods and refined sugar.
    """

    print(discharge_note)

    # ── DEMO: Pattern-based extraction ───────────────────────────────────────
    section("DEMO — Regex Extraction from Unstructured Text")

    patterns = {
        "Blood Pressure":  r"BP[:\s]+(\d{2,3}/\d{2,3})\s*mmHg",
        "Heart Rate":      r"HR[:\s]+(\d{2,3})\s*bpm",
        "Weight (kg)":     r"Weight[:\s]+(\d{2,3})\s*kg",
        "Blood Glucose":   r"glucose[:\s]+(\d{3})\s*mg/dL",
        "HbA1c":           r"HbA1c[:\s]+([\d.]+%)",
        "ICD-10 codes":    r"\(([A-Z]\d{2}(?:\.\d{1,3})?)\)",
        "Creatinine":      r"Creatinine[:\s]+([\d.]+)\s*mg/dL",
    }

    print("  Extracted values using regex patterns:\n")
    extracted = {}
    for label, pattern in patterns.items():
        hits = re.findall(pattern, discharge_note, re.IGNORECASE)
        extracted[label] = hits
        if hits:
            success(f"{label:20} → {', '.join(hits)}")
        else:
            warn(f"{label:20} → not found")

    # ── TODO BLOCK 1 ─────────────────────────────────────────────────────────
    section("TODO 1A — Extend the Extractor", RED)
    print(r"""
  The extractor misses several values in the note. Add regex patterns to
  capture the following:

      • SpO2 percentage          (hint: SpO2:\s+...)
      • eGFR value               (hint: eGFR:\s+...)
      • Platelet count           (hint: platelets\s+(\d+)K)
      • Microalbumin level       (hint: microalbumin:\s+...)

  Edit the dict below and run the cell again to verify.
    """)

    # ── Students fill this in ──────────────────────────────────────────────
    extra_patterns = {
        # TODO: add your patterns here
        # "SpO2":         r"...",
        # "eGFR":         r"...",
        # "Platelets":    r"...",
        # "Microalbumin": r"...",
    }
    # ── End student section ────────────────────────────────────────────────

    print("  Your extra patterns captured:")
    for label, pattern in extra_patterns.items():
        hits = re.findall(pattern, discharge_note, re.IGNORECASE)
        if hits:
            success(f"  {label:20} → {', '.join(hits)}")
        else:
            warn(f"  {label:20} → no match (check your pattern)")

    # ── TODO BLOCK 2 ─────────────────────────────────────────────────────────
    section("TODO 1B — Token Classifier", RED)
    print("""
  Complete the function classify_token() below.
  It receives a text snippet and should return one of:
      "structured"   — if it looks like a measurement, code, or numeric value
      "unstructured" — if it is free narrative text
      "mixed"        — if it contains both (e.g. "BP: 148/92 mmHg")

  Test tokens are provided — your function will be called on each.
    """)

    def classify_token(token: str) -> str:
        """
        TODO: Classify the token as 'structured', 'unstructured', or 'mixed'.

        Hints:
          - Structured tokens often contain digits, units (mmHg, mg, %), or codes
          - Unstructured tokens are mostly alphabetic words / sentences
          - Mixed tokens have both
          - Use re.search() to check for numeric patterns
          - Use len(token.split()) > 4 as a heuristic for narrative text
        """
        # ── Replace 'pass' with your implementation ────────────────────────
        pass
        # ── End student section ────────────────────────────────────────────

    test_tokens = [
        "BP: 148/92 mmHg",
        "Patient presented with a 4-day history of polydipsia and polyuria.",
        "HbA1c: 8.9%",
        "E11.65",
        "Bilateral pedal oedema (1+). Fundoscopy shows early retinopathy.",
        "WBC 7.8, Hb 13.2, platelets 215K",
        "Low glycaemic index diet. Avoid processed foods and refined sugar.",
        "eGFR: 68 mL/min",
    ]

    print("  Classification results:")
    correct_answers = ["mixed","unstructured","structured","structured",
                       "unstructured","structured","unstructured","structured"]
    for i, (tok, expected) in enumerate(zip(test_tokens, correct_answers)):
        result = classify_token(tok)
        short = tok[:55] + "…" if len(tok) > 55 else tok
        if result is None:
            warn(f"  [{i+1}] {short!r:60} → NOT IMPLEMENTED YET")
        elif result == expected:
            success(f"  [{i+1}] {short!r:60} → {result}")
        else:
            print(f"  {RED}  [{i+1}] {short!r:60} → got '{result}', expected '{expected}'{RESET}")

    # ── Debrief ──────────────────────────────────────────────────────────────
    separator()
    question("If a note contains 'BP: 148/92' — is that structured, unstructured, or both? Why?")
    question("The hospital's research team wants to find all patients with eGFR < 60. "
             "What is easier to query — structured tables or discharge notes?")
    question("~80% of clinical data is unstructured. What risks does this create?")


# ═══════════════════════════════════════════════════════════════════════════════
# EXERCISE 2 — EHR Data Schemas & Longitudinal Records
# ═══════════════════════════════════════════════════════════════════════════════

def exercise_2():
    banner("EXERCISE 2 — EHR Data Schemas & Longitudinal Patient Records", CYAN)
    print(textwrap.dedent("""
    Scenario: You are building a lightweight EHR database for Bangalore City
    Hospital. Design and query a star-schema database that holds longitudinal
    patient data across multiple encounters and years.
    """))

    conn = sqlite3.connect(":memory:")
    cur  = conn.cursor()

    # ── DEMO: Schema creation ─────────────────────────────────────────────────
    section("DEMO — Creating the EHR Star Schema")

    schema_sql = """
    CREATE TABLE patients (
        patient_id   TEXT PRIMARY KEY,
        mrn          TEXT UNIQUE,
        full_name    TEXT,
        dob          TEXT,
        gender       TEXT,
        blood_type   TEXT,
        created_at   TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE encounters (
        enc_id       TEXT PRIMARY KEY,
        patient_id   TEXT REFERENCES patients(patient_id),
        enc_date     TEXT,
        enc_type     TEXT,   -- 'outpatient', 'inpatient', 'emergency'
        department   TEXT,
        attending_dr TEXT
    );

    CREATE TABLE observations (
        obs_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        enc_id       TEXT REFERENCES encounters(enc_id),
        loinc_code   TEXT,
        display_name TEXT,
        value        REAL,
        unit         TEXT,
        obs_date     TEXT
    );

    CREATE TABLE conditions (
        cond_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id   TEXT REFERENCES patients(patient_id),
        icd10_code   TEXT,
        description  TEXT,
        onset_date   TEXT,
        status       TEXT   -- 'active', 'resolved', 'chronic'
    );

    CREATE TABLE medications (
        med_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id   TEXT REFERENCES patients(patient_id),
        enc_id       TEXT REFERENCES encounters(enc_id),
        rxnorm_code  TEXT,
        drug_name    TEXT,
        dose         TEXT,
        frequency    TEXT,
        start_date   TEXT,
        end_date     TEXT
    );
    """
    conn.executescript(schema_sql)
    success("Schema created: patients, encounters, observations, conditions, medications")

    # ── DEMO: Seed data ───────────────────────────────────────────────────────
    section("DEMO — Seeding Longitudinal Patient Data")

    patients = [
        ("PT-001", "MRN-10001", "Rajan Menon",     "1970-04-12", "M", "B+"),
        ("PT-002", "MRN-10002", "Lakshmi Nair",    "1985-09-22", "F", "O+"),
        ("PT-003", "MRN-10003", "Suresh Patel",    "1955-01-30", "M", "A-"),
    ]
    cur.executemany("INSERT INTO patients VALUES (?,?,?,?,?,?,datetime('now'))", patients)

    encounters = [
        # Rajan — 5 encounters over 6 years
        ("ENC-001", "PT-001", "2018-03-15", "outpatient", "Endocrinology",  "Dr. Sharma"),
        ("ENC-002", "PT-001", "2019-06-20", "outpatient", "Endocrinology",  "Dr. Sharma"),
        ("ENC-003", "PT-001", "2021-11-05", "inpatient",  "General Medicine","Dr. Kumar"),
        ("ENC-004", "PT-001", "2023-02-18", "outpatient", "Endocrinology",  "Dr. Sharma"),
        ("ENC-005", "PT-001", "2024-06-03", "inpatient",  "General Medicine","Dr. Sharma"),
        # Lakshmi — 3 encounters
        ("ENC-006", "PT-002", "2020-08-10", "outpatient", "Cardiology",     "Dr. Rao"),
        ("ENC-007", "PT-002", "2022-01-14", "emergency",  "Emergency",      "Dr. Reddy"),
        ("ENC-008", "PT-002", "2023-09-25", "outpatient", "Cardiology",     "Dr. Rao"),
        # Suresh — 2 encounters
        ("ENC-009", "PT-003", "2019-05-12", "outpatient", "Nephrology",     "Dr. Thomas"),
        ("ENC-010", "PT-003", "2024-03-08", "inpatient",  "Nephrology",     "Dr. Thomas"),
    ]
    cur.executemany("INSERT INTO encounters VALUES (?,?,?,?,?,?)", encounters)

    observations = [
        # Rajan's HbA1c trend (LOINC 4548-4)
        ("ENC-001","4548-4","HbA1c",     7.2, "%",      "2018-03-15"),
        ("ENC-002","4548-4","HbA1c",     7.8, "%",      "2019-06-20"),
        ("ENC-004","4548-4","HbA1c",     8.4, "%",      "2023-02-18"),
        ("ENC-005","4548-4","HbA1c",     8.9, "%",      "2024-06-03"),
        # Rajan's blood glucose (LOINC 2345-7)
        ("ENC-001","2345-7","Blood Glucose", 126, "mg/dL", "2018-03-15"),
        ("ENC-002","2345-7","Blood Glucose", 145, "mg/dL", "2019-06-20"),
        ("ENC-005","2345-7","Blood Glucose", 182, "mg/dL", "2024-06-03"),
        # Rajan's systolic BP (LOINC 8480-6)
        ("ENC-001","8480-6","Systolic BP", 130, "mmHg", "2018-03-15"),
        ("ENC-004","8480-6","Systolic BP", 140, "mmHg", "2023-02-18"),
        ("ENC-005","8480-6","Systolic BP", 148, "mmHg", "2024-06-03"),
        # Lakshmi's echo EF (LOINC 8806-2)
        ("ENC-006","8806-2","Echo EF",    60, "%",   "2020-08-10"),
        ("ENC-007","8806-2","Echo EF",    42, "%",   "2022-01-14"),
        ("ENC-008","8806-2","Echo EF",    48, "%",   "2023-09-25"),
    ]
    cur.executemany("INSERT INTO observations(enc_id,loinc_code,display_name,value,unit,obs_date) VALUES (?,?,?,?,?,?)", observations)

    conditions = [
        ("PT-001","E11.9",  "Type 2 Diabetes Mellitus",            "2018-03-15","chronic"),
        ("PT-001","E11.65", "T2DM with hyperglycaemia+hyperlipid.", "2024-06-03","active"),
        ("PT-001","I10",    "Essential Hypertension",               "2021-11-05","chronic"),
        ("PT-001","N08",    "Diabetic nephropathy",                 "2024-06-03","active"),
        ("PT-002","I50.9",  "Heart Failure, unspecified",           "2022-01-14","chronic"),
        ("PT-002","I10",    "Essential Hypertension",               "2020-08-10","chronic"),
        ("PT-003","N18.3",  "Chronic Kidney Disease, Stage 3",      "2019-05-12","chronic"),
    ]
    cur.executemany("INSERT INTO conditions(patient_id,icd10_code,description,onset_date,status) VALUES (?,?,?,?,?)", conditions)

    medications = [
        ("PT-001","ENC-001","860975","Metformin",   "500mg",  "BD","2018-03-15",None),
        ("PT-001","ENC-004","860975","Metformin",   "1000mg", "BD","2023-02-18",None),
        ("PT-001","ENC-005","310798","Glipizide",   "5mg",    "OD","2024-06-03",None),
        ("PT-001","ENC-003","329498","Amlodipine",  "5mg",    "OD","2021-11-05",None),
        ("PT-001","ENC-005","35208", "Ramipril",    "2.5mg",  "OD","2024-06-03",None),
        ("PT-002","ENC-006","200031","Furosemide",  "40mg",   "OD","2020-08-10",None),
        ("PT-002","ENC-007","308460","Carvedilol",  "6.25mg", "BD","2022-01-14",None),
        ("PT-003","ENC-009","206765","Losartan",    "50mg",   "OD","2019-05-12",None),
    ]
    cur.executemany("INSERT INTO medications(patient_id,enc_id,rxnorm_code,drug_name,dose,frequency,start_date,end_date) VALUES (?,?,?,?,?,?,?,?)", medications)

    conn.commit()
    success("Data seeded — 3 patients, 10 encounters, 13 observations, 7 conditions, 8 medications")

    # ── DEMO: Longitudinal HbA1c query ───────────────────────────────────────
    section("DEMO — Longitudinal HbA1c Trend for Rajan Menon")

    rows = cur.execute("""
        SELECT o.obs_date, o.value, o.unit,
               CASE WHEN o.value < 5.7 THEN 'Normal'
                    WHEN o.value < 6.5 THEN 'Pre-diabetic'
                    ELSE 'Diabetic range' END AS interpretation
        FROM observations o
        JOIN encounters e ON o.enc_id = e.enc_id
        WHERE e.patient_id = 'PT-001'
          AND o.loinc_code = '4548-4'
        ORDER BY o.obs_date
    """).fetchall()

    print(f"\n  {'Date':<14} {'HbA1c':>8} {'Unit':<6} {'Interpretation'}")
    print(f"  {'─'*12} {'─'*8} {'─'*6} {'─'*20}")
    for r in rows:
        flag = f"{RED}▲{RESET}" if r[1] > 8.0 else (f"{YELLOW}►{RESET}" if r[1] > 7.0 else f"{GREEN}●{RESET}")
        print(f"  {r[0]:<14} {r[1]:>6.1f}  {r[2]:<6} {flag} {r[3]}")

    # ── DEMO: Multi-condition summary ─────────────────────────────────────────
    section("DEMO — All Active Conditions (Multi-Patient View)")

    rows = cur.execute("""
        SELECT p.full_name, c.icd10_code, c.description, c.onset_date, c.status
        FROM conditions c
        JOIN patients p ON c.patient_id = p.patient_id
        ORDER BY p.full_name, c.onset_date
    """).fetchall()

    if TABULATE_OK:
        print(tabulate(rows, headers=["Patient","ICD-10","Description","Onset","Status"], tablefmt="rounded_outline"))
    else:
        for r in rows:
            print(f"  {r[0]:18} {r[1]:8} {r[2]:40} {r[3]}")

    # ── TODO BLOCK 1 ─────────────────────────────────────────────────────────
    section("TODO 2A — Write the Medication Timeline Query", RED)
    print("""
  Write a SQL query that returns Rajan Menon's (PT-001) complete medication
  history ordered by start_date. Include:
    • encounter date (from encounters table)
    • drug name, dose, frequency
    • start date

  Assign your SQL string to the variable `med_query` below and run the cell.
    """)

    # ── Students fill this in ──────────────────────────────────────────────
    med_query = """
    -- TODO: Write your query here
    -- Tables to JOIN: medications, encounters, patients
    -- Filter: patient_id = 'PT-001'
    -- ORDER BY: start_date ASC
    SELECT 'NOT IMPLEMENTED' AS note
    """
    # ── End student section ────────────────────────────────────────────────

    try:
        rows = cur.execute(med_query).fetchall()
        if rows and rows[0][0] != "NOT IMPLEMENTED":
            print("  Medication history:")
            for r in rows:
                print(f"    {str(r)}")
        else:
            warn("Query not yet implemented — replace the SELECT above.")
    except Exception as e:
        print(f"  {RED}SQL error: {e}{RESET}")

    # Expected output hint:
    info("Expected: 5 rows for Metformin→Metformin(dose-up)→Amlodipine→Glipizide→Ramipril")

    # ── TODO BLOCK 2 ─────────────────────────────────────────────────────────
    section("TODO 2B — Comorbidity Risk Flag", RED)
    print("""
  Write a SQL query that identifies patients with BOTH:
    • Diabetes (any ICD-10 code starting with E11)
    • Hypertension (ICD-10 I10)
  and returns: patient name, number of active conditions, latest encounter date.

  Assign your SQL to `comorbid_query` and run.
    """)

    # ── Students fill this in ──────────────────────────────────────────────
    comorbid_query = """
    -- TODO: Write your query here
    -- Hint: use GROUP BY patient_id and HAVING COUNT to check for both conditions
    -- Hint: use LIKE 'E11%' to match all T2DM subcodes
    SELECT 'NOT IMPLEMENTED' AS note
    """
    # ── End student section ────────────────────────────────────────────────

    try:
        rows = cur.execute(comorbid_query).fetchall()
        if rows and rows[0][0] != "NOT IMPLEMENTED":
            print("  Comorbid patients:")
            for r in rows:
                print(f"    {str(r)}")
        else:
            warn("Query not yet implemented — replace the SELECT above.")
    except Exception as e:
        print(f"  {RED}SQL error: {e}{RESET}")

    info("Expected: Rajan Menon (PT-001) — has both E11.x and I10")

    # ── TODO BLOCK 3 ─────────────────────────────────────────────────────────
    section("TODO 2C — Add a Missing Encounter", RED)
    print("""
  Insert a new outpatient encounter for Rajan (PT-001) today with:
    • A new HbA1c observation of 7.4% (LOINC: 4548-4) — after treatment
    • Attending: Dr. Sharma, Department: Endocrinology

  Then re-run the HbA1c trend query to confirm the new value appears.
    """)

    # ── Students fill this in ──────────────────────────────────────────────
    today = datetime.now().strftime("%Y-%m-%d")

    # TODO: Insert a new row into encounters
    # cur.execute("INSERT INTO encounters VALUES (...)")

    # TODO: Insert a new row into observations
    # cur.execute("INSERT INTO observations(...) VALUES (...)")

    conn.commit()
    # ── End student section ────────────────────────────────────────────────

    rows = cur.execute("""
        SELECT o.obs_date, o.value FROM observations o
        JOIN encounters e ON o.enc_id = e.enc_id
        WHERE e.patient_id = 'PT-001' AND o.loinc_code = '4548-4'
        ORDER BY o.obs_date
    """).fetchall()
    print("  Current HbA1c timeline:", [(r[0], r[1]) for r in rows])
    if any(r[0] == today for r in rows):
        success("New observation inserted successfully!")
    else:
        warn("Today's observation not found yet — complete the INSERT statements.")

    # ── Debrief ──────────────────────────────────────────────────────────────
    separator()
    question("Why do we store LOINC codes alongside observation names?")
    question("Rajan's HbA1c went from 7.2% in 2018 to 8.9% in 2024. "
             "What schema design makes it easy to detect this trend automatically?")
    question("If a patient transfers from Apollo to BCH, how would you merge "
             "their longitudinal record without creating duplicates?")

    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# EXERCISE 3 — Clinical Coding: ICD-10 & SNOMED CT
# ═══════════════════════════════════════════════════════════════════════════════

def exercise_3():
    banner("EXERCISE 3 — Clinical Coding: ICD-10 & SNOMED CT", CYAN)
    print(textwrap.dedent("""
    Scenario: You are a clinical informaticist validating coding quality for
    a hospital preparing for NABH accreditation. Use ICD-10 and SNOMED CT
    lookups to code a patient encounter and assess coding accuracy.
    """))

    # ── DEMO: ICD-10 lookup table ─────────────────────────────────────────────
    section("DEMO — ICD-10 Code Lookup Table")

    ICD10 = {
        # Endocrine
        "E11.9":  {"desc": "Type 2 DM without complications",           "chapter": "E", "block": "E10-E14"},
        "E11.65": {"desc": "T2DM with hyperglycaemia & hyperlipidaemia","chapter": "E", "block": "E10-E14"},
        "E11.22": {"desc": "T2DM with diabetic CKD stage 3",            "chapter": "E", "block": "E10-E14"},
        "E11.641":{"desc": "T2DM with diabetic polyneuropathy",         "chapter": "E", "block": "E10-E14"},
        # Cardiovascular
        "I10":    {"desc": "Essential (primary) hypertension",          "chapter": "I", "block": "I10-I15"},
        "I50.9":  {"desc": "Heart failure, unspecified",                "chapter": "I", "block": "I50"},
        "I63.9":  {"desc": "Cerebral infarction, unspecified",          "chapter": "I", "block": "I60-I69"},
        "I25.10": {"desc": "Atherosclerotic heart disease, unspecified", "chapter": "I", "block": "I20-I25"},
        # Respiratory
        "J18.9":  {"desc": "Pneumonia, unspecified organism",           "chapter": "J", "block": "J10-J18"},
        "J45.909":{"desc": "Unspecified asthma, uncomplicated",         "chapter": "J", "block": "J40-J47"},
        "J44.1":  {"desc": "COPD with acute exacerbation",             "chapter": "J", "block": "J40-J47"},
        # Renal
        "N18.3":  {"desc": "Chronic kidney disease, stage 3",          "chapter": "N", "block": "N17-N19"},
        "N18.4":  {"desc": "Chronic kidney disease, stage 4",          "chapter": "N", "block": "N17-N19"},
        "N08":    {"desc": "Glomerular disorders in diseases elsewhere","chapter": "N", "block": "N00-N08"},
        # Musculoskeletal
        "M79.3":  {"desc": "Panniculitis, unspecified",                "chapter": "M", "block": "M70-M79"},
        "M54.5":  {"desc": "Low back pain",                            "chapter": "M", "block": "M50-M54"},
        # Injury
        "S72.001A":{"desc": "Fracture of unspecified part of femoral neck, init enc","chapter":"S","block":"S70-S79"},
        # Mental health
        "F32.9":  {"desc": "Major depressive disorder, single episode, unspecified","chapter":"F","block":"F30-F39"},
    }

    print("  Sample ICD-10 codes loaded:")
    for code, meta in list(ICD10.items())[:6]:
        print(f"    {CYAN}{code:10}{RESET} {meta['desc'][:55]}")
    print(f"  ... and {len(ICD10)-6} more")

    def icd10_lookup(code: str) -> dict:
        """Look up an ICD-10 code. Returns metadata or error dict."""
        code = code.strip().upper()
        if code in ICD10:
            return {"found": True, "code": code, **ICD10[code]}
        # Try prefix match (e.g. E11 → matches E11.x)
        prefix_hits = [k for k in ICD10 if k.startswith(code)]
        if prefix_hits:
            return {"found": True, "code": prefix_hits[0], "note": f"prefix match from '{code}'", **ICD10[prefix_hits[0]]}
        return {"found": False, "code": code, "desc": "UNKNOWN CODE", "chapter": "?", "block": "?"}

    # ── DEMO: SNOMED CT hierarchy ─────────────────────────────────────────────
    section("DEMO — SNOMED CT Concept Hierarchy")

    SNOMED = {
        404684003: {
            "fsn": "Clinical finding (finding)",
            "children": [362965005, 118234003]
        },
        362965005: {
            "fsn": "Disorder of endocrine system (disorder)",
            "children": [73211009, 44054006]
        },
        73211009: {
            "fsn": "Diabetes mellitus (disorder)",
            "children": [44054006, 190331003, 81531005]
        },
        44054006: {
            "fsn": "Diabetes mellitus type 2 (disorder)",
            "children": [420789003, 421893009],
            "attributes": {
                "finding_site": "Structure of endocrine system (body structure)",
                "pathology":    "Metabolic pathology (morphologic abnormality)",
                "icd10_map":    "E11.9"
            }
        },
        420789003: {
            "fsn": "Diabetic retinopathy (disorder)",
            "attributes": {
                "finding_site": "Retinal structure (body structure)",
                "icd10_map":    "E11.31"
            }
        },
        421893009: {
            "fsn": "Diabetic nephropathy (disorder)",
            "attributes": {
                "finding_site": "Kidney structure (body structure)",
                "icd10_map":    "N08 + E11.22"
            }
        },
        118234003: {
            "fsn": "Finding of cardiovascular system (finding)",
            "children": [84114007, 38341003]
        },
        84114007: {
            "fsn": "Heart failure (disorder)",
            "attributes": {"finding_site": "Heart structure", "icd10_map": "I50.9"}
        },
        38341003: {
            "fsn": "Hypertensive disorder (disorder)",
            "attributes": {"finding_site": "Systemic arterial structure", "icd10_map": "I10"}
        },
        190331003: {
            "fsn": "Type 1 diabetes mellitus (disorder)",
            "attributes": {"icd10_map": "E10.9"}
        },
        81531005: {
            "fsn": "Diabetes mellitus in mother, complicating pregnancy (disorder)",
            "attributes": {"icd10_map": "O24.419"}
        },
        233604007: {
            "fsn": "Pneumonia (disorder)",
            "attributes": {
                "finding_site": "Lung structure (body structure)",
                "icd10_map":    "J18.9"
            }
        }
    }

    def snomed_ancestors(concept_id: int, hierarchy=SNOMED, path=None) -> list:
        """Return all ancestor concept IDs for a SNOMED concept."""
        if path is None:
            path = []
        for cid, concept in hierarchy.items():
            if concept_id in concept.get("children", []):
                return snomed_ancestors(cid, hierarchy, path + [cid])
        return path

    def snomed_describe(concept_id: int) -> None:
        """Print a concept card with attributes and ancestors."""
        concept = SNOMED.get(concept_id)
        if not concept:
            warn(f"Concept {concept_id} not in local hierarchy")
            return
        print(f"\n  {BOLD}Concept: {concept_id}{RESET}")
        print(f"  FSN       : {concept['fsn']}")
        attrs = concept.get("attributes", {})
        if attrs:
            for k, v in attrs.items():
                print(f"  {k:14}: {v}")
        ancestors = snomed_ancestors(concept_id)
        if ancestors:
            chain = " → ".join(str(a) for a in ancestors) + f" → {concept_id}"
            print(f"  Hierarchy : {chain}")
        children = concept.get("children", [])
        if children:
            print(f"  Children  : {children}")

    print("  Describing SNOMED concept 44054006 (T2DM):")
    snomed_describe(44054006)

    # ── DEMO: Code a clinical encounter ──────────────────────────────────────
    section("DEMO — Coding a Clinical Encounter")

    encounter_summary = {
        "patient":     "Rajan Menon",
        "date":        "2024-06-03",
        "diagnoses":   ["Type 2 diabetes with hyperglycaemia", "Essential hypertension", "Early diabetic nephropathy"],
        "procedures":  ["HbA1c measurement", "Renal function panel", "Fundoscopy"],
    }

    diagnosis_to_icd10 = {
        "Type 2 diabetes with hyperglycaemia":  "E11.65",
        "Essential hypertension":               "I10",
        "Early diabetic nephropathy":           "N08",
    }

    print(f"\n  Patient  : {encounter_summary['patient']}")
    print(f"  Date     : {encounter_summary['date']}\n")
    print(f"  {'Diagnosis':<42} {'ICD-10':>8} {'Description'}")
    print(f"  {'─'*41} {'─'*8} {'─'*30}")
    for diag in encounter_summary["diagnoses"]:
        code = diagnosis_to_icd10.get(diag, "NOT CODED")
        result = icd10_lookup(code)
        status = f"{GREEN}✓{RESET}" if result["found"] else f"{RED}✗{RESET}"
        print(f"  {diag:<42} {status} {code:>8}  {result['desc'][:35]}")

    # ── TODO BLOCK 1 ─────────────────────────────────────────────────────────
    section("TODO 3A — Code a New Encounter", RED)
    print("""
  Code the following encounter for a new patient.
  Look up the correct ICD-10 codes and fill in the mapping dict.

  Patient: Priya Iyer, 62F
  Diagnoses:
    1. "Community-acquired pneumonia"        → ICD-10: ?
    2. "Chronic obstructive pulmonary disease with exacerbation"  → ICD-10: ?
    3. "Heart failure, cause unknown"        → ICD-10: ?
    4. "Low back pain"                       → ICD-10: ?

  Hint: Use the ICD10 dict to look up codes.
  Hint: icd10_lookup("J18") will prefix-match to J18.9.
    """)

    # ── Students fill this in ──────────────────────────────────────────────
    priya_coding = {
        "Community-acquired pneumonia":                            None,   # TODO: replace None with the correct code string
        "Chronic obstructive pulmonary disease with exacerbation": None,
        "Heart failure, cause unknown":                            None,
        "Low back pain":                                           None,
    }
    # ── End student section ────────────────────────────────────────────────

    print("  Your coding results:")
    correct_codes = {"Community-acquired pneumonia": "J18.9",
                     "Chronic obstructive pulmonary disease with exacerbation": "J44.1",
                     "Heart failure, cause unknown": "I50.9",
                     "Low back pain": "M54.5"}
    score = 0
    for diag, code in priya_coding.items():
        if code is None:
            warn(f"  {diag[:42]:<42} → Not coded yet")
            continue
        result = icd10_lookup(code)
        expected = correct_codes.get(diag)
        if code.upper() == expected:
            success(f"  {diag[:42]:<42} → {code}  ✓ Correct!")
            score += 1
        else:
            print(f"  {RED}  {diag[:42]:<42} → {code}  ✗ Expected {expected}{RESET}")
    print(f"\n  Score: {score}/{len(priya_coding)}")

    # ── TODO BLOCK 2 ─────────────────────────────────────────────────────────
    section("TODO 3B — SNOMED Ancestor Walk", RED)
    print("""
  Write a function that, given a SNOMED concept ID, prints all ancestor
  concepts up to the root, showing each concept's FSN.

  Example for concept 421893009 (Diabetic nephropathy):
      421893009  Diabetic nephropathy (disorder)
        44054006  Type 2 DM (disorder)
        73211009  Diabetes mellitus (disorder)
       362965005  Disorder of endocrine system (disorder)
       404684003  Clinical finding (finding)    ← root
    """)

    def print_snomed_hierarchy(concept_id: int) -> None:
        """
        TODO: Print concept IDs and FSNs from concept_id up to root.
        Use snomed_ancestors() to get the list of ancestor IDs.
        Use SNOMED.get(cid, {}).get('fsn') to get the label.
        Print the concept itself first, then its ancestors.
        """
        # ── Replace 'pass' with your implementation ────────────────────────
        pass
        # ── End student section ────────────────────────────────────────────

    print("  SNOMED hierarchy for Diabetic Nephropathy (421893009):")
    print_snomed_hierarchy(421893009)

    # ── TODO BLOCK 3 ─────────────────────────────────────────────────────────
    section("TODO 3C — ICD-10 ↔ SNOMED Cross-Reference", RED)
    print("""
  The SNOMED concept attributes contain an 'icd10_map' key.
  Write a function snomed_to_icd10(concept_id) that:
    1. Looks up the concept in SNOMED
    2. Returns the icd10_map value if present
    3. If not present, checks its children recursively
    4. Returns None if no mapping is found

  Then call it on these concepts and verify the mappings:
    44054006  → should map to E11.9
    84114007  → should map to I50.9
    233604007 → should map to J18.9
    """)

    def snomed_to_icd10(concept_id: int) -> str:
        """
        TODO: Return ICD-10 mapping for a SNOMED concept, or None.
        """
        # ── Replace 'pass' with your implementation ────────────────────────
        pass
        # ── End student section ────────────────────────────────────────────

    test_mappings = [
        (44054006,  "E11.9"),
        (84114007,  "I50.9"),
        (233604007, "J18.9"),
    ]
    print("  Cross-reference results:")
    for cid, expected in test_mappings:
        result = snomed_to_icd10(cid)
        label = SNOMED.get(cid, {}).get("fsn", "?")
        if result is None:
            warn(f"  {cid} ({label[:35]}) → NOT IMPLEMENTED")
        elif result == expected:
            success(f"  {cid} ({label[:35]}) → {result}")
        else:
            print(f"  {RED}  {cid} ({label[:35]}) → got '{result}', expected '{expected}'{RESET}")

    # ── Debrief ──────────────────────────────────────────────────────────────
    separator()
    question("Why does SNOMED have 350K+ concepts while ICD-10 has only 71K?")
    question("A cardiologist codes heart failure as I50.9, but a researcher "
             "needs to know whether it is HFrEF or HFpEF. Which coding "
             "system handles this better, and why?")
    question("If you want to find ALL diabetes-related conditions across an EHR "
             "system — including subtypes — would you use ICD-10 LIKE 'E11%' "
             "or SNOMED hierarchy traversal? What are the tradeoffs?")
    question("NABH accreditation requires accurate ICD-10 coding. What goes "
             "wrong clinically if a coder uses E11.9 instead of E11.22?")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    exercises = {"1": exercise_1, "2": exercise_2, "3": exercise_3}

    if "--ex" in sys.argv:
        idx = sys.argv.index("--ex")
        key = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
        if key in exercises:
            exercises[key]()
        else:
            print(f"Unknown exercise '{key}'. Choose from: {list(exercises.keys())}")
    else:
        for fn in exercises.values():
            fn()
            print("\n" + "═" * 72 + "\n")

    banner("All Exercises Complete — Module 2 🎉", GREEN)
    print(f"""
  {BOLD}Submission checklist:{RESET}
    □ Ex 1A: Extra regex patterns (SpO2, eGFR, platelets, microalbumin)
    □ Ex 1B: classify_token() implemented and passing all 8 tests
    □ Ex 2A: Medication timeline SQL query returns 5 rows for PT-001
    □ Ex 2B: Comorbidity query identifies PT-001 correctly
    □ Ex 2C: New encounter + observation inserted for today
    □ Ex 3A: Priya Iyer's encounter coded 4/4 correctly
    □ Ex 3B: SNOMED hierarchy printed correctly for concept 421893009
    □ Ex 3C: ICD-10 cross-reference working for all 3 concepts

  Save your completed file and upload to the course portal.
    """)


if __name__ == "__main__":
    main()
