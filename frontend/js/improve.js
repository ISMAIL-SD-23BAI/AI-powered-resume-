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

let currentSessionId = null;
let currentSessionData = null;
let currentTotalSuggestions = 0;
let currentAcceptedCount = 0;

// ── Resumes ────────────────────────────────────────────────────────────────────

async function loadResumes() {
  const res = await fetch(`${API}/resumes/`, { headers: authHeaders() });
  if (handle401(res)) return;

  const resumes = await res.json();
  const sel = document.getElementById("resume-select");
  const btn = document.getElementById("generate-btn");

  if (!resumes.length) {
    sel.innerHTML = '<option value="">No resumes — upload one on the Dashboard first</option>';
    btn.disabled = true;
    return;
  }

  sel.innerHTML = resumes
    .map(r => `<option value="${r.id}">${escHtml(r.filename)}</option>`)
    .join("");
  btn.disabled = false;
}

document.getElementById("resume-select").addEventListener("change", function () {
  document.getElementById("generate-btn").disabled = !this.value;
});

// ── Form submit ────────────────────────────────────────────────────────────────

document.getElementById("improve-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const resume_id = parseInt(document.getElementById("resume-select").value);
  const job_description_text = document.getElementById("jd-textarea").value.trim();

  if (!resume_id) {
    setStatus("Please select a resume.", "error");
    return;
  }
  if (job_description_text.length < 50) {
    setStatus("Please paste a job description (at least 50 characters).", "error");
    return;
  }

  const btn = document.getElementById("generate-btn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Generating…';
  setStatus("Contacting AI — this may take 20–40 seconds…", "info");
  document.getElementById("result-section").style.display = "none";

  let res;
  try {
    res = await fetch(`${API}/improve/`, {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify({ resume_id, job_description_text }),
    });
  } catch {
    btn.disabled = false;
    btn.textContent = "Generate Suggestions";
    setStatus("Network error — is the server running?", "error");
    return;
  }

  btn.disabled = false;
  btn.textContent = "Generate Suggestions";

  if (handle401(res)) return;

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    setStatus("Error: " + (err.detail || "Generation failed"), "error");
    return;
  }

  setStatus("", "");
  const data = await res.json();
  renderSession(data);
  await loadHistory();
});

function setStatus(msg, type) {
  const el = document.getElementById("generate-status");
  el.textContent = msg;
  el.className = "analyze-status" + (type ? " " + type : "");
}

// ── Word-level diff (LCS) ──────────────────────────────────────────────────────

function wordDiff(original, suggested) {
  const aWords = (original || "").split(/\s+/).filter(Boolean);
  const bWords = (suggested || "").split(/\s+/).filter(Boolean);
  const m = aWords.length, n = bWords.length;

  const dp = [];
  for (let i = 0; i <= m; i++) dp.push(new Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] = aWords[i - 1].toLowerCase() === bWords[j - 1].toLowerCase()
        ? dp[i - 1][j - 1] + 1
        : Math.max(dp[i - 1][j], dp[i][j - 1]);
    }
  }

  const ops = [];
  let i = m, j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && aWords[i - 1].toLowerCase() === bWords[j - 1].toLowerCase()) {
      ops.unshift({ type: "same", word: bWords[j - 1] });
      i--; j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      ops.unshift({ type: "add", word: bWords[j - 1] });
      j--;
    } else {
      ops.unshift({ type: "del", word: aWords[i - 1] });
      i--;
    }
  }

  return ops.map(op => {
    const w = escHtml(op.word);
    if (op.type === "add") return `<mark class="diff-add">${w}</mark>`;
    if (op.type === "del") return `<span class="diff-del">${w}</span>`;
    return w;
  }).join(" ");
}

// ── Card ID helpers ────────────────────────────────────────────────────────────

function makeCardId(section, indices) {
  if (section === "summary") return "summary";
  if (section === "experience") return `experience-${indices.job_index}-${indices.bullet_index}`;
  if (section === "project") return `project-${indices.project_index}-${indices.bullet_index}`;
  if (section === "skills") return "skills";
  return "unknown";
}

function decodeCardId(cardId) {
  if (cardId === "summary") return { section: "summary" };
  if (cardId === "skills") return { section: "skills" };
  const parts = cardId.split("-");
  if (parts[0] === "experience") {
    return { section: "experience", job_index: parseInt(parts[1]), bullet_index: parseInt(parts[2]) };
  }
  if (parts[0] === "project") {
    return { section: "project", project_index: parseInt(parts[1]), bullet_index: parseInt(parts[2]) };
  }
  return { section: "unknown" };
}

// ── Build suggestion card HTML ─────────────────────────────────────────────────

function bulletCardHtml(section, indices, bsug) {
  const cardId = makeCardId(section, indices);
  const displayText = bsug.custom_text || bsug.suggested || "";
  const statusClass = bsug.status === "accepted" ? "suggestion-accepted"
    : bsug.status === "rejected" ? "suggestion-rejected" : "";

  let flagHtml = "";
  if (bsug.flagged && bsug.flag_reason) {
    flagHtml = `<div class="flag-banner">
      <span class="flag-icon">⚠</span>
      <span>Verify before accepting: ${escHtml(bsug.flag_reason)}</span>
    </div>`;
  }

  const acceptActive = bsug.status === "accepted" ? " active" : "";
  const rejectActive = bsug.status === "rejected" ? " active" : "";

  const customBadge = bsug.custom_text
    ? `<span class="custom-edit-badge">Edited</span>` : "";

  return `
  <div class="suggestion-card ${statusClass}" id="card-${escHtml(cardId)}">
    ${flagHtml}
    <div class="suggestion-panels">
      <div class="panel-orig">
        <div class="panel-label">Original</div>
        <div class="panel-text">${escHtml(bsug.original || "")}</div>
      </div>
      <div class="panel-sugg">
        <div class="panel-label">Suggested ${customBadge}</div>
        <div class="panel-text diff-text" id="difftext-${escHtml(cardId)}">${wordDiff(bsug.original || "", displayText)}</div>
      </div>
    </div>
    ${bsug.reason ? `<div class="suggestion-reason"><strong>Why:</strong> ${escHtml(bsug.reason)}</div>` : ""}
    <div class="suggestion-actions">
      <button class="btn btn-sm btn-accept${acceptActive}" onclick="handleAccept('${cardId}')">✓ Accept</button>
      <button class="btn btn-sm btn-reject${rejectActive}" onclick="handleReject('${cardId}')">✗ Reject</button>
      <button class="btn btn-sm btn-outline" onclick="handleEdit('${cardId}')">✏ Edit</button>
    </div>
    <div class="edit-mode" id="edit-${escHtml(cardId)}" style="display:none">
      <textarea class="edit-textarea" id="edittext-${escHtml(cardId)}" rows="3">${escHtml(bsug.custom_text || bsug.suggested || "")}</textarea>
      <div class="edit-actions">
        <button class="btn btn-sm btn-primary" onclick="handleSaveEdit('${cardId}')">Save</button>
        <button class="btn btn-sm btn-ghost" onclick="handleCancelEdit('${cardId}')">Cancel</button>
      </div>
    </div>
  </div>`;
}

function skillsCardHtml(skl) {
  const hasFlagged = skl.added_skills && skl.added_skills.length > 0;
  const statusClass = skl.status === "accepted" ? "suggestion-accepted"
    : skl.status === "rejected" ? "suggestion-rejected" : "";

  const acceptActive = skl.status === "accepted" ? " active" : "";
  const rejectActive = skl.status === "rejected" ? " active" : "";

  let flagHtml = "";
  if (hasFlagged) {
    flagHtml = `<div class="flag-banner">
      <span class="flag-icon">⚠</span>
      <span>Skill additions were blocked: <strong>${escHtml(skl.added_skills.join(", "))}</strong>. The reordered list shown excludes them.</span>
    </div>`;
  }

  const origChips = (skl.original || []).map(s =>
    `<span class="skill-chip">${escHtml(s)}</span>`
  ).join("");

  const suggChips = (skl.suggested || []).map(s =>
    `<span class="skill-chip">${escHtml(s)}</span>`
  ).join("");

  const suggestedIdentical = JSON.stringify(skl.original) === JSON.stringify(skl.suggested);
  if (suggestedIdentical && !hasFlagged) return "";

  return `
  <div class="card">
    <div class="improve-section-title">Skills Order</div>
    <div class="suggestion-card ${statusClass}" id="card-skills">
      ${flagHtml}
      <div class="suggestion-panels">
        <div class="panel-orig">
          <div class="panel-label">Original Order</div>
          <div class="panel-text chips-panel">${origChips || '<em>No skills listed</em>'}</div>
        </div>
        <div class="panel-sugg">
          <div class="panel-label">Suggested Order</div>
          <div class="panel-text chips-panel">${suggChips || '<em>No skills listed</em>'}</div>
        </div>
      </div>
      ${skl.reason ? `<div class="suggestion-reason"><strong>Why:</strong> ${escHtml(skl.reason)}</div>` : ""}
      <div class="suggestion-actions">
        <button class="btn btn-sm btn-accept${acceptActive}" onclick="handleAccept('skills')">✓ Accept Reorder</button>
        <button class="btn btn-sm btn-reject${rejectActive}" onclick="handleReject('skills')">✗ Keep Original</button>
      </div>
    </div>
  </div>`;
}

// ── Render session ─────────────────────────────────────────────────────────────

function renderSession(sessionOut) {
  currentSessionId = sessionOut.id;
  currentSessionData = sessionOut.session_data || {};
  currentTotalSuggestions = sessionOut.total_suggestions || 0;
  currentAcceptedCount = sessionOut.accepted_count || 0;

  const analysis = currentSessionData.role_analysis || "";
  document.getElementById("role-analysis-text").textContent = analysis;
  document.getElementById("analysis-card").style.display = analysis ? "block" : "none";

  updateProgress();

  const container = document.getElementById("suggestions-container");
  let html = "";

  // Summary suggestion
  const ss = currentSessionData.summary_suggestion;
  if (ss && ss.has_suggestion) {
    html += `<div class="card"><div class="improve-section-title">Professional Summary</div>`;
    html += bulletCardHtml("summary", {}, ss);
    html += `</div>`;
  }

  // Experience
  for (const jobSug of (currentSessionData.experience_suggestions || [])) {
    const activeBullets = (jobSug.bullet_suggestions || []).filter(b => b.has_suggestion);
    if (!activeBullets.length) continue;

    let title = escHtml(jobSug.title || "Experience");
    if (jobSug.company) title += ` — ${escHtml(jobSug.company)}`;
    const dates = jobSug.dates ? ` <span class="improve-dates">${escHtml(jobSug.dates)}</span>` : "";

    html += `<div class="card"><div class="improve-section-title">${title}${dates}</div>`;
    for (const bsug of activeBullets) {
      html += bulletCardHtml("experience", {
        job_index: jobSug.job_index,
        bullet_index: bsug.bullet_index,
      }, bsug);
    }
    html += `</div>`;
  }

  // Projects
  for (const projSug of (currentSessionData.project_suggestions || [])) {
    const activeBullets = (projSug.bullet_suggestions || []).filter(b => b.has_suggestion);
    if (!activeBullets.length) continue;

    html += `<div class="card"><div class="improve-section-title">${escHtml(projSug.name || "Project")}</div>`;
    for (const bsug of activeBullets) {
      html += bulletCardHtml("project", {
        project_index: projSug.project_index,
        bullet_index: bsug.bullet_index,
      }, bsug);
    }
    html += `</div>`;
  }

  // Skills
  const skl = currentSessionData.skills_suggestion;
  if (skl) {
    html += skillsCardHtml(skl);
  }

  if (!html) {
    html = `<div class="card"><p style="color:var(--muted); font-style:italic;">No improvement suggestions were generated for this resume and job description combination.</p></div>`;
  }

  container.innerHTML = html;

  const resultSection = document.getElementById("result-section");
  resultSection.style.display = "block";
  resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Progress bar ──────────────────────────────────────────────────────────────

function updateProgress() {
  document.getElementById("accepted-count").textContent = currentAcceptedCount;
  document.getElementById("total-count").textContent = currentTotalSuggestions;

  const pct = currentTotalSuggestions > 0
    ? Math.round((currentAcceptedCount / currentTotalSuggestions) * 100)
    : 0;
  document.getElementById("improve-progress-fill").style.width = pct + "%";

  const applyBtn = document.getElementById("apply-btn");
  applyBtn.disabled = currentAcceptedCount === 0;
  applyBtn.textContent = `Apply ${currentAcceptedCount} Accepted Change${currentAcceptedCount === 1 ? "" : "s"}`;
}

// ── Card actions ──────────────────────────────────────────────────────────────

function handleAccept(cardId) {
  patchSuggestion(cardId, "accepted", null);
}

function handleReject(cardId) {
  patchSuggestion(cardId, "rejected", null);
}

function handleEdit(cardId) {
  const editDiv = document.getElementById(`edit-${cardId}`);
  if (editDiv) editDiv.style.display = "block";
}

function handleCancelEdit(cardId) {
  const editDiv = document.getElementById(`edit-${cardId}`);
  if (editDiv) editDiv.style.display = "none";
}

function handleSaveEdit(cardId) {
  const textarea = document.getElementById(`edittext-${cardId}`);
  const customText = (textarea?.value || "").trim();
  if (!customText) {
    textarea?.focus();
    return;
  }
  patchSuggestion(cardId, "accepted", customText);
}

// ── PATCH suggestion ──────────────────────────────────────────────────────────

async function patchSuggestion(cardId, status, customText) {
  if (!currentSessionId) return;

  const meta = decodeCardId(cardId);
  const body = { section: meta.section, status };
  if (meta.job_index !== undefined) body.job_index = meta.job_index;
  if (meta.project_index !== undefined) body.project_index = meta.project_index;
  if (meta.bullet_index !== undefined) body.bullet_index = meta.bullet_index;
  if (customText !== null && customText !== undefined) body.custom_text = customText;

  // Optimistic UI: disable all action buttons on this card
  const card = document.getElementById(`card-${cardId}`);
  const actionBtns = card?.querySelectorAll(".suggestion-actions .btn");
  actionBtns?.forEach(b => (b.disabled = true));

  let res;
  try {
    res = await fetch(`${API}/improve/${currentSessionId}/suggestion`, {
      method: "PATCH",
      headers: jsonHeaders(),
      body: JSON.stringify(body),
    });
  } catch {
    actionBtns?.forEach(b => (b.disabled = false));
    alert("Network error — is the server running?");
    return;
  }

  actionBtns?.forEach(b => (b.disabled = false));

  if (handle401(res)) return;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Update failed" }));
    alert(err.detail || "Update failed");
    return;
  }

  const updated = await res.json();
  currentSessionData = updated.session_data || currentSessionData;
  currentTotalSuggestions = updated.total_suggestions;
  currentAcceptedCount = updated.accepted_count;
  updateProgress();

  // Update card visual state
  updateCardVisual(cardId, status, customText);

  // Hide edit mode
  const editDiv = document.getElementById(`edit-${cardId}`);
  if (editDiv) editDiv.style.display = "none";
}

function updateCardVisual(cardId, status, customText) {
  const card = document.getElementById(`card-${cardId}`);
  if (!card) return;

  card.classList.remove("suggestion-accepted", "suggestion-rejected");
  if (status === "accepted") card.classList.add("suggestion-accepted");
  if (status === "rejected") card.classList.add("suggestion-rejected");

  // Update button active states
  const acceptBtn = card.querySelector(".btn-accept");
  const rejectBtn = card.querySelector(".btn-reject");
  if (acceptBtn) acceptBtn.classList.toggle("active", status === "accepted");
  if (rejectBtn) rejectBtn.classList.toggle("active", status === "rejected");

  // Update diff text if custom
  if (customText !== null && customText !== undefined) {
    const diffEl = document.getElementById(`difftext-${cardId}`);
    if (diffEl) {
      // Find original text from session data
      const meta = decodeCardId(cardId);
      let originalText = "";
      if (meta.section === "summary") {
        originalText = currentSessionData?.summary_suggestion?.original || "";
      } else if (meta.section === "experience") {
        const job = (currentSessionData?.experience_suggestions || [])
          .find(j => j.job_index === meta.job_index);
        const b = (job?.bullet_suggestions || []).find(b => b.bullet_index === meta.bullet_index);
        originalText = b?.original || "";
      } else if (meta.section === "project") {
        const proj = (currentSessionData?.project_suggestions || [])
          .find(p => p.project_index === meta.project_index);
        const b = (proj?.bullet_suggestions || []).find(b => b.bullet_index === meta.bullet_index);
        originalText = b?.original || "";
      }
      diffEl.innerHTML = wordDiff(originalText, customText);
    }

    // Add edited badge to panel label
    const panel = card.querySelector(".panel-sugg .panel-label");
    if (panel && !panel.querySelector(".custom-edit-badge")) {
      panel.innerHTML += ` <span class="custom-edit-badge">Edited</span>`;
    }
  }
}

// ── Apply accepted changes ────────────────────────────────────────────────────

async function applyChanges() {
  if (!currentSessionId || currentAcceptedCount === 0) return;

  const btn = document.getElementById("apply-btn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Applying…';

  const statusDiv = document.getElementById("apply-status");
  statusDiv.style.display = "none";

  let res;
  try {
    res = await fetch(`${API}/improve/${currentSessionId}/apply`, {
      method: "POST",
      headers: jsonHeaders(),
    });
  } catch {
    btn.disabled = false;
    btn.textContent = `Apply ${currentAcceptedCount} Accepted Changes`;
    statusDiv.style.display = "block";
    statusDiv.innerHTML = `<span style="color:var(--danger)">Network error — is the server running?</span>`;
    return;
  }

  btn.disabled = currentAcceptedCount === 0;
  btn.textContent = `Apply ${currentAcceptedCount} Accepted Changes`;

  if (handle401(res)) return;

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Apply failed" }));
    statusDiv.style.display = "block";
    statusDiv.innerHTML = `<span style="color:var(--danger)">Error: ${escHtml(err.detail || "Apply failed")}</span>`;
    return;
  }

  const tailored = await res.json();
  const tailoredId = tailored.id;

  statusDiv.style.display = "block";
  statusDiv.innerHTML = `
    <span style="color:var(--success-text); font-weight:600">✓ Changes applied!</span>
    <button class="btn btn-outline btn-sm" onclick="downloadAppliedPdf(${tailoredId}, this)" style="margin-left:0.75rem">
      Download PDF
    </button>
    <a href="tailor.html?tailored_id=${tailoredId}" class="btn btn-ghost btn-sm" style="margin-left:0.25rem">
      View in Tailor
    </a>`;

  await loadHistory();
}

async function downloadAppliedPdf(tailoredId, triggerBtn) {
  const orig = triggerBtn.textContent;
  triggerBtn.disabled = true;
  triggerBtn.textContent = "Downloading…";
  try {
    const res = await fetch(`${API}/export/resume/${tailoredId}`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Download failed" }));
      alert(err.detail || "Download failed");
      return;
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "improved_resume.pdf";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 10000);
  } catch {
    alert("Network error — is the server running?");
  } finally {
    triggerBtn.disabled = false;
    triggerBtn.textContent = orig;
  }
}

// ── History ────────────────────────────────────────────────────────────────────

function renderHistoryItem(item) {
  const statusCls = item.status === "applied" ? "badge-ok" : "badge-warn";
  const statusLabel = item.status === "applied" ? "Applied" : "Active";
  const role = item.role_title
    ? escHtml(item.role_title)
    : '<span class="hist-unknown">Unknown Role</span>';

  const progress = item.total_suggestions > 0
    ? `${item.accepted_count}/${item.total_suggestions} accepted`
    : "0 suggestions";

  return `<li class="hist-card" data-id="${item.id}">
    <div class="hist-card-main">
      <div class="hist-role-row">
        <strong class="hist-role">${role}</strong>
        <span class="badge ${statusCls}">${statusLabel}</span>
      </div>
      <div class="hist-meta">
        <span>${fmtDate(item.created_at)}</span>
        <span style="color:var(--muted)">&middot; ${escHtml(progress)}</span>
      </div>
    </div>
    <div class="hist-card-actions">
      <button class="btn btn-outline btn-sm btn-view-session" data-id="${item.id}">View</button>
      <button class="btn btn-sm btn-delete" data-id="${item.id}">Delete</button>
    </div>
  </li>`;
}

async function loadHistory() {
  const loadEl  = document.getElementById("history-loading");
  const emptyEl = document.getElementById("history-empty");
  const listEl  = document.getElementById("history-list");
  const countEl = document.getElementById("history-count");

  loadEl.style.display = "block";
  emptyEl.style.display = "none";
  listEl.style.display  = "none";

  const res = await fetch(`${API}/improve/`, { headers: authHeaders() });
  if (handle401(res)) return;

  loadEl.style.display = "none";
  const items = await res.json();

  if (!items.length) {
    emptyEl.style.display = "block";
    countEl.textContent = "";
    return;
  }

  countEl.textContent = `${items.length} session${items.length === 1 ? "" : "s"}`;
  listEl.innerHTML = items.map(renderHistoryItem).join("");
  listEl.style.display = "flex";

  listEl.querySelectorAll(".btn-view-session").forEach(btn => {
    btn.addEventListener("click", () => viewSession(parseInt(btn.dataset.id)));
  });
  listEl.querySelectorAll(".btn-delete").forEach(btn => {
    btn.addEventListener("click", () => openDeleteDialog(parseInt(btn.dataset.id), false));
  });
}

async function viewSession(id) {
  const btn = document.querySelector(`.btn-view-session[data-id="${id}"]`);
  if (btn) { btn.disabled = true; btn.textContent = "Loading…"; }

  let res;
  try {
    res = await fetch(`${API}/improve/${id}`, { headers: authHeaders() });
  } catch {
    if (btn) { btn.disabled = false; btn.textContent = "View"; }
    alert("Network error — is the server running?");
    return;
  }

  if (btn) { btn.disabled = false; btn.textContent = "View"; }
  if (handle401(res)) return;
  if (!res.ok) { alert("Could not load session."); return; }

  const data = await res.json();
  renderSession(data);

  // If already applied, show apply status
  if (data.status === "applied" && data.tailored_resume_id) {
    const statusDiv = document.getElementById("apply-status");
    statusDiv.style.display = "block";
    statusDiv.innerHTML = `
      <span style="color:var(--success-text); font-weight:600">✓ Already applied.</span>
      <button class="btn btn-outline btn-sm" onclick="downloadAppliedPdf(${data.tailored_resume_id}, this)" style="margin-left:0.75rem">
        Download PDF
      </button>
      <a href="tailor.html?tailored_id=${data.tailored_resume_id}" class="btn btn-ghost btn-sm" style="margin-left:0.25rem">
        View in Tailor
      </a>`;
  }
}

function refreshHistoryCount() {
  const listEl  = document.getElementById("history-list");
  const emptyEl = document.getElementById("history-empty");
  const countEl = document.getElementById("history-count");
  const remaining = listEl.querySelectorAll(".hist-card").length;
  if (!remaining) {
    listEl.style.display  = "none";
    emptyEl.style.display = "block";
    countEl.textContent   = "";
  } else {
    countEl.textContent = `${remaining} session${remaining === 1 ? "" : "s"}`;
  }
}

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
  const isCurrent = pendingDeleteIsCurrentResult;
  pendingDeleteId = null;
  pendingDeleteIsCurrentResult = false;

  const card = document.querySelector(`#history-list .hist-card[data-id="${id}"]`);
  if (card) card.style.opacity = "0.4";

  const res = await fetch(`${API}/improve/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });

  if (handle401(res)) return;

  if (res.ok || res.status === 204) {
    if (isCurrent) {
      document.getElementById("result-section").style.display = "none";
      currentSessionId = null;
      currentSessionData = null;
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

// ── Logout ──────────────────────────────────────────────────────────────────────

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("token");
  window.location.href = "login.html";
});

// ── Init ───────────────────────────────────────────────────────────────────────

loadResumes();
loadHistory();
