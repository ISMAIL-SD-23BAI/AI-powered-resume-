const API = "http://127.0.0.1:8000";
const token = localStorage.getItem("token");
if (!token) window.location.href = "login.html";

function authHeaders(extra = {}) {
  return { Authorization: `Bearer ${token}`, ...extra };
}

// ── file selection ────────────────────────────────────────────────────────────

const fileInput = document.getElementById("file-input");
const dropZone  = document.getElementById("drop-zone");
const fileName  = document.getElementById("file-name");
const uploadBtn = document.getElementById("upload-btn");

let selectedFile = null;

function setFile(f) {
  if (!f) return;
  if (!f.name.toLowerCase().endsWith(".pdf")) {
    showStatus("Only PDF files are accepted.", "error");
    return;
  }
  if (f.size > 5 * 1024 * 1024) {
    showStatus("File exceeds the 5 MB limit.", "error");
    return;
  }
  selectedFile = f;
  fileName.textContent = f.name;
  uploadBtn.disabled = false;
  showStatus("", "");
}

fileInput.addEventListener("change", () => setFile(fileInput.files[0]));

dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  setFile(e.dataTransfer.files[0]);
});

// ── upload ────────────────────────────────────────────────────────────────────

uploadBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  uploadBtn.disabled = true;
  uploadBtn.textContent = "Uploading & parsing…";
  showStatus("Extracting text and running AI parsing — this may take 10–20 s…", "info");

  const body = new FormData();
  body.append("file", selectedFile);

  try {
    const res = await fetch(`${API}/resumes/upload`, {
      method: "POST",
      headers: authHeaders(),
      body,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? "Upload failed");

    showStatus("", "");
    renderResult(data);
    loadPrevResumes();
  } catch (err) {
    showStatus(err.message, "error");
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Parse Resume";
  }
});

// ── result rendering ──────────────────────────────────────────────────────────

function renderResult(resume) {
  document.getElementById("upload-card").style.display = "none";
  const section = document.getElementById("result-section");
  section.style.display = "block";

  document.getElementById("result-filename").textContent = resume.filename;

  const s = resume.structured_json;
  const hasParseError = s && s.parse_error;
  const badge = document.getElementById("parse-badge");
  if (hasParseError) {
    badge.textContent = "Partial parse";
    badge.className = "badge badge-warn";
  } else {
    badge.textContent = "Parsed successfully";
    badge.className = "badge badge-ok";
  }

  // Skills
  const skillsList = document.getElementById("skills-list");
  if (s && s.skills && s.skills.length) {
    skillsList.innerHTML = s.skills.map(sk => `<li class="tag">${esc(sk)}</li>`).join("");
  } else {
    skillsList.innerHTML = "<li class='muted'>None found</li>";
  }

  // Experience
  const expList = document.getElementById("experience-list");
  if (s && s.experience && s.experience.length) {
    expList.innerHTML = s.experience.map(e => `
      <div class="entry">
        <div class="entry-header">
          <strong>${esc(e.title || "")}</strong>
          <span class="muted">${esc(e.company || "")}${e.dates ? " · " + esc(e.dates) : ""}</span>
        </div>
        ${e.bullets && e.bullets.length ? `<ul>${e.bullets.map(b => `<li>${esc(b)}</li>`).join("")}</ul>` : ""}
      </div>`).join("");
  } else {
    expList.innerHTML = "<p class='muted'>None found</p>";
  }

  // Education
  const eduList = document.getElementById("education-list");
  if (s && s.education && s.education.length) {
    eduList.innerHTML = s.education.map(e => `
      <div class="entry">
        <div class="entry-header">
          <strong>${esc(e.degree || "")}</strong>
          <span class="muted">${esc(e.institution || "")}${e.dates ? " · " + esc(e.dates) : ""}</span>
        </div>
      </div>`).join("");
  } else {
    eduList.innerHTML = "<p class='muted'>None found</p>";
  }

  // Projects
  const projList = document.getElementById("projects-list");
  if (s && s.projects && s.projects.length) {
    projList.innerHTML = s.projects.map(p => `
      <div class="entry">
        <div class="entry-header">
          <strong>${esc(p.name || "")}</strong>
        </div>
        ${p.description ? `<p class="muted">${esc(p.description)}</p>` : ""}
        ${p.bullets && p.bullets.length ? `<ul>${p.bullets.map(b => `<li>${esc(b)}</li>`).join("")}</ul>` : ""}
      </div>`).join("");
  } else {
    projList.innerHTML = "<p class='muted'>None found</p>";
  }

  // Raw text
  document.getElementById("raw-text-output").textContent = resume.raw_text || "(empty)";
}

document.getElementById("upload-another-btn").addEventListener("click", () => {
  document.getElementById("result-section").style.display = "none";
  document.getElementById("upload-card").style.display = "block";
  selectedFile = null;
  fileInput.value = "";
  fileName.textContent = "";
  uploadBtn.disabled = true;
});

// ── previous resumes list ─────────────────────────────────────────────────────

async function loadPrevResumes() {
  const container = document.getElementById("prev-list");
  const empty = document.getElementById("prev-empty");
  try {
    const res = await fetch(`${API}/resumes/`, { headers: authHeaders() });
    if (res.status === 401) { localStorage.removeItem("token"); window.location.href = "login.html"; return; }
    const resumes = await res.json();
    if (!resumes.length) { empty.style.display = "block"; return; }
    empty.style.display = "none";
    container.innerHTML = resumes.map(r => `
      <div class="prev-item">
        <div class="prev-item-info">
          <strong>${esc(r.filename)}</strong>
          <span class="muted">${new Date(r.uploaded_at).toLocaleString()}</span>
        </div>
        <div class="prev-item-meta">
          ${r.structured_json && r.structured_json.skills
            ? `<span class="tag-sm">${r.structured_json.skills.length} skills</span>`
            : ""}
          ${r.structured_json && r.structured_json.experience
            ? `<span class="tag-sm">${r.structured_json.experience.length} roles</span>`
            : ""}
        </div>
        <button class="btn btn-outline btn-sm delete-btn" data-id="${r.id}">Delete</button>
      </div>`).join("");

    container.querySelectorAll(".delete-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this resume?")) return;
        await fetch(`${API}/resumes/${btn.dataset.id}`, { method: "DELETE", headers: authHeaders() });
        loadPrevResumes();
      });
    });
  } catch {
    empty.textContent = "Could not load resumes.";
  }
}

// ── misc ──────────────────────────────────────────────────────────────────────

function showStatus(msg, type) {
  const el = document.getElementById("upload-status");
  el.textContent = msg;
  el.className = type === "error" ? "upload-status error" : type === "info" ? "upload-status info" : "upload-status";
}

function esc(str) {
  return String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("token");
  window.location.href = "login.html";
});

loadPrevResumes();
