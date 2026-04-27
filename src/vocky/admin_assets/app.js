const TOKEN_STORAGE_KEY = "vocky.adminToken";
const ADMIN_API_PREFIX = "/admin/api/";
const DOCS_ASSET_PATH = "/admin/assets/docs.json";

const state = {
  token: sessionStorage.getItem(TOKEN_STORAGE_KEY) || "",
  activeView: "dashboard",
  docs: {
    activeTopicId: "",
    loaded: false,
    loading: false,
    topics: [],
  },
};

const shell = document.querySelector("[data-admin-shell]");
const tokenForm = document.querySelector("[data-token-form]");
const tokenInput = document.querySelector("[data-token-input]");
const tokenStatus = document.querySelector("[data-token-status]");
const authSummary = document.querySelector("[data-auth-summary]");
const healthPill = document.querySelector(".health-pill");
const healthLabel = document.querySelector("[data-health-label]");
const healthValue = document.querySelector("[data-health-value]");
const lastCheck = document.querySelector("[data-last-check]");
const eventList = document.querySelector("[data-event-list]");
const docsNav = document.querySelector("[data-docs-nav]");
const docsArticle = document.querySelector("[data-docs-article]");
const docsMeta = document.querySelector("[data-docs-meta]");

function isAdminApiUrl(url) {
  return (
    url.origin === window.location.origin &&
    (url.pathname === "/admin/api" || url.pathname.startsWith(ADMIN_API_PREFIX))
  );
}

function adminFetch(path, options = {}) {
  const url = new URL(path, window.location.origin);
  const headers = new Headers(options.headers || {});

  if (isAdminApiUrl(url) && state.token) {
    headers.set("Authorization", `Bearer ${state.token}`);
  }

  return fetch(url, {
    ...options,
    headers,
  });
}

function setText(element, text) {
  if (element) {
    element.textContent = text;
  }
}

function renderTokenState() {
  const label = state.token ? "Session token saved" : "Session token empty";
  setText(tokenStatus, label);
  setText(authSummary, state.token ? "Token saved" : "No token");

  if (tokenInput && state.token) {
    tokenInput.value = state.token;
  }
}

function pushEvent(message) {
  if (!eventList) {
    return;
  }

  eventList.replaceChildren();
  const item = document.createElement("li");
  item.textContent = message;
  eventList.append(item);
}

function setHealthState(stateName, label) {
  if (healthPill) {
    healthPill.dataset.healthState = stateName;
  }
  setText(healthLabel, label);
  setText(healthValue, label.replace("Admin API ", ""));
  setText(lastCheck, new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
  pushEvent(label);
}

async function checkAdminHealth() {
  setHealthState("checking", "Admin API checking");

  try {
    const response = await adminFetch("/admin/api/healthz", {
      headers: { Accept: "application/json" },
    });

    if (response.status === 401) {
      setHealthState("error", "Admin API unauthorized");
      return;
    }

    if (!response.ok) {
      setHealthState("error", `Admin API ${response.status}`);
      return;
    }

    const payload = await response.json();
    setHealthState(
      payload.status === "ok" ? "healthy" : "error",
      payload.status === "ok" ? "Admin API healthy" : "Admin API unavailable",
    );
  } catch {
    setHealthState("error", "Admin API unreachable");
  }
}

function normalizeText(value) {
  return typeof value === "string" ? value : "";
}

function getDocsTopics(payload) {
  if (!payload || !Array.isArray(payload.sections)) {
    return [];
  }

  const topics = [];

  payload.sections.forEach((section) => {
    if (!section || !Array.isArray(section.topics)) {
      return;
    }

    const sectionId = normalizeText(section.id);
    const sectionTitle = normalizeText(section.title);

    section.topics.forEach((topic) => {
      if (!topic || !normalizeText(topic.id) || !normalizeText(topic.title)) {
        return;
      }

      topics.push({
        ...topic,
        sectionId,
        sectionTitle,
      });
    });
  });

  return topics;
}

function renderDocsState(label) {
  if (docsNav) {
    docsNav.replaceChildren();
  }

  if (!docsArticle) {
    return;
  }

  const stateMessage = document.createElement("p");
  stateMessage.className = "docs-state";
  stateMessage.dataset.docsState = "";
  stateMessage.textContent = label;
  docsArticle.replaceChildren(stateMessage);
}

function appendTextElement(parent, tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) {
    element.className = className;
  }
  element.textContent = normalizeText(text);
  parent.append(element);
  return element;
}

function appendStructuredList(parent, block, ordered) {
  const list = document.createElement(ordered ? "ol" : "ul");
  list.className = ordered ? "docs-steps" : "docs-list";

  (Array.isArray(block.items) ? block.items : []).forEach((item) => {
    const listItem = document.createElement("li");

    if (typeof item === "string") {
      listItem.textContent = item;
    } else if (item && typeof item === "object") {
      if (normalizeText(item.title)) {
        appendTextElement(listItem, "strong", "", item.title);
      }
      if (normalizeText(item.text)) {
        appendTextElement(listItem, "span", "", item.text);
      }
    }

    if (listItem.textContent) {
      list.append(listItem);
    }
  });

  if (list.children.length) {
    parent.append(list);
  }
}

function appendDefinitionList(parent, block) {
  const list = document.createElement("dl");
  list.className = "docs-definitions";

  (Array.isArray(block.items) ? block.items : []).forEach((item) => {
    if (!item || !normalizeText(item.term)) {
      return;
    }

    appendTextElement(list, "dt", "", item.term);
    appendTextElement(list, "dd", "", item.description);
  });

  if (list.children.length) {
    parent.append(list);
  }
}

function appendCodeBlock(parent, block) {
  const pre = document.createElement("pre");
  pre.className = "docs-code";
  const code = document.createElement("code");
  if (normalizeText(block.language)) {
    code.dataset.language = block.language;
  }
  code.textContent = normalizeText(block.text);
  pre.append(code);
  parent.append(pre);
}

function appendTable(parent, block) {
  const headers = Array.isArray(block.headers) ? block.headers : [];
  const rows = Array.isArray(block.rows) ? block.rows : [];

  if (!headers.length || !rows.length) {
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "docs-table-wrap";
  const table = document.createElement("table");
  table.className = "docs-table";
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");

  headers.forEach((header) => {
    appendTextElement(headerRow, "th", "", header);
  });

  thead.append(headerRow);
  table.append(thead);

  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const bodyRow = document.createElement("tr");
    (Array.isArray(row) ? row : []).forEach((cell) => {
      appendTextElement(bodyRow, "td", "", cell);
    });
    if (bodyRow.children.length) {
      tbody.append(bodyRow);
    }
  });
  table.append(tbody);
  wrapper.append(table);
  parent.append(wrapper);
}

function appendCallout(parent, block) {
  const callout = document.createElement("div");
  callout.className = "docs-callout";
  if (normalizeText(block.title)) {
    appendTextElement(callout, "h3", "", block.title);
  }
  if (normalizeText(block.text)) {
    appendTextElement(callout, "p", "", block.text);
  }
  parent.append(callout);
}

function appendDocsBlock(parent, block) {
  if (!block || typeof block !== "object") {
    return;
  }

  switch (block.type) {
    case "heading":
      appendTextElement(parent, "h3", "docs-subheading", block.text || block.title);
      break;
    case "paragraph":
      appendTextElement(parent, "p", "docs-paragraph", block.text);
      break;
    case "list":
      appendStructuredList(parent, block, false);
      break;
    case "steps":
      appendStructuredList(parent, block, true);
      break;
    case "definition_list":
      appendDefinitionList(parent, block);
      break;
    case "code":
      appendCodeBlock(parent, block);
      break;
    case "table":
      appendTable(parent, block);
      break;
    case "callout":
      appendCallout(parent, block);
      break;
    default:
      if (normalizeText(block.text)) {
        appendTextElement(parent, "p", "docs-paragraph", block.text);
      }
  }
}

function renderDocsArticle(topic) {
  if (!docsArticle) {
    return;
  }

  const header = document.createElement("header");
  header.className = "docs-article-header";

  if (normalizeText(topic.sectionTitle)) {
    appendTextElement(header, "p", "section-kicker", topic.sectionTitle);
  }

  appendTextElement(header, "h2", "", topic.title);

  if (normalizeText(topic.summary)) {
    appendTextElement(header, "p", "docs-summary", topic.summary);
  }

  const content = document.createElement("div");
  content.className = "docs-content";
  const blocks = Array.isArray(topic.blocks) ? topic.blocks : [];
  blocks.forEach((block) => appendDocsBlock(content, block));

  if (!content.children.length) {
    appendTextElement(content, "p", "docs-state", "No docs content is available for this topic.");
  }

  docsArticle.replaceChildren(header, content);
}

function renderDocsNav() {
  if (!docsNav) {
    return;
  }

  docsNav.replaceChildren();

  state.docs.topics.forEach((topic) => {
    const button = document.createElement("button");
    button.className = "docs-topic-button";
    button.type = "button";
    button.dataset.docsTopicButton = "";
    button.dataset.docsTopicId = topic.id;

    if (topic.id === state.docs.activeTopicId) {
      button.classList.add("is-active");
      button.setAttribute("aria-current", "page");
    }

    appendTextElement(button, "span", "", topic.title);
    if (normalizeText(topic.summary)) {
      appendTextElement(button, "small", "", topic.summary);
    }

    button.addEventListener("click", () => {
      selectDocsTopic(topic.id);
    });

    docsNav.append(button);
  });
}

function selectDocsTopic(topicId) {
  const topic = state.docs.topics.find((candidate) => candidate.id === topicId) || state.docs.topics[0];

  if (!topic) {
    renderDocsState("No docs content is available.");
    setText(docsMeta, "Empty");
    return;
  }

  state.docs.activeTopicId = topic.id;
  renderDocsNav();
  renderDocsArticle(topic);
}

async function loadDocs() {
  if (state.docs.loaded || state.docs.loading) {
    return;
  }

  state.docs.loading = true;
  setText(docsMeta, "Loading");
  renderDocsState("Loading docs.");

  try {
    const response = await fetch(DOCS_ASSET_PATH, {
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error(`Docs asset returned ${response.status}`);
    }

    const payload = await response.json();
    const topics = getDocsTopics(payload);
    state.docs.topics = topics;
    state.docs.loaded = true;

    if (!topics.length) {
      setText(docsMeta, "Empty");
      renderDocsState("No docs content is available.");
      return;
    }

    setText(docsMeta, `${topics.length} ${topics.length === 1 ? "topic" : "topics"}`);
    selectDocsTopic(state.docs.activeTopicId || topics[0].id);
  } catch {
    setText(docsMeta, "Error");
    renderDocsState("Docs could not be loaded.");
  } finally {
    state.docs.loading = false;
  }
}

function activateView(viewName) {
  state.activeView = viewName;

  document.querySelectorAll("[data-view-tab]").forEach((tab) => {
    const isActive = tab.dataset.viewTab === viewName;
    tab.classList.toggle("is-active", isActive);
    if (isActive) {
      tab.setAttribute("aria-current", "page");
    } else {
      tab.removeAttribute("aria-current");
    }
  });

  document.querySelectorAll("[data-view-panel]").forEach((panel) => {
    const isActive = panel.dataset.viewPanel === viewName;
    panel.classList.toggle("is-active", isActive);
    panel.hidden = !isActive;
  });

  if (viewName === "docs") {
    void loadDocs();
  }
}

document.querySelectorAll("[data-view-tab]").forEach((tab) => {
  tab.addEventListener("click", () => {
    activateView(tab.dataset.viewTab || "dashboard");
  });
});

document.querySelectorAll("[data-health-check], [data-refresh-health]").forEach((button) => {
  button.addEventListener("click", () => {
    void checkAdminHealth();
  });
});

if (tokenForm) {
  tokenForm.addEventListener("submit", (event) => {
    event.preventDefault();
    state.token = tokenInput ? tokenInput.value.trim() : "";

    if (state.token) {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, state.token);
    } else {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    }

    renderTokenState();
    void checkAdminHealth();
  });
}

document.querySelectorAll("[data-token-clear]").forEach((button) => {
  button.addEventListener("click", () => {
    state.token = "";
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    if (tokenInput) {
      tokenInput.value = "";
    }
    renderTokenState();
    void checkAdminHealth();
  });
});

renderTokenState();
activateView(state.activeView);

if (shell) {
  shell.dataset.ready = "true";
}

void checkAdminHealth();

window.VockyAdmin = {
  TOKEN_STORAGE_KEY,
  ADMIN_API_PREFIX,
  DOCS_ASSET_PATH,
  adminFetch,
};
