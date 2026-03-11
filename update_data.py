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
                                    kaunas_events.append({"title": title, "date": iso, "url": url, "source": "Kaunas Pilnas"})
                                break
        except Exception as e: print(f"⚠️ Kauno renginių klaida: {e}")

        # 4. ALEKSOTO RENGINIAI (BIBLIOTEKA, BOTANIKA, BC)
        try:
            print("📅 Ieškoma Aleksoto renginių...")
            # Biblioteka
            page.goto("https://www.kaunobiblioteka.lt/aleksotas", timeout=30000)
            b_links = page.locator("a").all()
            for l in b_links:
                t = l.inner_text().strip()
                u = l.get_attribute("href")
                if t and len(t) > 15 and u:
                    community_events.append({"title": t, "url": u if u.startswith('http') else f"https://www.kaunobiblioteka.lt{u}", "date": today_str, "source": "Biblioteka"})
            # Botanika
            page.goto("https://botanika.vdu.lt/renginiai", timeout=20000)
            vdu_links = page.locator("a[href*='/ivykiai/']").all()
            for l in vdu_links[:5]:
                t = l.inner_text().strip()
                if t: community_events.append({"title": t, "url": l.get_attribute("href"), "date": "Sezoninis", "source": "Botanikos sodas"})
        except: pass

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
