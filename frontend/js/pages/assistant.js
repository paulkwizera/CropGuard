import { api } from "../api.js";
import { requireAuth } from "../auth.js";
import { mountShell } from "../components/shell.js";
import { escapeHtml, renderAdvice } from "../components/format.js";
import { icon } from "../components/icons.js";
import { getLanguage, mountLanguage } from "../components/lang.js";
import { toast } from "../components/toast.js";
import { cropName, hasIssue } from "../components/checks.js";
import { getMe } from "../session.js";
import { adviceLang, t } from "../i18n.js";

if (requireAuth()) init();

const MAX_SAVED = 40;

async function init() {
  mountShell("assistant");
  const $ = (id) => document.getElementById(id);
  const log = $("chat-log"), input = $("chat-input"), form = $("chat-form"), sendBtn = $("chat-send");
  const langBox = $("chat-lang");
  mountLanguage(langBox, adviceLang(), "reply_lang");

  const me = await getMe().catch(() => ({}));
  const storeKey = `cropguard.chat.${me.username || "guest"}`;
  let messages = [];                // [{role: "user" | "assistant", content}]
  let context = { district: me.district || "" };
  let busy = false;

  try { messages = JSON.parse(localStorage.getItem(storeKey)) || []; } catch { messages = []; }
  const save = () => { try { localStorage.setItem(storeKey, JSON.stringify(messages.slice(-MAX_SAVED))); } catch { /* storage full or blocked */ } };

  // ---- suggestions (the last chip is built from the farmer's real last check, if it found a disease)
  const SUGGESTIONS = [
    "How can I get more maize from my field?",
    "Which seeds should I plant this season?",
    "How do I protect cassava from disease?",
    "How should I store my harvest so it does not spoil?",
  ];
  function drawChips(extra) {
    const list = extra ? [extra, ...SUGGESTIONS] : SUGGESTIONS;
    $("chips").innerHTML = list.map((q) => `<button type="button" class="chip" data-q="${escapeHtml(q)}">${escapeHtml(q)}</button>`).join("");
  }
  drawChips();
  api.listDetections(1).then(({ results }) => {
    const last = results.find(hasIssue);
    if (!last) return;
    context.crop = cropName(last).toLowerCase();
    context.last_check = `${last.top_label} on ${context.crop}`;
    drawChips(t("My last photo check found {disease}. What should I do?", { disease: t(last.top_label) }));
    if (!messages.length) { /* the welcome view is showing, so the new chip is visible */ }
  }).catch(() => {});
  $("chips").addEventListener("click", (e) => { const q = e.target.closest("[data-q]")?.dataset.q; if (q) ask(q); });

  // ---- drawing messages
  function bubble(role, content) {
    const el = document.createElement("div");
    el.className = `msg msg--${role}`;
    el.innerHTML = role === "assistant"
      ? `<span class="msg-avatar" aria-hidden="true">${icon("leaf", "icon--sm")}</span><div class="msg-body prose-ai">${renderAdvice(content)}</div>`
      : `<div class="msg-body">${escapeHtml(content).replace(/\n/g, "<br>")}</div>`;
    return el;
  }
  function render() {
    const has = messages.length > 0;
    $("chat-welcome").hidden = has;
    $("clear-chat").hidden = !has;
    [...log.querySelectorAll(".msg, .msg-error")].forEach((n) => n.remove());
    for (const m of messages) log.append(bubble(m.role, m.content));
    log.scrollTop = log.scrollHeight;
  }
  function typing() {
    const el = document.createElement("div");
    el.className = "msg msg--assistant msg--typing";
    el.setAttribute("aria-label", t("The assistant is writing…"));
    el.innerHTML = `<span class="msg-avatar" aria-hidden="true">${icon("leaf", "icon--sm")}</span><div class="msg-body"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span></div>`;
    log.append(el); log.scrollTop = log.scrollHeight;
    return el;
  }
  function showError(message, retry) {
    const el = document.createElement("div");
    el.className = "msg-error alert alert--error";
    el.setAttribute("role", "alert");
    el.innerHTML = `${icon("alert")}<div><p>${escapeHtml(message)}</p><button type="button" class="btn btn--sm btn--secondary" style="margin-top:.5rem">${icon("refresh", "icon--sm")}Try again</button></div>`;
    el.querySelector("button").addEventListener("click", () => { el.remove(); retry(); });
    log.append(el); log.scrollTop = log.scrollHeight;
  }

  // ---- asking
  async function send() {
    busy = true; sendBtn.disabled = true;
    const wait = typing();
    try {
      const { reply } = await api.assistantChat(messages, getLanguage(langBox), context);
      messages.push({ role: "assistant", content: reply });
      save();
      wait.remove();
      render();
    } catch (err) {
      wait.remove();
      const text = err.status === 429 ? t("You are asking very quickly. Please wait a moment and try again.") : err.message;
      showError(text, send);
    } finally {
      busy = false; sendBtn.disabled = false; input.focus();
    }
  }
  function ask(text) {
    text = text.trim();
    if (!text || busy) return;
    messages.push({ role: "user", content: text });
    save(); render();
    input.value = ""; grow();
    send();
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); ask(input.value); });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); ask(input.value); } });
  const grow = () => { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 144) + "px"; };
  input.addEventListener("input", grow);

  $("clear-chat").addEventListener("click", () => {
    if (busy) return;
    messages = []; localStorage.removeItem(storeKey); render(); input.focus();
    toast("Started a new conversation.");
  });

  render();
  // the last stored message may be a question that never got an answer (page closed mid-reply)
  if (messages.at(-1)?.role === "user") send();
}
