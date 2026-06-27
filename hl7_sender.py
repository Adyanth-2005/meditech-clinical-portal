"""
Bangalore City Hospital — HL7 Message Sender UI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Interactive web UI for sending HL7 v2.5 messages.
Each send fires two actions:
  1. TCP → NiFi port 8081  (visible in NiFi canvas counters)
  2. HTTP POST → Elasticsearch  (visible in Kibana dashboard)

Prerequisites:  pip install flask requests
Run:            python3 hl7_sender.py
Open:           http://localhost:5050
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from flask import Flask, request, jsonify, render_template_string
import socket, json, threading, requests as req_lib
from datetime import datetime, timezone

app = Flask(__name__)
message_log, log_lock = [], threading.Lock()
counter = [1000]

NIFI_HOST, NIFI_PORT = "localhost", 8081
ES_URL = "http://localhost:9200"

# ── Patient data (mirrors init.sql) ──────────────────────────────────────────
PATIENTS = {
    "PT-001": {
        "name": "Rajan Menon", "age": 54, "gender": "M",
        "dob": "19700412", "mrn": "MRN-10001",
        "blood_type": "B+", "city": "Bangalore",
        "conditions": ["T2DM (E11.65)", "Hypertension (I10)", "Diabetic Nephropathy (N08)"],
        "dept": "Endocrinology", "room": "Room 12 Bed 2",
        "dr": "Sharma^Priya", "enc": "ENC-005",
        "icd": "E11.65",
        "obs": {
            "HbA1c":        {"v": 8.9,  "u": "%",      "l": "4548-4",  "f": "H", "ref": "<7.0"},
            "Blood Glucose":{"v": 182,  "u": "mg/dL",  "l": "2345-7",  "f": "H", "ref": "70-99"},
            "Systolic BP":  {"v": 148,  "u": "mmHg",   "l": "8480-6",  "f": "H", "ref": "90-120"},
            "eGFR":         {"v": 68,   "u": "mL/min", "l": "33914-3", "f": "L", "ref": ">90"},
        },
        "meds": [("Metformin","1000mg","BD"), ("Glipizide","5mg","OD"), ("Amlodipine","5mg","OD")],
    },
    "PT-002": {
        "name": "Lakshmi Nair", "age": 39, "gender": "F",
        "dob": "19850922", "mrn": "MRN-10002",
        "blood_type": "O+", "city": "Mysuru",
        "conditions": ["Heart Failure (I50.9)", "Hypertension (I10)"],
        "dept": "Cardiology", "room": "CCU Bed 1",
        "dr": "Rao^Suresh", "enc": "ENC-008",
        "icd": "I50.9",
        "obs": {
            "Echo EF":  {"v": 48,  "u": "%",    "l": "8806-2",  "f": "L", "ref": "55-70"},
            "BNP":      {"v": 380, "u": "pg/mL","l": "42637-9", "f": "H", "ref": "<100"},
            "Systolic BP":{"v":130,"u": "mmHg", "l": "8480-6",  "f": "N", "ref": "90-120"},
        },
        "meds": [("Furosemide","40mg","OD"), ("Carvedilol","12.5mg","BD")],
    },
    "PT-003": {
        "name": "Suresh Patel", "age": 69, "gender": "M",
        "dob": "19550130", "mrn": "MRN-10003",
        "blood_type": "A-", "city": "Bangalore",
        "conditions": ["CKD Stage 3 (N18.3)", "Hypertension (I10)"],
        "dept": "Nephrology", "room": "Room 8 Bed 3",
        "dr": "Thomas^George", "enc": "ENC-010",
        "icd": "N18.3",
        "obs": {
            "Creatinine": {"v": 2.4, "u": "mg/dL", "l": "2160-0",  "f": "H", "ref": "0.7-1.3"},
            "eGFR":       {"v": 38,  "u": "mL/min","l": "33914-3", "f": "L", "ref": ">60"},
            "Potassium":  {"v": 5.2, "u": "mEq/L", "l": "2823-3",  "f": "H", "ref": "3.5-5.0"},
        },
        "meds": [("Losartan","50mg","OD")],
    },
    "PT-004": {
        "name": "Priya Iyer", "age": 62, "gender": "F",
        "dob": "19620715", "mrn": "MRN-10004",
        "blood_type": "AB+", "city": "Hubli",
        "conditions": ["COPD w/ Exacerbation (J44.1)", "Heart Failure (I50.9)"],
        "dept": "Pulmonology", "room": "ICU Bed 4",
        "dr": "Verma^Anand", "enc": "ENC-011",
        "icd": "J44.1",
        "obs": {
            "SpO2":      {"v": 88,   "u": "%",   "l": "2708-6", "f": "L", "ref": ">95"},
            "Body Temp": {"v": 38.9, "u": "°C",  "l": "8310-5", "f": "H", "ref": "36-37.5"},
            "Resp Rate": {"v": 24,   "u": "/min", "l": "9279-1", "f": "H", "ref": "12-20"},
        },
        "meds": [("Salbutamol","2.5mg","nebulisation"), ("Carvedilol","3.125mg","BD")],
    },
    "PT-007": {
        "name": "Vikram Singh", "age": 76, "gender": "M",
        "dob": "19480602", "mrn": "MRN-10007",
        "blood_type": "A+", "city": "Delhi",
        "conditions": ["Atherosclerotic HD (I25.10)", "Hypertension (I10)"],
        "dept": "Cardiology", "room": "CCU Bed 2",
        "dr": "Rao^Suresh", "enc": "ENC-014",
        "icd": "I25.10",
        "obs": {
            "Troponin I": {"v": 2.8, "u": "ng/mL", "l": "10839-9", "f": "H", "ref": "<0.04"},
            "Systolic BP":{"v": 90,  "u": "mmHg",  "l": "8480-6",  "f": "L", "ref": "90-120"},
            "Heart Rate": {"v": 110, "u": "bpm",   "l": "8867-4",  "f": "H", "ref": "60-100"},
        },
        "meds": [("Aspirin","325mg","STAT"), ("Ticagrelor","90mg","BD")],
    },
}


# ── Flask routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE,
                                  patients_json=json.dumps(PATIENTS))

@app.route('/send', methods=['POST'])
def send_hl7():
    data   = request.get_json(silent=True) or {}
    hl7    = data.get('hl7', '')
    pid    = data.get('patient_id', '')
    mtype  = data.get('msg_type', '')

    counter[0] += 1
    msg_id = f"MSG{counter[0]:06d}"
    pname  = PATIENTS.get(pid, {}).get('name', 'Unknown')

    result = {"ok": False, "msg_id": msg_id, "patient": pname,
              "bytes": 0, "error": "", "es_ok": False}

    # 1. Send via TCP to NiFi ─────────────────────────────────────────────────
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((NIFI_HOST, NIFI_PORT))
        payload = hl7.encode('utf-8') + b'\n'
        sock.sendall(payload)
        sock.close()
        result["ok"]    = True
        result["bytes"] = len(payload)
    except Exception as e:
        result["error"] = f"NiFi TCP: {e}"

    # 2. Index in Elasticsearch (for Kibana) ──────────────────────────────────
    p = PATIENTS.get(pid, {})
    es_doc = {
        "@timestamp":    datetime.now(timezone.utc).isoformat(),
        "msg_id":        msg_id,
        "msg_type":      mtype,
        "patient_id":    pid,
        "patient_name":  pname,
        "department":    p.get("dept", ""),
        "icd10_code":    p.get("icd", ""),
        "conditions":    p.get("conditions", []),
        "hospital":      "BCH",
        "source":        "hl7-sender-ui",
        "segments":      hl7.count('\r') + 1,
        "nifi_ok":       result["ok"],
    }
    try:
        r = req_lib.post(f"{ES_URL}/hl7-messages/_doc",
                         json=es_doc, timeout=2)
        result["es_ok"] = r.status_code in (200, 201)
    except Exception:
        pass

    # Log locally
    with log_lock:
        message_log.insert(0, {**result, "ts": datetime.now().strftime("%H:%M:%S"),
                                "type": mtype})
        if len(message_log) > 100:
            message_log.pop()

    return jsonify(result)

@app.route('/ping')
def ping():
    nifi_ok, es_ok = False, False
    try:
        s = socket.socket(); s.settimeout(1)
        s.connect((NIFI_HOST, NIFI_PORT)); s.close(); nifi_ok = True
    except Exception:
        pass
    try:
        r = req_lib.get(f"{ES_URL}/_cluster/health", timeout=1)
        es_ok = r.status_code == 200
    except Exception:
        pass
    return jsonify({"nifi": nifi_ok, "es": es_ok})

@app.route('/log')
def get_log():
    return jsonify(message_log[:20])


# ── HTML template ─────────────────────────────────────────────────────────────
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>BCH HL7 Sender — Medical Informatics Lab</title>
<style>
:root {
  --bg:       #0d1117;
  --surf:     #161b22;
  --surf2:    #21262d;
  --border:   #30363d;
  --blue:     #58a6ff;
  --green:    #3fb950;
  --yellow:   #d29922;
  --red:      #f85149;
  --purple:   #bc8cff;
  --text:     #c9d1d9;
  --muted:    #8b949e;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:var(--bg);color:var(--text);height:100vh;overflow:hidden;display:flex;flex-direction:column}

/* ── Header ── */
header{background:var(--surf);border-bottom:1px solid var(--border);
       padding:10px 20px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
header h1{font-size:16px;color:var(--blue);font-weight:700}
header small{display:block;color:var(--muted);font-size:11px;margin-top:1px}
.status-bar{display:flex;gap:12px;align-items:center}
.status-pill{display:flex;align-items:center;gap:5px;font-size:11px;
             background:var(--surf2);border:1px solid var(--border);
             border-radius:20px;padding:3px 10px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--muted)}
.dot.ok{background:var(--green);box-shadow:0 0 6px var(--green)}
.dot.err{background:var(--red)}

/* ── Layout ── */
.layout{display:grid;grid-template-columns:255px 1fr 305px;flex:1;overflow:hidden}

/* ── Patient Panel ── */
.patients{background:var(--surf);border-right:1px solid var(--border);
          overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px}
.panel-title{font-size:10px;text-transform:uppercase;letter-spacing:1px;
             color:var(--muted);font-weight:700;padding:4px 0 8px}
.patient-card{background:var(--surf2);border:1px solid var(--border);
              border-radius:8px;padding:11px 12px;cursor:pointer;transition:all .15s}
.patient-card:hover{border-color:var(--blue);background:#1c2433}
.patient-card.active{border-color:var(--blue);background:#1c2433;
                     box-shadow:0 0 0 1px var(--blue)}
.pt-name{font-weight:600;font-size:13px;margin-bottom:2px}
.pt-meta{font-size:11px;color:var(--muted);margin-bottom:6px}
.badges{display:flex;flex-wrap:wrap;gap:3px}
.badge{font-size:10px;background:#2d333b;border:1px solid #444c56;
       border-radius:4px;padding:1px 6px;color:var(--muted)}
.badge.critical{border-color:#f8514966;color:#f85149}
.badge.warning{border-color:#d2992266;color:#d29922}

/* ── Workspace ── */
.workspace{display:flex;flex-direction:column;padding:16px 20px;gap:14px;
           overflow-y:auto;border-right:1px solid var(--border)}
.section-label{font-size:10px;text-transform:uppercase;letter-spacing:1px;
               color:var(--muted);font-weight:700;margin-bottom:8px}

/* message type buttons */
.msg-grid{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px}
.msg-btn{background:var(--surf2);border:1px solid var(--border);
         border-radius:8px;padding:10px 8px;cursor:pointer;text-align:center;
         transition:all .15s;color:var(--text)}
.msg-btn:hover,.msg-btn.active{border-color:var(--blue);background:#1c2433}
.msg-btn .icon{font-size:20px;display:block;margin-bottom:4px}
.msg-btn .code{font-size:11px;font-weight:700;color:var(--blue)}
.msg-btn .desc{font-size:10px;color:var(--muted);margin-top:2px}

/* HL7 preview */
.hl7-box{background:#0a0e14;border:1px solid var(--border);border-radius:8px;
         padding:14px;font-family:'JetBrains Mono','Courier New',monospace;
         font-size:11.5px;line-height:1.75;color:#adbac7;
         min-height:210px;max-height:280px;overflow-y:auto;white-space:pre}
.hl7-box .seg{color:#f47067;font-weight:700}
.hl7-box .field-sep{color:#636e7b}
.hl7-box .placeholder{color:var(--muted);font-style:italic}

/* Obs pills inside preview */
.obs-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:4px}
.obs-pill{font-size:11px;background:var(--surf2);border:1px solid var(--border);
          border-radius:6px;padding:3px 8px}
.obs-pill.H{border-color:#f8514966;color:#f85149}
.obs-pill.L{border-color:#58a6ff66;color:#58a6ff}
.obs-pill.N{border-color:#3fb95066;color:#3fb950}

/* Send button */
.send-wrap{display:flex;gap:10px}
.send-btn{flex:1;background:var(--blue);color:#000;border:none;border-radius:8px;
          padding:13px 20px;font-size:14px;font-weight:700;cursor:pointer;
          transition:background .15s}
.send-btn:hover{background:#79c0ff}
.send-btn:disabled{background:#2d333b;color:var(--muted);cursor:not-allowed}
.send-btn.busy{animation:pulse .6s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.65}}
.clear-btn{background:var(--surf2);border:1px solid var(--border);border-radius:8px;
           padding:13px 16px;cursor:pointer;color:var(--muted);font-size:13px}
.clear-btn:hover{color:var(--text)}

/* Hint */
.hint{font-size:10.5px;color:var(--muted);text-align:center}

/* ── Log Panel ── */
.log-panel{background:var(--surf);display:flex;flex-direction:column;padding:12px;gap:10px;overflow:hidden}
.stats-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px}
.stat{background:var(--surf2);border:1px solid var(--border);border-radius:8px;
      padding:8px;text-align:center}
.stat .num{font-size:22px;font-weight:700;color:var(--blue)}
.stat .num.green{color:var(--green)}
.stat .num.red{color:var(--red)}
.stat .lbl{font-size:9px;color:var(--muted);text-transform:uppercase;margin-top:1px}
.log-entries{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:6px}
.log-entry{background:var(--surf2);border:1px solid var(--border);border-radius:6px;
           padding:8px 10px;font-size:11px}
.log-entry .row1{display:flex;justify-content:space-between;margin-bottom:3px}
.log-entry .status{font-weight:700}
.log-entry .status.ok{color:var(--green)}
.log-entry .status.err{color:var(--red)}
.log-entry .mtype{font-size:10px;font-weight:700;padding:1px 6px;border-radius:3px;background:#30363d}
.log-entry .detail{color:var(--muted);font-size:10.5px}
.log-entry .meta{color:#444c56;font-size:10px;margin-top:2px}

/* Service links */
.links{display:flex;flex-direction:column;gap:5px}
.svc-link{display:flex;align-items:center;gap:8px;padding:7px 10px;
          background:var(--surf2);border:1px solid var(--border);border-radius:6px;
          text-decoration:none;color:var(--text);font-size:12px;transition:all .15s}
.svc-link:hover{border-color:var(--blue);color:var(--blue)}
.svc-link .svc-dot{width:8px;height:8px;border-radius:50%}
.svc-link small{color:var(--muted);font-size:10px;margin-left:auto}

/* Scrollbar */
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:#0d1117}
::-webkit-scrollbar-thumb{background:#30363d;border-radius:3px}
</style>
</head>
<body>

<header>
  <div>
    <h1>🏥 Bangalore City Hospital — HL7 Message Sender</h1>
    <small>Medical Informatics Lab · UE26MT324 · HL7 v2.5 → Apache NiFi + Elasticsearch</small>
  </div>
  <div class="status-bar">
    <div class="status-pill"><div class="dot" id="nifi-dot"></div><span id="nifi-lbl">NiFi :8081</span></div>
    <div class="status-pill"><div class="dot" id="es-dot"></div><span id="es-lbl">Elasticsearch</span></div>
    <div class="status-pill" style="color:var(--muted);font-size:10px">Ctrl+Enter to send</div>
  </div>
</header>

<div class="layout">

  <!-- ── PATIENT LIST ──────────────────────────────── -->
  <aside class="patients">
    <div class="panel-title">Select Patient</div>
    <div id="patient-list"></div>
  </aside>

  <!-- ── WORKSPACE ──────────────────────────────────── -->
  <main class="workspace">
    <div>
      <div class="section-label">Message Type</div>
      <div class="msg-grid" id="msg-grid">
        <div class="msg-btn active" onclick="selType('ADT_A01',this)">
          <span class="icon">🏥</span><span class="code">ADT-A01</span>
          <div class="desc">Patient Admission</div>
        </div>
        <div class="msg-btn" onclick="selType('ADT_A03',this)">
          <span class="icon">🚶</span><span class="code">ADT-A03</span>
          <div class="desc">Patient Discharge</div>
        </div>
        <div class="msg-btn" onclick="selType('ORU_R01',this)">
          <span class="icon">🧪</span><span class="code">ORU-R01</span>
          <div class="desc">Lab Results</div>
        </div>
        <div class="msg-btn" onclick="selType('ORM_O01',this)">
          <span class="icon">💊</span><span class="code">ORM-O01</span>
          <div class="desc">Medication Order</div>
        </div>
      </div>
    </div>

    <div>
      <div class="section-label">HL7 v2.5 Message Preview</div>
      <div class="hl7-box" id="hl7-preview">
        <span class="placeholder">← Select a patient from the left panel</span>
      </div>
    </div>

    <div id="obs-row" class="obs-row" style="display:none"></div>

    <div class="send-wrap">
      <button class="send-btn" id="send-btn" onclick="doSend()">
        📤 Send to Apache NiFi  (port 8081)
      </button>
      <button class="clear-btn" onclick="clearLog()" title="Clear log">⌫</button>
    </div>
    <div class="hint">Sends HL7 via TCP → NiFi  and  HTTP POST → Elasticsearch simultaneously</div>
  </main>

  <!-- ── ACTIVITY LOG ───────────────────────────────── -->
  <aside class="log-panel">
    <div class="panel-title">Activity Log</div>

    <div class="stats-row">
      <div class="stat"><div class="num" id="s-sent">0</div><div class="lbl">Sent</div></div>
      <div class="stat"><div class="num green" id="s-ok">0</div><div class="lbl">NiFi ✓</div></div>
      <div class="stat"><div class="num green" id="s-es">0</div><div class="lbl">ES ✓</div></div>
    </div>

    <div class="log-entries" id="log-entries">
      <div style="color:var(--muted);font-size:11px;text-align:center;padding:24px 0">
        No messages yet.<br>Select a patient and click Send.
      </div>
    </div>

    <div class="links">
      <a class="svc-link" href="https://localhost:8443/nifi" target="_blank">
        <div class="svc-dot" style="background:#e67e22"></div>
        Apache NiFi — Pipeline Canvas
        <small>:8443</small>
      </a>
      <a class="svc-link" href="http://localhost:5601" target="_blank">
        <div class="svc-dot" style="background:#00b4d8"></div>
        Kibana — Clinical Dashboard
        <small>:5601</small>
      </a>
      <a class="svc-link" href="http://localhost:9001" target="_blank">
        <div class="svc-dot" style="background:#27ae60"></div>
        MinIO — File Archive Console
        <small>:9001</small>
      </a>
      <a class="svc-link" href="http://localhost:9200/hl7-messages/_search?pretty&size=3" target="_blank">
        <div class="svc-dot" style="background:#f85149"></div>
        Elasticsearch — hl7-messages index
        <small>:9200</small>
      </a>
    </div>
  </aside>
</div>

<script>
const PATIENTS = {{ patients_json | safe }};
let selPid = null, selType_ = 'ADT_A01';
let nSent = 0, nOk = 0, nEs = 0;

const TYPE_COLORS = {
  ADT_A01:'#58a6ff', ADT_A03:'#a5d6ff', ORU_R01:'#79c0ff', ORM_O01:'#d2a8ff'
};
const TYPE_LABELS = {
  ADT_A01:'ADT-A01 Admission', ADT_A03:'ADT-A03 Discharge',
  ORU_R01:'ORU-R01 Lab Result', ORM_O01:'ORM-O01 Medication'
};

// ── Render patient list ──────────────────────────────────────────────────────
function renderPatients() {
  const list = document.getElementById('patient-list');
  list.innerHTML = '';
  Object.entries(PATIENTS).forEach(([pid, p]) => {
    const div = document.createElement('div');
    div.className = 'patient-card';
    div.id = `pc-${pid}`;
    div.onclick = () => selPatient(pid);
    const flagMap = {'H':'critical','L':'warning','N':''};
    const obs = Object.entries(p.obs).map(([n,o]) =>
      `<span class="badge ${flagMap[o.f]||''}">${n}: ${o.v}${o.u}</span>`
    ).join('');
    div.innerHTML = `
      <div class="pt-name">${p.name}</div>
      <div class="pt-meta">${p.gender==='M'?'♂':'♀'} ${p.age}y · ${p.mrn} · ${p.dept}</div>
      <div class="badges">
        ${p.conditions.map(c=>`<span class="badge">${c}</span>`).join('')}
      </div>`;
    list.appendChild(div);
  });
}

function selPatient(pid) {
  selPid = pid;
  document.querySelectorAll('.patient-card').forEach(c => c.classList.remove('active'));
  const card = document.getElementById(`pc-${pid}`);
  if (card) card.classList.add('active');
  updatePreview();
  updateObsRow();
}

function selType(type, el) {
  selType_ = type;
  document.querySelectorAll('.msg-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  updatePreview();
}

// ── Build HL7 message ────────────────────────────────────────────────────────
function ts14() {
  return new Date().toISOString().replace(/[-:T.]/g,'').slice(0,14);
}
function tsNow() { return ts14(); }
function msgId() { return 'MSG' + String(Date.now()).slice(-6); }

function buildHL7(pid, type) {
  const p = PATIENTS[pid];
  const now = tsNow();
  const mid = msgId();
  const nameHL7 = p.name.split(' ').reverse().join('^');
  const SEP = '\r';

  if (type === 'ADT_A01') {
    return [
      `MSH|^~\\&|HIS|BCH|NiFi|BCH|${now}||ADT^A01^ADT_A01|${mid}|P|2.5`,
      `EVN||${now}`,
      `PID|1||${pid}^^^BCH^MR||${nameHL7}||${p.dob}|${p.gender}|||${p.city}`,
      `PV1|1|I|${p.dept}^${p.room}|||||||${p.dr}||||||||${p.enc}`,
      `DG1|1||${p.icd}^${p.conditions[0]}^I10`,
    ].join(SEP);
  }
  if (type === 'ADT_A03') {
    return [
      `MSH|^~\\&|HIS|BCH|NiFi|BCH|${now}||ADT^A03^ADT_A03|${mid}|P|2.5`,
      `EVN||${now}`,
      `PID|1||${pid}^^^BCH^MR||${nameHL7}||${p.dob}|${p.gender}`,
      `PV1|1|O|${p.dept}^${p.room}|||||||${p.dr}||||||||${p.enc}`,
    ].join(SEP);
  }
  if (type === 'ORU_R01') {
    const obx = Object.entries(p.obs).map(([n, o], i) =>
      `OBX|${i+1}|NM|${o.l}^${n}^LN||${o.v}|${o.u}|${o.ref}||${o.f}|||F`
    ).join(SEP);
    return [
      `MSH|^~\\&|LIS|BCH|NiFi|BCH|${now}||ORU^R01^ORU_R01|${mid}|P|2.5`,
      `PID|1||${pid}^^^BCH^MR||${nameHL7}||${p.dob}|${p.gender}`,
      `OBR|1|||LAB^Laboratory Panel^L|||${now}`,
      obx,
    ].join(SEP);
  }
  if (type === 'ORM_O01') {
    const rxo = (p.meds || []).map((m, i) =>
      `RXO|${m[0]}^${m[0]}^RxNorm|${m[1]}||${m[2]}`
    ).join(SEP);
    return [
      `MSH|^~\\&|CPOE|BCH|NiFi|BCH|${now}||ORM^O01^ORM_O01|${mid}|P|2.5`,
      `PID|1||${pid}^^^BCH^MR||${nameHL7}||${p.dob}|${p.gender}`,
      `ORC|NW|${p.enc}-001|||||||${now}|||${p.dr}`,
      rxo,
    ].join(SEP);
  }
  return '';
}

// ── Update preview ───────────────────────────────────────────────────────────
function updatePreview() {
  const box = document.getElementById('hl7-preview');
  if (!selPid) { box.innerHTML = '<span class="placeholder">← Select a patient from the left panel</span>'; return; }
  const msg = buildHL7(selPid, selType_);
  // Syntax-highlight segment names
  const lines = msg.split('\r');
  box.innerHTML = lines.map(line => {
    const seg = line.split('|')[0];
    if (!seg) return line;
    return `<span class="seg">${seg}</span>${line.slice(seg.length)}`;
  }).join('\n');
}

function updateObsRow() {
  const row = document.getElementById('obs-row');
  if (!selPid) { row.style.display = 'none'; return; }
  const p = PATIENTS[selPid];
  const pills = Object.entries(p.obs).map(([n, o]) =>
    `<span class="obs-pill ${o.f}" title="${n}: ref ${o.ref}">${n} <b>${o.v}${o.u}</b> ${o.f!=='N'?'⚠':''}</span>`
  ).join('');
  row.innerHTML = `<div style="font-size:10px;color:var(--muted);margin-right:4px">Latest obs:</div>${pills}`;
  row.style.display = 'flex';
}

// ── Send ─────────────────────────────────────────────────────────────────────
async function doSend() {
  if (!selPid) { alert('Please select a patient first.'); return; }
  const btn = document.getElementById('send-btn');
  btn.disabled = true; btn.textContent = '⏳ Sending…'; btn.classList.add('busy');

  const hl7 = buildHL7(selPid, selType_);
  try {
    const resp = await fetch('/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({patient_id: selPid, msg_type: selType_, hl7})
    });
    const d = await resp.json();
    addLogEntry(d);
    nSent++; if (d.ok) nOk++; if (d.es_ok) nEs++;
    document.getElementById('s-sent').textContent = nSent;
    document.getElementById('s-ok').textContent   = nOk;
    document.getElementById('s-es').textContent   = nEs;
  } catch(e) {
    addLogEntry({ok:false, es_ok:false, patient:PATIENTS[selPid]?.name,
                 error:e.message, msg_id:'ERR', bytes:0});
    nSent++; document.getElementById('s-sent').textContent = nSent;
  } finally {
    btn.disabled = false;
    btn.textContent = '📤 Send to Apache NiFi  (port 8081)';
    btn.classList.remove('busy');
  }
}

function addLogEntry(d) {
  const log = document.getElementById('log-entries');
  const placeholder = log.querySelector('div[style]');
  if (placeholder) placeholder.remove();

  const e = document.createElement('div');
  e.className = 'log-entry';
  const now = new Date().toLocaleTimeString();
  const color = TYPE_COLORS[selType_] || '#58a6ff';
  const label = TYPE_LABELS[selType_] || selType_;
  e.innerHTML = `
    <div class="row1">
      <span class="status ${d.ok?'ok':'err'}">${d.ok ? '✓ DELIVERED' : '✗ FAILED'}</span>
      <span style="color:var(--muted);font-size:10px">${now}</span>
    </div>
    <div style="margin:3px 0">
      <span class="mtype" style="color:${color}">${label}</span>
    </div>
    <div class="detail">${d.patient}</div>
    <div class="meta">
      ${d.ok ? `NiFi: ${d.bytes}B  ·  ES: ${d.es_ok?'✓':'⏭'}  ·  ID: ${d.msg_id}` : d.error}
    </div>`;
  log.insertBefore(e, log.firstChild);
}

function clearLog() {
  const log = document.getElementById('log-entries');
  log.innerHTML = '<div style="color:var(--muted);font-size:11px;text-align:center;padding:24px 0">Log cleared.</div>';
  nSent = nOk = nEs = 0;
  document.getElementById('s-sent').textContent = 0;
  document.getElementById('s-ok').textContent   = 0;
  document.getElementById('s-es').textContent   = 0;
}

// ── Status polling ────────────────────────────────────────────────────────────
async function checkStatus() {
  try {
    const r = await fetch('/ping'); const d = await r.json();
    document.getElementById('nifi-dot').className = 'dot ' + (d.nifi ? 'ok' : 'err');
    document.getElementById('nifi-lbl').textContent = d.nifi ? 'NiFi :8081 ●' : 'NiFi :8081 ✗';
    document.getElementById('es-dot').className = 'dot ' + (d.es ? 'ok' : 'err');
    document.getElementById('es-lbl').textContent = d.es ? 'Elasticsearch ●' : 'Elasticsearch ✗';
  } catch(e) {}
}

// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.ctrlKey && e.key === 'Enter') doSend();
});
renderPatients();
selPatient('PT-001');
checkStatus();
setInterval(checkStatus, 8000);
</script>
</body>
</html>
"""


if __name__ == '__main__':
    import webbrowser, threading as th
    print("\n" + "═" * 56)
    print("  Bangalore City Hospital — HL7 Message Sender")
    print("═" * 56)
    print(f"  Web UI   :  http://localhost:5050")
    print(f"  NiFi TCP :  {NIFI_HOST}:{NIFI_PORT}  (must be running)")
    print(f"  ES index :  {ES_URL}/hl7-messages")
    print("─" * 56)
    print("  Press Ctrl+C to stop")
    print("═" * 56 + "\n")
    th.Timer(1.2, lambda: webbrowser.open("http://localhost:5050")).start()
    app.run(host='0.0.0.0', port=5050, debug=False)
