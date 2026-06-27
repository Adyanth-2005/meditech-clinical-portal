"""
setup_services.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One-shot setup script.  Run AFTER  docker compose up -d.
Loads mock data into Elasticsearch, creates Kibana index
patterns, and creates MinIO buckets with sample files.

Prerequisites:  pip install requests boto3
Run:            python3 setup_services.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import requests, json, time, sys, io

ES_URL     = "http://localhost:9200"
KIBANA_URL = "http://localhost:5601"
MINIO_URL  = "http://localhost:9000"
MINIO_KEY  = "admin"
MINIO_SEC  = "MeditechSecret123!"


# ─── helpers ─────────────────────────────────────────────────────────────────

def ok(msg):   print(f"  \033[32m✓\033[0m {msg}")
def err(msg):  print(f"  \033[31m✗\033[0m {msg}")
def info(msg): print(f"  \033[36mℹ\033[0m {msg}")
def hdr(msg):  print(f"\n\033[1m── {msg} {'─'*(52-len(msg))}\033[0m")

def wait_for(url, label, timeout=90):
    print(f"  Waiting for {label} ", end='', flush=True)
    for _ in range(timeout // 3):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code < 500:
                print(" ready")
                return True
        except Exception:
            pass
        print('.', end='', flush=True)
        time.sleep(3)
    print(" TIMEOUT")
    return False


# ─── 1. Elasticsearch ────────────────────────────────────────────────────────

PATIENTS_DOCS = [
    {"patient_id":"PT-001","mrn":"MRN-10001","full_name":"Rajan Menon",
     "dob":"1970-04-12","gender":"M","blood_type":"B+","city":"Bangalore",
     "age":54,"dept":"Endocrinology","conditions":["T2DM","Hypertension","Diabetic Nephropathy"]},
    {"patient_id":"PT-002","mrn":"MRN-10002","full_name":"Lakshmi Nair",
     "dob":"1985-09-22","gender":"F","blood_type":"O+","city":"Mysuru",
     "age":39,"dept":"Cardiology","conditions":["Heart Failure","Hypertension"]},
    {"patient_id":"PT-003","mrn":"MRN-10003","full_name":"Suresh Patel",
     "dob":"1955-01-30","gender":"M","blood_type":"A-","city":"Bangalore",
     "age":69,"dept":"Nephrology","conditions":["CKD Stage 3","Hypertension"]},
    {"patient_id":"PT-004","mrn":"MRN-10004","full_name":"Priya Iyer",
     "dob":"1962-07-15","gender":"F","blood_type":"AB+","city":"Hubli",
     "age":62,"dept":"Pulmonology","conditions":["COPD","Heart Failure"]},
    {"patient_id":"PT-005","mrn":"MRN-10005","full_name":"Arjun Krishnan",
     "dob":"1990-03-08","gender":"M","blood_type":"O-","city":"Bangalore",
     "age":34,"dept":"Orthopedics","conditions":["Low Back Pain"]},
    {"patient_id":"PT-006","mrn":"MRN-10006","full_name":"Meena Reddy",
     "dob":"1978-11-25","gender":"F","blood_type":"B-","city":"Hyderabad",
     "age":46,"dept":"Endocrinology","conditions":["T2DM"]},
    {"patient_id":"PT-007","mrn":"MRN-10007","full_name":"Vikram Singh",
     "dob":"1948-06-02","gender":"M","blood_type":"A+","city":"Delhi",
     "age":76,"dept":"Cardiology","conditions":["Atherosclerotic HD","Hypertension"]},
    {"patient_id":"PT-008","mrn":"MRN-10008","full_name":"Ananya Das",
     "dob":"2001-02-14","gender":"F","blood_type":"O+","city":"Kolkata",
     "age":23,"dept":"General Medicine","conditions":["Pneumonia"]},
]

OBS_DOCS = [
    # Rajan
    {"patient_id":"PT-001","patient_name":"Rajan Menon","loinc":"4548-4",
     "display_name":"HbA1c","value":7.2,"unit":"%","flag":"H","obs_date":"2018-03-15","dept":"Endocrinology"},
    {"patient_id":"PT-001","patient_name":"Rajan Menon","loinc":"4548-4",
     "display_name":"HbA1c","value":7.8,"unit":"%","flag":"H","obs_date":"2019-06-20","dept":"Endocrinology"},
    {"patient_id":"PT-001","patient_name":"Rajan Menon","loinc":"4548-4",
     "display_name":"HbA1c","value":8.4,"unit":"%","flag":"H","obs_date":"2023-02-18","dept":"Endocrinology"},
    {"patient_id":"PT-001","patient_name":"Rajan Menon","loinc":"4548-4",
     "display_name":"HbA1c","value":8.9,"unit":"%","flag":"H","obs_date":"2024-06-03","dept":"Endocrinology"},
    {"patient_id":"PT-001","patient_name":"Rajan Menon","loinc":"2345-7",
     "display_name":"Blood Glucose","value":182,"unit":"mg/dL","flag":"H","obs_date":"2024-06-03","dept":"Endocrinology"},
    {"patient_id":"PT-001","patient_name":"Rajan Menon","loinc":"8480-6",
     "display_name":"Systolic BP","value":148,"unit":"mmHg","flag":"H","obs_date":"2024-06-03","dept":"Endocrinology"},
    {"patient_id":"PT-001","patient_name":"Rajan Menon","loinc":"33914-3",
     "display_name":"eGFR","value":68,"unit":"mL/min","flag":"L","obs_date":"2024-06-03","dept":"Endocrinology"},
    # Lakshmi
    {"patient_id":"PT-002","patient_name":"Lakshmi Nair","loinc":"8806-2",
     "display_name":"Echo EF","value":60,"unit":"%","flag":"N","obs_date":"2020-08-10","dept":"Cardiology"},
    {"patient_id":"PT-002","patient_name":"Lakshmi Nair","loinc":"8806-2",
     "display_name":"Echo EF","value":42,"unit":"%","flag":"L","obs_date":"2022-01-14","dept":"Cardiology"},
    {"patient_id":"PT-002","patient_name":"Lakshmi Nair","loinc":"8806-2",
     "display_name":"Echo EF","value":48,"unit":"%","flag":"L","obs_date":"2023-09-25","dept":"Cardiology"},
    # Suresh
    {"patient_id":"PT-003","patient_name":"Suresh Patel","loinc":"2160-0",
     "display_name":"Creatinine","value":1.8,"unit":"mg/dL","flag":"H","obs_date":"2019-05-12","dept":"Nephrology"},
    {"patient_id":"PT-003","patient_name":"Suresh Patel","loinc":"2160-0",
     "display_name":"Creatinine","value":2.4,"unit":"mg/dL","flag":"H","obs_date":"2024-03-08","dept":"Nephrology"},
    # Priya
    {"patient_id":"PT-004","patient_name":"Priya Iyer","loinc":"2708-6",
     "display_name":"SpO2","value":88,"unit":"%","flag":"L","obs_date":"2023-11-20","dept":"Pulmonology"},
    {"patient_id":"PT-004","patient_name":"Priya Iyer","loinc":"8310-5",
     "display_name":"Body Temp","value":38.9,"unit":"C","flag":"H","obs_date":"2023-11-20","dept":"Pulmonology"},
    # Meena
    {"patient_id":"PT-006","patient_name":"Meena Reddy","loinc":"4548-4",
     "display_name":"HbA1c","value":9.2,"unit":"%","flag":"H","obs_date":"2022-07-05","dept":"Endocrinology"},
    # Vikram
    {"patient_id":"PT-007","patient_name":"Vikram Singh","loinc":"10839-9",
     "display_name":"Troponin I","value":2.8,"unit":"ng/mL","flag":"H","obs_date":"2024-05-18","dept":"Cardiology"},
    {"patient_id":"PT-007","patient_name":"Vikram Singh","loinc":"8480-6",
     "display_name":"Systolic BP","value":90,"unit":"mmHg","flag":"L","obs_date":"2024-05-18","dept":"Cardiology"},
]

CONDITIONS_DOCS = [
    {"patient_id":"PT-001","patient_name":"Rajan Menon","icd10":"E11.65",
     "description":"T2DM with Hyperglycaemia","icd10_chapter":"E","status":"active","onset":"2024-06-03"},
    {"patient_id":"PT-001","patient_name":"Rajan Menon","icd10":"I10",
     "description":"Essential Hypertension","icd10_chapter":"I","status":"chronic","onset":"2021-11-05"},
    {"patient_id":"PT-001","patient_name":"Rajan Menon","icd10":"N08",
     "description":"Diabetic Nephropathy","icd10_chapter":"N","status":"active","onset":"2024-06-03"},
    {"patient_id":"PT-002","patient_name":"Lakshmi Nair","icd10":"I50.9",
     "description":"Heart Failure","icd10_chapter":"I","status":"chronic","onset":"2022-01-14"},
    {"patient_id":"PT-002","patient_name":"Lakshmi Nair","icd10":"I10",
     "description":"Essential Hypertension","icd10_chapter":"I","status":"chronic","onset":"2020-08-10"},
    {"patient_id":"PT-003","patient_name":"Suresh Patel","icd10":"N18.3",
     "description":"Chronic Kidney Disease Stage 3","icd10_chapter":"N","status":"chronic","onset":"2019-05-12"},
    {"patient_id":"PT-003","patient_name":"Suresh Patel","icd10":"I10",
     "description":"Essential Hypertension","icd10_chapter":"I","status":"chronic","onset":"2019-05-12"},
    {"patient_id":"PT-004","patient_name":"Priya Iyer","icd10":"J44.1",
     "description":"COPD with Acute Exacerbation","icd10_chapter":"J","status":"active","onset":"2023-11-20"},
    {"patient_id":"PT-004","patient_name":"Priya Iyer","icd10":"I50.9",
     "description":"Heart Failure","icd10_chapter":"I","status":"active","onset":"2023-11-20"},
    {"patient_id":"PT-006","patient_name":"Meena Reddy","icd10":"E11.65",
     "description":"T2DM with Hyperglycaemia","icd10_chapter":"E","status":"active","onset":"2022-07-05"},
    {"patient_id":"PT-007","patient_name":"Vikram Singh","icd10":"I25.10",
     "description":"Atherosclerotic Heart Disease","icd10_chapter":"I","status":"active","onset":"2024-05-18"},
    {"patient_id":"PT-007","patient_name":"Vikram Singh","icd10":"I10",
     "description":"Essential Hypertension","icd10_chapter":"I","status":"chronic","onset":"2024-05-18"},
    {"patient_id":"PT-008","patient_name":"Ananya Das","icd10":"J18.9",
     "description":"Community-acquired Pneumonia","icd10_chapter":"J","status":"resolved","onset":"2024-02-28"},
]

def setup_elasticsearch():
    hdr("1. Elasticsearch")

    if not wait_for(f"{ES_URL}/_cluster/health", "Elasticsearch"):
        err("Elasticsearch not responding — is Docker running?")
        return False

    indices = {
        "ehr-patients": {
            "mappings": {"properties": {
                "patient_id":  {"type": "keyword"},
                "mrn":         {"type": "keyword"},
                "full_name":   {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "gender":      {"type": "keyword"},
                "blood_type":  {"type": "keyword"},
                "city":        {"type": "keyword"},
                "age":         {"type": "integer"},
                "dept":        {"type": "keyword"},
                "conditions":  {"type": "keyword"},
                "dob":         {"type": "date"},
            }}
        },
        "ehr-observations": {
            "mappings": {"properties": {
                "patient_id":   {"type": "keyword"},
                "patient_name": {"type": "keyword"},
                "loinc":        {"type": "keyword"},
                "display_name": {"type": "keyword"},
                "value":        {"type": "float"},
                "unit":         {"type": "keyword"},
                "flag":         {"type": "keyword"},
                "obs_date":     {"type": "date"},
                "dept":         {"type": "keyword"},
            }}
        },
        "ehr-conditions": {
            "mappings": {"properties": {
                "patient_id":    {"type": "keyword"},
                "patient_name":  {"type": "keyword"},
                "icd10":         {"type": "keyword"},
                "icd10_chapter": {"type": "keyword"},
                "description":   {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "status":        {"type": "keyword"},
                "onset":         {"type": "date"},
            }}
        },
        "hl7-messages": {
            "mappings": {"properties": {
                "@timestamp":   {"type": "date"},
                "msg_id":       {"type": "keyword"},
                "msg_type":     {"type": "keyword"},
                "patient_id":   {"type": "keyword"},
                "patient_name": {"type": "keyword"},
                "department":   {"type": "keyword"},
                "conditions":   {"type": "keyword"},
                "icd10_code":   {"type": "keyword"},
                "hospital":     {"type": "keyword"},
                "source":       {"type": "keyword"},
                "segments":     {"type": "integer"},
                "nifi_ok":      {"type": "boolean"},
            }}
        },
    }

    # Create indices
    for idx, body in indices.items():
        r = requests.delete(f"{ES_URL}/{idx}", timeout=5)  # clean slate
        r = requests.put(f"{ES_URL}/{idx}", json=body, timeout=5)
        if r.status_code in (200, 201):
            ok(f"Index created: {idx}")
        else:
            err(f"Index {idx}: {r.text[:80]}")

    # Bulk load
    def bulk_load(index, docs):
        body = ""
        for d in docs:
            body += json.dumps({"index": {"_index": index}}) + "\n"
            body += json.dumps(d) + "\n"
        r = requests.post(f"{ES_URL}/_bulk",
                          data=body,
                          headers={"Content-Type": "application/x-ndjson"},
                          timeout=10)
        if r.status_code == 200 and not r.json().get("errors"):
            ok(f"  Loaded {len(docs)} documents → {index}")
        else:
            err(f"  Bulk load {index}: {r.text[:120]}")

    bulk_load("ehr-patients",    PATIENTS_DOCS)
    bulk_load("ehr-observations", OBS_DOCS)
    bulk_load("ehr-conditions",   CONDITIONS_DOCS)
    return True


# ─── 2. Kibana ───────────────────────────────────────────────────────────────

def setup_kibana():
    hdr("2. Kibana")

    if not wait_for(f"{KIBANA_URL}/api/status", "Kibana"):
        err("Kibana not responding — is Docker running?")
        return False

    # Wait for Kibana to be fully initialised
    for _ in range(20):
        try:
            r = requests.get(f"{KIBANA_URL}/api/status", timeout=3)
            state = r.json().get("status", {}).get("overall", {}).get("level", "")
            if state == "available":
                break
        except Exception:
            pass
        time.sleep(3)

    headers = {"kbn-xsrf": "true", "Content-Type": "application/json"}

    # Create data views (index patterns) for each index
    data_views = [
        {"title": "ehr-patients",     "name": "EHR Patients"},
        {"title": "ehr-observations", "name": "EHR Observations", "timeFieldName": "obs_date"},
        {"title": "ehr-conditions",   "name": "EHR Conditions",  "timeFieldName": "onset"},
        {"title": "hl7-messages",     "name": "HL7 Messages",    "timeFieldName": "@timestamp"},
        {"title": "ehr-*",            "name": "EHR (all)",       "timeFieldName": "obs_date"},
    ]

    for dv in data_views:
        body = {"data_view": {
            "title": dv["title"],
            "name":  dv["name"],
        }}
        if "timeFieldName" in dv:
            body["data_view"]["timeFieldName"] = dv["timeFieldName"]

        r = requests.post(f"{KIBANA_URL}/api/data_views/data_view",
                          headers=headers, json=body, timeout=10)
        if r.status_code in (200, 201):
            ok(f"Data view: {dv['name']}  ({dv['title']})")
        elif "Duplicate" in r.text:
            info(f"Data view already exists: {dv['name']}")
        else:
            err(f"Data view {dv['name']}: {r.text[:100]}")

    info("Open Kibana → Analytics → Discover to browse data")
    info("Open Kibana → Analytics → Lens to build visualizations")
    info("Suggested first query: index=ehr-observations, filter flag=H (abnormal results)")
    return True


# ─── 3. MinIO ────────────────────────────────────────────────────────────────

def setup_minio():
    hdr("3. MinIO")

    try:
        import boto3
        from botocore.client import Config
    except ImportError:
        err("boto3 not installed — run: pip install boto3")
        return False

    if not wait_for(f"{MINIO_URL}/minio/health/live", "MinIO"):
        err("MinIO not responding — is Docker running?")
        return False

    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_URL,
        aws_access_key_id=MINIO_KEY,
        aws_secret_access_key=MINIO_SEC,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

    buckets = [
        "dicom-imaging",
        "discharge-reports",
        "hl7-archive",
        "fhir-responses",
        "lab-exports",
    ]
    for b in buckets:
        try:
            s3.create_bucket(Bucket=b)
            ok(f"Bucket created: {b}")
        except Exception as e:
            if "BucketAlreadyOwnedByYou" in str(e) or "BucketAlreadyExists" in str(e):
                info(f"Bucket exists:  {b}")
            else:
                err(f"Bucket {b}: {e}")

    # ── Upload sample files ───────────────────────────────────────────────────
    info("Uploading sample files…")

    # Discharge reports (text simulating PDF)
    discharge_samples = [
        ("PT-001", "ENC-005", "2024-06-03", "Rajan Menon",
         "T2DM + Hypertension + Diabetic Nephropathy",
         "Metformin 1000mg BD, Glipizide 5mg OD, Amlodipine 5mg OD, Ramipril 2.5mg OD"),
        ("PT-002", "ENC-007", "2022-01-16", "Lakshmi Nair",
         "Heart Failure with reduced EF (Echo EF 42%)",
         "Furosemide 40mg OD, Carvedilol 6.25mg BD"),
        ("PT-004", "ENC-011", "2023-11-25", "Priya Iyer",
         "COPD Exacerbation + Hypoxia (SpO2 88%)",
         "Salbutamol nebulisation, Carvedilol 3.125mg BD, O2 therapy"),
        ("PT-007", "ENC-014", "2024-05-22", "Vikram Singh",
         "NSTEMI — Troponin I 2.8 ng/mL — PCI performed",
         "Aspirin 325mg, Ticagrelor 90mg BD, Atorvastatin 40mg OD"),
    ]

    for pid, enc, date, name, dx, meds in discharge_samples:
        content = f"""BANGALORE CITY HOSPITAL
DISCHARGE SUMMARY
═══════════════════════════════════════════════════════

Patient Name   : {name}
Patient ID     : {pid}
Encounter      : {enc}
Discharge Date : {date}

PRINCIPAL DIAGNOSIS
───────────────────
{dx}

MEDICATIONS ON DISCHARGE
────────────────────────
{meds}

FOLLOW-UP
─────────
Review in 4 weeks. Repeat relevant investigations as advised.

───────────────────────────────────────────────────────
Attending Physician signature on file
Bangalore City Hospital · Healthcare Excellence Since 1982
""".encode('utf-8')
        key = f"{pid}/{enc}_discharge.txt"
        s3.put_object(Bucket="discharge-reports", Key=key,
                      Body=content, ContentType="text/plain")
        ok(f"  discharge-reports/{key}")

    # HL7 archive files
    hl7_samples = [
        ("2024/06/ENC-005_ADT_A01.hl7",
         b"MSH|^~\\&|HIS|BCH|ARCHIVE|BCH|20240603120000||ADT^A01|MSG001001|P|2.5\r"
         b"PID|1||PT-001^^^BCH||Menon^Rajan||19700412|M\r"
         b"PV1|1|I|Endocrinology^Room 12^Bed 2|||||||Sharma^Priya\r"),
        ("2024/06/ENC-005_ORU_R01.hl7",
         b"MSH|^~\\&|LIS|BCH|ARCHIVE|BCH|20240603140000||ORU^R01|MSG001002|P|2.5\r"
         b"PID|1||PT-001^^^BCH||Menon^Rajan||19700412|M\r"
         b"OBR|1|||LAB^Laboratory Panel^L\r"
         b"OBX|1|NM|4548-4^HbA1c^LN||8.9|%|<7.0||H|||F\r"
         b"OBX|2|NM|2345-7^Blood Glucose^LN||182|mg/dL|70-99||H|||F\r"),
        ("2024/05/ENC-014_ADT_A01.hl7",
         b"MSH|^~\\&|HIS|BCH|ARCHIVE|BCH|20240518090000||ADT^A01|MSG002001|P|2.5\r"
         b"PID|1||PT-007^^^BCH||Singh^Vikram||19480602|M\r"
         b"PV1|1|I|Cardiology^CCU Bed 2|||||||Rao^Suresh\r"
         b"DG1|1||I25.10^Atherosclerotic HD^ICD10\r"),
    ]
    for key, content in hl7_samples:
        s3.put_object(Bucket="hl7-archive", Key=key,
                      Body=content, ContentType="application/hl7-v2")
        ok(f"  hl7-archive/{key}")

    # FHIR JSON response (Patient resource)
    fhir_patient = {
        "resourceType": "Patient",
        "id": "PT-001",
        "identifier": [{"system": "urn:oid:BCH", "value": "MRN-10001"}],
        "name": [{"family": "Menon", "given": ["Rajan"]}],
        "birthDate": "1970-04-12",
        "gender": "male",
        "address": [{"city": "Bangalore", "country": "India"}],
    }
    s3.put_object(Bucket="fhir-responses",
                  Key="PT-001/patient_resource.json",
                  Body=json.dumps(fhir_patient, indent=2).encode(),
                  ContentType="application/fhir+json")
    ok("  fhir-responses/PT-001/patient_resource.json")

    # Lab CSV export
    csv = (
        "patient_id,patient_name,loinc,test_name,value,unit,flag,date\n"
        "PT-001,Rajan Menon,4548-4,HbA1c,8.9,%,H,2024-06-03\n"
        "PT-001,Rajan Menon,2345-7,Blood Glucose,182,mg/dL,H,2024-06-03\n"
        "PT-002,Lakshmi Nair,8806-2,Echo EF,42,%,L,2022-01-14\n"
        "PT-004,Priya Iyer,2708-6,SpO2,88,%,L,2023-11-20\n"
        "PT-006,Meena Reddy,4548-4,HbA1c,9.2,%,H,2022-07-05\n"
        "PT-007,Vikram Singh,10839-9,Troponin I,2.8,ng/mL,H,2024-05-18\n"
    )
    s3.put_object(Bucket="lab-exports",
                  Key="2024/Q2_critical_labs.csv",
                  Body=csv.encode(),
                  ContentType="text/csv")
    ok("  lab-exports/2024/Q2_critical_labs.csv")

    # DICOM placeholder
    dicom_placeholder = (
        b"DICOM placeholder - replace with real .dcm files from your PACS\n"
        b"Patient: Rajan Menon (PT-001)\n"
        b"Study: Chest X-Ray  ENC-005  2024-06-03\n"
        b"Modality: CR\n"
    )
    s3.put_object(Bucket="dicom-imaging",
                  Key="PT-001/ENC-005/chest_xray.dcm.placeholder",
                  Body=dicom_placeholder,
                  ContentType="application/octet-stream")
    ok("  dicom-imaging/PT-001/ENC-005/chest_xray.dcm.placeholder")

    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n\033[1m" + "═" * 56)
    print("  Bangalore City Hospital — Service Setup")
    print("  docker compose up -d  must already be running")
    print("═" * 56 + "\033[0m")

    es_ok     = setup_elasticsearch()
    kib_ok    = setup_kibana()
    minio_ok  = setup_minio()

    print("\n" + "═" * 56)
    print("  SUMMARY")
    print("─" * 56)
    print(f"  Elasticsearch : {'✓ ready' if es_ok    else '✗ failed'}")
    print(f"  Kibana        : {'✓ ready' if kib_ok   else '✗ failed'}")
    print(f"  MinIO         : {'✓ ready' if minio_ok else '✗ failed'}")
    print("─" * 56)
    print("  NEXT STEPS:")
    print("  1. python3 setup_nifi.py          (create pipeline)")
    print("  2. python3 hl7_sender.py          (open sender UI)")
    print("  3. https://localhost:8443/nifi    (see messages flow)")
    print("  4. http://localhost:5601          (Kibana dashboards)")
    print("  5. http://localhost:9001          (MinIO file browser)")
    print("═" * 56 + "\n")


if __name__ == "__main__":
    main()
