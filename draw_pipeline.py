"""
draw_pipeline.py
────────────────────────────────────────────────────────────────
Generates a detailed, student-friendly data-flow diagram of the
BCH Meditech Lab pipeline.

Output: lab_visualizations/pipeline_diagram.png
Run:    python3 draw_pipeline.py
────────────────────────────────────────────────────────────────
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

os.makedirs("lab_visualizations", exist_ok=True)

# ── Palette ────────────────────────────────────────────────────
BG      = "#0d1117"
SENDER  = "#1f6feb"
NIFI    = "#e6841a"
ES      = "#00bfb3"
KIBANA  = "#f04e98"
FILE    = "#3fb950"
ARROW1  = "#58a6ff"   # TCP path
ARROW2  = "#7ee787"   # HTTP path
TEXT_L  = "#e6edf3"
TEXT_D  = "#0d1117"
LABEL   = "#8b949e"
PANEL   = "#161b22"

fig, ax = plt.subplots(figsize=(24, 15))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 24)
ax.set_ylim(0, 15)
ax.axis('off')


# ─── helpers ──────────────────────────────────────────────────

def box(cx, cy, w, h, fill, title, subtitle="", lines=None, tc=TEXT_D,
        edge="white", ew=1.4, alpha=0.93, title_size=10.5):
    r = FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                       boxstyle="round,pad=0.07",
                       facecolor=fill, edgecolor=edge,
                       linewidth=ew, alpha=alpha, zorder=3)
    ax.add_patch(r)
    top = cy + h/2 - 0.2
    ax.text(cx, top, title, ha='center', va='top',
            fontsize=title_size, fontweight='bold', color=tc, zorder=4)
    if subtitle:
        top -= 0.32
        ax.text(cx, top, subtitle, ha='center', va='top',
                fontsize=8, color=tc, alpha=0.85, zorder=4, style='italic')
    if lines:
        top -= 0.1
        for ln in lines:
            top -= 0.24
            ax.text(cx, top, ln, ha='center', va='top',
                    fontsize=7.5, color=tc, alpha=0.82, zorder=4,
                    fontfamily='monospace')


def panel(x, y, w, h, fill, label):
    r = FancyBboxPatch((x, y), w, h,
                       boxstyle="round,pad=0.12",
                       facecolor=fill, edgecolor=fill,
                       linewidth=0, alpha=0.09, zorder=1)
    ax.add_patch(r)
    ax.text(x + 0.2, y + h - 0.2, label,
            ha='left', va='top', fontsize=8.5, color=fill,
            alpha=0.75, fontweight='bold', zorder=2)


def arr(x1, y1, x2, y2, col, lbl="", lw=2.6, rad=0.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='-|>', color=col, lw=lw,
                                connectionstyle=f"arc3,rad={rad}"),
                zorder=5)
    if lbl:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my + 0.18, lbl, ha='center', va='bottom',
                fontsize=8, color=col, fontweight='bold', zorder=6)


def note(x, y, w, h, fill, heading, body):
    r = FancyBboxPatch((x, y), w, h,
                       boxstyle="round,pad=0.07",
                       facecolor=fill, edgecolor=fill,
                       linewidth=0.8, alpha=0.14, zorder=2)
    ax.add_patch(r)
    ax.text(x + 0.14, y + h - 0.15, "  " + heading,
            ha='left', va='top', fontsize=8, color=fill,
            fontweight='bold', zorder=3)
    ax.text(x + 0.14, y + h - 0.42, body,
            ha='left', va='top', fontsize=7, color=TEXT_L,
            alpha=0.85, zorder=3)


# ═══════════════════════════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════════════════════════
ax.text(12, 14.65, "Bangalore City Hospital  —  HL7 Data Pipeline Architecture",
        ha='center', va='top', fontsize=17, fontweight='bold', color=TEXT_L)
ax.text(12, 14.2, "UE26MT324  Medical Informatics  |  PES University",
        ha='center', va='top', fontsize=10, color=LABEL)

# ═══════════════════════════════════════════════════════════════
# BACKGROUND PANELS
# ═══════════════════════════════════════════════════════════════
panel(0.3,  7.0, 3.6,  6.4, SENDER, "[ 1 ]  Student Action  (HL7 Sender UI)")
panel(4.2,  1.6, 11.2, 9.0, NIFI,   "[ 2 ]  Apache NiFi  —  Data Routing & Transformation Pipeline")
panel(16.0, 5.0,  7.5, 5.5, ES,     "[ 3 ]  Elasticsearch  —  Indexing & Search")
panel(16.0, 0.9,  7.5, 3.6, KIBANA, "[ 4 ]  Kibana  —  Dashboards & Exploration")

# ═══════════════════════════════════════════════════════════════
# SENDER PANEL BOXES
# ═══════════════════════════════════════════════════════════════
box(2.1, 12.4, 3.0, 1.5,
    fill=SENDER, tc=TEXT_L,
    title="HL7 Sender UI",
    subtitle="http://localhost:5050",
    lines=["Flask (Python 3)", "Dark web interface"])

box(2.1, 10.7, 3.0, 1.7,
    fill="#21262d", tc=TEXT_L, edge="#30363d",
    title="Patient + Message Type",
    subtitle="Student selects:",
    lines=["Patient  (5 pre-loaded)",
           "ADT-A01  Admission",
           "ADT-A03  Discharge",
           "ORU-R01  Lab Result",
           "ORM-O01  Medication Order"])

box(2.1, 8.65, 3.0, 1.7,
    fill="#21262d", tc=TEXT_L, edge="#30363d",
    title="Generated HL7 v2.5 Message",
    subtitle="Live preview in UI before sending:",
    lines=["MSH|^~\\&|BCH|...|ADT^A01",
           "EVN|A01|20240607120000",
           "PID|1||MRN-10001|Menon^R.",
           "PV1|1|I|Endocrinology|..."])

# ═══════════════════════════════════════════════════════════════
# NIFI PROCESSORS
# ═══════════════════════════════════════════════════════════════
PY  = 6.1   # vertical centre of processor row
PH  = 3.2   # processor box height
PW  = 2.3   # processor box width

# Processor 1 — ListenTCP
box(5.6, PY, PW, PH,
    fill="#e6841a", tc=TEXT_D,
    title="Processor 1",
    subtitle="ListenTCP",
    title_size=9,
    lines=["",
           "Receives raw HL7 bytes",
           "over plain TCP socket",
           "",
           "Port:       8081",
           "Delimiter:  \\n",
           "Charset:    UTF-8",
           "Max conn:   16"])

# Processor 2 — UpdateAttribute
box(8.4, PY, PW, PH,
    fill="#d4700f", tc=TEXT_D,
    title="Processor 2",
    subtitle="UpdateAttribute",
    title_size=9,
    lines=["",
           "Stamps metadata onto",
           "each HL7 FlowFile:",
           "",
           "filename: hl7-{ts}.hl7",
           "received.at: {datetime}",
           "source.system: sender-ui",
           "hospital.code: BCH"])

# Processor 3 — ReplaceText
box(11.2, PY, PW, PH,
    fill="#c4620e", tc=TEXT_D,
    title="Processor 3",
    subtitle="ReplaceText",
    title_size=9,
    lines=["",
           "Adds audit header line",
           "at top of file (Prepend):",
           "",
           "# BCH HL7 RECEIVED",
           "| 2024-06-07 12:00:00",
           "| src=hl7-sender-ui",
           "(Strategy: Prepend)"])

# Processor 4 — PutFile
box(14.0, PY, PW, PH,
    fill="#b45510", tc=TEXT_D,
    title="Processor 4",
    subtitle="PutFile",
    title_size=9,
    lines=["",
           "Writes FlowFile content",
           "to the filesystem:",
           "",
           "Dir: /tmp/nifi-hl7-inbox/",
           "Create dirs: true",
           "Conflict:    replace",
           "Auto-term: success+fail"])

# File on disk
box(14.0, 2.75, PW, 2.25,
    fill="#1a4731", tc=TEXT_L, edge=FILE, ew=1.2,
    title="HL7 File on Disk",
    subtitle="/tmp/nifi-hl7-inbox/",
    lines=["hl7-20240607-120000.hl7",
           "",
           "# BCH HL7 RECEIVED ...",
           "MSH|^~\\&|BCH|NIFI|...",
           "PID|1||MRN-10001|..."])

# ═══════════════════════════════════════════════════════════════
# ELASTICSEARCH + KIBANA
# ═══════════════════════════════════════════════════════════════
box(19.75, 8.6, 5.8, 3.6,
    fill="#005f5a", tc=TEXT_L, alpha=0.95,
    title="Elasticsearch",
    subtitle="http://localhost:9200",
    lines=["Index: hl7-messages",
           "",
           "JSON document per message:",
           "  @timestamp   2024-06-07T12:00Z",
           "  msg_type     ADT_A01",
           "  patient_id   PT-001",
           "  patient_name Rajan Menon",
           "  department   Endocrinology",
           "  icd10_code   E11.65",
           "  nifi_ok      true",
           "  segments     4"])

box(19.75, 2.5, 5.8, 3.4,
    fill="#6e1a55", tc=TEXT_L, alpha=0.95,
    title="Kibana",
    subtitle="http://localhost:5601",
    lines=["Data Views loaded:",
           "  hl7-messages      (live HL7 traffic)",
           "  ehr-patients      (8 patients)",
           "  ehr-observations  (17 obs / LOINC)",
           "  ehr-conditions    (13 ICD-10 dx)",
           "",
           "Analytics > Discover  (search & filter)",
           "Analytics > Lens      (build charts)"])

# ═══════════════════════════════════════════════════════════════
# ARROWS
# ═══════════════════════════════════════════════════════════════

# Inside sender panel (vertical connectors)
arr(2.1, 11.55, 2.1, 11.5,  col=TEXT_L, lw=1.5)
arr(2.1,  9.8,  2.1,  9.55, col=TEXT_L, lw=1.5)

# Sender -> ListenTCP  (TCP)
arr(3.64, 8.65, 4.48, 6.85, col=ARROW1, lbl="TCP  port 8081", lw=3.0)
ax.text(3.8, 5.9, "Raw HL7 bytes over TCP socket\n(sendall then close)",
        ha='left', va='top', fontsize=7.5, color=ARROW1, style='italic')

# Processor chain
arr(6.75, PY, 7.27, PY, col=NIFI, lbl="success", lw=2.5)
arr(9.53, PY, 10.07,PY, col=NIFI, lbl="success", lw=2.5)
arr(12.33,PY, 12.87,PY, col=NIFI, lbl="success", lw=2.5)

# PutFile -> file
arr(14.0, 4.73, 14.0, 3.88, col=FILE, lbl="writes file", lw=2.2)

# Sender -> Elasticsearch  (HTTP — curved arc over the NiFi panel)
ax.annotate("", xy=(16.85, 9.0), xytext=(3.64, 7.95),
            arrowprops=dict(arrowstyle='-|>', color=ARROW2, lw=3.0,
                            connectionstyle="arc3,rad=-0.25"),
            zorder=6)
ax.text(10.5, 11.2,
        "HTTP POST  :9200/hl7-messages/_doc",
        ha='center', va='bottom', fontsize=9.5, color=ARROW2,
        fontweight='bold', zorder=7)
ax.text(10.5, 10.87,
        "JSON body: {timestamp, patient_id, msg_type, department, icd10_code, nifi_ok, segments ...}",
        ha='center', va='bottom', fontsize=8, color=ARROW2,
        style='italic', zorder=7)

# ES -> Kibana
arr(19.75, 6.8, 19.75, 3.93, col="#ff7ab2", lbl="reads index", lw=2.5)

# ═══════════════════════════════════════════════════════════════
# CALLOUT NOTES  (top-right corner)
# ═══════════════════════════════════════════════════════════════
note(16.1, 12.4, 7.2, 1.0, NIFI,
     "NiFi Canvas  (https://localhost:8443/nifi)",
     "Watch FlowFile counters increment in real time as HL7 arrives.\nLogin: admin / MeditechSecret123!")

note(16.1, 11.1, 7.2, 1.0, NIFI,
     "Data Provenance  (right-click any processor > View data provenance)",
     "Click on a FlowFile to see its full journey through all 4 processors,\nattributes stamped, and content at each step.")

note(16.1,  9.9, 7.2, 1.0, ES,
     "Kibana Discover  (Analytics > Discover > hl7-messages)",
     "Filter: msg_type : ADT_A01  |  Sort by @timestamp desc\nSee each message indexed within 1-2 seconds of sending.")

note(16.1,  8.7, 7.2, 1.0, FILE,
     "MinIO Archive  (http://localhost:9001)",
     "HL7 files also archived in MinIO bucket hl7-archive.\nLogin: admin / MeditechSecret123!")

# ═══════════════════════════════════════════════════════════════
# HL7 SEGMENT GLOSSARY  (bottom-left)
# ═══════════════════════════════════════════════════════════════
ax.text(0.5, 6.4, "HL7 v2.5  SEGMENT REFERENCE", ha='left', fontsize=8.5,
        color=SENDER, fontweight='bold')
segs = [
    ("MSH", "#79c0ff", "Message Header  — sender, receiver, timestamp, message type (e.g. ADT^A01)"),
    ("EVN", "#a5d6ff", "Event           — trigger code for what happened (A01=admit, A03=discharge)"),
    ("PID", "#cae8ff", "Patient ID      — MRN, full name, DOB, gender, address, blood type"),
    ("PV1", "#e6f3ff", "Patient Visit   — ward, bed number, attending physician, encounter ID"),
    ("OBX", "#ffa657", "Observation     — lab result with LOINC code, value, unit, normal flag"),
    ("ORM", "#ff7b72", "Order           — medication or test ordered; links to RxNorm / SNOMED codes"),
]
sy = 6.05
for seg, col, desc in segs:
    ax.text(0.55, sy, seg, ha='left', va='top', fontsize=8, color=col,
            fontweight='bold', fontfamily='monospace')
    ax.text(1.45, sy, desc, ha='left', va='top', fontsize=7.5, color=TEXT_L, alpha=0.82)
    sy -= 0.3

# ── PATH LEGEND ───────────────────────────────────────────────
ly = 2.1
ax.text(0.5, ly + 0.55, "DATA PATHS:", ha='left', fontsize=8,
        color=LABEL, fontweight='bold')
ax.plot([0.5, 1.3], [ly + 0.14, ly + 0.14], color=ARROW1, lw=2.5)
ax.text(1.45, ly + 0.18, "TCP path  ->  NiFi pipeline  ->  .hl7 file on disk  (for pipeline demo in NiFi canvas)",
        ha='left', va='center', fontsize=7.5, color=ARROW1)
ax.plot([0.5, 1.3], [ly - 0.18, ly - 0.18], color=ARROW2, lw=2.5)
ax.text(1.45, ly - 0.14, "HTTP path  ->  Elasticsearch  ->  Kibana dashboards  (for search & analytics demo)",
        ha='left', va='center', fontsize=7.5, color=ARROW2)

# ── FOOTER ────────────────────────────────────────────────────
ax.text(12, 0.22,
        "Both paths fire simultaneously on every Send click   "
        "|   NiFi shows raw HL7 byte flow   "
        "|   Kibana shows structured JSON for analytics",
        ha='center', va='bottom', fontsize=8, color=LABEL, style='italic')

# ── HORIZONTAL DIVIDER between NiFi panel and inbox ───────────
ax.plot([4.3, 15.1], [4.55, 4.55], color=NIFI, lw=0.6, alpha=0.3, ls='--')

out = "lab_visualizations/pipeline_diagram.png"
plt.savefig(out, dpi=160, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
plt.close()
print(f"Saved: {out}")
