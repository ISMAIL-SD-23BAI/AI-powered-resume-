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
  return String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
function fmtDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
  });
}
function fmtDateInput(iso) {
  // Returns YYYY-MM-DD for <input type="date">
  if (!iso) return "";
  return iso.slice(0, 10);
}
function handle401(res) {
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "login.html";
    return true;
  }
  return false;
}

// ── Status config ──────────────────────────────────────────────────────────────

const STATUS_LABELS = {
  saved:      "Saved",
  applied:    "Applied",
  assessment: "Assessment",
  interview:  "Interview",
  offer:      "Offer",
  rejected:   "Rejected",
};
const STATUS_CLASSES = {
  saved:      "trk-badge-saved",
  applied:    "trk-badge-applied",
  assessment: "trk-badge-assessment",
  interview:  "trk-badge-interview",
  offer:      "trk-badge-offer",
  rejected:   "trk-badge-rejected",
};

function statusBadge(status) {
  const label = STATUS_LABELS[status] || status;
  const cls   = STATUS_CLASSES[status] || "";
  return `<span class="trk-badge ${cls}">${escHtml(label)}</span>`;
}

// ── State ──────────────────────────────────────────────────────────────────────

let _editingId  = null;   // null = create mode, int = edit mode
let _deletingId = null;
let _resumes    = [];

// ── Init ───────────────────────────────────────────────────────────────────────

(async function init() {
  await Promise.all([loadResumes(), loadStats(), loadList()]);
})();

// ── Resumes (for the form dropdown) ───────────────────────────────────────────

async function loadResumes() {
  try {
    const res = await fetch(`${API}/resumes/`, { headers: authHeaders() });
    if (handle401(res)) return;
    _resumes = await res.json();
    populateResumeDropdown();
  } catch (e) {
    console.error("Failed to load resumes:", e);
  }
}

function populateResumeDropdown() {
  const sel = document.getElementById("f-resume");
  // keep the "None" option, then add resumes
  sel.innerHTML = '<option value="">None</option>' +
    _resumes.map(r => `<option value="${r.id}">${escHtml(r.filename)}</option>`).join("");
}

// ── Stats ──────────────────────────────────────────────────────────────────────

async function loadStats() {
  try {
    const res = await fetch(`${API}/tracker/stats`, { headers: authHeaders() });
    if (handle401(res)) return;
    const data = await res.json();
    document.getElementById("stat-total-num").textContent     = data.total;
    document.getElementById("stat-saved-num").textContent     = data.saved;
    document.getElementById("stat-active-num").textContent    = data.active;
    document.getElementById("stat-interview-num").textContent = data.interviews;
    document.getElementById("stat-offer-num").textContent     = data.offers;
    document.getElementById("stat-rejected-num").textContent  = data.rejected;
  } catch (e) {
    console.error("Failed to load stats:", e);
  }
}

// ── List ───────────────────────────────────────────────────────────────────────

async function loadList() {
  const search = document.getElementById("search-input").value.trim();
  const status = document.getElementById("status-filter").value;

  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (search) params.set("search", search);
  const qs = params.toString() ? `?${params}` : "";

  try {
    const res = await fetch(`${API}/tracker/${qs}`, { headers: authHeaders() });
    if (handle401(res)) return;
    const items = await res.json();
    renderList(items);
  } catch (e) {
    console.error("Failed to load applications:", e);
  } finally {
    document.getElementById("list-loading").style.display = "none";
  }
}

function renderList(items) {
  const listEl  = document.getElementById("app-list");
  const emptyEl = document.getElementById("list-empty");

  if (!items.length) {
    listEl.style.display  = "none";
    emptyEl.style.display = "";
    return;
  }

  emptyEl.style.display = "none";
  listEl.style.display  = "";
  listEl.innerHTML = items.map(appCardHtml).join("");

  listEl.querySelectorAll(".trk-edit-btn").forEach(btn => {
    btn.addEventListener("click", () => openEdit(parseInt(btn.dataset.id)));
  });
  listEl.querySelectorAll(".trk-delete-btn").forEach(btn => {
    btn.addEventListener("click", () => openDeleteDialog(parseInt(btn.dataset.id)));
  });
  listEl.querySelectorAll(".trk-status-select").forEach(sel => {
    sel.addEventListener("change", async function () {
      await quickPatchStatus(parseInt(this.dataset.id), this.value);
    });
  });
}

function appCardHtml(app) {
  const hasUrl = app.job_url;
  const titleLink = hasUrl
    ? `<a href="${escHtml(app.job_url)}" target="_blank" rel="noopener noreferrer" class="trk-company-link">${escHtml(app.company_name)}</a>`
    : escHtml(app.company_name);

  const dates = [];
  if (app.application_date) dates.push(`Applied ${fmtDate(app.application_date)}`);
  if (app.deadline)         dates.push(`Deadline ${fmtDate(app.deadline)}`);
  if (app.interview_date)   dates.push(`Interview ${fmtDate(app.interview_date)}`);

  const resumeChip = app.resume_id
    ? `<span class="trk-meta-chip">Resume #${app.resume_id}</span>` : "";

  const notesSnippet = app.notes
    ? `<div class="trk-notes-snippet">${escHtml(app.notes.slice(0, 120))}${app.notes.length > 120 ? "…" : ""}</div>`
    : "";

  const statusOptions = Object.entries(STATUS_LABELS)
    .map(([v, l]) => `<option value="${v}"${v === app.status ? " selected" : ""}>${l}</option>`)
    .join("");

  return `<div class="trk-card" id="app-card-${app.id}">
    <div class="trk-card-main">
      <div class="trk-card-header">
        <div class="trk-company">${titleLink}</div>
        <div class="trk-title">${escHtml(app.job_title)}</div>
      </div>
      <div class="trk-card-meta">
        ${dates.map(d => `<span class="trk-meta-chip">${escHtml(d)}</span>`).join("")}
        ${resumeChip}
      </div>
      ${notesSnippet}
    </div>
    <div class="trk-card-right">
      <select class="trk-status-select" data-id="${app.id}" aria-label="Status for ${escHtml(app.company_name)}">
        ${statusOptions}
      </select>
      <div class="trk-card-actions">
        <button class="btn btn-outline btn-sm trk-edit-btn" data-id="${app.id}">Edit</button>
        <button class="btn-delete trk-delete-btn" data-id="${app.id}">Delete</button>
      </div>
    </div>
  </div>`;
}

// ── Quick status update from card dropdown ─────────────────────────────────────

async function quickPatchStatus(appId, newStatus) {
  try {
    const res = await fetch(`${API}/tracker/${appId}`, {
      method: "PATCH",
      headers: jsonHeaders(),
      body: JSON.stringify({ status: newStatus }),
    });
    if (handle401(res)) return;
    if (res.ok) await loadStats();
  } catch (e) {
    console.error("Status update failed:", e);
    await loadList();  // revert optimistic UI
  }
}

// ── Search / filter controls ───────────────────────────────────────────────────

let _searchTimer = null;
document.getElementById("search-input").addEventListener("input", () => {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(loadList, 300);
});
document.getElementById("status-filter").addEventListener("change", loadList);

// ── Add / Edit dialog ──────────────────────────────────────────────────────────

document.getElementById("add-btn").addEventListener("click", () => openCreate());

function openCreate() {
  _editingId = null;
  document.getElementById("dialog-title").textContent = "Add Application";
  document.getElementById("form-save-btn").textContent = "Save Application";
  clearForm();
  document.getElementById("app-dialog").showModal();
}

async function openEdit(appId) {
  _editingId = appId;
  document.getElementById("dialog-title").textContent = "Edit Application";
  document.getElementById("form-save-btn").textContent = "Save Changes";

  try {
    const res = await fetch(`${API}/tracker/${appId}`, { headers: authHeaders() });
    if (handle401(res)) return;
    if (!res.ok) return;
    const app = await res.json();
    populateForm(app);
    document.getElementById("app-dialog").showModal();
  } catch (e) {
    console.error("Failed to load application for edit:", e);
  }
}

function clearForm() {
  document.getElementById("f-company").value       = "";
  document.getElementById("f-title").value         = "";
  document.getElementById("f-status").value        = "saved";
  document.getElementById("f-url").value           = "";
  document.getElementById("f-app-date").value      = "";
  document.getElementById("f-deadline").value      = "";
  document.getElementById("f-interview-date").value = "";
  document.getElementById("f-resume").value        = "";
  document.getElementById("f-jd").value            = "";
  document.getElementById("f-notes").value         = "";
  hideFormError();
}

function populateForm(app) {
  document.getElementById("f-company").value        = app.company_name   || "";
  document.getElementById("f-title").value          = app.job_title      || "";
  document.getElementById("f-status").value         = app.status         || "saved";
  document.getElementById("f-url").value            = app.job_url        || "";
  document.getElementById("f-app-date").value       = fmtDateInput(app.application_date);
  document.getElementById("f-deadline").value       = fmtDateInput(app.deadline);
  document.getElementById("f-interview-date").value = fmtDateInput(app.interview_date);
  document.getElementById("f-resume").value         = app.resume_id      || "";
  document.getElementById("f-jd").value             = app.job_description || "";
  document.getElementById("f-notes").value          = app.notes          || "";
  hideFormError();
}

function closeDialog() {
  document.getElementById("app-dialog").close();
  _editingId = null;
}

document.getElementById("dialog-close-btn").addEventListener("click", closeDialog);
document.getElementById("form-cancel-btn").addEventListener("click", closeDialog);

// ── Form submit ────────────────────────────────────────────────────────────────

document.getElementById("app-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideFormError();

  const company = document.getElementById("f-company").value.trim();
  const title   = document.getElementById("f-title").value.trim();
  if (!company) { showFormError("Company name is required."); return; }
  if (!title)   { showFormError("Job title is required."); return; }

  const rawUrl = document.getElementById("f-url").value.trim();
  if (rawUrl && !rawUrl.startsWith("http://") && !rawUrl.startsWith("https://")) {
    showFormError("Job URL must start with http:// or https://");
    return;
  }

  const payload = {
    company_name:      company,
    job_title:         title,
    status:            document.getElementById("f-status").value,
    job_url:           rawUrl || null,
    application_date:  document.getElementById("f-app-date").value || null,
    deadline:          document.getElementById("f-deadline").value || null,
    interview_date:    document.getElementById("f-interview-date").value || null,
    job_description:   document.getElementById("f-jd").value.trim() || null,
    notes:             document.getElementById("f-notes").value.trim() || null,
    resume_id:         document.getElementById("f-resume").value
                         ? parseInt(document.getElementById("f-resume").value) : null,
  };

  const saveBtn = document.getElementById("form-save-btn");
  saveBtn.disabled = true;
  saveBtn.textContent = "Saving…";

  try {
    let res;
    if (_editingId) {
      res = await fetch(`${API}/tracker/${_editingId}`, {
        method: "PATCH",
        headers: jsonHeaders(),
        body: JSON.stringify(payload),
      });
    } else {
      res = await fetch(`${API}/tracker/`, {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify(payload),
      });
    }
    if (handle401(res)) return;
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showFormError(err.detail || `Error ${res.status}`);
      return;
    }
    closeDialog();
    await Promise.all([loadStats(), loadList()]);
  } catch (err) {
    showFormError(`Error: ${err.message}`);
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = _editingId ? "Save Changes" : "Save Application";
  }
});

function showFormError(msg) {
  const el = document.getElementById("form-error");
  el.textContent = msg;
  el.style.display = "";
}
function hideFormError() {
  document.getElementById("form-error").style.display = "none";
}

// ── Delete dialog ──────────────────────────────────────────────────────────────

function openDeleteDialog(appId) {
  _deletingId = appId;
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
    const res = await fetch(`${API}/tracker/${id}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    if (handle401(res)) return;
    if (res.status === 204 || res.ok) {
      await Promise.all([loadStats(), loadList()]);
    }
  } catch (e) {
    console.error("Delete failed:", e);
  }
});

// ── Logout ─────────────────────────────────────────────────────────────────────

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("token");
  window.location.href = "login.html";
});
