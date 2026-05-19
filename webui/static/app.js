const CORE_DOCUMENTS = ["STATE.md", "FACTS.md", ".ctf-files", ".pwnrun"];

const state = {
  challenges: [],
  filter: "",
  selected: null,
  detail: null,
  activeDocument: "STATE.md",
  drafts: {},
  runInfo: null,
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

function currentDraft() {
  if (!state.selected) {
    return "";
  }
  const challengeDrafts = state.drafts[state.selected] || {};
  return challengeDrafts[state.activeDocument] ?? "";
}

function setCurrentDraft(content) {
  if (!state.selected) {
    return;
  }
  if (!state.drafts[state.selected]) {
    state.drafts[state.selected] = {};
  }
  state.drafts[state.selected][state.activeDocument] = content;
}

function syncDraftsFromDetail() {
  if (!state.selected || !state.detail) {
    return;
  }
  state.drafts[state.selected] = { ...state.detail.documents };
}

function filteredChallenges() {
  const needle = state.filter.trim().toLowerCase();
  if (!needle) {
    return state.challenges;
  }
  return state.challenges.filter((challenge) => challenge.name.toLowerCase().includes(needle));
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

  elements.challengeList.innerHTML = items
    .map((challenge) => {
      const badges = [
        challenge.initialized ? `<span class="chip ok">initialized</span>` : `<span class="chip warn">not init</span>`,
        `<span class="chip">${challenge.checkpoint_count} cp</span>`,
        `<span class="chip">${challenge.artifact_count} files</span>`,
      ].join("");

      return `
        <button class="challenge-card ${challenge.name === state.selected ? "active" : ""}" data-name="${escapeHtml(challenge.name)}" type="button">
          <div class="challenge-card-title">
            <strong>${escapeHtml(challenge.name)}</strong>
            <span class="meta">${escapeHtml(challenge.updated_at.slice(5, 16).replace("T", " "))}</span>
          </div>
          <div class="challenge-card-badges">${badges}</div>
          <p class="meta">${escapeHtml(challenge.path)}</p>
        </button>
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
        <p class="muted">The right pane will show docs, checkpoints, runtime info, and filesystem state.</p>
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
        <pre class="doc-editor mono">${escapeHtml((runInfo.stderr || runInfo.stdout || "No output").trim())}</pre>
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

function renderDetail() {
  if (!state.detail || !state.selected) {
    renderEmptyDetail();
    return;
  }

  const { summary, checkpoints, attempts, artifacts } = state.detail;
  const docTabs = CORE_DOCUMENTS.map(
    (name) => `
      <button class="tab ${name === state.activeDocument ? "active" : ""}" data-doc="${escapeHtml(name)}" type="button">
        ${escapeHtml(name)}
      </button>
    `
  ).join("");

  const checkpointMarkup = checkpoints.length
    ? checkpoints
        .map(
          (checkpoint) => `
            <div class="checkpoint-item">
              <div>
                <div class="entry-title">${escapeHtml(checkpoint.name)}</div>
                <div class="entry-copy mono">${escapeHtml(checkpoint.id)}</div>
                <div class="entry-copy">${escapeHtml(checkpoint.created_at)}</div>
              </div>
              <div class="split-actions">
                ${checkpoint.is_latest ? `<span class="chip ok">latest</span>` : ""}
                <button class="button ghost checkpoint-restore" data-checkpoint="${escapeHtml(checkpoint.id)}" type="button">Restore</button>
              </div>
            </div>
          `
        )
        .join("")
    : `<p class="muted">No checkpoints yet.</p>`;

  const artifactMarkup = artifacts.length
    ? artifacts
        .map(
          (artifact) => `
            <div class="artifact-item">
              <div>
                <div class="entry-title">${escapeHtml(artifact.name)}</div>
                <div class="entry-copy">${escapeHtml(artifact.modified_at)}</div>
              </div>
              <div class="split-actions">
                <span class="chip">${escapeHtml(artifact.type)}</span>
                ${artifact.is_executable ? `<span class="chip ok">exec</span>` : ""}
                <span class="chip">${escapeHtml(String(artifact.size))} B</span>
              </div>
            </div>
          `
        )
        .join("")
    : `<p class="muted">No top-level files.</p>`;

  const attemptMarkup = attempts.length
    ? attempts
        .map(
          (attempt) => `
            <div class="attempt-item">
              <div>
                <div class="entry-title">${escapeHtml(attempt.name)}</div>
                <div class="entry-copy">${escapeHtml(attempt.modified_at)}</div>
              </div>
              <span class="chip">${escapeHtml(String(attempt.size))} B</span>
            </div>
          `
        )
        .join("")
    : `<p class="muted">No attempt notes.</p>`;

  elements.detail.innerHTML = `
    <section class="detail-card">
      <div class="detail-header">
        <div>
          <p class="eyebrow">Challenge</p>
          <h3>${escapeHtml(summary.name)}</h3>
          <p class="muted">${escapeHtml(summary.path)}</p>
        </div>
        <div class="detail-actions split-actions">
          <button id="init-challenge" class="button secondary" type="button">Init Files</button>
          <button id="refresh-detail" class="button ghost" type="button">Refresh</button>
        </div>
      </div>
      <div class="stats-grid">
        <div class="stat"><span class="meta">Checkpoints</span><strong>${summary.checkpoint_count}</strong></div>
        <div class="stat"><span class="meta">Attempts</span><strong>${summary.attempt_count}</strong></div>
        <div class="stat"><span class="meta">Artifacts</span><strong>${summary.artifact_count}</strong></div>
        <div class="stat"><span class="meta">Core Files</span><strong>${Object.values(summary.core_files).filter(Boolean).length}/${CORE_DOCUMENTS.length}</strong></div>
      </div>
    </section>

    <div class="detail-grid">
      <section class="detail-card stack">
        <div class="doc-header">
          <div>
            <h3>Core Documents</h3>
            <p class="muted">Edit state, facts, manifest, and run config in place.</p>
          </div>
          <button id="save-document" class="button primary" type="button">Save ${escapeHtml(state.activeDocument)}</button>
        </div>
        <div class="tabs">${docTabs}</div>
        <textarea id="doc-editor" class="doc-editor" spellcheck="false">${escapeHtml(currentDraft())}</textarea>
      </section>

      <div class="stack">
        ${renderRunInfoCard()}

        <section class="detail-card stack">
          <div class="detail-header">
            <h3>Checkpoint Control</h3>
            <span class="chip">${checkpoints.length} saved</span>
          </div>
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
    </div>

    <div class="detail-grid">
      <section class="detail-card stack">
        <div class="detail-header">
          <h3>Top-Level Files</h3>
          <span class="chip">${artifacts.length} entries</span>
        </div>
        <div class="artifact-list">${artifactMarkup}</div>
      </section>

      <section class="detail-card stack">
        <div class="detail-header">
          <h3>Attempt Notes</h3>
          <span class="chip">${attempts.length} entries</span>
        </div>
        <div class="attempt-list">${attemptMarkup}</div>
      </section>
    </div>
  `;

  elements.detail.querySelectorAll("[data-doc]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeDocument = button.dataset.doc;
      renderDetail();
    });
  });

  const editor = document.querySelector("#doc-editor");
  editor?.addEventListener("input", (event) => {
    setCurrentDraft(event.target.value);
  });

  document.querySelector("#save-document")?.addEventListener("click", saveActiveDocument);
  document.querySelector("#init-challenge")?.addEventListener("click", initializeSelectedChallenge);
  document.querySelector("#refresh-detail")?.addEventListener("click", () => loadChallengeDetail(state.selected));
  document.querySelector("#checkpoint-form")?.addEventListener("submit", createCheckpoint);
  document.querySelectorAll(".checkpoint-restore").forEach((button) => {
    button.addEventListener("click", () => restoreCheckpoint(button.dataset.checkpoint));
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
  renderChallengeList();
  renderDetail();

  const payload = await request(`/api/challenges/${encodeURIComponent(name)}`);
  state.detail = payload.challenge;
  syncDraftsFromDetail();
  renderDetail();

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
    showToast("Challenge name is required.", "error");
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
    syncDraftsFromDetail();
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

async function saveActiveDocument() {
  if (!state.selected) {
    return;
  }

  const button = document.querySelector("#save-document");
  setBusy(button, true);
  try {
    const payload = await request(
      `/api/challenges/${encodeURIComponent(state.selected)}/document?name=${encodeURIComponent(state.activeDocument)}`,
      {
        method: "PUT",
        body: JSON.stringify({ content: currentDraft() }),
      }
    );
    state.detail = payload.challenge;
    syncDraftsFromDetail();
    showToast(`Saved ${state.activeDocument}`, "success");
    await loadChallenges();
    renderDetail();
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
  const confirmed = window.confirm(`Restore checkpoint ${checkpoint}? This will overwrite tracked files in the challenge directory.`);
  if (!confirmed) {
    return;
  }

  try {
    const payload = await request(`/api/challenges/${encodeURIComponent(state.selected)}/restore`, {
      method: "POST",
      body: JSON.stringify({ checkpoint }),
    });
    state.detail = payload.challenge;
    syncDraftsFromDetail();
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
