// Atliekų grafiko aplikacija – PC versija
// Seniavos pl. 56F, Kauno m. sav.

const months_lt = ['Sausio', 'Vasario', 'Kovo', 'Balandžio', 'Gegužės', 'Birželio',
    'Liepos', 'Rugpjūčio', 'Rugsėjo', 'Spalio', 'Lapkričio', 'Gruodžio'];
const weekdays_lt = ['Sekmadienis', 'Pirmadienis', 'Antradienis', 'Trečiadienis',
    'Ketvirtadienis', 'Penktadienis', 'Šeštadienis'];

// ─── Šventės ────────────────────────────────────────

function getEaster(year) {
    const f = Math.floor,
        G = year % 19,
        C = f(year / 100),
        H = (C - f(C / 4) - f((8 * C + 13) / 25) + 19 * G + 15) % 30,
        I = H - f(H / 28) * (1 - f(29 / (H + 1)) * f((21 - G) / 11)),
        J = (year + f(year / 4) + I + 2 - C + f(C / 4)) % 7,
        L = I - J,
        month = 3 + f((L + 40) / 44),
        day = L + 28 - 31 * f(month / 4);
    return new Date(year, month - 1, day);
}

function getLithuanianHolidays(year) {
    const easter = getEaster(year);
    const easterMonday = new Date(easter);
    easterMonday.setDate(easter.getDate() + 1);

    const holidays = [
        { date: `${year}-01-01`, name: "Naujieji metai" },
        { date: `${year}-02-16`, name: "Valstybės atkūrimo diena" },
        { date: `${year}-03-11`, name: "Nepriklausomybės atkūrimo diena" },
        { date: easter.toISOString().split('T')[0], name: "Velykos" },
        { date: easterMonday.toISOString().split('T')[0], name: "Velykų antroji diena" },
        { date: `${year}-05-01`, name: "Tarptautinė darbininkų diena" },
        { date: `${year}-06-24`, name: "Joninės" },
        { date: `${year}-07-06`, name: "Valstybės diena (Mindaugo karūnavimas)" },
        { date: `${year}-08-15`, name: "Žolinė" },
        { date: `${year}-11-01`, name: "Visų šventųjų diena" },
        { date: `${year}-11-02`, name: "Vėlinės" },
        { date: `${year}-12-24`, name: "Kūčios" },
        { date: `${year}-12-25`, name: "Kalėdos" },
        { date: `${year}-12-26`, name: "Kalėdų antroji diena" }
    ];
    return holidays;
}

function getUpcomingHolidays(count = 3) {
    const today = todayDate();
    const currentYear = today.getFullYear();
    let allHolidays = [
        ...getLithuanianHolidays(currentYear),
        ...getLithuanianHolidays(currentYear + 1)
    ];

    return allHolidays
        .map(h => ({ ...h, days: daysUntil(h.date) }))
        .filter(h => h.days >= 0)
        .sort((a, b) => a.days - b.days)
        .slice(0, count);
}

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
        let jsonBody = {};
        let isGitHub = window.location.hostname.includes('github.io');

        if (isGitHub && !force) {
            try {
                const r = await fetch('grafikas.json?t=' + Date.now());
                if (r.ok) {
                    jsonBody = await r.json();
                    data = jsonBody.contracts || [];
                }
            } catch (e) { console.log("GitHub data fail"); }
        }

        if (!data) {
            const r = await fetch('/api/grafikas' + (force ? '?force=1' : ''));
            if (r.ok) {
                jsonBody = await r.json();
                data = jsonBody.contracts || [];
            } else {
                data = [];
            }
        }

        contractsCache = data;
        const news = jsonBody.news || [];
        const airQuality = jsonBody.air_quality || null;

        renderAll(contractsCache, neighborhoodWorks, news, airQuality);
        showState('content');

        const now = new Date();
        document.getElementById('last-updated').textContent =
            'Atnaujinta ' + now.toLocaleDateString('lt-LT') + ' ' + now.toLocaleTimeString('lt-LT', { hour: '2-digit', minute: '2-digit' });

    } catch (err) {
        console.error(err);
        showState('error');
    }
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
    const litHolidays = getLithuanianHolidays(todayDate().getFullYear());
    const litHolidaysNext = getLithuanianHolidays(todayDate().getFullYear() + 1);
    const allHolidaysList = [...litHolidays, ...litHolidaysNext];

    let result = items.filter(item => {
        const k = item.dateStr + '|' + item.desc;
        if (seen.has(k)) return false;
        seen.add(k); return true;
    }).slice(0, 25);

    // Check for holidays
    result.forEach(item => {
        const holiday = allHolidaysList.find(h => h.date === item.dateStr);
        if (holiday) {
            item.holidayName = holiday.name;
        }
    });

    return result;
}

function renderHolidays() {
    const holidays = getUpcomingHolidays(3);
    const container = document.getElementById('holidays-container');
    if (!container) return;

    if (holidays.length === 0) {
        container.parentElement.classList.add('hidden');
        return;
    }

    container.innerHTML = holidays.map(h => `
        <div class="holiday-chip">
            <span class="holiday-name">${h.name}</span>
            <span class="holiday-date">${h.days === 0 ? 'Šiandien' : (h.days === 1 ? 'Rytoj' : `už ${h.days} d.`)}</span>
        </div>
    `).join('');
    container.parentElement.classList.remove('hidden');
}

function renderWorks(works) {
    const container = document.getElementById('works-container');
    if (!container) return;

    if (!works || works.length === 0) {
        container.parentElement.classList.add('hidden');
        return;
    }

    container.innerHTML = works.map(w => `
        <div class="work-card">
            <div class="work-icon">🏗️</div>
            <div class="work-content">
                <div class="work-header">
                    <h4>${w.title}</h4>
                    <span class="work-status-badge ${w.status === 'Vykdoma' ? 'status-active' : 'status-planned'}">${w.status}</span>
                </div>
                <p class="work-desc">${w.description}</p>
                <div class="work-footer">
                    <span class="work-date">📅 ${w.date}</span>
                </div>
            </div>
        </div>
    `).join('');
    container.parentElement.classList.remove('hidden');
}

function renderNews(news) {
    const container = document.getElementById('news-container');
    if (!container) return;

    if (!news || news.length === 0) {
        container.parentElement.classList.add('hidden');
        return;
    }

    container.innerHTML = news.map(n => `
        <a href="${n.url}" target="_blank" class="news-card">
            <div class="news-content">
                <h4>${n.title}</h4>
                <div class="news-meta">
                    <span class="news-date">📅 ${n.date}</span>
                    <span class="news-more">Skaityti daugiau →</span>
                </div>
            </div>
        </a>
    `).join('');
    container.parentElement.classList.remove('hidden');
}

function renderAirQuality(aqi) {
    const container = document.getElementById('aqi-widget');
    if (!container || !aqi) return;

    const statusClass = aqi.index < 25 ? 'aqi-excellent' : (aqi.index < 50 ? 'aqi-good' : 'aqi-moderate');

    container.innerHTML = `
        <div class="aqi-card ${statusClass}">
            <div class="aqi-header">
                <span class="aqi-label">Oro kokybė (${aqi.station})</span>
                <span class="aqi-value">${aqi.index} AQI</span>
            </div>
            <div class="aqi-body">
                <span class="aqi-status">${aqi.status}</span>
                <p class="aqi-desc">${aqi.description}</p>
            </div>
        </div>
    `;
    container.classList.remove('hidden');
}

function renderAll(contracts, works, news, airQuality) {
    renderHolidays();
    renderWorks(works);
    renderNews(news);
    renderAirQuality(airQuality);
    const pickups = buildPickupList(contracts);
    if (!pickups.length) { showState('empty'); return; }

    const first = pickups[0];
    const sameDayItems = pickups.filter(p => p.days === first.days);

    // Hero Section
    document.getElementById('hero-days').textContent = first.days === 0 ? '🚛' : first.days;
    document.getElementById('hero-days-label').textContent =
        first.days === 0 ? 'Šiandien' : (first.days === 1 ? 'Rytoj' : 'dienų');
    document.getElementById('hero-title').textContent =
        first.days === 0 ? 'Šiandien vežama!' : (first.days === 1 ? 'Rytoj vežama!' : `Kitas šiukšlių išvežimas už ${first.days} d.`);
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
                ${p.holidayName ? `<div class="holiday-warning">⚠️ ${p.holidayName}</div>` : ''}
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
    fetchData();
});
