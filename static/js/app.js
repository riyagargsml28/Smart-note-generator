/**
 * Smart Notes Generator - Frontend Application Logic
 * Implements view navigation, document & audio uploads, AI notes synthesis,
 * active recall flashcards, interactive self-quiz engine, inline editing, and exports.
 */

// Global Application State
const AppState = {
  currentNote: null,
  isEditing: false,
  samplesCache: [],
  quizScore: { correct: 0, answered: 0, total: 0 },
  historySearchTimeout: null
};

// DOM Content Loaded Initializer
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  loadConfigStatus();
  loadSamplesList();
  loadNotesHistory();
  updateWordCount();
});

/* ==========================================================================
   1. Navigation & Routing
   ========================================================================== */
function navigateTo(pageId) {
  // Update nav buttons
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-page") === pageId);
  });

  // Switch visible page view
  document.querySelectorAll(".page-view").forEach(view => {
    view.classList.remove("active");
  });

  const targetView = document.getElementById(`view-${pageId}`);
  if (targetView) {
    targetView.classList.add("active");
  }

  // Refresh history view if navigated
  if (pageId === "history") {
    loadNotesHistory();
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

function switchInputTab(tabId) {
  document.querySelectorAll(".tab-strip .tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
  });

  document.querySelectorAll(".generator-main-card .tab-pane").forEach(pane => {
    pane.classList.toggle("active", pane.id === tabId);
  });
}

function switchNotesSection(sectionId) {
  document.querySelectorAll(".notes-subnav .subnav-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("onclick").includes(sectionId));
  });

  document.querySelectorAll(".notes-display-body .note-tab-content").forEach(content => {
    content.classList.toggle("active", content.id === sectionId);
  });
}

/* ==========================================================================
   2. Configuration & Initialization
   ========================================================================== */
async function loadConfigStatus() {
  try {
    const res = await fetch("/api/config-status");
    if (res.ok) {
      const data = await res.json();
      console.log("[Status] Config loaded:", data);
    }
  } catch (err) {
    console.warn("[Warning] Could not load config status:", err);
  }
}

async function loadSamplesList() {
  try {
    const res = await fetch("/api/samples");
    if (res.ok) {
      const data = await res.json();
      AppState.samplesCache = data.samples || [];
      renderSampleModalList();
    }
  } catch (err) {
    console.warn("[Warning] Could not load samples:", err);
  }
}

/* ==========================================================================
   3. Input Handling & File Uploads
   ========================================================================== */
function initEventListeners() {
  const textarea = document.getElementById("transcript-input");
  if (textarea) {
    textarea.addEventListener("input", updateWordCount);
  }

  // Setup Drag & Drop for Documents
  setupDropZone("document-dropzone", (file) => handleDocumentUpload(file));

  // Setup Drag & Drop for Audio
  setupDropZone("audio-dropzone", (file) => handleAudioUpload(file));
}

function setupDropZone(dropZoneId, fileHandler) {
  const zone = document.getElementById(dropZoneId);
  if (!zone) return;

  ["dragenter", "dragover"].forEach(evtName => {
    zone.addEventListener(evtName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      zone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(evtName => {
    zone.addEventListener(evtName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      zone.classList.remove("dragover");
    });
  });

  zone.addEventListener("drop", (e) => {
    if (e.dataTransfer && e.dataTransfer.files.length > 0) {
      fileHandler(e.dataTransfer.files[0]);
    }
  });
}

function updateWordCount() {
  const text = (document.getElementById("transcript-input").value || "").trim();
  const words = text ? text.split(/\s+/).length : 0;
  const chars = text.length;
  document.getElementById("word-char-counter").innerText = `${words.toLocaleString()} words | ${chars.toLocaleString()} characters`;
}

function clearTranscriptInput() {
  document.getElementById("transcript-input").value = "";
  updateWordCount();
  showToast("Transcript editor cleared.", "info");
}

function handleSubjectChange(value) {
  const customInput = document.getElementById("custom-subject-input");
  if (value === "__custom__") {
    customInput.style.display = "block";
    customInput.focus();
  } else {
    customInput.style.display = "none";
  }
}

// Upload & Parse Document
async function handleDocumentUpload(file) {
  if (!file) return;

  const statusBox = document.getElementById("document-upload-status");
  statusBox.style.display = "block";
  statusBox.innerHTML = `<span>⏳ Extracting text from <strong>${file.name}</strong>...</span>`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload-file", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Failed to parse document.");
    }

    document.getElementById("transcript-input").value = data.text;
    updateWordCount();
    statusBox.innerHTML = `<span>✅ <strong>${file.name}</strong> parsed successfully (${data.word_count} words).</span>`;
    showToast(`Loaded ${data.word_count} words from ${file.name}`, "success");

    // Automatically switch to the paste tab to show the extracted content
    switchInputTab("tab-paste");
  } catch (err) {
    statusBox.innerHTML = `<span style="color:#e11d48;">❌ ${err.message}</span>`;
    showToast(err.message, "error");
  }
}

// Upload & Transcribe Audio
async function handleAudioUpload(file) {
  if (!file) return;

  const statusBox = document.getElementById("audio-upload-status");
  statusBox.style.display = "block";
  statusBox.innerHTML = `<span>🎙️ Transcribing <strong>${file.name}</strong> (${(file.size / (1024 * 1024)).toFixed(1)} MB)...</span>`;

  const formData = new FormData();
  formData.append("audio", file);

  try {
    const res = await fetch("/api/transcribe-audio", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Audio transcription failed.");
    }

    document.getElementById("transcript-input").value = data.text;
    updateWordCount();

    const durationInfo = data.duration_seconds ? ` (~${Math.round(data.duration_seconds)}s)` : "";
    statusBox.innerHTML = `<span>✅ Transcription complete via <strong>${data.engine}</strong>${durationInfo}.</span>`;
    showToast("Audio transcription completed!", "success");

    // Automatically switch to the paste tab to show the transcribed text
    switchInputTab("tab-paste");
  } catch (err) {
    statusBox.innerHTML = `<span style="color:#e11d48;">❌ ${err.message}</span>`;
    showToast(err.message, "error");
  }
}

/* ==========================================================================
   4. Sample Loaders
   ========================================================================== */
function loadSampleIntoGenerator(sampleKey) {
  const sample = AppState.samplesCache.find(s => s.id.includes(sampleKey));
  if (sample) {
    document.getElementById("transcript-input").value = sample.content;
    const subjectSelect = document.getElementById("subject-select");
    subjectSelect.value = sample.subject;
    handleSubjectChange(sample.subject);

    updateWordCount();
    navigateTo("generator");
    switchInputTab("tab-paste");
    showToast(`Loaded sample: ${sample.title}`, "success");
  } else {
    // If not yet loaded into cache, request samples
    loadSamplesList().then(() => {
      const retry = AppState.samplesCache.find(s => s.id.includes(sampleKey));
      if (retry) {
        document.getElementById("transcript-input").value = retry.content;
        updateWordCount();
        navigateTo("generator");
        showToast(`Loaded sample: ${retry.title}`, "success");
      }
    });
  }
}

function loadSampleModal() {
  document.getElementById("sample-modal").style.display = "flex";
}

function closeSampleModal() {
  document.getElementById("sample-modal").style.display = "none";
}

function closeModalOnBackdrop(e) {
  if (e.target.id === "sample-modal") {
    closeSampleModal();
  }
}

function renderSampleModalList() {
  const list = document.getElementById("sample-modal-list");
  if (!list) return;

  if (AppState.samplesCache.length === 0) {
    list.innerHTML = `<p class="text-muted">No sample lectures available.</p>`;
    return;
  }

  list.innerHTML = AppState.samplesCache.map(sample => `
    <div class="sample-modal-item" onclick="selectSampleAndClose('${sample.id}')">
      <div>
        <strong style="color:var(--text-main); font-size:0.95rem;">${sample.title}</strong>
        <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.2rem;">
          Subject: ${sample.subject} • ${sample.words} words
        </div>
      </div>
      <button class="btn btn-secondary btn-sm">Load</button>
    </div>
  `).join("");
}

function selectSampleAndClose(sampleId) {
  const sample = AppState.samplesCache.find(s => s.id === sampleId);
  if (sample) {
    document.getElementById("transcript-input").value = sample.content;
    const subjectSelect = document.getElementById("subject-select");
    subjectSelect.value = sample.subject;
    handleSubjectChange(sample.subject);

    updateWordCount();
    closeSampleModal();
    switchInputTab("tab-paste");
    showToast(`Loaded: ${sample.title}`, "success");
  }
}

/* ==========================================================================
   5. AI Notes Generation Pipeline
   ========================================================================== */
async function generateNotes() {
  const rawTranscript = (document.getElementById("transcript-input").value || "").trim();
  if (!rawTranscript) {
    showToast("Please paste or upload a lecture transcript first.", "error");
    return;
  }

  // Get subject
  const subjectSelect = document.getElementById("subject-select");
  let subject = subjectSelect.value;
  if (subject === "__custom__") {
    subject = (document.getElementById("custom-subject-input").value || "").trim() || "General";
  }

  // Get detail level
  const detailRadio = document.querySelector('input[name="detail_level"]:checked');
  const detailLevel = detailRadio ? detailRadio.value : "medium";

  // Pre-processing options
  const cleanFillers = document.getElementById("clean-fillers-check").checked;
  const removeTimestamps = document.getElementById("remove-timestamps-check").checked;
  const enableSegmentation = document.getElementById("enable-segmentation-check").checked;

  // UI Progress Animation
  const progressBox = document.getElementById("generation-progress");
  const progressBar = document.getElementById("progress-bar");
  const progressText = document.getElementById("progress-text");
  const generateBtn = document.getElementById("btn-generate");

  progressBox.style.display = "block";
  generateBtn.disabled = true;

  updateProgress(20, "Validating transcript content...");

  setTimeout(() => updateProgress(45, "Cleaning verbal fillers and formatting timestamps..."), 400);
  setTimeout(() => updateProgress(70, "Segmenting topics and extracting key concepts..."), 900);
  setTimeout(() => updateProgress(88, "Synthesizing structured notes, formulas, and quiz questions..."), 1500);

  try {
    const res = await fetch("/api/generate-notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transcript: rawTranscript,
        subject: subject,
        detail_level: detailLevel,
        clean_fillers: cleanFillers,
        remove_timestamps: removeTimestamps,
        enable_segmentation: enableSegmentation
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Failed to generate study notes.");
    }

    updateProgress(100, "Notes generated and saved successfully!");

    // Set active note state
    AppState.currentNote = {
      id: data.note_id,
      title: data.title,
      subject: data.subject,
      detail_level: data.detail_level,
      word_count: data.word_count,
      raw_transcript: rawTranscript,
      cleaning_stats: data.cleaning_stats,
      structured_notes: data.structured_notes
    };

    // Render notes into the viewer
    renderCurrentNote();

    // Show 'Current Note' in navigation
    document.getElementById("nav-notes-btn").style.display = "inline-flex";

    // Switch to notes view
    setTimeout(() => {
      progressBox.style.display = "none";
      generateBtn.disabled = false;
      navigateTo("notes-view");
      showToast("Smart Study Notes successfully generated!", "success");
      loadNotesHistory(); // Refresh background history count
    }, 500);

  } catch (err) {
    progressBox.style.display = "none";
    generateBtn.disabled = false;
    showToast(err.message, "error");
  }
}

function updateProgress(percent, message) {
  const bar = document.getElementById("progress-bar");
  const text = document.getElementById("progress-text");
  if (bar) bar.style.width = `${percent}%`;
  if (text) text.innerText = message;
}

/* ==========================================================================
   6. Notes Rendering & Display
   ========================================================================== */
function renderCurrentNote() {
  const note = AppState.currentNote;
  if (!note || !note.structured_notes) return;

  const data = note.structured_notes;

  // Header badges & title
  document.getElementById("note-view-title").innerText = cleanTimestamps(data.title || note.title || "Lecture Notes");
  document.getElementById("note-view-subject").innerText = note.subject || "General";
  document.getElementById("note-view-level").innerText = `${(note.detail_level || "Medium").toUpperCase()} NOTES`;
  document.getElementById("note-view-words").innerText = `${(note.word_count || 0).toLocaleString()} words`;

  const engineName = data._meta ? data._meta.engine : "Academic AI";
  document.getElementById("note-view-engine").innerText = engineName;

  // Overview
  document.getElementById("note-overview-text").innerText = cleanTimestamps(data.overview || "No overview available.");

  // Sections
  const secContainer = document.getElementById("note-sections-container");
  secContainer.innerHTML = "";

  (data.sections || []).forEach((sec, idx) => {
    const card = document.createElement("div");
    card.className = "section-card";

    let kpListHtml = "";
    (sec.key_points || []).forEach(kp => {
      const cleanKp = cleanTimestamps(kp);
      if (cleanKp) kpListHtml += `<li>${escapeHtml(cleanKp)}</li>`;
    });

    let defsHtml = "";
    (sec.definitions || []).forEach(d => {
      const cleanTerm = cleanTimestamps(d.term);
      const cleanMeaning = cleanTimestamps(d.meaning);
      if (cleanTerm) {
        defsHtml += `
          <div class="definition-box">
            <div class="def-term">Definition: ${escapeHtml(cleanTerm)}</div>
            <div class="def-meaning">${escapeHtml(cleanMeaning)}</div>
          </div>
        `;
      }
    });

    let examplesHtml = "";
    (sec.examples || []).forEach(ex => {
      const cleanEx = cleanTimestamps(ex);
      if (cleanEx) {
        examplesHtml += `
          <div class="example-box">
            <strong>Example:</strong> ${escapeHtml(cleanEx)}
          </div>
        `;
      }
    });

    const cleanHeading = cleanTimestamps(sec.heading || `Topic ${idx + 1}`);
    card.innerHTML = `
      <h3 class="section-heading">
        <span class="section-number">${idx + 1}.</span>
        <span class="sec-title-text">${escapeHtml(cleanHeading)}</span>
      </h3>
      ${kpListHtml ? `<ul class="key-points-list">${kpListHtml}</ul>` : ""}
      ${defsHtml}
      ${examplesHtml}
    `;

    secContainer.appendChild(card);
  });

  // Summary
  document.getElementById("note-summary-text").innerText = cleanTimestamps(data.summary || "No summary provided.");

  // Formulas
  const formulas = data.formulas || [];
  document.getElementById("count-formulas").innerText = formulas.length;
  const fContainer = document.getElementById("note-formulas-container");
  if (formulas.length === 0) {
    fContainer.innerHTML = `<p class="text-muted">No explicit formulas or mathematical laws detected in this lecture.</p>`;
  } else {
    fContainer.innerHTML = formulas.map(f => {
      if (typeof f === "object") {
        return `
          <div class="formula-card">
            <div class="formula-name">${escapeHtml(cleanTimestamps(f.name || "Formula"))}</div>
            <code class="formula-code">${escapeHtml(cleanTimestamps(f.formula || ""))}</code>
            <div class="formula-exp">${escapeHtml(cleanTimestamps(f.explanation || ""))}</div>
          </div>
        `;
      } else {
        return `
          <div class="formula-card">
            <code class="formula-code">${escapeHtml(cleanTimestamps(String(f)))}</code>
          </div>
        `;
      }
    }).join("");
  }

  // Glossary
  const glossary = data.glossary || [];
  document.getElementById("count-glossary").innerText = glossary.length;
  const gContainer = document.getElementById("note-glossary-container");
  if (glossary.length === 0) {
    gContainer.innerHTML = `<p class="text-muted">No glossary items generated.</p>`;
  } else {
    gContainer.innerHTML = glossary.map(g => {
      if (typeof g === "object") {
        return `
          <div class="glossary-card">
            <div class="glossary-term">${escapeHtml(cleanTimestamps(g.term || "Term"))}</div>
            <div class="glossary-meaning">${escapeHtml(cleanTimestamps(g.meaning || g.definition || ""))}</div>
          </div>
        `;
      } else {
        return `
          <div class="glossary-card">
            <div class="glossary-meaning">${escapeHtml(cleanTimestamps(String(g)))}</div>
          </div>
        `;
      }
    }).join("");
  }

  // Revision Questions (Active Recall Accordion)
  const revQuestions = data.revision_questions || [];
  document.getElementById("count-revision").innerText = revQuestions.length;
  const rContainer = document.getElementById("note-revision-container");
  if (revQuestions.length === 0) {
    rContainer.innerHTML = `<p class="text-muted">No revision questions available.</p>`;
  } else {
    rContainer.innerHTML = revQuestions.map((q, i) => {
      const cleanQ = cleanTimestamps(q.question);
      const cleanA = cleanTimestamps(q.answer);
      return `
      <div class="rev-card" id="rev-card-${i}">
        <div class="rev-question-header" onclick="toggleRevisionCard(${i})">
          <span class="rev-q-text"><strong>Q${i + 1}:</strong> ${escapeHtml(cleanQ)}</span>
          <svg class="rev-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </div>
        <div class="rev-answer-body">
          <strong>Model Answer:</strong>
          <p style="margin-top:0.35rem;">${escapeHtml(cleanA)}</p>
        </div>
      </div>
    `;
    }).join("");
  }

  // Interactive Quiz (MCQs)
  renderQuizSection(data.mcqs || []);

  // Transcript Cleaning Comparison
  renderTranscriptComparison(note);

  // Default to study guide section
  switchNotesSection("sec-content");
}

/* ==========================================================================
   7. Interactive Quiz Engine
   ========================================================================== */
function renderQuizSection(mcqs) {
  document.getElementById("count-mcqs").innerText = mcqs.length;
  const qContainer = document.getElementById("note-quiz-container");

  AppState.quizScore = { correct: 0, answered: 0, total: mcqs.length };
  updateQuizScoreBadge();

  if (mcqs.length === 0) {
    qContainer.innerHTML = `<p class="text-muted">No multiple-choice questions generated for this lecture.</p>`;
    return;
  }

  qContainer.innerHTML = mcqs.map((mcq, qIdx) => {
    const cleanQ = cleanTimestamps(mcq.question);
    const cleanAns = cleanTimestamps(mcq.correct_answer);
    const cleanExp = cleanTimestamps(mcq.explanation || '');

    const optsHtml = (mcq.options || []).map((opt, optIdx) => {
      const cleanOpt = cleanTimestamps(opt);
      return `
      <button class="quiz-opt-btn" onclick="handleQuizAnswer(${qIdx}, '${escapeHtml(cleanOpt)}', '${escapeHtml(cleanAns)}', '${escapeHtml(cleanExp)}')">
        ${escapeHtml(cleanOpt)}
      </button>
    `;
    }).join("");

    return `
      <div class="quiz-card" id="quiz-card-${qIdx}">
        <div class="quiz-q-title"><strong>Question ${qIdx + 1}:</strong> ${escapeHtml(cleanQ)}</div>
        <div class="quiz-options-grid">${optsHtml}</div>
        <div class="quiz-feedback-box" id="quiz-feedback-${qIdx}" style="display:none;"></div>
      </div>
    `;
  }).join("");
}

function handleQuizAnswer(qIdx, selectedOpt, correctOpt, explanation) {
  const card = document.getElementById(`quiz-card-${qIdx}`);
  if (!card) return;

  const buttons = card.querySelectorAll(".quiz-opt-btn");
  let alreadyAnswered = false;
  buttons.forEach(b => {
    if (b.disabled) alreadyAnswered = true;
  });
  if (alreadyAnswered) return;

  // Normalize for comparison
  const normSelected = selectedOpt.trim().toLowerCase();
  const normCorrect = correctOpt.trim().toLowerCase();
  const isMatch = normSelected === normCorrect ||
                  normCorrect.startsWith(normSelected.substring(0, 2)) ||
                  normSelected.startsWith(normCorrect.substring(0, 2));

  buttons.forEach(btn => {
    btn.disabled = true;
    const btnText = btn.innerText.trim().toLowerCase();
    if (btnText === normCorrect || btnText.startsWith(normCorrect.substring(0, 2))) {
      btn.classList.add("correct");
    } else if (btn.innerText.trim() === selectedOpt.trim()) {
      btn.classList.add(isMatch ? "correct" : "wrong");
    }
  });

  const feedback = document.getElementById(`quiz-feedback-${qIdx}`);
  feedback.style.display = "block";

  if (isMatch) {
    feedback.className = "quiz-feedback-box correct";
    feedback.innerHTML = `<strong>🎉 Correct!</strong> ${escapeHtml(explanation || "Great job understanding this concept.")}`;
    AppState.quizScore.correct++;
  } else {
    feedback.className = "quiz-feedback-box wrong";
    feedback.innerHTML = `<strong>❌ Not quite.</strong> The correct answer is <strong>${escapeHtml(correctOpt)}</strong>.<br/><span style="margin-top:4px; display:inline-block;">${escapeHtml(explanation || "")}</span>`;
  }

  AppState.quizScore.answered++;
  updateQuizScoreBadge();
}

function updateQuizScoreBadge() {
  const badge = document.getElementById("quiz-score-display");
  if (badge) {
    const { correct, total } = AppState.quizScore;
    const pct = total > 0 ? Math.round((correct / total) * 100) : 0;
    badge.innerText = `Score: ${correct} / ${total} (${pct}%)`;
  }
}

function scrollToQuiz() {
  switchNotesSection("sec-quiz");
  document.getElementById("sec-quiz").scrollIntoView({ behavior: "smooth" });
}

function toggleRevisionCard(index) {
  const card = document.getElementById(`rev-card-${index}`);
  if (card) {
    card.classList.toggle("open");
  }
}

/* ==========================================================================
   8. Transcript Cleaning Stats & Comparison
   ========================================================================== */
function renderTranscriptComparison(note) {
  const statsBox = document.getElementById("cleaning-stats-box");
  const stats = note.cleaning_stats || {};

  statsBox.innerHTML = `
    <h4 style="margin-bottom:0.5rem; font-weight:700;">Transcript Cleaning Insights</h4>
    <div style="display:flex; gap:1.5rem; flex-wrap:wrap; font-size:0.92rem;">
      <div><strong>Original Words:</strong> ${(stats.original_words || 0).toLocaleString()}</div>
      <div><strong>Cleaned Words:</strong> ${(stats.cleaned_words || 0).toLocaleString()}</div>
      <div><strong>Fillers & Stutters Removed:</strong> ${stats.fillers_removed || 0}</div>
      <div><strong>Word Reduction:</strong> <span style="color:#059669; font-weight:700;">${stats.reduction_percentage || 0}%</span></div>
    </div>
  `;

  document.getElementById("display-cleaned-transcript").innerText = note.cleaned_transcript || "Cleaned transcript not available.";
  document.getElementById("display-raw-transcript").innerText = note.raw_transcript || "Original input not available.";
}

/* ==========================================================================
   9. Inline Note Editing
   ========================================================================== */
function toggleEditMode() {
  AppState.isEditing = !AppState.isEditing;

  const btnText = document.getElementById("edit-btn-text");
  const overviewEl = document.getElementById("note-overview-text");
  const summaryEl = document.getElementById("note-summary-text");

  if (AppState.isEditing) {
    btnText.innerText = "Save Changes";
    overviewEl.contentEditable = "true";
    summaryEl.contentEditable = "true";
    overviewEl.classList.add("editable-active");
    summaryEl.classList.add("editable-active");
    showToast("Edit mode active. Click overview or summary to edit, then click 'Save Changes'.", "info");
  } else {
    btnText.innerText = "Edit Notes";
    overviewEl.contentEditable = "false";
    summaryEl.contentEditable = "false";
    overviewEl.classList.remove("editable-active");
    summaryEl.classList.remove("editable-active");

    // Persist edits to database
    saveNoteEdits();
  }
}

async function saveNoteEdits() {
  if (!AppState.currentNote || !AppState.currentNote.id) return;

  const noteId = AppState.currentNote.id;
  const newOverview = document.getElementById("note-overview-text").innerText.trim();
  const newSummary = document.getElementById("note-summary-text").innerText.trim();

  // Update in memory
  AppState.currentNote.structured_notes.overview = newOverview;
  AppState.currentNote.structured_notes.summary = newSummary;

  try {
    const res = await fetch(`/api/notes/${noteId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        structured_notes: AppState.currentNote.structured_notes
      })
    });

    if (res.ok) {
      showToast("Changes saved successfully to database!", "success");
    } else {
      throw new Error("Failed to save changes.");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ==========================================================================
   10. Multi-Format Downloads & Clipboard
   ========================================================================== */
function downloadCurrentNote(format) {
  if (!AppState.currentNote || !AppState.currentNote.id) {
    showToast("No active note to download.", "error");
    return;
  }

  const noteId = AppState.currentNote.id;
  const url = `/api/notes/${noteId}/export?format=${format}`;

  // Trigger browser download via hidden anchor
  const a = document.createElement("a");
  a.href = url;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  showToast(`Downloading study notes as ${format.toUpperCase()}...`, "success");
}

function copyNotesToClipboard() {
  if (!AppState.currentNote || !AppState.currentNote.structured_notes) {
    showToast("No notes content available to copy.", "error");
    return;
  }

  const data = AppState.currentNote.structured_notes;
  let text = `# ${data.title || "Lecture Notes"}\n\n`;
  text += `## Overview\n${data.overview}\n\n`;

  (data.sections || []).forEach((s, idx) => {
    text += `### ${idx + 1}. ${s.heading}\n`;
    (s.key_points || []).forEach(kp => text += `- ${kp}\n`);
    (s.definitions || []).forEach(d => text += `- Definition (${d.term}): ${d.meaning}\n`);
    (s.examples || []).forEach(ex => text += `- Example: ${ex}\n`);
    text += "\n";
  });

  text += `## Summary\n${data.summary}\n`;

  navigator.clipboard.writeText(text).then(() => {
    showToast("Notes copied to clipboard as Markdown!", "success");
  }).catch(() => {
    showToast("Failed to copy to clipboard.", "error");
  });
}

/* ==========================================================================
   11. Notes History & Search (SQLite CRUD)
   ========================================================================== */
async function loadNotesHistory() {
  const query = (document.getElementById("history-search-input") ? document.getElementById("history-search-input").value : "").trim();
  const subjectFilter = (document.getElementById("history-subject-filter") ? document.getElementById("history-subject-filter").value : "all");

  try {
    let url = `/api/notes?q=${encodeURIComponent(query)}`;
    if (subjectFilter && subjectFilter !== "all") {
      url += `&subject=${encodeURIComponent(subjectFilter)}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load notes library.");

    const data = await res.json();
    const notes = data.notes || [];

    // Update history badge count
    const badge = document.getElementById("history-count-badge");
    if (badge) badge.innerText = notes.length;

    const statsBadge = document.getElementById("library-stats-badge");
    if (statsBadge) statsBadge.innerHTML = `<span>${notes.length} Notes in Library</span>`;

    renderHistoryGrid(notes);
  } catch (err) {
    console.error("[Error] History fetch error:", err);
  }
}

function debounceHistorySearch() {
  clearTimeout(AppState.historySearchTimeout);
  AppState.historySearchTimeout = setTimeout(() => {
    loadNotesHistory();
  }, 300);
}

function renderHistoryGrid(notes) {
  const grid = document.getElementById("history-notes-grid");
  const emptyState = document.getElementById("history-empty-state");
  if (!grid) return;

  if (notes.length === 0) {
    grid.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }

  emptyState.style.display = "none";
  grid.innerHTML = notes.map(note => {
    const dateFormatted = new Date(note.created_at).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric"
    });

    return `
      <div class="history-card" id="history-card-${note.id}">
        <div class="history-card-top">
          <div class="history-card-tags">
            <span class="tag tag-subject">${escapeHtml(note.subject || "General")}</span>
            <span class="tag tag-detail">${escapeHtml(note.detail_level || "Medium")}</span>
          </div>
          <h3 class="history-card-title" onclick="openNoteFromHistory(${note.id})">
            ${escapeHtml(note.title)}
          </h3>
          <p class="history-card-excerpt">
            ${(note.word_count || 0).toLocaleString()} words • Saved on ${dateFormatted}
          </p>
        </div>
        <div class="history-card-bottom">
          <span>${dateFormatted}</span>
          <div class="history-card-actions">
            <button class="btn btn-secondary btn-sm" onclick="openNoteFromHistory(${note.id})" title="View Note">
              Open
            </button>
            <button class="btn btn-secondary btn-sm" onclick="downloadHistoryNote(${note.id}, 'pdf')" title="Download PDF">
              PDF
            </button>
            <button class="btn btn-text btn-sm" onclick="deleteNoteFromHistory(${note.id})" title="Delete" style="color:#e11d48;">
              Delete
            </button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

async function openNoteFromHistory(noteId) {
  try {
    const res = await fetch(`/api/notes/${noteId}`);
    if (!res.ok) throw new Error("Could not retrieve note details.");

    const note = await res.json();
    AppState.currentNote = note;

    renderCurrentNote();
    document.getElementById("nav-notes-btn").style.display = "inline-flex";
    navigateTo("notes-view");
    showToast(`Loaded: ${note.title}`, "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function downloadHistoryNote(noteId, format) {
  const url = `/api/notes/${noteId}/export?format=${format}`;
  const a = document.createElement("a");
  a.href = url;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showToast(`Downloading note #${noteId} as ${format.toUpperCase()}...`, "success");
}

async function deleteNoteFromHistory(noteId) {
  if (!confirm("Are you sure you want to delete this study note from your library?")) {
    return;
  }

  try {
    const res = await fetch(`/api/notes/${noteId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete note.");

    showToast("Note deleted from history.", "info");

    // If deleting the active note, hide current note view
    if (AppState.currentNote && AppState.currentNote.id === noteId) {
      AppState.currentNote = null;
      document.getElementById("nav-notes-btn").style.display = "none";
      navigateTo("history");
    }

    loadNotesHistory();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ==========================================================================
   12. Utilities & Toast Notifications
   ========================================================================== */
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  let icon = "ℹ️";
  if (type === "success") icon = "✅";
  if (type === "error") icon = "⚠️";

  toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function cleanTimestamps(text) {
  if (!text) return "";
  let str = String(text);
  let optPrefix = "";
  const optMatch = str.match(/^([A-Da-d][\)\.]|\d+[\)\.])\s*/);
  if (optMatch) {
    optPrefix = optMatch[0];
    str = str.substring(optPrefix.length);
  }
  str = str.replace(/\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*(?:-->|->|–|-)\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?/gi, " ");
  str = str.replace(/\b(?:at|on|in|around|timestamp|timecode)\s*\[\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\]/gi, " ");
  str = str.replace(/\b(?:at|on|in|around|timestamp|timecode)\s*\(\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\)/gi, " ");
  str = str.replace(/\[\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\]/gi, " ");
  str = str.replace(/\(\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\)/gi, " ");
  str = str.replace(/\<\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\>/gi, " ");
  str = str.replace(/\b\d{1,2}:\d{2}:\d{2}(?:[\.,]\d{1,3})?\b/gi, " ");
  str = str.replace(/\b(?:at|timestamp|timecode)\s+\[?\d{1,2}:\d{2}(?::\d{2})?\]?\b/gi, " ");
  str = str.replace(/^\s*(?:at\s+|timestamp\s*:?\s*)?\d{1,2}:\d{2}(?::\d{2})?\s*[-–:]?\s*/gi, " ");
  str = str.replace(/(?<=\s)\d{1,2}:\d{2}(?=\s|[-–:,\.]|$)/g, " ");
  str = str.replace(/^\s*(?:[A-Z][A-Za-z\.\s]{1,25}|Speaker\s*\d+|Prof(?:essor)?\.?\s*[A-Z][a-z]+|Instructor|Student\s*\d?)\s*:\s*/i, "");
  str = str.replace(/\b(?:at|on|in|around)\s*([,.:;?!])/gi, "$1");
  str = str.replace(/[ \t]+/g, " ");
  str = str.replace(/\s+([,.:;?!])/g, "$1");
  str = str.replace(/^\s*[,;:\-\.]\s*/, "");
  str = str.trim();
  if (str && str[0] === str[0].toLowerCase()) {
    str = str[0].toUpperCase() + str.slice(1);
  }
  return (optPrefix + str).trim();
}
