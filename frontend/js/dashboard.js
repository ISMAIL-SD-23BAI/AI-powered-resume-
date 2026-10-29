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

// ── Resumes ────────────────────────────────────────────────────────────────

async function loadResumes() {
  const res = await fetch(`${API}/resumes/`, { headers: authHeaders() });
  if (res.status === 401) { localStorage.removeItem("token"); window.location.href = "login.html"; return; }
  const resumes = await res.json();
  const list = document.getElementById("resume-list");
  if (!resumes.length) {
    list.innerHTML = '<li class="chip chip-empty">No resumes uploaded yet</li>';
    return;
  }
  list.innerHTML = resumes
    .map(r => `<li class="chip">${escHtml(r.filename)}</li>`)
    .join("");
}

// ── Upload ─────────────────────────────────────────────────────────────────

const fileInput = document.getElementById("resume-file");
const fileLabel = document.getElementById("file-label");
const uploadBtn = document.getElementById("upload-btn");
const uploadStatus = document.getElementById("upload-status");

fileInput.addEventListener("change", () => {
  const name = fileInput.files[0]?.name;
  fileLabel.textContent = name || "Choose PDF";
  uploadBtn.disabled = !name;
});

document.getElementById("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = fileInput.files[0];
  if (!file) return;

  uploadBtn.disabled = true;
  uploadBtn.textContent = "Uploading…";
  uploadStatus.textContent = "";
  uploadStatus.className = "upload-status";

  const body = new FormData();
  body.append("file", file);
  const res = await fetch(`${API}/resumes/upload`, { method: "POST", headers: authHeaders(), body });

  uploadBtn.disabled = false;
  uploadBtn.textContent = "Upload";

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    uploadStatus.textContent = err.detail || "Upload failed";
    uploadStatus.className = "upload-status error";
    return;
  }

  fileLabel.textContent = "Choose PDF";
  fileInput.value = "";
  uploadBtn.disabled = true;
  uploadStatus.textContent = "Uploaded";
  uploadStatus.className = "upload-status ok";
  setTimeout(() => (uploadStatus.textContent = ""), 2500);
  await loadResumes();
});

// ── PDF download ──────────────────────────────────────────────────────────

async function downloadPdf(url, filename, btn) {
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = "…";
  try {
    const res = await fetch(url, {
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
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 10000);
  } catch {
    alert("Network error — is the server running?");
  } finally {
    btn.disabled = false;
    btn.textContent = orig;
  }
}

// ── History ────────────────────────────────────────────────────────────────

function matchBadgeHtml(score) {
  if (score == null) return "";
  const cls = score >= 70 ? "badge-ok" : score >= 50 ? "badge-warn" : "badge-low";
  return `<span class="badge ${cls}">Match: ${score}%</span>`;
}

function renderHistoryItem(item) {
  const roleTitle = item.role_title
    ? escHtml(item.role_title)
    : '<span class="hist-unknown">Unknown Role</span>';
  const seniority = item.seniority_level
    ? `<span class="hist-seniority">${escHtml(item.seniority_level)}</span>`
    : "";
  const clBadge = item.has_cover_letter
    ? '<span class="badge badge-cl">Cover Letter</span>'
    : "";
  const note = item.alignment_note
    ? `<p class="hist-note">${escHtml(item.alignment_note)}</p>`
    : "";

  return `
    <li class="hist-card" data-id="${item.id}">
      <div class="hist-card-main">
        <div class="hist-role-row">
          <strong class="hist-role">${roleTitle}</strong>
          ${seniority}
          ${matchBadgeHtml(item.match_score)}
          ${clBadge}
        </div>
        <div class="hist-meta">
          <span>${escHtml(item.resume_filename)}</span>
          <span class="hist-dot">·</span>
          <span>${fmtDate(item.created_at)}</span>
        </div>
        ${note}
      </div>
      <div class="hist-card-actions">
        <a href="tailor.html?tailored_id=${item.id}" class="btn btn-primary btn-sm">View &amp; Edit</a>
        <button class="btn btn-sm btn-dl-resume" data-id="${item.id}" title="Download tailored resume as PDF">↓ Resume</button>
        ${item.has_cover_letter && item.cover_letter_id
          ? `<button class="btn btn-sm btn-dl-cl" data-cl-id="${item.cover_letter_id}" title="Download cover letter as PDF">↓ Cover Letter</button>`
          : ""}
        <button class="btn btn-sm btn-delete" data-id="${item.id}" aria-label="Delete">Delete</button>
      </div>
    </li>`;
}

async function loadHistory() {
  const loadingEl = document.getElementById("history-loading");
  const emptyEl = document.getElementById("history-empty");
  const listEl = document.getElementById("history-list");
  const countEl = document.getElementById("history-count");

  const res = await fetch(`${API}/history/`, { headers: authHeaders() });
  if (res.status === 401) { localStorage.removeItem("token"); window.location.href = "login.html"; return; }

  loadingEl.style.display = "none";
  const items = await res.json();

  if (!items.length) {
    emptyEl.style.display = "block";
    return;
  }

  countEl.textContent = `${items.length} entr${items.length === 1 ? "y" : "ies"}`;
  listEl.innerHTML = items.map(renderHistoryItem).join("");
  listEl.style.display = "flex";

  listEl.querySelectorAll(".btn-delete").forEach(btn => {
    btn.addEventListener("click", () => confirmDelete(parseInt(btn.dataset.id)));
  });

  listEl.querySelectorAll(".btn-dl-resume").forEach(btn => {
    btn.addEventListener("click", function () {
      const id = this.dataset.id;
      downloadPdf(`${API}/export/resume/${id}`, "resume.pdf", this);
    });
  });

  listEl.querySelectorAll(".btn-dl-cl").forEach(btn => {
    btn.addEventListener("click", function () {
      const id = this.dataset.clId;
      downloadPdf(`${API}/export/cover-letter/${id}`, "cover_letter.pdf", this);
    });
  });
}

// ── Delete ─────────────────────────────────────────────────────────────────

let pendingDeleteId = null;
const dialog = document.getElementById("confirm-dialog");

function confirmDelete(id) {
  pendingDeleteId = id;
  dialog.showModal();
}

document.getElementById("confirm-yes").addEventListener("click", async () => {
  dialog.close();
  if (!pendingDeleteId) return;

  const id = pendingDeleteId;
  pendingDeleteId = null;

  const card = document.querySelector(`.hist-card[data-id="${id}"]`);
  if (card) card.style.opacity = "0.4";

  const res = await fetch(`${API}/history/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });

  if (res.ok || res.status === 204) {
    if (card) card.remove();
    const listEl = document.getElementById("history-list");
    const remaining = listEl.querySelectorAll(".hist-card").length;
    if (!remaining) {
      listEl.style.display = "none";
      document.getElementById("history-empty").style.display = "block";
      document.getElementById("history-count").textContent = "";
    } else {
      document.getElementById("history-count").textContent =
        `${remaining} entr${remaining === 1 ? "y" : "ies"}`;
    }
  } else {
    if (card) card.style.opacity = "1";
    alert("Delete failed — please try again.");
  }
});

document.getElementById("confirm-no").addEventListener("click", () => {
  dialog.close();
  pendingDeleteId = null;
});

// close dialog on backdrop click
dialog.addEventListener("click", (e) => {
  if (e.target === dialog) { dialog.close(); pendingDeleteId = null; }
});

// ── Auth ───────────────────────────────────────────────────────────────────

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("token");
  window.location.href = "login.html";
});

// ── Init ───────────────────────────────────────────────────────────────────

loadResumes();
loadHistory();
