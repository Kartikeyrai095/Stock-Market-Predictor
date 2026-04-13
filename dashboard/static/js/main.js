/* ══════════════════════════════════════════════════════════
   ANTIGRAVITY.AI — FULL DASHBOARD JAVASCRIPT (SPA)
══════════════════════════════════════════════════════════ */

/* ─── State ─── */
let currentPage    = 'dashboard';
let currentTab     = 'stocks';
let currentFilter  = 'all';
let currentNewsFilter = 'all';
let allRecsData    = [];
let allNewsData    = [];
let searchTimeout  = null;

/* ─── Init ─── */
document.addEventListener('DOMContentLoaded', () => {
    initSidebarState();
    loadPage('dashboard');
    fetchSystemStatus();
    initSearch();
    setMarketStatus();

    // Refresh system status every 5 minutes
    setInterval(fetchSystemStatus, 5 * 60 * 1000);
});

/* ─── Sidebar ─── */
function initSidebarState() {
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
        document.getElementById('sidebar').classList.remove('open');
    }
}

function toggleSidebar() {
    const sidebar  = document.getElementById('sidebar');
    const overlay  = document.getElementById('sidebar-overlay');
    const isMobile = window.innerWidth <= 768;

    if (isMobile) {
        sidebar.classList.toggle('open');
        overlay.classList.toggle('visible');
    } else {
        // On desktop, toggle the main wrapper's left margin (collapse sidebar)
        const wrapper = document.getElementById('main-wrapper');
        const isCollapsed = sidebar.style.transform === 'translateX(-100%)';
        if (isCollapsed) {
            sidebar.style.transform = '';
            wrapper.style.marginLeft = 'var(--sidebar-w)';
        } else {
            sidebar.style.transform = 'translateX(-100%)';
            wrapper.style.marginLeft = '0';
        }
    }
}

function closeSidebar() {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebar-overlay').classList.remove('visible');
}

/* ─── Page Navigation ─── */
const PAGE_META = {
    dashboard:       { title: 'Dashboard',        icon: 'ph-squares-four',         load: loadDashboard },
    recommendations: { title: 'Recommendations',  icon: 'ph-target',               load: loadRecommendations },
    strategies:      { title: 'Strategy Lab',     icon: 'ph-chart-line-up',        load: loadStrategies },
    news:            { title: 'News Intelligence', icon: 'ph-newspaper-clipping',   load: loadNews },
    agents:          { title: 'Agent Status',      icon: 'ph-robot',               load: loadAgents },
    settings:        { title: 'Settings',          icon: 'ph-gear',                load: loadSettings },
};

function navigate(page, clickedEl) {
    if (page === currentPage) { closeSidebar(); return; }
    currentPage = page;

    // Update active in sidebar
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    const sidebarLink = document.querySelector(`.nav-item[data-page="${page}"]`);
    if (sidebarLink) sidebarLink.classList.add('active');

    // Update bottom nav
    document.querySelectorAll('.bottom-nav-item').forEach(el => el.classList.remove('active'));
    const bnItem = document.querySelector(`.bottom-nav-item[data-page="${page}"]`);
    if (bnItem) bnItem.classList.add('active');

    // Update breadcrumb
    const meta = PAGE_META[page];
    if (meta) {
        document.getElementById('breadcrumb-title').textContent = meta.title;
        document.getElementById('breadcrumb-icon').innerHTML = `<i class="ph ${meta.icon}"></i>`;
    }

    // Show/hide pages
    document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
    const target = document.getElementById(`page-${page}`);
    if (target) target.classList.remove('hidden');

    // Load data
    if (meta?.load) meta.load();

    closeSidebar();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
function loadPage(page) { navigate(page, null); }

/* ─── Market Status ─── */
function setMarketStatus() {
    const now = new Date();
    const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
    const day  = ist.getDay();
    const hour = ist.getHours();
    const min  = ist.getMinutes();
    const totalMins = hour * 60 + min;
    const isWeekday = day >= 1 && day <= 5;
    const isOpen = isWeekday && totalMins >= 555 && totalMins <= 930; // 9:15 – 15:30

    const badge = document.getElementById('market-status-badge');
    const text  = document.getElementById('market-status-text');
    const dot   = badge?.querySelector('.status-dot');
    if (!badge) return;
    if (isOpen) {
        text.textContent = 'Market Open';
        dot?.classList.remove('closed');
    } else {
        text.textContent = 'Market Closed';
        dot?.classList.add('closed');
    }
}

/* ═══════════════════════════════════
   DASHBOARD
═══════════════════════════════════ */
function loadDashboard() {
    fetchOverview();
    fetchDashboardRecs();
    fetchDashboardSentiment();
}

async function fetchOverview() {
    try {
        const res  = await fetch('/api/overview');
        const data = await res.json();
        const container = document.getElementById('market-overview');
        if (!container || data.status !== 'success') return;

        const LABEL_MAP = { NIFTY_50: 'NIFTY 50', SENSEX: 'SENSEX', BANK_NIFTY: 'NIFTY BANK' };
        container.innerHTML = '';
        for (const [key, info] of Object.entries(data.indices)) {
            const sign = info.change >= 0 ? '+' : '';
            const cls  = info.change > 0 ? 'up' : info.change < 0 ? 'down' : 'flat';
            container.innerHTML += `
                <div class="index-card">
                    <div class="ic-label">${LABEL_MAP[key] || key}</div>
                    <div class="ic-price">₹${Number(info.price).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                    <span class="ic-change ${cls}">
                        <i class="ph ph-${cls === 'up' ? 'trend-up' : cls === 'down' ? 'trend-down' : 'minus'}"></i>
                        ${sign}${info.change}%
                    </span>
                </div>`;
        }
    } catch (e) { console.error('Overview fetch failed', e); }
}

async function fetchDashboardRecs() {
    const container = document.getElementById('dashboard-rec-list');
    if (!container) return;
    try {
        const res  = await fetch('/api/recommendations?limit=4');
        const data = await res.json();
        const recs = (data.data || []).slice(0, 4);
        if (!recs.length) { container.innerHTML = '<div class="empty-state"><i class="ph ph-robot"></i>Waiting for next AI run...</div>'; return; }

        allRecsData = data.data || [];
        updateRecBadge(allRecsData.length);

        container.innerHTML = recs.map(r => `
            <div class="rec-compact">
                <div>
                    <div class="rc-ticker">${r.ticker} <span class="rec-strategy-tag">${r.strategy || 'Swing'}</span></div>
                    <div class="rc-name">${r.name || r.ticker}</div>
                    <div class="rc-confidence">Confidence ${r.confidence}%</div>
                </div>
                <div class="rc-prices">
                    <div class="rc-price-item"><span>Entry</span><strong>₹${fmt(r.entry)}</strong></div>
                    <div class="rc-price-item"><span>Target</span><strong style="color:var(--green)">₹${fmt(r.target)}</strong></div>
                    <div class="rc-price-item"><span>SL</span><strong style="color:var(--red)">₹${fmt(r.stop)}</strong></div>
                </div>
                <span class="action-badge action-${(r.action||'BUY').toLowerCase()}">${r.action}</span>
            </div>`).join('');

        // Update conviction
        const avgConfidence = recs.reduce((s, r) => s + (r.confidence || 75), 0) / recs.length;
        setConviction(Math.round(avgConfidence));
    } catch (e) { console.error('Dashboard recs failed', e); }
}

async function fetchDashboardSentiment() {
    const container = document.getElementById('dash-sentiment-list');
    if (!container) return;
    try {
        const res  = await fetch('/api/sentiment');
        const data = await res.json();
        const items = (data.data || []).slice(0, 3);
        if (!items.length) { container.innerHTML = '<p style="color:var(--text-3);font-size:.8rem;">No sentiment data yet.</p>'; return; }
        container.innerHTML = items.map(n => `
            <div class="dash-sentiment-item">
                <div class="dsi-row">
                    <span class="dsi-source">${n.source} · ${n.time}</span>
                    <span class="sentiment-badge ${(n.label||'').toLowerCase()}">${n.label}</span>
                </div>
                <div class="dsi-headline">${n.headline}</div>
            </div>`).join('');
    } catch (e) { console.error('Sentiment fetch failed', e); }
}

function setConviction(pct) {
    const fill  = document.getElementById('conviction-fill');
    const thumb = document.getElementById('conviction-thumb');
    const val   = document.getElementById('conviction-value');
    if (!fill) return;
    fill.style.width  = `${pct}%`;
    thumb.style.left  = `${pct}%`;
    const label = pct >= 60 ? 'Bullish' : pct <= 40 ? 'Bearish' : 'Neutral';
    const color = pct >= 60 ? 'var(--green)' : pct <= 40 ? 'var(--red)' : 'var(--amber)';
    val.textContent = `${pct}% ${label}`;
    val.style.color = color;
}

function updateRecBadge(count) {
    const badge = document.getElementById('rec-count-badge');
    if (badge) badge.textContent = count > 0 ? count : '';
}

/* ═══════════════════════════════════
   RECOMMENDATIONS PAGE
═══════════════════════════════════ */
function loadRecommendations() {
    fetchAllRecs();
}

async function fetchAllRecs() {
    const container = document.getElementById('full-rec-list');
    if (!container) return;
    container.innerHTML = '<div class="empty-state"><i class="ph ph-circle-notch spin"></i> Loading...</div>';

    try {
        const res  = await fetch(`/api/recommendations?type=${currentTab}`);
        const data = await res.json();
        allRecsData = data.data || [];
        updateRecBadge(allRecsData.length);
        renderRecs();
    } catch (e) { container.innerHTML = '<div class="empty-state"><i class="ph ph-warning"></i> Could not load recommendations.</div>'; }
}

function renderRecs() {
    const container = document.getElementById('full-rec-list');
    if (!container) return;

    let recs = [...allRecsData];
    if (currentFilter !== 'all') recs = recs.filter(r => r.action === currentFilter);

    const countEl = document.getElementById('rec-count-label');
    if (countEl) countEl.textContent = `${recs.length} signal${recs.length !== 1 ? 's' : ''}`;

    if (!recs.length) {
        container.innerHTML = `<div class="empty-state"><i class="ph ph-target"></i>No ${currentFilter !== 'all' ? currentFilter + ' ' : ''}signals for ${TAB_LABELS[currentTab]} yet. GitHub Actions will populate this after the next scheduled run.</div>`;
        return;
    }

    container.innerHTML = recs.map(r => `
        <div class="rec-card">
            <div class="rec-top">
                <div class="rec-ticker-block">
                    <div class="ticker">${r.ticker}
                        <span class="rec-strategy-tag">${r.strategy || 'Swing'}</span>
                    </div>
                    <div class="ticker-meta">
                        <span>${r.name || r.ticker}</span>
                        <span class="asset-type">${getAssetType(r.ticker)}</span>
                        <span style="color:var(--text-3)">· ${r.time || '—'}</span>
                    </div>
                </div>
                <div class="rec-right">
                    <div class="confidence-ring">
                        <strong>${r.confidence}%</strong>
                        <span>confidence</span>
                    </div>
                    <span class="action-badge action-${(r.action||'BUY').toLowerCase()}">${r.action}</span>
                </div>
            </div>
            <div class="rec-prices">
                <div class="rp-item">
                    <div class="rp-label">Entry Price</div>
                    <div class="rp-value rp-entry">₹${fmt(r.entry)}</div>
                </div>
                <div class="rp-item">
                    <div class="rp-label">Target</div>
                    <div class="rp-value rp-target">₹${fmt(r.target)}</div>
                </div>
                <div class="rp-item">
                    <div class="rp-label">Stop Loss</div>
                    <div class="rp-value rp-stop">₹${fmt(r.stop)}</div>
                </div>
            </div>
            <div class="rec-reason"><i class="ph ph-robot"></i> ${r.reasoning || 'AI analysis complete.'}</div>
        </div>`).join('');
}

const TAB_LABELS = { stocks: 'Stocks', mutual_funds: 'Mutual Funds', options: 'Options', indices: 'Indices' };

function switchTab(tab, el) {
    currentTab = tab;
    currentFilter = 'all';
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    document.querySelector('.chip[data-filter="all"]')?.classList.add('active');
    fetchAllRecs();
}

function filterRecs(filter, el) {
    currentFilter = filter;
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    renderRecs();
}

/* ═══════════════════════════════════
   STRATEGIES PAGE
═══════════════════════════════════ */
function loadStrategies() {
    fetchStrategies();
}

async function fetchStrategies() {
    const tbody = document.getElementById('strategy-table-body');
    if (!tbody) return;
    try {
        const res  = await fetch('/api/strategies');
        const data = await res.json();
        const items = data.data || [];

        if (!items.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="table-loading">No backtests run yet. Engine will populate after market close.</td></tr>';
            updateStratStats(null);
            return;
        }

        updateStratStats(items);
        tbody.innerHTML = items.map(s => `
            <tr>
                <td><strong${s.ticker}</strong></td>
                <td>${s.strategy}</td>
                <td style="color:${s.total_return_pct >= 0 ? 'var(--green)' : 'var(--red)'}">${s.total_return_pct?.toFixed(2)}%</td>
                <td>${s.win_rate_pct?.toFixed(1)}%</td>
                <td>${s.sharpe_ratio?.toFixed(2)}</td>
                <td style="color:var(--red)">${s.max_drawdown_pct?.toFixed(1)}%</td>
                <td>${s.total_trades}</td>
                <td>₹${Number(s.end_balance).toLocaleString('en-IN')}</td>
            </tr>`).join('');
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="8" class="table-loading">Could not load strategies.</td></tr>';
    }
}

function updateStratStats(items) {
    if (!items?.length) {
        ['strat-total-return','strat-win-rate','strat-drawdown','strat-sharpe'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '—';
        });
        return;
    }
    const avg = k => (items.reduce((s, i) => s + (i[k] || 0), 0) / items.length);
    document.getElementById('strat-total-return').textContent = `${avg('total_return_pct').toFixed(1)}%`;
    document.getElementById('strat-win-rate').textContent = `${avg('win_rate_pct').toFixed(1)}%`;
    document.getElementById('strat-drawdown').textContent  = `${avg('max_drawdown_pct').toFixed(1)}%`;
    document.getElementById('strat-sharpe').textContent    = avg('sharpe_ratio').toFixed(2);
}

/* ═══════════════════════════════════
   NEWS PAGE
═══════════════════════════════════ */
function loadNews() { fetchFullNews(); }

async function fetchFullNews() {
    const container = document.getElementById('full-news-list');
    if (!container) return;
    container.innerHTML = '<div class="empty-state"><i class="ph ph-circle-notch spin"></i> Loading...</div>';
    try {
        const res  = await fetch('/api/sentiment?full=1');
        const data = await res.json();
        allNewsData = data.data || [];

        // Overall sentiment badge
        const pos = allNewsData.filter(n => n.label === 'POSITIVE').length;
        const neg = allNewsData.filter(n => n.label === 'NEGATIVE').length;
        const overallBadge = document.getElementById('overall-sentiment-badge');
        if (overallBadge) {
            const overall = pos > neg ? 'POSITIVE' : neg > pos ? 'NEGATIVE' : 'NEUTRAL';
            overallBadge.innerHTML = `<i class="ph ph-activity"></i> Overall: <strong style="color:${overall==='POSITIVE'?'var(--green)':overall==='NEGATIVE'?'var(--red)':'var(--amber)'}">${overall}</strong>`;
        }

        renderNews();
    } catch (e) { container.innerHTML = '<div class="empty-state"><i class="ph ph-warning"></i> Could not load news.</div>'; }
}

function filterNews(filter, el) {
    currentNewsFilter = filter;
    document.querySelectorAll('#page-news .tab-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
    renderNews();
}

function renderNews() {
    const container = document.getElementById('full-news-list');
    if (!container) return;
    let items = [...allNewsData];
    if (currentNewsFilter !== 'all') {
        items = items.filter(n => n.label?.toLowerCase() === currentNewsFilter);
    }
    if (!items.length) {
        container.innerHTML = `<div class="empty-state"><i class="ph ph-newspaper-clipping"></i> No ${currentNewsFilter} news.</div>`;
        return;
    }
    container.innerHTML = items.map(n => `
        <div class="news-card">
            <div class="nc-header">
                <span class="nc-source">${n.source}</span>
                <span class="nc-time">${n.time}</span>
            </div>
            <div class="nc-headline">${n.headline}</div>
            <span class="sentiment-badge ${(n.label||'').toLowerCase()}">${n.label}</span>
            ${n.score ? `<span class="nc-score">Score: ${Math.abs(n.score).toFixed(1)}</span>` : ''}
        </div>`).join('');
}

/* ═══════════════════════════════════
   AGENTS PAGE
═══════════════════════════════════ */
const AGENTS_STATIC = [
    { num: 1, name: 'Data Collection Agent',   desc: 'Fetches OHLCV data from NSE/BSE via yfinance and nsepython for NIFTY 50, Next 50, and Mid-caps.', status: 'online' },
    { num: 2, name: 'Data Processing Agent',   desc: 'Cleans, normalises and computes 20+ technical indicators (RSI, MACD, EMA, Bollinger Bands, ATR, OBV...).', status: 'online' },
    { num: 3, name: 'Prediction Agent',        desc: 'Runs LSTM and Transformer models to forecast price over 5-day horizon. Outputs probability and confidence.', status: 'online' },
    { num: 4, name: 'Backtesting Agent',       desc: 'Validates strategies on historical data using vectorised Pandas. Computes Sharpe, Win Rate, Max Drawdown.', status: 'online' },
    { num: 5, name: 'Self-Learning Agent',     desc: 'Monitors directional accuracy and triggers model retraining when performance drops below threshold.', status: 'idle' },
    { num: 6, name: 'News Intelligence Agent', desc: 'Scrapes 9 Indian financial RSS feeds, classifies headlines with FinBERT, stores sentiment score per ticker.', status: 'online' },
    { num: 7, name: 'Strategy Agent',          desc: 'Combines ML predictions, TA signals and sentiment to score the best trade setup per ticker.', status: 'online' },
    { num: 8, name: 'Risk Management Agent',   desc: 'Enforces position sizing, R:R ratio (min 1:2), VaR checks, and portfolio-level drawdown limits.', status: 'online' },
    { num: 9, name: 'Recommendation Agent',   desc: 'Formats risk-cleared strategies into actionable recommendations with entry, target, stop-loss and reasoning.', status: 'online' },
    { num: 10, name: 'Continuous Learning Agent', desc: 'Weekly retraining cycle: retrains LSTM/Transformer on expanded dataset with latest market data.', status: 'idle' },
];

function loadAgents() {
    const container = document.getElementById('agents-grid');
    if (!container) return;
    container.innerHTML = AGENTS_STATIC.map(a => `
        <div class="agent-card">
            <div class="agent-header">
                <div class="agent-name-block">
                    <div class="agent-num">${a.num}</div>
                    <div class="agent-title">${a.name}</div>
                </div>
                <span class="agent-status-badge status-${a.status}">${a.status === 'online' ? 'Active' : 'Idle'}</span>
            </div>
            <div class="agent-desc">${a.desc}</div>
            <div class="agent-last-run">Last triggered: GitHub Actions scheduled run</div>
        </div>`).join('');
}

/* ═══════════════════════════════════
   SETTINGS PAGE
═══════════════════════════════════ */
function loadSettings() { /* Static content, nothing to load */ }

/* ═══════════════════════════════════
   SEARCH
═══════════════════════════════════ */
const STOCK_DB = [
    { ticker: 'RELIANCE.NS', name: 'Reliance Industries', type: 'Stock' },
    { ticker: 'TCS.NS', name: 'Tata Consultancy Services', type: 'Stock' },
    { ticker: 'HDFCBANK.NS', name: 'HDFC Bank', type: 'Stock' },
    { ticker: 'INFY.NS', name: 'Infosys', type: 'Stock' },
    { ticker: 'ICICIBANK.NS', name: 'ICICI Bank', type: 'Stock' },
    { ticker: 'BAJFINANCE.NS', name: 'Bajaj Finance', type: 'Stock' },
    { ticker: 'AXISBANK.NS', name: 'Axis Bank', type: 'Stock' },
    { ticker: 'WIPRO.NS', name: 'Wipro', type: 'Stock' },
    { ticker: 'LT.NS', name: 'Larsen & Toubro', type: 'Stock' },
    { ticker: 'MARUTI.NS', name: 'Maruti Suzuki', type: 'Stock' },
    { ticker: 'SUNPHARMA.NS', name: 'Sun Pharmaceutical', type: 'Stock' },
    { ticker: 'ADANIENT.NS', name: 'Adani Enterprises', type: 'Stock' },
    { ticker: 'ONGC.NS', name: 'ONGC', type: 'Stock' },
    { ticker: 'TATAMOTORS.NS', name: 'Tata Motors', type: 'Stock' },
    { ticker: 'TATASTEEL.NS', name: 'Tata Steel', type: 'Stock' },
    { ticker: 'NTPC.NS', name: 'NTPC', type: 'Stock' },
    { ticker: 'POWERGRID.NS', name: 'Power Grid Corporation', type: 'Stock' },
    { ticker: 'SBIN.NS', name: 'State Bank of India', type: 'Stock' },
    { ticker: 'KOTAKBANK.NS', name: 'Kotak Mahindra Bank', type: 'Stock' },
    { ticker: 'HINDUNILVR.NS', name: 'Hindustan Unilever', type: 'Stock' },
    { ticker: 'MIRAE001', name: 'Mirae Asset Large Cap Fund', type: 'Mutual Fund' },
    { ticker: 'PPFC001', name: 'Parag Parikh Flexi Cap Fund', type: 'Mutual Fund' },
    { ticker: 'AXIS001', name: 'Axis Bluechip Fund', type: 'Mutual Fund' },
    { ticker: '^NSEI', name: 'NIFTY 50', type: 'Index' },
    { ticker: '^BSESN', name: 'SENSEX', type: 'Index' },
    { ticker: '^NSEBANK', name: 'NIFTY BANK', type: 'Index' },
];

function initSearch() {
    const input    = document.getElementById('search-input');
    const clearBtn = document.getElementById('search-clear');
    const results  = document.getElementById('search-results');

    if (!input) return;

    input.addEventListener('input', () => {
        const q = input.value.trim();
        clearBtn.classList.toggle('visible', q.length > 0);
        clearTimeout(searchTimeout);
        if (q.length < 2) { results.classList.remove('visible'); return; }
        searchTimeout = setTimeout(() => runSearch(q), 180);
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-wrapper')) {
            results.classList.remove('visible');
        }
    });
}

function runSearch(query) {
    const q = query.toLowerCase();
    const results = document.getElementById('search-results');
    const matches = STOCK_DB.filter(s =>
        s.ticker.toLowerCase().includes(q) || s.name.toLowerCase().includes(q)
    ).slice(0, 8);

    if (!matches.length) {
        results.innerHTML = '<div class="search-result-item"><div class="sri-left"><span class="sri-name">No results found</span></div></div>';
    } else {
        results.innerHTML = matches.map(s => `
            <div class="search-result-item" onclick="selectTicker('${s.ticker}', '${s.name}')">
                <div class="sri-left">
                    <span class="sri-ticker">${s.ticker}</span>
                    <span class="sri-name">${s.name}</span>
                </div>
                <span class="sri-type">${s.type}</span>
            </div>`).join('');
    }
    results.classList.add('visible');
}

function selectTicker(ticker, name) {
    showToast(`🔍 Navigating to ${name}`);
    document.getElementById('search-results').classList.remove('visible');
    document.getElementById('search-input').value = ticker;
    // Navigate to recommendations and filter
    navigate('recommendations', null);
    setTimeout(() => {
        // Try to highlight the matching rec card if it exists
        const cards = document.querySelectorAll('.rec-card');
        for (const card of cards) {
            if (card.textContent.includes(ticker)) {
                card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                card.style.borderColor = 'var(--indigo)';
                setTimeout(() => card.style.borderColor = '', 2000);
                break;
            }
        }
    }, 800);
}

function clearSearch() {
    document.getElementById('search-input').value = '';
    document.getElementById('search-clear').classList.remove('visible');
    document.getElementById('search-results').classList.remove('visible');
}

/* ═══════════════════════════════════
   RUN ANALYSIS
═══════════════════════════════════ */
function runAnalysis() {
    document.getElementById('run-modal').classList.remove('hidden');
}
function closeModal() {
    document.getElementById('run-modal').classList.add('hidden');
}
// Close on backdrop click
document.getElementById('run-modal')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeModal();
});

/* ═══════════════════════════════════
   SYSTEM STATUS
═══════════════════════════════════ */
async function fetchSystemStatus() {
    try {
        const res  = await fetch('/api/system_status');
        const data = await res.json();
        const el   = document.getElementById('last-run-time');
        if (!el) return;
        const raw = data.last_run_at;
        if (raw && raw !== 'Never') {
            const dt = new Date(raw);
            el.textContent = dt.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'short', timeStyle: 'short' });
        } else {
            el.textContent = 'Never (first run pending)';
        }
    } catch (e) { /* silent */ }
}

/* ═══════════════════════════════════
   HELPERS
═══════════════════════════════════ */
function fmt(val) {
    if (!val && val !== 0) return '—';
    return Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getAssetType(ticker) {
    if (!ticker) return 'Equity';
    if (ticker.includes('MF') || ['MIRAE001','PPFC001','AXIS001'].includes(ticker)) return 'Mutual Fund';
    if (ticker.startsWith('^')) return 'Index';
    if (ticker.includes('CE') || ticker.includes('PE')) return 'Option';
    return 'Equity';
}

function showToast(message) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2800);
}
