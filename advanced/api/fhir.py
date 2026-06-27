"""
fhir.py — map internal records to FHIR R4 resources with proper terminology.

Supported resources (educational subset, aligned with HL7 FHIR R4):
  • Patient            — demographics (identifier, name, gender, birthDate, address)
  • Observation        — vitals / labs, coded with LOINC, valueQuantity (UCUM)
  • Condition          — diagnoses, coded with ICD-10 (SNOMED slot ready)
  • MedicationRequest  — medication orders, coded with RxNorm

Terminology systems use the canonical FHIR URIs so the resources validate against
standard tooling. This is not a full FHIR server, but the resource shapes, codings,
Bundle, and CapabilityStatement follow the R4 specification.
"""

from typing import Dict, List, Optional

# ── canonical terminology system URIs ────────────────────────────────────────
SYS_LOINC = "http://loinc.org"
SYS_ICD10 = "http://hl7.org/fhir/sid/icd-10"
SYS_SNOMED = "http://snomed.info/sct"
SYS_RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
SYS_UCUM = "http://unitsofmeasure.org"
SYS_MRN = "urn:bch:mrn"

_GENDER = {"M": "male", "F": "female"}

# LOINC codes for the common observations in this dataset (display-name → LOINC)
_LOINC = {
    "hba1c": "4548-4", "blood glucose": "2339-0", "glucose": "2339-0",
    "systolic bp": "8480-6", "diastolic bp": "8462-4", "blood pressure": "85354-9",
    "egfr": "33914-3", "creatinine": "2160-0", "heart rate": "8867-4",
    "spo2": "59408-5", "temperature": "8310-5", "respiratory rate": "9279-1",
    "ldl": "13457-7", "hdl": "2085-9", "total cholesterol": "2093-3",
    "hemoglobin": "718-7", "potassium": "2823-3", "sodium": "2951-2",
}


def _loinc_for(name: str) -> Optional[str]:
    return _LOINC.get((name or "").strip().lower())


def _split_name(full: str):
    full = (full or "").strip()
    if not full:
        return "", ""
    parts = full.split()
    return parts[0], (parts[-1] if len(parts) > 1 else "")


def _get(d: Dict, *names):
    """Case-insensitive flexible field lookup (robust to schema variation)."""
    low = {k.lower(): v for k, v in d.items()}
    for n in names:
        if n in low and low[n] not in (None, ""):
            return low[n]
    return None


# ── individual resources ─────────────────────────────────────────────────────

def to_fhir_patient(p: Dict) -> Dict:
    name = (p.get("full_name") or "").strip()
    given, family = _split_name(name)
    res = {
        "resourceType": "Patient",
        "id": p.get("patient_id"),
        "identifier": [{"use": "usual", "system": SYS_MRN, "value": p.get("patient_id")}],
        "active": True,
        "name": [{"use": "official", "text": name,
                  "family": family, "given": [given] if given else []}],
        "gender": _GENDER.get((p.get("gender") or "").upper(), "unknown"),
    }
    if p.get("dob"):
        res["birthDate"] = str(p["dob"])
    if p.get("city"):
        res["address"] = [{"use": "home", "city": p["city"], "country": "India"}]
    if p.get("phone"):
        res["telecom"] = [{"system": "phone", "value": p["phone"], "use": "mobile"}]
    return res


def to_fhir_observation(o: Dict, pid: str) -> Dict:
    name = o.get("name") or o.get("display_name") or ""
    loinc = o.get("loinc_code") or _loinc_for(name)
    coding = [{"system": SYS_LOINC, "code": loinc, "display": name}] if loinc else []
    res = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "vital-signs"}]}],
        "code": {"coding": coding, "text": name},
        "subject": {"reference": f"Patient/{pid}"},
    }
    if o.get("obs_date"):
        res["effectiveDateTime"] = str(o["obs_date"])
    if o.get("value") is not None:
        res["valueQuantity"] = {"value": o.get("value"), "unit": o.get("unit", ""),
                                "system": SYS_UCUM, "code": o.get("unit", "")}
    flag = o.get("flag")
    if flag:
        fmap = {"H": ("H", "High"), "L": ("L", "Low"), "N": ("N", "Normal")}
        code, disp = fmap.get(flag, (flag, flag))
        res["interpretation"] = [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
            "code": code, "display": disp}]}]
    return res


def to_fhir_condition(c, pid: str) -> Dict:
    if isinstance(c, str):
        # InMemory conditions look like "E11.9 Type 2 Diabetes Mellitus"
        parts = c.split(None, 1)
        code = parts[0] if parts and any(ch.isdigit() for ch in parts[0]) else ""
        text = parts[1] if code and len(parts) > 1 else c
    else:
        code = c.get("icd10_code", "")
        text = c.get("description", code)
    coding = [{"system": SYS_ICD10, "code": code, "display": text}] if code else []
    res = {
        "resourceType": "Condition",
        "clinicalStatus": {"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
            "code": (c.get("status", "active") if isinstance(c, dict) else "active")}]},
        "code": {"coding": coding, "text": str(text)},
        "subject": {"reference": f"Patient/{pid}"},
    }
    if isinstance(c, dict) and c.get("onset_date"):
        res["onsetDateTime"] = str(c["onset_date"])
    return res


def to_fhir_medication_request(m: Dict, pid: str) -> Dict:
    name = _get(m, "drug_name", "name", "medication", "display_name") or "Medication"
    rxnorm = _get(m, "rxnorm_code", "rxnorm", "code")
    dose = _get(m, "dose", "dosage", "sig")
    freq = _get(m, "frequency", "freq")
    status = (_get(m, "status") or "active")
    coding = [{"system": SYS_RXNORM, "code": str(rxnorm), "display": name}] if rxnorm else []
    res = {
        "resourceType": "MedicationRequest",
        "status": status,
        "intent": "order",
        "medicationCodeableConcept": {"coding": coding, "text": name},
        "subject": {"reference": f"Patient/{pid}"},
    }
    if dose or freq:
        res["dosageInstruction"] = [{"text": " ".join(str(x) for x in (dose, freq) if x)}]
    return res


# ── bundles & search ─────────────────────────────────────────────────────────

def _bundle(entries: List[Dict], btype: str = "searchset") -> Dict:
    return {"resourceType": "Bundle", "type": btype,
            "total": len(entries),
            "entry": [{"resource": r} for r in entries]}


def observations_for(p: Dict) -> List[Dict]:
    pid = p.get("patient_id")
    return [to_fhir_observation(o, pid) for o in (p.get("observations") or [])]


def conditions_for(p: Dict) -> List[Dict]:
    pid = p.get("patient_id")
    return [to_fhir_condition(c, pid) for c in (p.get("conditions") or [])]


def medication_requests_for(p: Dict) -> List[Dict]:
    pid = p.get("patient_id")
    return [to_fhir_medication_request(m, pid) for m in (p.get("medications") or [])]


def search_bundle(p: Dict, resource_type: str) -> Dict:
    rt = resource_type.lower()
    if rt == "observation":
        return _bundle(observations_for(p))
    if rt == "condition":
        return _bundle(conditions_for(p))
    if rt == "medicationrequest":
        return _bundle(medication_requests_for(p))
    if rt == "patient":
        return _bundle([to_fhir_patient(p)])
    raise ValueError(f"unsupported resource type '{resource_type}'")


def to_fhir_bundle(p: Dict) -> Dict:
    """Patient $everything — Patient + Conditions + Observations + MedicationRequests."""
    entries = [to_fhir_patient(p)]
    entries += conditions_for(p)
    entries += observations_for(p)
    entries += medication_requests_for(p)
    return _bundle(entries)


def capability_statement() -> Dict:
    """Minimal FHIR R4 CapabilityStatement describing supported resources."""
    def res(name, interactions):
        return {"type": name, "interaction": [{"code": i} for i in interactions]}
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json"],
        "software": {"name": "Bangalore City Hospital — Meditech Lab FHIR facade"},
        "rest": [{
            "mode": "server",
            "resource": [
                res("Patient", ["read", "search-type"]),
                res("Observation", ["read", "search-type", "create"]),
                res("Condition", ["search-type"]),
                res("MedicationRequest", ["search-type"]),
            ],
            "operation": [{"name": "everything",
                           "definition": "http://hl7.org/fhir/OperationDefinition/Patient-everything"}],
        }],
    }
