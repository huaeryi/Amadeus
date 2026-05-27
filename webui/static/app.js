const state = {
  challenges: [],
  filter: "",
  selected: null,
  detail: null,
  runInfo: null,
  filePreview: null,
  activeFilePath: null,
  filePreviewLoading: false,
  browserPath: ".",
  browserEntries: [],
  browserLoading: false,
};

const elements = {
  createForm: document.querySelector("#create-form"),
  createName: document.querySelector("#create-name"),
  refreshList: document.querySelector("#refresh-list"),
  filterInput: document.querySelector("#challenge-filter"),
  challengeList: document.querySelector("#challenge-list"),
  detail: document.querySelector("#detail"),
  toastLayer: document.querySelector("#toast-layer"),
};

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

function setBusy(target, busy) {
  if (!target) {
    return;
  }
  target.disabled = busy;
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

  const preferred = ["exp.py", "solve.py", "wp.md", "metadata.json", "exp_template.py", "README.md"];
  for (const name of preferred) {
    if (paths.includes(name)) {
      return name;
    }
  }

  return paths[0];
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

function renderCheckpointGraph(checkpointGraph, checkpoints) {
  const { nodes, edges } = normalizeCheckpointGraph(checkpointGraph, checkpoints);
  if (!nodes.length) {
    return `
      <div class="checkpoint-graph">
        <div class="checkpoint-graph-empty">No checkpoints</div>
      </div>
    `;
  }

  const sorted = nodes;
  const childMap = new Map();
  for (const edge of edges) {
    if (!childMap.has(edge.parent)) {
      childMap.set(edge.parent, []);
    }
    childMap.get(edge.parent).push(edge.child);
  }

  const columnById = new Map();
  let nextColumn = 0;
  for (const node of sorted) {
    if (columnById.has(node.id)) {
      continue;
    }
    if (!node.parent_id || !columnById.has(node.parent_id)) {
      columnById.set(node.id, nextColumn++);
      continue;
    }

    const siblings = childMap.get(node.parent_id) || [];
    const siblingIndex = siblings.indexOf(node.id);
    if (siblingIndex <= 0) {
      columnById.set(node.id, columnById.get(node.parent_id));
    } else {
      columnById.set(node.id, nextColumn++);
    }
  }

  const rowById = new Map(sorted.map((node, index) => [node.id, index]));
  const maxColumn = Math.max(...columnById.values(), 0);
  const xStep = 110;
  const yStep = 72;
  const left = 24;
  const top = 22;
  const width = left + maxColumn * xStep + 320;
  const height = top + Math.max(0, sorted.length - 1) * yStep + 42;
  const nodeRadius = 8;
  const edgeGap = 8;

  const edgeMarkup = edges
    .filter((edge) => rowById.has(edge.parent) && rowById.has(edge.child))
    .map((edge) => {
      const parentX = left + columnById.get(edge.parent) * xStep;
      const parentY = top + rowById.get(edge.parent) * yStep;
      const childX = left + columnById.get(edge.child) * xStep;
      const childY = top + rowById.get(edge.child) * yStep;
      const midY = parentY + (childY - parentY) / 2;
      const deltaX = childX - parentX;
      const deltaY = childY - parentY;

      if (deltaX === 0) {
        const directionY = Math.sign(deltaY) || 1;
        const endY = childY - directionY * (nodeRadius + edgeGap);
        return `<path class="checkpoint-svg-edge" marker-end="url(#checkpoint-arrow)" d="M ${parentX} ${parentY} L ${parentX} ${midY} L ${childX} ${endY}" />`;
      }

      const directionX = Math.sign(deltaX) || 1;
      const endX = childX - directionX * (nodeRadius + edgeGap);
      return `<path class="checkpoint-svg-edge" marker-end="url(#checkpoint-arrow)" d="M ${parentX} ${parentY} L ${parentX} ${midY} L ${endX} ${midY} L ${endX} ${childY}" />`;
    })
    .join("");

  const nodeMarkup = sorted
    .map((node) => {
      const x = left + columnById.get(node.id) * xStep;
      const y = top + rowById.get(node.id) * yStep;
      const classes = [
        "checkpoint-svg-node",
        node.is_head ? "head" : "",
        node.is_latest ? "latest" : "",
      ]
        .filter(Boolean)
        .join(" ");
      const branchText = (childMap.get(node.id) || []).length > 1 ? "branch" : "";
      const badges = [node.is_head ? "head" : "", node.is_latest ? "latest" : "", branchText]
        .filter(Boolean)
        .join(" · ");
      const created = node.created_at ? node.created_at.slice(5, 16).replace("T", " ") : "";
      const commit = node.short_id || node.id.slice(0, 7);

      return `
        <g class="${classes}" transform="translate(${x}, ${y})">
          <circle class="checkpoint-svg-dot" r="8"></circle>
          <text class="checkpoint-svg-title" x="18" y="-2">${escapeHtml(node.name)}</text>
          <text class="checkpoint-svg-meta" x="18" y="14">${escapeHtml(commit)} · ${escapeHtml(created)}${badges ? ` · ${escapeHtml(badges)}` : ""}</text>
        </g>
      `;
    })
    .join("");

  return `
    <div class="checkpoint-graph">
      <svg class="checkpoint-graph-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMinYMin meet">
        <defs>
          <marker id="checkpoint-arrow" markerWidth="5" markerHeight="5" refX="4.4" refY="2.5" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L5,2.5 L0,5 z" fill="rgba(19, 33, 47, 0.36)"></path>
          </marker>
        </defs>
        ${edgeMarkup}
        ${nodeMarkup}
      </svg>
    </div>
  `;
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

function renderChallengeList() {
  const items = filteredChallenges();
  if (!items.length) {
    elements.challengeList.innerHTML = `
      <div class="empty-state">
        <div>
          <h3>No matches</h3>
          <p class="muted">Create a new challenge or clear the filter.</p>
        </div>
      </div>
    `;
    return;
  }

  elements.challengeList.innerHTML = groupChallenges(items)
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
        <p class="muted">The right pane will show file previews, checkpoints, runtime info, and filesystem state.</p>
      </div>
    </section>
  `;
}

function renderRunInfoCard() {
  const runInfo = state.runInfo;
  if (!runInfo) {
    return `
      <section class="detail-card stack">
        <div class="detail-header">
          <h3>Run Info</h3>
          <span class="badge">loading</span>
        </div>
        <p class="muted">Resolving binary, libc, ld, and host/port information...</p>
      </section>
    `;
  }

  if (!runInfo.ok) {
    return `
      <section class="detail-card stack">
        <div class="detail-header">
          <h3>Run Info</h3>
          <span class="chip danger">script error</span>
        </div>
        <p class="muted">run_pwn.sh info did not resolve cleanly.</p>
        <pre class="file-preview">${escapeHtml((runInfo.stderr || runInfo.stdout || "No output").trim())}</pre>
      </section>
    `;
  }

  const fields = Object.entries(runInfo.info)
    .map(
      ([key, value]) => `
        <div class="runtime-field">
          <span>${escapeHtml(key)}</span>
          <strong>${escapeHtml(value || "-")}</strong>
        </div>
      `
    )
    .join("");

  return `
    <section class="detail-card stack">
      <div class="detail-header">
        <h3>Run Info</h3>
        <span class="chip ok">resolved</span>
      </div>
      <div class="runtime-grid">${fields || `<p class="muted">No run metadata.</p>`}</div>
    </section>
  `;
}

function renderFilePreviewCard() {
  if (!state.detail) {
    return "";
  }

  if (state.filePreviewLoading) {
    return `
      <section class="detail-card stack">
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
      <section class="detail-card stack">
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
      <section class="detail-card stack">
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
        <div class="stack">${entries}</div>
      </section>
    `;
  }

  const kindChip = state.filePreview.preview_kind === "binary" ? "binary" : "text";
  const truncateChip = state.filePreview.truncated
    ? `<span class="chip warn">preview capped at ${escapeHtml(String(state.filePreview.preview_limit))} B</span>`
    : "";

  return `
    <section class="detail-card stack">
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
      <section class="detail-card stack">
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
    <section class="detail-card stack">
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

  const { summary, checkpoints, checkpoint_graph, artifacts } = state.detail;
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
                <div class="entry-copy mono">${escapeHtml(checkpoint.short_id || checkpoint.id.slice(0, 12))}</div>
                <div class="entry-copy">${escapeHtml(checkpoint.created_at)}</div>
              </div>
              <div class="split-actions">
                ${checkpoint.is_latest ? `<span class="chip ok">latest</span>` : ""}
                <button class="button ghost checkpoint-restore" data-checkpoint="${escapeHtml(checkpoint.id)}" type="button">Restore Files</button>
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
        <div class="detail-actions split-actions">
          <button id="init-challenge" class="button secondary" type="button">Init Files</button>
          <button id="refresh-detail" class="button ghost" type="button">Refresh</button>
        </div>
      </div>
      <div class="stats-grid">
        <div class="stat"><span class="meta">Checkpoints</span><strong>${summary.checkpoint_count}</strong></div>
        <div class="stat"><span class="meta">Type</span><strong>${escapeHtml(challengeType)}</strong></div>
        <div class="stat"><span class="meta">Artifacts</span><strong>${summary.artifact_count}</strong></div>
        <div class="stat"><span class="meta">Previewable</span><strong>${previewableCount}</strong></div>
      </div>
    </section>

    <div class="detail-grid">
      ${renderFilePreviewCard()}
      ${renderFilesBrowserCard()}
    </div>

    <div class="detail-grid">
      <div class="stack">
        ${renderRunInfoCard()}

        <section class="detail-card stack">
          <div class="detail-header">
            <h3>Checkpoint Control</h3>
            <span class="chip">${checkpointView.nodes.length} saved</span>
          </div>
          ${renderCheckpointGraph(checkpoint_graph, checkpoints)}
          <form id="checkpoint-form" class="stack">
            <label class="field">
              <span>Checkpoint name</span>
              <input id="checkpoint-name" type="text" placeholder="primitive-confirmed" autocomplete="off" />
            </label>
            <button class="button primary" type="submit">Create Checkpoint</button>
          </form>
          <div class="checkpoints">${checkpointMarkup}</div>
        </section>
      </div>
      <section class="detail-card stack">
        <div class="detail-header">
          <h3>Workspace</h3>
          <span class="chip">${summary.artifact_count} root entries</span>
        </div>
        <div class="stats-grid">
          <div class="stat"><span class="meta">Root Entries</span><strong>${summary.artifact_count}</strong></div>
          <div class="stat"><span class="meta">Previewable</span><strong>${previewableCount}</strong></div>
        </div>
        <p class="muted">Use the file browser above to inspect nested directories; checkpoints are stored as git commits in the challenge directory.</p>
      </section>
    </div>
  `;
  document.querySelector("#init-challenge")?.addEventListener("click", initializeSelectedChallenge);
  document.querySelector("#refresh-detail")?.addEventListener("click", () => loadChallengeDetail(state.selected));
  document.querySelector("#checkpoint-form")?.addEventListener("submit", createCheckpoint);
  document.querySelectorAll(".checkpoint-restore").forEach((button) => {
    button.addEventListener("click", () => restoreCheckpoint(button.dataset.checkpoint));
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
    state.runInfo = null;
    renderDetail();
  }
}

async function loadChallengeDetail(name) {
  if (!name) {
    return;
  }
  state.selected = name;
  state.runInfo = null;
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

  loadRunInfo(name).catch((error) => {
    console.error(error);
  });
}

async function loadRunInfo(name) {
  const payload = await request(`/api/challenges/${encodeURIComponent(name)}/run-info`);
  if (state.selected !== name) {
    return;
  }
  state.runInfo = payload.run_info;
  renderDetail();
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

async function createChallenge(event) {
  event.preventDefault();
  const name = elements.createName.value.trim();
  if (!name) {
    showToast("Challenge path is required.", "error");
    return;
  }
  if (name.split("/").filter(Boolean).length !== 2) {
    showToast("Use a grouped path like defcon/baby_heap.", "error");
    return;
  }

  const button = elements.createForm.querySelector("button[type=submit]");
  setBusy(button, true);
  try {
    await request("/api/challenges", {
      method: "POST",
      body: JSON.stringify({ name, initialize: true }),
    });
    elements.createName.value = "";
    showToast(`Created ${name}`, "success");
    await loadChallenges({ preserveSelection: false });
    await loadChallengeDetail(name);
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function initializeSelectedChallenge() {
  if (!state.selected) {
    return;
  }
  const button = document.querySelector("#init-challenge");
  setBusy(button, true);
  try {
    const payload = await request(`/api/challenges/${encodeURIComponent(state.selected)}/init`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    state.detail = payload.challenge;
    showToast(`Initialized ${state.selected}`, "success");
    await loadChallenges();
    renderDetail();
    await loadRunInfo(state.selected);
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function createCheckpoint(event) {
  event.preventDefault();
  if (!state.selected) {
    return;
  }

  const input = document.querySelector("#checkpoint-name");
  const name = input?.value.trim();
  if (!name) {
    showToast("Checkpoint name is required.", "error");
    return;
  }

  const button = event.currentTarget.querySelector("button[type=submit]");
  setBusy(button, true);
  try {
    const payload = await request(`/api/challenges/${encodeURIComponent(state.selected)}/checkpoints`, {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    state.detail = payload.challenge;
    input.value = "";
    showToast(`Checkpoint ${name} created`, "success");
    await loadChallenges();
    renderDetail();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function restoreCheckpoint(checkpoint) {
  if (!state.selected || !checkpoint) {
    return;
  }
  const confirmed = window.confirm(`Restore tracked files from git checkpoint ${checkpoint.slice(0, 12)}?`);
  if (!confirmed) {
    return;
  }

  try {
    const payload = await request(`/api/challenges/${encodeURIComponent(state.selected)}/restore`, {
      method: "POST",
      body: JSON.stringify({ checkpoint }),
    });
    state.detail = payload.challenge;
    showToast(`Restored ${checkpoint}`, "success");
    await loadChallenges();
    renderDetail();
    await loadRunInfo(state.selected);
  } catch (error) {
    showToast(error.message, "error");
  }
}

function bindEvents() {
  elements.createForm.addEventListener("submit", createChallenge);
  elements.refreshList.addEventListener("click", () => {
    loadChallenges().catch((error) => showToast(error.message, "error"));
  });
  elements.filterInput.addEventListener("input", (event) => {
    state.filter = event.target.value;
    renderChallengeList();
  });
}

async function bootstrap() {
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
