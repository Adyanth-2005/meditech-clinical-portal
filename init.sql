-- ============================================================
--  Bangalore City Hospital — Mock EHR Database
--  Auto-loaded by PostgreSQL on first container start.
--  Students: this data is pre-seeded so you can start
--  querying immediately with psql or any SQL client.
-- ============================================================

-- ── 1. PATIENTS ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS patients (
    patient_id   TEXT PRIMARY KEY,
    mrn          TEXT UNIQUE,
    full_name    TEXT NOT NULL,
    dob          DATE,
    gender       CHAR(1),   -- 'M' or 'F'
    blood_type   TEXT,
    phone        TEXT,
    city         TEXT
);

INSERT INTO patients VALUES
  ('PT-001','MRN-10001','Rajan Menon',      '1970-04-12','M','B+','9845012345','Bangalore'),
  ('PT-002','MRN-10002','Lakshmi Nair',     '1985-09-22','F','O+','9876543210','Mysuru'),
  ('PT-003','MRN-10003','Suresh Patel',     '1955-01-30','M','A-','9741234567','Bangalore'),
  ('PT-004','MRN-10004','Priya Iyer',       '1962-07-15','F','AB+','9900112233','Hubli'),
  ('PT-005','MRN-10005','Arjun Krishnan',   '1990-03-08','M','O-','9123456789','Bangalore'),
  ('PT-006','MRN-10006','Meena Reddy',      '1978-11-25','F','B-','9988776655','Hyderabad'),
  ('PT-007','MRN-10007','Vikram Singh',     '1948-06-02','M','A+','9871234560','Delhi'),
  ('PT-008','MRN-10008','Ananya Das',       '2001-02-14','F','O+','9000123456','Kolkata');

-- ── 2. ENCOUNTERS ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS encounters (
    enc_id       TEXT PRIMARY KEY,
    patient_id   TEXT REFERENCES patients(patient_id),
    enc_date     DATE,
    enc_type     TEXT,          -- 'outpatient' | 'inpatient' | 'emergency'
    department   TEXT,
    attending_dr TEXT,
    discharge_dt DATE           -- NULL for outpatient
);

INSERT INTO encounters VALUES
  ('ENC-001','PT-001','2018-03-15','outpatient','Endocrinology',  'Dr. Sharma',  NULL),
  ('ENC-002','PT-001','2019-06-20','outpatient','Endocrinology',  'Dr. Sharma',  NULL),
  ('ENC-003','PT-001','2021-11-05','inpatient', 'General Medicine','Dr. Kumar',  '2021-11-09'),
  ('ENC-004','PT-001','2023-02-18','outpatient','Endocrinology',  'Dr. Sharma',  NULL),
  ('ENC-005','PT-001','2024-06-03','inpatient', 'General Medicine','Dr. Sharma', '2024-06-07'),
  ('ENC-006','PT-002','2020-08-10','outpatient','Cardiology',     'Dr. Rao',     NULL),
  ('ENC-007','PT-002','2022-01-14','emergency', 'Emergency',      'Dr. Reddy',   '2022-01-16'),
  ('ENC-008','PT-002','2023-09-25','outpatient','Cardiology',     'Dr. Rao',     NULL),
  ('ENC-009','PT-003','2019-05-12','outpatient','Nephrology',     'Dr. Thomas',  NULL),
  ('ENC-010','PT-003','2024-03-08','inpatient', 'Nephrology',     'Dr. Thomas',  '2024-03-14'),
  ('ENC-011','PT-004','2023-11-20','inpatient', 'Pulmonology',    'Dr. Verma',   '2023-11-25'),
  ('ENC-012','PT-005','2024-01-10','outpatient','Orthopedics',    'Dr. Mehta',   NULL),
  ('ENC-013','PT-006','2022-07-05','outpatient','Endocrinology',  'Dr. Sharma',  NULL),
  ('ENC-014','PT-007','2024-05-18','inpatient', 'Cardiology',     'Dr. Rao',     '2024-05-22'),
  ('ENC-015','PT-008','2024-02-28','outpatient','General Medicine','Dr. Kumar',  NULL);

-- ── 3. OBSERVATIONS (Vitals & Lab results) ───────────────────
--  loinc_code: international standard for lab & clinical tests
CREATE TABLE IF NOT EXISTS observations (
    obs_id       SERIAL PRIMARY KEY,
    enc_id       TEXT REFERENCES encounters(enc_id),
    loinc_code   TEXT,
    display_name TEXT,
    value        NUMERIC,
    unit         TEXT,
    obs_date     DATE
);

INSERT INTO observations (enc_id, loinc_code, display_name, value, unit, obs_date) VALUES
  -- Rajan: HbA1c trend (worsening over years)
  ('ENC-001','4548-4', 'HbA1c',        7.2,  '%',      '2018-03-15'),
  ('ENC-002','4548-4', 'HbA1c',        7.8,  '%',      '2019-06-20'),
  ('ENC-004','4548-4', 'HbA1c',        8.4,  '%',      '2023-02-18'),
  ('ENC-005','4548-4', 'HbA1c',        8.9,  '%',      '2024-06-03'),
  -- Rajan: Blood glucose
  ('ENC-001','2345-7', 'Blood Glucose',126,  'mg/dL',  '2018-03-15'),
  ('ENC-002','2345-7', 'Blood Glucose',145,  'mg/dL',  '2019-06-20'),
  ('ENC-005','2345-7', 'Blood Glucose',182,  'mg/dL',  '2024-06-03'),
  -- Rajan: Systolic BP
  ('ENC-001','8480-6', 'Systolic BP',  130,  'mmHg',   '2018-03-15'),
  ('ENC-004','8480-6', 'Systolic BP',  140,  'mmHg',   '2023-02-18'),
  ('ENC-005','8480-6', 'Systolic BP',  148,  'mmHg',   '2024-06-03'),
  -- Rajan: eGFR (renal function)
  ('ENC-003','33914-3','eGFR',         72,   'mL/min', '2021-11-05'),
  ('ENC-005','33914-3','eGFR',         68,   'mL/min', '2024-06-03'),
  -- Lakshmi: Echo Ejection Fraction (heart pumping strength)
  ('ENC-006','8806-2', 'Echo EF',      60,   '%',      '2020-08-10'),
  ('ENC-007','8806-2', 'Echo EF',      42,   '%',      '2022-01-14'),  -- acute drop → emergency
  ('ENC-008','8806-2', 'Echo EF',      48,   '%',      '2023-09-25'),
  -- Suresh: Creatinine (kidney marker)
  ('ENC-009','2160-0', 'Creatinine',   1.8,  'mg/dL',  '2019-05-12'),
  ('ENC-010','2160-0', 'Creatinine',   2.4,  'mg/dL',  '2024-03-08'),
  -- Priya: SpO2
  ('ENC-011','2708-6', 'SpO2',         88,   '%',      '2023-11-20'),
  ('ENC-011','8310-5', 'Body Temp',    38.9, 'C',      '2023-11-20'),
  -- Arjun: Body Weight
  ('ENC-012','29463-7','Body Weight',  95,   'kg',     '2024-01-10'),
  -- Meena: HbA1c
  ('ENC-013','4548-4', 'HbA1c',        9.2,  '%',      '2022-07-05'),
  -- Vikram: Troponin (heart attack marker)
  ('ENC-014','10839-9','Troponin I',   2.8,  'ng/mL',  '2024-05-18'),
  ('ENC-014','8480-6', 'Systolic BP',  90,   'mmHg',   '2024-05-18');  -- hypotensive

-- ── 4. CONDITIONS (Diagnoses) ────────────────────────────────
CREATE TABLE IF NOT EXISTS conditions (
    cond_id      SERIAL PRIMARY KEY,
    patient_id   TEXT REFERENCES patients(patient_id),
    icd10_code   TEXT,
    description  TEXT,
    onset_date   DATE,
    status       TEXT   -- 'active' | 'chronic' | 'resolved'
);

INSERT INTO conditions (patient_id, icd10_code, description, onset_date, status) VALUES
  ('PT-001','E11.9',  'Type 2 Diabetes Mellitus',                '2018-03-15','chronic'),
  ('PT-001','E11.65', 'T2DM with hyperglycaemia & hyperlipid.',  '2024-06-03','active'),
  ('PT-001','I10',    'Essential Hypertension',                   '2021-11-05','chronic'),
  ('PT-001','N08',    'Diabetic nephropathy',                     '2024-06-03','active'),
  ('PT-002','I50.9',  'Heart Failure, unspecified',               '2022-01-14','chronic'),
  ('PT-002','I10',    'Essential Hypertension',                   '2020-08-10','chronic'),
  ('PT-003','N18.3',  'Chronic Kidney Disease, Stage 3',          '2019-05-12','chronic'),
  ('PT-003','I10',    'Essential Hypertension',                   '2019-05-12','chronic'),
  ('PT-004','J44.1',  'COPD with acute exacerbation',             '2023-11-20','active'),
  ('PT-004','I50.9',  'Heart Failure, unspecified',               '2023-11-20','active'),
  ('PT-005','M54.5',  'Low back pain',                            '2024-01-10','resolved'),
  ('PT-006','E11.9',  'Type 2 Diabetes Mellitus',                 '2022-07-05','chronic'),
  ('PT-006','E11.65', 'T2DM with hyperglycaemia',                 '2022-07-05','active'),
  ('PT-007','I25.10', 'Atherosclerotic heart disease',            '2024-05-18','active'),
  ('PT-007','I10',    'Essential Hypertension',                   '2024-05-18','chronic'),
  ('PT-008','J18.9',  'Pneumonia, unspecified',                   '2024-02-28','resolved');

-- ── 5. MEDICATIONS ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS medications (
    med_id       SERIAL PRIMARY KEY,
    patient_id   TEXT REFERENCES patients(patient_id),
    enc_id       TEXT REFERENCES encounters(enc_id),
    rxnorm_code  TEXT,   -- standard US drug code (used internationally)
    drug_name    TEXT,
    dose         TEXT,
    frequency    TEXT,   -- OD=once daily, BD=twice daily, TDS=three times daily
    start_date   DATE,
    end_date     DATE
);

INSERT INTO medications (patient_id, enc_id, rxnorm_code, drug_name, dose, frequency, start_date, end_date) VALUES
  ('PT-001','ENC-001','860975','Metformin',   '500mg', 'BD','2018-03-15', NULL),
  ('PT-001','ENC-004','860975','Metformin',   '1000mg','BD','2023-02-18', NULL),  -- dose escalation
  ('PT-001','ENC-005','310798','Glipizide',   '5mg',   'OD','2024-06-03', NULL),
  ('PT-001','ENC-003','329498','Amlodipine',  '5mg',   'OD','2021-11-05', NULL),
  ('PT-001','ENC-005','35208', 'Ramipril',    '2.5mg', 'OD','2024-06-03', NULL),
  ('PT-002','ENC-006','200031','Furosemide',  '40mg',  'OD','2020-08-10', NULL),
  ('PT-002','ENC-007','308460','Carvedilol',  '6.25mg','BD','2022-01-14', NULL),
  ('PT-002','ENC-008','308460','Carvedilol',  '12.5mg','BD','2023-09-25', NULL),  -- dose escalation
  ('PT-003','ENC-009','206765','Losartan',    '50mg',  'OD','2019-05-12', NULL),
  ('PT-004','ENC-011','2395481','Salbutamol', '2.5mg', 'nebulisation','2023-11-20','2023-11-25'),
  ('PT-004','ENC-011','308460','Carvedilol',  '3.125mg','BD','2023-11-20', NULL),
  ('PT-007','ENC-014','1037045','Aspirin',    '325mg', 'STAT','2024-05-18', NULL),
  ('PT-007','ENC-014','1656340','Ticagrelor', '90mg',  'BD','2024-05-18', NULL);

-- ── 6. AUDIT LOG (who accessed what) ─────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    log_id      SERIAL PRIMARY KEY,
    user_name   TEXT,
    action      TEXT,
    table_name  TEXT,
    record_id   TEXT,
    accessed_at TIMESTAMP DEFAULT now()
);

INSERT INTO audit_log (user_name, action, table_name, record_id) VALUES
  ('dr.sharma',  'READ',   'patients',     'PT-001'),
  ('dr.sharma',  'READ',   'observations', 'ENC-005'),
  ('dr.rao',     'READ',   'patients',     'PT-002'),
  ('nurse.kavya','UPDATE', 'observations', 'ENC-007'),
  ('dr.thomas',  'READ',   'patients',     'PT-003'),
  ('admin.user', 'EXPORT', 'patients',     'ALL');    -- flag: bulk export needs review

-- ── Useful views for student queries ─────────────────────────

-- Latest observation per patient per test
CREATE VIEW latest_obs AS
  SELECT DISTINCT ON (e.patient_id, o.loinc_code)
         e.patient_id, p.full_name, o.display_name,
         o.value, o.unit, o.obs_date
  FROM observations o
  JOIN encounters e ON o.enc_id = e.enc_id
  JOIN patients p   ON e.patient_id = p.patient_id
  ORDER BY e.patient_id, o.loinc_code, o.obs_date DESC;

-- Patients with diabetes + hypertension (comorbidity flag)
CREATE VIEW diabetic_hypertensive AS
  SELECT p.patient_id, p.full_name,
         COUNT(DISTINCT c.icd10_code) AS condition_count
  FROM patients p
  JOIN conditions c ON p.patient_id = c.patient_id
  WHERE c.patient_id IN (
        SELECT patient_id FROM conditions WHERE icd10_code LIKE 'E11%')
    AND c.patient_id IN (
        SELECT patient_id FROM conditions WHERE icd10_code = 'I10')
  GROUP BY p.patient_id, p.full_name;
