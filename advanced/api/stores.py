"""
stores.py — data access behind clean interfaces.

Two backends:
  • InMemoryStore  — zero external deps; used for MEDITECH_DEMO=1 and for tests.
  • PostgresStore  — talks to the lab's running PostgreSQL (localhost:5432);
                     bootstraps an `app_users` table and reuses the existing
                     `patients/observations/conditions/medications/audit_log`.

The route layer is identical for both — it only ever sees these interfaces.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional
import os
import json

from auth import hash_password


@dataclass
class User:
    user_id: int
    username: str
    role: str           # 'admin' | 'doctor' | 'patient'
    linked_id: Optional[str]   # patient_id for patients, else None
    full_name: str
    active: bool = True

    def public(self) -> dict:
        d = asdict(self)
        return d


# ── seed content (mirrors init.sql / setup_services.py) ──────────────────────

SEED_PATIENTS = [
    # patient_id, name, age, gender, dept, conditions
    ("PT-001", "Rajan Menon",    54, "M", "Endocrinology",   ["T2DM (E11.65)", "Hypertension (I10)", "Diabetic Nephropathy (N08)"]),
    ("PT-002", "Lakshmi Nair",   39, "F", "Cardiology",      ["Heart Failure (I50.9)", "Hypertension (I10)"]),
    ("PT-003", "Suresh Patel",   69, "M", "Nephrology",      ["CKD Stage 3 (N18.3)", "Hypertension (I10)"]),
    ("PT-004", "Priya Iyer",     62, "F", "Pulmonology",     ["COPD w/ Exacerbation (J44.1)", "Heart Failure (I50.9)"]),
    ("PT-005", "Arjun Krishnan", 34, "M", "Orthopedics",     ["Low Back Pain (M54.5)"]),
    ("PT-006", "Meena Reddy",    46, "F", "Endocrinology",   ["T2DM (E11.65)"]),
    ("PT-007", "Vikram Singh",   76, "M", "Cardiology",      ["Atherosclerotic HD (I25.10)", "Hypertension (I10)"]),
    ("PT-008", "Ananya Das",     23, "F", "General Medicine", ["Pneumonia (J18.9)"]),
]

SEED_OBS = {
    "PT-001": [("HbA1c", 8.9, "%", "H"), ("Blood Glucose", 182, "mg/dL", "H"),
               ("Systolic BP", 148, "mmHg", "H"), ("eGFR", 68, "mL/min", "L")],
    "PT-002": [("Echo EF", 48, "%", "L"), ("BNP", 380, "pg/mL", "H")],
    "PT-003": [("Creatinine", 2.4, "mg/dL", "H"), ("eGFR", 38, "mL/min", "L"),
               ("Potassium", 5.2, "mEq/L", "H")],
    "PT-004": [("SpO2", 88, "%", "L"), ("Body Temp", 38.9, "C", "H"), ("Resp Rate", 24, "/min", "H")],
    "PT-006": [("HbA1c", 9.2, "%", "H")],
    "PT-007": [("Troponin I", 2.8, "ng/mL", "H"), ("Systolic BP", 90, "mmHg", "L"),
               ("Heart Rate", 110, "bpm", "H")],
}

# medications with RxNorm codes (for FHIR MedicationRequest in demo mode)
SEED_MEDS = {
    "PT-001": [{"drug_name": "Metformin", "rxnorm_code": "6809", "dose": "1000mg", "frequency": "BD", "status": "active"},
               {"drug_name": "Ramipril", "rxnorm_code": "35296", "dose": "2.5mg", "frequency": "OD", "status": "active"}],
    "PT-002": [{"drug_name": "Furosemide", "rxnorm_code": "4603", "dose": "40mg", "frequency": "OD", "status": "active"},
               {"drug_name": "Carvedilol", "rxnorm_code": "20352", "dose": "6.25mg", "frequency": "BD", "status": "active"}],
    "PT-003": [{"drug_name": "Amlodipine", "rxnorm_code": "17767", "dose": "5mg", "frequency": "OD", "status": "active"}],
    "PT-007": [{"drug_name": "Aspirin", "rxnorm_code": "1191", "dose": "75mg", "frequency": "OD", "status": "active"},
               {"drug_name": "Atorvastatin", "rxnorm_code": "83367", "dose": "40mg", "frequency": "HS", "status": "active"}],
}

# username, password, role, linked_id, full_name
SEED_USERS = [
    ("admin",     "admin123",   "admin",   None,     "System Administrator"),
    ("dr.sharma", "doctor123",  "doctor",  None,     "Dr. Priya Sharma"),
    ("rajan",     "patient123", "patient", "PT-001", "Rajan Menon"),
]


# ── interface (duck-typed; both backends implement these) ────────────────────

class BaseStore:
    # users
    def get_user(self, username): raise NotImplementedError
    def create_user(self, username, password, role, linked_id, full_name, enrolled_by): raise NotImplementedError
    def list_users(self): raise NotImplementedError
    # clinical
    def list_patients(self): raise NotImplementedError
    def get_patient(self, patient_id): raise NotImplementedError
    # audit
    def audit(self, user_name, action, table_name, record_id): raise NotImplementedError
    def list_audit(self, limit=100): raise NotImplementedError


# ── in-memory backend ────────────────────────────────────────────────────────

class InMemoryStore(BaseStore):
    def __init__(self):
        self._users = {}
        self._audit = []
        self._next_id = 1
        # enrolled (non-seed) users persist to disk so they survive restarts
        self._persist_path = os.environ.get(
            "MEDITECH_USERS_FILE",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "meditech_users.json"))
        # patients keyed by id
        self._patients = {}
        for pid, name, age, gender, dept, conds in SEED_PATIENTS:
            self._patients[pid] = {
                "patient_id": pid, "full_name": name, "age": age, "gender": gender,
                "dept": dept, "conditions": conds,
                "observations": [
                    {"name": n, "value": v, "unit": u, "flag": f}
                    for (n, v, u, f) in SEED_OBS.get(pid, [])
                ],
                "medications": SEED_MEDS.get(pid, []),
            }
        for uname, pw, role, linked, full in SEED_USERS:
            self._add(uname, pw, role, linked, full, enrolled_by="system")
        self._load_persisted()

    def _load_persisted(self):
        try:
            with open(self._persist_path, "r", encoding="utf-8") as fh:
                for rec in json.load(fh):
                    if rec["username"] in self._users:
                        continue
                    u = User(self._next_id, rec["username"], rec["role"],
                             rec.get("linked_id"), rec.get("full_name", ""), True)
                    self._users[rec["username"]] = {
                        "user": u, "hash": rec["hash"],
                        "enrolled_by": rec.get("enrolled_by", ""),
                        "enrolled_at": rec.get("enrolled_at", "")}
                    self._next_id += 1
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

    def _persist(self, username):
        rec = self._users[username]
        out = []
        if os.path.exists(self._persist_path):
            try:
                with open(self._persist_path, "r", encoding="utf-8") as fh:
                    out = json.load(fh)
            except (json.JSONDecodeError, OSError):
                out = []
        out = [r for r in out if r.get("username") != username]
        out.append({"username": username, "hash": rec["hash"],
                    "role": rec["user"].role, "linked_id": rec["user"].linked_id,
                    "full_name": rec["user"].full_name,
                    "enrolled_by": rec["enrolled_by"], "enrolled_at": rec["enrolled_at"]})
        try:
            with open(self._persist_path, "w", encoding="utf-8") as fh:
                json.dump(out, fh, indent=2)
        except OSError:
            pass

    def _add(self, username, password, role, linked_id, full_name, enrolled_by):
        u = User(self._next_id, username, role, linked_id, full_name, True)
        self._users[username] = {"user": u, "hash": hash_password(password),
                                 "enrolled_by": enrolled_by,
                                 "enrolled_at": datetime.now(timezone.utc).isoformat()}
        self._next_id += 1
        return u

    def get_user(self, username):
        rec = self._users.get(username)
        return rec if rec else None

    def create_user(self, username, password, role, linked_id, full_name, enrolled_by):
        if username in self._users:
            raise ValueError("username already exists")
        if role not in ("admin", "doctor", "patient"):
            raise ValueError("invalid role")
        if role == "patient" and linked_id not in self._patients:
            raise ValueError(f"unknown patient_id {linked_id}")
        u = self._add(username, password, role, linked_id, full_name, enrolled_by)
        self._persist(username)
        return u

    def list_users(self):
        return [{**r["user"].public(), "enrolled_by": r["enrolled_by"],
                 "enrolled_at": r["enrolled_at"]} for r in self._users.values()]

    def list_patients(self):
        return [{"patient_id": p["patient_id"], "full_name": p["full_name"],
                 "age": p["age"], "gender": p["gender"], "dept": p["dept"],
                 "conditions": p["conditions"]} for p in self._patients.values()]

    def get_patient(self, patient_id):
        return self._patients.get(patient_id)

    def audit(self, user_name, action, table_name, record_id):
        self._audit.insert(0, {
            "user_name": user_name, "action": action, "table_name": table_name,
            "record_id": record_id, "accessed_at": datetime.now(timezone.utc).isoformat()})

    def list_audit(self, limit=100):
        return self._audit[:limit]


# ── postgres backend ─────────────────────────────────────────────────────────

class PostgresStore(BaseStore):
    def __init__(self, dsn=None):
        import psycopg2
        import psycopg2.extras
        self._psycopg2 = psycopg2
        self._extras = psycopg2.extras
        self.dsn = dsn or os.environ.get(
            "MEDITECH_PG_DSN",
            "host=localhost port=5432 dbname=healthcare_db user=admin password=adminpassword",
        )
        self._bootstrap()

    def _conn(self):
        return self._psycopg2.connect(self.dsn)

    def _bootstrap(self):
        with self._conn() as c, c.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_users (
                    user_id      SERIAL PRIMARY KEY,
                    username     TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role         TEXT NOT NULL CHECK (role IN ('admin','doctor','patient')),
                    linked_id    TEXT,
                    full_name    TEXT,
                    active       BOOLEAN DEFAULT TRUE,
                    enrolled_by  TEXT,
                    enrolled_at  TIMESTAMP DEFAULT now()
                );
            """)
            c.commit()
            # seed default users once
            cur.execute("SELECT COUNT(*) FROM app_users;")
            if cur.fetchone()[0] == 0:
                for uname, pw, role, linked, full in SEED_USERS:
                    cur.execute(
                        "INSERT INTO app_users (username,password_hash,role,linked_id,full_name,enrolled_by) "
                        "VALUES (%s,%s,%s,%s,%s,'system')",
                        (uname, hash_password(pw), role, linked, full))
                c.commit()

    def _row_to_user(self, row):
        return {"user": User(row["user_id"], row["username"], row["role"],
                             row["linked_id"], row["full_name"], row["active"]),
                "hash": row["password_hash"]}

    def get_user(self, username):
        with self._conn() as c, c.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM app_users WHERE username=%s", (username,))
            row = cur.fetchone()
            return self._row_to_user(row) if row else None

    def create_user(self, username, password, role, linked_id, full_name, enrolled_by):
        if role not in ("admin", "doctor", "patient"):
            raise ValueError("invalid role")
        with self._conn() as c, c.cursor() as cur:
            if role == "patient":
                cur.execute("SELECT 1 FROM patients WHERE patient_id=%s", (linked_id,))
                if not cur.fetchone():
                    raise ValueError(f"unknown patient_id {linked_id}")
            try:
                cur.execute(
                    "INSERT INTO app_users (username,password_hash,role,linked_id,full_name,enrolled_by) "
                    "VALUES (%s,%s,%s,%s,%s,%s) RETURNING user_id",
                    (username, hash_password(password), role, linked_id, full_name, enrolled_by))
                uid = cur.fetchone()[0]
                c.commit()
            except self._psycopg2.errors.UniqueViolation:
                raise ValueError("username already exists")
        return User(uid, username, role, linked_id, full_name, True)

    def list_users(self):
        with self._conn() as c, c.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
            cur.execute("SELECT user_id,username,role,linked_id,full_name,active,enrolled_by,enrolled_at "
                        "FROM app_users ORDER BY user_id")
            return [dict(r, enrolled_at=str(r["enrolled_at"])) for r in cur.fetchall()]

    def list_patients(self):
        with self._conn() as c, c.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT p.patient_id, p.full_name, p.gender,
                       date_part('year', age(p.dob))::int AS age,
                       COALESCE(array_agg(DISTINCT c.icd10_code) FILTER (WHERE c.icd10_code IS NOT NULL), '{}') AS icd_codes
                FROM patients p LEFT JOIN conditions c ON c.patient_id = p.patient_id
                GROUP BY p.patient_id, p.full_name, p.gender, p.dob
                ORDER BY p.patient_id
            """)
            return [dict(r, conditions=list(r.pop("icd_codes"))) for r in cur.fetchall()]

    def get_patient(self, patient_id):
        with self._conn() as c, c.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
            cur.execute("SELECT patient_id, full_name, gender, dob, blood_type, city "
                        "FROM patients WHERE patient_id=%s", (patient_id,))
            p = cur.fetchone()
            if not p:
                return None
            cur.execute("SELECT icd10_code, description, status, onset_date FROM conditions WHERE patient_id=%s", (patient_id,))
            conds = [dict(r, onset_date=str(r["onset_date"])) for r in cur.fetchall()]
            cur.execute("""
                SELECT o.loinc_code, o.display_name, o.value, o.unit, o.obs_date
                FROM observations o JOIN encounters e ON o.enc_id=e.enc_id
                WHERE e.patient_id=%s ORDER BY o.obs_date DESC
            """, (patient_id,))
            obs = [dict(r, value=float(r["value"]) if r["value"] is not None else None,
                        obs_date=str(r["obs_date"])) for r in cur.fetchall()]
            meds = self._medications(patient_id)
            return {**dict(p, dob=str(p["dob"])), "conditions": conds,
                    "observations": obs, "medications": meds}

    def _medications(self, patient_id):
        """Best-effort: medications schema varies; never let it break a patient read."""
        for q in ("SELECT * FROM medications WHERE patient_id=%s",
                  "SELECT m.* FROM medications m JOIN encounters e ON m.enc_id=e.enc_id "
                  "WHERE e.patient_id=%s"):
            try:
                with self._conn() as c, c.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
                    cur.execute(q, (patient_id,))
                    return [dict(r) for r in cur.fetchall()]
            except Exception:
                continue
        return []

    def audit(self, user_name, action, table_name, record_id):
        try:
            with self._conn() as c, c.cursor() as cur:
                cur.execute("INSERT INTO audit_log (user_name,action,table_name,record_id) "
                            "VALUES (%s,%s,%s,%s)", (user_name, action, table_name, record_id))
                c.commit()
        except Exception:
            pass  # never let audit writes break a core request

    def list_audit(self, limit=100):
        with self._conn() as c, c.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
            cur.execute("SELECT user_name,action,table_name,record_id,accessed_at "
                        "FROM audit_log ORDER BY accessed_at DESC LIMIT %s", (limit,))
            return [dict(r, accessed_at=str(r["accessed_at"])) for r in cur.fetchall()]


def build_store():
    """Factory: in-memory if MEDITECH_DEMO=1, else Postgres."""
    if os.environ.get("MEDITECH_DEMO") == "1":
        return InMemoryStore(), "in-memory demo"
    return PostgresStore(), "postgres"
