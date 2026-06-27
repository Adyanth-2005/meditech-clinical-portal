"""
visualize_meditech_lab.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generates 5 hospital-grade visualisation figures,
one per Meditech Lab service, using the mock data
from init.sql. No Docker connection required.

Run:    python3 visualize_meditech_lab.py
Output: lab_visualizations/  (5 PNG files)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyBboxPatch
import numpy as np
import os

OUTPUT = "lab_visualizations"
os.makedirs(OUTPUT, exist_ok=True)

plt.rcParams.update({
    'font.family':       'DejaVu Sans',
    'axes.spines.top':   False,
    'axes.spines.right': False,
    'figure.facecolor':  '#f8f9fa',
    'axes.facecolor':    '#ffffff',
    'axes.grid':         True,
    'grid.alpha':        0.3,
    'grid.linestyle':    '--',
})

C = dict(
    ok='#27ae60', warn='#e67e22', crit='#e74c3c',
    blue='#2980b9', teal='#16a085', purple='#8e44ad',
    gray='#95a5a6', dark='#2c3e50', light='#ecf0f1',
    blue2='#3498db', orange='#d35400',
)


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE 1 — PostgreSQL: Relational EHR Data Store
# ═══════════════════════════════════════════════════════════════════════════
def fig_postgres():
    fig = plt.figure(figsize=(16, 7))
    fig.text(0.5, 0.99,
             'SERVICE 1 · PostgreSQL — Relational EHR Data Store',
             ha='center', va='top', fontsize=14, fontweight='bold', color=C['blue'])
    fig.text(0.5, 0.955,
             'Clinical use case: Longitudinal diabetes management · Multi-patient comorbidity tracking',
             ha='center', va='top', fontsize=9, color=C['gray'])

    gs = gridspec.GridSpec(1, 2, figure=fig, left=0.06, right=0.96,
                           bottom=0.12, top=0.91, wspace=0.38)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    # ── Panel A: HbA1c longitudinal trend ────────────────────────────────────
    years = [2018.25, 2019.5, 2023.125, 2024.42]
    hba1c = [7.2, 7.8, 8.4, 8.9]

    ax1.axhspan(0,   5.7, alpha=0.10, color=C['ok'],   zorder=0)
    ax1.axhspan(5.7, 6.5, alpha=0.10, color=C['warn'], zorder=0)
    ax1.axhspan(6.5, 12,  alpha=0.10, color=C['crit'], zorder=0)
    ax1.axhline(7.0, color=C['ok'],  ls='--', lw=1.8, label='ADA target < 7%',   zorder=3)
    ax1.axhline(8.0, color=C['crit'],ls=':',  lw=1.8, label='Escalate therapy > 8%', zorder=3)

    ax1.plot(years, hba1c, 'o-', color=C['blue'], lw=2.5,
             ms=10, mfc='white', mew=2.5, zorder=5)

    for x, y in zip(years, hba1c):
        col = C['crit'] if y > 8 else (C['warn'] if y > 7 else C['ok'])
        ax1.annotate(f'{y}%', (x, y), xytext=(0, 13),
                     textcoords='offset points',
                     ha='center', fontsize=10, fontweight='bold', color=col)

    ax1.annotate('Metformin 500mg\n(BD) started',
                 xy=(2018.25, 7.2), xytext=(2019.0, 6.1),
                 fontsize=8, color=C['teal'],
                 arrowprops=dict(arrowstyle='->', color=C['teal'], lw=1.2))
    ax1.annotate('Dose ↑ 1000mg\n+ Glipizide 5mg OD',
                 xy=(2024.42, 8.9), xytext=(2023.1, 9.8),
                 fontsize=8, color=C['crit'],
                 arrowprops=dict(arrowstyle='->', color=C['crit'], lw=1.2))

    sql = ("-- PostgreSQL query\n"
           "SELECT obs_date, value, unit\n"
           "FROM observations o\n"
           "JOIN encounters e ON o.enc_id = e.enc_id\n"
           "WHERE e.patient_id = 'PT-001'\n"
           "  AND loinc_code   = '4548-4'\n"
           "ORDER BY obs_date;")
    ax1.text(2024.55, 5.05, sql, fontsize=6.8, family='monospace',
             va='bottom',
             bbox=dict(boxstyle='round,pad=0.45', fc='#eaf4fb',
                       ec=C['blue'], alpha=0.95, lw=1.5))

    ax1.set(xlim=(2017.5, 2026), ylim=(4.8, 11.2),
            xlabel='Year', ylabel='HbA1c (%)')
    ax1.set_title('Longitudinal HbA1c — Rajan Menon (PT-001)\n'
                  'T2DM · LOINC 4548-4 · 6-year trend',
                  fontsize=11, fontweight='bold', pad=8)

    zone_patches = [
        mpatches.Patch(color=C['ok'],   alpha=0.4, label='Normal  < 5.7%'),
        mpatches.Patch(color=C['warn'], alpha=0.4, label='Pre-diabetic 5.7–6.5%'),
        mpatches.Patch(color=C['crit'], alpha=0.4, label='Diabetic  > 6.5%'),
    ]
    line_handles, line_labels = ax1.get_legend_handles_labels()
    ax1.legend(handles=zone_patches + line_handles,
               fontsize=7.5, loc='upper left', ncol=1)

    # ── Panel B: Patient comorbidity matrix ───────────────────────────────────
    patients = ['Rajan\nMenon', 'Lakshmi\nNair', 'Suresh\nPatel',
                'Priya\nIyer', 'Arjun\nKrishnan', 'Meena\nReddy',
                'Vikram\nSingh', 'Ananya\nDas']
    conds    = ['Diabetes\n(E11.x)', 'HTN\n(I10)', 'Heart\nFailure\n(I50.x)',
                'Renal\n(N08/N18)', 'Respiratory\n(J-codes)', 'Ischaemic\nHD (I25)']
    matrix   = np.array([
        [1, 1, 0, 1, 0, 0],
        [0, 1, 1, 0, 0, 0],
        [0, 1, 0, 1, 0, 0],
        [0, 0, 1, 0, 1, 0],
        [0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 1],
        [0, 0, 0, 0, 1, 0],
    ])

    ax2.imshow(matrix, cmap=ListedColormap(['#f0f3f4', '#e74c3c']),
               aspect='auto', vmin=0, vmax=1)
    for i in range(len(patients)):
        for j in range(len(conds)):
            if matrix[i, j]:
                ax2.text(j, i, '✓', ha='center', va='center',
                         fontsize=14, color='white', fontweight='bold')

    # Risk bar per patient
    risk = matrix.sum(axis=1)
    for i, r in enumerate(risk):
        col = C['crit'] if r >= 3 else (C['warn'] if r >= 2 else (C['ok'] if r == 1 else C['gray']))
        ax2.barh(i, r / risk.max() * 0.9, left=len(conds) + 0.35,
                 height=0.55, color=col, alpha=0.85)
        ax2.text(len(conds) + 0.4 + r / risk.max() * 0.9, i, f' {r}',
                 va='center', fontsize=9, color=col, fontweight='bold')

    # Highlight highest comorbidity row
    ax2.add_patch(plt.Rectangle((-0.5, -0.5), len(conds), 1,
                                 fill=False, edgecolor='gold', lw=3))

    ax2.set_xticks(range(len(conds)))
    ax2.set_yticks(range(len(patients)))
    ax2.set_xticklabels(conds, fontsize=8)
    ax2.set_yticklabels(patients, fontsize=9)
    ax2.set_xlim(-0.5, len(conds) + 1.7)
    ax2.set_title('Patient Comorbidity Matrix\n'
                  'Gold border = highest risk · Bar = condition count',
                  fontsize=11, fontweight='bold', pad=8)
    ax2.grid(False)

    fig.text(0.5, 0.02,
             'Bangalore City Hospital · Medical Informatics Lab · UE26MT324',
             ha='center', fontsize=8, color=C['gray'])

    out = f"{OUTPUT}/01_postgresql.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✓ {out}")


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE 2 — Elasticsearch: Clinical Search & Real-Time Analytics
# ═══════════════════════════════════════════════════════════════════════════
def fig_elasticsearch():
    fig = plt.figure(figsize=(16, 7))
    fig.text(0.5, 0.99,
             'SERVICE 2 · Elasticsearch — Clinical Search & Real-Time Analytics',
             ha='center', va='top', fontsize=14, fontweight='bold', color=C['orange'])
    fig.text(0.5, 0.955,
             'Clinical use case: Full-text discharge note search · Critical lab value alerting across all patients',
             ha='center', va='top', fontsize=9, color=C['gray'])

    gs = gridspec.GridSpec(1, 2, figure=fig, left=0.06, right=0.96,
                           bottom=0.10, top=0.91, wspace=0.42)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    # ── Panel A: Simulated full-text search results ───────────────────────────
    docs = [
        ('Rajan Menon — Diabetic nephropathy (N08)',         95.4, True),
        ('Rajan Menon — T2DM + eGFR 68 mL/min (↓)',         88.1, True),
        ('Suresh Patel — CKD Stage 3 (N18.3)',               72.3, True),
        ('Rajan Menon — Microalbumin 42 mg/g creat.',        61.7, True),
        ('Suresh Patel — Creatinine 2.4 mg/dL (↑)',          54.2, True),
        ('Meena Reddy — T2DM HbA1c 9.2% (uncontrolled)',    41.5, False),
        ('Lakshmi Nair — Heart failure, Furosemide 40mg',    23.8, False),
        ('Ananya Das — Community pneumonia (J18.9)',           8.2, False),
    ]
    labels   = [d[0] for d in docs]
    scores   = [d[1] for d in docs]
    relevant = [d[2] for d in docs]
    colors   = [C['crit'] if r else C['gray'] for r in relevant]

    bars = ax1.barh(range(len(docs)), scores, color=colors, alpha=0.85, height=0.65)
    for bar, score, rel in zip(bars, scores, relevant):
        ax1.text(score + 0.5, bar.get_y() + bar.get_height() / 2,
                 f'{score:.1f}', va='center', fontsize=9,
                 color=C['crit'] if rel else C['gray'],
                 fontweight='bold' if rel else 'normal')

    ax1.set_yticks(range(len(docs)))
    ax1.set_yticklabels(labels, fontsize=8)
    ax1.set_xlabel('Relevance Score (BM25 algorithm)', fontsize=9)
    ax1.set_xlim(0, 115)
    ax1.axvline(50, color=C['warn'], ls='--', lw=1.5, alpha=0.8,
                label='Relevance threshold (50)')
    ax1.invert_yaxis()
    ax1.set_title('Full-Text Search: "diabetic kidney disease"\n'
                  'Across 15 discharge summaries indexed in Elasticsearch',
                  fontsize=11, fontweight='bold', pad=8)
    ax1.legend(fontsize=8)

    es_q = ('GET /discharge_notes/_search\n'
            '{\n'
            '  "query": {\n'
            '    "multi_match": {\n'
            '      "query":  "diabetic kidney disease",\n'
            '      "fields": ["note_text","diagnoses",\n'
            '                 "icd10_codes"]\n'
            '    }\n'
            '  }\n'
            '}')
    ax1.text(51, 7.6, es_q, fontsize=6.5, family='monospace', va='bottom',
             bbox=dict(boxstyle='round,pad=0.45', fc='#fef9e7',
                       ec=C['orange'], alpha=0.95, lw=1.5))

    # ── Panel B: Critical lab value alerts ────────────────────────────────────
    tests = [
        ('HbA1c (%)\nRajan (PT-001)',          8.9,  5.7,  7.0,  14),
        ('HbA1c (%)\nMeena (PT-006)',           9.2,  5.7,  7.0,  14),
        ('Echo EF (%)\nLakshmi (PT-002)',       42,   55,   70,   100),
        ('SpO2 (%)\nPriya (PT-004)',            88,   95,   100,  100),
        ('Troponin I (ng/mL)\nVikram (PT-007)', 2.8,  0,    0.04, 5),
        ('Creatinine (mg/dL)\nSuresh (PT-003)', 2.4,  0.7,  1.3,  4),
        ('Systolic BP (mmHg)\nRajan (PT-001)',  148,  90,   120,  200),
    ]

    ax2.set_yticks(range(len(tests)))
    ax2.set_yticklabels([t[0] for t in tests], fontsize=8)
    ax2.invert_yaxis()

    for i, (label, value, lo, hi, mx) in enumerate(tests):
        norm = lambda v: v / mx * 100
        # Normal zone shading
        ax2.barh(i, norm(hi) - norm(lo), left=norm(lo),
                 height=0.65, color=C['ok'], alpha=0.20, zorder=1)
        # Actual value bar
        abnormal = value > hi or value < lo
        col = C['crit'] if abnormal else C['ok']
        ax2.barh(i, norm(value), height=0.55, color=col, alpha=0.85, zorder=2)
        ax2.text(norm(value) + 0.5, i, f'{value}',
                 va='center', fontsize=9, color=col, fontweight='bold')
        if abnormal:
            ax2.text(104, i, '⚠ ALERT', va='center', fontsize=8,
                     color=C['crit'], fontweight='bold')

    ax2.set_xlabel('Value (normalised to 0–100 scale per test)', fontsize=9)
    ax2.set_title('Real-Time Critical Lab Alerts\n'
                  'ES aggregation across all 8 patients · LOINC reference ranges',
                  fontsize=11, fontweight='bold', pad=8)
    ax2.set_xlim(0, 122)

    legend_items = [
        mpatches.Patch(color=C['ok'],   alpha=0.4, label='Normal range'),
        mpatches.Patch(color=C['crit'], alpha=0.8, label='Abnormal / Critical'),
    ]
    ax2.legend(handles=legend_items, fontsize=8, loc='lower right')

    fig.text(0.5, 0.02,
             'Bangalore City Hospital · Medical Informatics Lab · UE26MT324',
             ha='center', fontsize=8, color=C['gray'])

    out = f"{OUTPUT}/02_elasticsearch.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✓ {out}")


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE 3 — Kibana: Clinical Operations Dashboard
# ═══════════════════════════════════════════════════════════════════════════
def fig_kibana():
    fig = plt.figure(figsize=(16, 9))
    fig.patch.set_facecolor('#1a1a2e')

    fig.text(0.5, 0.97,
             '● SERVICE 3 · Kibana — Clinical Operations Dashboard',
             ha='center', va='top', fontsize=14, fontweight='bold', color='#00b4d8')
    fig.text(0.5, 0.935,
             'Clinical use case: Hospital leadership · Ward situational awareness · Real-time monitoring',
             ha='center', va='top', fontsize=9, color='#adb5bd')

    gs = gridspec.GridSpec(3, 4, figure=fig, left=0.04, right=0.97,
                           bottom=0.06, top=0.90, hspace=0.55, wspace=0.35)

    TXT = '#e2e8f0'
    BG  = '#16213e'

    # ── Row 0: KPI metric cards ───────────────────────────────────────────────
    kpis = [
        ('PATIENTS ON RECORD', '8',    '#00b4d8', 'Unique patient records'),
        ('TOTAL ENCOUNTERS',   '15',   '#06d6a0', 'Visits (2018–2024)'),
        ('ACTIVE ALERTS',      '4',    '#ef476f', 'Critical lab values'),
        ('AVG HbA1c',          '8.7%', '#ffd166', 'Diabetic cohort (n=2)'),
    ]
    for col_i, (title, value, color, sub) in enumerate(kpis):
        ax = fig.add_subplot(gs[0, col_i])
        ax.set_facecolor(BG)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_edgecolor(color); sp.set_linewidth(2)
        ax.text(0.5, 0.68, value,  ha='center', va='center', fontsize=30,
                fontweight='bold', color=color, transform=ax.transAxes)
        ax.text(0.5, 0.36, title,  ha='center', va='center', fontsize=8.5,
                color=TXT, transform=ax.transAxes)
        ax.text(0.5, 0.13, sub,    ha='center', va='center', fontsize=7,
                color='#6c757d', transform=ax.transAxes)

    # ── Row 1 Left: Encounters by department ─────────────────────────────────
    ax_dept = fig.add_subplot(gs[1, :2])
    ax_dept.set_facecolor(BG)
    depts  = ['Endocrinology', 'Cardiology', 'General Medicine',
              'Nephrology', 'Pulmonology', 'Emergency', 'Orthopedics']
    counts = [5, 3, 3, 2, 1, 1, 1]
    dept_colors = ['#00b4d8', '#ef476f', '#06d6a0',
                   '#8e44ad', '#d35400', '#e74c3c', '#95a5a6']
    bars = ax_dept.barh(depts, counts, color=dept_colors, alpha=0.85, height=0.65)
    for bar, cnt in zip(bars, counts):
        ax_dept.text(cnt + 0.05, bar.get_y() + bar.get_height() / 2,
                     str(cnt), va='center', fontsize=10,
                     color='white', fontweight='bold')
    for sp in ax_dept.spines.values():
        sp.set_edgecolor('#2d3748')
    ax_dept.set_facecolor(BG)
    ax_dept.tick_params(axis='both', colors=TXT)
    ax_dept.set_xlabel('Number of Encounters', color=TXT, fontsize=9)
    ax_dept.set_title('Encounters by Department', color='#00b4d8',
                      fontsize=11, fontweight='bold', pad=8)
    ax_dept.set_xlim(0, 7.5)
    ax_dept.xaxis.grid(True, alpha=0.15, color='white')
    ax_dept.yaxis.grid(False)

    # ── Row 1 Right: Encounter type distribution ──────────────────────────────
    ax_pie = fig.add_subplot(gs[1, 2:])
    ax_pie.set_facecolor(BG)
    enc_types  = ['Outpatient', 'Inpatient', 'Emergency']
    enc_counts = [9, 5, 1]
    pie_colors = ['#00b4d8', '#06d6a0', '#ef476f']
    wedges, texts, autotexts = ax_pie.pie(
        enc_counts, labels=enc_types, autopct='%1.0f%%',
        colors=pie_colors, startangle=90, pctdistance=0.68,
        wedgeprops=dict(edgecolor='#1a1a2e', linewidth=3)
    )
    for t in texts:
        t.set_color(TXT); t.set_fontsize(10)
    for at in autotexts:
        at.set_color('white'); at.set_fontweight('bold'); at.set_fontsize(10)
    ax_pie.set_title('Encounter Type Mix', color='#00b4d8',
                     fontsize=11, fontweight='bold', pad=8)

    # ── Row 2: Critical alerts table ─────────────────────────────────────────
    ax_al = fig.add_subplot(gs[2, :])
    ax_al.set_facecolor(BG)
    ax_al.set_xticks([]); ax_al.set_yticks([])
    ax_al.grid(False)
    for sp in ax_al.spines.values():
        sp.set_edgecolor('#ef476f'); sp.set_linewidth(1.5)
    ax_al.set_title('  ⚠ ACTIVE CRITICAL ALERTS — Elasticsearch Real-Time Monitor',
                    color='#ef476f', fontsize=11, fontweight='bold', loc='left', pad=8)

    col_x = [0.01, 0.10, 0.24, 0.56, 0.82]
    hdrs  = ['SEVERITY', 'PATIENT', 'FINDING', 'CLINICAL CONTEXT', 'DEPT · DATE']
    for x, h in zip(col_x, hdrs):
        ax_al.text(x, 0.88, h, va='top', fontsize=8,
                   color='#6c757d', fontweight='bold', transform=ax_al.transAxes)
    ax_al.plot([0, 1], [0.82, 0.82], color='#2d3748', lw=1,
               transform=ax_al.transAxes, clip_on=False)

    alerts = [
        ('⚠ CRITICAL', 'PT-004 · Priya Iyer',
         'SpO2: 88%  (ref: >95%)',
         'Hypoxia — likely COPD exacerbation, O2 therapy initiated',
         'Pulmonology · 2023-11-20'),
        ('⚠ CRITICAL', 'PT-007 · Vikram Singh',
         'Troponin I: 2.8 ng/mL  (ref: <0.04)',
         'Elevated troponin → NSTEMI confirmed, PCI planned',
         'Cardiology · 2024-05-18'),
        ('⚠ HIGH',     'PT-001 · Rajan Menon',
         'HbA1c: 8.9%  (target: <7.0%)',
         'Uncontrolled T2DM — Glipizide added, diet counselling',
         'Endocrinology · 2024-06-03'),
        ('⚠ HIGH',     'PT-006 · Meena Reddy',
         'HbA1c: 9.2%  (target: <7.0%)',
         'Poorly controlled T2DM — therapy intensification needed',
         'Endocrinology · 2022-07-05'),
    ]
    for row_i, (sev, pt, finding, context, dept) in enumerate(alerts):
        y = 0.70 - row_i * 0.17
        col = '#ef476f' if 'CRITICAL' in sev else '#ffd166'
        for xi, v in zip(col_x, [sev, pt, finding, context, dept]):
            ax_al.text(xi, y, v, va='top', fontsize=8.5,
                       color=col if xi == col_x[0] else TXT,
                       fontweight='bold' if xi == col_x[0] else 'normal',
                       transform=ax_al.transAxes)
        if row_i < len(alerts) - 1:
            ax_al.plot([0, 1], [y - 0.10, y - 0.10], color='#2d3748',
                       lw=0.5, alpha=0.6, transform=ax_al.transAxes,
                       clip_on=False)

    fig.text(0.5, 0.01,
             'Bangalore City Hospital · Medical Informatics Lab · UE26MT324',
             ha='center', fontsize=8, color='#495057')

    out = f"{OUTPUT}/03_kibana.png"
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"  ✓ {out}")


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE 4 — Apache NiFi: HL7 Data Pipeline
# ═══════════════════════════════════════════════════════════════════════════
def fig_nifi():
    fig, ax = plt.subplots(figsize=(18, 9))
    ax.set_facecolor('#1b2631')
    fig.patch.set_facecolor('#1b2631')
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 9)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.grid(False)

    fig.text(0.5, 0.97,
             'SERVICE 4 · Apache NiFi — HL7 to EHR Data Pipeline',
             ha='center', va='top', fontsize=14, fontweight='bold', color='#3498db')
    fig.text(0.5, 0.935,
             'Clinical use case: Real-time HL7 ADT & lab message ingestion · FHIR API routing · Zero-code pipeline builder',
             ha='center', va='top', fontsize=9, color='#adb5bd')

    def proc(x, y, w, h, label, sub='', color='#2980b9'):
        box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                              boxstyle='round,pad=0.1',
                              fc=color, ec='white', lw=1.5, alpha=0.92, zorder=3)
        ax.add_patch(box)
        ax.text(x, y + (0.1 if sub else 0), label,
                ha='center', va='center', fontsize=8.5,
                fontweight='bold', color='white', zorder=4)
        if sub:
            ax.text(x, y - 0.28, sub, ha='center', va='center',
                    fontsize=6.5, color='#bdc3c7', zorder=4)

    def arrow(x1, y1, x2, y2, label='', color='#95a5a6'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color,
                                   lw=2.0, mutation_scale=18), zorder=2)
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2 + 0.2
            ax.text(mx, my, label, ha='center', va='bottom',
                    fontsize=7, color='#dfe6e9',
                    bbox=dict(boxstyle='round,pad=0.18', fc='#2c3e50', ec='none'))

    def store(x, y, label, color='#27ae60'):
        ell_top = mpatches.Ellipse((x, y + 0.38), 1.7, 0.42,
                                    fc=color, ec='white', lw=1.5, alpha=0.92, zorder=3)
        rect    = plt.Rectangle((x - 0.85, y - 0.38), 1.7, 0.76,
                                  fc=color, ec='none', alpha=0.92, zorder=2)
        ell_bot = mpatches.Ellipse((x, y - 0.38), 1.7, 0.42,
                                    fc=color, ec='white', lw=1.5, alpha=0.9, zorder=3)
        ax.add_patch(ell_bot)
        ax.add_patch(rect)
        ax.add_patch(ell_top)
        ax.text(x, y, label, ha='center', va='center',
                fontsize=8, fontweight='bold', color='white', zorder=4)

    # ── Stage labels ──────────────────────────────────────────────────────────
    for sx, label, col in [
        (1.3,  'SOURCES',   '#8e44ad'),
        (4.3,  'PARSE',     '#e67e22'),
        (7.5,  'VALIDATE',  '#27ae60'),
        (10.8, 'ENRICH',    '#16a085'),
        (14.0, 'ROUTE',     '#c0392b'),
        (17.0, 'STORE',     '#7f8c8d'),
    ]:
        ax.text(sx, 8.5, f'── {label} ──', ha='center', fontsize=9,
                fontweight='bold', color=col)

    # ── Source processors ─────────────────────────────────────────────────────
    proc(1.3, 7.0, 2.0, 0.85, 'ListenTCP',       'Port 8081\nHL7 v2 ADT/Lab', '#8e44ad')
    proc(1.3, 5.4, 2.0, 0.85, 'HandleHTTP',      'Port 8082\nFHIR JSON POST', '#8e44ad')
    proc(1.3, 3.8, 2.0, 0.85, 'GetFile',         'Batch DICOM\nfrom scanner', '#8e44ad')

    # ── Parse processors ──────────────────────────────────────────────────────
    proc(4.3, 7.0, 2.0, 0.85, 'ParseHL7',        'Segments:\nPID/OBR/OBX',  '#e67e22')
    proc(4.3, 5.4, 2.0, 0.85, 'ParseJSON\nFHIR', 'Map to\ninternal model',  '#e67e22')
    proc(4.3, 3.8, 2.0, 0.85, 'IdentifyMIME',    'DICOM → tag\nextraction',  '#e67e22')

    # ── Validate ──────────────────────────────────────────────────────────────
    proc(7.5, 6.1, 2.1, 0.85, 'ValidatePatient\n& Dedup',
         'MRN lookup\nDuplicate check', '#27ae60')

    # ── Enrich ────────────────────────────────────────────────────────────────
    proc(10.8, 6.1, 2.1, 0.85, 'CodeMapper',
         'ICD-10 / LOINC\nRxNorm lookup', '#16a085')

    # ── Route ─────────────────────────────────────────────────────────────────
    proc(14.0, 6.1, 2.1, 0.90, 'RouteByType',
         'EHR → DB\nNotes → ES\nImages → S3', '#c0392b')

    # ── Destination stores ────────────────────────────────────────────────────
    store(17.0, 7.2, 'PostgreSQL\n(EHR DB)',     '#2980b9')
    store(17.0, 5.8, 'Elasticsearch\n(Search)',   '#e67e22')
    store(17.0, 4.4, 'MinIO\n(DICOM/PDFs)',       '#27ae60')

    # ── Arrows ────────────────────────────────────────────────────────────────
    arrow(2.3, 7.0, 3.3, 7.0, 'HL7 stream')
    arrow(2.3, 5.4, 3.3, 5.4, 'FHIR JSON')
    arrow(2.3, 3.8, 3.3, 3.8, 'DICOM files')
    arrow(5.3, 7.0, 6.1, 6.5)
    arrow(5.3, 5.4, 6.1, 5.8)
    arrow(5.3, 3.8, 6.1, 5.6)
    arrow(8.55, 6.1,  9.75, 6.1, 'deduplicated')
    arrow(11.85, 6.1, 12.95, 6.1, 'enriched')
    arrow(15.05, 6.6, 16.15, 7.2, 'labs/visits')
    arrow(15.05, 6.1, 16.15, 5.8, 'notes/text')
    arrow(15.05, 5.6, 16.15, 4.4, 'DICOM/PDF')

    # ── HL7 message sample ────────────────────────────────────────────────────
    hl7 = ("Sample HL7 v2.5 ADT-A01 (Admission)\n"
           "──────────────────────────────────────\n"
           "MSH|^~\\&|HIS|BCH|NiFi|20240603\n"
           "ADT^A01|MSG001|P|2.5\n"
           "PID|1||PT-001^^^BCH||Menon^Rajan\n"
           "||19700412|M|||Bangalore^^^KA\n"
           "PV1|1|I|Endocrinology^Rm12^Bed2\n"
           "OBX|1|NM|4548-4^HbA1c^LOINC\n"
           "||8.9|%||H|||F|||20240603")
    ax.text(1.0, 3.0, hl7, fontsize=6.5, family='monospace',
            va='top', color='#dfe6e9',
            bbox=dict(boxstyle='round,pad=0.5', fc='#0d1117',
                      ec='#8e44ad', lw=1.5, alpha=0.9, zorder=5))

    ax.annotate('NiFi parses each field\ninto structured records →',
                xy=(4.3, 4.4), xytext=(4.0, 2.8),
                fontsize=7.5, color='#e67e22',
                arrowprops=dict(arrowstyle='->', color='#e67e22', lw=1.2),
                zorder=6)

    # ── Throughput stats box ──────────────────────────────────────────────────
    stats = ("Live throughput (simulated)\n"
             "──────────────────────────\n"
             "HL7 messages/day : 2,400\n"
             "FHIR API calls   :   320\n"
             "DICOM uploads    :    48\n"
             "Pipeline latency : <2 sec\n"
             "Failed routes    :     3  ⚠")
    ax.text(9.8, 3.2, stats, fontsize=7.5, family='monospace',
            va='top', color='#dfe6e9',
            bbox=dict(boxstyle='round,pad=0.5', fc='#0d1117',
                      ec='#16a085', lw=1.5, alpha=0.9, zorder=5))

    fig.text(0.5, 0.01,
             'Bangalore City Hospital · Medical Informatics Lab · UE26MT324',
             ha='center', fontsize=8, color='#495057')

    out = f"{OUTPUT}/04_nifi.png"
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"  ✓ {out}")


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE 5 — MinIO: Medical File Archive
# ═══════════════════════════════════════════════════════════════════════════
def fig_minio():
    fig = plt.figure(figsize=(16, 7))
    fig.text(0.5, 0.99,
             'SERVICE 5 · MinIO — Long-Term Medical File Archive (S3-Compatible)',
             ha='center', va='top', fontsize=14, fontweight='bold', color=C['teal'])
    fig.text(0.5, 0.955,
             'Clinical use case: DICOM imaging archive · Signed discharge PDFs · HL7 audit trail · 10-year retention policy',
             ha='center', va='top', fontsize=9, color=C['gray'])

    gs = gridspec.GridSpec(1, 3, figure=fig, left=0.05, right=0.97,
                           bottom=0.10, top=0.91, wspace=0.42)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2])

    # ── Panel A: Storage by file type (pie) ───────────────────────────────────
    file_types = ['DICOM\n(X-ray/CT/MRI)', 'PDF\n(Discharge notes)',
                  'HL7\n(Audit archive)', 'FHIR JSON\n(API cache)',
                  'CSV\n(Lab exports)']
    sizes_gb   = [2400, 180, 45, 28, 12]
    pie_cols   = [C['blue'], C['teal'], C['purple'], C['orange'], C['gray']]

    wedges, texts, autos = ax1.pie(
        sizes_gb, labels=None, autopct='%1.0f%%',
        colors=pie_cols, startangle=90, pctdistance=0.70,
        wedgeprops=dict(edgecolor='white', linewidth=2.5)
    )
    for at in autos:
        at.set_fontsize(9); at.set_fontweight('bold'); at.set_color('white')

    patches = [mpatches.Patch(color=c, label=f'{t}  ({s:,} GB)')
               for c, t, s in zip(pie_cols, file_types, sizes_gb)]
    ax1.legend(handles=patches, loc='lower center',
               bbox_to_anchor=(0.5, -0.50), fontsize=8,
               title=f'Total: {sum(sizes_gb)/1000:.1f} TB', title_fontsize=9)
    ax1.set_title('Storage by File Type\n5 S3 buckets in use',
                  fontsize=11, fontweight='bold', pad=8)

    # ── Panel B: Cumulative archive growth ────────────────────────────────────
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    dicom  = [1.80,1.90,2.00,2.08,2.15,2.20,2.24,2.28,2.32,2.35,2.38,2.40]
    pdfs   = [0.14,0.145,0.15,0.155,0.16,0.165,0.17,0.172,0.175,0.177,0.178,0.180]
    other  = [0.07,0.072,0.075,0.077,0.079,0.080,0.081,0.082,0.083,0.084,0.084,0.085]

    x = range(len(months))
    ax2.stackplot(x, dicom, pdfs, other,
                  labels=['DICOM', 'PDFs', 'Other'],
                  colors=[C['blue'], C['teal'], C['gray']], alpha=0.85)
    ax2.set_xticks(x)
    ax2.set_xticklabels(months, fontsize=8)
    ax2.set_ylabel('Cumulative Storage (TB)', fontsize=9)
    ax2.set_title('Archive Growth — 2024\nMonth-by-month cumulative',
                  fontsize=11, fontweight='bold', pad=8)
    ax2.legend(fontsize=8, loc='upper left')

    ax2.annotate('CT batch upload\n(50 radiology patients)',
                 xy=(5, 2.20 + 0.165 + 0.080), xytext=(3.0, 2.65),
                 fontsize=8, color=C['blue'],
                 arrowprops=dict(arrowstyle='->', color=C['blue'], lw=1.2))

    # ── Panel C: S3 bucket structure ──────────────────────────────────────────
    ax3.set_xlim(0, 10); ax3.set_ylim(0, 10)
    ax3.set_xticks([]); ax3.set_yticks([])
    ax3.set_facecolor('#f0f4f8')
    ax3.set_title('S3 Bucket Layout\nminio.bchosp.in:9000',
                  fontsize=11, fontweight='bold', pad=8)
    ax3.grid(False)

    buckets = [
        ('dicom-imaging',     'X-ray, MRI, CT scans (DICOM format)',           '2.4 TB',  C['blue']),
        ('discharge-reports', 'Signed discharge PDFs per patient/encounter',    '180 GB',  C['teal']),
        ('hl7-archive',       'Raw HL7 v2 messages — 30-day rolling window',    '45 GB',   C['purple']),
        ('fhir-responses',    'FHIR R4 API response cache',                     '28 GB',   C['orange']),
        ('lab-exports',       'CSV/Excel exports for research & audit',         '12 GB',   C['gray']),
    ]
    for i, (bucket, desc, size, color) in enumerate(buckets):
        y = 8.8 - i * 1.6
        box = FancyBboxPatch((0.3, y - 0.52), 9.4, 1.05,
                              boxstyle='round,pad=0.1',
                              fc='white', ec=color, lw=2, alpha=0.95)
        ax3.add_patch(box)
        ax3.text(0.65, y + 0.15, '🪣', fontsize=13, va='center')
        ax3.text(1.3,  y + 0.18, f's3://{bucket}', fontsize=9,
                 fontweight='bold', color=color, va='center')
        ax3.text(1.3,  y - 0.20, desc, fontsize=7.5, color=C['dark'], va='center')
        ax3.text(9.55, y,        size, fontsize=9, fontweight='bold',
                 color=color, va='center', ha='right')

    boto = ("# Python access via boto3\n"
            "import boto3\n"
            "s3 = boto3.client('s3',\n"
            "  endpoint_url='http://localhost:9000',\n"
            "  aws_access_key_id='admin',\n"
            "  aws_secret_access_key='MeditechSecret123!')\n"
            "\n"
            "# Download a DICOM scan\n"
            "s3.download_file(\n"
            "  'dicom-imaging',\n"
            "  'PT-007/ENC-014/cardiac_mri.dcm',\n"
            "  '/tmp/vikram_mri.dcm')")
    ax3.text(0.3, 0.75, boto, fontsize=6.5, family='monospace',
             va='bottom', color=C['dark'],
             bbox=dict(boxstyle='round,pad=0.4', fc='#eaf4fb',
                       ec=C['teal'], alpha=0.95, lw=1.5))

    fig.text(0.5, 0.02,
             'Bangalore City Hospital · Medical Informatics Lab · UE26MT324',
             ha='center', fontsize=8, color=C['gray'])

    out = f"{OUTPUT}/05_minio.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✓ {out}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("\nBangalore City Hospital — Meditech Lab Visualisations")
    print("=" * 54)
    fig_postgres()
    fig_elasticsearch()
    fig_kibana()
    fig_nifi()
    fig_minio()
    print(f"\n5 figures saved → ./{OUTPUT}/")
    print()
    for f in sorted(os.listdir(OUTPUT)):
        path = os.path.join(OUTPUT, f)
        kb   = os.path.getsize(path) // 1024
        print(f"  {f:<38} {kb:>4} KB")
    print()


if __name__ == "__main__":
    main()
