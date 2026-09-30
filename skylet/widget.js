(() => {
  const sessionKey = "maccaSkyletSessionV1";
  const copy = {
    en: {
      subtitle: "Powered by PkLavc · GTA & Rockstar",
      intro: "Hi, I’m Skylet, powered by PkLavc. Ask me about GTA and Rockstar coverage on Macca Blog, or Patrick Araujo’s public PkLavc projects and technology writing.",
      placeholder: "Ask about GTA, Rockstar, or PkLavc…", send: "Send message", clear: "Clear conversation", close: "Close chat",
      confirmClear: "Clear this conversation from this browser?", thinking: "Thinking…", error: "I couldn’t answer right now. Please try again.", launcher: "Open or close Skylet chat", status: "GTA · Rockstar · PkLavc"
    },
    pt: {
      subtitle: "Powered by PkLavc · GTA e Rockstar",
      intro: "Oi, eu sou a Skylet, powered by PkLavc. Pergunte sobre as notícias de GTA e Rockstar no blog do Macca ou sobre os projetos públicos e textos técnicos de Patrick Araujo no PkLavc.",
      placeholder: "Pergunte sobre GTA, Rockstar ou PkLavc…", send: "Enviar mensagem", clear: "Limpar conversa", close: "Fechar chat",
      confirmClear: "Limpar esta conversa deste navegador?", thinking: "Pensando…", error: "Não consegui responder agora. Tente novamente.", launcher: "Abrir ou fechar o chat da Skylet", status: "GTA · Rockstar · PkLavc"
    },
    es: {
      subtitle: "Powered by PkLavc · GTA y Rockstar",
      intro: "Hola, soy Skylet, powered by PkLavc. Pregúntame sobre GTA y Rockstar en Macca Blog, o sobre los proyectos públicos y textos técnicos de Patrick Araujo en PkLavc.",
      placeholder: "Pregunta sobre GTA, Rockstar o PkLavc…", send: "Enviar mensaje", clear: "Borrar conversación", close: "Cerrar chat",
      confirmClear: "¿Borrar esta conversación de este navegador?", thinking: "Pensando…", error: "No pude responder ahora. Inténtalo de nuevo.", launcher: "Abrir o cerrar el chat de Skylet", status: "GTA · Rockstar · PkLavc"
    }
  };

  const locale = /^pt/i.test(navigator.language || "") ? "pt" : (/^es/i.test(navigator.language || "") ? "es" : "en");
  const text = copy[locale];
  const state = { apiBase: "", messages: [], open: false, busy: false, introduced: false };
  const root = document.documentElement;
  let launcher, panel, log, status, form, input, sendButton, closeButton, clearButton;

  function loadState() {
    try {
      const value = JSON.parse(localStorage.getItem(sessionKey) || "{}");
      state.messages = Array.isArray(value.messages) ? value.messages.slice(-8).filter(item => item && ["user", "assistant"].includes(item.role) && typeof item.content === "string") : [];
    } catch { state.messages = []; }
  }

  function saveState() {
    try { localStorage.setItem(sessionKey, JSON.stringify({ messages: state.messages.slice(-8) })); } catch { /* Chat remains available for this page view. */ }
  }

  function linkify(node, value) {
    const pattern = /https:\/\/[^\s<>]+/g;
    let cursor = 0;
    const message = String(value || "");
    for (const match of message.matchAll(pattern)) {
      const start = match.index;
      if (start > cursor) node.append(document.createTextNode(message.slice(cursor, start)));
      const raw = match[0];
      const url = raw.replace(/[),.;!?]+$/g, "");
      const suffix = raw.slice(url.length);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
      anchor.className = "skylet-inline-link";
      anchor.textContent = url;
      node.append(anchor, document.createTextNode(suffix));
      cursor = start + raw.length;
    }
    if (cursor < message.length) node.append(document.createTextNode(message.slice(cursor)));
  }

  function appendMessage(role, message, pending = false) {
    const article = document.createElement("article");
    article.className = `about-chat-message ${role}${pending ? " is-pending" : ""}`;
    linkify(article, message);
    log.append(article);
    log.scrollTop = log.scrollHeight;
    return article;
  }

  function renderHistory() {
    log.replaceChildren();
    if (state.messages.length) state.messages.forEach(item => appendMessage(item.role, item.content));
    else appendMessage("assistant", text.intro);
  }

  function setOpen(open) {
    state.open = open;
    panel.classList.toggle("is-open", open);
    panel.setAttribute("aria-hidden", String(!open));
    panel.inert = !open;
    launcher.setAttribute("aria-expanded", String(open));
    if (open) { renderHistory(); input.focus(); }
    else launcher.focus();
  }

  function makeMarkup() {
    launcher = document.createElement("button");
    launcher.id = "about-chat-launcher";
    launcher.type = "button";
    launcher.className = "about-chat-launcher";
    launcher.setAttribute("aria-controls", "about-chat-widget");
    launcher.setAttribute("aria-expanded", "false");
    launcher.setAttribute("aria-label", text.launcher);
    launcher.innerHTML = '<img src="/skylet/skylet-icon.webp" alt="Skylet" width="108" height="108" loading="lazy" decoding="async">';

    panel = document.createElement("section");
    panel.id = "about-chat-widget";
    panel.className = "about-chat-widget";
    panel.setAttribute("aria-label", "Skylet chat widget");
    panel.setAttribute("aria-hidden", "true");
    panel.inert = true;
    panel.innerHTML = [
      '<header class="about-chat-header">',
      '  <div class="about-chat-title"><strong>Skylet</strong><span></span></div>',
      '  <div class="about-chat-actions">',
      `    <button class="about-chat-action-btn about-chat-clear-btn" type="button" aria-label="${text.clear}" title="${text.clear}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7m4 4v5m4-5v5"></path></svg></button>`,
      `    <button class="about-chat-action-btn about-chat-close-btn" type="button" aria-label="${text.close}" title="${text.close}"><span class="about-chat-close-icon" aria-hidden="true"></span></button>`,
      '  </div>',
      '</header>',
      '<div class="about-chat-log" aria-live="polite"></div>',
      `<div class="about-chat-status">${text.status}</div>`,
      '<form class="about-chat-form">',
      `  <div class="about-chat-input-wrap"><textarea class="about-chat-input" rows="1" maxlength="1200" aria-label="${text.placeholder}" placeholder="${text.placeholder}"></textarea></div>`,
      `  <button class="about-chat-send" type="submit" aria-label="${text.send}" title="${text.send}"><svg class="about-chat-send-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h8"></path><path d="m12 5 7 7-7 7"></path></svg></button>`,
      '</form>'
    ].join("");
    document.body.append(launcher, panel);
    log = panel.querySelector(".about-chat-log");
    status = panel.querySelector(".about-chat-status");
    form = panel.querySelector(".about-chat-form");
    input = panel.querySelector(".about-chat-input");
    sendButton = panel.querySelector(".about-chat-send");
    closeButton = panel.querySelector(".about-chat-close-btn");
    clearButton = panel.querySelector(".about-chat-clear-btn");
    panel.querySelector(".about-chat-title span").textContent = text.subtitle;
  }

  function resizeInput() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 132)}px`;
  }

  async function sendMessage(event) {
    event.preventDefault();
    const message = input.value.trim();
    if (!message || state.busy) return;
    input.value = "";
    resizeInput();
    appendMessage("user", message);
    const pending = appendMessage("assistant", text.thinking, true);
    state.busy = true;
    sendButton.disabled = true;
    clearButton.disabled = true;
    status.textContent = "";
    try {
      if (!state.apiBase) throw new Error("Skylet service is not configured yet.");
      const response = await fetch(`${state.apiBase}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history: state.messages.slice(-8), locale, pagePath: location.pathname, pageTitle: document.title }),
        signal: AbortSignal.timeout(30000)
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.reply) throw new Error(data.error || "Chat request failed.");
      pending.remove();
      appendMessage("assistant", data.reply);
      state.messages.push({ role: "user", content: message }, { role: "assistant", content: data.reply });
      state.messages = state.messages.slice(-8);
      saveState();
    } catch (error) {
      pending.textContent = text.error;
      status.textContent = "";
      console.warn("Skylet chat request failed", error instanceof Error ? error.message : "unknown");
    } finally {
      state.busy = false;
      sendButton.disabled = false;
      clearButton.disabled = false;
      input.focus();
    }
  }

  function bindEvents() {
    launcher.addEventListener("click", () => setOpen(!state.open));
    closeButton.addEventListener("click", () => setOpen(false));
    clearButton.addEventListener("click", () => {
      if (!window.confirm(text.confirmClear)) return;
      state.messages = [];
      saveState();
      renderHistory();
    });
    form.addEventListener("submit", sendMessage);
    input.addEventListener("input", resizeInput);
    input.addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); }
    });
  }

  async function start() {
    loadState();
    makeMarkup();
    bindEvents();
    try {
      const response = await fetch("/skylet/config.json", { cache: "no-store" });
      const config = response.ok ? await response.json() : {};
      state.apiBase = typeof config.apiBase === "string" ? config.apiBase.replace(/\/$/, "") : "";
    } catch { state.apiBase = ""; }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
