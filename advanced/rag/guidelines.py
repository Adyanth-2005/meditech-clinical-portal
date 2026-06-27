"""
guidelines.py — builds the RAG corpus (pure functions, no network).

Two kinds of chunks, each tagged for RBAC-aware retrieval:
  • guideline chunks : source_type="guideline", patient_id=""  (everyone may read)
  • ehr chunks       : source_type="ehr",       patient_id="PT-00x" (scoped)

The guideline text is SYNTHETIC and for education only — it is NOT copied from
ACC/AHA/KDIGO/GOLD or any copyrighted source. It paraphrases widely-known
clinical thresholds in our own words so the lab has something to retrieve.
"""

from typing import List, Dict

EMBED_DIM = 768  # nomic-embed-text output dimension


# ── synthetic guideline corpus (paraphrased, educational) ────────────────────

SYNTHETIC_GUIDELINES: List[Dict] = [
    {"title": "Type 2 Diabetes — glycaemic targets", "department": "Endocrinology",
     "text": "For most non-pregnant adults with type 2 diabetes a reasonable HbA1c "
             "goal is below 7 percent. A value at or above 6.5 percent supports the "
             "diagnosis. Fasting plasma glucose is generally kept in the 80 to 130 mg/dL "
             "range. Persistently high HbA1c such as 8 to 9 percent indicates poor "
             "control and warrants intensification of therapy and review of adherence."},
    {"title": "Type 2 Diabetes — first-line therapy", "department": "Endocrinology",
     "text": "Metformin is the usual first-line agent for type 2 diabetes alongside "
             "lifestyle measures. When there is established cardiovascular or kidney "
             "disease, an SGLT2 inhibitor or a GLP-1 receptor agonist is often added "
             "for organ protection independent of further glucose lowering."},
    {"title": "Heart failure with reduced ejection fraction", "department": "Cardiology",
     "text": "Heart failure with reduced ejection fraction is defined by an ejection "
             "fraction at or below 40 percent. Guideline-directed therapy combines four "
             "pillars: an ARNI or ACE inhibitor, a beta-blocker, a mineralocorticoid "
             "receptor antagonist, and an SGLT2 inhibitor. An elevated BNP supports the "
             "diagnosis and helps gauge severity."},
    {"title": "Chronic kidney disease — staging", "department": "Nephrology",
     "text": "Chronic kidney disease is staged by estimated GFR. Stage 3a is an eGFR of "
             "45 to 59 and stage 3b is 30 to 44 mL/min per 1.73 m2. A falling eGFR with a "
             "rising creatinine signals progression. ACE inhibitors or ARBs slow decline, "
             "especially when there is associated proteinuria or diabetes."},
    {"title": "Hyperkalaemia — recognition", "department": "Nephrology",
     "text": "Serum potassium above 5.0 mEq/L is hyperkalaemia; values above 6.0 are "
             "dangerous and can cause cardiac arrhythmia. In chronic kidney disease, "
             "potassium-retaining drugs should be reviewed and an ECG obtained when the "
             "level is markedly elevated."},
    {"title": "COPD exacerbation", "department": "Pulmonology",
     "text": "A COPD exacerbation is an acute worsening of breathlessness, cough or "
             "sputum. Management includes inhaled bronchodilators, a short course of oral "
             "corticosteroids, and antibiotics when sputum is purulent. Oxygen is titrated "
             "to a target saturation of about 88 to 92 percent to avoid CO2 retention."},
    {"title": "Hypertension — thresholds", "department": "Cardiology",
     "text": "An office systolic pressure at or above 140 mmHg or diastolic at or above "
             "90 mmHg indicates hypertension in most guidelines. Treatment usually starts "
             "with an ACE inhibitor or ARB, a calcium channel blocker, or a thiazide-type "
             "diuretic, with the choice guided by age and comorbidity."},
    {"title": "Acute coronary syndrome — troponin", "department": "Cardiology",
     "text": "A rising cardiac troponin above the assay's 99th percentile in the right "
             "clinical context indicates myocardial injury and may signal acute coronary "
             "syndrome. Markedly elevated troponin with chest pain and ECG changes is "
             "treated as a medical emergency."},
    {"title": "NEWS2 early-warning score", "department": "General Medicine",
     "text": "The National Early Warning Score 2 aggregates respiratory rate, oxygen "
             "saturation, supplemental oxygen, temperature, systolic pressure, heart rate "
             "and consciousness. A total of 5 or more, or any single parameter scoring 3, "
             "triggers urgent clinical review for possible deterioration or sepsis."},
    {"title": "Community-acquired pneumonia", "department": "General Medicine",
     "text": "Community-acquired pneumonia presents with fever, cough and focal chest "
             "signs. Severity is assessed with tools such as CURB-65. Empirical antibiotics "
             "are started promptly and oxygen is given when saturation is low."},
    {"title": "Diabetic kidney disease", "department": "Nephrology",
     "text": "Diabetes is a leading cause of chronic kidney disease. Albuminuria and a "
             "falling eGFR mark diabetic nephropathy. An ACE inhibitor or ARB plus an SGLT2 "
             "inhibitor slows progression. Blood pressure and glucose are controlled together, "
             "and potassium is monitored after starting renin-angiotensin blockade."},
    {"title": "Diabetic retinopathy and foot care", "department": "Endocrinology",
     "text": "Long-standing or poorly controlled diabetes damages small vessels, causing "
             "retinopathy and neuropathy. Annual eye screening and regular foot examination "
             "detect complications early. Numbness, ulcers or deformity of the foot need prompt "
             "podiatry review to prevent amputation."},
    {"title": "Insulin and hypoglycaemia", "department": "Endocrinology",
     "text": "Insulin is used when oral agents fail to reach glycaemic targets or in type 1 "
             "diabetes. Hypoglycaemia, a blood glucose below 70 mg/dL, causes sweating, tremor "
             "and confusion and is treated with fast-acting carbohydrate. Recurrent lows prompt "
             "a review of insulin dose and timing."},
    {"title": "Dyslipidaemia and statins", "department": "Cardiology",
     "text": "Raised LDL cholesterol drives atherosclerosis. A statin is first-line for "
             "lowering LDL and cardiovascular risk. High-intensity statin therapy is used after "
             "a cardiovascular event or in diabetes with risk factors. Liver enzymes and "
             "symptoms of myopathy are monitored."},
    {"title": "Atrial fibrillation and stroke prevention", "department": "Cardiology",
     "text": "Atrial fibrillation is an irregular rhythm that raises stroke risk. The "
             "CHA2DS2-VASc score estimates that risk and guides anticoagulation with a direct "
             "oral anticoagulant or warfarin. Rate or rhythm control manages symptoms. "
             "Bleeding risk is weighed before starting anticoagulation."},
    {"title": "Anticoagulation and INR monitoring", "department": "Haematology",
     "text": "Warfarin requires regular INR monitoring with a usual target range of 2.0 to "
             "3.0 for most indications. Direct oral anticoagulants need no routine INR but "
             "require dose adjustment for kidney function. Any anticoagulant raises bleeding "
             "risk, so signs of bleeding are reviewed at each visit."},
    {"title": "Asthma — assessment and stepwise therapy", "department": "Pulmonology",
     "text": "Asthma causes variable airflow obstruction with wheeze, cough and "
             "breathlessness. Inhaled corticosteroids are the controller foundation, stepped up "
             "with long-acting beta-agonists as needed. Reliever overuse signals poor control. "
             "Peak flow and symptom frequency guide adjustments."},
    {"title": "Stroke and TIA", "department": "Neurology",
     "text": "An acute stroke causes sudden focal neurological deficit. Rapid imaging "
             "distinguishes ischaemic from haemorrhagic stroke. Ischaemic stroke within the "
             "treatment window may receive thrombolysis or thrombectomy. A transient ischaemic "
             "attack is a warning that warrants urgent risk-factor management."},
    {"title": "Sepsis recognition", "department": "General Medicine",
     "text": "Sepsis is life-threatening organ dysfunction from a dysregulated response to "
             "infection. Fever, tachycardia, low blood pressure, confusion and a high NEWS2 "
             "should prompt sepsis screening. Early antibiotics, fluids and source control "
             "improve outcomes; lactate helps gauge severity."},
    {"title": "Acute kidney injury", "department": "Nephrology",
     "text": "Acute kidney injury is a rapid rise in creatinine or a fall in urine output. "
             "Common causes are dehydration, sepsis and nephrotoxic drugs. Management restores "
             "perfusion, stops offending drugs and treats the cause. Potassium and fluid "
             "balance are watched closely."},
    {"title": "Hyponatraemia", "department": "General Medicine",
     "text": "Hyponatraemia is a serum sodium below 135 mmol/L. Symptoms range from nausea "
             "and confusion to seizures when severe or rapid. Assessment of fluid status and "
             "urine osmolality guides treatment. Sodium is corrected slowly to avoid neurological "
             "harm."},
    {"title": "Thyroid disorders", "department": "Endocrinology",
     "text": "Hypothyroidism raises TSH and causes fatigue, weight gain and cold intolerance; "
             "it is treated with levothyroxine titrated to TSH. Hyperthyroidism lowers TSH with "
             "weight loss, tremor and palpitations and is managed with antithyroid drugs, "
             "radioiodine or surgery."},
    {"title": "Anaemia — initial workup", "department": "Haematology",
     "text": "Anaemia is a low haemoglobin and is classified by red-cell size. Microcytic "
             "anaemia is often iron deficiency; macrocytic suggests B12 or folate deficiency. "
             "Investigation seeks the cause, such as blood loss, before treating with iron or "
             "vitamin replacement."},
    {"title": "Venous thromboembolism", "department": "Haematology",
     "text": "Deep vein thrombosis and pulmonary embolism form the spectrum of venous "
             "thromboembolism. Unilateral leg swelling or sudden breathlessness with low oxygen "
             "raises suspicion. D-dimer and imaging confirm the diagnosis, and anticoagulation "
             "is the mainstay of treatment."},
    {"title": "Gastrointestinal bleeding", "department": "Gastroenterology",
     "text": "Upper gastrointestinal bleeding presents with vomiting blood or black stools. "
             "Resuscitation comes first, followed by endoscopy to find and treat the source. "
             "Proton pump inhibitors are used for peptic ulcer bleeding, and anticoagulants are "
             "reviewed."},
    {"title": "Liver function and abnormal LFTs", "department": "Gastroenterology",
     "text": "Liver function tests include ALT, AST, bilirubin and albumin. A hepatocellular "
             "pattern raises ALT and AST, while a cholestatic pattern raises ALP and bilirubin. "
             "Persistent abnormalities prompt evaluation for viral, alcoholic, metabolic or "
             "drug-related liver disease."},
    {"title": "Hypertensive emergency", "department": "Cardiology",
     "text": "A hypertensive emergency is severe blood pressure elevation with evidence of "
             "acute organ damage such as chest pain, breathlessness, neurological signs or "
             "kidney injury. Blood pressure is lowered in a controlled way, avoiding overly "
             "rapid reduction."},
    {"title": "Acute coronary syndrome — management", "department": "Cardiology",
     "text": "Suspected acute coronary syndrome is managed with aspirin, a second "
             "antiplatelet agent, anticoagulation and anti-anginal therapy as appropriate. "
             "ST-elevation infarction needs urgent reperfusion. Risk scores and serial troponin "
             "guide decisions, and secondary prevention follows."},
    {"title": "Obesity and lifestyle", "department": "General Medicine",
     "text": "A body mass index of 25 to 29.9 is overweight and 30 or above is obesity. "
             "Weight reduction improves blood pressure, glucose and lipids. Structured diet, "
             "physical activity and, when indicated, pharmacotherapy or surgery support "
             "sustained weight loss."},
    {"title": "Smoking cessation", "department": "General Medicine",
     "text": "Smoking is a major modifiable risk factor for cardiovascular, respiratory and "
             "malignant disease. Brief advice, nicotine replacement and pharmacotherapy improve "
             "quit rates. Stopping smoking benefits health at any age and is reinforced at every "
             "visit."},
    {"title": "Gout", "department": "Rheumatology",
     "text": "Gout is acute arthritis from urate crystal deposition, often in the big toe. "
             "Acute attacks are treated with anti-inflammatory drugs or colchicine. Recurrent "
             "attacks or high urate warrant urate-lowering therapy with adequate hydration."},
    {"title": "Electrolyte reference ranges", "department": "General Medicine",
     "text": "Typical reference ranges are sodium 135 to 145 mmol/L, potassium 3.5 to 5.0 "
             "mEq/L, and creatinine that varies with muscle mass. Values outside these ranges "
             "are interpreted in the clinical context and trended over time rather than judged "
             "on a single result."},
    {"title": "Interpreting HbA1c", "department": "Endocrinology",
     "text": "HbA1c reflects average glucose over roughly three months. Below 5.7 percent is "
             "normal, 5.7 to 6.4 percent is prediabetes, and 6.5 percent or above supports "
             "diabetes. It is less reliable in anaemia or recent blood loss."},
    {"title": "Estimating and acting on eGFR", "department": "Nephrology",
     "text": "Estimated GFR gauges kidney function from creatinine, age and sex. A value "
             "below 60 for three months or more defines chronic kidney disease. Drug doses for "
             "renally-cleared medicines are adjusted as eGFR falls, and nephrotoxins are "
             "avoided."},
    {"title": "Urinary tract infection", "department": "General Medicine",
     "text": "Lower urinary tract infection causes dysuria, frequency and urgency. "
             "Uncomplicated cases in otherwise well adults are treated with a short antibiotic "
             "course. Fever, flank pain or systemic features suggest pyelonephritis and need "
             "broader treatment."},
]


# Longer multi-section synthetic monographs (markdown headers + several
# paragraphs) — these exercise all three chunking layers. Still paraphrased /
# educational, not copied from any source.
SYNTHETIC_MONOGRAPHS: List[Dict] = [
    {"title": "Monograph — Heart Failure", "department": "Cardiology", "text":
"""# Heart Failure with Reduced Ejection Fraction

Heart failure with reduced ejection fraction is defined by an ejection fraction at
or below 40 percent. Diagnosis is supported by an elevated natriuretic peptide such
as BNP or NT-proBNP. Typical symptoms are breathlessness on exertion, fatigue, and
fluid retention with peripheral oedema.

## Pharmacological therapy

Guideline-directed medical therapy rests on four pillars. An ARNI is preferred over
an ACE inhibitor or ARB where tolerated. A beta-blocker proven in heart failure is
added and uptitrated. A mineralocorticoid receptor antagonist reduces mortality. An
SGLT2 inhibitor lowers hospitalisation and is now part of foundational therapy.

## Monitoring and safety

Renal function and serum potassium are checked within one to two weeks of starting
or uptitrating an MRA or ARNI. Daily weight is a practical marker of fluid status.
A rise of more than two kilograms over three days suggests decompensation and
prompts a review of diuretic dosing."""},
    {"title": "Monograph — Chronic Kidney Disease", "department": "Nephrology", "text":
"""# Chronic Kidney Disease

Chronic kidney disease is a sustained reduction in kidney function over at least
three months. It is staged by estimated GFR and by the degree of albuminuria.

## Staging

Stage 1 and 2 have preserved or mildly reduced GFR with evidence of kidney damage.
Stage 3a is an eGFR of 45 to 59 and stage 3b is 30 to 44 mL/min per 1.73 m2. Stage
4 is 15 to 29 and stage 5 is below 15 or dialysis. A rising creatinine alongside a
falling eGFR indicates progression.

## Management

Blood pressure control with an ACE inhibitor or ARB slows decline, particularly
with proteinuria or diabetes. Potassium is monitored because these agents and a
failing kidney both raise it. An SGLT2 inhibitor now has a role in slowing
progression in selected patients."""},
    {"title": "Monograph — Type 2 Diabetes", "department": "Endocrinology", "text":
"""# Type 2 Diabetes Mellitus

Type 2 diabetes is a chronic disorder of glucose regulation driven by insulin
resistance and relative insulin deficiency. Diagnosis rests on an HbA1c of 6.5
percent or above, a fasting glucose of 126 mg/dL or above, or a random glucose of
200 mg/dL or above with symptoms.

## Glycaemic targets and monitoring

A common HbA1c goal is below 7 percent, individualised by age, frailty and
hypoglycaemia risk. Fasting glucose is generally targeted at 80 to 130 mg/dL.
Persistently high values such as 8 to 9 percent indicate poor control and warrant
treatment intensification and adherence review.

## Therapy

Lifestyle change and metformin are first-line. When cardiovascular or kidney
disease is present, an SGLT2 inhibitor or GLP-1 receptor agonist is added for organ
protection. Insulin is introduced when targets are not met. Blood pressure and lipid
control plus annual eye and foot screening reduce complications.

## Complications

Chronic hyperglycaemia damages large and small vessels, causing coronary disease,
nephropathy, retinopathy and neuropathy. Regular screening detects these early so
that protective therapy can begin."""},
    {"title": "Monograph — Hypertension", "department": "Cardiology", "text":
"""# Hypertension

Hypertension is persistently raised arterial pressure and a major risk factor for
stroke, heart failure and kidney disease. Most guidelines define it as an office
systolic of 140 mmHg or above or diastolic of 90 mmHg or above, confirmed on repeat
measurement or with ambulatory monitoring.

## Assessment

Evaluation looks for target-organ damage and secondary causes, and quantifies
overall cardiovascular risk. Blood pressure is measured correctly with an
appropriately sized cuff after rest.

## Management

Lifestyle measures — salt reduction, weight loss, exercise and limiting alcohol —
are advised for everyone. Drug therapy typically begins with an ACE inhibitor or
ARB, a calcium channel blocker, or a thiazide-type diuretic, chosen by age and
comorbidity. Combinations are common, and electrolytes and kidney function are
checked after starting renin-angiotensin blockade."""},
]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# rough educational reference ranges → (interpret fn). Returns (level, note) where
# level is "high"/"low"/"normal" and note is plain language for patient education.
def _interpret(name: str, value) -> tuple:
    v = _num(value)
    n = (name or "").strip().lower()
    if v is None:
        return ("", "")
    if "hba1c" in n:
        if v >= 9: return ("high", "well above the usual target of 7 percent, indicating poorly controlled diabetes")
        if v >= 7: return ("high", "above the usual target of 7 percent, suggesting diabetes control could be improved")
        if v >= 6.5: return ("borderline", "in the diabetic range")
        return ("normal", "within a reasonable range")
    if "glucose" in n:
        if v >= 180: return ("high", "high; fasting glucose is usually kept between 80 and 130 mg/dL")
        if v >= 130: return ("high", "above the typical 80 to 130 mg/dL target")
        if v < 70: return ("low", "low (possible hypoglycaemia)")
        return ("normal", "within the usual target range")
    if "systolic" in n or ("bp" in n and "dias" not in n) or "blood pressure" in n:
        if v >= 160: return ("high", "markedly raised; 140 mmHg or above is hypertension")
        if v >= 140: return ("high", "raised; 140 mmHg or above indicates hypertension")
        return ("normal", "within an acceptable range")
    if "diastolic" in n:
        if v >= 90: return ("high", "raised; 90 mmHg or above indicates hypertension")
        return ("normal", "within an acceptable range")
    if "egfr" in n:
        if v < 30: return ("low", "low, indicating significantly reduced kidney function (CKD stage 4)")
        if v < 45: return ("low", "reduced, consistent with moderate chronic kidney disease (stage 3b)")
        if v < 60: return ("low", "mildly reduced, consistent with early chronic kidney disease (stage 3a)")
        if v < 90: return ("borderline", "slightly below the ideal of 90 or above")
        return ("normal", "normal kidney function")
    if "creatinine" in n:
        if v > 1.3: return ("high", "above the usual range, suggesting reduced kidney function")
        if v < 0.6: return ("low", "slightly low")
        return ("normal", "within the usual range")
    if "potassium" in n:
        if v > 5.0: return ("high", "above 5.0 mEq/L (hyperkalaemia)")
        if v < 3.5: return ("low", "below 3.5 mEq/L (hypokalaemia)")
        return ("normal", "within the normal range")
    if "sodium" in n:
        if v > 145: return ("high", "above the normal range")
        if v < 135: return ("low", "below the normal range (hyponatraemia)")
        return ("normal", "within the normal range")
    if "hemoglobin" in n or "haemoglobin" in n:
        if v < 12: return ("low", "low, which can indicate anaemia")
        return ("normal", "within a reasonable range")
    if "ldl" in n:
        if v >= 130: return ("high", "above the desirable level")
        return ("normal", "at or below the desirable level")
    if "spo2" in n or "saturation" in n:
        if v < 92: return ("low", "low oxygen saturation")
        return ("normal", "normal oxygen saturation")
    if "temperature" in n:
        if v >= 38: return ("high", "a fever")
        return ("normal", "normal temperature")
    if "heart rate" in n or "pulse" in n:
        if v > 100: return ("high", "faster than the normal 60 to 100 range")
        if v < 60: return ("low", "slower than the normal 60 to 100 range")
        return ("normal", "within the normal 60 to 100 range")
    return ("", "")


def _patient_to_text(p: Dict) -> str:
    """Clinical EHR summary chunk with reference-range interpretation baked in,
    so it grounds both clinician and patient questions (works in Postgres mode
    too, where stored observations carry no flag)."""
    name = p.get("full_name", "")
    pid = p.get("patient_id", "")
    age = p.get("age", "")
    gender = p.get("gender", "")
    dept = p.get("dept") or p.get("department") or ""
    conds = []
    for c in (p.get("conditions") or []):
        conds.append(c if isinstance(c, str) else
                     f"{c.get('icd10_code','')} {c.get('description','')}".strip())
    obs, abnormal = [], []
    for o in (p.get("observations") or []):
        nm = o.get("name") or o.get("display_name") or ""
        val = o.get("value", "")
        unit = o.get("unit", "")
        level, note = _interpret(nm, val)
        # prefer a stored flag if present, else our computed level
        flag = o.get("flag")
        tag = {"H": "high", "L": "low", "N": "normal"}.get(flag, level)
        obs.append(f"{nm} {val}{unit}" + (f" ({tag})" if tag else ""))
        if level in ("high", "low") or flag in ("H", "L"):
            abnormal.append(f"{nm} of {val}{unit} is {note}" if note else f"{nm} {val}{unit} is abnormal")
    parts = [f"Patient {name} ({pid}), {age} year old {gender}, {dept}."]
    if conds:
        parts.append("Active conditions: " + "; ".join(conds) + ".")
    if obs:
        parts.append("Recent observations: " + "; ".join(obs) + ".")
    if abnormal:
        parts.append("Results that are outside the usual range: " + "; ".join(abnormal) + ".")
    return " ".join(parts)


def _patient_results_summary(p: Dict) -> str:
    """A plain-language 'what your results mean' chunk for patient questions."""
    name = p.get("full_name", "")
    pid = p.get("patient_id", "")
    conds = []
    for c in (p.get("conditions") or []):
        conds.append(c if isinstance(c, str) else (c.get("description") or c.get("icd10_code", "")))
    lines = [f"Results summary for {name} ({pid})."]
    if conds:
        lines.append("Recorded conditions: " + "; ".join(x for x in conds if x) + ".")
    explained = []
    for o in (p.get("observations") or []):
        nm = o.get("name") or o.get("display_name") or ""
        val = o.get("value", "")
        unit = o.get("unit", "")
        level, note = _interpret(nm, val)
        if note:
            explained.append(f"The {nm} reading of {val}{unit} is {note}.")
    if explained:
        lines.append("What the recent results mean: " + " ".join(explained))
    else:
        lines.append("Recent results are broadly within usual ranges.")
    lines.append("This is a plain-language summary for the patient and does not replace "
                 "advice from the treating clinician.")
    return " ".join(lines)


def build_corpus(store) -> List[Dict]:
    """Return all chunks (guidelines + per-patient EHR) with RBAC metadata."""
    chunks: List[Dict] = []
    for g in SYNTHETIC_GUIDELINES:
        chunks.append({"text": f"{g['title']}. {g['text']}",
                       "source_type": "guideline", "patient_id": "",
                       "department": g["department"], "title": g["title"]})
    for m in SYNTHETIC_MONOGRAPHS:
        chunks.append({"text": m["text"],
                       "source_type": "guideline", "patient_id": "",
                       "department": m["department"], "title": m["title"]})
    for summary in store.list_patients():
        pid = summary["patient_id"]
        full = store.get_patient(pid) or summary
        dept = full.get("dept") or full.get("department") or ""
        chunks.append({"text": _patient_to_text(full),
                       "source_type": "ehr", "patient_id": pid,
                       "department": dept,
                       "title": f"EHR — {full.get('full_name', pid)}"})
        chunks.append({"text": _patient_results_summary(full),
                       "source_type": "ehr", "patient_id": pid,
                       "department": dept,
                       "title": f"Results summary — {full.get('full_name', pid)}"})
    return chunks
