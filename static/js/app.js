/* ============================================================
   Trek Planner Agent — Frontend Logic
   Handles: Chat, Recommendations, Itinerary, Checklist, Fitness
   ============================================================ */

"use strict";

// ── marked.js config ──────────────────────────────────────────────────────────
marked.setOptions({
  breaks: true,
  gfm: true,
});

// ── State ──────────────────────────────────────────────────────────────────────
let chatHistory = [];

// ══════════════════════════════════════════════════════════════════════════════
//  THEME TOGGLE
// ══════════════════════════════════════════════════════════════════════════════
(function initTheme() {
  const saved = localStorage.getItem("tpa-theme") || "dark";
  applyTheme(saved);
})();

function applyTheme(theme) {
  document.documentElement.setAttribute("data-bs-theme", theme);
  const icon = document.getElementById("themeIcon");
  if (icon) {
    icon.className = theme === "dark" ? "bi bi-sun-fill" : "bi bi-moon-fill";
  }
  localStorage.setItem("tpa-theme", theme);
}

document.getElementById("themeToggle")?.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-bs-theme");
  applyTheme(current === "dark" ? "light" : "dark");
});

// ══════════════════════════════════════════════════════════════════════════════
//  UTILITIES
// ══════════════════════════════════════════════════════════════════════════════
function showLoading(text = "Generating…") {
  const overlay = document.getElementById("loadingOverlay");
  const label   = document.getElementById("loadingText");
  if (overlay) { overlay.classList.remove("d-none"); }
  if (label)   { label.textContent = text; }
}

function hideLoading() {
  document.getElementById("loadingOverlay")?.classList.add("d-none");
}

function showToast(message, variant = "info") {
  const toastEl   = document.getElementById("tpaToast");
  const toastBody = document.getElementById("toastBody");
  if (!toastEl || !toastBody) return;

  toastBody.textContent = message;
  toastEl.className = `toast tpa-toast align-items-center border-${variant}`;
  const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
  toast.show();
}

function renderMarkdown(md) {
  return marked.parse(md || "");
}

function setResultContent(containerId, markdownText) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = renderMarkdown(markdownText);
  // Smooth scroll to result
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function apiPost(endpoint, body) {
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

function formToObject(form) {
  const data = {};
  new FormData(form).forEach((v, k) => {
    const n = parseFloat(v);
    data[k] = isNaN(n) || v.includes(" ") ? v : n;
  });
  return data;
}

// ══════════════════════════════════════════════════════════════════════════════
//  CHAT
// ══════════════════════════════════════════════════════════════════════════════
const chatMessages = document.getElementById("chatMessages");
const chatInput    = document.getElementById("chatInput");

function appendMessage(role, content) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `tpa-msg tpa-msg-${role}`;

  const avatarDiv = document.createElement("div");
  avatarDiv.className = "tpa-msg-avatar";
  avatarDiv.innerHTML = role === "bot"
    ? '<i class="bi bi-mountain-fill"></i>'
    : '<i class="bi bi-person-fill"></i>';

  const bubbleDiv = document.createElement("div");
  bubbleDiv.className = "tpa-msg-bubble";

  if (role === "bot") {
    bubbleDiv.innerHTML = renderMarkdown(content);
  } else {
    bubbleDiv.textContent = content;
  }

  msgDiv.appendChild(avatarDiv);
  msgDiv.appendChild(bubbleDiv);
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return msgDiv;
}

function appendTypingIndicator() {
  const msgDiv = document.createElement("div");
  msgDiv.className = "tpa-msg tpa-msg-bot tpa-typing";
  msgDiv.id = "typingIndicator";
  msgDiv.innerHTML = `
    <div class="tpa-msg-avatar"><i class="bi bi-mountain-fill"></i></div>
    <div class="tpa-msg-bubble">
      <div class="tpa-dots">
        <span></span><span></span><span></span>
      </div>
    </div>`;
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
  document.getElementById("typingIndicator")?.remove();
}

async function sendMessage() {
  const text = (chatInput?.value || "").trim();
  if (!text) return;

  chatInput.value = "";
  document.getElementById("sendBtn").disabled = true;

  appendMessage("user", text);
  chatHistory.push({ role: "user", content: text });

  appendTypingIndicator();

  try {
    const data = await apiPost("/api/chat", { message: text, history: chatHistory });
    removeTypingIndicator();
    const reply = data.response || "Sorry, I couldn't generate a response.";
    appendMessage("bot", reply);
    chatHistory.push({ role: "assistant", content: reply });

    // Keep history manageable (last 10 turns)
    if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);

  } catch (err) {
    removeTypingIndicator();
    appendMessage("bot", `⚠️ Error: ${err.message}`);
    showToast("Chat request failed — check server logs.", "danger");
  } finally {
    document.getElementById("sendBtn").disabled = false;
    chatInput.focus();
  }
}

function sendQuick(prompt) {
  if (!chatInput) return;
  chatInput.value = prompt;
  sendMessage();
  // Hide chip row after first use to keep UI tidy
  document.getElementById("quickChips")?.style && (
    document.getElementById("quickChips").style.display = "none"
  );
}

// Enter key in chat input
chatInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Clear chat
document.getElementById("clearChat")?.addEventListener("click", () => {
  chatHistory = [];
  chatMessages.innerHTML = "";
  appendMessage("bot", "Chat cleared. How can I help you plan your next trek? 🏔️");
  document.getElementById("quickChips") && (
    document.getElementById("quickChips").style.display = "flex"
  );
});

// ══════════════════════════════════════════════════════════════════════════════
//  TREK RECOMMENDATIONS
// ══════════════════════════════════════════════════════════════════════════════
document.getElementById("recommendForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = formToObject(e.target);

  const resultEl = document.getElementById("recommendResult");
  resultEl.innerHTML = `<div class="tpa-result-placeholder"><div class="tpa-spinner-mountain" style="font-size:2rem"><i class="bi bi-mountain-fill text-accent"></i></div><p class="text-muted mt-2">Generating recommendations…</p></div>`;

  showLoading("Finding your perfect treks…");
  try {
    const data = await apiPost("/api/recommend", body);
    setResultContent("recommendResult", data.response);
    showToast("Recommendations ready!", "success");
  } catch (err) {
    resultEl.innerHTML = `<div class="alert alert-danger m-0">Error: ${err.message}</div>`;
    showToast("Failed to get recommendations.", "danger");
  } finally {
    hideLoading();
  }
});

// ══════════════════════════════════════════════════════════════════════════════
//  ITINERARY GENERATOR
// ══════════════════════════════════════════════════════════════════════════════
document.getElementById("itineraryForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = formToObject(e.target);

  const resultEl = document.getElementById("itineraryResult");
  resultEl.innerHTML = `<div class="tpa-result-placeholder"><div class="tpa-spinner-mountain" style="font-size:2rem"><i class="bi bi-mountain-fill text-accent"></i></div><p class="text-muted mt-2">Building your itinerary…</p></div>`;

  showLoading("Creating day-wise itinerary…");
  try {
    const data = await apiPost("/api/itinerary", body);
    setResultContent("itineraryResult", data.response);
    showToast("Itinerary generated!", "success");
  } catch (err) {
    resultEl.innerHTML = `<div class="alert alert-danger m-0">Error: ${err.message}</div>`;
    showToast("Failed to generate itinerary.", "danger");
  } finally {
    hideLoading();
  }
});

// ══════════════════════════════════════════════════════════════════════════════
//  PACKING CHECKLIST
// ══════════════════════════════════════════════════════════════════════════════
document.getElementById("checklistForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = formToObject(e.target);

  const resultEl = document.getElementById("checklistResult");
  resultEl.innerHTML = `<div class="tpa-result-placeholder"><div class="tpa-spinner-mountain" style="font-size:2rem"><i class="bi bi-mountain-fill text-accent"></i></div><p class="text-muted mt-2">Preparing your checklist…</p></div>`;

  showLoading("Generating smart packing list…");
  try {
    const data = await apiPost("/api/checklist", body);
    setResultContent("checklistResult", data.response);
    showToast("Packing checklist ready!", "success");
  } catch (err) {
    resultEl.innerHTML = `<div class="alert alert-danger m-0">Error: ${err.message}</div>`;
    showToast("Failed to generate checklist.", "danger");
  } finally {
    hideLoading();
  }
});

// ══════════════════════════════════════════════════════════════════════════════
//  FITNESS ASSESSMENT
// ══════════════════════════════════════════════════════════════════════════════
document.getElementById("fitnessForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = formToObject(e.target);

  const resultEl = document.getElementById("fitnessResult");
  resultEl.innerHTML = `<div class="tpa-result-placeholder"><div class="tpa-spinner-mountain" style="font-size:2rem"><i class="bi bi-mountain-fill text-accent"></i></div><p class="text-muted mt-2">Analysing your fitness profile…</p></div>`;

  showLoading("Assessing your readiness…");
  try {
    const data = await apiPost("/api/fitness", body);
    setResultContent("fitnessResult", data.response);
    showToast("Fitness assessment complete!", "success");
  } catch (err) {
    resultEl.innerHTML = `<div class="alert alert-danger m-0">Error: ${err.message}</div>`;
    showToast("Failed to run fitness assessment.", "danger");
  } finally {
    hideLoading();
  }
});

// ══════════════════════════════════════════════════════════════════════════════
//  SCROLL-TRIGGERED ANIMATIONS (Intersection Observer)
// ══════════════════════════════════════════════════════════════════════════════
const animateObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.style.animationPlayState = "running";
        animateObserver.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12 }
);

document.querySelectorAll(".animate-slide-up").forEach((el) => {
  el.style.animationPlayState = "paused";
  animateObserver.observe(el);
});

// ══════════════════════════════════════════════════════════════════════════════
//  SMOOTH SCROLL FOR NAV LINKS
// ══════════════════════════════════════════════════════════════════════════════
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", (e) => {
    const target = document.querySelector(anchor.getAttribute("href"));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      // Close mobile nav if open
      const navCollapse = document.getElementById("navMenu");
      if (navCollapse?.classList.contains("show")) {
        new bootstrap.Collapse(navCollapse).hide();
      }
    }
  });
});

// ══════════════════════════════════════════════════════════════════════════════
//  HEALTH CHECK on page load (checks API availability)
// ══════════════════════════════════════════════════════════════════════════════
(async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (!data.model_available) {
      showToast(
        "Running in demo mode — add IBM credentials to .env for live AI.",
        "warning"
      );
    }
  } catch {
    // silently ignore — server not up yet in some dev setups
  }
})();
