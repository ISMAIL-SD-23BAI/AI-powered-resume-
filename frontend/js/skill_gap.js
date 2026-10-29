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

let currentRoadmapId = null;

// ── Resumes ────────────────────────────────────────────────────────────────────

async function loadResumes() {
  const res = await fetch(`${API}/resumes/`, { headers: authHeaders() });
  if (handle401(res)) return;

  const resumes = await res.json();
  const sel = document.getElementById("resume-select");
  const btn = document.getElementById("analyze-btn");

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
  document.getElementById("analyze-btn").disabled = !this.value;
});

// ── Form submit ────────────────────────────────────────────────────────────────

document.getElementById("gap-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const resume_id = parseInt(document.getElementById("resume-select").value);
  const job_description_text = document.getElementById("jd-textarea").value.trim();

  if (!resume_id) {
    setStatus("Please select a resume.", "error");
    return;
  }
  if (job_description_text.length < 50) {
    setStatus("Job description must be at least 50 characters.", "error");
    return;
  }

  setStatus("Analyzing… this may take a moment.", "info");
  document.getElementById("analyze-btn").disabled = true;
  document.getElementById("result-section").style.display = "none";

  try {
    const res = await fetch(`${API}/skill-gap/`, {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify({ resume_id, job_description_text }),
    });
    if (handle401(res)) return;
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${res.status}`);
    }
    const data = await res.json();
    setStatus("", "");
    currentRoadmapId = data.id;
    renderResult(data);
    await loadHistory();
  } catch (err) {
    setStatus(`Error: ${err.message}`, "error");
  } finally {
    document.getElementById("analyze-btn").disabled = false;
  }
});

function setStatus(msg, cls) {
  const el = document.getElementById("analyze-status");
  el.textContent = msg;
  el.className = `analyze-status${cls ? " " + cls : ""}`;
}

// ── Render result ──────────────────────────────────────────────────────────────

function scoreGrade(score) {
  if (score >= 80) return { label: "Strong", color: "var(--success)" };
  if (score >= 60) return { label: "Good",   color: "var(--warning)" };
  if (score >= 40) return { label: "Fair",   color: "#f97316" };
  return               { label: "Low",    color: "var(--danger)" };
}

function renderResult(data) {
  const section = document.getElementById("result-section");
  section.style.display = "";

  // Score ring
  const score = Math.round(data.overall_score || 0);
  const grade = scoreGrade(score);
  const numEl = document.getElementById("sg-score-number");
  const pctEl = numEl.nextElementSibling;  // .score-pct
  numEl.textContent = score;
  pctEl.style.display = "";

  const gradeEl = document.getElementById("sg-score-grade");
  gradeEl.textContent = grade.label;
  gradeEl.style.color = grade.color;

  const fill = document.getElementById("sg-ring-fill");
  fill.style.stroke = grade.color;
  fill.style.strokeDashoffset = 314.16 - (314.16 * score / 100);

  // Role badge
  const roleBadge = document.getElementById("sg-role-badge");
  if (data.role_title) {
    roleBadge.textContent = data.role_title;
    roleBadge.style.display = "inline-flex";
  } else {
    roleBadge.style.display = "none";
  }

  // Gap summary chips
  const classifications = data.skill_classifications || [];
  const counts = { demonstrated: 0, partially_demonstrated: 0, requires_verification: 0, not_found: 0 };
  for (const c of classifications) {
    if (counts[c.classification] !== undefined) counts[c.classification]++;
  }
  document.getElementById("sg-gap-summary").innerHTML = `
    <div class="sg-gap-chip sg-chip-demonstrated">${counts.demonstrated} Demonstrated</div>
    <div class="sg-gap-chip sg-chip-partial">${counts.partially_demonstrated} Partial</div>
    <div class="sg-gap-chip sg-chip-verify">${counts.requires_verification} Verify</div>
    <div class="sg-gap-chip sg-chip-notfound">${counts.not_found} Not Evidenced</div>
  `;

  renderClassifications(classifications);
  renderRoadmap(data.roadmap_items || [], data.id);

  document.getElementById("disclaimer-text").textContent = data.disclaimer || "";

  document.getElementById("delete-result-btn").onclick = () => openDeleteDialog(data.id);
  document.getElementById("analyze-another-btn").onclick = () => {
    section.style.display = "none";
    document.getElementById("jd-textarea").value = "";
    document.getElementById("jd-textarea").focus();
  };
}

// ── Classification buckets ─────────────────────────────────────────────────────

function renderClassifications(classifications) {
  const buckets = { demonstrated: [], partially_demonstrated: [], requires_verification: [], not_found: [] };
  for (const c of classifications) {
    if (buckets[c.classification]) buckets[c.classification].push(c);
  }

  const maps = [
    { key: "demonstrated",        listId: "demonstrated-list", countId: "demonstrated-count", emptyId: "demonstrated-empty" },
    { key: "partially_demonstrated", listId: "partial-list",   countId: "partial-count",      emptyId: "partial-empty" },
    { key: "requires_verification",  listId: "verify-list",    countId: "verify-count",       emptyId: "verify-empty" },
    { key: "not_found",           listId: "notfound-list",  countId: "notfound-count",     emptyId: "notfound-empty" },
  ];

  for (const { key, listId, countId, emptyId } of maps) {
    const items = buckets[key] || [];
    document.getElementById(countId).textContent = items.length;
    const list  = document.getElementById(listId);
    const empty = document.getElementById(emptyId);
    if (!items.length) {
      list.innerHTML = "";
      empty.style.display = "";
    } else {
      empty.style.display = "none";
      list.innerHTML = items.map(classificationItemHtml).join("");
    }
  }
}

function classificationItemHtml(c) {
  const preferredBadge = c.is_preferred
    ? `<span class="sg-preferred-badge">preferred</span>` : "";
  const sources = (c.resume_sections || []).length
    ? `<span class="sg-sources">${c.resume_sections.map(escHtml).join(", ")}</span>` : "";
  const conf = (c.confidence != null && c.confidence > 0 && c.confidence < 1)
    ? `<span class="sg-confidence">${Math.round(c.confidence * 100)}%</span>` : "";
  const note = c.notes
    ? `<div class="sg-skill-note">${escHtml(c.notes)}</div>` : "";

  return `<li class="sg-skill-item">
    <div class="sg-skill-row">
      <span class="sg-skill-name">${escHtml(c.skill)}</span>
      ${preferredBadge}${conf}${sources}
    </div>
    ${note}
  </li>`;
}

// ── Roadmap ────────────────────────────────────────────────────────────────────

function renderRoadmap(items, roadmapId) {
  const container = document.getElementById("roadmap-items");
  const empty     = document.getElementById("roadmap-empty");
  const badge     = document.getElementById("roadmap-progress-badge");

  if (!items.length) {
    container.innerHTML = "";
    empty.style.display = "";
    badge.textContent = "No gaps";
    return;
  }

  empty.style.display = "none";
  updateProgressBadge(items);
  container.innerHTML = items.map(item => roadmapItemHtml(item, roadmapId)).join("");
}

function updateProgressBadge(items) {
  const completed = items.filter(i => i.status === "completed").length;
  document.getElementById("roadmap-progress-badge").textContent =
    `${completed}/${items.length} completed`;
}

function roadmapItemHtml(item, roadmapId) {
  const seqHtml = (item.learning_sequence || [])
    .map(s => `<li class="sg-seq-item">${escHtml(s)}</li>`)
    .join("");

  const ns = item.status === "not_started";
  const ip = item.status === "in_progress";
  const cp = item.status === "completed";

  const resourcesHtml = item.resources_note
    ? `<div class="sg-resources-note">${escHtml(item.resources_note)}</div>` : "";

  return `<div class="sg-roadmap-card" id="roadmap-item-${item.item_index}">
    <div class="sg-roadmap-header">
      <div class="sg-roadmap-skill">${escHtml(item.skill)}</div>
      <div class="sg-status-btns"
           data-roadmap-id="${roadmapId}"
           data-item-idx="${item.item_index}">
        <button class="sg-status-btn${ns ? " active" : ""}"
                data-status="not_started">To Do</button>
        <button class="sg-status-btn${ip ? " active" : ""}"
                data-status="in_progress">In Progress</button>
        <button class="sg-status-btn sg-status-btn-complete${cp ? " active" : ""}"
                data-status="completed">Completed</button>
      </div>
    </div>

    <p class="sg-why">${escHtml(item.why_it_matters)}</p>

    <div class="sg-seq-section">
      <div class="sg-seq-label">Learning sequence</div>
      <ol class="sg-seq-list">${seqHtml}</ol>
    </div>

    <div class="sg-project-section">
      <div class="sg-seq-label">Practical project</div>
      <p class="sg-project-text">${escHtml(item.practical_project)}</p>
    </div>

    ${resourcesHtml}
  </div>`;
}

// ── Roadmap item status PATCH ──────────────────────────────────────────────────

document.getElementById("roadmap-items").addEventListener("click", async (e) => {
  const btn = e.target.closest(".sg-status-btn");
  if (!btn) return;

  const group = btn.closest(".sg-status-btns");
  if (!group) return;

  const roadmapId = parseInt(group.dataset.roadmapId);
  const itemIdx   = parseInt(group.dataset.itemIdx);
  const newStatus = btn.dataset.status;

  // Optimistic update
  group.querySelectorAll(".sg-status-btn").forEach(b => b.classList.toggle("active", b === btn));

  try {
    const res = await fetch(`${API}/skill-gap/${roadmapId}/item/${itemIdx}`, {
      method: "PATCH",
      headers: jsonHeaders(),
      body: JSON.stringify({ status: newStatus }),
    });
    if (handle401(res)) return;
    if (!res.ok) throw new Error(`Error ${res.status}`);

    const updated = await res.json();
    updateProgressBadge(updated.roadmap_items || []);
  } catch (err) {
    console.error("Failed to update item status:", err);
    await reloadCurrentRoadmap();
  }
});

async function reloadCurrentRoadmap() {
  if (!currentRoadmapId) return;
  try {
    const res = await fetch(`${API}/skill-gap/${currentRoadmapId}`, { headers: authHeaders() });
    if (handle401(res)) return;
    if (res.ok) renderResult(await res.json());
  } catch (e) {
    console.error(e);
  }
}

// ── Delete ─────────────────────────────────────────────────────────────────────

let _deletingId = null;

function openDeleteDialog(roadmapId) {
  _deletingId = roadmapId;
  document.getElementById("delete-dialog").showModal();
}

document.getElementById("delete-cancel-btn").addEventListener("click", () => {
  _deletingId = null;
  document.getElementById("delete-dialog").close();
});

document.getElementById("delete-confirm-btn").addEventListener("click", async () => {
  const id = _deletingId;
  document.getElementById("delete-dialog").close();
  _deletingId = null;
  if (!id) return;

  try {
    const res = await fetch(`${API}/skill-gap/${id}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    if (handle401(res)) return;
    if (res.status === 204 || res.ok) {
      if (currentRoadmapId === id) {
        document.getElementById("result-section").style.display = "none";
        currentRoadmapId = null;
      }
      await loadHistory();
    }
  } catch (err) {
    console.error("Delete failed:", err);
  }
});

// ── History ────────────────────────────────────────────────────────────────────

async function loadHistory() {
  const res = await fetch(`${API}/skill-gap/`, { headers: authHeaders() });
  if (handle401(res)) return;

  const items = await res.json();
  const loading    = document.getElementById("history-loading");
  const empty      = document.getElementById("history-empty");
  const list       = document.getElementById("history-list");
  const countBadge = document.getElementById("history-count");

  loading.style.display = "none";
  countBadge.textContent = items.length;

  if (!items.length) {
    empty.style.display = "";
    list.style.display  = "none";
    return;
  }

  empty.style.display = "none";
  list.style.display  = "";
  list.innerHTML = items.map(histItemHtml).join("");

  list.querySelectorAll(".sg-hist-view").forEach(btn => {
    btn.addEventListener("click", () => loadRoadmapById(parseInt(btn.dataset.id)));
  });
  list.querySelectorAll(".sg-hist-delete").forEach(btn => {
    btn.addEventListener("click", () => openDeleteDialog(parseInt(btn.dataset.id)));
  });
}

function histItemHtml(item) {
  const role = item.role_title
    ? escHtml(item.role_title)
    : `<span class="hist-unknown">Unknown role</span>`;
  const score   = item.overall_score != null ? `${Math.round(item.overall_score)}%` : "—";
  const gaps    = item.gap_count || 0;
  const done    = item.completed_count || 0;
  const total   = item.total_roadmap_items || 0;
  const progress = total
    ? `${done}/${total} roadmap items completed`
    : "No roadmap items";

  const gapBadge = gaps > 0
    ? `<span class="badge badge-warn">${gaps} gap${gaps !== 1 ? "s" : ""}</span>`
    : `<span class="badge badge-ok">No gaps</span>`;

  return `<li>
    <div class="hist-card">
      <div class="hist-card-main">
        <div class="hist-role-row">
          <span class="hist-role">${role}</span>
          <span class="badge badge-seniority">${escHtml(score)}</span>
          ${gapBadge}
        </div>
        <div class="hist-meta">
          <span>${fmtDate(item.created_at)}</span>
          <span class="hist-dot">·</span>
          <span>${progress}</span>
        </div>
      </div>
      <div class="hist-card-actions">
        <button class="btn btn-outline btn-sm sg-hist-view" data-id="${item.id}">View</button>
        <button class="btn-delete sg-hist-delete" data-id="${item.id}">Delete</button>
      </div>
    </div>
  </li>`;
}

async function loadRoadmapById(id) {
  try {
    const res = await fetch(`${API}/skill-gap/${id}`, { headers: authHeaders() });
    if (handle401(res)) return;
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const data = await res.json();
    currentRoadmapId = id;
    renderResult(data);
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    console.error("Failed to load roadmap:", err);
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
