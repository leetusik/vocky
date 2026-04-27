const TOKEN_STORAGE_KEY = "vocky.adminToken";
const ADMIN_API_PREFIX = "/admin/api/";
const DOCS_ASSET_PATH = "/admin/assets/docs.json";
const DEFAULT_DASHBOARD_WINDOW_DAYS = 30;
const DASHBOARD_WINDOW_PRESETS = [7, 30, 90];

const state = {
  token: sessionStorage.getItem(TOKEN_STORAGE_KEY) || "",
  activeView: "dashboard",
  dashboard: {
    windowDays: DEFAULT_DASHBOARD_WINDOW_DAYS,
    loading: false,
    status: "idle",
    metrics: null,
    recentRecords: [],
    refreshedAt: null,
    error: "",
  },
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
const dashboardStatus = document.querySelector("[data-dashboard-status]");
const dashboardUpdated = document.querySelector("[data-dashboard-updated]");
const dashboardMessage = document.querySelector("[data-dashboard-message]");
const dashboardWindowButtons = document.querySelectorAll("[data-dashboard-window-days]");
const metricTotal = document.querySelector("[data-metric-total]");
const metricLiked = document.querySelector("[data-metric-liked]");
const metricDisliked = document.querySelector("[data-metric-disliked]");
const metricUnrated = document.querySelector("[data-metric-unrated]");
const metricWindowLabel = document.querySelector("[data-metric-window-label]");
const trendChart = document.querySelector("[data-trend-chart]");
const recentList = document.querySelector("[data-recent-list]");
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

function createAdminApiError(response) {
  const error = new Error(`Admin API ${response.status}`);
  error.status = response.status;
  return error;
}

async function requestAdminJson(path) {
  const response = await adminFetch(path, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw createAdminApiError(response);
  }

  return response.json();
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
  setText(dashboardMessage, message);
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
    const payload = await requestAdminJson("/admin/api/healthz");
    setHealthState(
      payload.status === "ok" ? "healthy" : "error",
      payload.status === "ok" ? "Admin API healthy" : "Admin API unavailable",
    );
  } catch (error) {
    if (error.status === 401) {
      setHealthState("error", "Admin API unauthorized");
    } else if (error.status) {
      setHealthState("error", `Admin API ${error.status}`);
    } else {
      setHealthState("error", "Admin API unreachable");
    }
  }
}

function setDashboardStatus(statusName, label) {
  state.dashboard.status = statusName;
  state.dashboard.error = statusName === "error" ? label : "";

  if (dashboardStatus) {
    dashboardStatus.dataset.dashboardState = statusName;
    dashboardStatus.textContent = label;
  }

  if (shell) {
    shell.dataset.dashboardStatus = statusName;
  }
}

function renderDashboardWindowControls() {
  dashboardWindowButtons.forEach((button) => {
    const days = Number.parseInt(button.dataset.dashboardWindowDays || "", 10);
    const isActive = days === state.dashboard.windowDays;
    button.classList.toggle("is-active", isActive);
    if (isActive) {
      button.setAttribute("aria-pressed", "true");
    } else {
      button.setAttribute("aria-pressed", "false");
    }
  });
}

function getDashboardWindow(days) {
  const end = new Date();
  const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);

  return {
    start,
    end,
    startIngestedAt: start.toISOString(),
    endIngestedAt: end.toISOString(),
  };
}

function makeDashboardMetricsPath(windowRange) {
  const params = new URLSearchParams({
    start_ingested_at: windowRange.startIngestedAt,
    end_ingested_at: windowRange.endIngestedAt,
  });
  return `/admin/api/feedback/metrics?${params.toString()}`;
}

function makeRecentFeedbackPath() {
  return "/admin/api/feedback?limit=5";
}

function normalizeRecentRecords(payload) {
  if (!payload || !Array.isArray(payload.records)) {
    return [];
  }
  return payload.records;
}

function renderDashboardLoadedState() {
  const total = state.dashboard.metrics?.totals?.total || 0;
  const recentCount = state.dashboard.recentRecords.length;
  state.dashboard.refreshedAt = new Date();
  state.dashboard.loading = false;

  setMetricDisplays(state.dashboard.metrics);
  renderTrendChart(state.dashboard.metrics?.daily_counts);
  renderRecentActivity(state.dashboard.recentRecords);

  setText(
    dashboardUpdated,
    state.dashboard.refreshedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  );

  if (total === 0 && recentCount === 0) {
    setDashboardStatus("empty", `No feedback in the last ${state.dashboard.windowDays} days`);
    pushEvent("Dashboard loaded with no feedback records.");
    return;
  }

  setDashboardStatus("refreshed", `Last ${state.dashboard.windowDays} days refreshed`);
  pushEvent(`Dashboard refreshed with ${formatCount(total)} feedback records in the selected window.`);
}

async function refreshDashboard() {
  state.dashboard.loading = true;
  setDashboardStatus("loading", "Loading dashboard");
  renderDashboardWindowControls();
  setMetricDisplays(null);
  renderTrendState("Loading trend.");
  renderRecentState("Loading recent feedback.");
  pushEvent("Loading dashboard.");

  const windowRange = getDashboardWindow(state.dashboard.windowDays);
  const metricsPath = makeDashboardMetricsPath(windowRange);

  try {
    const [healthPayload, metricsPayload, recentPayload] = await Promise.all([
      requestAdminJson("/admin/api/healthz"),
      requestAdminJson(metricsPath),
      requestAdminJson(makeRecentFeedbackPath()),
    ]);

    state.dashboard.metrics = metricsPayload;
    state.dashboard.recentRecords = normalizeRecentRecords(recentPayload);

    setHealthState(
      healthPayload.status === "ok" ? "healthy" : "error",
      healthPayload.status === "ok" ? "Admin API healthy" : "Admin API unavailable",
    );
    renderDashboardLoadedState();
  } catch (error) {
    state.dashboard.loading = false;
    state.dashboard.metrics = null;
    state.dashboard.recentRecords = [];

    if (error.status === 401) {
      setHealthState("error", "Admin API unauthorized");
      setDashboardStatus("unauthorized", "Admin API unauthorized");
      renderDashboardUnavailable("Admin API unauthorized.");
      return;
    }

    setHealthState("error", error.status ? `Admin API ${error.status}` : "Admin API unreachable");
    setDashboardStatus("error", "Dashboard unavailable");
    renderDashboardUnavailable("Dashboard unavailable.");
  }
}

function normalizeText(value) {
  return typeof value === "string" ? value : "";
}

function formatCount(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat().format(Number.isFinite(number) ? number : 0);
}

function formatShortDay(value) {
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return normalizeText(value);
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function formatDateTime(value) {
  const date = new Date(normalizeText(value));
  if (Number.isNaN(date.getTime())) {
    return "Unknown time";
  }
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatFeedbackValue(value) {
  if (value === 1) {
    return "Liked";
  }
  if (value === 2) {
    return "Disliked";
  }
  return "Unrated";
}

function getFeedbackTone(value) {
  if (value === 1) {
    return "liked";
  }
  if (value === 2) {
    return "disliked";
  }
  return "unrated";
}

function setMetricDisplays(metrics) {
  const totals = metrics?.totals || {};
  setText(metricTotal, formatCount(totals.total));
  setText(metricLiked, formatCount(totals.liked));
  setText(metricDisliked, formatCount(totals.disliked));
  setText(metricUnrated, formatCount(totals.unrated));
  setText(metricWindowLabel, `Last ${state.dashboard.windowDays} days`);
}

function renderTrendState(label) {
  if (!trendChart) {
    return;
  }

  const message = document.createElement("p");
  message.className = "dashboard-empty-state";
  message.dataset.trendState = "";
  message.textContent = label;
  trendChart.replaceChildren(message);
}

function renderTrendChart(dailyCounts) {
  if (!trendChart) {
    return;
  }

  const buckets = Array.isArray(dailyCounts) ? dailyCounts : [];
  if (!buckets.length) {
    renderTrendState("No trend buckets are available.");
    return;
  }

  const maxTotal = Math.max(...buckets.map((bucket) => Number(bucket.total || 0)), 1);
  const fragment = document.createDocumentFragment();

  buckets.forEach((bucket) => {
    const total = Number(bucket.total || 0);
    const row = document.createElement("div");
    row.className = "trend-row";

    const day = document.createElement("time");
    day.dateTime = normalizeText(bucket.day);
    day.textContent = formatShortDay(bucket.day);

    const track = document.createElement("div");
    track.className = "trend-track";
    const bar = document.createElement("span");
    bar.className = "trend-bar";
    bar.style.width = `${Math.max((total / maxTotal) * 100, total > 0 ? 4 : 0)}%`;
    bar.setAttribute(
      "aria-label",
      `${formatCount(total)} feedback records on ${normalizeText(bucket.day)}`,
    );
    track.append(bar);

    const count = document.createElement("strong");
    count.textContent = formatCount(total);

    row.append(day, track, count);
    fragment.append(row);
  });

  trendChart.replaceChildren(fragment);
}

function renderRecentState(label) {
  const list = recentList || eventList;
  if (!list) {
    return;
  }

  const item = document.createElement("li");
  item.className = "dashboard-empty-state";
  item.dataset.recentState = "";
  item.textContent = label;
  list.replaceChildren(item);
}

function appendRecentMeta(parent, label) {
  if (!normalizeText(label)) {
    return;
  }

  const item = document.createElement("span");
  item.textContent = label;
  parent.append(item);
}

function renderRecentActivity(records) {
  const list = recentList || eventList;
  if (!list) {
    return;
  }

  const recentRecords = Array.isArray(records) ? records : [];
  if (!recentRecords.length) {
    renderRecentState("No recent feedback records.");
    return;
  }

  const fragment = document.createDocumentFragment();
  recentRecords.forEach((record) => {
    const item = document.createElement("li");
    item.className = "recent-item";

    const header = document.createElement("div");
    header.className = "recent-item-header";

    const badge = document.createElement("span");
    badge.className = `feedback-badge is-${getFeedbackTone(record.feedback_value)}`;
    badge.textContent = formatFeedbackValue(record.feedback_value);

    const time = document.createElement("time");
    time.dateTime = normalizeText(record.ingested_at);
    time.textContent = formatDateTime(record.ingested_at);

    header.append(badge, time);

    const message = document.createElement("p");
    message.className = "recent-message";
    message.textContent = normalizeText(record.message) || "Untitled feedback";

    const meta = document.createElement("div");
    meta.className = "recent-meta";
    appendRecentMeta(meta, normalizeText(record.source_product));
    appendRecentMeta(meta, normalizeText(record.channel));
    appendRecentMeta(meta, normalizeText(record.conversation_id));

    item.append(header, message);
    if (meta.children.length) {
      item.append(meta);
    }

    if (normalizeText(record.comment)) {
      const comment = document.createElement("p");
      comment.className = "recent-comment";
      comment.textContent = record.comment;
      item.append(comment);
    }

    fragment.append(item);
  });

  list.replaceChildren(fragment);
}

function renderDashboardUnavailable(label) {
  setMetricDisplays(null);
  renderTrendState(label);
  renderRecentState(label);
  pushEvent(label);
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

document.querySelectorAll("[data-health-check]").forEach((button) => {
  button.addEventListener("click", () => {
    void checkAdminHealth();
  });
});

document.querySelectorAll("[data-refresh-dashboard]").forEach((button) => {
  button.addEventListener("click", () => {
    void refreshDashboard();
  });
});

dashboardWindowButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const days = Number.parseInt(button.dataset.dashboardWindowDays || "", 10);
    if (!DASHBOARD_WINDOW_PRESETS.includes(days)) {
      return;
    }

    state.dashboard.windowDays = days;
    void refreshDashboard();
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
    void refreshDashboard();
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
    void refreshDashboard();
  });
});

renderTokenState();
renderDashboardWindowControls();
activateView(state.activeView);

if (shell) {
  shell.dataset.ready = "true";
}

void refreshDashboard();

window.VockyAdmin = {
  TOKEN_STORAGE_KEY,
  ADMIN_API_PREFIX,
  DOCS_ASSET_PATH,
  DEFAULT_DASHBOARD_WINDOW_DAYS,
  DASHBOARD_WINDOW_PRESETS,
  adminFetch,
  getDashboardWindow,
  makeDashboardMetricsPath,
  makeRecentFeedbackPath,
  refreshDashboard,
};
