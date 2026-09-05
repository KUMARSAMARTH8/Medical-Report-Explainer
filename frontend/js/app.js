const configuredBase = window.APP_CONFIG && typeof window.APP_CONFIG.API_BASE === "string"
  ? window.APP_CONFIG.API_BASE.trim().replace(/\/$/, "")
  : "";
const API_BASE = configuredBase;
let MAX_UPLOAD_MB = 10;
let ALLOWED_EXTS = [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"];

const $ = id => document.getElementById(id);
const fileInput = $("file-input");
const dropzone = $("dropzone");
const uploadStatus = $("upload-status");
const resultsPanel = $("results-panel");
const chatPanel = $("chat-panel");
const dashboardEmpty = $("dashboard-empty");
const dashboardContent = $("dashboard-content");
let currentReportId = null;
let isUploading = false;
let reportsCache = [];

function api(path) { return `${API_BASE}${path}`; }

async function requestJSON(path, options = {}) {
  const response = await fetch(api(path), options);
  let data = {};
  try { data = await response.json(); } catch { data = {}; }
  if (!response.ok) {
    const err = new Error(data.detail || `Request failed (${response.status})`);
    err.status = response.status;
    throw err;
  }
  return data;
}

function setStatus(message, kind = "") {
  uploadStatus.textContent = message;
  uploadStatus.className = `status${kind ? ` ${kind}` : ""}`;
}

async function initialize() {
  await Promise.allSettled([checkHealth(), loadCapabilities(), refreshDashboard()]);
}

async function checkHealth() {
  const badge = $("api-badge");
  try {
    const health = await requestJSON("/api/health");
    badge.className = "api-badge online";
    badge.querySelector("span:last-child").textContent = `Server online · v${health.version}`;
  } catch {
    badge.className = "api-badge offline";
    badge.querySelector("span:last-child").textContent = "Server offline";
  }
}

async function loadCapabilities() {
  try {
    const data = await requestJSON("/api/capabilities");
    MAX_UPLOAD_MB = Number(data.max_upload_size_mb) || 10;
    ALLOWED_EXTS = data.allowed_extensions || ALLOWED_EXTS;
    const ocr = data.ocr || {};
    $("ocr-status").textContent = ocr.image_ocr
      ? `OCR ready · ${ocr.tesseract ? "Tesseract" : "EasyOCR"}`
      : "Text PDFs ready · image/scanned-PDF OCR not installed";
  } catch {
    $("ocr-status").textContent = "Could not read server capabilities.";
  }
}

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) uploadReport(fileInput.files[0]);
});
["dragover", "dragenter"].forEach(eventName => dropzone.addEventListener(eventName, event => {
  event.preventDefault();
  if (!isUploading) dropzone.classList.add("drag-active");
}));
["dragleave", "drop"].forEach(eventName => dropzone.addEventListener(eventName, event => {
  event.preventDefault();
  dropzone.classList.remove("drag-active");
}));
dropzone.addEventListener("drop", event => {
  if (!isUploading && event.dataTransfer.files[0]) uploadReport(event.dataTransfer.files[0]);
});
dropzone.addEventListener("keydown", event => {
  if ((event.key === "Enter" || event.key === " ") && !isUploading) fileInput.click();
});

function validateFile(file) {
  const dot = file.name.lastIndexOf(".");
  const ext = dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
  if (!ALLOWED_EXTS.includes(ext)) return `Unsupported file type '${ext || "unknown"}'.`;
  if (file.size === 0) return "This file is empty.";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `File is larger than ${MAX_UPLOAD_MB} MB.`;
  return null;
}

async function uploadReport(file) {
  const error = validateFile(file);
  if (error) return setStatus(error, "error");
  isUploading = true;
  dropzone.classList.add("is-busy");
  setStatus(`Reading ${file.name}…`, "loading");
  const formData = new FormData();
  formData.append("file", file);
  try {
    const data = await requestJSON("/api/upload", { method: "POST", body: formData });
    setStatus(`Processed ${data.parameters.length} supported parameters.`, "success");
    showAnalysis(data);
    await refreshDashboard();
  } catch (err) {
    setStatus(err.message || "Could not process this report.", "error");
  } finally {
    isUploading = false;
    dropzone.classList.remove("is-busy");
    fileInput.value = "";
  }
}

$("demo-btn").addEventListener("click", async () => {
  const btn = $("demo-btn");
  btn.disabled = true;
  setStatus("Loading the built-in sample report…", "loading");
  try {
    const data = await requestJSON("/api/demo", { method: "POST" });
    setStatus("Sample report loaded successfully.", "success");
    showAnalysis(data);
    await refreshDashboard();
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    btn.disabled = false;
  }
});

function td(text) {
  const cell = document.createElement("td");
  cell.textContent = String(text);
  return cell;
}

function showAnalysis(data) {
  currentReportId = data.report_id;
  resultsPanel.classList.remove("hidden");
  chatPanel.classList.remove("hidden");
  $("report-name").textContent = `Results — ${data.filename}`;
  $("report-overview").textContent = data.summary.overview;
  $("disclaimer-text").textContent = data.disclaimer;

  const tbody = $("lab-table-body");
  tbody.replaceChildren();
  data.parameters.forEach(param => {
    const row = document.createElement("tr");
    row.appendChild(td(param.name));
    row.appendChild(td(`${param.value} ${param.unit}`));
    row.appendChild(td(param.normal_range));
    const statusCell = document.createElement("td");
    const pill = document.createElement("span");
    pill.className = `pill ${String(param.status).toLowerCase()}`;
    pill.textContent = param.status;
    statusCell.appendChild(pill);
    row.appendChild(statusCell);
    tbody.appendChild(row);
  });

  const explanations = $("explanations");
  explanations.replaceChildren();
  data.summary.explanations.forEach(item => {
    const div = document.createElement("div");
    div.className = `explain-item ${String(item.status).toLowerCase()}`;
    const strong = document.createElement("b");
    strong.textContent = item.name;
    div.append(strong, document.createTextNode(` — ${item.explanation}`));
    explanations.appendChild(div);
  });

  const risksBlock = $("risks-block");
  const risksList = $("risks-list");
  risksList.replaceChildren();
  if (!data.risks || data.risks.length === 0) {
    risksBlock.classList.add("hidden");
  } else {
    risksBlock.classList.remove("hidden");
    data.risks.forEach(risk => {
      const card = document.createElement("div");
      card.className = "risk-card";
      const title = document.createElement("h4");
      title.textContent = `${risk.parameter} — ${risk.status}`;
      const note = document.createElement("p");
      note.textContent = risk.risk;
      const list = document.createElement("ul");
      (risk.suggestions || []).forEach(text => {
        const li = document.createElement("li");
        li.textContent = text;
        list.appendChild(li);
      });
      card.append(title, note, list);
      risksList.appendChild(card);
    });
  }

  const score = Math.max(0, Math.min(100, Number(data.health_score) || 0));
  const circumference = 326.7;
  const fill = $("dial-fill");
  fill.style.strokeDashoffset = String(circumference - (score / 100) * circumference);
  fill.style.stroke = score >= 70 ? "#2f6f5e" : score >= 40 ? "#a94f22" : "#9f3f35";
  $("score-value").textContent = String(score);

  $("chat-log").replaceChildren();
  appendChatMessage("Report loaded. Ask me about one of the detected parameters.", "bot");
  resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

const chatForm = $("chat-form");
const chatInput = $("chat-input");
const chatLog = $("chat-log");
chatForm.addEventListener("submit", event => {
  event.preventDefault();
  sendQuestion(chatInput.value);
});
$("quick-prompts").addEventListener("click", event => {
  const button = event.target.closest("button[data-question]");
  if (button) sendQuestion(button.dataset.question);
});

async function sendQuestion(rawQuestion) {
  const question = String(rawQuestion || "").trim();
  if (!question || !currentReportId) return;
  appendChatMessage(question, "user");
  chatInput.value = "";
  chatInput.disabled = true;
  chatForm.querySelector("button").disabled = true;
  try {
    const data = await requestJSON("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, report_id: currentReportId }),
    });
    appendChatMessage(data.answer, "bot");
  } catch (err) {
    appendChatMessage(err.message || "Could not answer right now.", "bot");
  } finally {
    chatInput.disabled = false;
    chatForm.querySelector("button").disabled = false;
    chatInput.focus();
  }
}

function appendChatMessage(text, who) {
  const div = document.createElement("div");
  div.className = `chat-msg ${who}`;
  div.textContent = String(text);
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function refreshDashboard() {
  try {
    reportsCache = await requestJSON("/api/reports?limit=100");
    if (!reportsCache.length) {
      dashboardEmpty.classList.remove("hidden");
      dashboardContent.classList.add("hidden");
      return;
    }
    dashboardEmpty.classList.add("hidden");
    dashboardContent.classList.remove("hidden");
    $("report-count").textContent = `${reportsCache.length} saved report${reportsCache.length === 1 ? "" : "s"}`;
    renderTrend(reportsCache);
    renderHistory(reportsCache);
  } catch {
    dashboardEmpty.textContent = "Could not load report history. Check that the backend is running.";
  }
}

function renderHistory(reports) {
  const wrap = $("report-history");
  wrap.replaceChildren();
  [...reports].reverse().forEach(report => {
    const row = document.createElement("div");
    row.className = "history-row";
    const main = document.createElement("div"); main.className = "history-main";
    const name = document.createElement("div"); name.className = "history-name"; name.textContent = report.filename;
    const meta = document.createElement("div"); meta.className = "history-meta";
    meta.textContent = `${new Date(report.uploaded_at).toLocaleString()} · ${report.parameters.length} parameters`;
    main.append(name, meta);
    const score = document.createElement("div"); score.className = "history-score"; score.textContent = `${report.health_score}% in range`;
    const actions = document.createElement("div"); actions.className = "history-actions";
    const openBtn = document.createElement("button"); openBtn.type = "button"; openBtn.textContent = "Open";
    openBtn.addEventListener("click", () => openSavedReport(report.id));
    const deleteBtn = document.createElement("button"); deleteBtn.type = "button"; deleteBtn.textContent = "Delete"; deleteBtn.className = "delete-btn";
    deleteBtn.addEventListener("click", () => removeSavedReport(report.id));
    actions.append(openBtn, deleteBtn);
    row.append(main, score, actions);
    wrap.appendChild(row);
  });
}

async function openSavedReport(id) {
  try {
    const data = await requestJSON(`/api/report/${id}`);
    showAnalysis(data);
  } catch (err) { setStatus(err.message, "error"); }
}

async function removeSavedReport(id) {
  if (!window.confirm("Delete this saved analysis from local history?")) return;
  try {
    await requestJSON(`/api/report/${id}`, { method: "DELETE" });
    if (currentReportId === id) {
      currentReportId = null;
      resultsPanel.classList.add("hidden");
      chatPanel.classList.add("hidden");
    }
    await refreshDashboard();
  } catch (err) { setStatus(err.message, "error"); }
}

$("clear-history-btn").addEventListener("click", async () => {
  if (!reportsCache.length || !window.confirm("Clear all locally saved report analyses?")) return;
  try {
    await requestJSON("/api/reports", { method: "DELETE" });
    currentReportId = null;
    resultsPanel.classList.add("hidden");
    chatPanel.classList.add("hidden");
    await refreshDashboard();
    setStatus("Local report history cleared.", "success");
  } catch (err) { setStatus(err.message, "error"); }
});

function renderTrend(reports) {
  const canvas = $("trend-chart");
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(300, canvas.clientWidth || 800);
  const height = 170;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);
  const pad = { left: 35, right: 12, top: 12, bottom: 24 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  ctx.font = "11px Inter, sans-serif";
  ctx.fillStyle = "#647069";
  ctx.strokeStyle = "#ded9cd";
  ctx.lineWidth = 1;
  [0, 50, 100].forEach(value => {
    const y = pad.top + plotH - (value / 100) * plotH;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(width - pad.right, y); ctx.stroke();
    ctx.fillText(String(value), 5, y + 4);
  });
  const points = reports.map((report, index) => ({
    x: reports.length === 1 ? pad.left + plotW / 2 : pad.left + (index / (reports.length - 1)) * plotW,
    y: pad.top + plotH - (Number(report.health_score) / 100) * plotH,
  }));
  if (!points.length) return;
  ctx.strokeStyle = "#2f6f5e"; ctx.lineWidth = 2.5; ctx.beginPath();
  points.forEach((point, index) => index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
  ctx.stroke();
  ctx.fillStyle = "#2f6f5e";
  points.forEach(point => { ctx.beginPath(); ctx.arc(point.x, point.y, 3.5, 0, Math.PI * 2); ctx.fill(); });
  ctx.fillStyle = "#647069";
  ctx.fillText("oldest", pad.left, height - 5);
  const recent = "latest"; ctx.fillText(recent, width - pad.right - ctx.measureText(recent).width, height - 5);
}

window.addEventListener("resize", () => { if (reportsCache.length) renderTrend(reportsCache); });
initialize();
