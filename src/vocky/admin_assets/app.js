const TOKEN_STORAGE_KEY = "vocky.adminToken";
const API_TOKEN_STORAGE_KEY = "vocky.apiToken";
const ADMIN_API_PREFIX = "/admin/api/";
const DOCS_ASSET_PATH = "/admin/assets/docs.json";
const DEFAULT_DASHBOARD_WINDOW_DAYS = 30;
const DASHBOARD_WINDOW_PRESETS = [7, 30, 90];
const CHANNEL_CATEGORIES = ["web", "mobile", "support"];
const LEGACY_CHANNEL_VALUE = "__legacy_channel__";

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
  feedback: {
    filters: {
      start_ingested_at: "",
      end_ingested_at: "",
      source_product: "",
      source_integration: "",
      conversation_id: "",
      session_id: "",
      user_id: "",
      feedback_value: "",
      channel: "",
      target_type: "",
      trigger_type: "",
      tag: "",
      limit: "50",
    },
    loading: false,
    status: "idle",
    records: [],
    nextCursor: "",
    cursors: [""],
    pageIndex: 0,
    detail: {
      selectedId: "",
      loading: false,
      status: "idle",
      record: null,
      editing: false,
      saving: false,
      confirmingDelete: false,
      deleting: false,
      error: "",
    },
    refreshedAt: null,
    error: "",
  },
  docs: {
    activeTopicId: "",
    apiToken: sessionStorage.getItem(API_TOKEN_STORAGE_KEY) || "",
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
const feedbackStatus = document.querySelector("[data-feedback-status]");
const feedbackMessage = document.querySelector("[data-feedback-message]");
const feedbackUpdated = document.querySelector("[data-feedback-updated]");
const feedbackForm = document.querySelector("[data-feedback-filter-form]");
const feedbackList = document.querySelector("[data-feedback-list]");
const feedbackPrevButton = document.querySelector("[data-feedback-prev]");
const feedbackNextButton = document.querySelector("[data-feedback-next]");
const feedbackPageLabel = document.querySelector("[data-feedback-page-label]");
const feedbackDetail = document.querySelector("[data-feedback-detail]");
const feedbackDetailMeta = document.querySelector("[data-feedback-detail-meta]");
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

function createAdminApiError(response, payload = null) {
  const error = new Error(`Admin API ${response.status}`);
  error.status = response.status;
  error.detail = payload && typeof payload.detail === "string" ? payload.detail : "";
  return error;
}

async function requestAdminJson(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  const response = await adminFetch(path, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    throw createAdminApiError(response, payload);
  }

  if (response.status === 204) {
    return null;
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

function formatUtcDateTime(value) {
  const date = new Date(normalizeText(value));
  if (Number.isNaN(date.getTime())) {
    return "Unknown time";
  }
  return date.toISOString().replace(".000Z", "Z");
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
    appendRecentMeta(meta, formatTargetSummary(record));

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

function setFeedbackStatus(statusName, label) {
  state.feedback.status = statusName;
  state.feedback.error = statusName === "error" ? label : "";

  if (feedbackStatus) {
    feedbackStatus.dataset.feedbackState = statusName;
    feedbackStatus.textContent = label;
  }

  setText(feedbackMessage, label);
}

function getFeedbackFilterInput(name) {
  return feedbackForm ? feedbackForm.querySelector(`[data-feedback-filter="${name}"]`) : null;
}

function toUtcIngestedParam(value) {
  const cleaned = normalizeText(value).trim();
  if (!cleaned) {
    return "";
  }

  const withSeconds = cleaned.length === 16 ? `${cleaned}:00` : cleaned;
  const candidate = `${withSeconds}Z`;
  const parsed = new Date(candidate);
  if (Number.isNaN(parsed.getTime())) {
    return candidate;
  }
  return parsed.toISOString();
}

function readFeedbackFiltersFromForm() {
  const nextFilters = { ...state.feedback.filters };

  Object.keys(nextFilters).forEach((name) => {
    const input = getFeedbackFilterInput(name);
    if (input) {
      nextFilters[name] = input.value.trim();
    }
  });

  if (!nextFilters.limit) {
    nextFilters.limit = "50";
  }

  return nextFilters;
}

function appendTrimmedParam(params, name, value) {
  const cleaned = normalizeText(value).trim();
  if (cleaned) {
    params.set(name, cleaned);
  }
}

function makeFeedbackListPath(cursor = "") {
  const params = new URLSearchParams();
  const filters = state.feedback.filters;

  appendTrimmedParam(
    params,
    "start_ingested_at",
    toUtcIngestedParam(filters.start_ingested_at),
  );
  appendTrimmedParam(
    params,
    "end_ingested_at",
    toUtcIngestedParam(filters.end_ingested_at),
  );
  appendTrimmedParam(params, "source_product", filters.source_product);
  appendTrimmedParam(params, "source_integration", filters.source_integration);
  appendTrimmedParam(params, "conversation_id", filters.conversation_id);
  appendTrimmedParam(params, "session_id", filters.session_id);
  appendTrimmedParam(params, "user_id", filters.user_id);
  appendTrimmedParam(params, "feedback_value", filters.feedback_value);
  appendTrimmedParam(params, "channel", filters.channel);
  appendTrimmedParam(params, "target_type", filters.target_type);
  appendTrimmedParam(params, "trigger_type", filters.trigger_type);
  appendTrimmedParam(params, "tag", filters.tag);
  appendTrimmedParam(params, "limit", filters.limit);
  appendTrimmedParam(params, "cursor", cursor);

  const query = params.toString();
  return query ? `/admin/api/feedback?${query}` : "/admin/api/feedback";
}

function renderFeedbackState(label) {
  if (!feedbackList) {
    return;
  }

  const item = document.createElement("li");
  item.className = "feedback-empty-state";
  item.dataset.feedbackListState = "";
  item.textContent = label;
  feedbackList.replaceChildren(item);
}

function renderFeedbackPaging() {
  const isLoading = state.feedback.loading;
  if (feedbackPrevButton) {
    feedbackPrevButton.disabled = isLoading || state.feedback.pageIndex === 0;
  }
  if (feedbackNextButton) {
    feedbackNextButton.disabled = isLoading || !state.feedback.nextCursor;
  }
  setText(feedbackPageLabel, `Page ${state.feedback.pageIndex + 1}`);
}

function appendFeedbackTagList(parent, tags) {
  const normalizedTags = Array.isArray(tags) ? tags : [];
  if (!normalizedTags.length) {
    return;
  }

  const list = document.createElement("ul");
  list.className = "feedback-tag-list";
  normalizedTags.forEach((tag) => {
    const item = document.createElement("li");
    item.textContent = normalizeText(tag);
    if (item.textContent) {
      list.append(item);
    }
  });

  if (list.children.length) {
    parent.append(list);
  }
}

function setFeedbackDetailMeta(label) {
  setText(feedbackDetailMeta, label);
}

function renderFeedbackDetailState(label) {
  if (!feedbackDetail) {
    return;
  }

  const item = document.createElement("p");
  item.className = "feedback-empty-state";
  item.dataset.feedbackDetailState = "";
  item.textContent = label;
  feedbackDetail.replaceChildren(item);
}

function clearFeedbackDetail(label = "Select a record.") {
  state.feedback.detail.selectedId = "";
  state.feedback.detail.loading = false;
  state.feedback.detail.status = "idle";
  state.feedback.detail.record = null;
  state.feedback.detail.editing = false;
  state.feedback.detail.saving = false;
  state.feedback.detail.confirmingDelete = false;
  state.feedback.detail.deleting = false;
  state.feedback.detail.error = "";
  setFeedbackDetailMeta("Read only");
  renderFeedbackDetailState(label);
}

function getDisplayValue(value) {
  const normalized = normalizeText(value);
  return normalized || "None";
}

function formatTargetSummary(record) {
  const targetType = normalizeText(record?.target_type);
  const targetId = normalizeText(record?.target_id);
  const targetRole = normalizeText(record?.target_role);
  const targetText = normalizeText(record?.target_text);
  if (!targetType && !targetId && !targetRole && !targetText) {
    return "";
  }

  const roleAndType = [targetRole, targetType].filter(Boolean).join(" ");
  const parts = [roleAndType, targetId].filter(Boolean);
  if (!parts.length) {
    parts.push("text");
  }

  return `Target: ${parts.join(" ")}`;
}

function appendDetailField(list, term, value) {
  const label = document.createElement("dt");
  label.textContent = term;
  const detail = document.createElement("dd");
  detail.textContent = getDisplayValue(value);
  list.append(label, detail);
}

function appendDetailSection(parent, title) {
  const section = document.createElement("section");
  section.className = "feedback-detail-section";
  const heading = document.createElement("h3");
  heading.textContent = title;
  section.append(heading);
  parent.append(section);
  return section;
}

function appendJsonSection(parent, title, value) {
  const section = appendDetailSection(parent, title);
  const pre = document.createElement("pre");
  pre.className = "feedback-json-block";
  const code = document.createElement("code");
  code.textContent = JSON.stringify(value ?? null, null, 2);
  pre.append(code);
  section.append(pre);
}

function getEditableTagsValue(record) {
  return Array.isArray(record.tags) ? record.tags.join(", ") : "";
}

function isAllowedChannel(value) {
  return CHANNEL_CATEGORIES.includes(normalizeText(value));
}

function parseEditableTags(value) {
  return normalizeText(value)
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function updateCurrentFeedbackRecord(record) {
  const index = state.feedback.records.findIndex(
    (candidate) => normalizeText(candidate.id) === normalizeText(record.id),
  );
  if (index >= 0) {
    state.feedback.records[index] = record;
    renderFeedbackList(state.feedback.records);
  }
}

function enterFeedbackEditMode() {
  if (!state.feedback.detail.record || state.feedback.detail.saving) {
    return;
  }

  state.feedback.detail.editing = true;
  state.feedback.detail.error = "";
  renderFeedbackDetailRecord(state.feedback.detail.record);
}

function cancelFeedbackEditMode() {
  if (!state.feedback.detail.record || state.feedback.detail.saving) {
    return;
  }

  state.feedback.detail.editing = false;
  state.feedback.detail.error = "";
  renderFeedbackDetailRecord(state.feedback.detail.record);
}

function beginFeedbackDelete() {
  if (
    !state.feedback.detail.record ||
    state.feedback.detail.saving ||
    state.feedback.detail.deleting
  ) {
    return;
  }

  state.feedback.detail.editing = false;
  state.feedback.detail.confirmingDelete = true;
  state.feedback.detail.error = "";
  renderFeedbackDetailRecord(state.feedback.detail.record);
}

function cancelFeedbackDelete() {
  if (!state.feedback.detail.record || state.feedback.detail.deleting) {
    return;
  }

  state.feedback.detail.confirmingDelete = false;
  state.feedback.detail.error = "";
  renderFeedbackDetailRecord(state.feedback.detail.record);
}

async function deleteSelectedFeedbackRecord() {
  const recordId = state.feedback.detail.selectedId;
  if (!recordId || state.feedback.detail.deleting) {
    return;
  }

  state.feedback.detail.deleting = true;
  state.feedback.detail.error = "";
  setFeedbackDetailMeta("Deleting");
  renderFeedbackDetailRecord(state.feedback.detail.record);

  try {
    await requestAdminJson(`/admin/api/feedback/${encodeURIComponent(recordId)}`, {
      method: "DELETE",
    });
    state.feedback.records = state.feedback.records.filter(
      (record) => normalizeText(record.id) !== recordId,
    );
    clearFeedbackDetail("Feedback record deleted.");
    renderFeedbackList(state.feedback.records);
    renderFeedbackPaging();
    await refreshFeedback();
    setFeedbackStatus("loaded", "Feedback record deleted");
  } catch (error) {
    state.feedback.detail.deleting = false;
    state.feedback.detail.error = error.detail || "Feedback record could not be deleted.";

    if (error.status === 401) {
      setFeedbackDetailMeta("Unauthorized");
      setFeedbackStatus("unauthorized", "Admin API unauthorized");
    } else if (error.status === 404) {
      setFeedbackDetailMeta("Missing");
      setFeedbackStatus("error", "Feedback record was not found");
    } else {
      setFeedbackDetailMeta("Error");
      setFeedbackStatus("error", "Feedback record could not be deleted");
    }

    renderFeedbackDetailRecord(state.feedback.detail.record);
  }
}

function getFeedbackPatchPayload(form) {
  const formData = new FormData(form);
  const feedbackValue = normalizeText(formData.get("feedback_value")).trim();
  const channelValue = normalizeText(formData.get("channel")).trim();
  const payload = {
    feedback_value: feedbackValue ? Number(feedbackValue) : null,
    comment: normalizeText(formData.get("comment")).trim() || null,
    tags: parseEditableTags(formData.get("tags")),
  };

  if (channelValue !== LEGACY_CHANNEL_VALUE) {
    payload.channel = channelValue || null;
  }

  return payload;
}

function setFeedbackEditFormSaving(form, saving) {
  form.querySelectorAll("input, select, textarea, button").forEach((field) => {
    field.disabled = saving;
  });
}

async function saveFeedbackReviewFields(form) {
  const recordId = state.feedback.detail.selectedId;
  if (!recordId || state.feedback.detail.saving) {
    return;
  }

  const payload = getFeedbackPatchPayload(form);
  state.feedback.detail.saving = true;
  state.feedback.detail.error = "";
  setFeedbackDetailMeta("Saving");
  setFeedbackEditFormSaving(form, true);

  try {
    const responsePayload = await requestAdminJson(
      `/admin/api/feedback/${encodeURIComponent(recordId)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );

    state.feedback.detail.record = responsePayload.record || null;
    state.feedback.detail.editing = false;
    state.feedback.detail.saving = false;
    state.feedback.detail.status = "loaded";
    state.feedback.detail.error = "";

    if (state.feedback.detail.record) {
      updateCurrentFeedbackRecord(state.feedback.detail.record);
      renderFeedbackDetailRecord(state.feedback.detail.record);
      setFeedbackStatus("loaded", "Feedback record saved");
    } else {
      renderFeedbackDetailState("Feedback detail unavailable.");
    }
  } catch (error) {
    state.feedback.detail.saving = false;
    state.feedback.detail.error = error.detail || "Feedback record could not be saved.";
    setFeedbackDetailMeta(error.status === 401 ? "Unauthorized" : "Error");
    setFeedbackEditFormSaving(form, false);

    const errorMessage = form.querySelector("[data-feedback-edit-error]");
    setText(errorMessage, state.feedback.detail.error);

    if (error.status === 401) {
      setFeedbackStatus("unauthorized", "Admin API unauthorized");
    } else if (error.status === 404) {
      setFeedbackStatus("error", "Feedback record was not found");
    } else {
      setFeedbackStatus("error", "Feedback record could not be saved");
    }
  }
}

function buildFeedbackEditForm(record) {
  const form = document.createElement("form");
  form.className = "feedback-edit-form";
  form.dataset.feedbackEditForm = "";

  const valueLabel = document.createElement("label");
  appendTextElement(valueLabel, "span", "", "Feedback value");
  const valueSelect = document.createElement("select");
  valueSelect.name = "feedback_value";
  [
    ["", "Unrated"],
    ["1", "Liked"],
    ["2", "Disliked"],
  ].forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    if (String(record.feedback_value || "") === value) {
      option.selected = true;
    }
    valueSelect.append(option);
  });
  valueLabel.append(valueSelect);

  const channelLabel = document.createElement("label");
  appendTextElement(channelLabel, "span", "", "Channel");
  channelLabel.append(buildChannelSelect(record));

  const commentLabel = document.createElement("label");
  commentLabel.className = "feedback-edit-wide";
  appendTextElement(commentLabel, "span", "", "Comment");
  const commentInput = document.createElement("textarea");
  commentInput.name = "comment";
  commentInput.rows = 4;
  commentInput.value = normalizeText(record.comment);
  commentLabel.append(commentInput);

  const tagsLabel = document.createElement("label");
  tagsLabel.className = "feedback-edit-wide";
  appendTextElement(tagsLabel, "span", "", "Tags");
  const tagsInput = document.createElement("input");
  tagsInput.name = "tags";
  tagsInput.type = "text";
  tagsInput.autocomplete = "off";
  tagsInput.spellcheck = false;
  tagsInput.value = getEditableTagsValue(record);
  tagsLabel.append(tagsInput);

  const error = document.createElement("p");
  error.className = "feedback-edit-error";
  error.dataset.feedbackEditError = "";
  error.textContent = state.feedback.detail.error;

  const actions = document.createElement("div");
  actions.className = "feedback-detail-actions";
  const saveButton = document.createElement("button");
  saveButton.className = "primary-button";
  saveButton.type = "submit";
  saveButton.textContent = "Save";
  const cancelButton = document.createElement("button");
  cancelButton.className = "secondary-button";
  cancelButton.type = "button";
  cancelButton.textContent = "Cancel";
  cancelButton.addEventListener("click", cancelFeedbackEditMode);
  actions.append(saveButton, cancelButton);

  form.append(valueLabel, channelLabel, commentLabel, tagsLabel, error, actions);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void saveFeedbackReviewFields(form);
  });

  return form;
}

function appendChannelOption(select, value, label, selectedValue) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  if (value === selectedValue) {
    option.selected = true;
  }
  select.append(option);
}

function buildChannelSelect(record) {
  const select = document.createElement("select");
  const channel = normalizeText(record.channel);
  const selectedValue = channel && !isAllowedChannel(channel) ? LEGACY_CHANNEL_VALUE : channel;
  select.name = "channel";

  if (channel && !isAllowedChannel(channel)) {
    appendChannelOption(select, LEGACY_CHANNEL_VALUE, `Legacy: ${channel}`, selectedValue);
  }

  appendChannelOption(select, "", "None", selectedValue);
  CHANNEL_CATEGORIES.forEach((category) => {
    appendChannelOption(select, category, category, selectedValue);
  });

  return select;
}

function renderFeedbackDetailRecord(record) {
  if (!feedbackDetail) {
    return;
  }

  const container = document.createDocumentFragment();
  const header = document.createElement("header");
  header.className = "feedback-detail-header";

  const titleRow = document.createElement("div");
  titleRow.className = "feedback-detail-title-row";
  const titleMeta = document.createElement("div");
  titleMeta.className = "feedback-detail-source-row";
  const badge = document.createElement("span");
  badge.className = `feedback-badge is-${getFeedbackTone(record.feedback_value)}`;
  badge.textContent = formatFeedbackValue(record.feedback_value);
  const ingested = document.createElement("time");
  ingested.dateTime = normalizeText(record.ingested_at);
  ingested.textContent = formatUtcDateTime(record.ingested_at);
  titleMeta.append(badge, ingested);

  const titleActions = document.createElement("div");
  titleActions.className = "feedback-detail-actions";
  if (!state.feedback.detail.editing) {
    if (state.feedback.detail.confirmingDelete) {
      const confirmButton = document.createElement("button");
      confirmButton.className = "danger-button";
      confirmButton.type = "button";
      confirmButton.dataset.feedbackDeleteConfirm = "";
      confirmButton.textContent = state.feedback.detail.deleting ? "Deleting" : "Confirm delete";
      confirmButton.disabled = state.feedback.detail.deleting;
      confirmButton.addEventListener("click", () => {
        void deleteSelectedFeedbackRecord();
      });

      const cancelButton = document.createElement("button");
      cancelButton.className = "secondary-button";
      cancelButton.type = "button";
      cancelButton.dataset.feedbackDeleteCancel = "";
      cancelButton.textContent = "Cancel";
      cancelButton.disabled = state.feedback.detail.deleting;
      cancelButton.addEventListener("click", cancelFeedbackDelete);
      titleActions.append(confirmButton, cancelButton);
    } else {
      const editButton = document.createElement("button");
      editButton.className = "secondary-button";
      editButton.type = "button";
      editButton.dataset.feedbackEdit = "";
      editButton.textContent = "Edit";
      editButton.addEventListener("click", enterFeedbackEditMode);

      const deleteButton = document.createElement("button");
      deleteButton.className = "danger-button";
      deleteButton.type = "button";
      deleteButton.dataset.feedbackDelete = "";
      deleteButton.textContent = "Delete";
      deleteButton.addEventListener("click", beginFeedbackDelete);
      titleActions.append(editButton, deleteButton);
    }
  }
  titleRow.append(titleMeta, titleActions);

  const message = document.createElement("p");
  message.className = "feedback-detail-message";
  message.textContent = normalizeText(record.message) || "Untitled feedback";

  const sourceRow = document.createElement("div");
  sourceRow.className = "feedback-detail-source-row";
  appendRecentMeta(sourceRow, normalizeText(record.source_product));
  appendRecentMeta(sourceRow, normalizeText(record.source_integration));
  appendRecentMeta(sourceRow, normalizeText(record.channel));

  header.append(titleRow, message);
  if (sourceRow.children.length) {
    header.append(sourceRow);
  }
  if (normalizeText(record.comment)) {
    const comment = document.createElement("p");
    comment.className = "feedback-detail-comment";
    comment.textContent = record.comment;
    header.append(comment);
  }
  appendFeedbackTagList(header, record.tags);
  if (state.feedback.detail.confirmingDelete) {
    const deletePrompt = document.createElement("p");
    deletePrompt.className = "feedback-delete-prompt";
    deletePrompt.textContent = "Confirm deletion before this record is removed.";
    header.append(deletePrompt);
  }
  container.append(header);

  if (state.feedback.detail.editing) {
    container.append(buildFeedbackEditForm(record));
    setFeedbackDetailMeta("Editing");
  } else if (state.feedback.detail.deleting) {
    setFeedbackDetailMeta("Deleting");
  } else if (state.feedback.detail.confirmingDelete) {
    setFeedbackDetailMeta("Confirm delete");
  } else {
    setFeedbackDetailMeta("Read only");
  }

  const fieldsSection = appendDetailSection(container, "Fields");
  const fields = document.createElement("dl");
  fields.className = "feedback-detail-grid";
  appendDetailField(fields, "ID", record.id);
  appendDetailField(fields, "Source product", record.source_product);
  appendDetailField(fields, "Source integration", record.source_integration);
  appendDetailField(fields, "Conversation ID", record.conversation_id);
  appendDetailField(fields, "Session ID", record.session_id);
  appendDetailField(fields, "User ID", record.user_id);
  appendDetailField(fields, "Channel", record.channel);
  appendDetailField(fields, "Feedback value", formatFeedbackValue(record.feedback_value));
  appendDetailField(fields, "Event at", record.event_at ? formatUtcDateTime(record.event_at) : "");
  appendDetailField(fields, "Ingested at", formatUtcDateTime(record.ingested_at));
  fieldsSection.append(fields);

  const targetSection = appendDetailSection(container, "Target");
  const targetFields = document.createElement("dl");
  targetFields.className = "feedback-detail-grid";
  appendDetailField(targetFields, "Type", record.target_type);
  appendDetailField(targetFields, "ID", record.target_id);
  appendDetailField(targetFields, "Role", record.target_role);
  appendDetailField(targetFields, "Text", record.target_text);
  targetSection.append(targetFields);

  const triggerSection = appendDetailSection(container, "Trigger");
  const triggerFields = document.createElement("dl");
  triggerFields.className = "feedback-detail-grid";
  appendDetailField(triggerFields, "Type", record.trigger_type);
  appendDetailField(triggerFields, "Message", record.trigger_message);
  triggerSection.append(triggerFields);
  const triggerMetadata = document.createElement("pre");
  triggerMetadata.className = "feedback-json-block";
  const triggerMetadataCode = document.createElement("code");
  triggerMetadataCode.textContent = JSON.stringify(record.trigger_metadata || {}, null, 2);
  triggerMetadata.append(triggerMetadataCode);
  triggerSection.append(triggerMetadata);

  appendJsonSection(container, "Messages", Array.isArray(record.messages) ? record.messages : []);
  appendJsonSection(
    container,
    "Used context",
    Array.isArray(record.used_context) ? record.used_context : [],
  );
  appendJsonSection(container, "Source metadata", record.source_metadata || {});
  appendJsonSection(container, "Attributes", record.attributes || {});

  feedbackDetail.replaceChildren(container);
}

function syncSelectedFeedbackListItem() {
  if (!feedbackList) {
    return;
  }

  feedbackList.querySelectorAll("[data-feedback-select]").forEach((button) => {
    const isSelected = button.dataset.feedbackRecordId === state.feedback.detail.selectedId;
    button.classList.toggle("is-selected", isSelected);
    if (isSelected) {
      button.setAttribute("aria-current", "true");
    } else {
      button.removeAttribute("aria-current");
    }
  });
}

async function selectFeedbackRecord(recordId) {
  const selectedId = normalizeText(recordId);
  if (!selectedId || state.feedback.detail.loading) {
    return;
  }

  state.feedback.detail.selectedId = selectedId;
  state.feedback.detail.loading = true;
  state.feedback.detail.status = "loading";
  state.feedback.detail.record = null;
  state.feedback.detail.editing = false;
  state.feedback.detail.saving = false;
  state.feedback.detail.confirmingDelete = false;
  state.feedback.detail.deleting = false;
  state.feedback.detail.error = "";
  syncSelectedFeedbackListItem();
  setFeedbackDetailMeta("Loading");
  renderFeedbackDetailState("Loading feedback detail.");

  try {
    const payload = await requestAdminJson(`/admin/api/feedback/${encodeURIComponent(selectedId)}`);
    state.feedback.detail.record = payload.record || null;
    state.feedback.detail.loading = false;
    state.feedback.detail.status = "loaded";
    if (state.feedback.detail.record) {
      renderFeedbackDetailRecord(state.feedback.detail.record);
    } else {
      state.feedback.detail.status = "error";
      renderFeedbackDetailState("Feedback detail unavailable.");
    }
  } catch (error) {
    state.feedback.detail.loading = false;
    state.feedback.detail.record = null;
    syncSelectedFeedbackListItem();

    if (error.status === 401) {
      state.feedback.detail.status = "unauthorized";
      setFeedbackDetailMeta("Unauthorized");
      renderFeedbackDetailState("Admin API unauthorized.");
      return;
    }

    if (error.status === 404) {
      state.feedback.detail.status = "missing";
      setFeedbackDetailMeta("Missing");
      renderFeedbackDetailState("Feedback record was not found.");
      return;
    }

    state.feedback.detail.status = "error";
    setFeedbackDetailMeta("Error");
    renderFeedbackDetailState("Feedback detail unavailable.");
  }
}

function renderFeedbackList(records) {
  if (!feedbackList) {
    return;
  }

  const feedbackRecords = Array.isArray(records) ? records : [];
  if (!feedbackRecords.length) {
    renderFeedbackState("No feedback records match these filters.");
    return;
  }

  const fragment = document.createDocumentFragment();
  feedbackRecords.forEach((record) => {
    const item = document.createElement("li");
    item.className = "feedback-list-item";
    const recordId = normalizeText(record.id);

    const button = document.createElement("button");
    button.className = "feedback-list-button";
    button.type = "button";
    button.dataset.feedbackSelect = "";
    button.dataset.feedbackRecordId = recordId;
    if (recordId === state.feedback.detail.selectedId) {
      button.classList.add("is-selected");
      button.setAttribute("aria-current", "true");
    }
    button.addEventListener("click", () => {
      void selectFeedbackRecord(recordId);
    });

    const header = document.createElement("div");
    header.className = "feedback-list-item-header";

    const badge = document.createElement("span");
    badge.className = `feedback-badge is-${getFeedbackTone(record.feedback_value)}`;
    badge.textContent = formatFeedbackValue(record.feedback_value);

    const time = document.createElement("time");
    time.dateTime = normalizeText(record.ingested_at);
    time.textContent = formatUtcDateTime(record.ingested_at);

    header.append(badge, time);

    const message = document.createElement("p");
    message.className = "feedback-list-message";
    message.textContent = normalizeText(record.message) || "Untitled feedback";

    const meta = document.createElement("div");
    meta.className = "feedback-list-meta";
    appendRecentMeta(meta, normalizeText(record.source_product));
    appendRecentMeta(meta, normalizeText(record.source_integration));
    appendRecentMeta(meta, normalizeText(record.channel));
    appendRecentMeta(meta, normalizeText(record.conversation_id));
    appendRecentMeta(meta, normalizeText(record.session_id));
    appendRecentMeta(meta, normalizeText(record.user_id));
    appendRecentMeta(meta, normalizeText(record.trigger_type));
    appendRecentMeta(meta, formatTargetSummary(record));

    button.append(header, message);
    if (meta.children.length) {
      button.append(meta);
    }

    appendFeedbackTagList(button, record.tags);

    if (normalizeText(record.comment)) {
      const comment = document.createElement("p");
      comment.className = "feedback-comment";
      comment.textContent = record.comment;
      button.append(comment);
    }

    item.append(button);
    fragment.append(item);
  });

  feedbackList.replaceChildren(fragment);
}

function renderFeedbackLoadedState() {
  const count = state.feedback.records.length;
  state.feedback.refreshedAt = new Date();
  state.feedback.loading = false;
  if (
    state.feedback.detail.selectedId &&
    !state.feedback.records.some((record) => normalizeText(record.id) === state.feedback.detail.selectedId)
  ) {
    clearFeedbackDetail();
  }
  renderFeedbackList(state.feedback.records);
  renderFeedbackPaging();
  setText(
    feedbackUpdated,
    state.feedback.refreshedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  );

  if (count === 0) {
    setFeedbackStatus("empty", "No feedback records found");
    return;
  }

  setFeedbackStatus("loaded", `${formatCount(count)} feedback records loaded`);
}

async function refreshFeedback(options = {}) {
  if (options.resetPage) {
    state.feedback.cursors = [""];
    state.feedback.pageIndex = 0;
    state.feedback.nextCursor = "";
    clearFeedbackDetail();
  }

  state.feedback.loading = true;
  setFeedbackStatus("loading", "Loading feedback records");
  renderFeedbackState("Loading feedback records.");
  renderFeedbackPaging();

  const cursor = state.feedback.cursors[state.feedback.pageIndex] || "";

  try {
    const payload = await requestAdminJson(makeFeedbackListPath(cursor));
    state.feedback.records = Array.isArray(payload.records) ? payload.records : [];
    state.feedback.nextCursor = normalizeText(payload.next_cursor);
    renderFeedbackLoadedState();
  } catch (error) {
    state.feedback.loading = false;
    state.feedback.records = [];
    state.feedback.nextCursor = "";
    renderFeedbackPaging();

    if (error.status === 401) {
      setFeedbackStatus("unauthorized", "Admin API unauthorized");
      renderFeedbackState("Admin API unauthorized.");
      return;
    }

    setFeedbackStatus("error", "Feedback records unavailable");
    renderFeedbackState("Feedback records unavailable.");
  }
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

function getRestCaptureTryMethod(block) {
  return normalizeText(block ? block.method : "").trim().toUpperCase() || "POST";
}

function getRestCaptureTryPath(block) {
  const path = normalizeText(block ? block.path : "").trim();
  return path.startsWith("/") ? path : "/api/feedback";
}

function getRestCaptureTryDefaultPayload(block) {
  const payload =
    block &&
    block.default_payload &&
    typeof block.default_payload === "object" &&
    !Array.isArray(block.default_payload)
      ? block.default_payload
      : {};

  return JSON.stringify(payload, null, 2);
}

function setDocsApiToken(value) {
  state.docs.apiToken = normalizeText(value).trim();

  if (state.docs.apiToken) {
    sessionStorage.setItem(API_TOKEN_STORAGE_KEY, state.docs.apiToken);
  } else {
    sessionStorage.removeItem(API_TOKEN_STORAGE_KEY);
  }
}

function createRestTryOutputPanel(title, className) {
  const panel = document.createElement("section");
  panel.className = `docs-rest-try-output ${className}`;
  const heading = document.createElement("h4");
  heading.textContent = title;
  const pre = document.createElement("pre");
  pre.className = "docs-rest-try-code";
  const code = document.createElement("code");
  pre.append(code);
  panel.append(heading, pre);
  return { panel, code };
}

function setRestTryStatus(statusElement, stateName, label) {
  statusElement.dataset.restTryState = stateName;
  statusElement.textContent = label;
}

function setRestTryFormBusy(form, busy) {
  form.querySelectorAll("input, textarea, button").forEach((field) => {
    field.disabled = busy;
  });
}

function parseRestTryResponseBody(rawText) {
  if (!rawText) {
    return {
      parsed: null,
      display: "null",
      parseError: "",
    };
  }

  try {
    const parsed = JSON.parse(rawText);
    return {
      parsed,
      display: JSON.stringify(parsed, null, 2),
      parseError: "",
    };
  } catch (error) {
    return {
      parsed: null,
      display: rawText,
      parseError: error instanceof Error ? error.message : "Response body is not valid JSON.",
    };
  }
}

function getRestTryHttpErrorDetail(response, parsedBody, responseParseError) {
  const statusText = response.statusText ? ` ${response.statusText}` : "";
  const details = [`HTTP ${response.status}${statusText}`];

  if (parsedBody && typeof parsedBody.detail === "string") {
    details.push(parsedBody.detail);
  }

  if (responseParseError) {
    details.push(`Response body was not valid JSON: ${responseParseError}`);
  }

  return details.join("\n");
}

async function sendRestCaptureTryRequest(block, form, elements) {
  setDocsApiToken(elements.tokenInput.value);
  const method = getRestCaptureTryMethod(block);
  const path = getRestCaptureTryPath(block);
  const rawRequestBody = elements.payloadInput.value;
  let requestPayload;
  let requestBody;

  try {
    requestPayload = JSON.parse(rawRequestBody);
  } catch (error) {
    elements.requestCode.textContent = rawRequestBody;
    elements.responseCode.textContent = "";
    elements.errorCode.textContent =
      error instanceof Error ? error.message : "Request body is not valid JSON.";
    setRestTryStatus(elements.statusValue, "error", "Request JSON invalid");
    return;
  }

  if (!requestPayload || typeof requestPayload !== "object" || Array.isArray(requestPayload)) {
    elements.requestCode.textContent = rawRequestBody;
    elements.responseCode.textContent = "";
    elements.errorCode.textContent = "Request body must be a JSON object.";
    setRestTryStatus(elements.statusValue, "error", "Request JSON invalid");
    return;
  }

  requestBody = JSON.stringify(requestPayload, null, 2);
  elements.requestCode.textContent = requestBody;
  elements.responseCode.textContent = "";
  elements.errorCode.textContent = "";
  setRestTryStatus(elements.statusValue, "loading", `Sending ${method} ${path}`);
  setRestTryFormBusy(form, true);

  const headers = new Headers({
    Accept: "application/json",
    "Content-Type": "application/json",
  });

  if (state.docs.apiToken) {
    headers.set("Authorization", `Bearer ${state.docs.apiToken}`);
  }

  try {
    const response = await fetch(path, {
      method,
      headers,
      body: requestBody,
    });
    const rawResponseBody = await response.text();
    const parsedResponse = parseRestTryResponseBody(rawResponseBody);
    const statusText = response.statusText ? ` ${response.statusText}` : "";

    elements.responseCode.textContent = parsedResponse.display;

    if (!response.ok) {
      elements.errorCode.textContent = getRestTryHttpErrorDetail(
        response,
        parsedResponse.parsed,
        parsedResponse.parseError,
      );
      setRestTryStatus(elements.statusValue, "error", `${response.status}${statusText}`);
      return;
    }

    if (parsedResponse.parseError) {
      elements.errorCode.textContent = `Response body was not valid JSON: ${parsedResponse.parseError}`;
      setRestTryStatus(elements.statusValue, "error", "Response JSON invalid");
      return;
    }

    elements.errorCode.textContent = "";
    setRestTryStatus(elements.statusValue, "success", `${response.status}${statusText}`);
  } catch (error) {
    elements.responseCode.textContent = "";
    elements.errorCode.textContent =
      error instanceof Error ? error.message : "Network request failed.";
    setRestTryStatus(elements.statusValue, "error", "Network error");
  } finally {
    setRestTryFormBusy(form, false);
  }
}

function appendRestCaptureTryBlock(parent, block) {
  const wrapper = document.createElement("section");
  wrapper.className = "docs-rest-try";
  const blockId = normalizeText(block.id).trim();
  if (blockId) {
    wrapper.id = blockId;
  }

  const header = document.createElement("div");
  header.className = "docs-rest-try-header";
  appendTextElement(header, "h3", "", block.title || "Try REST Capture");
  appendTextElement(
    header,
    "p",
    "docs-rest-try-meta",
    `${getRestCaptureTryMethod(block)} ${getRestCaptureTryPath(block)}`,
  );

  const form = document.createElement("form");
  form.className = "docs-rest-try-form";

  const tokenLabel = document.createElement("label");
  appendTextElement(tokenLabel, "span", "", "API bearer token");
  const tokenInput = document.createElement("input");
  tokenInput.type = "password";
  tokenInput.autocomplete = "off";
  tokenInput.placeholder = "VOCKY_API_AUTH_TOKEN";
  tokenInput.value = state.docs.apiToken;
  tokenInput.dataset.restTryApiToken = "";
  tokenLabel.append(tokenInput);

  const payloadLabel = document.createElement("label");
  payloadLabel.className = "docs-rest-try-payload";
  appendTextElement(payloadLabel, "span", "", "JSON request body");
  const payloadInput = document.createElement("textarea");
  payloadInput.rows = 18;
  payloadInput.spellcheck = false;
  payloadInput.value = getRestCaptureTryDefaultPayload(block);
  payloadInput.dataset.restTryPayload = "";
  payloadLabel.append(payloadInput);

  const actions = document.createElement("div");
  actions.className = "docs-rest-try-actions";
  const sendButton = document.createElement("button");
  sendButton.className = "primary-button";
  sendButton.type = "submit";
  sendButton.textContent = "Send";
  actions.append(sendButton);

  form.append(tokenLabel, payloadLabel, actions);

  const output = document.createElement("div");
  output.className = "docs-rest-try-results";
  const statusPanel = document.createElement("section");
  statusPanel.className = "docs-rest-try-output docs-rest-try-status";
  const statusHeading = document.createElement("h4");
  statusHeading.textContent = "HTTP status";
  const statusValue = document.createElement("p");
  statusValue.className = "docs-rest-try-status-value";
  setRestTryStatus(statusValue, "idle", "Not sent");
  statusPanel.append(statusHeading, statusValue);

  const requestPanel = createRestTryOutputPanel("Request body", "docs-rest-try-request");
  requestPanel.code.textContent = "No request sent yet.";
  const responsePanel = createRestTryOutputPanel("JSON response", "docs-rest-try-response");
  responsePanel.code.textContent = "No response yet.";
  const errorPanel = createRestTryOutputPanel("Error details", "docs-rest-try-error");
  errorPanel.code.textContent = "";
  output.append(statusPanel, requestPanel.panel, responsePanel.panel, errorPanel.panel);

  tokenInput.addEventListener("input", () => {
    setDocsApiToken(tokenInput.value);
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void sendRestCaptureTryRequest(block, form, {
      tokenInput,
      payloadInput,
      statusValue,
      requestCode: requestPanel.code,
      responseCode: responsePanel.code,
      errorCode: errorPanel.code,
    });
  });

  wrapper.append(header, form, output);
  parent.append(wrapper);
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
    case "rest_capture_try":
      appendRestCaptureTryBlock(parent, block);
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

  if (viewName === "feedback" && state.feedback.status === "idle") {
    void refreshFeedback({ resetPage: true });
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

document.querySelectorAll("[data-refresh-feedback]").forEach((button) => {
  button.addEventListener("click", () => {
    state.feedback.filters = readFeedbackFiltersFromForm();
    void refreshFeedback({ resetPage: true });
  });
});

if (feedbackForm) {
  feedbackForm.addEventListener("submit", (event) => {
    event.preventDefault();
    state.feedback.filters = readFeedbackFiltersFromForm();
    void refreshFeedback({ resetPage: true });
  });

  feedbackForm.addEventListener("reset", () => {
    window.setTimeout(() => {
      state.feedback.filters = readFeedbackFiltersFromForm();
      void refreshFeedback({ resetPage: true });
    }, 0);
  });
}

if (feedbackPrevButton) {
  feedbackPrevButton.addEventListener("click", () => {
    if (state.feedback.pageIndex === 0 || state.feedback.loading) {
      return;
    }

    state.feedback.pageIndex -= 1;
    state.feedback.nextCursor = "";
    void refreshFeedback();
  });
}

if (feedbackNextButton) {
  feedbackNextButton.addEventListener("click", () => {
    if (!state.feedback.nextCursor || state.feedback.loading) {
      return;
    }

    state.feedback.cursors = state.feedback.cursors.slice(0, state.feedback.pageIndex + 1);
    state.feedback.cursors.push(state.feedback.nextCursor);
    state.feedback.pageIndex += 1;
    state.feedback.nextCursor = "";
    void refreshFeedback();
  });
}

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
    if (state.activeView === "feedback") {
      void refreshFeedback({ resetPage: true });
    }
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
    if (state.activeView === "feedback") {
      void refreshFeedback({ resetPage: true });
    }
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
  API_TOKEN_STORAGE_KEY,
  ADMIN_API_PREFIX,
  DOCS_ASSET_PATH,
  DEFAULT_DASHBOARD_WINDOW_DAYS,
  DASHBOARD_WINDOW_PRESETS,
  CHANNEL_CATEGORIES,
  adminFetch,
  getDashboardWindow,
  makeDashboardMetricsPath,
  makeRecentFeedbackPath,
  makeFeedbackListPath,
  getRestCaptureTryMethod,
  getRestCaptureTryPath,
  getRestCaptureTryDefaultPayload,
  parseRestTryResponseBody,
  selectFeedbackRecord,
  deleteSelectedFeedbackRecord,
  refreshFeedback,
  refreshDashboard,
};
