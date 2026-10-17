// State
let criteria = [
    { id: 1, market: "İlk Yarı Skoru", selection: "0:0", odd: 2.20, tolerance: "0.05" }
];
let matchMode = "AND"; // "AND" or "OR"
let currentResults = [];
let marketsCatalog = {};
let isScanning = false;
let nextId = 2;

// DOM Elements
const criteriaContainer = document.getElementById('criteriaContainer');
const btnModeAND = document.getElementById('btnModeAND');
const btnModeOR = document.getElementById('btnModeOR');
const inputLeague = document.getElementById('inputLeague');
const inputMatchText = document.getElementById('inputMatchText');
const searchSummary = document.getElementById('searchCriteriaSummary');

const resultsList = document.getElementById('resultsList');
const resultsCountBadge = document.getElementById('resultsCountBadge');
const emptyState = document.getElementById('emptyState');
const loadingState = document.getElementById('loadingState');
const selectSort = document.getElementById('selectSort');

const scanningBanner = document.getElementById('scanningBanner');
const scanStatusMsg = document.getElementById('scanStatusMsg');
const scanPercentText = document.getElementById('scanPercentText');
const scanProgressBar = document.getElementById('scanProgressBar');
const matchCountBadge = document.getElementById('matchCountBadge');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const rescanIcon = document.getElementById('rescanIcon');

document.addEventListener('DOMContentLoaded', () => {
    renderCriteriaRows();
    updateSummary();
    fetchStatus();
    fetchMarketsCatalog();
    initProgressStream();

    // Setup team/league enter triggers
    [inputLeague, inputMatchText].forEach(el => {
        if (el) {
            el.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') executeSearch();
            });
        }
    });

    // Initial search
    setTimeout(() => {
        executeSearch();
    }, 1200);
});

// Render dynamic criteria rows
function renderCriteriaRows() {
    criteriaContainer.innerHTML = criteria.map((c, index) => {
        const canDelete = criteria.length > 1;
        return `
        <div class="glass-card p-4 rounded-xl border border-slate-700/80 bg-slate-900/60 relative group" id="crit-row-${c.id}">
            <div class="flex items-center justify-between pb-2 mb-3 border-b border-slate-800">
                <div class="flex items-center space-x-2">
                    <span class="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-400 font-bold text-xs flex items-center justify-center border border-emerald-500/30">
                        ${index + 1}
                    </span>
                    <span class="text-xs font-bold text-slate-200">
                        Seçenek ${index + 1}
                    </span>
                    ${index > 0 ? `
                        <span class="text-[10px] uppercase font-extrabold px-1.5 py-0.2 rounded ${matchMode === 'AND' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}">
                            ${matchMode === 'AND' ? 'VE' : 'VEYA'}
                        </span>
                    ` : ''}
                </div>

                ${canDelete ? `
                    <button type="button" onclick="removeCriterionRow(${c.id})" class="text-xs text-slate-500 hover:text-red-400 transition p-1" title="Kriteri Kaldır">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                ` : ''}
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <!-- Market Type -->
                <div class="space-y-1">
                    <label class="block text-[11px] font-semibold text-slate-400">Market Türü</label>
                    <input type="text" list="globalMarketList" value="${escapeHtml(c.market)}" oninput="updateCriterion(${c.id}, 'market', this.value)" placeholder="İlk Yarı Skoru, MS..." class="w-full px-3 py-2 rounded-xl bg-slate-950/80 border border-slate-700 focus:border-emerald-500 text-xs text-white placeholder-slate-500">
                </div>

                <!-- Selection -->
                <div class="space-y-1">
                    <label class="block text-[11px] font-semibold text-slate-400">Seçim / Skor</label>
                    <input type="text" list="globalSelectionList" value="${escapeHtml(c.selection)}" oninput="updateCriterion(${c.id}, 'selection', this.value)" placeholder="0:0, MS 1, 2,5 Üst..." class="w-full px-3 py-2 rounded-xl bg-slate-950/80 border border-slate-700 focus:border-emerald-500 text-xs text-white placeholder-slate-500">
                </div>

                <!-- Target Odd -->
                <div class="space-y-1">
                    <div class="flex items-center justify-between text-[11px] font-semibold text-slate-400">
                        <span>Hedef Oran</span>
                        <span class="text-emerald-400 font-bold">${parseFloat(c.odd || 0).toFixed(2)}</span>
                    </div>
                    <div class="relative flex items-center">
                        <button type="button" onclick="adjustCriterionOdd(${c.id}, -0.05)" class="absolute left-1.5 text-slate-400 hover:text-white px-1.5 py-0.5">
                            <i class="fa-solid fa-minus text-[10px]"></i>
                        </button>
                        <input type="number" step="0.01" value="${c.odd}" oninput="updateCriterion(${c.id}, 'odd', this.value)" class="w-full text-center px-6 py-2 rounded-xl bg-slate-950/80 border border-slate-700 focus:border-emerald-500 text-xs font-bold text-emerald-400">
                        <button type="button" onclick="adjustCriterionOdd(${c.id}, 0.05)" class="absolute right-1.5 text-slate-400 hover:text-white px-1.5 py-0.5">
                            <i class="fa-solid fa-plus text-[10px]"></i>
                        </button>
                    </div>
                </div>

                <!-- Tolerance -->
                <div class="space-y-1">
                    <label class="block text-[11px] font-semibold text-slate-400">Hassasiyet / Tolerans</label>
                    <select onchange="updateCriterion(${c.id}, 'tolerance', this.value)" class="w-full px-2.5 py-2 rounded-xl bg-slate-950/80 border border-slate-700 focus:border-emerald-500 text-xs text-white">
                        <option value="0.00" ${c.tolerance === '0.00' ? 'selected' : ''}>🎯 Birebir Tam (${parseFloat(c.odd).toFixed(2)})</option>
                        <option value="0.02" ${c.tolerance === '0.02' ? 'selected' : ''}>🤏 Dar (±0.02)</option>
                        <option value="0.05" ${c.tolerance === '0.05' ? 'selected' : ''}>⚖️ Orta (±0.05)</option>
                        <option value="0.10" ${c.tolerance === '0.10' ? 'selected' : ''}>🌊 Geniş (±0.10)</option>
                        <option value="0.20" ${c.tolerance === '0.20' ? 'selected' : ''}>🚀 Esnek (±0.20)</option>
                    </select>
                </div>
            </div>
        </div>
        `;
    }).join('');
}

function addCriterionRow() {
    criteria.push({
        id: nextId++,
        market: "Maç Sonucu",
        selection: "MS 1",
        odd: 1.80,
        tolerance: "0.05"
    });
    renderCriteriaRows();
    updateSummary();
}

function removeCriterionRow(id) {
    if (criteria.length <= 1) return;
    criteria = criteria.filter(c => c.id !== id);
    renderCriteriaRows();
    updateSummary();
    executeSearch();
}

function updateCriterion(id, field, value) {
    const item = criteria.find(c => c.id === id);
    if (!item) return;

    if (field === 'odd') {
        item.odd = parseFloat(value || 0);
    } else {
        item[field] = value;
    }
    updateSummary();
}

function adjustCriterionOdd(id, delta) {
    const item = criteria.find(c => c.id === id);
    if (!item) return;
    let val = parseFloat(item.odd || 2.20);
    val = Math.max(1.01, +(val + delta).toFixed(2));
    item.odd = val;
    renderCriteriaRows();
    updateSummary();
    executeSearch();
}

function setMatchMode(mode) {
    matchMode = mode;
    if (mode === 'AND') {
        btnModeAND.className = "px-3 py-1.5 rounded-lg text-xs font-bold transition bg-emerald-600 text-white shadow-sm flex items-center space-x-1.5";
        btnModeOR.className = "px-3 py-1.5 rounded-lg text-xs font-bold text-slate-400 hover:text-white transition flex items-center space-x-1.5";
    } else {
        btnModeOR.className = "px-3 py-1.5 rounded-lg text-xs font-bold transition bg-emerald-600 text-white shadow-sm flex items-center space-x-1.5";
        btnModeAND.className = "px-3 py-1.5 rounded-lg text-xs font-bold text-slate-400 hover:text-white transition flex items-center space-x-1.5";
    }
    renderCriteriaRows();
    updateSummary();
    executeSearch();
}

function applyMultiPreset(presetCriteria, mode) {
    matchMode = mode || 'AND';
    criteria = presetCriteria.map((c, i) => ({
        id: i + 1,
        market: c.market,
        selection: c.selection,
        odd: parseFloat(c.odd),
        tolerance: String(c.tolerance || '0.05')
    }));
    nextId = criteria.length + 1;
    setMatchMode(matchMode);
    renderCriteriaRows();
    updateSummary();
    executeSearch();
}

function resetFilters() {
    criteria = [
        { id: 1, market: "İlk Yarı Skoru", selection: "0:0", odd: 2.20, tolerance: "0.05" }
    ];
    matchMode = "AND";
    inputLeague.value = "";
    inputMatchText.value = "";
    setMatchMode("AND");
    renderCriteriaRows();
    updateSummary();
    executeSearch();
}

function broadenAllTolerances() {
    criteria.forEach(c => c.tolerance = "0.10");
    renderCriteriaRows();
    updateSummary();
    executeSearch();
}

function updateSummary() {
    const modeBadge = matchMode === 'AND' ? '🔗 [Aynı Maçta TÜMÜ]' : '🔀 [HERHANGİ BİRİ]';
    const parts = criteria.map((c, i) => {
        const m = c.market || 'Market';
        const s = c.selection || 'Seçim';
        const o = parseFloat(c.odd || 0).toFixed(2);
        return `${m} (${s}) @ ${o}`;
    });
    searchSummary.textContent = `${modeBadge} ${parts.join(' + ')}`;
}

// Fetch Status & Markets
async function fetchStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        updateStatusUI(data);
    } catch (e) {
        console.error('Status fetch error:', e);
    }
}

async function fetchMarketsCatalog() {
    try {
        const res = await fetch('/api/markets');
        marketsCatalog = await res.json();
        updateMarketDatalist();
    } catch (e) {
        console.error('Markets catalog fetch error:', e);
    }
}

function updateMarketDatalist() {
    const marketList = document.getElementById('globalMarketList');
    if (!marketList) return;

    const existingNames = new Set(Array.from(marketList.options).map(o => o.value));
    for (const mName of Object.keys(marketsCatalog)) {
        if (!existingNames.has(mName)) {
            const opt = document.createElement('option');
            opt.value = mName;
            marketList.appendChild(opt);
        }
    }
}

function updateStatusUI(data) {
    matchCountBadge.textContent = `${data.matches_count || 0} Maç`;
    if (data.is_scanning) {
        isScanning = true;
        statusDot.className = "w-2.5 h-2.5 rounded-full bg-amber-400 scanning-pulse";
        statusText.textContent = "Taranıyor...";
        scanningBanner.classList.remove('hidden');
        rescanIcon.classList.add('animate-spin');

        const prog = data.progress || {};
        scanStatusMsg.textContent = prog.status || "Bülten taranıyor...";
        scanPercentText.textContent = `%${prog.percent || 0}`;
        scanProgressBar.style.width = `${prog.percent || 0}%`;
    } else {
        isScanning = false;
        statusDot.className = "w-2.5 h-2.5 rounded-full bg-emerald-400";
        statusText.textContent = "Bülten Hazır";
        scanningBanner.classList.add('hidden');
        rescanIcon.classList.remove('animate-spin');
    }
}

// SSE Live Progress Streaming
function initProgressStream() {
    try {
        const eventSource = new EventSource('/api/stream-progress');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const wasScanning = isScanning;
            updateStatusUI(data);

            if (wasScanning && !data.is_scanning) {
                fetchMarketsCatalog();
                executeSearch();
            }
        };
        eventSource.onerror = () => {
            eventSource.close();
            setTimeout(initProgressStream, 5000);
        };
    } catch (e) {
        console.error('SSE connection failed:', e);
    }
}

async function triggerScan() {
    try {
        rescanIcon.classList.add('animate-spin');
        await fetch('/api/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tab_type: 1, bulletin_type: 2 })
        });
        fetchStatus();
    } catch (e) {
        console.error('Trigger scan error:', e);
    }
}

// Execute Multi-Criteria Search
async function executeSearch() {
    loadingState.classList.remove('hidden');
    resultsList.innerHTML = '';
    emptyState.classList.add('hidden');

    const formattedCriteria = criteria.map(c => ({
        market: c.market ? c.market.trim() : null,
        selection: c.selection ? c.selection.trim() : null,
        target_odd: c.odd ? parseFloat(c.odd) : null,
        tolerance: c.tolerance ? parseFloat(c.tolerance) : 0.05
    }));

    const payload = {
        criteria: formattedCriteria,
        match_mode: matchMode,
        league: inputLeague.value.trim() || null,
        match_text: inputMatchText.value.trim() || null
    };

    try {
        const res = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        currentResults = data.results || [];
        sortAndRenderResults();
    } catch (e) {
        console.error('Search error:', e);
        resultsList.innerHTML = `<div class="col-span-full p-4 rounded-xl bg-red-950/40 border border-red-500/30 text-red-300 text-sm">Arama hatası: ${e.message}</div>`;
    } finally {
        loadingState.classList.add('hidden');
    }
}

// Sort & Render Results
function sortAndRenderResults() {
    const sortBy = selectSort.value;
    const sorted = [...currentResults];

    if (sortBy === 'odd_asc') {
        sorted.sort((a, b) => a.odd - b.odd);
    } else if (sortBy === 'odd_desc') {
        sorted.sort((a, b) => b.odd - a.odd);
    } else if (sortBy === 'time') {
        sorted.sort((a, b) => (a.match_time || '').localeCompare(b.match_time || ''));
    } else if (sortBy === 'league') {
        sorted.sort((a, b) => (a.league || '').localeCompare(b.league || ''));
    }

    resultsCountBadge.textContent = `${sorted.length} Maç Bulundu`;

    if (sorted.length === 0) {
        emptyState.classList.remove('hidden');
        resultsList.innerHTML = '';
        return;
    }

    emptyState.classList.add('hidden');
    resultsList.innerHTML = sorted.map(item => renderMatchCard(item)).join('');
}

function renderMatchCard(item) {
    const mbsBadgeClass = item.mbs === 1
        ? 'bg-amber-500/20 text-amber-400 border-amber-500/40 font-bold'
        : 'bg-slate-800 text-slate-400 border-slate-700 font-medium';

    const matchedOdds = item.matched_odds || [{
        market_name: item.market_name,
        selection: item.selection,
        odd_str: item.odd_str,
        odd: item.odd
    }];

    // Compute combined total odd if multiple criteria in AND mode
    let combinedOddText = "";
    if (matchedOdds.length > 1) {
        const prod = matchedOdds.reduce((acc, cur) => acc * cur.odd, 1.0);
        combinedOddText = `
        <div class="mt-2 pt-2 border-t border-slate-800 flex items-center justify-between text-xs">
            <span class="text-emerald-400 font-bold flex items-center space-x-1">
                <i class="fa-solid fa-layer-group text-[10px]"></i>
                <span>Kombine Oran:</span>
            </span>
            <span class="px-2 py-0.5 rounded-lg bg-emerald-500/20 text-emerald-300 font-black">
                ${prod.toFixed(2)}
            </span>
        </div>
        `;
    }

    const oddsHtml = matchedOdds.map(odd => `
        <div class="bg-slate-900/90 rounded-xl p-2.5 border border-slate-800 flex items-center justify-between">
            <div class="space-y-0.5">
                <div class="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
                    ${escapeHtml(odd.market_name)}
                </div>
                <div class="text-xs font-extrabold text-white flex items-center space-x-1.5">
                    <span class="text-emerald-400">●</span>
                    <span>${escapeHtml(odd.selection)}</span>
                </div>
            </div>
            <div class="badge-odd px-2.5 py-1 rounded-lg text-sm font-black tracking-tight">
                ${odd.odd_str}
            </div>
        </div>
    `).join('');

    return `
    <div class="glass-card rounded-2xl p-5 flex flex-col justify-between relative group">
        <!-- Card Header: League & Time & MBS -->
        <div class="flex items-center justify-between text-xs pb-3 border-b border-slate-800/80 mb-3">
            <div class="flex items-center space-x-2 truncate max-w-[70%]">
                <i class="fa-solid fa-trophy text-emerald-500 text-[11px]"></i>
                <span class="text-slate-300 font-semibold truncate" title="${escapeHtml(item.league)}">
                    ${escapeHtml(item.league)}
                </span>
            </div>
            <div class="flex items-center space-x-2">
                <span class="px-2 py-0.5 rounded text-[11px] border ${mbsBadgeClass}">
                    MBS ${item.mbs}
                </span>
                <span class="text-slate-400 text-[11px] font-medium whitespace-nowrap">
                    ${escapeHtml(item.match_time || '')}
                </span>
            </div>
        </div>

        <!-- Teams -->
        <div class="space-y-1 mb-4">
            <div class="flex items-center justify-between">
                <span class="text-sm font-bold text-white group-hover:text-emerald-300 transition truncate">
                    ${escapeHtml(item.home_team)}
                </span>
            </div>
            <div class="text-[11px] text-slate-500 font-semibold">vs</div>
            <div class="flex items-center justify-between">
                <span class="text-sm font-bold text-white group-hover:text-emerald-300 transition truncate">
                    ${escapeHtml(item.away_team)}
                </span>
            </div>
        </div>

        <!-- Matched Odds List -->
        <div class="space-y-2 mb-4">
            ${oddsHtml}
            ${combinedOddText}
        </div>

        <!-- Card Footer: Copy / Share Details (No external links) -->
        <div class="flex items-center space-x-2 pt-2 border-t border-slate-800/80">
            <button onclick="copyMatchDetails('${escapeHtml(item.match_title)}', this)" class="flex-1 py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold text-center border border-slate-700 transition flex items-center justify-center space-x-1.5 cursor-pointer">
                <i class="fa-solid fa-copy text-emerald-400"></i>
                <span>Maç ve Oran Bilgisini Kopyala</span>
            </button>
        </div>
    </div>
    `;
}

function copyMatchDetails(match, btn) {
    navigator.clipboard.writeText(`Goal Signals Iddaa Bot: ${match}`);
    const span = btn.querySelector('span');
    const icon = btn.querySelector('i');
    const oldText = span.textContent;
    span.textContent = "Kopyalandı!";
    icon.className = "fa-solid fa-check text-emerald-400";
    setTimeout(() => {
        span.textContent = oldText;
        icon.className = "fa-solid fa-copy text-emerald-400";
    }, 1500);
}

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
