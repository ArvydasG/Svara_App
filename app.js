// Atliekų grafiko aplikacija – PC versija
// Seniavos pl. 56F, Kauno m. sav.

const months_lt = ['Sausio', 'Vasario', 'Kovo', 'Balandžio', 'Gegužės', 'Birželio',
    'Liepos', 'Rugpjūčio', 'Rugsėjo', 'Spalio', 'Lapkričio', 'Gruodžio'];
const weekdays_lt = ['Sekmadienis', 'Pirmadienis', 'Antradienis', 'Trečiadienis',
    'Ketvirtadienis', 'Penktadienis', 'Šeštadienis'];

// ─── Pagalbiniai ────────────────────────────────────

function todayDate() {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
}

function daysUntil(dateStr) {
    const t = todayDate();
    const d = new Date(dateStr + 'T00:00:00');
    return Math.round((d - t) / 86400000);
}

function formatDate(dateStr) {
    const d = new Date(dateStr + 'T00:00:00');
    return `${weekdays_lt[d.getDay()]}, ${d.getDate()} ${months_lt[d.getMonth()]} ${d.getFullYear()}`;
}

function getWasteStyle(desc) {
    const s = (desc || '').toLowerCase();
    if (s.includes('stikl'))
        return { cls: 'dot-glass', color: '#22c55e', badge: '#14532d22', textColor: '#bbf7d0' };
    if (s.includes('plastik') || s.includes('popier') || s.includes('pakuot'))
        return { cls: 'dot-plastic', color: '#3b82f6', badge: '#1e3a8a22', textColor: '#bfdbfe' };
    if (s.includes('bio') || s.includes('žalio') || s.includes('maist'))
        return { cls: 'dot-bio', color: '#a3e635', badge: '#3f621222', textColor: '#d9f99d' };
    if (s.includes('popieriaus') || s.includes('karton'))
        return { cls: 'dot-paper', color: '#f97316', badge: '#7c2d1222', textColor: '#fed7aa' };
    return { cls: 'dot-mixed', color: '#94a3b8', badge: '#33415522', textColor: '#cbd5e1' };
}

// Generuoja orientacinius grafikus kai tikrų datų nėra
function estimateDates(desc, idx) {
    const today = todayDate();
    const intervals = [
        ['plastik', 2], ['popier', 2], ['pakuot', 2],
        ['stikl', 4], ['bio', 1], ['žalio', 1], ['mišr', 2]
    ];
    let interval = 2;
    const dl = (desc || '').toLowerCase();
    for (const [k, v] of intervals) if (dl.includes(k)) { interval = v; break; }

    const offset = idx % 3;
    let start = new Date(today);
    start.setDate(start.getDate() + offset);

    const dates = [];
    for (let i = 0; i < 5; i++) {
        const d = new Date(start);
        d.setDate(d.getDate() + i * interval * 7);
        if (daysUntil(d.toISOString().slice(0, 10)) >= 0)
            dates.push(d.toISOString().slice(0, 10));
    }
    return dates.slice(0, 4);
}

// ─── Duomenų gavimas ─────────────────────────────────

let pollingTimer = null;
let contractsCache = [];

async function fetchData(force = false) {
    showState('loading');

    try {
        let data = null;
        let isGitHub = window.location.hostname.includes('github.io');

        if (isGitHub && !force) {
            // Bandome GitHub statinį JSON
            try {
                const r = await fetch('grafikas.json?t=' + Date.now());
                if (r.ok) {
                    const json = await r.json();
                    data = json.contracts || [];
                }
            } catch (e) { console.log("GitHub data fail"); }
        }

        if (!data) {
            // Kreipiamės į vietinį serverį / API
            const url = '/api/grafikas' + (force ? '?force=1' : '');
            const r = await fetch(url);
            if (!r.ok) throw new Error('Nepavyko gauti duomenų iš serverio');
            const json = await r.json();
            data = json.contracts || [];
        }

        contractsCache = data;
        const hasAny = contractsCache.length > 0;
        const hasRealDates = contractsCache.some(c => c.hasRealDates && c.dates.length > 0);

        if (!hasAny) {
            showState('empty');
            return;
        }

        renderAll(contractsCache);
        showState('content');

        const now = new Date();
        document.getElementById('last-updated').textContent =
            'Atnaujinta ' + now.toLocaleTimeString('lt-LT', { hour: '2-digit', minute: '2-digit' });

        if (!hasRealDates && !isGitHub) {
            showRefreshingBanner(true);
            scheduleAutoRefresh(30);
        } else {
            showRefreshingBanner(false);
            clearAutoRefresh();
        }

    } catch (err) {
        console.error(err);
        document.getElementById('error-message').textContent =
            'Klaida: ' + err.message;
        showState('error');
    }
}

async function triggerRefresh() {
    try { await fetch('/api/refresh'); } catch (e) { }
    showRefreshingBanner(true);
    scheduleAutoRefresh(20);
}

function scheduleAutoRefresh(secs) {
    clearAutoRefresh();
    pollingTimer = setTimeout(async () => {
        const r = await fetch('/api/grafikas');
        const json = await r.json();
        const newData = json.contracts || [];
        const hasReal = newData.some(c => c.hasRealDates && c.dates.length > 0);
        if (hasReal) {
            contractsCache = newData;
            renderAll(contractsCache);
            showRefreshingBanner(false);
            document.getElementById('last-updated').textContent =
                'Atnaujinta ' + new Date().toLocaleTimeString('lt-LT', { hour: '2-digit', minute: '2-digit' });
        } else {
            scheduleAutoRefresh(20);
        }
    }, secs * 1000);
}

function clearAutoRefresh() {
    if (pollingTimer) { clearTimeout(pollingTimer); pollingTimer = null; }
}

// ─── Renderingas ─────────────────────────────────────

function buildPickupList(contracts) {
    const today = todayDate().toISOString().slice(0, 10);
    const items = [];

    contracts.forEach((c, idx) => {
        const desc = c.description || 'Atliekų išvežimas';
        const style = getWasteStyle(desc);
        const real = c.hasRealDates && (c.dates || []).length > 0;
        const dates = real ? c.dates : estimateDates(desc, idx);

        dates.forEach(dateStr => {
            const days = daysUntil(dateStr);
            if (days >= 0) {
                items.push({
                    dateStr, days, desc,
                    container: c.containerType || '',
                    style,
                    isEstimated: !real
                });
            }
        });
    });

    items.sort((a, b) => a.days - b.days);
    const seen = new Set();
    return items.filter(item => {
        const k = item.dateStr + '|' + item.desc;
        if (seen.has(k)) return false;
        seen.add(k); return true;
    }).slice(0, 25);
}

function renderAll(contracts) {
    const pickups = buildPickupList(contracts);
    if (!pickups.length) { showState('empty'); return; }

    const first = pickups[0];
    const sameDayItems = pickups.filter(p => p.days === first.days);

    let heroBg;
    if (first.days === 0) heroBg = '#16a34a';
    else if (first.days === 1) heroBg = '#ca8a04';
    else heroBg = '#6c63ff';

    document.getElementById('hero-days').textContent = first.days === 0 ? '🚛' : first.days;
    document.getElementById('hero-days-label').textContent =
        first.days === 0 ? 'Šiandien' : first.days === 1 ? 'Rytoj' : 'dienų';
    document.querySelector('.days-counter').style.background = heroBg;

    document.getElementById('hero-title').textContent =
        first.days === 0 ? 'Šiandien vežama!' : first.days === 1 ? 'Rytoj vežama!' : `Kitas išvežimas už ${first.days} d.`;
    document.getElementById('hero-date').textContent = formatDate(first.dateStr);

    const badgesEl = document.getElementById('hero-badges');
    badgesEl.innerHTML = sameDayItems.map(p => {
        const s = p.style;
        return `<span class="type-badge" style="color:${s.textColor};border-color:${s.color};background:${s.badge}">${p.desc}</span>`;
    }).join('');

    const container = document.getElementById('schedule-container');
    container.innerHTML = '';

    pickups.forEach((p, i) => {
        const card = document.createElement('div');
        const isToday = p.days === 0;
        const isSoon = p.days === 1 || p.days === 2;
        card.className = `pickup-card ${isToday ? 'today' : ''} ${isSoon && !isToday ? 'soon' : ''}`;

        let daysBg = isToday ? 'today-bg' : (isSoon ? 'soon-bg' : 'normal-bg');
        const dNum = isToday ? '🚛' : p.days;
        const dLab = isToday ? 'šiandien' : (p.days === 1 ? 'rytoj' : 'dienų');

        const estBadge = p.isEstimated
            ? `<span class="meta-chip" style="color:#f97316;">⚠ Orientacinis</span>`
            : `<span class="meta-chip" style="color:#22c55e;">✓ Tikslus</span>`;

        card.innerHTML = `
            <div class="card-days ${daysBg}">
                <div class="d-num">${dNum}</div>
                <div class="d-lab">${dLab}</div>
            </div>
            <div class="card-info">
                <h3>${p.desc}</h3>
                <div style="color:var(--text2);font-size:0.82rem;margin-top:2px">${formatDate(p.dateStr)}</div>
                <div class="card-meta">
                    ${p.container ? `<span class="meta-chip">📦 ${p.container}</span>` : ''}
                    ${estBadge}
                </div>
            </div>
            <div class="dot ${p.style.cls}" style="margin-left:auto;flex-shrink:0"></div>
        `;
        container.appendChild(card);
    });
}

function showRefreshingBanner(show) {
    let banner = document.getElementById('refreshing-banner');
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'refreshing-banner';
        banner.style.cssText = `
            background: rgba(108,99,255,0.12); border: 1px solid rgba(108,99,255,0.3);
            border-radius: 10px; padding: 10px 18px; margin-bottom: 20px;
            color: #a78bfa; font-size: 0.84rem; display: flex; align-items: center; gap: 10px;
        `;
        banner.innerHTML = `<div class="spinner" style="width:16px;height:16px;border-width:2px;"></div>
            <span>Tikros datos kraunamos fone… Puslapis atsinaujins automatiškai.</span>`;
        if (document.getElementById('next-pickup-hero'))
            document.getElementById('next-pickup-hero').before(banner);
    }
    if (banner) banner.style.display = show ? 'flex' : 'none';
}

function showState(state) {
    ['loading', 'error-state', 'empty-state', 'content'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });
    const targets = { loading: 'loading', error: 'error-state', empty: 'empty-state', content: 'content' };
    const el = document.getElementById(targets[state] || state);
    if (el) el.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('refresh-btn');
    if (btn) btn.addEventListener('click', () => {
        clearAutoRefresh();
        triggerRefresh();
        fetchData(false);
    });
    fetchData();
});
