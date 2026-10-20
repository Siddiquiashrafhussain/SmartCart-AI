/**
 * SmartCart AI - Staff Admin Dashboard Application
 * Handles API orchestration, WebSocket real-time event subscription,
 * shelf-auditing file uploads, alert resolution, and verification inspection.
 */

const API_BASE = '/api/v1';
let ws = null;
let reconnectTimer = null;
let currentAuditResult = null;

// Application State
const state = {
  inventory: [],
  products: [],
  alerts: [],
  activeSessions: [],
  summaryStats: null,
  activeTab: 'overview',
  activeAlertFilter: 'ALL'
};

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initWebSocket();
  initVisionUploader();
  initSimulatorControls();
  refreshAllData();
});

/* ==========================================================================
   Navigation & Tabs
   ========================================================================== */
function initNavigation() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      switchTab(target);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tabId);
  });
  document.querySelectorAll('.tab-content').forEach(c => {
    c.classList.toggle('active', c.id === `tab-${tabId}`);
  });

  if (tabId === 'inventory') renderInventoryTable();
  if (tabId === 'alerts') renderAlertsList();
  if (tabId === 'overview') renderOverview();
}

/* ==========================================================================
   Real-Time WebSocket Stream
   ========================================================================== */
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}${API_BASE}/ws/dashboard`;
  const badge = document.getElementById('ws-badge');
  const badgeText = document.getElementById('ws-badge-text');

  if (ws) {
    try { ws.close(); } catch (e) {}
  }

  badge.className = 'connection-badge reconnecting';
  badgeText.textContent = 'Connecting...';

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    badge.className = 'connection-badge';
    badgeText.textContent = 'Live Stream Connected';
    if (reconnectTimer) clearInterval(reconnectTimer);

    // Heartbeat ping every 25s
    setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 25000);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleRealtimeEvent(data);
    } catch (e) {
      console.warn('Malformed WS message:', event.data);
    }
  };

  ws.onclose = () => {
    badge.className = 'connection-badge offline';
    badgeText.textContent = 'Stream Offline (Reconnecting)';
    scheduleReconnect();
  };

  ws.onerror = () => {
    badge.className = 'connection-badge offline';
    badgeText.textContent = 'Connection Error';
  };
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    initWebSocket();
  }, 4000);
}

function handleRealtimeEvent(event) {
  if (event.event_type === 'ALERT_TRIGGERED') {
    showToast(`New Alert: ${event.alert.alert_type} on Shelf #${event.alert.shelf_id}`, 'warning');
    refreshAlerts();
    refreshInventory();
  } else if (event.event_type === 'ALERT_RESOLVED') {
    showToast(`Alert #${event.alert.id} Resolved by Attendant`, 'success');
    refreshAlerts();
    refreshInventory();
  } else if (event.event_type === 'SESSION_VERIFIED') {
    const outcomeLabel = event.outcome.replace(/_/g, ' ');
    const toastType = event.outcome === 'NO_DISCREPANCY_DETECTED' ? 'success' : 'warning';
    showToast(`Session #${event.session_id} Verified: ${outcomeLabel}`, toastType);
    refreshOverview();
  }
}

/* ==========================================================================
   Data Fetching & APIs
   ========================================================================== */
async function refreshAllData() {
  await Promise.all([
    refreshInventory(),
    refreshAlerts(),
    refreshStats()
  ]);
  renderOverview();
}

async function refreshInventory() {
  try {
    const [invRes, prodRes] = await Promise.all([
      fetch(`${API_BASE}/inventory?limit=100`),
      fetch(`${API_BASE}/products?limit=100`)
    ]);

    if (invRes.ok && prodRes.ok) {
      state.inventory = await invRes.json();
      state.products = await prodRes.json();
      renderInventoryTable();
    }
  } catch (err) {
    showToast('Failed to load store inventory', 'error');
  }
}

async function refreshAlerts() {
  try {
    const res = await fetch(`${API_BASE}/alerts?limit=100`);
    if (res.ok) {
      state.alerts = await res.json();
      const openCount = state.alerts.filter(a => !a.is_resolved).length;
      document.getElementById('alerts-tab-badge').textContent = openCount;
      renderAlertsList();
    }
  } catch (err) {
    showToast('Failed to load restock alerts', 'error');
  }
}

async function refreshStats() {
  try {
    const res = await fetch(`${API_BASE}/alerts/stats/summary`);
    if (res.ok) {
      state.summaryStats = await res.json();
      renderKPIs();
    }
  } catch (err) {}
}

/* ==========================================================================
   Renderers: Overview & KPIs
   ========================================================================== */
function renderKPIs() {
  const stats = state.summaryStats || {
    total_active_alerts: 0,
    active_stockouts: 0,
    active_low_stock: 0,
    total_resolved_alerts: 0
  };

  document.getElementById('kpi-total-items').textContent = state.products.length || '12';
  document.getElementById('kpi-active-alerts').textContent = stats.total_active_alerts;
  document.getElementById('kpi-stockouts').textContent = stats.active_stockouts;
  document.getElementById('kpi-low-stock').textContent = stats.active_low_stock;

  // Calculate Health Index (% of products strictly above safety threshold)
  if (state.inventory.length > 0) {
    const healthyCount = state.inventory.filter(i => i.estimated_visible_stock > i.safety_threshold).length;
    const healthPercent = Math.round((healthyCount / state.inventory.length) * 100);
    document.getElementById('kpi-shelf-health').textContent = `${healthPercent}%`;
  }
}

function renderOverview() {
  renderKPIs();
  const queueEl = document.getElementById('urgent-attention-queue');
  const activeAlerts = state.alerts.filter(a => !a.is_resolved);

  if (activeAlerts.length === 0) {
    queueEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">✓</div>
        <p>No critical stockouts or unreviewed discrepancies. All shelf aisles operating normally.</p>
      </div>
    `;
    return;
  }

  queueEl.innerHTML = activeAlerts.slice(0, 5).map(a => `
    <div style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); padding: 14px 18px; border-radius: var(--radius-md); margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
      <div>
        <span class="chip ${a.alert_type === 'STOCKOUT' ? 'chip-danger' : 'chip-warning'}">${a.alert_type}</span>
        <strong style="margin-left: 10px;">${escapeHtml(a.product_name || a.product_sku)}</strong>
        <span style="color: var(--text-muted); font-size: 0.8rem; margin-left: 8px;">Shelf Bay #${a.shelf_id} (${escapeHtml(a.shelf_bay_code || '')})</span>
        <div style="font-size: 0.78rem; color: var(--text-dim); margin-top: 4px;">
          Observed Visible: <strong>${a.observed_count}</strong> | Safety Threshold: <strong>${a.threshold}</strong>
        </div>
      </div>
      <div>
        <button class="btn btn-secondary btn-sm" onclick="openResolveModal(${a.id}, '${escapeJs(a.product_name)}')">Take Action</button>
      </div>
    </div>
  `).join('');
}

/* ==========================================================================
   Renderers: Inventory & Catalogue
   ========================================================================== */
function renderInventoryTable() {
  const tbody = document.getElementById('inventory-table-body');
  const search = (document.getElementById('inventory-search')?.value || '').toLowerCase();
  const filterCat = document.getElementById('inventory-cat-filter')?.value || '';

  const filtered = state.products.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(search) || p.sku.toLowerCase().includes(search) || p.barcode.includes(search);
    const matchesCat = !filterCat || p.category.toLowerCase() === filterCat.toLowerCase();
    return matchesSearch && matchesCat;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="empty-state">No matching merchandise items found.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(prod => {
    const inv = state.inventory.find(i => i.product_id === prod.id) || {
      total_store_stock: 0,
      estimated_visible_stock: 0,
      safety_threshold: 2
    };

    let statusChip = '<span class="chip chip-success">In Stock</span>';
    if (inv.estimated_visible_stock === 0) {
      statusChip = '<span class="chip chip-danger">Stockout</span>';
    } else if (inv.estimated_visible_stock <= inv.safety_threshold) {
      statusChip = '<span class="chip chip-warning">Low Stock</span>';
    }

    return `
      <tr>
        <td><strong>${escapeHtml(prod.sku)}</strong></td>
        <td>${escapeHtml(prod.name)}</td>
        <td><span class="chip chip-info">${escapeHtml(prod.category)}</span></td>
        <td><code>${escapeHtml(prod.barcode)}</code></td>
        <td>$${prod.price.toFixed(2)}</td>
        <td>${prod.tare_weight_g.toFixed(0)}g</td>
        <td><strong>${inv.total_store_stock}</strong></td>
        <td><span style="font-size: 1rem; font-weight: 700; color: ${inv.estimated_visible_stock <= inv.safety_threshold ? 'var(--accent-rose)' : 'var(--accent-emerald)'};">${inv.estimated_visible_stock}</span></td>
        <td>${statusChip}</td>
      </tr>
    `;
  }).join('');
}

/* ==========================================================================
   Renderers: Alerts & Task Management
   ========================================================================== */
function renderAlertsList() {
  const container = document.getElementById('alerts-list-container');
  const filter = state.activeAlertFilter;

  const filtered = state.alerts.filter(a => {
    if (filter === 'ACTIVE') return !a.is_resolved;
    if (filter === 'RESOLVED') return a.is_resolved;
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🔔</div>
        <p>No restock alerts match the selected filter.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(a => {
    const isStockout = a.alert_type === 'STOCKOUT';
    const chipClass = a.is_resolved ? 'chip-info' : isStockout ? 'chip-danger' : 'chip-warning';
    const auditId = a.evidence_metadata?.audit_id ? `<span style="font-family: monospace; font-size: 0.72rem; color: var(--text-dim);">Audit ID: ${a.evidence_metadata.audit_id}</span>` : '';

    return `
      <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 20px; margin-bottom: 16px; box-shadow: var(--shadow-card);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
          <div>
            <span class="chip ${chipClass}">${a.alert_type}</span>
            <span class="chip ${a.is_resolved ? 'chip-success' : 'chip-warning'}" style="margin-left: 8px;">${a.is_resolved ? 'RESOLVED' : 'ACTION REQUIRED'}</span>
            <h3 style="font-size: 1.1rem; margin-top: 8px; font-weight: 700;">${escapeHtml(a.product_name || a.product_sku)}</h3>
          </div>
          <div>
            ${!a.is_resolved ? `
              <button class="btn btn-primary btn-sm" onclick="openResolveModal(${a.id}, '${escapeJs(a.product_name || a.product_sku)}')">Resolve & Restock</button>
            ` : `
              <span style="font-size: 0.78rem; color: var(--text-muted);">Resolved: ${new Date(a.resolved_at).toLocaleTimeString()}</span>
            `}
          </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; font-size: 0.85rem; color: var(--text-muted); background: var(--bg-secondary); padding: 12px 16px; border-radius: var(--radius-md); margin-bottom: 12px;">
          <div>Shelf Bay: <strong style="color: var(--text-main);">#${a.shelf_id} (${escapeHtml(a.shelf_bay_code || 'Aisle Bay')})</strong></div>
          <div>Observed Visible: <strong style="color: ${isStockout ? 'var(--accent-rose)' : 'var(--accent-amber)'};">${a.observed_count} units</strong></div>
          <div>Safety Threshold: <strong style="color: var(--text-main);">${a.threshold} units</strong></div>
          <div>Triggered: <strong style="color: var(--text-main);">${new Date(a.created_at).toLocaleTimeString()}</strong></div>
        </div>

        ${a.resolution_note ? `
          <div style="font-size: 0.82rem; color: var(--status-success-text); background: var(--status-success-bg); border: 1px solid var(--status-success-border); padding: 8px 12px; border-radius: var(--radius-sm); margin-top: 8px;">
            Attendant Note: "${escapeHtml(a.resolution_note)}"
          </div>
        ` : ''}

        <div style="margin-top: 8px;">
          ${auditId}
        </div>
      </div>
    `;
  }).join('');
}

function filterAlerts(status) {
  state.activeAlertFilter = status;
  document.querySelectorAll('.alert-filter-btn').forEach(btn => {
    btn.classList.toggle('btn-primary', btn.dataset.filter === status);
    btn.classList.toggle('btn-secondary', btn.dataset.filter !== status);
  });
  renderAlertsList();
}

/* ==========================================================================
   Alert Resolution Modal Workflow
   ========================================================================== */
function openResolveModal(alertId, productName) {
  document.getElementById('resolve-alert-id').value = alertId;
  document.getElementById('resolve-product-title').textContent = productName;
  document.getElementById('resolve-note-input').value = 'Replenished stock from warehouse backroom';
  document.getElementById('resolve-units-input').value = '4';
  document.getElementById('resolve-modal').classList.add('active');
}

function closeResolveModal() {
  document.getElementById('resolve-modal').classList.remove('active');
}

async function submitAlertResolution() {
  const alertId = document.getElementById('resolve-alert-id').value;
  const note = document.getElementById('resolve-note-input').value.trim();
  const units = parseInt(document.getElementById('resolve-units-input').value, 10);

  if (!alertId) return;

  try {
    const res = await fetch(`${API_BASE}/alerts/${alertId}/resolve`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resolution_note: note,
        units_restocked: isNaN(units) ? null : units
      })
    });

    if (res.ok) {
      showToast(`Alert #${alertId} successfully resolved and shelf restocked`, 'success');
      closeResolveModal();
      await refreshAllData();
    } else {
      const err = await res.json();
      showToast(err.detail || 'Failed to resolve alert', 'error');
    }
  } catch (e) {
    showToast('Network error resolving alert', 'error');
  }
}

/* ==========================================================================
   Computer Vision & Shelf Auditing Area
   ========================================================================== */
function initVisionUploader() {
  const fileInput = document.getElementById('shelf-file-input');
  const dropzone = document.getElementById('shelf-dropzone');

  if (!fileInput || !dropzone) return;

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = 'var(--accent-primary)';
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.style.borderColor = 'rgba(99, 102, 241, 0.35)';
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = 'rgba(99, 102, 241, 0.35)';
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleImageAudit(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files[0]) {
      handleImageAudit(fileInput.files[0]);
    }
  });
}

async function handleImageAudit(file) {
  const shelfSelect = document.getElementById('audit-shelf-select');
  const shelfId = shelfSelect ? shelfSelect.value : 1;
  const statusEl = document.getElementById('vision-upload-status');

  statusEl.innerHTML = `<span class="spinner"></span> Running OpenCV preprocessing and YOLO detection...`;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('shelf_id', shelfId);
  formData.append('return_annotated_base64', 'true');

  try {
    const res = await fetch(`${API_BASE}/vision/audit-shelf`, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Image processing failed');
    }

    currentAuditResult = await res.json();
    renderVisionAuditResults(currentAuditResult);
    statusEl.innerHTML = `<span style="color: var(--accent-emerald);">✓ Audit complete in ${currentAuditResult.inference_time_ms}ms</span>`;
    showToast(`Shelf image audited: ${currentAuditResult.total_objects_detected} objects detected`, 'success');
  } catch (err) {
    statusEl.innerHTML = `<span style="color: var(--accent-rose);">✕ Error: ${escapeHtml(err.message)}</span>`;
    showToast(err.message, 'error');
  }
}

function renderVisionAuditResults(result) {
  const previewImg = document.getElementById('annotated-shelf-preview');
  const countsEl = document.getElementById('vision-class-counts');
  const qualityEl = document.getElementById('vision-quality-metrics');
  const evalBtn = document.getElementById('btn-evaluate-alerts-from-vision');

  if (result.annotated_image_base64) {
    previewImg.src = result.annotated_image_base64;
    previewImg.style.display = 'block';
    document.getElementById('vision-empty-preview').style.display = 'none';
  }

  // Render Detected Counts
  const entries = Object.entries(result.detected_counts_by_class || {});
  if (entries.length === 0) {
    countsEl.innerHTML = `<div style="color: var(--text-dim); font-size: 0.85rem;">0 objects detected on shelf bay. Shelf appears empty or occluded.</div>`;
  } else {
    countsEl.innerHTML = entries.map(([cls, cnt]) => `
      <div class="metric-pill">
        <span class="chip chip-info" style="font-size: 0.72rem;">${escapeHtml(cls)}</span>
        <strong>${cnt} visible facings</strong>
      </div>
    `).join('');
  }

  // Quality Diagnostics
  const q = result.image_metadata;
  qualityEl.innerHTML = `
    <div class="metric-pill">Resolution: <strong>${q.width}x${q.height}</strong></div>
    <div class="metric-pill">Blurriness (Laplacian Var): <strong>${q.blurriness_laplacian_var} (${q.quality_assessment})</strong></div>
    <div class="metric-pill">Brightness: <strong>${q.average_brightness}/255</strong></div>
    <div class="metric-pill">Inference: <strong>${result.inference_time_ms} ms</strong></div>
  `;

  // Enable Push to Alert Engine button
  evalBtn.disabled = false;
  evalBtn.onclick = () => pushVisionObservationsToAlerts(result);
}

async function pushVisionObservationsToAlerts(auditResult) {
  const shelfSelect = document.getElementById('audit-shelf-select');
  const shelfId = shelfSelect ? parseInt(shelfSelect.value, 10) : 1;

  try {
    const res = await fetch(`${API_BASE}/alerts/evaluate-shelf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        shelf_id: shelfId,
        observations: auditResult.detected_counts_by_class || {},
        audit_id: auditResult.audit_id,
        evidence_metadata: {
          inference_time_ms: auditResult.inference_time_ms,
          total_detected: auditResult.total_objects_detected
        }
      })
    });

    if (res.ok) {
      const data = await res.json();
      showToast(`Alerts updated: ${data.alerts_created} created, ${data.alerts_updated} deduplicated`, 'success');
      await refreshAllData();
      switchTab('alerts');
    } else {
      const err = await res.json();
      showToast(err.detail || 'Evaluation failed', 'error');
    }
  } catch (e) {
    showToast('Failed to evaluate shelf alerts', 'error');
  }
}

/* ==========================================================================
   Sessions & Checkout Verification Inspector
   ========================================================================== */
async function inspectSessionVerification(sessionId) {
  const id = sessionId || document.getElementById('inspect-session-id-input').value.trim();
  if (!id) return;

  const resultContainer = document.getElementById('session-verification-result');
  resultContainer.innerHTML = `<span class="spinner"></span> Running multi-modal event correlation...`;

  try {
    const res = await fetch(`${API_BASE}/verification/verify/${id}`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to verify session');
    }

    const data = await res.json();
    renderVerificationOutcome(data);
  } catch (err) {
    resultContainer.innerHTML = `<div style="color: var(--status-danger-text); padding: 12px;">✕ Error: ${escapeHtml(err.message)}</div>`;
  }
}

function renderVerificationOutcome(data) {
  const container = document.getElementById('session-verification-result');

  let outcomeChipClass = 'chip-success';
  if (data.outcome === 'POTENTIAL_DISCREPANCY') outcomeChipClass = 'chip-danger';
  if (data.outcome === 'INCONCLUSIVE') outcomeChipClass = 'chip-warning';

  let decisionChipClass = data.checkout_decision === 'AUTO_APPROVE' ? 'chip-success' : 'chip-warning';

  container.innerHTML = `
    <div style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 22px;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; margin-bottom: 16px;">
        <div>
          <span class="chip ${outcomeChipClass}" style="font-size: 0.85rem;">${data.outcome}</span>
          <span class="chip ${decisionChipClass}" style="margin-left: 8px;">${data.checkout_decision}</span>
          <h3 style="font-size: 1.2rem; font-weight: 700; margin-top: 8px;">Shopping Session #${data.session_id}</h3>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 1.4rem; font-weight: 700; color: ${data.confidence_score >= 0.85 ? 'var(--accent-emerald)' : 'var(--accent-amber)'};">
            ${(data.confidence_score * 100).toFixed(0)}%
          </div>
          <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase;">Confidence Score</div>
        </div>
      </div>

      <div style="margin-bottom: 16px; background: rgba(0,0,0,0.25); border-radius: var(--radius-md); padding: 14px;">
        <h4 style="font-size: 0.85rem; font-weight: 700; color: var(--text-dim); text-transform: uppercase; margin-bottom: 8px;">Correlation Reasons & Findings:</h4>
        <ul style="padding-left: 20px; font-size: 0.85rem; color: var(--text-main);">
          ${data.reasons.map(r => `<li style="margin-bottom: 4px;">${escapeHtml(r)}</li>`).join('')}
        </ul>
      </div>

      <div class="disclaimer-banner" style="margin-top: 0; margin-bottom: 16px;">
        <div>🛡️</div>
        <div>${escapeHtml(data.safety_and_trust_notice)}</div>
      </div>

      <h4 style="font-size: 0.85rem; font-weight: 700; color: var(--text-dim); text-transform: uppercase; margin-bottom: 8px;">Multi-Modal Correlated Events (${data.relevant_event_references.length}):</h4>
      <div style="max-height: 220px; overflow-y: auto;">
        ${data.relevant_event_references.map(e => `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: var(--bg-card); border-bottom: 1px solid var(--border-subtle); font-size: 0.8rem;">
            <div>
              <span class="chip chip-info" style="font-size: 0.68rem;">${e.event_type}</span>
              <strong style="margin-left: 8px;">${escapeHtml(e.summary)}</strong>
            </div>
            <div style="color: var(--text-dim); font-size: 0.75rem;">
              ${new Date(e.timestamp).toLocaleTimeString()}
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

/* ==========================================================================
   Simulator Controls for Hackathon Demonstration
   ========================================================================== */
function initSimulatorControls() {
  const container = document.getElementById('simulator-btn-strip');
  if (!container) return;

  const scenarios = [
    { id: 'normal_purchase', label: '1. Normal Purchase (Matching)', color: 'btn-secondary' },
    { id: 'unscanned_pickup', label: '2. Unscanned Pickup', color: 'btn-danger' },
    { id: 'product_mismatch', label: '3. Product Mismatch', color: 'btn-danger' },
    { id: 'quantity_mismatch', label: '4. Quantity Conflict', color: 'btn-danger' },
    { id: 'delayed_evidence', label: '5. Time Drift (Inconclusive)', color: 'btn-secondary' },
    { id: 'missing_evidence', label: '6. Missing Sensors', color: 'btn-secondary' }
  ];

  container.innerHTML = scenarios.map(s => `
    <button class="btn ${s.color} btn-sm" onclick="runSimulatedScenario('${s.id}')">
      ${s.label}
    </button>
  `).join('');
}

async function runSimulatedScenario(scenarioId) {
  const logEl = document.getElementById('simulation-run-log');
  logEl.innerHTML = `<span class="spinner"></span> Generating simulated telemetry for "${scenarioId}"...`;

  try {
    // 1. Start a temporary demo session
    const sessRes = await fetch(`${API_BASE}/sessions/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: 'sim_shopper', cart_id: 'cart_demo_01' })
    });
    const session = await sessRes.json();

    // 2. Add sample barcode scan to session
    await fetch(`${API_BASE}/events/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: session.id,
        barcode: scenarioId === 'product_mismatch' ? '8901030122211' : '8901030018241',
        quantity: 1,
        is_simulated: true
      })
    });

    if (scenarioId === 'normal_purchase') {
      // Add matching pickup and scale
      await fetch(`${API_BASE}/events/pickup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shelf_id: 1, detected_class: 'cereal', quantity_removed: 1, confidence: 0.94, is_simulated: true })
      });
      await fetch(`${API_BASE}/events/sensor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sensor_id: 'SCALE-01', sensor_type: 'WEIGHT_CART', delta_weight_g: 450.0, session_id: session.id, is_simulated: true })
      });
    } else if (scenarioId === 'quantity_mismatch') {
      // Camera sees 2 units
      await fetch(`${API_BASE}/events/pickup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shelf_id: 1, detected_class: 'cereal', quantity_removed: 2, confidence: 0.92, is_simulated: true })
      });
    }

    // Run verification on session
    const verifRes = await fetch(`${API_BASE}/verification/verify/${session.id}`, { method: 'POST' });
    const verifData = await verifRes.json();

    logEl.innerHTML = `
      <div style="color: var(--status-success-text); font-weight: 700;">✓ Scenario "${scenarioId}" executed on Session #${session.id}</div>
      <div style="font-size: 0.85rem; margin-top: 6px;">Outcome: <strong>${verifData.outcome}</strong> | Decision: <strong>${verifData.checkout_decision}</strong></div>
      <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">Reasons: ${verifData.reasons.join('; ')}</div>
    `;

    document.getElementById('inspect-session-id-input').value = session.id;
    inspectSessionVerification(session.id);
    await refreshAllData();
  } catch (err) {
    logEl.innerHTML = `<div style="color: var(--status-danger-text);">✕ Simulation failed: ${escapeHtml(err.message)}</div>`;
  }
}

/* ==========================================================================
   Utilities: Toast Notifications & Escaping
   ========================================================================== */
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(30px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeJs(str) {
  if (!str) return '';
  return String(str).replace(/'/g, "\\'").replace(/"/g, '\\"');
}
