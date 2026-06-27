// app.js — Meditech Clinical Portal (Phase 1)
let TOKEN = sessionStorage.getItem("tok") || null;
let ROLE  = sessionStorage.getItem("role") || null;
let NAME  = sessionStorage.getItem("name") || null;
let LINKED = sessionStorage.getItem("linked") || null;

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const hide = (id) => $(id).classList.add("hidden");

async function api(path, method = "GET", body = null) {
  const opt = { method, headers: {} };
  if (TOKEN) opt.headers["Authorization"] = "Bearer " + TOKEN;
  if (body) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  const r = await fetch("/api" + path, opt);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
  return data;
}

async function login() {
  $("login-err").textContent = "";
  try {
    const d = await api("/login", "POST", { username: $("u").value.trim(), password: $("p").value });
    TOKEN = d.token; ROLE = d.role; NAME = d.full_name; LINKED = d.linked_id;
    sessionStorage.setItem("tok", TOKEN); sessionStorage.setItem("role", ROLE);
    sessionStorage.setItem("name", NAME || ""); sessionStorage.setItem("linked", LINKED || "");
    enterApp();
  } catch (e) { $("login-err").textContent = e.message; }
}

function logout() {
  TOKEN = ROLE = NAME = LINKED = null;
  sessionStorage.clear();
  ["admin-view", "doctor-view", "patient-view"].forEach(hide);
  hide("whoami"); show("login-view");
}

function enterApp() {
  hide("login-view");
  $("who-text").textContent = `${NAME || ""} · ${ROLE}`;
  show("whoami");
  if (ROLE === "admin")   { show("admin-view");   loadUsers(); loadAudit(); }
  if (ROLE === "doctor")  { show("doctor-view");  loadDocPatients(); initRisk("doc-risk"); }
  if (ROLE === "patient") { show("patient-view"); loadMyRecord(); initRisk("pt-risk"); }
}

// ── admin ──────────────────────────────────────────────────────────────────
function toggleLinked() {
  $("e-role").value === "patient" ? show("e-linked") : hide("e-linked");
}
async function enroll() {
  $("enroll-msg").textContent = "";
  try {
    const d = await api("/admin/enroll", "POST", {
      username: $("e-username").value.trim(), password: $("e-password").value,
      role: $("e-role").value, full_name: $("e-fullname").value.trim(),
      linked_id: $("e-role").value === "patient" ? $("e-linked").value.trim() : null,
    });
    $("enroll-msg").textContent = "✓ Enrolled " + d.user.username;
    $("enroll-msg").className = "msg ok";
    ["e-username", "e-fullname", "e-password", "e-linked"].forEach(i => $(i).value = "");
    loadUsers();
  } catch (e) { $("enroll-msg").textContent = "✗ " + e.message; $("enroll-msg").className = "msg err"; }
}
async function loadUsers() {
  const us = await api("/admin/users");
  $("user-list").innerHTML = us.map(u =>
    `<div class="row"><b>${u.username}</b> <span class="tag ${u.role}">${u.role}</span>
     <span class="muted">${u.linked_id || ""} ${u.full_name ? "· " + u.full_name : ""}</span></div>`).join("");
}
async function loadAudit() {
  const a = await api("/admin/audit?limit=40");
  $("audit-list").innerHTML = a.map(x =>
    `<div class="row">${x.accessed_at?.slice(0,19)?.replace("T"," ") || ""} · <b>${x.user_name}</b>
     ${x.action} ${x.table_name}/${x.record_id}</div>`).join("") || "<span class='muted'>No events.</span>";
}

// ── doctor ───────────────────────────────────────────────────────────────────
async function loadDocPatients() {
  const ps = await api("/patients");
  $("doc-patients").innerHTML = ps.map(p =>
    `<div class="row clickable" onclick="docDetail('${p.patient_id}')">
       <b>${p.full_name}</b> <span class="muted">${p.patient_id} · ${p.dept || ""} · ${p.gender}${p.age?" "+p.age+"y":""}</span>
     </div>`).join("");
  // fill the Q&A scope dropdown (default = All)
  const sel = $("doc-scope");
  sel.innerHTML = `<option value="">All patients + guidelines</option>` +
    ps.map(p => `<option value="${p.patient_id}">${p.full_name} (${p.patient_id})</option>`).join("");
}
async function docDetail(pid) {
  const p = await api("/patients/" + pid);
  renderRecord("doc-detail", p);
  $("doc-detail").insertAdjacentHTML("beforeend",
    `<div class="actions">
       <button class="ghost" onclick="runNews2('${pid}')">NEWS2 score</button>
       <button class="ghost" onclick="runCds('${pid}')">Decision support</button>
       <button class="ghost" onclick="runFhir('${pid}')">FHIR resource</button>
     </div><div id="doc-action-out" class="action-out"></div>
     <div class="docs" id="docs-${pid}">
       <div class="docs-head">
         <b>Documents</b>
         <span class="doc-actions">
           <button class="ghost" onclick="docForm('${pid}','lab')">+ Lab report</button>
           <button class="ghost" onclick="docForm('${pid}','prescription')">+ Clinical prescription</button>
           <button class="ghost" onclick="docForm('${pid}','discharge')">+ Discharge summary</button>
         </span>
       </div>
       <div id="docform-${pid}" class="docform"></div>
       <div id="doclist-${pid}" class="doclist"><span class="muted">Loading…</span></div>
     </div>`);
  loadDocs(pid, false);
}

// ── patient ──────────────────────────────────────────────────────────────────
async function loadMyRecord() {
  try {
    const p = await api("/me/record");
    renderRecord("pt-record", p);
    $("pt-record").insertAdjacentHTML("beforeend",
      `<div class="actions"><button class="ghost" onclick="runNews2('${p.patient_id}')">NEWS2 score</button></div>
       <div id="pt-action-out" class="action-out"></div>
       <div class="docs" id="docs-${p.patient_id}">
         <div class="docs-head">
           <b>My Documents</b>
           <span class="doc-actions">
             <button class="ghost" onclick="docForm('${p.patient_id}','patient-upload')">+ Add document</button>
           </span>
         </div>
         <div id="docform-${p.patient_id}" class="docform"></div>
         <div id="doclist-${p.patient_id}" class="doclist"><span class="muted">Loading…</span></div>
       </div>`);
    loadDocs(p.patient_id, true);
  }
  catch (e) { $("pt-record").textContent = e.message; }
}

function renderRecord(target, p) {
  const conds = (p.conditions || []).map(c =>
    `<span class="tag">${typeof c === "string" ? c : (c.icd10_code + " " + (c.description||""))}</span>`).join(" ");
  const obs = (p.observations || []).map(o => {
    const flag = o.flag || "";
    const cls = flag === "H" ? "high" : flag === "L" ? "low" : "norm";
    return `<span class="obs ${cls}">${o.name || o.display_name}: <b>${o.value}${o.unit||""}</b> ${flag}</span>`;
  }).join(" ");
  $(target).innerHTML = `
    <div class="pt-head">${p.full_name} <span class="muted">${p.patient_id}${p.gender?" · "+p.gender:""}${p.age?" · "+p.age+"y":""}</span></div>
    <div class="sub">Conditions</div><div>${conds || "<span class='muted'>none</span>"}</div>
    <div class="sub">Observations</div><div class="obs-row">${obs || "<span class='muted'>none</span>"}</div>`;
}

// ── Phase 4 actions: NEWS2 / CDS / FHIR ──────────────────────────────────────
function _actionOut() { return $("doc-action-out") || $("pt-action-out"); }

function renderNews2(d) {
  const rows = Object.entries(d.breakdown || {}).map(([k, v]) =>
    `<span class="obs ${v.points >= 3 ? 'high' : v.points >= 1 ? 'low' : 'norm'}">${v.name}: ${v.value}${v.unit || ''} → +${v.points}</span>`).join(" ");
  const cls = d.risk === 'high' ? 'high' : d.risk === 'medium' ? 'low' : 'norm';
  return `<div><b>NEWS2 = ${d.score}</b> · <span class="obs ${cls}">${d.risk} risk</span> — ${d.action}</div>
          <div class="obs-row" style="margin-top:8px">${rows || "<span class='muted'>no scoreable vitals</span>"}</div>
          ${d.missing && d.missing.length ? `<div class="muted" style="margin-top:6px">missing params: ${d.missing.join(', ')}</div>` : ''}`;
}

async function runNews2(pid) {
  const out = _actionOut(); out.innerHTML = "…";
  try { out.innerHTML = renderNews2(await api(`/patients/${pid}/news2`)); }
  catch (e) { out.textContent = e.message; }
}

async function runCds(pid) {
  const out = _actionOut(); out.innerHTML = "<span class='muted'>Generating assessment… (~15s)</span>";
  try {
    const d = await api(`/cds/${pid}`, "POST", {});
    const cites = (d.citations && d.citations.length)
      ? `<div class="cites"><b>Sources</b> ` + d.citations.map(c =>
          `<span class="tag">[${c.n}] ${c.source_type}${c.patient_id ? " " + c.patient_id : ""} · ${c.title}</span>`).join(" ") + `</div>` : "";
    out.innerHTML = `${d.news2 ? renderNews2(d.news2) + "<hr style='border-color:#30363d;margin:12px 0'>" : ""}
      <div class="ans-body">${(d.answer || "").replace(/\n/g, "<br>")}</div>${cites}`;
  } catch (e) { out.textContent = e.message; }
}

async function runFhir(pid) {
  const out = _actionOut(); out.innerHTML = "…";
  try {
    const d = await api(`/fhir/Patient/${pid}/everything`);
    const counts = {};
    (d.entry || []).forEach(e => {
      const t = e.resource.resourceType; counts[t] = (counts[t] || 0) + 1;
    });
    const summary = Object.entries(counts).map(([k, v]) => `${v} ${k}`).join(" · ");
    out.innerHTML =
      `<div class="ans-meta"><span class="tag doctor">FHIR R4 Bundle</span>
         <span class="muted">${summary || "no resources"}</span></div>
       <pre class="mono fhir">${JSON.stringify(d, null, 2)}</pre>`;
  } catch (e) { out.textContent = e.message; }
}

// ── Familial Risk Calculator ─────────────────────────────────────────────────
const RISK_RELATIONS = ["parent", "sibling", "child", "grandparent", "aunt", "uncle", "cousin"];

async function initRisk(target) {
  try {
    const meta = await api("/familial-risk/conditions");
    const opts = meta.conditions.map(c =>
      `<option value="${c.key}">${c.label}${c.model === "mendelian" ? " — " + c.inheritance : ""}</option>`).join("");
    const chips = RISK_RELATIONS.map(r =>
      `<button type="button" class="chip" data-rel="${r}" onclick="toggleRel(this)">${r}</button>`).join("");
    $(target).innerHTML = `
      <div class="risk-controls">
        <label class="risk-lbl">Condition</label>
        <select id="${target}-cond">${opts}</select>
        <label class="risk-lbl">Affected relatives <span class="muted">(tap all that apply)</span></label>
        <div class="chips" id="${target}-chips">${chips}</div>
        <button class="primary" onclick="assessRisk('${target}')">Assess risk</button>
      </div>
      <div class="risk-result" id="${target}-out"></div>`;
  } catch (e) { $(target).textContent = e.message; }
}

function toggleRel(btn) { btn.classList.toggle("on"); }

function riskColor(cat) {
  return cat === "high" ? "#ff6b6b" : cat === "moderate" ? "#f0a020" : "#3fb950";
}

function gaugeSVG(pct, color) {
  const r = 70, c = 2 * Math.PI * r, frac = Math.max(0, Math.min(100, pct)) / 100;
  const dash = (frac * c).toFixed(1), gap = (c - frac * c).toFixed(1);
  return `<svg viewBox="0 0 180 180" class="gauge">
    <circle cx="90" cy="90" r="${r}" fill="none" stroke="#21262d" stroke-width="14"/>
    <circle cx="90" cy="90" r="${r}" fill="none" stroke="${color}" stroke-width="14"
      stroke-linecap="round" stroke-dasharray="${dash} ${gap}"
      transform="rotate(-90 90 90)" style="transition:stroke-dasharray .9s ease"/>
    <text x="90" y="84" text-anchor="middle" class="gauge-num" fill="${color}">${pct}%</text>
    <text x="90" y="106" text-anchor="middle" class="gauge-sub">lifetime risk</text>
  </svg>`;
}

async function assessRisk(target) {
  const cond = $(`${target}-cond`).value;
  const relatives = [...document.querySelectorAll(`#${target}-chips .chip.on`)].map(b => b.dataset.rel);
  const out = $(`${target}-out`);
  out.innerHTML = "<span class='muted'>Calculating…</span>";
  try {
    const d = await api("/familial-risk", "POST", { condition: cond, relatives });
    const color = riskColor(d.category);
    const base = d.baseline_pct != null
      ? `<div class="risk-stat"><span>${d.baseline_pct}%</span><label>population baseline</label></div>` : "";
    const ratio = d.risk_ratio != null
      ? `<div class="risk-stat"><span>${d.risk_ratio}×</span><label>vs baseline</label></div>` : "";
    const inh = d.inheritance
      ? `<div class="risk-stat"><span>${d.inheritance}</span><label>inheritance</label></div>` : "";
    const factors = (d.factors && d.factors.length)
      ? `<div class="risk-factors">${d.factors.map(f =>
          `<span class="tag">${f.relation} · ${f.degree}°${f.multiplier ? " · " + f.multiplier + "×" : ""}</span>`).join(" ")}</div>` : "";
    out.innerHTML = `
      <div class="risk-readout">
        ${gaugeSVG(d.estimated_pct, color)}
        <div class="risk-meta">
          <div class="risk-cat" style="color:${color}">${d.category.toUpperCase()} RISK</div>
          <div class="risk-stats">${base}${ratio}${inh}</div>
          <p class="risk-exp">${d.explanation}</p>
          ${factors}
        </div>
      </div>
      <p class="risk-disc">${d.disclaimer}</p>`;
  } catch (e) { out.textContent = e.message; }
}

// ── Patient documents (MinIO) ─────────────────────────────────────────────────
const DOC_ICON = { lab: "🧪", prescription: "💊", discharge: "📄", fhir: "🔗", imaging: "🩻", "patient-upload": "📎" };

async function loadDocs(pid, readonly) {
  const list = $(`doclist-${pid}`);
  try {
    const d = await api(`/patients/${pid}/documents`);
    if (!d.documents.length) { list.innerHTML = "<span class='muted'>No documents yet.</span>"; return; }
    list.innerHTML = d.documents.map(doc => {
      const kb = (doc.size / 1024).toFixed(1);
      const when = (doc.modified || "").slice(0, 10);
      return `<div class="docrow">
        <span class="docname">${DOC_ICON[doc.kind] || "📁"} ${doc.name}</span>
        <span class="muted">${doc.kind} · ${kb} KB · ${when}</span>
        <button class="ghost" onclick="openDoc('${doc.bucket}','${doc.key}')">view</button>
      </div>`;
    }).join("");
  } catch (e) { list.innerHTML = `<span class="muted">${e.message}</span>`; }
}

function openDoc(bucket, key) {
  // open in a new tab with the auth token via fetch->blob (header can't go in <a href>)
  fetch(`/api/documents/${bucket}/${encodeURIComponent(key).replace(/%2F/g, "/")}`,
        { headers: { Authorization: "Bearer " + TOKEN } })
    .then(r => r.ok ? r.blob() : r.json().then(j => { throw new Error(j.detail || r.status); }))
    .then(b => window.open(URL.createObjectURL(b), "_blank"))
    .catch(e => alert("Could not open: " + e.message));
}

function docForm(pid, kind) {
  const box = $(`docform-${pid}`);
  const labels = { lab: "Lab report", prescription: "Clinical prescription",
                   discharge: "Discharge summary", "patient-upload": "Document" };
  let fields;
  if (kind === "discharge") {
    fields = `
      <input id="df-diag-${pid}" placeholder="Principal diagnosis">
      <input id="df-meds-${pid}" placeholder="Medications on discharge">
      <input id="df-fu-${pid}" placeholder="Follow-up instructions">`;
  } else if (kind === "prescription") {
    fields = `
      <input id="df-med-${pid}" placeholder="Medication (e.g. Metformin)">
      <input id="df-dose-${pid}" placeholder="Dosage (e.g. 1000mg)">
      <input id="df-freq-${pid}" placeholder="Frequency (e.g. BD / twice daily)">
      <input id="df-dur-${pid}" placeholder="Duration (e.g. 3 months)">
      <input id="df-notes-${pid}" placeholder="Notes (optional)">`;
  } else {
    fields = `
      <textarea id="df-text-${pid}" rows="3" placeholder="Type ${labels[kind].toLowerCase()} text…"></textarea>
      <div class="docform-or">or attach a file</div>
      <input type="file" id="df-file-${pid}">`;
  }
  box.innerHTML = `<div class="docform-inner">
    <div class="docform-title">New ${labels[kind]}</div>
    ${fields}
    <div class="docform-btns">
      <button class="primary" onclick="submitDoc('${pid}','${kind}')">Save</button>
      <button class="ghost" onclick="$('docform-${pid}').innerHTML=''">Cancel</button>
    </div>
    <div id="df-msg-${pid}" class="muted"></div>
  </div>`;
}

async function submitDoc(pid, kind) {
  const msg = $(`df-msg-${pid}`);
  const fd = new FormData();
  fd.append("kind", kind);
  if (kind === "discharge") {
    fd.append("diagnosis", ($(`df-diag-${pid}`).value || ""));
    fd.append("medications", ($(`df-meds-${pid}`).value || ""));
    fd.append("followup", ($(`df-fu-${pid}`).value || ""));
  } else if (kind === "prescription") {
    const med = $(`df-med-${pid}`).value.trim();
    if (!med) { msg.textContent = "Medication is required."; return; }
    fd.append("medication", med);
    fd.append("dosage", ($(`df-dose-${pid}`).value || ""));
    fd.append("frequency", ($(`df-freq-${pid}`).value || ""));
    fd.append("duration", ($(`df-dur-${pid}`).value || ""));
    fd.append("notes", ($(`df-notes-${pid}`).value || ""));
  } else {
    const f = $(`df-file-${pid}`).files[0];
    const txt = $(`df-text-${pid}`).value.trim();
    if (f) fd.append("file", f);
    else if (txt) fd.append("text", txt);
    else { msg.textContent = "Enter text or choose a file."; return; }
  }
  msg.textContent = "Saving…";
  try {
    const r = await fetch(`/api/patients/${pid}/documents`,
      { method: "POST", headers: { Authorization: "Bearer " + TOKEN }, body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || ("HTTP " + r.status));
    $(`docform-${pid}`).innerHTML = "";
    loadDocs(pid, false);
  } catch (e) { msg.textContent = e.message; }
}

// ── RAG ──────────────────────────────────────────────────────────────────────
async function ask(who) {
  const q = who === "doctor" ? $("doc-q").value : $("pt-q").value;
  const out = who === "doctor" ? "doc-answer" : "pt-answer";
  if (!q.trim()) return;
  $(out).innerHTML = "<span class='muted'>Thinking… (first call can take ~10–20s on the local model)</span>";
  const body = { question: q };
  if (who === "doctor") body.patient_id = $("doc-scope").value || null;
  try {
    const d = await api("/rag/query", "POST", body);
    let cites = "";
    if (d.citations && d.citations.length) {
      cites = `<div class="cites"><b>Sources</b> ` + d.citations.map(c =>
        `<span class="tag">[${c.n}] ${c.source_type}${c.patient_id ? " " + c.patient_id : ""} · ${c.title}</span>`).join(" ") + `</div>`;
    }
    const badge = d.grounded === false ? `<span class="tag admin">ungrounded</span>` :
                  `<span class="tag patient">grounded · ${d.n_context} sources</span>`;
    $(out).innerHTML = `<div class="ans-meta">${badge} <span class="muted">scope: ${d.scope || "all"}</span></div>
                        <div class="ans-body">${(d.answer||"").replace(/\n/g,"<br>")}</div>${cites}`;
  } catch (e) { $(out).textContent = e.message; }
}

// ── boot ─────────────────────────────────────────────────────────────────────
if (TOKEN && ROLE) { enterApp(); } else { show("login-view"); }
