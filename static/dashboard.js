// dashboard.js — Frontend logic for /dashboard

const imgModal = new bootstrap.Modal(document.getElementById("imgModal"));

// ── Stats ─────────────────────────────────────────────────────

async function fetchStats() {
  try {
    const res  = await fetch("/api/stats");
    const data = await res.json();

    document.getElementById("stat-detections").textContent = data.total_detections ?? "—";
    document.getElementById("stat-vlm-yes").textContent    = data.vlm_yes_count ?? "—";
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

function openImageUrl(url, caption, reasoning) {
  document.getElementById("modal-preview").src = url;
  document.getElementById("modal-caption").textContent = caption || "";
  document.getElementById("modal-title").textContent   = "Image Preview";

  const reasonCol  = document.getElementById("modal-reasoning-col");
  const reasonText = document.getElementById("modal-reasoning-text");
  
  if (reasoning && reasoning.trim()) {
    reasonText.textContent = reasoning;
    reasonCol.style.display = "block";
  } else {
    reasonCol.style.display = "none";
  }

  imgModal.show();
}

// ── YOLO Detections ───���───────────────────────────────────────

async function loadDetections() {
  const tbody = document.getElementById("detections-tbody");
  if (!tbody) return;
  
  tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Loading...</td></tr>';

  const params = new URLSearchParams();
  // Status is now always 'accepted' for the main detections table (> 0.80)
  params.set("status", "accepted");
  
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
      tbody.innerHTML = `<tr class="empty-row"><td colspan="6">No high-confidence detections found.</td></tr>`;
      return;
    }

    tbody.innerHTML = rows.map(r => {
      let imgSrc = null;
      if (r.image) {
        imgSrc = r.image.includes("/") ? `/static/${r.image}` : `data:image/jpeg;base64,${r.image}`;
      }

      const imgCell = imgSrc
        ? `<img class="thumb" src="${imgSrc}" alt="img"
              onclick="openImageUrl('${imgSrc}', '${r.defect_type} | ${r.model_name || ""} | conf ${r.confidence}')">`
        : '<span style="color:#475569;font-size:12px">no image</span>';

      const conf = r.confidence != null
        ? `<span style="color:#059669;font-weight:600">${r.confidence.toFixed(3)}</span>`
        : "—";

      return `<tr>
        <td style="color:#475569">${r.track_id ?? r.id}</td>
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

function loadAllYoloDetections() {
  loadDetections();
}

// ── VLM Rejections ────────────────────────────────────────────

async function loadVlmYes() {
  const tbody = document.getElementById("vlm-yes-tbody");
  if (!tbody) return;
  tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Loading...</td></tr>';

  const params = new URLSearchParams();
  const defectType = document.getElementById("f-vlm-defect-type").value.trim();
  const model      = document.getElementById("f-vlm-model-name").value.trim();
  const start      = document.getElementById("f-vlm-start").value;
  const end        = document.getElementById("f-vlm-end").value;

  if (defectType) params.set("defect_type", defectType);
  if (model)      params.set("model", model);
  if (start)      params.set("start", start.replace("T", " "));
  if (end)        params.set("end",   end.replace("T", " "));

  try {
    const res  = await fetch("/api/vlm-yes?" + params);
    const rows = await res.json();

    if (!rows.length) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No confirmed detections.</td></tr>';
      return;
    }

    tbody.innerHTML = rows.map(r => {
      let imgSrc = r.image ? (r.image.includes("/") ? `/static/${r.image}` : `data:image/jpeg;base64,${r.image}`) : null;
      const imgCell = imgSrc
        ? `<img class="thumb" src="${imgSrc}" alt="img" onclick="openImageUrl('${imgSrc}', 'VLM Confirmed | ${(r.model || "").replace(/"/g, "&quot;")}', '${(r.reasoning || "").replace(/'/g, "\\'").replace(/"/g, "&quot;").replace(/\n/g, "\\n").replace(/\r/g, "")}')">`
        : '<span style="color:#475569;font-size:12px">no image</span>';

      const reasoning = r.reasoning
        ? `<div class="reasoning-text" title="${r.reasoning}">${r.reasoning}</div>`
        : '<span style="color:#475569">—</span>';

      return `<tr>
        <td style="color:#475569">${r.track_id ?? r.id}</td>
        <td><span class="badge-type">${r.defect_type || "—"}</span></td>
        <td style="color:#94a3b8">${r.model || "—"}</td>
        <td style="color:#64748b;font-size:12px">${r.timestamp || "—"}</td>
        <td>${imgCell}</td>
      </tr>`;
    }).join("");
  } catch (e) {
    console.error("loadVlmYes failed:", e);
    tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Error loading data.</td></tr>';
  }
}

async function loadVlmNo() {
  const tbody = document.getElementById("vlm-no-tbody");
  if (!tbody) return;
  tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Loading...</td></tr>';

  const params = new URLSearchParams();
  const defectType = document.getElementById("f-vlm-defect-type").value.trim();
  const model      = document.getElementById("f-vlm-model-name").value.trim();
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
      let imgSrc = null;
      if (r.image) {
        imgSrc = r.image.includes("/") ? `/static/${r.image}` : `data:image/jpeg;base64,${r.image}`;
      }

      const imgCell = imgSrc
        ? `<img class="thumb" src="${imgSrc}" alt="img"
              onclick="openImageUrl('${imgSrc}', 'VLM Rejection | ${(r.model || "").replace(/"/g, "&quot;")}', '${(r.reasoning || "").replace(/'/g, "\\'").replace(/"/g, "&quot;").replace(/\n/g, "\\n").replace(/\r/g, "")}')">`
        : '<span style="color:#475569;font-size:12px">no image</span>';

      const reasoning = r.reasoning
        ? `<div class="reasoning-text" title="${r.reasoning}">${r.reasoning}</div>`
        : '<span style="color:#475569">—</span>';

      return `<tr>
        <td style="color:#475569">${r.track_id ?? r.id}</td>
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

function loadAllVlmDetections() {
  const activeTab = document.querySelector('#vlmSubTabs .nav-link.active');
  if (activeTab && activeTab.textContent.trim().toLowerCase().includes('rejected')) {
    loadVlmNo();
  } else {
    loadVlmYes();
  }
}

// ── Live Feed ─────────────────────────────────────────────────

const LIVE_POLL_MS = 2500;
const LIVE_SHOW_MAX = 80;

const ROUTE_COLORS = {
  "AUTO-ACCEPT"    : "#059669",
  "VLM-YES"        : "#0d9488",
  "CACHED-ACCEPT"  : "#2563eb",
  "LOW-CONF REJECT": "#64748b",
  "VLM-NO"         : "#dc2626",
  "CACHED-REJECT"  : "#7c3aed",
};

let seenLiveKeys = new Set();
let liveStarted = false;

function routeStyle(route) {
  const col = ROUTE_COLORS[route] || "#64748b";
  return `background:${col}15; color:${col}; border:1px solid ${col}30;`;
}

function timeAgo(ts) {
  const s = Math.floor(Date.now() / 1000 - ts);
  if (s < 60) return s + "s ago";
  if (s < 3600) return Math.floor(s / 60) + "m ago";
  return Math.floor(s / 3600) + "h ago";
}

function makeLiveCard(item) {
  const col = ROUTE_COLORS[item.route] || "#64748b";
  const key = item.frame_name + "_" + item.track_id + "_" + item.route;
  if (seenLiveKeys.has(key)) return null;
  seenLiveKeys.add(key);

  const card = document.createElement("div");
  card.className = "live-card";

  const imgSrc = `/api/frame/${encodeURIComponent(item.frame_name)}/${item.track_id}/${item.route}`;
  const isRejected = item.route === "VLM-NO" || item.route === "LOW-CONF REJECT" || item.route === "CACHED-REJECT";
  const reason = (item.reason && isRejected)
    ? `<div class="live-reason">VLM: ${item.reason.substring(0, 120)}${item.reason.length > 120 ? "…" : ""}</div>`
    : "";

  card.innerHTML = `
    <img src="${imgSrc}" alt="${item.frame_name}" loading="lazy"
         onerror="this.style.display='none'"
         onclick="openImageUrl('${imgSrc}', '${(item.label || "").replace(/'/g, "\\'").replace(/"/g, "&quot;")} ${item.confidence} | ${item.route} | Track#${item.track_id}', '${(item.reason || "").replace(/'/g, "\\'").replace(/"/g, "&quot;").replace(/\n/g, "\\n").replace(/\r/g, "")}')">
    <div class="card-body">
      <span class="live-route" style="${routeStyle(item.route)}">${item.route}</span>
      <div class="live-meta">
        <div class="mb-1 d-flex align-items-center flex-wrap gap-2">
          <b style="color:#0f172a; font-size:14px;">${item.label || "—"}</b>
          <span style="color:${col}; font-weight:600; font-size:12px;">conf ${item.confidence || "—"}</span>
        </div>
        <div style="color:#64748b; font-size:12px; font-weight:500;">
          Track#${item.track_id ?? "—"} &bull; ${item.frame_name || ""} &bull; ${timeAgo(item.ts || item.received_at)}
        </div>
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
      label.style.color = "#059669";
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
    loadVlmNo();
    loadVlmYes();
  });

  // Auto-refresh DB stats every 10 seconds
  setInterval(fetchStats, 10000);
});
