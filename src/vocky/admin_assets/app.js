const TOKEN_STORAGE_KEY = "vocky.adminToken";
const ADMIN_API_PREFIX = "/admin/api/";

const state = {
  token: sessionStorage.getItem(TOKEN_STORAGE_KEY) || "",
  activeView: "dashboard",
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
  adminFetch,
};
