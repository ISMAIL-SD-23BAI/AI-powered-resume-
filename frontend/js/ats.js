const API = "http://127.0.0.1:8000";
const token = localStorage.getItem("token");
if (!token) window.location.href = "login.html";

function authHeaders() {
  return { Authorization: `Bearer ${token}` };
}
function jsonHeaders() {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
  });
}

function handle401(res) {
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "login.html";
    return true;
  }
  return false;
}

// ── State ──────────────────────────────────────────────────────────────────────

let currentMatchId = null;
let currentResumeId = null;

// ── Resumes ────────────────────────────────────────────────────────────────────

async function loadResumes() {
  const res = await fetch(`${API}/resumes/`, { headers: authHeaders() });
  if (handle401(res)) return;

  const resumes = await res.json();
  const sel = document.getElementById("resume-select");
  const btn = document.getElementById("analyze-btn");

  if (!resumes.length) {
    sel.innerHTML = '<option value="">No resumes — upload one below</option>';
    btn.disabled = true;
    return;
  }

  sel.innerHTML = resumes
    .map(r => `<option value="${r.id}">${escHtml(r.filename)}</option>`)
    .join("");

  btn.disabled = false;
  currentResumeId = parseInt(sel.value);
  updateTailorLink();
}

document.getElementById("resume-select").addEventListener("change", function () {
  const val = parseInt(this.value);
  const btn = document.getElementById("analyze-btn");
  btn.disabled = !val;
  currentResumeId = val || null;
  updateTailorLink();
});

function updateTailorLink() {
  const link = document.getElementById("tailor-link");
  if (currentResumeId) {
    link.href = `tailor.html?resume_id=${currentResumeId}`;
  } else {
    link.href = "tailor.html";
  }
}

// ── Quick upload ───────────────────────────────────────────────────────────────

document.getElementById("resume-file-input").addEventListener("change", async function () {
  const file = this.files[0];
  if (!file) return;

  const statusEl = document.getElementById("quick-upload-status");
  statusEl.textContent = "Uploading…";
  statusEl.className = "quick-upload-status";

  const body = new FormData();
  body.append("file", file);

  let res;
  try {
    res = await fetch(`${API}/resumes/upload`, {
      method: "POST",
      headers: authHeaders(),
      body,
    });
  } catch {
    statusEl.textContent = "Network error";
    statusEl.className = "quick-upload-status error";
    return;
  }

  if (handle401(res)) return;

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    statusEl.textContent = err.detail || "Upload failed";
    statusEl.className = "quick-upload-status error";
    return;
  }

  const uploaded = await res.json();
  statusEl.textContent = "Uploaded";
  statusEl.className = "quick-upload-status ok";
  setTimeout(() => (statusEl.textContent = ""), 3000);

  // Refresh resume list and select the new one
  const sel = document.getElementById("resume-select");
  await loadResumes();
  const opt = sel.querySelector(`option[value="${uploaded.id}"]`);
  if (opt) {
    opt.selected = true;
    currentResumeId = uploaded.id;
    document.getElementById("analyze-btn").disabled = false;
    updateTailorLink();
  }

  this.value = "";
});

// ── Analyze form ───────────────────────────────────────────────────────────────

document.getElementById("ats-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const resume_id = parseInt(document.getElementById("resume-select").value);
  const job_description_text = document.getElementById("jd-textarea").value.trim();

  if (!resume_id) {
    setAnalyzeStatus("Please select a resume.", "error");
    return;
  }
  if (job_description_text.length < 10) {
    setAnalyzeStatus("Please paste a job description (at least 10 characters).", "error");
    return;
  }

  const btn = document.getElementById("analyze-btn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Analyzing…';
  setAnalyzeStatus("Running local analysis — this is fast…", "info");
  document.getElementById("result-section").style.display = "none";

  currentResumeId = resume_id;

  let res;
  try {
    res = await fetch(`${API}/match/`, {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify({ resume_id, job_description_text }),
    });
  } catch {
    btn.disabled = false;
    btn.textContent = "Analyze Compatibility";
    setAnalyzeStatus("Network error — is the server running?", "error");
    return;
  }

  btn.disabled = false;
  btn.textContent = "Analyze Compatibility";

  if (handle401(res)) return;

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Analysis failed" }));
    setAnalyzeStatus("Error: " + (err.detail || "Analysis failed"), "error");
    return;
  }

  setAnalyzeStatus("", "");
  const data = await res.json();
  renderResult(data);
  await loadHistory();
});

function setAnalyzeStatus(msg, type) {
  const el = document.getElementById("analyze-status");
  el.textContent = msg;
  el.className = "analyze-status" + (type ? " " + type : "");
}

// ── Render result ──────────────────────────────────────────────────────────────

function renderResult(data) {
  currentMatchId = data.id;
  currentResumeId = data.resume_id;
  updateTailorLink();

  animateScoreRing(data.overall_score);
  renderComponentBars(data);
  renderSkills(data);
  renderRecommendations(data);

  // JD role badge
  const badge = document.getElementById("jd-role-badge");
  if (data.jd_role_title) {
    badge.textContent = data.jd_role_title;
    badge.style.display = "inline-flex";
  } else {
    badge.style.display = "none";
  }

  // Disclaimer
  if (data.disclaimer) {
    document.getElementById("disclaimer-text").textContent = data.disclaimer;
  }

  const resultSection = document.getElementById("result-section");
  resultSection.style.display = "block";
  resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Score ring animation ───────────────────────────────────────────────────────

function animateScoreRing(score) {
  const CIRC = 314.16;
  const fill = document.getElementById("score-ring-fill");
  const numEl = document.getElementById("score-number");
  const pctEl = document.getElementById("score-pct");
  const gradeEl = document.getElementById("score-grade");

  const color = score >= 70 ? "var(--success)" : score >= 50 ? "var(--warning)" : "var(--danger)";
  fill.style.stroke = color;

  // Reset before animating so transition fires every time
  fill.style.transition = "none";
  fill.style.strokeDashoffset = CIRC;
  numEl.textContent = "0";

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      fill.style.transition = "stroke-dashoffset 1.1s cubic-bezier(0.22,1,0.36,1), stroke 0.3s";
      fill.style.strokeDashoffset = CIRC * (1 - score / 100);
    });
  });

  // Counter animation
  let current = 0;
  const step = Math.max(1, Math.ceil(score / 40));
  const timer = setInterval(() => {
    current = Math.min(current + step, score);
    numEl.textContent = current;
    if (current >= score) clearInterval(timer);
  }, 25);

  pctEl.style.display = "";
  gradeEl.textContent = score >= 70 ? "Strong Match" : score >= 50 ? "Moderate Match" : "Weak Match";
  gradeEl.style.color = color;
}

// ── Component score bars ───────────────────────────────────────────────────────

function barColorClass(score) {
  if (score >= 70) return "bar-success";
  if (score >= 50) return "bar-warning";
  return "bar-danger";
}

function setBar(barId, valId, score) {
  const bar = document.getElementById(barId);
  const val = document.getElementById(valId);
  const pct = Math.round(score);
  val.textContent = pct + "%";
  // Reset width for animation
  bar.style.width = "0%";
  bar.className = "score-bar-fill " + barColorClass(pct);
  requestAnimationFrame(() => {
    bar.style.width = pct + "%";
  });
}

function renderComponentBars(data) {
  setBar("req-score-bar",  "req-score-val",  data.required_skill_score  || 0);
  setBar("exp-score-bar",  "exp-score-val",  data.experience_score      || 0);
  setBar("pref-score-bar", "pref-score-val", data.preferred_skill_score || 0);
  setBar("edu-score-bar",  "edu-score-val",  data.education_score       || 0);
}

// ── Skills ─────────────────────────────────────────────────────────────────────

function skillEntryHtml(match, entryClass) {
  const typeCls = match.match_type === "exact"     ? "skill-type-exact"
                : match.match_type === "semantic"  ? "skill-type-semantic"
                :                                    "skill-type-partial";
  const typeLabel = match.match_type === "exact"
    ? "exact"
    : `~${Math.round((match.confidence || 0) * 100)}%`;
  const sections = (match.resume_sections || []).join(", ");

  return `<li class="skill-entry ${entryClass}">
    <span class="skill-entry-name">${escHtml(match.skill)}</span>
    <div class="skill-entry-row">
      <span class="skill-match-badge ${typeCls}">${escHtml(typeLabel)}</span>
      ${sections ? `<span class="skill-entry-source">in: ${escHtml(sections)}</span>` : ""}
    </div>
  </li>`;
}

function renderSkills(data) {
  const matched  = data.matched_requirements || [];
  const partial  = data.partial_matches      || [];
  const missing  = data.missing_requirements || [];

  // Matched
  const matchedList  = document.getElementById("matched-list");
  const matchedEmpty = document.getElementById("matched-empty");
  const matchedCount = document.getElementById("matched-count");
  matchedCount.textContent = matched.length;
  if (matched.length) {
    matchedList.innerHTML  = matched.map(m => skillEntryHtml(m, "skill-entry-matched")).join("");
    matchedEmpty.style.display = "none";
    matchedList.style.display  = "";
  } else {
    matchedList.innerHTML  = "";
    matchedEmpty.style.display = "";
    matchedList.style.display  = "none";
  }

  // Partial
  const partialList  = document.getElementById("partial-list");
  const partialEmpty = document.getElementById("partial-empty");
  const partialCount = document.getElementById("partial-count");
  partialCount.textContent = partial.length;
  if (partial.length) {
    partialList.innerHTML  = partial.map(m => skillEntryHtml(m, "skill-entry-partial")).join("");
    partialEmpty.style.display = "none";
    partialList.style.display  = "";
  } else {
    partialList.innerHTML  = "";
    partialEmpty.style.display = "";
    partialList.style.display  = "none";
  }

  // Missing
  const missingList  = document.getElementById("missing-list");
  const missingEmpty = document.getElementById("missing-empty");
  const missingCount = document.getElementById("missing-count");
  missingCount.textContent = missing.length;
  if (missing.length) {
    missingList.innerHTML = missing.map(skill => `
      <li class="skill-entry skill-entry-missing">
        <span class="skill-entry-name">${escHtml(skill)}</span>
        <span class="skill-missing-note">not evidenced in resume</span>
      </li>`).join("");
    missingEmpty.style.display = "none";
    missingList.style.display  = "";
  } else {
    missingList.innerHTML  = "";
    missingEmpty.style.display = "";
    missingList.style.display  = "none";
  }
}

// ── Recommendations ────────────────────────────────────────────────────────────

function renderRecommendations(data) {
  const recs = data.recommendations || [];
  const list = document.getElementById("recommendations-list");
  if (!recs.length) {
    list.innerHTML = '<li class="rec-item"><span class="rec-text" style="color:var(--muted)">No specific recommendations — great alignment!</span></li>';
    return;
  }
  let html = "";
  recs.forEach((rec, i) => {
    html += `<li class="rec-item">
      <span class="rec-num">${i + 1}</span>
      <span class="rec-text">${escHtml(rec)}</span>
    </li>`;
  });
  list.innerHTML = html;
}

// ── Action buttons ─────────────────────────────────────────────────────────────

document.getElementById("analyze-another-btn").addEventListener("click", () => {
  document.getElementById("result-section").style.display = "none";
  document.getElementById("jd-textarea").value = "";
  setAnalyzeStatus("", "");
  currentMatchId = null;
  window.scrollTo({ top: 0, behavior: "smooth" });
});

document.getElementById("delete-result-btn").addEventListener("click", () => {
  if (!currentMatchId) return;
  openDeleteDialog(currentMatchId, true);
});

// ── Delete dialog ──────────────────────────────────────────────────────────────

let pendingDeleteId = null;
let pendingDeleteIsCurrentResult = false;
const deleteDialog = document.getElementById("delete-dialog");

function openDeleteDialog(id, isCurrentResult) {
  pendingDeleteId = id;
  pendingDeleteIsCurrentResult = isCurrentResult || false;
  deleteDialog.showModal();
}

document.getElementById("delete-confirm-btn").addEventListener("click", async () => {
  deleteDialog.close();
  if (!pendingDeleteId) return;

  const id = pendingDeleteId;
  const isResult = pendingDeleteIsCurrentResult;
  pendingDeleteId = null;
  pendingDeleteIsCurrentResult = false;

  // Dim the history card immediately
  const card = document.querySelector(`#ats-history-list .hist-card[data-id="${id}"]`);
  if (card) card.style.opacity = "0.4";

  const res = await fetch(`${API}/match/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });

  if (handle401(res)) return;

  if (res.ok || res.status === 204) {
    if (isResult) {
      document.getElementById("result-section").style.display = "none";
      currentMatchId = null;
    }
    if (card) card.remove();
    refreshHistoryCount();
  } else {
    if (card) card.style.opacity = "1";
    alert("Delete failed — please try again.");
  }
});

document.getElementById("delete-cancel-btn").addEventListener("click", () => {
  deleteDialog.close();
  pendingDeleteId = null;
});
deleteDialog.addEventListener("click", (e) => {
  if (e.target === deleteDialog) {
    deleteDialog.close();
    pendingDeleteId = null;
  }
});

// ── History ────────────────────────────────────────────────────────────────────

function renderHistoryItem(item) {
  const score = item.overall_score;
  const cls = score >= 70 ? "badge-ok" : score >= 50 ? "badge-warn" : "badge-low";
  const role = item.jd_role_title
    ? escHtml(item.jd_role_title)
    : '<span class="hist-unknown">Unknown Role</span>';

  return `<li class="hist-card" data-id="${item.id}">
    <div class="hist-card-main">
      <div class="hist-role-row">
        <strong class="hist-role">${role}</strong>
        <span class="badge ${cls}">Match: ${score}%</span>
      </div>
      <div class="hist-meta">
        <span>${fmtDate(item.created_at)}</span>
      </div>
    </div>
    <div class="hist-card-actions">
      <button class="btn btn-outline btn-sm btn-view-match" data-id="${item.id}">View</button>
      <button class="btn btn-sm btn-delete" data-id="${item.id}">Delete</button>
    </div>
  </li>`;
}

async function loadHistory() {
  const loadingEl = document.getElementById("ats-history-loading");
  const emptyEl   = document.getElementById("ats-history-empty");
  const listEl    = document.getElementById("ats-history-list");
  const countEl   = document.getElementById("ats-history-count");

  loadingEl.style.display = "block";
  emptyEl.style.display   = "none";
  listEl.style.display    = "none";

  const res = await fetch(`${API}/match/`, { headers: authHeaders() });
  if (handle401(res)) return;

  loadingEl.style.display = "none";
  const items = await res.json();

  if (!items.length) {
    emptyEl.style.display = "block";
    countEl.textContent   = "";
    return;
  }

  countEl.textContent  = `${items.length} anal${items.length === 1 ? "ysis" : "yses"}`;
  listEl.innerHTML     = items.map(renderHistoryItem).join("");
  listEl.style.display = "flex";

  listEl.querySelectorAll(".btn-view-match").forEach(btn => {
    btn.addEventListener("click", () => viewMatchResult(parseInt(btn.dataset.id)));
  });

  listEl.querySelectorAll(".btn-delete").forEach(btn => {
    btn.addEventListener("click", () => openDeleteDialog(parseInt(btn.dataset.id), false));
  });
}

async function viewMatchResult(id) {
  const btn = document.querySelector(`.btn-view-match[data-id="${id}"]`);
  if (btn) { btn.disabled = true; btn.textContent = "Loading…"; }

  let res;
  try {
    res = await fetch(`${API}/match/${id}`, { headers: authHeaders() });
  } catch {
    if (btn) { btn.disabled = false; btn.textContent = "View"; }
    alert("Network error — is the server running?");
    return;
  }

  if (btn) { btn.disabled = false; btn.textContent = "View"; }
  if (handle401(res)) return;
  if (!res.ok) { alert("Could not load analysis."); return; }

  const data = await res.json();
  renderResult(data);

  // Update the select to match this result's resume
  const sel = document.getElementById("resume-select");
  const opt = sel.querySelector(`option[value="${data.resume_id}"]`);
  if (opt) { opt.selected = true; }
  currentResumeId = data.resume_id;
  updateTailorLink();
}

function refreshHistoryCount() {
  const listEl  = document.getElementById("ats-history-list");
  const emptyEl = document.getElementById("ats-history-empty");
  const countEl = document.getElementById("ats-history-count");
  const remaining = listEl.querySelectorAll(".hist-card").length;
  if (!remaining) {
    listEl.style.display  = "none";
    emptyEl.style.display = "block";
    countEl.textContent   = "";
  } else {
    countEl.textContent = `${remaining} anal${remaining === 1 ? "ysis" : "yses"}`;
  }
}

// ── Logout ─────────────────────────────────────────────────────────────────────

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("token");
  window.location.href = "login.html";
});

// ── Init ───────────────────────────────────────────────────────────────────────

loadResumes();
loadHistory();
