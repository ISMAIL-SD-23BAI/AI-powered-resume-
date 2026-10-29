/* interview.js — AI Interview Preparation module */

const API = "http://127.0.0.1:8000";
let _token = null;

// ── Auth ───────────────────────────────────────────────────────────────────────

function token() {
  if (!_token) _token = localStorage.getItem("token");
  return _token;
}

function authHeaders() {
  return { "Content-Type": "application/json", Authorization: `Bearer ${token()}` };
}

async function api(method, path, body) {
  const opts = { method, headers: authHeaders() };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const resp = await fetch(API + path, opts);
  if (resp.status === 401) { localStorage.removeItem("token"); location.href = "login.html"; }
  return resp;
}

// ── State ──────────────────────────────────────────────────────────────────────

let _session = null;        // full session object (questions array)
let _activeQIdx = 0;
let _deleteSessionId = null;

// ── DOM helpers ────────────────────────────────────────────────────────────────

const $ = id => document.getElementById(id);
const setHtml = (id, html) => $(id).innerHTML = html;

function setStatus(id, msg, isError = false) {
  const el = $(id);
  if (!el) return;
  el.textContent = msg;
  el.style.color = isError ? "var(--danger)" : "var(--muted)";
}

// ── Bootstrap ──────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  if (!token()) { location.href = "index.html"; return; }

  $("logout-btn").addEventListener("click", () => {
    localStorage.removeItem("token");
    location.href = "index.html";
  });

  loadResumes();
  loadHistory();

  $("session-form").addEventListener("submit", onGenerateSubmit);
  $("answer-textarea").addEventListener("input", onAnswerInput);
  $("submit-answer-btn").addEventListener("click", onSubmitAnswer);
  $("try-again-btn").addEventListener("click", resetAnswerForm);
  $("close-session-btn").addEventListener("click", closeSession);
  $("delete-cancel-btn").addEventListener("click", () => $("delete-dialog").close());
  $("delete-confirm-btn").addEventListener("click", confirmDelete);
});

// ── Resume list ────────────────────────────────────────────────────────────────

async function loadResumes() {
  const resp = await api("GET", "/resumes/");
  if (!resp.ok) return;
  const resumes = await resp.json();
  const sel = $("resume-select");
  sel.innerHTML = resumes.length
    ? `<option value="">— Select a resume —</option>` +
      resumes.map(r => `<option value="${r.id}">${escHtml(r.filename)}</option>`).join("")
    : `<option value="">No resumes uploaded yet</option>`;
  sel.addEventListener("change", updateGenerateBtn);
  $("jd-textarea").addEventListener("input", updateGenerateBtn);
  updateGenerateBtn();
}

function updateGenerateBtn() {
  const ok = $("resume-select").value && $("jd-textarea").value.trim().length >= 50;
  $("generate-btn").disabled = !ok;
}

// ── Generate session ───────────────────────────────────────────────────────────

async function onGenerateSubmit(e) {
  e.preventDefault();
  const resumeId = parseInt($("resume-select").value, 10);
  const jdText = $("jd-textarea").value.trim();

  $("generate-btn").disabled = true;
  setStatus("generate-status", "Generating questions…");

  let resp;
  try {
    resp = await api("POST", "/interview/", {
      resume_id: resumeId,
      job_description_text: jdText,
    });
  } catch (_) {
    setStatus("generate-status", "Could not reach the interview service. Check your connection and try again.", true);
    $("generate-btn").disabled = false;
    return;
  }

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    setStatus("generate-status", resp.status === 429 ? "Question generation limit reached. Wait a minute, then try again." : (err.detail || "Failed to generate questions. Please try again."), true);
    $("generate-btn").disabled = false;
    return;
  }

  const session = await resp.json();
  setStatus("generate-status", "");
  $("generate-btn").disabled = false;
  openSession(session);
  loadHistory();
}

// ── Session display ────────────────────────────────────────────────────────────

function openSession(session) {
  _session = session;
  _activeQIdx = 0;

  const role = session.role_title || "Interview Session";
  $("session-role-heading").textContent = role;
  $("session-meta").textContent =
    `${session.question_count} question${session.question_count !== 1 ? "s" : ""} · Resume ID ${session.resume_id}`;

  buildTabs();
  renderQuestion(0);
  $("session-section").style.display = "";
  $("session-section").scrollIntoView({ behavior: "smooth", block: "start" });
}

function closeSession() {
  _session = null;
  $("session-section").style.display = "none";
  $("session-form").reset();
  updateGenerateBtn();
}

function buildTabs() {
  const tabs = $("question-tabs");
  const TYPE_ABBR = { technical: "Tech", behavioral: "Behav", hr: "HR", project: "Proj" };
  tabs.innerHTML = _session.questions.map((q, i) =>
    `<button class="ivw-tab${i === 0 ? " ivw-tab-active" : ""}"
       data-idx="${i}" role="tab" aria-selected="${i === 0}"
       aria-label="Question ${i + 1}: ${TYPE_ABBR[q.type] || q.type}">
       <span class="ivw-tab-num">${i + 1}</span>
       <span class="ivw-tab-type ivw-type-${q.type}">${TYPE_ABBR[q.type] || q.type}</span>
     </button>`
  ).join("");

  tabs.querySelectorAll(".ivw-tab").forEach(btn =>
    btn.addEventListener("click", () => switchTab(parseInt(btn.dataset.idx, 10)))
  );
}

function switchTab(idx) {
  _activeQIdx = idx;
  $("question-tabs").querySelectorAll(".ivw-tab").forEach((btn, i) => {
    btn.classList.toggle("ivw-tab-active", i === idx);
    btn.setAttribute("aria-selected", i === idx);
  });
  renderQuestion(idx);
}

function renderQuestion(idx) {
  const q = _session.questions[idx];
  const TYPE_LABELS = { technical: "Technical", behavioral: "Behavioural", hr: "HR", project: "Project" };

  $("q-type-badge").textContent = TYPE_LABELS[q.type] || q.type;
  $("q-type-badge").className = `ivw-type-badge ivw-type-${q.type}`;
  $("q-number").textContent = `Question ${idx + 1} of ${_session.questions.length}`;
  $("q-text").textContent = q.question;
  $("q-guidance").textContent = q.guidance || "";
  $("q-structure").textContent = q.answer_structure ? `Example answer structure: ${q.answer_structure}` : "Example answer structure: Situation/task → action and reasoning → result and learning.";

  resetAnswerForm();
  loadPrevAttempts(idx);
}

function resetAnswerForm() {
  $("answer-textarea").value = "";
  $("answer-char-count").textContent = "0 / 5000";
  $("submit-answer-btn").disabled = true;
  $("answer-status").textContent = "";
  $("answer-form-wrap").style.display = "";
  $("feedback-panel").style.display = "none";
}

function onAnswerInput() {
  const len = $("answer-textarea").value.length;
  $("answer-char-count").textContent = `${len} / 5000`;
  $("submit-answer-btn").disabled = len < 10 || len > 5000;
}

// ── Submit answer ──────────────────────────────────────────────────────────────

async function onSubmitAnswer() {
  const answer = $("answer-textarea").value.trim();
  $("submit-answer-btn").disabled = true;
  setStatus("answer-status", "Evaluating…");

  let resp;
  try {
    resp = await api("POST", `/interview/${_session.id}/answer`, {
      question_index: _activeQIdx,
      user_answer: answer,
    });
  } catch (_) {
    setStatus("answer-status", "Could not reach the interview service. Your answer may not have been saved; check your connection and retry.", true);
    $("submit-answer-btn").disabled = false;
    return;
  }

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    setStatus("answer-status", resp.status === 429 ? "Answer evaluation limit reached. Wait a minute, then retry." : (err.detail || "Submission failed. Please try again."), true);
    $("submit-answer-btn").disabled = false;
    return;
  }

  const result = await resp.json();
  setStatus("answer-status", "");
  $("answer-form-wrap").style.display = "none";
  renderFeedback(result);
  loadPrevAttempts(_activeQIdx);
  updateTabBadge(_activeQIdx);
}

// ── Feedback rendering ─────────────────────────────────────────────────────────

function renderFeedback(answerOut) {
  const fb = answerOut.feedback;

  if (!fb) {
    // Evaluation failed — show the error, let user retry
    $("score-bars").innerHTML = "";
    $("strengths-list").innerHTML = "<li>Evaluation unavailable.</li>";
    $("improvements-list").innerHTML = "";
    $("feedback-text").textContent = answerOut.evaluation_error || "Evaluation failed.";
    $("feedback-disclaimer").textContent = "";
    $("overall-score-badge").textContent = "";
    $("overall-score-badge").className = "ivw-overall-badge";
    $("unsupported-wrap").style.display = "none";
    $("feedback-panel").style.display = "";
    return;
  }

  $("overall-score-badge").textContent = `${fb.overall_score}/5`;
  $("overall-score-badge").className = `ivw-overall-badge ivw-score-${fb.overall_score}`;

  const SCORE_DIMS = [
    ["Relevance", fb.relevance_score],
    ["Clarity", fb.clarity_score],
    ["Structure", fb.structure_score],
  ];
  if (fb.technical_score != null) SCORE_DIMS.push(["Technical", fb.technical_score]);

  $("score-bars").innerHTML = SCORE_DIMS.map(([label, val]) => `
    <div class="ivw-score-row">
      <span class="ivw-score-label">${label}</span>
      <div class="ivw-score-track">
        <div class="ivw-score-fill ivw-score-${val}" style="width:${val * 20}%"></div>
      </div>
      <span class="ivw-score-val">${val}/5</span>
    </div>`).join("");

  $("strengths-list").innerHTML = (fb.strengths || [])
    .map(s => `<li>${escHtml(s)}</li>`).join("") || "<li>None noted.</li>";
  $("improvements-list").innerHTML = (fb.improvements || [])
    .map(s => `<li>${escHtml(s)}</li>`).join("") || "<li>None noted.</li>";

  if (fb.unsupported_claims && fb.unsupported_claims.length > 0) {
    $("unsupported-list").innerHTML = fb.unsupported_claims.map(c => `<li>${escHtml(c)}</li>`).join("");
    $("unsupported-wrap").style.display = "";
  } else {
    $("unsupported-wrap").style.display = "none";
  }

  $("feedback-text").textContent = fb.feedback_text || "";
  $("feedback-disclaimer").textContent = fb.disclaimer || "";
  $("feedback-panel").style.display = "";
}

// ── Previous attempts ──────────────────────────────────────────────────────────

async function loadPrevAttempts(qIdx) {
  if (!_session) return;
  const resp = await api("GET", `/interview/${_session.id}/question/${qIdx}`);
  if (!resp.ok) return;
  const data = await resp.json();

  if (data.attempt_count <= 1) {
    $("prev-attempts-wrap").style.display = "none";
    return;
  }

  // Show all but the latest (latest is shown in main feedback panel)
  const prevAttempts = data.attempts.slice(0, -1);
  $("attempt-count-badge").textContent = data.attempt_count;
  $("prev-attempts-list").innerHTML = prevAttempts.map((a, i) =>
    renderAttemptCollapsed(a, i + 1)
  ).join("");
  $("prev-attempts-wrap").style.display = "";

  // Toggle expand
  $("prev-attempts-list").querySelectorAll(".ivw-attempt-toggle").forEach(btn => {
    btn.addEventListener("click", () => {
      const body = btn.closest(".ivw-attempt").querySelector(".ivw-attempt-body");
      const open = body.style.display !== "none";
      body.style.display = open ? "none" : "";
      btn.textContent = open ? "Show" : "Hide";
    });
  });
}

function renderAttemptCollapsed(attempt, num) {
  const score = attempt.feedback ? `${attempt.feedback.overall_score}/5` : "No feedback";
  const date = new Date(attempt.created_at).toLocaleString();
  const feedbackHtml = attempt.feedback
    ? `<p class="ivw-attempt-feedback">${escHtml(attempt.feedback.feedback_text || "")}</p>`
    : `<p class="ivw-attempt-feedback" style="color:var(--muted)">${escHtml(attempt.evaluation_error || "Evaluation unavailable.")}</p>`;

  return `
    <div class="ivw-attempt">
      <div class="ivw-attempt-header">
        <span class="ivw-attempt-label">Attempt ${num} — ${date}</span>
        <span class="ivw-overall-badge ivw-score-${attempt.feedback ? attempt.feedback.overall_score : 0} ivw-attempt-score">${score}</span>
        <button class="btn btn-ghost btn-sm ivw-attempt-toggle">Show</button>
      </div>
      <div class="ivw-attempt-body" style="display:none">
        <p class="ivw-attempt-answer"><strong>Your answer:</strong> ${escHtml(attempt.user_answer)}</p>
        ${feedbackHtml}
      </div>
    </div>`;
}

// ── Tab badge update ───────────────────────────────────────────────────────────

function updateTabBadge(idx) {
  const tab = $("question-tabs").querySelectorAll(".ivw-tab")[idx];
  if (tab) tab.classList.add("ivw-tab-answered");
}

// ── Session history ────────────────────────────────────────────────────────────

async function loadHistory() {
  const resp = await api("GET", "/interview/");
  if (!resp.ok) return;
  const sessions = await resp.json();

  $("history-loading").style.display = "none";
  const list = $("history-list");
  const empty = $("history-empty");
  const badge = $("history-count");

  badge.textContent = sessions.length || "";

  if (sessions.length === 0) {
    empty.style.display = "";
    list.style.display = "none";
    return;
  }

  empty.style.display = "none";
  list.style.display = "";
  list.innerHTML = sessions.map(s => renderHistoryItem(s)).join("");

  list.querySelectorAll(".ivw-history-open").forEach(btn => {
    btn.addEventListener("click", async () => {
      const sid = parseInt(btn.dataset.id, 10);
      const resp = await api("GET", `/interview/${sid}`);
      if (!resp.ok) return;
      openSession(await resp.json());
    });
  });

  list.querySelectorAll(".ivw-history-delete").forEach(btn => {
    btn.addEventListener("click", () => {
      _deleteSessionId = parseInt(btn.dataset.id, 10);
      $("delete-dialog").showModal();
    });
  });
}

function renderHistoryItem(s) {
  const date = new Date(s.created_at).toLocaleDateString();
  const role = s.role_title ? escHtml(s.role_title) : "Role not specified";
  const progress = `${s.answered_count}/${s.question_count} answered`;
  return `
    <li class="history-item ivw-history-item">
      <div class="history-item-main">
        <span class="history-item-name">${role}</span>
        <span class="history-item-meta">${progress} · ${s.answer_count} submission${s.answer_count !== 1 ? "s" : ""} · ${date}</span>
      </div>
      <div class="history-item-actions">
        <button class="btn btn-outline btn-sm ivw-history-open" data-id="${s.id}">Open</button>
        <button class="btn btn-ghost btn-sm ivw-history-delete" data-id="${s.id}" style="color:var(--danger)">Delete</button>
      </div>
    </li>`;
}

async function confirmDelete() {
  if (!_deleteSessionId) return;
  $("delete-dialog").close();
  const resp = await api("DELETE", `/interview/${_deleteSessionId}`);
  if (resp.ok) {
    if (_session && _session.id === _deleteSessionId) closeSession();
    _deleteSessionId = null;
    loadHistory();
  }
}

// ── Utilities ──────────────────────────────────────────────────────────────────

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
