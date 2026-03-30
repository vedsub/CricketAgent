const form = document.getElementById("analysis-form");
const team1Select = document.getElementById("team1");
const team2Select = document.getElementById("team2");
const venueSelect = document.getElementById("venue");
const matchDateInput = document.getElementById("match-date");
const terminalSection = document.getElementById("terminal-section");
const terminal = document.getElementById("terminal");
const progressBar = document.getElementById("progress-bar");
const resultsSection = document.getElementById("results-section");
const runButton = document.getElementById("run-button");
const downloadButton = document.getElementById("download-json");
const bowlingTabs = document.getElementById("bowling-tabs");
const warningBanner = document.getElementById("warning-banner");

const API_BASE = window.location.origin;

let currentEventSource = null;
let currentReport = null;
let currentBowlingTab = "team1";
let currentWarnings = [];

document.addEventListener("DOMContentLoaded", async () => {
  setDefaultDate();
  bindEvents();
  await loadOptions();
});

function bindEvents() {
  form.addEventListener("submit", handleSubmit);
  downloadButton.addEventListener("click", downloadReport);
  bowlingTabs.addEventListener("click", (event) => {
    const button = event.target.closest(".tab-button");
    if (!button || !currentReport) {
      return;
    }

    currentBowlingTab = button.dataset.team;
    updateTabState();
    renderBowlingPlan(currentReport);
  });
}

async function loadOptions() {
  try {
    const [teams, venues] = await Promise.all([
      fetchJson(`${API_BASE}/teams`),
      fetchJson(`${API_BASE}/venues`),
    ]);

    populateSelect(team1Select, teams);
    populateSelect(team2Select, teams);
    team1Select.selectedIndex = 0;
    team2Select.selectedIndex = Math.min(1, teams.length - 1);

    venueSelect.innerHTML = venues
      .map(
        (venue, index) => `
          <option value="${escapeHtml(venue.name)}" ${index === 0 ? "selected" : ""}>
            ${escapeHtml(venue.name)} (${escapeHtml(venue.pitch_type)}, SR ${venue.sr_index})
          </option>
        `
      )
      .join("");
  } catch (error) {
    appendTerminalLine(`❌ Failed to load setup data — ${error.message}`);
    terminalSection.classList.remove("hidden");
  }
}

function populateSelect(selectNode, items) {
  selectNode.innerHTML = items
    .map(
      (item) => `
        <option value="${escapeHtml(item)}">${escapeHtml(item)}</option>
      `
    )
    .join("");
}

function setDefaultDate() {
  const today = new Date();
  const day = today.getDay();
  const daysUntilSaturday = ((6 - day + 7) % 7) || 7;
  const nextSaturday = new Date(today);
  nextSaturday.setDate(today.getDate() + daysUntilSaturday);
  matchDateInput.value = nextSaturday.toISOString().split("T")[0];
}

async function handleSubmit(event) {
  event.preventDefault();

  const payload = {
    team1: team1Select.value,
    team2: team2Select.value,
    venue: venueSelect.value,
    match_date: matchDateInput.value,
  };

  if (payload.team1 === payload.team2) {
    window.alert("Choose two different teams for the matchup.");
    return;
  }

  resetRunState();
  runButton.disabled = true;
  terminalSection.classList.remove("hidden");
  appendTerminalLine(`⚙️ Booting graph for ${payload.team1} vs ${payload.team2} at ${payload.venue}`);

  const params = new URLSearchParams(payload);
  currentEventSource = new EventSource(`${API_BASE}/analyze/stream?${params.toString()}`);

  currentEventSource.onmessage = (message) => {
    const data = JSON.parse(message.data);
    updateProgress(data.progress ?? 0);

    if (data.layer === "complete" || data.status === "done") {
      appendTerminalLine("✅ Layer 4 - Coach Final Synthesis — Final report ready");
      currentReport = data.report;
      currentWarnings = data.errors || currentWarnings;
      currentEventSource.close();
      currentEventSource = null;
      finishRun(data.report, currentWarnings);
      return;
    }

    currentWarnings = data.warnings || currentWarnings;
    appendTerminalLine(`✅ ${data.layer} — ${data.summary}`);
  };

  currentEventSource.onerror = () => {
    appendTerminalLine("❌ Stream interrupted. Check the API server and try again.");
    if (currentEventSource) {
      currentEventSource.close();
      currentEventSource = null;
    }
    runButton.disabled = false;
  };
}

function resetRunState() {
  if (currentEventSource) {
    currentEventSource.close();
    currentEventSource = null;
  }

  currentReport = null;
  currentBowlingTab = "team1";
  currentWarnings = [];
  terminal.innerHTML = "";
  progressBar.style.width = "0%";
  resultsSection.classList.add("hidden");
  warningBanner.classList.add("hidden");
  warningBanner.textContent = "";
}

function finishRun(report, warnings) {
  runButton.disabled = false;
  terminalSection.classList.add("hidden");
  resultsSection.classList.remove("hidden");
  updateTabState();
  renderWarnings(warnings || []);
  renderReport(report);
}

function updateProgress(value) {
  progressBar.style.width = `${Math.max(0, Math.min(100, value))}%`;
}

function appendTerminalLine(text) {
  const line = document.createElement("div");
  line.className = "terminal-line";
  line.textContent = text;
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

function renderReport(report) {
  renderOverview(report);
  renderToss(report);
  renderXI("team1", report.team1_playing_xi || [], report);
  renderXI("team2", report.team2_playing_xi || [], report);
  renderMatchups(report.key_matchups || []);
  renderBowlingPlan(report);
  renderTarget(report);
}

function renderWarnings(warnings) {
  if (!warnings.length) {
    warningBanner.classList.add("hidden");
    warningBanner.textContent = "";
    return;
  }

  warningBanner.classList.remove("hidden");
  warningBanner.textContent = `Warning: ${warnings.join(" | ")}`;
}

function renderOverview(report) {
  const container = document.getElementById("match-overview");
  container.innerHTML = `
    <div class="overview-matchup">${escapeHtml(report.match || "Match Overview")}</div>
    <div class="overview-meta">
      <div>${escapeHtml(report.venue || "Venue TBD")}</div>
      <div>${formatDate(report.date)}</div>
    </div>
    <div class="badge-row">
      <span class="badge badge-accent">${escapeHtml((report.pitch_type || "balanced").toUpperCase())}</span>
      <span class="badge">${escapeHtml(report.dom_type || "balanced conditions")}</span>
    </div>
  `;
}

function renderToss(report) {
  const toss = report.toss_recommendation || {};
  const confidence = Math.round((Number(toss.confidence) || 0) * 100);
  const container = document.getElementById("toss-card");

  container.innerHTML = `
    <div class="toss-decision">${escapeHtml((toss.decision || "TBD").toUpperCase())}</div>
    <div class="confidence-shell">
      <div class="confidence-fill" style="width: ${confidence}%"></div>
    </div>
    <div>${confidence}% confidence</div>
    <p class="toss-reasoning">${escapeHtml(toss.reasoning || "Awaiting toss recommendation.")}</p>
  `;
}

function renderXI(teamKey, players, report) {
  const titleNode = document.getElementById(`${teamKey}-xi-title`);
  const container = document.getElementById(`${teamKey}-xi-card`);
  const impact = report[`${teamKey}_impact_player`];
  const teamLabel = teamKey === "team1" ? getTeamNameFromMatch(report.match, 0) : getTeamNameFromMatch(report.match, 1);

  titleNode.textContent = `${teamLabel} Playing XI`;

  const impactMarkup = impact
    ? `
      <div class="xi-impact">
        <div class="impact-badge">⚡ Impact Player</div>
        <div><strong>${escapeHtml(impact.player || "TBD")}</strong> (${escapeHtml(impact.role || "role flexible")})</div>
        <div class="overview-meta">${escapeHtml(impact.use_case || "Use based on match situation.")}</div>
      </div>
    `
    : "";

  const rows = players
    .map(
      (player) => `
        <tr>
          <td>${player.batting_position ?? "-"}</td>
          <td>${escapeHtml(player.name || "")}</td>
          <td><span class="role-pill">${escapeHtml(player.role || "")}</span></td>
          <td>${escapeHtml(player.reason || "")}</td>
        </tr>
      `
    )
    .join("");

  container.innerHTML = `
    ${impactMarkup}
    <table class="xi-table">
      <thead>
        <tr>
          <th>Position</th>
          <th>Player</th>
          <th>Role</th>
          <th>Reason</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderMatchups(matchups) {
  const container = document.getElementById("matchups-grid");

  if (!matchups.length) {
    container.innerHTML = `<div class="empty-state">No key matchups were returned for this report.</div>`;
    return;
  }

  container.innerHTML = matchups
    .map((matchup) => {
      const type = matchup.matchup_type === "danger" ? "danger" : matchup.matchup_type === "exploit" ? "exploit" : "neutral";
      const tagLabel = type === "danger" ? "🔴 DANGER" : type === "exploit" ? "🟢 EXPLOIT" : "⚪ NEUTRAL";
      return `
        <div class="matchup-card ${type}">
          <div class="matchup-top">
            <div class="matchup-side">
              <div class="avatar">${initials(matchup.batter)}</div>
              <div class="player-name">${escapeHtml(matchup.batter)}</div>
            </div>
            <div class="versus">vs</div>
            <div class="matchup-side">
              <div class="avatar">${initials(matchup.bowler)}</div>
              <div class="player-name">${escapeHtml(matchup.bowler)}</div>
            </div>
          </div>
          <div class="matchup-stats">SR: ${escapeHtml(String(matchup.strike_rate))} | W: ${escapeHtml(String(matchup.wickets))} | ${escapeHtml(String(matchup.balls))}b</div>
          <div class="matchup-tag ${type}">${tagLabel}</div>
        </div>
      `;
    })
    .join("");
}

function renderBowlingPlan(report) {
  const container = document.getElementById("bowling-plan-content");
  const teamName = currentBowlingTab === "team1" ? getTeamNameFromMatch(report.match, 0) : getTeamNameFromMatch(report.match, 1);
  const plan = currentBowlingTab === "team1" ? report.team1_bowling_plan : report.team2_bowling_plan;
  const overPlan = plan?.over_plan || null;

  if (!overPlan) {
    container.innerHTML = `
      <div class="timeline-note">
        ${escapeHtml(teamName)} does not have an over-by-over plan in the current report. ${escapeHtml(plan?.plan || "Only a high-level bowling note is available.")}
      </div>
    `;
    return;
  }

  const blocks = Array.from({ length: 20 }, (_, index) => {
    const over = index + 1;
    const bowler = overPlan[String(over)] || "TBD";
    const phase = over <= 6 ? "powerplay" : over <= 15 ? "middle" : "death";
    return `
      <div class="over-block ${phase}" title="${escapeHtml(bowler)}">
        <span class="over-number">Over ${over}</span>
        <span class="over-bowler">${escapeHtml(bowler)}</span>
      </div>
    `;
  }).join("");

  container.innerHTML = `
    <div class="overview-meta">${escapeHtml(teamName)} bowling plan</div>
    <div class="timeline-grid">${blocks}</div>
    <div class="timeline-legend">
      <span class="legend-item"><span class="legend-swatch swatch-powerplay"></span>Powerplay</span>
      <span class="legend-item"><span class="legend-swatch swatch-middle"></span>Middle</span>
      <span class="legend-item"><span class="legend-swatch swatch-death"></span>Death</span>
    </div>
  `;
}

function renderTarget(report) {
  const container = document.getElementById("target-card");
  container.innerHTML = `
    <div class="target-number">${escapeHtml(String(report.first_innings_target || "-"))}</div>
    <div class="target-subtext">Based on venue SR index and team form</div>
    <p class="overview-meta">${escapeHtml(report.batting_summary || "Batting summary unavailable.")}</p>
  `;
}

function updateTabState() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.team === currentBowlingTab);
  });
}

function downloadReport() {
  if (!currentReport) {
    return;
  }

  const blob = new Blob([JSON.stringify(currentReport, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `cricket-intelligence-${slugify(currentReport.match || "report")}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}

function getTeamNameFromMatch(match, index) {
  const teams = String(match || "").split(" vs ").map((item) => item.trim()).filter(Boolean);
  return teams[index] || `Team ${index + 1}`;
}

function formatDate(dateValue) {
  if (!dateValue) {
    return "Date TBD";
  }

  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) {
    return dateValue;
  }

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function initials(name) {
  return String(name || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

function slugify(value) {
  return String(value).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
