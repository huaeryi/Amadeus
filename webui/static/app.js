const state = {
  challenges: [],
  filter: "",
  selected: null,
  detail: null,
  filePreview: null,
  activeFilePath: null,
  filePreviewLoading: false,
  browserPath: ".",
  browserEntries: [],
  browserLoading: false,
  collapsedEvents: new Set(),
  theme: "light",
};

const elements = {
  refreshList: document.querySelector("#refresh-list"),
  filterInput: document.querySelector("#challenge-filter"),
  challengeList: document.querySelector("#challenge-list"),
  detail: document.querySelector("#detail"),
  toastLayer: document.querySelector("#toast-layer"),
  themeToggle: document.querySelector("#theme-toggle"),
  serverLabel: document.querySelector("#server-label"),
};

const THEME_STORAGE_KEY = "amadeus-theme";
const COMMON_FILE_SHORTCUTS = [
  { label: "cognition", path: "amds_state/cognition.json" },
  { label: "COGNITION", path: "amds_state/COGNITION.md" },
  { label: "run.env", path: "amds_state/run.env" },
  { label: "exp.py", path: "exp.py" },
  { label: "wp.md", path: "wp.md" },
];

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error || `Request failed: ${response.status}`);
    error.payload = payload;
    throw error;
  }
  return payload;
}

function showToast(message, tone = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${tone}`;
  toast.textContent = message;
  elements.toastLayer.appendChild(toast);

  window.setTimeout(() => {
    toast.remove();
  }, 2600);
}

function preferredTheme() {
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark") {
    return stored;
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
  state.theme = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = state.theme;
  if (elements.themeToggle) {
    elements.themeToggle.textContent = state.theme === "dark" ? "Light" : "Dark";
    elements.themeToggle.setAttribute("aria-label", `Switch to ${state.theme === "dark" ? "light" : "dark"} theme`);
  }
}

function toggleTheme() {
  const nextTheme = state.theme === "dark" ? "light" : "dark";
  window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
  applyTheme(nextTheme);
}

function syncSystemTheme(event) {
  if (window.localStorage.getItem(THEME_STORAGE_KEY)) {
    return;
  }
  applyTheme(event.matches ? "dark" : "light");
}

function renderServerLabel() {
  if (!elements.serverLabel) {
    return;
  }
  const port = window.location.port || (window.location.protocol === "https:" ? "443" : "80");
  elements.serverLabel.textContent = `${window.location.hostname}:${port}`;
}

function previewablePaths(detail) {
  if (!detail) {
    return [];
  }

  const artifactPaths = detail.artifacts
    .filter((artifact) => artifact.previewable)
    .map((artifact) => artifact.path);
  return artifactPaths;
}

function preferredPreviewPath(detail) {
  const paths = previewablePaths(detail);
  if (!paths.length) {
    return null;
  }

  if (state.activeFilePath && paths.includes(state.activeFilePath)) {
    return state.activeFilePath;
  }

  const preferred = ["exp.py", "solve.py", "wp.md", "cognition.json", "exp_template.py", "README.md"];
  for (const name of preferred) {
    if (paths.includes(name)) {
      return name;
    }
  }

  return paths[0];
}

function shortcutAvailable(path) {
  if (!state.detail) {
    return false;
  }
  return state.detail.artifacts.some((artifact) => artifact.path === path);
}

function renderFileShortcuts() {
  if (!state.detail) {
    return "";
  }

  const buttons = COMMON_FILE_SHORTCUTS.map((shortcut) => {
    const available = shortcutAvailable(shortcut.path);
    const active = shortcut.path === state.activeFilePath;
    return `
      <button class="quick-file ${active ? "active" : ""}" data-quick-file="${escapeHtml(shortcut.path)}" type="button" ${available ? "" : "disabled"}>
        ${escapeHtml(shortcut.label)}
      </button>
    `;
  }).join("");

  return `<div class="quick-files">${buttons}</div>`;
}

function buildBrowserBreadcrumbs(path) {
  const crumbs = [{ label: ".", path: "." }];
  if (!path || path === ".") {
    return crumbs;
  }

  const parts = path.split("/").filter(Boolean);
  let current = "";
  for (const part of parts) {
    current = current ? `${current}/${part}` : part;
    crumbs.push({ label: part, path: current });
  }
  return crumbs;
}

function normalizeCheckpointGraph(checkpointGraph, checkpoints) {
  const checkpointById = new Map((checkpoints || []).map((checkpoint) => [checkpoint.id, checkpoint]));
  const graphNodes = Array.isArray(checkpointGraph?.nodes) ? checkpointGraph.nodes : [];
  const graphEdges = Array.isArray(checkpointGraph?.edges) ? checkpointGraph.edges : [];
  const nodeById = new Map();
  const nodeOrder = [];

  const addNode = (rawNode, fallbackCheckpoint) => {
    const id = String(rawNode?.id || fallbackCheckpoint?.id || "").trim();
    if (!id) {
      return;
    }

    const checkpoint = fallbackCheckpoint || checkpointById.get(id) || {};
    if (nodeById.has(id)) {
      const node = nodeById.get(id);
      node.name = String(rawNode?.name || node.name || checkpoint.name || id);
      node.short_id = String(rawNode?.short_id || node.short_id || checkpoint.short_id || "").trim();
      node.created_at = String(rawNode?.created_at || node.created_at || checkpoint.created_at || "");
      node.target_dir = String(rawNode?.target_dir || node.target_dir || checkpoint.target_dir || ".");
      node.parent_id = String(rawNode?.parent_id || node.parent_id || checkpoint.parent_id || "").trim() || null;
      node.is_latest = node.is_latest || Boolean(checkpoint.is_latest);
      node.is_head = node.is_head || Boolean(checkpoint.is_head);
      return;
    }

    nodeById.set(id, {
      id,
      short_id: String(rawNode?.short_id || checkpoint.short_id || "").trim(),
      name: String(rawNode?.name || checkpoint.name || id),
      created_at: String(rawNode?.created_at || checkpoint.created_at || ""),
      target_dir: String(rawNode?.target_dir || checkpoint.target_dir || "."),
      parent_id: String(rawNode?.parent_id || checkpoint.parent_id || "").trim() || null,
      is_latest: Boolean(checkpoint.is_latest),
      is_head: Boolean(checkpoint.is_head),
    });
    nodeOrder.push(id);
  };

  for (const rawNode of graphNodes) {
    addNode(rawNode);
  }

  for (const checkpoint of checkpoints || []) {
    addNode(checkpoint, checkpoint);
  }

  for (const edge of graphEdges) {
    if (!edge || typeof edge !== "object") {
      continue;
    }
    const child = String(edge.child || "").trim();
    const parent = String(edge.parent || "").trim() || null;
    if (!child || !nodeById.has(child)) {
      continue;
    }
    nodeById.get(child).parent_id = parent;
  }

  const edges = [];
  const edgeSeen = new Set();
  for (const edge of graphEdges) {
    if (!edge || typeof edge !== "object") {
      continue;
    }
    const parent = String(edge.parent || "").trim();
    const child = String(edge.child || "").trim();
    if (!parent || !child) {
      continue;
    }
    const key = `${parent}->${child}`;
    if (edgeSeen.has(key)) {
      continue;
    }
    edgeSeen.add(key);
    edges.push({ parent, child });
  }

  if (!edges.length) {
    for (const node of nodeById.values()) {
      if (node.parent_id && nodeById.has(node.parent_id)) {
        const key = `${node.parent_id}->${node.id}`;
        if (!edgeSeen.has(key)) {
          edgeSeen.add(key);
          edges.push({ parent: node.parent_id, child: node.id });
        }
      }
    }
  }

  const childrenByParent = new Map();
  const childIds = new Set();
  for (const edge of edges) {
    if (!childrenByParent.has(edge.parent)) {
      childrenByParent.set(edge.parent, []);
    }
    childrenByParent.get(edge.parent).push(edge.child);
    childIds.add(edge.child);
  }

  const orderedIds = [];
  const visited = new Set();
  const visit = (id) => {
    if (!id || visited.has(id) || !nodeById.has(id)) {
      return;
    }
    visited.add(id);
    orderedIds.push(id);
    for (const child of childrenByParent.get(id) || []) {
      visit(child);
    }
  };

  const roots = nodeOrder.filter((id) => !childIds.has(id));
  for (const root of roots.length ? roots : nodeOrder.slice(0, 1)) {
    visit(root);
  }
  for (const id of nodeOrder) {
    visit(id);
  }

  const nodes = orderedIds.map((id) => nodeById.get(id)).filter(Boolean);
  return { nodes, edges };
}

function filteredChallenges() {
  const needle = state.filter.trim().toLowerCase();
  if (!needle) {
    return state.challenges;
  }
  return state.challenges.filter((challenge) => {
    const haystack = [
      challenge.name,
      challenge.group,
      challenge.title,
      challenge.challenge_type,
      ...(challenge.tags || []),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(needle);
  });
}

function challengeDisplayName(challenge) {
  if (challenge.group && challenge.name.startsWith(`${challenge.group}/`)) {
    return challenge.name.slice(challenge.group.length + 1);
  }
  return challenge.name;
}

function groupChallenges(challenges) {
  const groups = new Map();
  for (const challenge of challenges) {
    const group = challenge.group || "Ungrouped";
    if (!groups.has(group)) {
      groups.set(group, []);
    }
    groups.get(group).push(challenge);
  }
  return [...groups.entries()];
}

function eventName(challenge) {
  return challenge.event || challenge.name.split("/")[0] || "Ungrouped";
}

function groupChallengesByEvent(challenges) {
  const events = new Map();
  for (const challenge of challenges) {
    const event = eventName(challenge);
    if (!events.has(event)) {
      events.set(event, []);
    }
    events.get(event).push(challenge);
  }
  return [...events.entries()];
}

function renderChallengeList() {
  const items = filteredChallenges();
  if (!items.length) {
    elements.challengeList.innerHTML = `
      <div class="empty-state">
        <div>
          <h3>No matches</h3>
          <p class="muted">Clear the filter or refresh the challenge list.</p>
        </div>
      </div>
    `;
    return;
  }

  elements.challengeList.innerHTML = groupChallengesByEvent(items)
    .map(([event, eventChallenges]) => {
      const collapsed = state.collapsedEvents.has(event);
      const groups = groupChallenges(eventChallenges)
        .map(([group, challenges]) => {
          const cards = challenges
            .map((challenge) => {
              const statusTone = challenge.solve_status === "solved" ? "ok" : "warn";
              const challengeType = challenge.challenge_type || "unknown";
              const badges = [
                `<span class="chip type">${escapeHtml(challengeType)}</span>`,
                `<span class="chip ${statusTone}">${escapeHtml(challenge.solve_status)}</span>`,
                challenge.initialized ? `<span class="chip ok">initialized</span>` : `<span class="chip warn">not init</span>`,
                `<span class="chip">${challenge.checkpoint_count} cp</span>`,
              ].join("");

              return `
                <button class="challenge-card ${challenge.name === state.selected ? "active" : ""}" data-name="${escapeHtml(challenge.name)}" type="button">
                  <div class="challenge-card-title">
                    <strong>${escapeHtml(challengeDisplayName(challenge))}</strong>
                    <span class="meta">${escapeHtml(challenge.updated_at.slice(5, 16).replace("T", " "))}</span>
                  </div>
                  <div class="challenge-card-badges">${badges}</div>
                  <p class="meta mono">${escapeHtml(challenge.name)}</p>
                </button>
              `;
            })
            .join("");

          return `
            <section class="challenge-group">
              <div class="challenge-group-heading">
                <span>${escapeHtml(group)}</span>
                <span class="chip">${challenges.length}</span>
              </div>
              <div class="challenge-group-list">${cards}</div>
            </section>
          `;
        })
        .join("");
      return `
        <section class="challenge-event ${collapsed ? "collapsed" : ""}">
          <button class="challenge-event-heading" data-event="${escapeHtml(event)}" type="button" aria-expanded="${String(!collapsed)}">
            <span class="challenge-event-title">
              <span class="challenge-event-chevron">${collapsed ? ">" : "v"}</span>
              <span>${escapeHtml(event)}</span>
            </span>
            <span class="chip">${eventChallenges.length}</span>
          </button>
          <div class="challenge-event-list">${collapsed ? "" : groups}</div>
        </section>
      `;
    })
    .join("");

  elements.challengeList.querySelectorAll("[data-event]").forEach((button) => {
    button.addEventListener("click", () => {
      const event = button.dataset.event;
      if (state.collapsedEvents.has(event)) {
        state.collapsedEvents.delete(event);
      } else {
        state.collapsedEvents.add(event);
      }
      renderChallengeList();
    });
  });

  elements.challengeList.querySelectorAll("[data-name]").forEach((button) => {
    button.addEventListener("click", () => {
      selectChallenge(button.dataset.name);
    });
  });
}

function renderEmptyDetail() {
  elements.detail.innerHTML = `
    <section class="empty-state">
      <div>
        <p class="eyebrow">Ready</p>
        <h3>Select a challenge</h3>
        <p class="muted">The right pane will show file previews, checkpoints, and filesystem state.</p>
      </div>
    </section>
  `;
}

function renderFilePreviewCard() {
  if (!state.detail) {
    return "";
  }

  if (state.filePreviewLoading) {
    return `
      <section class="detail-card stack file-preview-card">
        <div class="detail-header">
          <h3>File Preview</h3>
          <span class="badge">loading</span>
        </div>
        <p class="muted">Loading file content...</p>
      </section>
    `;
  }

  if (!state.filePreview) {
    return `
      <section class="detail-card stack file-preview-card">
        <div class="detail-header">
          <h3>File Preview</h3>
          <span class="chip">idle</span>
        </div>
        <p class="muted">Select a file like <span class="mono">exp.py</span> or <span class="mono">wp.md</span> to preview it here.</p>
      </section>
    `;
  }

  if (state.filePreview.type === "directory") {
    const entries = state.filePreview.entries.length
      ? state.filePreview.entries
          .map((entry) => `<div class="entry-copy mono">${escapeHtml(entry.type)}  ${escapeHtml(entry.name)}</div>`)
          .join("")
      : `<p class="muted">Directory is empty.</p>`;

    return `
      <section class="detail-card stack file-preview-card">
        <div class="detail-header">
          <div>
            <h3>File Preview</h3>
            <p class="muted mono">${escapeHtml(state.filePreview.path)}</p>
          </div>
          <span class="chip">directory</span>
        </div>
        <div class="preview-meta">
          <span class="chip">${escapeHtml(state.filePreview.modified_at)}</span>
        </div>
        <div class="file-preview-list">${entries}</div>
      </section>
    `;
  }

  const kindChip = state.filePreview.preview_kind === "binary" ? "binary" : "text";
  const truncateChip = state.filePreview.truncated
    ? `<span class="chip warn">preview capped at ${escapeHtml(String(state.filePreview.preview_limit))} B</span>`
    : "";

  return `
    <section class="detail-card stack file-preview-card">
      <div class="detail-header">
        <div>
          <h3>File Preview</h3>
          <p class="muted mono">${escapeHtml(state.filePreview.path)}</p>
        </div>
        <div class="split-actions">
          <span class="chip">${escapeHtml(kindChip)}</span>
          <span class="chip">${escapeHtml(String(state.filePreview.size))} B</span>
          ${truncateChip}
        </div>
      </div>
      <div class="preview-meta">
        <span class="chip">${escapeHtml(state.filePreview.modified_at)}</span>
      </div>
      <pre class="file-preview">${escapeHtml(state.filePreview.content)}</pre>
    </section>
  `;
}

function renderFilesBrowserCard() {
  if (!state.detail) {
    return "";
  }

  if (state.browserLoading) {
    return `
      <section class="detail-card stack files-browser-card">
        <div class="detail-header">
          <h3>Files</h3>
          <span class="badge">loading</span>
        </div>
        <p class="muted">Loading directory entries...</p>
      </section>
    `;
  }

  const crumbs = buildBrowserBreadcrumbs(state.browserPath)
    .map(
      (crumb) => `
        <button class="browser-crumb ${crumb.path === state.browserPath ? "active" : ""}" data-browser-path="${escapeHtml(crumb.path)}" type="button">
          ${escapeHtml(crumb.label)}
        </button>
      `
    )
    .join("");

  const upButton =
    state.browserPath && state.browserPath !== "."
      ? `<button class="button ghost browser-up" data-browser-path="${escapeHtml(state.browserPath)}" type="button">Up</button>`
      : "";

  const browserMarkup = state.browserEntries.length
    ? state.browserEntries
        .map((entry) => {
          const rowClass = entry.path === state.activeFilePath ? "browser-item active" : "browser-item";
          const entryAction =
            entry.type === "directory"
              ? "browser-dir"
              : "browser-file";
          const entryTone = entry.type === "directory" ? "directory" : "file";

          return `
            <div class="${rowClass}">
              <div>
                <button class="entry-title file-link ${entryAction}" data-path="${escapeHtml(entry.path)}" type="button">${escapeHtml(entry.name)}</button>
                <div class="entry-copy">${escapeHtml(entry.modified_at)}</div>
              </div>
              <div class="split-actions">
                <span class="chip">${escapeHtml(entryTone)}</span>
                ${entry.is_executable ? `<span class="chip ok">exec</span>` : ""}
                <span class="chip">${escapeHtml(String(entry.size))} B</span>
              </div>
            </div>
          `;
        })
        .join("")
    : `<p class="muted">Directory is empty.</p>`;

  return `
    <section class="detail-card stack files-browser-card">
      <div class="detail-header">
        <h3>Files</h3>
        <div class="split-actions">
          <span class="chip mono">${escapeHtml(state.browserPath)}</span>
          ${upButton}
        </div>
      </div>
      <div class="browser-breadcrumbs">${crumbs}</div>
      <div class="artifact-list">${browserMarkup}</div>
    </section>
  `;
}

function renderDetail() {
  if (!state.detail || !state.selected) {
    renderEmptyDetail();
    return;
  }

  const { summary, checkpoints, checkpoint_graph } = state.detail;
  const checkpointView = normalizeCheckpointGraph(checkpoint_graph, checkpoints);
  const previewableCount = previewablePaths(state.detail).length;
  const statusTone = summary.solve_status === "solved" ? "ok" : "warn";
  const challengeType = summary.challenge_type || "unknown";

  const checkpointMarkup = checkpointView.nodes.length
    ? checkpointView.nodes
        .map(
          (checkpoint) => `
            <div class="checkpoint-item">
              <div>
                <div class="entry-title">${escapeHtml(checkpoint.name)}</div>
                <div class="checkpoint-meta">
                  <span class="entry-copy mono">${escapeHtml(checkpoint.short_id || checkpoint.id.slice(0, 12))}</span>
                  <span class="entry-copy">${escapeHtml(checkpoint.created_at)}</span>
                </div>
              </div>
              <div class="checkpoint-actions">
                ${checkpoint.is_head ? `<span class="chip ok">head</span>` : ""}
                ${checkpoint.is_latest ? `<span class="chip ok">latest</span>` : ""}
              </div>
            </div>
          `
        )
        .join("")
    : `<p class="muted">No checkpoints yet.</p>`;

  elements.detail.innerHTML = `
    <section class="detail-card">
      <div class="detail-header">
        <div>
          <p class="eyebrow">Challenge</p>
          <h3>${escapeHtml(summary.name)}</h3>
          <p class="muted">${escapeHtml(summary.path)}</p>
        </div>
        <div class="split-actions">
          <span class="chip type">${escapeHtml(challengeType)}</span>
          <span class="chip ${statusTone}">${escapeHtml(summary.solve_status)}</span>
        </div>
        <button id="refresh-detail" class="button ghost" type="button">Refresh</button>
      </div>
      <div class="stats-grid">
        <div class="stat"><span class="meta">Checkpoints</span><strong>${summary.checkpoint_count}</strong></div>
        <div class="stat"><span class="meta">Type</span><strong>${escapeHtml(challengeType)}</strong></div>
        <div class="stat"><span class="meta">Artifacts</span><strong>${summary.artifact_count}</strong></div>
        <div class="stat"><span class="meta">Previewable</span><strong>${previewableCount}</strong></div>
      </div>
      ${renderFileShortcuts()}
    </section>

    <div class="detail-grid">
      <div class="stack content-column">
        ${renderFilePreviewCard()}
        <section class="detail-card saved-commits-card stack">
          <div class="detail-header">
            <h3>Saved commits</h3>
            <div class="checkpoint-summary">
              <span class="chip">${checkpointView.nodes.length} saved</span>
              <span class="chip ok">${summary.checkpoint_count} commits</span>
            </div>
          </div>
          <div class="checkpoints">${checkpointMarkup}</div>
        </section>
      </div>
      <div class="side-column">
        ${renderFilesBrowserCard()}
      </div>
    </div>
  `;
  document.querySelector("#refresh-detail")?.addEventListener("click", () => loadChallengeDetail(state.selected));
  document.querySelectorAll(".quick-file").forEach((button) => {
    button.addEventListener("click", () => loadFilePreview(button.dataset.quickFile));
  });
  document.querySelectorAll(".browser-file").forEach((button) => {
    button.addEventListener("click", () => loadFilePreview(button.dataset.path));
  });
  document.querySelectorAll(".browser-dir").forEach((button) => {
    button.addEventListener("click", () => loadBrowser(button.dataset.path));
  });
  document.querySelectorAll(".browser-crumb").forEach((button) => {
    button.addEventListener("click", () => loadBrowser(button.dataset.browserPath));
  });
  document.querySelector(".browser-up")?.addEventListener("click", () => {
    const current = state.browserPath;
    const parts = current.split("/").filter(Boolean);
    parts.pop();
    const nextPath = parts.length ? parts.join("/") : ".";
    loadBrowser(nextPath);
  });
}

async function loadChallenges({ preserveSelection = true } = {}) {
  const payload = await request("/api/challenges");
  state.challenges = payload.challenges;
  const visibleEvents = new Set(state.challenges.map(eventName));
  for (const event of visibleEvents) {
    if (event && !state.collapsedEvents.has(event)) {
      state.collapsedEvents.add(event);
    }
  }

  if (preserveSelection && state.selected && state.challenges.some((item) => item.name === state.selected)) {
    renderChallengeList();
    return;
  }

  state.selected = state.challenges[0]?.name || null;
  renderChallengeList();

  if (state.selected) {
    await loadChallengeDetail(state.selected);
  } else {
    state.detail = null;
    renderDetail();
  }
}

async function loadChallengeDetail(name) {
  if (!name) {
    return;
  }
  state.selected = name;
  state.filePreview = null;
  state.activeFilePath = null;
  state.filePreviewLoading = false;
  state.browserPath = ".";
  state.browserEntries = [];
  state.browserLoading = false;
  renderChallengeList();
  renderDetail();

  const payload = await request(`/api/challenges/${encodeURIComponent(name)}`);
  state.detail = payload.challenge;
  renderDetail();

  loadBrowser(".").catch((error) => {
    console.error(error);
  });

  const previewPath = preferredPreviewPath(state.detail);
  if (previewPath) {
    loadFilePreview(previewPath).catch((error) => {
      console.error(error);
    });
  }
}

async function loadFilePreview(path) {
  if (!state.selected || !path) {
    return;
  }

  state.activeFilePath = path;
  state.filePreviewLoading = true;
  renderDetail();

  try {
    const payload = await request(
      `/api/challenges/${encodeURIComponent(state.selected)}/file?path=${encodeURIComponent(path)}`
    );
    if (path !== state.activeFilePath) {
      return;
    }
    state.filePreview = payload.file;
  } catch (error) {
    showToast(error.message, "error");
    state.filePreview = null;
  } finally {
    state.filePreviewLoading = false;
    renderDetail();
  }
}

async function loadBrowser(path = ".") {
  if (!state.selected) {
    return;
  }

  state.browserPath = path || ".";
  state.browserLoading = true;
  renderDetail();

  try {
    const payload = await request(
      `/api/challenges/${encodeURIComponent(state.selected)}/file?path=${encodeURIComponent(state.browserPath)}`
    );
    if (payload.file.type !== "directory") {
      throw new Error("Browser path is not a directory.");
    }
    state.browserEntries = payload.file.entries;
    state.browserPath = payload.file.path || ".";
  } catch (error) {
    showToast(error.message, "error");
    state.browserEntries = [];
  } finally {
    state.browserLoading = false;
    renderDetail();
  }
}

async function selectChallenge(name) {
  if (name === state.selected && state.detail) {
    return;
  }
  try {
    await loadChallengeDetail(name);
  } catch (error) {
    showToast(error.message, "error");
  }
}

function bindEvents() {
  elements.themeToggle?.addEventListener("click", toggleTheme);
  elements.refreshList.addEventListener("click", () => {
    loadChallenges().catch((error) => showToast(error.message, "error"));
  });
  elements.filterInput.addEventListener("input", (event) => {
    state.filter = event.target.value;
    renderChallengeList();
  });
}

async function bootstrap() {
  applyTheme(preferredTheme());
  renderServerLabel();
  const systemTheme = window.matchMedia?.("(prefers-color-scheme: dark)");
  systemTheme?.addEventListener("change", syncSystemTheme);
  bindEvents();
  renderEmptyDetail();
  try {
    await loadChallenges({ preserveSelection: false });
  } catch (error) {
    console.error(error);
    showToast(error.message, "error");
  }
}

bootstrap();
