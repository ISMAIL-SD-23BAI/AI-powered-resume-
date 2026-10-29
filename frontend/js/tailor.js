const API = "http://127.0.0.1:8000";
const token = localStorage.getItem("token");
if (!token) window.location.href = "login.html";

function authHeaders() {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

let originalResumeData = null;
let lastResult = null;
let currentTailoredId = null;   // id of the last TailoredResume record
let currentCoverLetterId = null; // id of the saved CoverLetter record

// ── Load resumes into select ───────────────────────────────────────────────

async function loadResumes() {
  const res = await fetch(`${API}/resumes/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "login.html";
    return;
  }
  const resumes = await res.json();
  const sel = document.getElementById("resume-select");
  if (!resumes.length) {
    sel.innerHTML = '<option value="">No resumes — upload one on the Dashboard first</option>';
    return;
  }
  sel.innerHTML = resumes
    .map(r => `<option value="${r.id}" data-resume='${encodeResumeAttr(r)}'>${escHtml(r.filename)}</option>`)
    .join("");
  updateOriginalResume();

  // auto-select from URL param
  const _rId = new URLSearchParams(location.search).get("resume_id");
  if (_rId) {
    const opt = sel.querySelector(`option[value="${parseInt(_rId)}"]`);
    if (opt) { opt.selected = true; updateOriginalResume(); }
  }
}

function encodeResumeAttr(r) {
  // Store as base64 JSON to avoid attribute quoting issues
  return btoa(unescape(encodeURIComponent(JSON.stringify(r))));
}

function decodeResumeAttr(encoded) {
  return JSON.parse(decodeURIComponent(escape(atob(encoded))));
}

function updateOriginalResume() {
  const opt = document.getElementById("resume-select").selectedOptions[0];
  if (!opt?.dataset.resume) { originalResumeData = null; return; }
  try { originalResumeData = decodeResumeAttr(opt.dataset.resume); }
  catch { originalResumeData = null; }
}

document.getElementById("resume-select").addEventListener("change", updateOriginalResume);

// ── Helpers ────────────────────────────────────────────────────────────────

function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// ── Render a structured resume object into a container ─────────────────────

function renderResume(container, structured, matchedSkills) {
  const matched = new Set((matchedSkills || []).map(s => s.toLowerCase()));

  function hl(text) {
    // Highlight matched keywords inside already-escaped HTML
    let out = escHtml(text);
    for (const skill of matched) {
      const re = new RegExp(`(${escRegex(escHtml(skill))})`, "gi");
      out = out.replace(re, "<mark>$1</mark>");
    }
    return out;
  }

  let html = "";

  if (structured.summary) {
    html += `<div class="resume-summary">${hl(structured.summary)}</div>`;
  }

  if (structured.skills?.length) {
    html += `<div class="resume-section"><h4>Skills</h4><ul class="tag-list">`;
    for (const s of structured.skills) {
      const isMatch = matched.has(s.toLowerCase());
      html += `<li class="tag${isMatch ? " tag-match" : ""}">${escHtml(s)}</li>`;
    }
    html += `</ul></div>`;
  }

  if (structured.experience?.length) {
    html += `<div class="resume-section"><h4>Experience</h4>`;
    for (const job of structured.experience) {
      html += `<div class="entry">
        <div class="entry-header">
          <strong>${escHtml(job.title || "")}${job.company ? " — " + escHtml(job.company) : ""}</strong>
          <span>${escHtml(job.dates || "")}</span>
        </div>`;
      if (job.bullets?.length) {
        html += `<ul>${job.bullets.map(b => `<li>${hl(b)}</li>`).join("")}</ul>`;
      }
      html += `</div>`;
    }
    html += `</div>`;
  }

  if (structured.projects?.length) {
    html += `<div class="resume-section"><h4>Projects</h4>`;
    for (const p of structured.projects) {
      html += `<div class="entry">
        <div class="entry-header"><strong>${escHtml(p.name || "")}</strong></div>`;
      if (p.description) html += `<p>${hl(p.description)}</p>`;
      if (p.bullets?.length) {
        html += `<ul>${p.bullets.map(b => `<li>${hl(b)}</li>`).join("")}</ul>`;
      }
      html += `</div>`;
    }
    html += `</div>`;
  }

  if (structured.education?.length) {
    html += `<div class="resume-section"><h4>Education</h4>`;
    for (const e of structured.education) {
      html += `<div class="entry">
        <div class="entry-header">
          <strong>${escHtml(e.degree || "")}${e.institution ? " — " + escHtml(e.institution) : ""}</strong>
          <span>${escHtml(e.dates || "")}</span>
        </div>
      </div>`;
    }
    html += `</div>`;
  }

  container.innerHTML = html || '<p class="muted">No structured content available.</p>';
}

// ── Form submit ────────────────────────────────────────────────────────────

document.getElementById("tailor-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const resume_id = parseInt(document.getElementById("resume-select").value);
  const job_description_text = document.getElementById("jd-text").value.trim();
  if (!resume_id || !job_description_text) return;

  const btn = document.getElementById("tailor-btn");
  const status = document.getElementById("tailor-status");

  btn.disabled = true;
  btn.textContent = "Tailoring…";
  status.textContent = "Contacting AI — this takes 15–30 seconds…";
  status.className = "tailor-status info";
  document.getElementById("result-section").style.display = "none";

  let res;
  try {
    res = await fetch(`${API}/tailor/`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ resume_id, job_description_text }),
    });
  } catch {
    btn.disabled = false;
    btn.textContent = "Tailor with AI";
    status.textContent = "Network error — is the server running?";
    status.className = "tailor-status error";
    return;
  }

  btn.disabled = false;
  btn.textContent = "Tailor with AI";

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    status.textContent = "Error: " + (err.detail || "Failed to tailor resume");
    status.className = "tailor-status error";
    return;
  }

  status.textContent = "";
  lastResult = await res.json();
  currentTailoredId = lastResult.id;
  currentCoverLetterId = null;
  resetCoverLetterPanel();
  renderResult(lastResult);
});

// ── Render result ──────────────────────────────────────────────────────────

function renderResult(data) {
  const tc = data.tailored_content_json || {};
  const tailored = tc.tailored_resume || {};
  const matchScore = typeof tc.match_score === "number" ? tc.match_score : 0;
  const alignmentNote = tc.alignment_note || "";
  const matchedSkills = tc.matched_skills || [];
  const missingSkills = tc.missing_skills || [];

  // Match score badge
  const badge = document.getElementById("match-badge");
  badge.textContent = `Match: ${matchScore}%`;
  badge.className = "badge " + (
    matchScore >= 70 ? "badge-ok" :
    matchScore >= 50 ? "badge-warn" :
    "badge-low"
  );

  // Alignment note
  document.getElementById("alignment-note").textContent = alignmentNote;

  // Missing skills
  const missingSection = document.getElementById("missing-skills-section");
  const missingList = document.getElementById("missing-skills-list");
  if (missingSkills.length) {
    missingList.innerHTML = missingSkills
      .map(s => `<li class="tag tag-missing">${escHtml(s)}</li>`)
      .join("");
    missingSection.style.display = "block";
  } else {
    missingSection.style.display = "none";
  }

  // Before / after
  const originalStructured = originalResumeData?.structured_json || {};
  renderResume(document.getElementById("original-content"), originalStructured, []);
  renderResume(document.getElementById("tailored-content"), tailored, matchedSkills);

  document.getElementById("result-section").style.display = "block";
  document.getElementById("result-section").scrollIntoView({ behavior: "smooth" });
}

// ── Action buttons ─────────────────────────────────────────────────────────

document.getElementById("copy-btn").addEventListener("click", () => {
  if (!lastResult?.tailored_content_json) return;
  const btn = document.getElementById("copy-btn");
  navigator.clipboard
    .writeText(JSON.stringify(lastResult.tailored_content_json, null, 2))
    .then(() => {
      btn.textContent = "Copied!";
      setTimeout(() => (btn.textContent = "Copy Tailored as JSON"), 2000);
    });
});

document.getElementById("new-tailor-btn").addEventListener("click", () => {
  document.getElementById("result-section").style.display = "none";
  document.getElementById("jd-text").value = "";
  currentTailoredId = null;
  currentCoverLetterId = null;
  window.scrollTo({ top: 0, behavior: "smooth" });
});

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("token");
  window.location.href = "login.html";
});

// ── Cover letter ───────────────────────────────────────────────────────────

function resetCoverLetterPanel() {
  document.getElementById("cl-section").style.display = "none";
  document.getElementById("cl-loading").style.display = "none";
  document.getElementById("cl-textarea").value = "";
  document.getElementById("cl-save-status").textContent = "";
  document.getElementById("gen-cl-btn").disabled = false;
  document.getElementById("gen-cl-btn").textContent = "Generate Cover Letter";
}

async function runGenerateCoverLetter() {
  if (!currentTailoredId) return;

  const genBtn = document.getElementById("gen-cl-btn");
  genBtn.disabled = true;
  genBtn.textContent = "Generating…";
  document.getElementById("cl-section").style.display = "none";
  document.getElementById("cl-loading").style.display = "flex";
  document.getElementById("cl-save-status").textContent = "";

  let res;
  try {
    res = await fetch(`${API}/cover-letter/generate`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ tailored_resume_id: currentTailoredId }),
    });
  } catch {
    document.getElementById("cl-loading").style.display = "none";
    genBtn.disabled = false;
    genBtn.textContent = "Generate Cover Letter";
    showClStatus("Network error — is the server running?", "error");
    return;
  }

  document.getElementById("cl-loading").style.display = "none";
  genBtn.disabled = false;
  genBtn.textContent = "Generate Cover Letter";

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    showClStatus("Error: " + (err.detail || "Generation failed"), "error");
    return;
  }

  const cl = await res.json();
  currentCoverLetterId = cl.id;
  document.getElementById("cl-textarea").value = cl.content;
  document.getElementById("cl-section").style.display = "block";
  document.getElementById("cl-textarea").focus();
}

function showClStatus(msg, type) {
  const bar = document.getElementById("cl-status-bar");
  bar.textContent = msg;
  bar.className = "cl-status-bar cl-status-" + type;
  bar.style.display = "block";
  if (type !== "error") setTimeout(() => (bar.style.display = "none"), 3000);
}

document.getElementById("gen-cl-btn").addEventListener("click", runGenerateCoverLetter);
document.getElementById("cl-regen-btn").addEventListener("click", runGenerateCoverLetter);

document.getElementById("cl-save-btn").addEventListener("click", async () => {
  if (!currentCoverLetterId) return;
  const content = document.getElementById("cl-textarea").value.trim();
  if (!content) return;

  const btn = document.getElementById("cl-save-btn");
  const status = document.getElementById("cl-save-status");
  btn.disabled = true;
  btn.textContent = "Saving…";

  const res = await fetch(`${API}/cover-letter/${currentCoverLetterId}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify({ content }),
  });

  btn.disabled = false;
  btn.textContent = "Save Changes";

  if (!res.ok) {
    status.textContent = "Save failed";
    status.className = "cl-save-status error";
  } else {
    status.textContent = "Saved";
    status.className = "cl-save-status ok";
    setTimeout(() => (status.textContent = ""), 2500);
  }
});

document.getElementById("cl-copy-btn").addEventListener("click", () => {
  const text = document.getElementById("cl-textarea").value;
  if (!text) return;
  const btn = document.getElementById("cl-copy-btn");
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = "Copied!";
    setTimeout(() => (btn.textContent = "Copy"), 2000);
  });
});

// ── PDF download ───────────────────────────────────────────────────────────

async function downloadPdf(url, filename, triggerBtn) {
  const orig = triggerBtn.textContent;
  triggerBtn.disabled = true;
  triggerBtn.textContent = "Downloading…";

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
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
    triggerBtn.disabled = false;
    triggerBtn.textContent = orig;
  }
}

document.getElementById("dl-resume-btn").addEventListener("click", function () {
  if (!currentTailoredId) return;
  downloadPdf(`${API}/export/resume/${currentTailoredId}`, "resume.pdf", this);
});

document.getElementById("cl-dl-btn").addEventListener("click", function () {
  if (!currentCoverLetterId) return;
  downloadPdf(`${API}/export/cover-letter/${currentCoverLetterId}`, "cover_letter.pdf", this);
});

// ── View mode: load existing tailored resume via ?tailored_id= ─────────────

async function loadExistingEntry(tailoredId) {
  // Switch UI to view mode
  document.getElementById("tailor-input-section").style.display = "none";
  document.getElementById("view-mode-bar").style.display = "flex";

  const label = document.getElementById("view-mode-label");
  label.textContent = "Loading…";

  // 1. Fetch the tailored resume record
  let tailoredRes;
  try {
    tailoredRes = await fetch(`${API}/tailor/${tailoredId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    label.textContent = "Network error loading entry.";
    return;
  }
  if (!tailoredRes.ok) {
    label.textContent = tailoredRes.status === 404 ? "Entry not found." : "Failed to load entry.";
    return;
  }
  const tailored = await tailoredRes.json();

  // 2. Fetch the original resume for the "before" panel
  const resumeRes = await fetch(`${API}/resumes/${tailored.resume_id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (resumeRes.ok) {
    originalResumeData = await resumeRes.json();
  }

  // 3. Set IDs so cover letter buttons work
  currentTailoredId = tailored.id;
  currentCoverLetterId = null;
  lastResult = tailored;

  // Show role title in the view bar if available
  const tc = tailored.tailored_content_json || {};
  label.textContent = "";

  // 4. Render the result section
  renderResult(tailored);

  // 5. Try loading an existing cover letter
  const clRes = await fetch(`${API}/cover-letter/for/${tailoredId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (clRes.ok) {
    const cl = await clRes.json();
    currentCoverLetterId = cl.id;
    document.getElementById("cl-textarea").value = cl.content;
    document.getElementById("cl-section").style.display = "block";
  }
}

// ── Init ────────────────────────────────────────────────────────────────────

const _viewId = new URLSearchParams(location.search).get("tailored_id");
if (_viewId) {
  loadExistingEntry(parseInt(_viewId));
} else {
  loadResumes();
}
