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

// ── YOLO Detections ───────────────────────────────────────────

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

// ── Init ──────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  fetchStats();
  loadDetections();

  // Load VLM tab data when tab is first clicked
  document.querySelector('[data-bs-target="#tab-vlm-no"]').addEventListener("shown.bs.tab", () => {
    if (document.getElementById("vlm-no-tbody").querySelector(".empty-row")) {
      loadVlmNo();
    }
  });

  // Auto-refresh stats every 10 seconds
  setInterval(fetchStats, 10000);
});
