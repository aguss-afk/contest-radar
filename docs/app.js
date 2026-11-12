(() => {
  "use strict";

  // ---------------------------------------------------------------- data ---

  const SITES = {
    codeforces: { name: "Codeforces", icon: "codeforces.svg", host: "codeforces.com" },
    atcoder: { name: "AtCoder", icon: "atcoder.svg", host: "atcoder.jp" },
    codechef: { name: "CodeChef", icon: "codechef.svg", host: "codechef.com" },
    leetcode: { name: "LeetCode", icon: "leetcode.svg", host: "leetcode.com" },
    hackerrank: { name: "HackerRank", icon: "hackerrank.svg", host: "hackerrank.com" },
    hackerearth: { name: "HackerEarth", icon: "hackerearth.svg", host: "hackerearth.com" },
  };
  const SITE_ORDER = Object.keys(SITES);
  const THEME_KEY = "contest-radar:theme";
  const FILTER_KEY = "contest-radar:filter";
  const POLL_MS = 60_000;
  const RETRY_MS = 4_000;

  const state = {
    contests: [],
    sources: [],
    generatedAt: 0,
    ready: false,
    loading: true,
    error: "",
    filter: readStorage(FILTER_KEY) || "all",
    query: "",
    mode: "live",
    refreshing: false,
    manualBusy: false,
    firstRender: true,
    lastLoad: 0,
  };

  const els = {};
  let retryTimer = null;
  let toastTimer = null;

  // ------------------------------------------------------------- helpers ---

  function readStorage(key) {
    try {
      return localStorage.getItem(key);
    } catch (_) {
      return null;
    }
  }

  function writeStorage(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (_) {
      // Storage may be unavailable in private browsing; the page still works.
    }
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => {
      switch (character) {
        case "&": return "&amp;";
        case "<": return "&lt;";
        case ">": return "&gt;";
        case '"': return "&quot;";
        default: return "&#39;";
      }
    });
  }

  function safeUrl(value, site) {
    const meta = SITES[site];
    if (!meta) return "#";
    try {
      const url = new URL(String(value));
      if (url.protocol !== "https:") return "#";
      if (url.hostname !== meta.host && !url.hostname.endsWith(`.${meta.host}`)) return "#";
      return url.href;
    } catch (_) {
      return "#";
    }
  }

  function siteKey(site) {
    return SITES[site] ? site : "unknown";
  }

  function siteMeta(site) {
    return SITES[site] || { name: String(site || "Contest"), icon: "trophy", host: "" };
  }

  function icon(name, className = "icon") {
    if (name.endsWith(".svg")) {
      return `<img class="${className}" src="icons/${name}" alt="" aria-hidden="true" decoding="async">`;
    }
    return `<svg class="${className}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
  }

  function plural(count, singular) {
    return `${count} ${count === 1 ? singular : `${singular}s`}`;
  }

  const timeFormatter = new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
  const weekdayFormatter = new Intl.DateTimeFormat(undefined, { weekday: "long" });
  const shortDateFormatter = new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const monthDayFormatter = new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  });

  function formatTime(ms) {
    return timeFormatter.format(new Date(ms));
  }

  function localDateKey(ms) {
    const date = new Date(ms);
    return [
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0"),
    ].join("-");
  }

  function dayLabel(ms) {
    const key = localDateKey(ms);
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);

    if (key === localDateKey(now.getTime())) {
      return { title: "Today", date: shortDateFormatter.format(new Date(ms)) };
    }
    if (key === localDateKey(tomorrow.getTime())) {
      return { title: "Tomorrow", date: shortDateFormatter.format(new Date(ms)) };
    }
    return { title: weekdayFormatter.format(new Date(ms)), date: monthDayFormatter.format(new Date(ms)) };
  }

  function formatDuration(seconds) {
    const total = Math.max(0, Math.floor(Number(seconds) || 0));
    if (!total) return "";
    const days = Math.floor(total / 86400);
    if (days > 0) return `${days}d`;
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    if (hours > 0) return minutes ? `${hours}h ${minutes}m` : `${hours}h`;
    return `${Math.max(1, minutes)}m`;
  }

  function relativeFuture(ms) {
    const seconds = Math.max(0, Math.ceil(ms / 1000));
    if (seconds < 60) return `in ${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `in ${minutes}m`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
      const rest = minutes % 60;
      return rest ? `in ${hours}h ${rest}m` : `in ${hours}h`;
    }
    const days = Math.floor(hours / 24);
    const rest = hours % 24;
    if (days < 8) return rest ? `in ${days}d ${rest}h` : `in ${days}d`;
    return `in ${days}d`;
  }

  function countdownText(startMs, endMs, nowMs) {
    if (nowMs >= endMs) return "ended";
    if (nowMs >= startMs) return `ends ${relativeFuture(endMs - nowMs)}`;
    return relativeFuture(startMs - nowMs);
  }

  function formatUpdated() {
    if (!state.generatedAt) return "";
    const age = Math.max(0, Math.floor(Date.now() / 1000 - state.generatedAt));
    const suffix = state.mode === "static" ? "snapshot" : "updated";
    if (age < 30) return state.mode === "static" ? "Saved snapshot · just now" : "Updated just now";
    if (age < 3600) return `${suffix} ${Math.floor(age / 60)}m ago`;
    if (age < 86400) return `${suffix} ${Math.floor(age / 3600)}h ago`;
    return `${suffix} ${Math.floor(age / 86400)}d ago`;
  }

  function sleep(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function isTyping(target) {
    return Boolean(
      target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
    );
  }

  // --------------------------------------------------------------- theme ---

  let themePreference = readStorage(THEME_KEY) || "system";
  const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

  function applyTheme() {
    const dark = themePreference === "dark" || (themePreference === "system" && darkQuery.matches);
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    if (els.themeButton) {
      els.themeButton.setAttribute(
        "aria-label",
        dark ? "Switch to light theme" : "Switch to dark theme"
      );
      els.themeButton.title = `Toggle theme (T) · currently ${dark ? "dark" : "light"}`;
    }
  }

  function toggleTheme() {
    themePreference = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    writeStorage(THEME_KEY, themePreference);
    applyTheme();
  }

  const onSystemThemeChange = () => {
    if (themePreference === "system") applyTheme();
  };
  if (typeof darkQuery.addEventListener === "function") {
    darkQuery.addEventListener("change", onSystemThemeChange);
  } else if (typeof darkQuery.addListener === "function") {
    darkQuery.addListener(onSystemThemeChange);
  }

  // --------------------------------------------------------------- fetch ---

  async function fetchJson(url) {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 15_000);
    try {
      const separator = url.includes("?") ? "&" : "?";
      const response = await fetch(`${url}${separator}_=${Date.now()}`, {
        cache: "no-store",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } finally {
      window.clearTimeout(timer);
    }
  }

  function applyPayload(payload, mode) {
    if (!payload || !Array.isArray(payload.contests)) {
      throw new Error("Unexpected contest payload");
    }
    state.contests = payload.contests;
    state.sources = Array.isArray(payload.sources) ? payload.sources : [];
    state.generatedAt = Number(payload.generated_at || 0);
    state.ready = payload.ready !== false;
    state.refreshing = Boolean(payload.refreshing);
    state.mode = mode;
    state.lastLoad = Date.now();
    state.loading = false;
    state.error = "";

    if (state.filter !== "all" && !SITES[state.filter]) {
      state.filter = "all";
    }
  }

  async function loadData({ animate = false, silent = false } = {}) {
    if (state.manualBusy) return;
    const previousGenerated = state.generatedAt;
    const previousCount = state.contests.length;

    try {
      let payload;
      try {
        payload = await fetchJson("/api/contests");
        if (payload.ready === false && !(payload.contests || []).length) {
          state.loading = true;
          state.sources = Array.isArray(payload.sources) ? payload.sources : [];
          state.refreshing = Boolean(payload.refreshing);
          render({ skeleton: true });
          scheduleRetry(2_000);
          return;
        }
        applyPayload(payload, "live");
      } catch (_apiError) {
        payload = await fetchJson("data/contests.json");
        applyPayload(payload, "static");
      }

      const changed =
        state.generatedAt !== previousGenerated ||
        state.contests.length !== previousCount ||
        state.firstRender;

      if (changed || animate) {
        render({ animate: animate || state.firstRender });
        state.firstRender = false;
      } else {
        updateStatus();
        updateCountdowns();
        renderHealth();
      }

      if (!state.ready && !silent) {
        scheduleRetry(RETRY_MS);
      }
    } catch (error) {
      state.loading = false;
      state.error = "Couldn't load contest data.";
      if (!state.contests.length) {
        render();
        scheduleRetry(RETRY_MS);
      } else {
        updateStatus();
      }
    }
  }

  function scheduleRetry(delay = RETRY_MS) {
    if (retryTimer) return;
    retryTimer = window.setTimeout(() => {
      retryTimer = null;
      loadData({ silent: true });
    }, delay);
  }

  // --------------------------------------------------------------- render ---

  function activeContests() {
    const now = Date.now();
    return state.contests.filter((contest) => Number(contest.end) * 1000 > now);
  }

  function render({ animate = false, skeleton = false } = {}) {
    const active = activeContests();
    renderFilters(active);
    renderHealth();
    updateStatus(active);

    if (skeleton || state.loading) {
      els.list.setAttribute("aria-busy", "true");
      els.list.innerHTML = skeletonHtml();
      return;
    }

    if (state.error && !active.length) {
      els.list.setAttribute("aria-busy", "false");
      els.list.innerHTML = errorHtml();
      return;
    }

    const query = state.query.trim().toLowerCase();
    const filtered = active
      .filter((contest) => state.filter === "all" || contest.site === state.filter)
      .filter((contest) => {
        if (!query) return true;
        const meta = siteMeta(contest.site);
        return `${contest.title} ${meta.name} ${contest.note || ""}`.toLowerCase().includes(query);
      })
      .sort((a, b) => Number(a.start) - Number(b.start) || String(a.title).localeCompare(String(b.title)));

    els.list.setAttribute("aria-busy", "false");

    if (!filtered.length) {
      els.list.innerHTML = emptyHtml(active.length > 0);
      return;
    }

    const groups = new Map();
    for (const contest of filtered) {
      const key = localDateKey(Number(contest.start) * 1000);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(contest);
    }

    const keys = Array.from(groups.keys()).sort();
    els.list.innerHTML = keys
      .map((key, index) => {
        const items = groups.get(key);
        const label = dayLabel(Number(items[0].start) * 1000);
        return `
          <section class="day${animate ? " is-animated" : ""}" style="--i:${Math.min(index, 8)}" aria-labelledby="day-${key}">
            <div class="day-heading">
              <h2 id="day-${key}">${escapeHtml(label.title)}</h2>
              <span class="day-date">${escapeHtml(label.date)}</span>
              <span class="day-count">${plural(items.length, "contest")}</span>
            </div>
            <div class="day-list">
              ${items.map(contestHtml).join("")}
            </div>
          </section>`;
      })
      .join("");

    updateCountdowns();
  }

  function contestHtml(contest) {
    const meta = siteMeta(contest.site);
    const site = siteKey(contest.site);
    const now = Date.now();
    const start = Number(contest.start) * 1000;
    const end = Number(contest.end) * 1000;
    const live = now >= start && now < end;
    const soon = !live && start > now && start - now <= 3_600_000;
    const duration = formatDuration(contest.duration);
    const note = contest.note
      ? `<span class="note">${escapeHtml(contest.note)}</span>`
      : "";
    const badge = live
      ? `<span class="badge live">Live</span>`
      : soon
        ? `<span class="badge soon">Soon</span>`
        : "";
    const url = safeUrl(contest.url, contest.site);
    const aria = `${meta.name}: ${contest.title}. ${
      live ? "Live now. " : ""
    }Starts ${new Date(start).toLocaleString()}. Opens in a new tab.`;

    return `
      <a class="contest${live ? " is-live" : ""}${soon ? " is-soon" : ""}"
         href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer"
         aria-label="${escapeHtml(aria)}">
        <span class="site-mark">${icon(meta.icon)}</span>
        <span class="contest-main">
          <span class="contest-top">
            <span class="site-name">${escapeHtml(meta.name)}</span>
            ${badge}${note}
          </span>
          <span class="contest-title">${escapeHtml(contest.title)}</span>
          <span class="contest-meta">
            <time datetime="${new Date(start).toISOString()}">${formatTime(start)}</time>
            ${duration ? `<span class="meta-dot" aria-hidden="true"></span><span>${escapeHtml(duration)}</span>` : ""}
          </span>
        </span>
        <span class="contest-side">
          <span class="countdown" data-start="${Number(contest.start)}" data-end="${Number(contest.end)}">${countdownText(start, end, now)}</span>
          ${icon("arrow", "icon contest-arrow")}
        </span>
      </a>`;
  }

  function renderFilters(active) {
    const counts = Object.fromEntries(SITE_ORDER.map((site) => [site, 0]));
    for (const contest of active) {
      if (counts[contest.site] !== undefined) counts[contest.site] += 1;
    }

    const chips = [
      `<button type="button" class="chip" data-filter="all" aria-pressed="${state.filter === "all"}">
        <span class="dot" aria-hidden="true"></span>
        <span>All</span>
        <span class="count">${active.length}</span>
      </button>`,
      ...SITE_ORDER.map((site) => {
        const meta = SITES[site];
        return `<button type="button" class="chip" data-filter="${site}" aria-pressed="${state.filter === site}">
          <span class="dot" aria-hidden="true"></span>
          <span>${escapeHtml(meta.name)}</span>
          <span class="count">${counts[site]}</span>
        </button>`;
      }),
    ];

    els.filters.innerHTML = chips.join("");
  }

  function renderHealth() {
    if (!state.sources.length) {
      els.sourceHealth.innerHTML = `<span class="source-pill">Sources loading</span>`;
      return;
    }

    els.sourceHealth.innerHTML = state.sources
      .map((source) => {
        const site = siteKey(source.id);
        const error = source.ok ? "" : source.error || "Source unavailable";
        return `<span class="source-pill${source.ok ? "" : " is-error"}" title="${escapeHtml(error)}">
          <span class="dot" aria-hidden="true"></span>
          <span>${escapeHtml(source.name || source.id)}</span>
        </span>`;
      })
      .join("");
  }

  function updateStatus(active = activeContests()) {
    const now = Date.now();
    const live = active.filter(
      (contest) => Number(contest.start) * 1000 <= now && Number(contest.end) * 1000 > now
    ).length;
    const upcoming = active.filter((contest) => Number(contest.start) * 1000 > now).length;

    if (els.statusStrip) els.statusStrip.classList.toggle("has-live", live > 0);

    if (state.loading) {
      els.statusText.textContent = "Loading contests…";
    } else if (state.error && !active.length) {
      els.statusText.textContent = "Contest data is unavailable";
    } else if (live > 0) {
      els.statusText.textContent = `${plural(live, "live contest")} · ${plural(upcoming, "upcoming contest")}`;
    } else if (active.length) {
      els.statusText.textContent = plural(upcoming, "upcoming contest");
    } else {
      els.statusText.textContent = "No upcoming contests";
    }

    els.updatedText.textContent = state.refreshing
      ? "Refreshing…"
      : state.error && active.length
        ? "Offline · last known data"
        : formatUpdated();

    const modeLabel = state.mode === "static" ? "Static snapshot" : "Live server";
    const cadence = state.mode === "static" ? "15 min" : "10 min";
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone || "local time";
    els.footerMeta.innerHTML = `<strong>${modeLabel}</strong> · times in ${escapeHtml(zone)}<br>Auto-updates every ${cadence} · <strong>R</strong> refresh · <strong>T</strong> theme`;
  }

  function updateCountdowns() {
    const now = Date.now();
    document.querySelectorAll("[data-start][data-end]").forEach((node) => {
      const start = Number(node.dataset.start) * 1000;
      const end = Number(node.dataset.end) * 1000;
      const live = now >= start && now < end;
      const soon = !live && start > now && start - now <= 3_600_000;
      const row = node.closest(".contest");
      if (row) {
        row.classList.toggle("is-live", live);
        row.classList.toggle("is-soon", soon);
        row.classList.toggle("is-ended", now >= end);
      }
      node.textContent = countdownText(start, end, now);
    });
  }

  function skeletonHtml() {
    return `<div class="skeleton-list" aria-hidden="true">${"<div class=\"skeleton-row\"></div>".repeat(4)}</div>`;
  }

  function errorHtml() {
    return `<div class="empty is-error">
      <div class="empty-icon">${icon("wifi-off")}</div>
      <h2>Couldn't load contests</h2>
      <p>Check your connection or make sure the local server is running. The last known data will be used if it is available.</p>
      <button class="pill-btn" type="button" data-action="retry">${icon("refresh")}<span>Try again</span></button>
    </div>`;
  }

  function emptyHtml(hasOtherContests) {
    const filtering = state.filter !== "all" || state.query.trim();
    if (filtering && hasOtherContests) {
      return `<div class="empty">
        <div class="empty-icon">${icon("search")}</div>
        <h2>No contests match</h2>
        <p>Try a different site or clear the search.</p>
        <button class="pill-btn" type="button" data-action="clear-filters">Clear filters</button>
      </div>`;
    }
    return `<div class="empty">
      <div class="empty-icon">${icon("trophy")}</div>
      <h2>No upcoming contests</h2>
      <p>The sources are quiet right now. Check back later or refresh the list.</p>
      <button class="pill-btn" type="button" data-action="refresh">${icon("refresh")}<span>Refresh</span></button>
    </div>`;
  }

  // ------------------------------------------------------------- actions ---

  function setRefreshBusy(busy) {
    state.manualBusy = busy;
    els.refreshButton.disabled = busy;
    els.refreshButton.classList.toggle("is-busy", busy);
    els.refreshButton.setAttribute("aria-busy", String(busy));
  }

  async function manualRefresh() {
    if (state.manualBusy) return;
    setRefreshBusy(true);
    const before = state.generatedAt;
    let posted = false;

    try {
      const response = await fetch("/api/refresh", { method: "POST" });
      posted = response.ok;
    } catch (_) {
      posted = false;
    }

    if (posted) {
      for (let attempt = 0; attempt < 24; attempt += 1) {
        await sleep(500);
        try {
          const payload = await fetchJson("/api/contests");
          if (payload.refreshing) continue;
          applyPayload(payload, "live");
          render({ animate: true });
          if (state.generatedAt !== before) break;
        } catch (_) {
          break;
        }
      }
      toast("Contest data refreshed");
    } else {
      setRefreshBusy(false);
      await loadData({ animate: true });
      toast("Showing saved snapshot");
      updateStatus();
      return;
    }

    setRefreshBusy(false);
    updateStatus();
  }

  function clearFilters() {
    state.filter = "all";
    state.query = "";
    els.searchInput.value = "";
    writeStorage(FILTER_KEY, state.filter);
    render({ animate: true });
    els.searchInput.focus();
  }

  function toast(message) {
    els.toast.textContent = message;
    els.toast.classList.add("is-visible");
    if (toastTimer) window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      els.toast.classList.remove("is-visible");
    }, 2_200);
  }

  // -------------------------------------------------------------- events ---

  function bindEvents() {
    els.themeButton.addEventListener("click", toggleTheme);
    els.refreshButton.addEventListener("click", manualRefresh);

    els.filters.addEventListener("click", (event) => {
      const button = event.target.closest("[data-filter]");
      if (!button) return;
      state.filter = button.dataset.filter;
      writeStorage(FILTER_KEY, state.filter);
      render({ animate: true });
    });

    els.searchInput.addEventListener("input", () => {
      state.query = els.searchInput.value;
      render();
    });

    els.list.addEventListener("click", (event) => {
      const action = event.target.closest("[data-action]");
      if (!action) return;
      if (action.dataset.action === "retry" || action.dataset.action === "refresh") {
        manualRefresh();
      } else if (action.dataset.action === "clear-filters") {
        clearFilters();
      }
    });

    document.addEventListener("keydown", (event) => {
      const typing = isTyping(event.target);

      if (event.key === "/" && !typing) {
        event.preventDefault();
        els.searchInput.focus();
        els.searchInput.select();
        return;
      }

      if (event.key === "Escape") {
        if (els.searchInput.value) {
          els.searchInput.value = "";
          state.query = "";
          render();
        }
        els.searchInput.blur();
        return;
      }

      if (typing) return;

      if (event.key === "r" || event.key === "R") {
        event.preventDefault();
        manualRefresh();
      } else if (event.key === "t" || event.key === "T") {
        event.preventDefault();
        toggleTheme();
      }
    });

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden && Date.now() - state.lastLoad > POLL_MS) {
        loadData({ silent: true });
      }
    });
  }

  // ---------------------------------------------------------------- init ---

  function init() {
    els.themeButton = document.getElementById("theme-toggle");
    els.refreshButton = document.getElementById("refresh");
    els.filters = document.getElementById("filters");
    els.searchInput = document.getElementById("search");
    els.list = document.getElementById("contest-list");
    els.statusStrip = document.querySelector(".status-strip");
    els.statusText = document.getElementById("status-text");
    els.updatedText = document.getElementById("updated-text");
    els.sourceHealth = document.getElementById("source-health");
    els.footerMeta = document.getElementById("footer-meta");
    els.toast = document.getElementById("toast");

    applyTheme();
    bindEvents();
    updateStatus();
    loadData({ animate: true });

    window.setInterval(() => {
      updateCountdowns();
    }, 1_000);

    window.setInterval(() => {
      updateStatus();
    }, 30_000);

    window.setInterval(() => {
      if (!document.hidden) loadData({ silent: true });
    }, POLL_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
