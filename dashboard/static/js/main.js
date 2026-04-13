document.addEventListener('DOMContentLoaded', () => {
    
    // Fetch and render data on load
    fetchOverview();
    fetchRecommendations();
    fetchSentiment();
    fetchSystemStatus();

    // Auto refresh every 5 minutes
    setInterval(() => {
        fetchOverview();
        fetchRecommendations();
        fetchSentiment();
        fetchSystemStatus();
    }, 300000);
});

async function fetchOverview() {
    try {
        const response = await fetch('/api/overview');
        const result = await response.json();
        
        if (result.status === 'success') {
            const container = document.getElementById('market-overview');
            container.innerHTML = ''; // Clear loaders
            
            const dirs = {
                'NIFTY_50': 'NIFTY 50',
                'SENSEX': 'SENSEX',
                'BANK_NIFTY': 'NIFTY BANK'
            };

            for (const [key, data] of Object.entries(result.indices)) {
                const isPositive = data.change >= 0;
                const sign = isPositive ? '+' : '';
                const formatClass = isPositive ? 'positive' : 'negative';
                
                const card = `
                    <div class="glass-card index-card">
                        <h3>${dirs[key]}</h3>
                        <div class="price">₹${data.price.toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
                        <span class="badge ${formatClass}">${sign}${data.change}%</span>
                    </div>
                `;
                container.innerHTML += card;
            }
        }
    } catch (error) {
        console.error("Failed to fetch overview", error);
    }
}

async function fetchRecommendations() {
    try {
        const response = await fetch('/api/recommendations');
        const result = await response.json();
        
        if (result.status === 'success') {
            const container = document.getElementById('rec-list');
            container.innerHTML = '';
            
            result.data.forEach(rec => {
                const actionClass = rec.action.toLowerCase();
                const card = `
                    <div class="rec-card">
                        <div class="rec-main">
                            <div class="stock-info">
                                <div class="ticker">${rec.ticker} <span class="badge" style="background: rgba(255,255,255,0.1); margin-left: 8px;">${rec.strategy}</span></div>
                                <div class="name">${rec.name} • Confidence: ${rec.confidence}%</div>
                            </div>
                            <div class="action-badge action-${actionClass}">${rec.action}</div>
                        </div>
                        <div class="price-grid">
                            <div class="price-item">
                                <span>Entry</span>
                                <strong>₹${rec.entry.toLocaleString('en-IN')}</strong>
                            </div>
                            <div class="price-item">
                                <span>Target</span>
                                <strong style="color: var(--success)">₹${rec.target.toLocaleString('en-IN')}</strong>
                            </div>
                            <div class="price-item">
                                <span>Stop Loss</span>
                                <strong style="color: var(--danger)">₹${rec.stop.toLocaleString('en-IN')}</strong>
                            </div>
                        </div>
                        <div class="reasoning">
                            <i class="ph ph-robot"></i> ${rec.reasoning}
                        </div>
                    </div>
                `;
                container.innerHTML += card;
            });
        }
    } catch (error) {
        console.error("Failed to fetch recs", error);
    }
}

async function fetchSentiment() {
    try {
        const response = await fetch('/api/sentiment');
        const result = await response.json();
        
        if (result.status === 'success') {
            const container = document.getElementById('news-list');
            container.innerHTML = '';
            
            result.data.forEach(news => {
                const formatClass = news.label === 'POSITIVE' ? 'positive' : (news.label === 'NEGATIVE' ? 'negative' : '');
                
                const item = `
                    <div class="news-item">
                        <div class="news-meta">
                            <span>${news.source} • ${news.time}</span>
                            <span class="badge ${formatClass}">${news.label}</span>
                        </div>
                        <div class="news-headline">${news.headline}</div>
                    </div>
                `;
                container.innerHTML += item;
            });
        }
    } catch (error) {
        console.error("Failed to fetch sentiment", error);
    }
}

async function fetchSystemStatus() {
    try {
        const response = await fetch('/api/system_status');
        const result = await response.json();
        
        if (result.status === 'success') {
            const el = document.getElementById('sync-time');
            if (el) {
                const raw = result.last_run_at;
                if (raw && raw !== 'Never') {
                    // Format the ISO timestamp nicely
                    const dt = new Date(raw);
                    el.innerText = dt.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'short', timeStyle: 'short' });
                } else {
                    el.innerText = '—';
                }
            }
        }
    } catch (error) {
        console.error("Failed to fetch system status", error);
    }
}
