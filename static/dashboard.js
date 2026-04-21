// dashboard.js — Frontend logic for /dashboard

const imgModal = new bootstrap.Modal(document.getElementById("imgModal"));

// ── Stats ─────────────────────────────────────────────────────

async function fetchStats() {
  try {
    const res  = await fetch("/api/stats");
    const data = await res.json();

    document.getElementById("stat-detections").textContent = data.total_detections ?? "—";
    document.getElementById("stat-vlm-no").textContent     = data.vlm_no_count ?? "—";

    const models = data.models || [];
    document.getElementById("stat-models").textContent      = models.length;
    document.getElementById("stat-models-list").textContent = models.join(", ") || "none yet";
  } catch (e) {
    console.error("fetchStats failed:", e);
  }
}

// ── Image preview ─────────────────────────────────────────────

function openImageB64(b64, caption) {
  document.getElementById("modal-preview").src = "data:image/jpeg;base64," + b64;
  document.getElementById("modal-caption").textContent = caption || "";
  document.getElementById("modal-title").textContent   = "Image Preview";
  imgModal.show();
}

function openImageUrl(url, caption) {
  document.getElementById("modal-preview").src = url;
  document.getElementById("modal-caption").textContent = caption || "";
  document.getElementById("modal-title").textContent   = "Image Preview";
  imgModal.show();
}

// ── YOLO Detections ───���───────────────────────────────────────

async function loadDetections() {
  const tbody = document.getElementById("detections-tbody");
  tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Loading...</td></tr>';

  const params = new URLSearchParams();
  const defectType = document.getElementById("f-defect-type").value.trim();
  const start      = document.getElementById("f-start").value;
  const end        = document.getElementById("f-end").value;

  if (defectType) params.set("defect_type", defectType);
  if (start)      params.set("start",       start.replace("T", " "));
  if (end)        params.set("end",         end.replace("T", " "));

  try {
    const res  = await fetch("/api/detections?" + params);
    const rows = await res.json();

    if (!rows.length) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No detections found.</td></tr>';
      return;
    }

    tbody.innerHTML = rows.map(r => {
      const imgSrc  = r.image ? `data:image/jpeg;base64,${r.image}` : null;
      const imgCell = imgSrc
        ? `<img class="thumb" src="${imgSrc}" alt="img"
              onclick="openImageB64('${r.image}', '${r.defect_type} | ${r.model_name || ""} | conf ${r.confidence}')">`
        : '<span style="color:#475569;font-size:12px">no image</span>';

      const conf = r.confidence != null
        ? `<span style="color:${r.confidence >= 0.7 ? '#34d399' : r.confidence >= 0.4 ? '#fb923c' : '#f87171'};font-weight:600">${r.confidence.toFixed(3)}</span>`
        : "—";

      return `<tr>
        <td style="color:#475569">${r.id}</td>
        <td><span class="badge-type">${r.defect_type || "—"}</span></td>
        <td>${conf}</td>
        <td style="color:#94a3b8">${r.model_name || "—"}</td>
        <td style="color:#64748b;font-size:12px">${r.timestamp || "—"}</td>
        <td>${imgCell}</td>
      </tr>`;
    }).join("");

  } catch (e) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Error loading data.</td></tr>';
    console.error("loadDetections failed:", e);
  }
}

// ── VLM Rejections ────────────────────────────────────────────

async function loadVlmNo() {
  const tbody = document.getElementById("vlm-no-tbody");
  tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Loading...</td></tr>';

  const params = new URLSearchParams();
  const defectType = document.getElementById("f-vlm-defect").value.trim();
  const model      = document.getElementById("f-vlm-model").value.trim();
  const start      = document.getElementById("f-vlm-start").value;
  const end        = document.getElementById("f-vlm-end").value;

  if (defectType) params.set("defect_type", defectType);
  if (model)      params.set("model", model);
  if (start)      params.set("start", start.replace("T", " "));
  if (end)        params.set("end",   end.replace("T", " "));

  try {
    const res  = await fetch("/api/vlm-no?" + params);
    const rows = await res.json();

    if (!rows.length) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No VLM rejections found.</td></tr>';
      return;
    }

    tbody.innerHTML = rows.map(r => {
      const imgSrc  = r.image ? `data:image/jpeg;base64,${r.image}` : null;
      const imgCell = imgSrc
        ? `<img class="thumb" src="${imgSrc}" alt="img"
              onclick="openImageB64('${r.image}', 'VLM Rejection | ${r.model || ""}')">`
        : '<span style="color:#475569;font-size:12px">no image</span>';

      const reasoning = r.reasoning
        ? `<div class="reasoning-text" title="${r.reasoning}">${r.reasoning}</div>`
        : '<span style="color:#475569">—</span>';

      return `<tr>
        <td style="color:#475569">${r.id}</td>
        <td><span class="badge-type">${r.defect_type || "—"}</span></td>
        <td style="color:#94a3b8">${r.model || "—"}</td>
        <td>${reasoning}</td>
        <td style="color:#64748b;font-size:12px">${r.timestamp || "—"}</td>
        <td>${imgCell}</td>
      </tr>`;
    }).join("");

  } catch (e) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Error loading data.</td></tr>';
    console.error("loadVlmNo failed:", e);
  }
}

// ── Live Feed ─────────────────────────────────────────────────

const LIVE_POLL_MS = 2500;
const LIVE_SHOW_MAX = 80;

const ROUTE_COLORS = {
  "AUTO-ACCEPT"    : "#34d399",
  "VLM-YES"        : "#4ade80",
  "CACHED-ACCEPT"  : "#60a5fa",
  "LOW-CONF REJECT": "#94a3b8",
  "VLM-NO"         : "#f87171",
  "CACHED-REJECT"  : "#c084fc",
};

let seenLiveKeys = new Set();
let liveStarted = false;

function routeStyle(route) {
  const col = ROUTE_COLORS[route] || "#e2e8f0";
  return `background:${col}22;color:${col};border:1px solid ${col}44;`;
}

function timeAgo(ts) {
  const s = Math.floor(Date.now() / 1000 - ts);
  if (s < 60) return s + "s ago";
  if (s < 3600) return Math.floor(s / 60) + "m ago";
  return Math.floor(s / 3600) + "h ago";
}

function makeLiveCard(item) {
  const col = ROUTE_COLORS[item.route] || "#e2e8f0";
  const key = item.frame_name + "_" + item.track_id + "_" + item.route;
  if (seenLiveKeys.has(key)) return null;
  seenLiveKeys.add(key);

  const card = document.createElement("div");
  card.className = "live-card";

  const imgSrc = `/api/frame/${encodeURIComponent(item.frame_name)}/${item.track_id}/${item.route}`;
  const reason = item.reason
    ? `<div class="live-reason">VLM: ${item.reason.substring(0, 80)}${item.reason.length > 80 ? "…" : ""}</div>`
    : "";

  card.innerHTML = `
    <img src="${imgSrc}" alt="${item.frame_name}" loading="lazy"
         onerror="this.style.display='none'"
         onclick="openImageUrl('${imgSrc}', '${(item.label || "").replace(/'/g, "\\'")} ${item.confidence} | ${item.route} | Track#${item.track_id}')">
    <div class="card-body">
      <span class="live-route" style="${routeStyle(item.route)}">${item.route}</span>
      <div class="live-meta">
        <b style="color:${col}">${item.label || "—"}</b>
        &nbsp;conf <b>${item.confidence || "—"}</b>
        &nbsp;&bull;&nbsp; Track#<b>${item.track_id ?? "—"}</b><br>
        <span style="color:#475569">${item.frame_name || ""} &bull; ${timeAgo(item.ts || item.received_at)}</span>
      </div>
      ${reason}
    </div>`;
  return card;
}

async function pollLive() {
  try {
    const resp = await fetch("/api/live?limit=60");
    const data = await resp.json();

    // Update live counters
    document.getElementById("stat-live-total").textContent = data.counters.total;
    document.getElementById("cnt-accepted").textContent    = data.counters.accepted;
    document.getElementById("cnt-rejected").textContent    = data.counters.rejected;
    document.getElementById("cnt-vlm").textContent         = data.counters.vlm_called;
    document.getElementById("cnt-cached").textContent      = data.counters.cached;
    document.getElementById("last-update").textContent     = "Updated: " + new Date().toLocaleTimeString();

    // Update live indicator
    const dot   = document.querySelector(".live-dot");
    const label = document.getElementById("live-label");
    if (data.counters.total > 0) {
      dot.classList.remove("offline");
      label.textContent = data.counters.total + " received";
      label.style.color = "#34d399";
    } else {
      label.textContent = "no data yet";
    }

    document.getElementById("live-status").textContent =
      data.items.length > 0
        ? `Showing ${data.items.length} recent detections`
        : "Waiting for detections from Colab pipeline...";

    // Render cards
    const grid = document.getElementById("live-grid");
    const emptyMsg = document.getElementById("live-empty");

    for (const item of data.items) {
      const card = makeLiveCard(item);
      if (card) {
        grid.prepend(card);
        if (emptyMsg) emptyMsg.style.display = "none";
      }
    }

    while (grid.children.length > LIVE_SHOW_MAX) {
      grid.removeChild(grid.lastChild);
    }
  } catch (e) {
    document.getElementById("live-status").textContent = "Connection error, retrying...";
  }
  setTimeout(pollLive, LIVE_POLL_MS);
}

// ── Init ───────��──────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  fetchStats();
  loadDetections();
  pollLive();  // Start live polling immediately for stats

  // Load VLM tab data when tab is first clicked
  document.querySelector('[data-bs-target="#tab-vlm-no"]').addEventListener("shown.bs.tab", () => {
    if (document.getElementById("vlm-no-tbody").querySelector(".empty-row")) {
      loadVlmNo();
    }
  });

  // Auto-refresh DB stats every 10 seconds
  setInterval(fetchStats, 10000);
});
