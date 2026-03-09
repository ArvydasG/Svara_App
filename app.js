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
        return { color: 'var(--color-glass)', label: 'Stiklas' };
    if (s.includes('plastik') || s.includes('popier') || s.includes('pakuot'))
        return { color: 'var(--color-plastic)', label: 'Pakuotės' };
    if (s.includes('bio') || s.includes('žalio') || s.includes('maist'))
        return { color: 'var(--color-bio)', label: 'Žaliosios' };
    if (s.includes('mišr'))
        return { color: 'var(--color-mixed)', label: 'Mišrios' };
    return { color: 'var(--color-paper)', label: 'Kita' };
}

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
            try {
                const r = await fetch('grafikas.json?t=' + Date.now());
                if (r.ok) {
                    const json = await r.json();
                    data = json.contracts || [];
                }
            } catch (e) { console.log("GitHub data fail"); }
        }

        if (!data) {
            const r = await fetch('/api/grafikas' + (force ? '?force=1' : ''));
            if (r.ok) {
                const json = await r.json();
                data = json.contracts || [];
            } else {
                // Fallback jei nėra nei GitHub nei API (lokalus testavimas)
                data = [];
            }
        }

        contractsCache = data;
        if (!contractsCache.length) { showState('empty'); return; }

        renderAll(contractsCache);
        showState('content');

        const now = new Date();
        document.getElementById('last-updated').textContent =
            'Atnaujinta ' + now.toLocaleTimeString('lt-LT', { hour: '2-digit', minute: '2-digit' });

    } catch (err) {
        console.error(err);
        showState('error');
    }
}

async function triggerRefresh() {
    try { await fetch('/api/refresh'); } catch (e) { }
    fetchData(true);
}

// ─── Renderingas ─────────────────────────────────────

function buildPickupList(contracts) {
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

    // Hero Section
    document.getElementById('hero-days').textContent = first.days === 0 ? '🚛' : first.days;
    document.getElementById('hero-days-label').textContent =
        first.days === 0 ? 'Šiandien' : (first.days === 1 ? 'Rytoj' : 'dienų');
    document.getElementById('hero-title').textContent =
        first.days === 0 ? 'Šiandien vežama!' : (first.days === 1 ? 'Rytoj vežama!' : `Kitas išvežimas už ${first.days} d.`);
    document.getElementById('hero-date').textContent = formatDate(first.dateStr);

    document.getElementById('hero-badges').innerHTML = sameDayItems.map(p =>
        `<span class="type-badge" style="border-color:${p.style.color}; color:${p.style.color}">${p.desc}</span>`
    ).join('');

    // Schedule Grid
    const container = document.getElementById('schedule-container');
    container.innerHTML = '';

    pickups.forEach((p) => {
        const card = document.createElement('div');
        card.className = 'pickup-card';

        const isToday = p.days === 0;
        const isSoon = p.days === 1 || p.days === 2;
        const daysCls = isToday ? 'today-bg' : (isSoon ? 'soon-bg' : '');

        card.innerHTML = `
            <div class="card-days ${daysCls}">
                <div class="d-num">${isToday ? '🚛' : p.days}</div>
                <div class="d-lab">${isToday ? 'šiandien' : (p.days === 1 ? 'rytoj' : 'dienų')}</div>
            </div>
            <div class="card-info">
                <h3>${p.desc}</h3>
                <div class="card-date">${formatDate(p.dateStr)}</div>
                <div class="card-meta">
                    ${p.container ? `<span class="meta-chip">📦 ${p.container}</span>` : ''}
                    <span class="meta-chip">${p.isEstimated ? '⚠️ Orientacinis' : '✓ Tikslus'}</span>
                </div>
            </div>
            <div class="waste-indicator" style="color:${p.style.color}; background:currentColor"></div>
        `;
        container.appendChild(card);
    });
}

function showState(state) {
    ['loading', 'error-state', 'empty-state', 'content'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });
    const targets = { loading: 'loading', error: 'error-state', empty: 'empty-state', content: 'content' };
    const el = document.getElementById(targets[state]);
    if (el) el.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('refresh-btn');
    if (btn) btn.addEventListener('click', () => triggerRefresh());
    fetchData();
});
