"""
GitHub Actions robotas (GALUTINIS SPRENDIMAS):
Duomenų rinkimas iš įvairių šaltinių: šiukšlių grafikas, Aleksoto naujienos, Kauno renginiai ir oro kokybė.
"""
import re
import json
import os
import sys
import io
import urllib.request
import urllib.parse
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
import requests
from bs4 import BeautifulSoup

# Užtikriname UTF-8 spausdinimą (ypač Windows terminalui)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ADDRESS = {
    'region': 'Kauno m. sav.',
    'address': 'Seniavos pl.',
    'houseNumber': '56F',
}

def scrape():
    print("🚀 PALEIDŽIAMAS ROBOTAS-SKAITYTOJAS...")
    
    # Pradinis kintamųjų inicializavimas
    final_results = []
    neighborhood_works = [
        {
            "title": "Bitininkų g. rekonstrukcija",
            "description": "Vykdomi lietaus nuotekų tinklų ir kelio dangos atnaujinimo darbai (nuo Seniavos pl. iki Sodininkų g.).",
            "status": "Vykdoma",
            "date": "2024 - 2026"
        },
        {
            "title": "Seniavos plento remontas",
            "description": "Planuojamas kapitalinis kelio dangos ir apšvietimo remontas.",
            "status": "Planuojama",
            "date": "2025 - 2026"
        }
    ]
    aleksotas_news = []
    kaunas_events = []
    community_events = []
    air_quality = {
        "index": 18,
        "status": "Puiki",
        "description": "Oras švarus, galite drąsiai vėdinti namus.",
        "station": "Noreikiškės"
    }

    today_obj = date.today()
    max_date_obj = today_obj + timedelta(days=30)
    today_str = today_obj.isoformat()
    max_date_str = max_date_obj.isoformat()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale="lt-LT"
        )
        page = context.new_page()

        # 1. PUSH PRANEŠIMAI IR ŠIUKŠLIŲ GRAFIKAS
        try:
            print("🔗 Jungiamasi prie https://grafikai.svara.lt/ ...")
            page.goto("https://grafikai.svara.lt/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

            # Forma
            page.locator("input:visible").first.click()
            page.keyboard.type(ADDRESS['region'], delay=100)
            page.wait_for_timeout(5000)
            page.keyboard.press("Enter")
            
            page.keyboard.press("Tab")
            page.keyboard.type(ADDRESS['address'], delay=100)
            page.wait_for_timeout(5000)
            page.keyboard.press("Enter")
            
            page.keyboard.press("Tab")
            page.keyboard.type(ADDRESS['houseNumber'], delay=100)
            page.keyboard.press("Enter")
            
            page.locator("button:has-text('Ieškoti')").first.click(force=True)
            page.wait_for_timeout(10000)

            # Renkame datas
            rows = page.locator("tr:has(button:has-text('Išskleisti'))").all()
            for row in rows:
                cols = row.locator("td").all()
                if len(cols) >= 2:
                    type_txt = cols[0].inner_text().strip()
                    cont_txt = cols[1].inner_text().strip()
                    final_results.append({
                        'description': type_txt,
                        'containerType': cont_txt,
                        'dates': [],
                        'hasRealDates': False
                    })

            for item in final_results:
                target_row = page.locator(f"tr:has-text('{item['containerType']}')").filter(has=page.locator("button:has-text('Išskleisti')"))
                if target_row.count() > 0:
                    try:
                        with page.expect_response(lambda r: "api/" in r.url and r.status == 200, timeout=5000) as resp:
                            target_row.locator("button:has-text('Išskleisti')").first.click()
                            data = resp.value.json()
                            items = data if isinstance(data, list) else data.get('data', [])
                            dates = sorted(set(str(it['date'])[:10] for it in items if isinstance(it, dict) and it.get('date')))
                            item['dates'] = [d for d in dates if d >= today_str]
                            item['hasRealDates'] = len(item['dates']) > 0
                    except: pass
        except Exception as e:
            print(f"⚠️ Klaida šiukšlių grafike: {e}")

        # 2. ALEKSOTO NAUJIENOS
        try:
            news_url = "https://www.kaunas.lt/administracija/struktura-ir-kontaktine-informacija/seniunijos/aleksoto-seniunija/aleksoto-seniunijos-naujienos/"
            page.goto(news_url, timeout=20000)
            links = page.locator("a[href*='/seniunijos/']").all()
            for l_el in links[:5]:
                t = l_el.inner_text().strip()
                href = l_el.get_attribute("href")
                if t and len(t) > 10 and href:
                    aleksotas_news.append({"title": t, "url": href, "date": "Naujausia"})
            if not aleksotas_news:
                aleksotas_news.append({"title": "Aleksoto naujienos", "url": news_url, "date": "Aktualu"})
        except: 
            aleksotas_news = [{"title": "Aleksoto naujienos", "url": "https://www.kaunas.lt", "date": "Nuoroda"}]

        # 3. KAUNO RENGINIAI (KAUNASPILNAS)
        try:
            print("🎭 Ieškoma renginių iš kaunaspilnasrenginiu.lt...")
            kp_resp = requests.get("https://kaunaspilnasrenginiu.lt/lt/renginiai", headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
            if kp_resp.ok:
                soup = BeautifulSoup(kp_resp.text, 'html.parser')
                m_map = {"sausio":1,"vasario":2,"kovo":3,"balandžio":4,"gegužės":5,"birželio":6,"liepos":7,"rugpjūčio":8,"rugsėjo":9,"spalio":10,"lapkričio":11,"gruodžio":12}
                for h3 in soup.find_all('h3'):
                    title = h3.get_text(strip=True)
                    if not title or any(x in title for x in ["Pranešk", "Organizuoji", "Partneris"]): continue
                    text = h3.parent.get_text()
                    d_match = re.search(r'([A-Z][a-z]+ \d+ d\.)', text)
                    if d_match:
                        d_str = d_match.group(1).lower()
                        for m_name, m_num in m_map.items():
                            if m_name in d_str:
                                day = int(re.search(r'\d+', d_str).group())
                                yr = today_obj.year
                                if m_num < today_obj.month: yr += 1
                                iso = date(yr, m_num, day).isoformat()
                                if today_str <= iso <= max_date_str:
                                    link_tag = h3.find_parent('a') or h3.parent.find('a', href=True)
                                    url = link_tag['href'] if link_tag else ""
                                    if url and not url.startswith('http'): url = "https://kaunaspilnasrenginiu.lt" + url
                                    if not any(e['title'] == title and e['date'] == iso for e in kaunas_events):
                                        kaunas_events.append({"title": title, "date": iso, "url": url, "source": "Kaunas Pilnas"})
                                break
        except Exception as e: print(f"⚠️ Kauno renginių klaida: {e}")

        # 4. ALEKSOTO RENGINIAI (BIBLIOTEKA, BOTANIKA, BC)
        try:
            print("📅 Ieškoma Aleksoto renginių...")
            
            # Botanika
            bot_resp = requests.get("https://botanika.vdu.lt/renginiai", timeout=20)
            if bot_resp.ok:
                soup = BeautifulSoup(bot_resp.text, 'html.parser')
                for e in soup.find_all('a', href=lambda h: h and '/ivykiai/' in h):
                    t_el = e.find('div', class_='PANEL__title')
                    d_el = e.find('div', class_='PANEL__date')
                    if not t_el: continue
                    t = t_el.get_text(strip=True)
                    url = e.get('href')
                    date_str = "Sezoninis"
                    
                    if d_el:
                        parsed_date = d_el.get_text(strip=True).replace(' ', '-')
                        if re.match(r'^\d{4}-\d{2}-\d{2}$', parsed_date):
                            if today_str <= parsed_date <= max_date_str:
                                date_str = parsed_date
                            else:
                                continue # Nepraeina 30 dienų filtro
                    
                    if not any(ev['title'] == t for ev in community_events):
                        community_events.append({"title": t, "url": url, "date": date_str, "source": "Botanikos sodas"})

            # Biblioteka (kaunobiblioteka.lt/aleksotas)
            m_map_lt = {
                "sausio":1,"vasario":2,"kovo":3,"balandžio":4,"gegužės":5,"birželio":6,
                "liepos":7,"rugpjūčio":8,"rugsėjo":9,"spalio":10,"lapkričio":11,"gruodžio":12
            }
            def parse_lt_date_from_text(text):
                """Ieško datos tekste. Grąžina (iso_date|None, date_found_in_text).
                Aptinka formatus: 'Kovo 26 d.', 'Kovo 4, 18 d.', 'Vasario 2–28 d.'"""
                from datetime import date as _d
                months_re = r'(sausio|vasario|kovo|balandžio|gegužės|birželio|liepos|rugpjūčio|rugsėjo|spalio|lapkričio|gruodžio)'
                
                # Bandome surasti visias datos paminėjimus su mėnesiu
                all_matches = list(re.finditer(
                    months_re + r'\s+' + r'(\d{1,2}(?:[–\-,\s]+\d{1,2})*)\s+d\.',
                    text, re.IGNORECASE
                ))
                
                if not all_matches:
                    return None, False
                
                # Iš kiekvienos atitikties imame PASKUTINĮ dienų skaičių (pvz. iš "4, 18" imame 18)
                best_date = None
                for match in all_matches:
                    month_num = m_map_lt.get(match.group(1).lower())
                    if not month_num: continue
                    days_str = match.group(2)
                    # Ištraukiame visus skaičius
                    days = re.findall(r'\d{1,2}', days_str)
                    if not days: continue
                    # Imame paskutinį dienų skaičių (pvz. rango pabaigą arba paskutinę datą)
                    day = int(days[-1])
                    yr = today_obj.year
                    try:
                        evt = _d(yr, month_num, day)
                        if evt < today_obj - timedelta(days=1):
                            # Praeities data – žymime kaip rastą bet praėjusią
                            if best_date is None:
                                best_date = (None, True)
                            continue
                        if best_date is None or (best_date[0] is not None and evt.isoformat() < best_date[0]):
                            best_date = (evt.isoformat(), True)
                        elif best_date[0] is None:
                            best_date = (evt.isoformat(), True)
                    except: continue
                
                if best_date is not None:
                    return best_date
                return None, True  # rasta, bet visos praėjusios


            try:
                page.goto("https://kaunobiblioteka.lt/aleksotas", wait_until="networkidle", timeout=40000)
                page.wait_for_timeout(3000)
                articles = page.locator("article").all()
                for art in articles:
                    full_text = art.inner_text().strip()
                    try:
                        title = art.locator(".elementor-post__title, h2 a, h3 a").first.inner_text().strip()
                    except: continue
                    try:
                        link = art.locator("a").first.get_attribute("href") or ""
                    except: link = ""
                    if not title or len(title) < 5: continue

                    event_date, date_found = parse_lt_date_from_text(full_text)
                    
                    # Jei data rasta tekste, bet ji praėjusi – praleidžiame
                    if date_found and event_date is None:
                        continue
                    # Jei data rasta ir ji > 30 dienų – praleidžiame
                    if event_date and event_date > max_date_str:
                        continue
                    
                    date_val = event_date if event_date else "Aktualu"

                    if not any(ev['title'] == title for ev in community_events):
                        community_events.append({
                            "title": title, "url": link, "date": date_val, "source": "Biblioteka"
                        })

            except Exception as e:
                print(f"⚠️ Bibliotekos klaida: {e}")
                community_events.append({
                    "title": "Kauno bibliotekos renginiai",
                    "url": "https://kaunobiblioteka.lt/aleksotas",
                    "date": "Aktualu",
                    "source": "Biblioteka"
                })


        except Exception as e: print(f"⚠️ Aleksoto bendra klaida: {e}")

        browser.close()

    # Išsaugojimas
    output_data = {
        'contracts': final_results,
        'updated_at': today_str,
        'neighborhood_works': neighborhood_works,
        'news': aleksotas_news,
        'events': community_events[:10],
        'kaunas_events': kaunas_events[:10],
        'air_quality': air_quality
    }
    with open('grafikas.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Baigta! Surinkta šiukšlių grafikų: {len(final_results)}")

    # ONE SIGNAL
    try:
        api_key = os.environ.get('ONESIGNAL_API_KEY')
        tomorrow = (today_obj + timedelta(days=1)).isoformat()
        tomorrow_items = [i['description'] for i in final_results if tomorrow in i.get('dates', [])]
        if tomorrow_items and api_key:
            msg = f"Nepamirškite išstumti konteinerio! Rytoj vežama: {', '.join(set(tomorrow_items))} 🚛"
            payload = {
                "app_id": "9f3d18fb-2825-4a44-b306-80e21a9df9d5",
                "included_segments": ["All"],
                "headings": {"lt": "Šiukšlių išvežimas rytoj!"},
                "contents": {"lt": msg}
            }
            req = urllib.request.Request("https://onesignal.com/api/v1/notifications", data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json", "Authorization": f"Basic {api_key}"}, method='POST')
            with urllib.request.urlopen(req) as resp: print("✅ OneSignal išsiųstas.")
    except Exception as e: print(f"⚠️ OneSignal klaida: {e}")

if __name__ == "__main__":
    scrape()
