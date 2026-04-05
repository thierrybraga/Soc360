# Sync Page JavaScript Reference Guide

## 📝 Overview

The `sync.js` file implements comprehensive synchronization management with real-time status polling, toast notifications, error handling, and accessibility support. It manages four independent sync modules (NVD, EUVD, MITRE, MITRE ATT&CK) with unified state management.

**File**: `app/static/js/pages/nvd/sync.js`
**Lines**: 551
**Entry Point**: `DOMContentLoaded` event
**Dependencies**: None (vanilla JavaScript ES6+)

## 🏗️ Architecture Overview

```
┌─ Event Listeners (DOM Setup)
├─ Element Cache (Performance)
├─ API Client (Network Layer)
├─ Toast System (User Feedback)
├─ Status Updaters (UI State)
├─ Action Handlers (Async Operations)
├─ Polling Manager (Real-time Updates)
└─ Initialization (Page Load)
```

## 1️⃣ DOMContentLoaded Event

```javascript
document.addEventListener('DOMContentLoaded', function() {
    console.log('[Sync Page] Initializing...');
    // All code runs here
    console.log('[Sync Page] Initialization complete');
});
```

**Why**:
- Ensures all DOM elements are loaded
- Prevents accessing non-existent elements
- Clean namespace isolation
- Guaranteed execution order

## 2️⃣ UI Elements Cache

```javascript
const elements = {
    nvd: {
        icon: document.getElementById('status-icon'),
        text: document.getElementById('status-text'),
        details: document.getElementById('status-details'),
        container: document.getElementById('progress-container'),
        bar: document.getElementById('progress-bar'),
        // ... more elements
        btns: {
            incremental: document.getElementById('btn-incremental'),
            full: document.getElementById('btn-full'),
            cancel: document.getElementById('btn-cancel')
        }
    },
    euvd: { /* Similar structure */ },
    mitre: { /* Similar structure */ },
    mitreAttack: { /* Similar structure */ }
};
```

**Performance**:
- DOM queries run once on page load
- Reference stored for reuse
- Faster access compared to repeatedly querying
- ~10-50ms faster for complex pages

**Structure**:
- Grouped by sync module
- Consistent nested keys
- Easy to extend with new elements

## 3️⃣ API Client Proxy

```javascript
const api = window.OpenMonitor?.api || {
    get: async (url) => {
        const res = await fetch(url);
        if (!res.ok) throw new Error(res.statusText);
        return res.json();
    },
    post: async (url, body) => {
        const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
        const res = await fetch(url, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json', 
                'X-CSRFToken': csrf 
            },
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.error || res.statusText);
        }
        return res.json();
    }
};
```

**Uses window.OpenMonitor.api if available**:
- Respects global API configuration
- Fallback to native fetch if unavailable
- CSRF token automatic handling
- Error parsing from response body

## 4️⃣ Toast Notification System

```javascript
function showToast(message, type = 'info', duration = 3000) {
    // Try using global toast system first
    if (window.OpenMonitor?.showToast) {
        window.OpenMonitor.showToast(message, type);
        return;
    }

    // Create custom toast element
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 14px;
        z-index: 9999;
        animation: slideInRight 0.3s ease-out;
        background: ${getBackgroundColor(type)};
        color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}
```

**Types**:
- `'success'`: Green (#10b981)
- `'error'`: Red (#ef4444)
- `'warning'`: Amber (#f59e0b)
- `'info'`: Blue (#3b82f6)

**Features**:
- Fixed position (bottom-right)
- Auto-dismissal after duration
- Smooth entrance/exit animation
- Z-index 9999 (above all content)
- Fallback if global toast unavailable

## 5️⃣ NVD Status Updater

```javascript
function updateNvdUI(data) {
    const el = elements.nvd;
    if (!el.lastSync) return;  // Safety check

    // Update timestamps
    el.lastSync.textContent = data.last_updated 
        ? new Date(data.last_updated).toLocaleString('pt-BR') 
        : 'Nunca';

    // Update counters
    el.total.textContent = `${data.processed_cves || 0} / ${data.total_cves || 0}`;
    if (el.firstSync) el.firstSync.textContent = data.first_sync_completed 
        ? '✓ Concluído' 
        : '○ Pendente';

    // Update statistics
    if(el.inserted) el.inserted.textContent = data.inserted || 0;
    if(el.updated) el.updated.textContent = data.updated || 0;
    if(el.skipped) el.skipped.textContent = data.skipped || 0;
    if(el.errors) el.errors.textContent = data.errors || 0;

    const status = (data.status || '').toUpperCase();

    // Reset to default state
    el.container.classList.add('d-none');
    el.btns.cancel.classList.add('d-none');
    el.btns.incremental.disabled = false;
    el.btns.full.disabled = false;

    // Handle each status
    if (['RUNNING', 'STARTING'].includes(status)) {
        el.icon.innerHTML = '<i class="fas fa-sync fa-spin fa-3x text-primary"></i>';
        el.text.textContent = 'Sincronização em Andamento';
        el.details.textContent = data.message || 'Processando...';
        
        el.container.classList.remove('d-none');
        const percent = data.total_cves > 0 
            ? Math.round((data.processed_cves / data.total_cves) * 100) 
            : 0;
        el.bar.style.width = `${percent}%`;
        el.bar.textContent = `${percent}%`;
        
        el.btns.incremental.disabled = true;
        el.btns.full.disabled = true;
        el.btns.cancel.classList.remove('d-none');
        
        startPolling('nvd');
    } 
    else if (status === 'COMPLETED') {
        el.icon.innerHTML = '<i class="fas fa-check-circle fa-3x text-success animate-popIn"></i>';
        el.text.textContent = 'Sincronização Concluída';
        el.details.textContent = 'A base de dados está atualizada.';
        stopPolling('nvd');
        showToast('Sincronização NVD concluída com sucesso!', 'success');
    } 
    // ... more status handlers
}
```

**Status Handlers**:
- `RUNNING/STARTING`: Show spinner, enable cancel
- `COMPLETED`: Show success, notify user
- `FAILED`: Show error, log details
- `CANCELLED`: Show warning, stop polling
- `IDLE`: Show awaiting state

## 6️⃣ EUVD/MITRE/MITRE ATT&CK Updaters

Similar pattern to NVD with module-specific variations:

```javascript
function updateEuvdUI(data) {
    // Simpler structure (one action)
    const el = elements.euvd;
    const status = (data.status || 'idle').toLowerCase();
    // ... similar state updates
}

function updateMitreUI(data) {
    // Enrichment focus
    el.text.textContent = 'Enriquecimento em Andamento';
}

function updateMitreAttackUI(data) {
    // Framework plus mapping
    // Handles two distinct operations
}
```

## 7️⃣ Status Check Function

```javascript
async function checkStatus(type) {
    try {
        let url;
        if (type === 'nvd') url = '/vulnerabilities/api/sync/status';
        else if (type === 'euvd') url = '/api/euvd/sync/status';
        else if (type === 'mitre') url = '/api/mitre/sync/status';
        else if (type === 'mitreAttack') url = '/vulnerabilities/api/mitre-attack/status';
        
        const data = await api.get(url);
        
        // Route to appropriate updater
        if (type === 'nvd') updateNvdUI(data);
        else if (type === 'euvd') updateEuvdUI(data);
        else if (type === 'mitre') updateMitreUI(data);
        else if (type === 'mitreAttack') updateMitreAttackUI(data);

        console.log(`[Sync] ${type.toUpperCase()} status:`, data);
    } catch (error) {
        console.error(`[Sync] Error checking ${type} status:`, error);
        // Show error state
    }
}
```

**Called by**:
- Initial page load (all 4 types)
- Polling interval (every 3 seconds)
- After sync start confirmation

## 8️⃣ Start Sync Function

```javascript
async function startSync(type, mode) {
    const msg = mode 
        ? `Iniciar sincronização ${mode === 'incremental' ? 'incremental' : 'completa'}?` 
        : `Iniciar sincronização ${type.toUpperCase()}?`;
    
    // Confirmation dialog
    if (!confirm(msg)) return;
    
    try {
        let url;
        if (type === 'nvd') url = '/vulnerabilities/api/sync/start';
        else if (type === 'euvd') url = '/api/euvd/sync/latest';
        else if (type === 'mitre') url = '/api/mitre/enrich';
        
        const body = mode ? { mode } : {};
        
        console.log(`[Sync] Starting ${type}${mode ? ` (${mode})` : ''}...`);
        await api.post(url, body);
        showToast('Operação iniciada!', 'success');
        
        // Start polling for updates
        await checkStatus(type);
        startPolling(type);
    } catch (error) {
        console.error(`[Sync] Error starting ${type}:`, error);
        showToast(error.message || `Erro ao iniciar sincronização ${type}`, 'error', 5000);
    }
}
```

**Parameters**:
- `type`: Module name (nvd, euvd, mitre, mitreAttack)
- `mode`: Optional (incremental, full) - NVD only

## 9️⃣ Cancel Sync Function

```javascript
async function cancelSync(type) {
    if (!confirm('Deseja cancelar a sincronização?')) return;
    try {
        const url = type === 'nvd' 
            ? '/vulnerabilities/api/sync/cancel' 
            : `/api/${type}/sync/cancel`;
        console.log(`[Sync] Cancelling ${type}...`);
        await api.post(url, {});
        showToast('Cancelamento solicitado', 'info');
        await checkStatus(type);
    } catch (error) {
        console.error(`[Sync] Error cancelling ${type}:`, error);
        showToast(`Erro ao cancelar ${type}`, 'error');
    }
}
```

**Features**:
- User confirmation required
- Console logging
- Status check after cancel
- Error notification

## 🔟 Polling Management

```javascript
const intervals = { 
    nvd: null, 
    euvd: null, 
    mitre: null, 
    mitreAttack: null 
};

function startPolling(type) {
    if (!intervals[type]) {
        console.log(`[Sync] Starting polling for ${type}`);
        intervals[type] = setInterval(() => checkStatus(type), 3000);
    }
}

function stopPolling(type) {
    if (intervals[type]) {
        console.log(`[Sync] Stopping polling for ${type}`);
        clearInterval(intervals[type]);
        intervals[type] = null;
    }
}
```

**Polling Interval**: 3 seconds (3000ms)

**Why separate polling**:
- Each module can run independently
- Cancel one without affecting others
- Cleaner memory management
- Easier to debug

## 1️⃣1️⃣ Event Listeners

### NVD Buttons
```javascript
if (elements.nvd.btns.incremental) {
    elements.nvd.btns.incremental.addEventListener('click', function() {
        this.blur();  // Remove focus ring
        startSync('nvd', 'incremental');
    });
    
    // Keyboard support
    elements.nvd.btns.incremental.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this.click();
        }
    });
}
```

**Features**:
- Click handles
- Keyboard support (Enter, Space)
- Removes focus outline after click
- Confirmation required

### EUVD Button
```javascript
if (elements.euvd.btn) {
    elements.euvd.btn.addEventListener('click', function() {
        this.blur();
        startSync('euvd');
    });
}
```

### MITRE Button
```javascript
if (elements.mitre.btn) {
    elements.mitre.btn.addEventListener('click', async function() {
        this.blur();
        try {
            if (!confirm('Iniciar enriquecimento MITRE?')) return;
            await api.post('/api/mitre/sync');
            showToast('Enriquecimento iniciado!', 'success');
            checkStatus('mitre');
            startPolling('mitre');
        } catch (err) {
            console.error('[Sync] Error starting MITRE enrichment:', err);
            showToast('Erro ao iniciar enriquecimento MITRE: ' + err.message, 'error', 5000);
        }
    });
}
```

### MITRE ATT&CK Buttons
```javascript
if (elements.mitreAttack.btns.sync) {
    elements.mitreAttack.btns.sync.addEventListener('click', async function() {
        // Sync Framework
        if (!confirm('Sincronizar framework MITRE ATT&CK?')) return;
        await api.post('/vulnerabilities/api/mitre-attack/sync');
        // ... polling
    });
}

if (elements.mitreAttack.btns.map) {
    elements.mitreAttack.btns.map.addEventListener('click', async function() {
        // Map CVEs
        if (!confirm('Mapear CVEs para técnicas MITRE ATT&CK?')) return;
        await api.post('/vulnerabilities/api/mitre-attack/map');
        // ... polling
    });
}
```

## 🎯 Console Logging Strategy

Prefixed logging for easy filtering:

```javascript
console.log('[Sync Page] Initializing...');
console.log('[Sync] Starting nvd...');
console.error('[Sync] Error checking nvd status:', error);
```

**DevTools Filter**: Type `[Sync]` in console filter for focused debugging

## 🧹 Cleanup on Unload

```javascript
window.addEventListener('beforeunload', () => {
    Object.keys(intervals).forEach(type => stopPolling(type));
});
```

**Purpose**: Prevent memory leaks and orphaned intervals

## 📊 Data Flow Diagram

```
User Click
    ↓
Event Listener (click/keypress)
    ↓
Confirmation Dialog
    ↓
API POST /start
    ↓
Success Toast
    ↓
checkStatus()  ─→ API GET /status
    ↓
Update UI (updateNvdUI, etc)
    ↓
startPolling() ─→ setInterval(checkStatus, 3000)
    ↓
    ├─→ Complete = showToast + stopPolling()
    ├─→ Failed = showToast + stopPolling()
    └─→ Running = continue polling
```

## 🔗 API Endpoints

### NVD
```
GET  /vulnerabilities/api/sync/status
POST /vulnerabilities/api/sync/start    {mode: 'incremental'|'full'}
POST /vulnerabilities/api/sync/cancel   {}
```

### EUVD
```
GET  /api/euvd/sync/status
POST /api/euvd/sync/latest  {}
```

### MITRE
```
GET  /api/mitre/sync/status
POST /api/mitre/sync        {}
POST /api/mitre/enrich      {}
```

### MITRE ATT&CK
```
GET  /vulnerabilities/api/mitre-attack/status
POST /vulnerabilities/api/mitre-attack/sync  {}
POST /vulnerabilities/api/mitre-attack/map   {}
```

## 🧪 Testing Checklist

- [x] All 4 modules initialize on page load
- [x] Buttons disabled during sync
- [x] Cancel button appears when running
- [x] Progress bar updates in real-time
- [x] Toast notifications appear
- [x] Keyboard navigation works (Tab, Enter, Space)
- [x] Error handling shows user-friendly messages
- [x] Console logging aids debugging
- [x] Memory cleanup on page unload
- [x] CSRF token sent with POST requests

## 📖 Related Documentation

- **[Settings JS Guide](../SETTINGS_JS_GUIDE.md)** - Similar patterns
- **[Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)** - Network request
- **[Console API](https://developer.mozilla.org/en-US/docs/Web/API/Console)** - Debugging
- **[Event Handling](https://developer.mozilla.org/en-US/docs/Web/API/Event)** - DOM events

---

**Version**: 1.0
**Last Updated**: 2024
**Dependencies**: None (Vanilla JS)
**Browser Support**: ES6+ compatible
**Maintenance Status**: Production Ready
