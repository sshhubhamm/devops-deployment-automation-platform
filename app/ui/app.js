const API_BASE = "http://127.0.0.1:5000";

let allPods = [];
let filteredPods = [];

// Modal controls
const logsModal = document.getElementById('logs-modal');
const modalTitle = document.getElementById('modal-pod-title');
const logsContent = document.getElementById('logs-content');
const podsBody = document.getElementById('pods-body');
const podsCount = document.getElementById('pods-count');
const podsSearch = document.getElementById('pods-search');
const namespaceFilter = document.getElementById('namespace-filter');
const podsRefresh = document.getElementById('pods-refresh');

// Status badge classes
function getStatusClass(status) {
    switch (status.toLowerCase()) {
        case 'running': return 'badge green';
        case 'pending': return 'badge orange';
        case 'succeeded': return 'badge green';
        case 'failed': 
        case 'error': 
        case 'crashloopbackoff': return 'badge red';
        default: return 'badge blue';
    }
}

function getReadyClass(ready) {
    if (ready === '0/0') return 'badge blue';
    const [readyCount, total] = ready.split('/').map(Number);
    if (readyCount === total && total > 0) return 'badge green';
    return 'badge orange';
}

function showSkeleton() {
    podsBody.innerHTML = `
        <tr><td colspan="6" style="text-align:center;padding:40px;color:var(--muted)">
            <div class="skeleton" style="height:20px;width:200px;margin:0 auto 20px"></div>
            Loading pods...
        </td></tr>
    `;
}

async function loadPods() {
    try {
        showSkeleton();
        
        const podsRes = await fetch(`${API_BASE}/api/k8s/pods`);
        const pods = await podsRes.json();
        
        allPods = pods;
        filteredPods = pods;
        applyFilters();
        podsCount.innerText = filteredPods.length;
        
    } catch (err) {
        console.error("Pods load error:", err);
        podsBody.innerHTML = `
            <tr><td colspan="6" class="error">Failed to load pods: ${err.message}</td></tr>
        `;
        podsCount.innerText = "Error";
    }
}

function renderPods(pods) {
    if (!pods || pods.length === 0) {
        podsBody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--muted)">No pods found</td></tr>';
        return;
    }
    
    podsBody.innerHTML = pods.map(pod => {
        // Compute ready from status or default
        const readyStatus = pod.status === 'Running' ? '1/1' : '0/1';
        return `
        <tr>
            <td>${pod.name}</td>
            <td>${pod.namespace}</td>
            <td><span class="${getStatusClass(pod.status)}">${pod.status}</span></td>
            <td><span class="${getReadyClass(readyStatus)}">${readyStatus}</span></td>
            <td>${pod.node || 'N/A'}</td>
            <td>${pod.ip || 'N/A'}</td>
            <td>
                <button class="btn-view" onclick="showPodLogs('${pod.name}', '${pod.namespace}')">View Logs</button>
            </td>
        </tr>
    `;
    }).join('');
}

function applyFilters() {
    const searchTerm = podsSearch.value.toLowerCase();
    const nsFilter = namespaceFilter.value;
    
    filteredPods = allPods.filter(pod => {
        const matchesSearch = pod.name.toLowerCase().includes(searchTerm) ||
                             pod.namespace.toLowerCase().includes(searchTerm);
        const matchesNS = !nsFilter || pod.namespace === nsFilter;
        return matchesSearch && matchesNS;
    });
    
    renderPods(filteredPods);
    updateNamespaceFilter();
    podsCount.innerText = filteredPods.length;
}

function updateNamespaceFilter() {
    const namespaces = [...new Set(allPods.map(p => p.namespace))].sort();
    namespaceFilter.innerHTML = '<option value="">All Namespaces</option>' +
        namespaces.map(ns => `<option value="${ns}">${ns}</option>`).join('');
}

async function showPodLogs(podName, namespace = 'default') {
    try {
        modalTitle.textContent = `Logs: ${podName} (${namespace})`;
        logsContent.textContent = 'Loading logs...';
        logsModal.classList.add('show');
        
        const url = new URL(`${API_BASE}/api/k8s/logs`);
        url.searchParams.append('pod', podName);
        url.searchParams.append('namespace', namespace);
        const res = await fetch(url);
        const data = await res.json();
        logsContent.textContent = data.logs || data.error || 'No logs available';
    } catch (err) {
        logsContent.textContent = `Error loading logs: ${err.message}`;
    }
}

// Event listeners
function initEventListeners() {
    podsSearch.addEventListener('input', applyFilters);
    namespaceFilter.addEventListener('change', applyFilters);
    podsRefresh.addEventListener('click', loadPods);
    
    // Modal close
    logsModal.addEventListener('click', (e) => {
        if (e.target === logsModal) logsModal.classList.remove('show');
    });
    document.querySelector('.modal-close').addEventListener('click', () => {
        logsModal.classList.remove('show');
    });
    
    // ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && logsModal.classList.contains('show')) {
            logsModal.classList.remove('show');
        }
    });
}

// Dashboard cards - Fixed error handling (show 0 on fail)
async function loadDashboardCards() {
    try {
        // Pods count (sync with table)
        document.getElementById("pods-count").innerText = allPods.length || 0;

        // Deployments
        try {
            const depRes = await fetch(`${API_BASE}/api/k8s/deployments`);
            if (depRes.ok) {
                const deps = await depRes.json();
                if (Array.isArray(deps) && !deps.some(d => 'error' in d)) {
                    document.getElementById("deploy-count").innerText = deps.length;
                } else {
                    document.getElementById("deploy-count").innerText = "0";
                }
            } else {
                document.getElementById("deploy-count").innerText = "0";
            }
        } catch (depErr) {
            console.error("Deployments error:", depErr);
            document.getElementById("deploy-count").innerText = "0";
        }

        // Jenkins (graceful fail)
        try {
            const jRes = await fetch(`${API_BASE}/api/jenkins/status`);
            if (jRes.ok) {
                const j = await jRes.json();
                document.getElementById("build-status").innerText = j.status || "N/A";
            } else {
                document.getElementById("build-status").innerText = "N/A";
            }
        } catch (jErr) {
            console.error("Jenkins error:", jErr);
            document.getElementById("build-status").innerText = "N/A";
        }

        // Metrics (static for now)
        document.getElementById("cpu-usage").innerText = "45%";
        document.getElementById("memory-usage").innerText = "62%";

    } catch (err) {
        console.error("Cards error:", err);
        // Fallback to 0/N/A on total fail
        document.getElementById("pods-count").innerText = "0";
        document.getElementById("deploy-count").innerText = "0";
        document.getElementById("build-status").innerText = "N/A";
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadPods();
    loadDashboardCards();
    
    // Real-time refresh every 10s (pods only, no flicker)
    setInterval(() => {
        loadPods();
        loadDashboardCards();
    }, 10000);
});
