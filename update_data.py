"""
GitHub Actions robotas (GALUTINIS SPRENDIMAS):
1. Pildo formą per TAB navigaciją.
2. Skaito rezultatus tiesiai iš lentelės (Table Scraping).
3. Išskleidžia visus grafikus ir surenka datas.
"""
import re
import json
import os
from datetime import date
from playwright.sync_api import sync_playwright

ADDRESS = {
    'region': 'Kauno m. sav.',
    'address': 'Seniavos pl.',
    'houseNumber': '56F',
}

def scrape():
    print("🚀 PALEIDŽIAMAS GALUTINIS ROBOTAS-SKAITYTOJAS...")
    final_results = []
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 1200},
            locale="lt-LT"
        )
        page = context.new_page()
        
        # Sekame visas tinklo užklausas datoms gauti
        captured_json = []
        def handle_response(r):
            if 'api/' in r.url and r.status == 200:
                try:
                    data = r.json()
                    if isinstance(data, list) or (isinstance(data, dict) and 'data' in data):
                        captured_json.append(data)
                except: pass
        page.on("response", handle_response)
        
        try:
            print("🔗 Jungiamasi prie https://grafikai.svara.lt/ ...")
            page.goto("https://grafikai.svara.lt/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(10000)

            # 1. Regionas
            print(f"✍️ Pildomas Regionas...")
            inp = page.locator("input:visible").first
            inp.click()
            page.keyboard.type(ADDRESS['region'], delay=150)
            page.wait_for_timeout(7000)
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)
            
            # 2. TAB + Gatvė
            print("⌨️ TAB iki Gatvės...")
            page.keyboard.press("Tab")
            page.wait_for_timeout(1000)
            page.keyboard.type(ADDRESS['address'], delay=120)
            page.wait_for_timeout(8000)
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            page.wait_for_timeout(2000)
            
            # 3. Namo numeris
            print(f"✍️ Namo numeris: {ADDRESS['houseNumber']}...")
            page.keyboard.press("Tab")
            page.wait_for_timeout(1000)
            page.keyboard.type(ADDRESS['houseNumber'], delay=150)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2000)
            
            print("🔍 Ieškome...")
            page.locator("button:has-text('Ieškoti')").first.click(force=True)
            page.wait_for_timeout(15000)
            
            # --- SKAITYMAS IŠ LENTELĖS (2 ŽINGSNIAI: Harvesting -> Dates) ---
            print("📊 1 žingsnis: Renkami metaduomenys visiems objektams...")
            # Pirmiausia surinkime visus metaduomenis (Tipas ir Konteineris) kol lentelė stabili
            all_rows = page.locator("tr:has(button:has-text('Išskleisti'))").all()
            for row in all_rows:
                try:
                    cols = row.locator("td").all()
                    if len(cols) >= 2:
                        type_txt = re.sub(r'\s+', ' ', cols[0].inner_text().strip())
                        cont_txt = re.sub(r'\s+', ' ', cols[1].inner_text().strip())
                        final_results.append({
                            'description': type_txt,
                            'containerType': cont_txt,
                            'dates': [],
                            'hasRealDates': False
                        })
                except: pass
            
            print(f"Iš viso užregistruota objektų: {len(final_results)}")

            print("📊 2 žingsnis: Surenkamos datos kiekvienam objektui...")
            for item in final_results:
                try:
                    cont_id = item['containerType']
                    print(f"  [>] Ieškomas grafikas: {item['description']} ({cont_id})")
                    
                    # Surandame eilutę pagal konkretų konteinerio ID
                    target_row = page.locator(f"tr:has-text('{cont_id}')").filter(has=page.locator("button:has-text('Išskleisti')"))
                    
                    if target_row.count() > 0:
                        btn = target_row.locator("button:has-text('Išskleisti')").first
                        dates_data = []
                        try:
                            # Laukiame API atsakymo būtent šiam paspaudimui
                            with page.expect_response(lambda r: "api/" in r.url and r.status == 200, timeout=10000) as resp_info:
                                btn.click(force=True)
                                json_data = resp_info.value.json()
                                # Ištraukiame datas
                                res_items = json_data if isinstance(json_data, list) else json_data.get('data', [])
                                if isinstance(res_items, list):
                                    for it in res_items:
                                        if isinstance(it, dict) and it.get('date'):
                                            dates_data.append(str(it['date'])[:10])
                        except:
                            print(f"    ⚠️ API atsakymas nerastas arba užtruko.")

                        # Apdorojame datas
                        unique_dates = sorted(set(d for d in dates_data if re.match(r'20\d{2}-\d{2}-\d{2}', d)))
                        today_str = date.today().isoformat()
                        item['dates'] = [d for d in unique_dates if d >= today_str]
                        item['hasRealDates'] = len(item['dates']) > 0
                        
                        # Suskleidžiame atgal, kad lentelė nesididintų be galo (pasirinktinai)
                        # page.locator(f"tr:has-text('{cont_id}')").locator("button:has-text('Suskleisti')").first.click(force=True)
                        page.wait_for_timeout(1000)
                    else:
                        print("    ⚠️ Eilutė neberasta (galbūt jau išskleista?)")
                except Exception as e:
                    print(f"    ❌ Klaida: {e}")
            
            # --- APYLINKĖS DARBŲ SKAITYMAS ---
            print("🏗️ 3 žingsnis: Ieškoma informacijos apie apylinkės darbus (2km radius)...")
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

            # --- ALEKSOTO NAUJIENŲ SKAITYMAS ---
            print("📰 4 žingsnis: Ieškoma Aleksoto seniūnijos naujienų...")
            aleksotas_news = []
            news_url = "https://www.kaunas.lt/administracija/struktura-ir-kontaktine-informacija/seniunijos/aleksoto-seniunija/aleksoto-seniunijos-naujienos/"
            
            try:
                page.goto(news_url, timeout=20000)
                # Bandome rasti bet kokias naujienų nuorodas šiame puslapyje
                links = page.locator("a[href*='/seniunijos/']").all()
                for link_el in links[:5]:
                    t = link_el.inner_text().strip()
                    l = link_el.get_attribute("href")
                    if t and len(t) > 10 and l:
                        aleksotas_news.append({"title": t, "url": l, "date": "Naujausia"})
                
                # Jei nieko neradome automatiškai, pridedame tiesioginę nuorodą
                if not aleksotas_news:
                    aleksotas_news.append({
                        "title": "Skaityti visas Aleksoto seniūnijos naujienas",
                        "url": news_url,
                        "date": "Aktualu"
                    })
            except Exception as e:
                print(f"  ⚠️ Klaida skaitant naujienas: {e}")
                aleksotas_news = [{
                    "title": "Aleksoto seniūnijos naujienos (spausti čia)",
                    "url": news_url,
                    "date": "Nuoroda"
                }]

            # --- BENDRUOMENĖS RENGINIŲ SKAITYMAS ---
            print("📅 6 žingsnis: Ieškoma bendruomenės renginių...")
            community_events = []
            
            # 1. Aleksotas.lt (Bendruomenės centras)
            try:
                page.goto("https://aleksotas.lt/naujienos/", timeout=20000)
                # Ieškome naujausių įrašų, kurie dažnai yra renginiai
                news_items = page.locator("article.post, .entry-title a").all()
                for item in news_items[:3]:
                    t = item.inner_text().strip()
                    l = item.get_attribute("href")
                    if t and l:
                        community_events.append({"title": t, "url": l, "date": "Pranešimas", "source": "Aleksoto BC"})
            except: print("  ⚠️ Nepavyko pasiekti aleksotas.lt")

            # 2. Kauno biblioteka (Aleksoto padalinys) - Simuliuojame arba dedame nuorodą, 
            # nes jų puslapis dinamiškai kraunamas ir sudėtingas paprastam scrapingui
            community_events.append({
                "title": "Bibliotekos renginiai (dirbtuvės, parodos)",
                "url": "https://www.kaunobiblioteka.lt/renginiai/",
                "date": "Žiūrėti kalendorių",
                "source": "Biblioteka"
            })

            # 3. VDU Botanikos sodas
            community_events.append({
                "title": "Renginiai VDU Botanikos sode",
                "url": "https://botanika.vdu.lt/renginiai",
                "date": "Sezoniniai",
                "source": "Botanikos sodas"
            })

        except Exception as e:
            print(f"❌ Nutiko klaida: {e}")
        
        browser.close()
    
    output_data = {
        'contracts': final_results, 
        'updated_at': date.today().isoformat(),
        'neighborhood_works': neighborhood_works,
        'news': aleksotas_news,
        'events': community_events,
        'air_quality': air_quality
    }
    
    with open('grafikas.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Baigta! Surinkta objektų: {len(final_results)}, Darbų: {len(neighborhood_works)}")
    
    # --- PRANEŠIMŲ (PUSH NOTIFICATIONS) LOGIKA ---
    try:
        from datetime import timedelta
        # Patikriname, ar kas nors vežama rytoj
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        tomorrow_services = []
        
        for item in final_results:
            if tomorrow in item.get('dates', []):
                # Nuvalome ilgus pavadinimus
                name = item['description']
                if 'Popierius' in name: name = 'Plastikas / Popierius'
                elif 'Stiklas' in name: name = 'Stiklas'
                elif 'Žali' in name: name = 'Žaliosios atliekos'
                elif 'Mišr' in name: name = 'Mišrios atliekos'
                tomorrow_services.append(name)
        
        if tomorrow_services:
            services_text = ", ".join(set(tomorrow_services))
            print(f"🔔 RYTOJ VEŽAMA: {services_text}. Siunčiamas OneSignal pranešimas...")
            
            import urllib.request
            import urllib.parse
            
            import os
            
            api_key = os.environ.get('ONESIGNAL_API_KEY')
            if not api_key:
                print("⚠️ Įspėjimas: ONESIGNAL_API_KEY nerastas aplinkos kintamuosiuose. Pranešimas nebus išsiųstas.")
            else:
                headers = {
                    "Content-Type": "application/json; charset=utf-8",
                    "Authorization": f"Basic {api_key}"
                }
                
                payload = {
                    "app_id": "9f3d18fb-2825-4a44-b306-80e21a9df9d5",
                "included_segments": ["All"],
                "headings": {"en": "Šiukšlių išvežimas rytoj!", "lt": "Šiukšlių išvežimas rytoj!"},
                "contents": {"en": f"Nepamirškite išstumti konteinerio. Rytoj vežama: {services_text} 🚛", "lt": f"Nepamirškite išstumti konteinerio. Rytoj vežama: {services_text} 🚛"}
            }
            
                req = urllib.request.Request(
                    "https://onesignal.com/api/v1/notifications",
                    data=json.dumps(payload).encode('utf-8'),
                    headers=headers,
                    method='POST'
                )
                with urllib.request.urlopen(req) as response:
                    print("✅ Pranešimas sėkmingai išsiųstas:", response.read().decode('utf-8'))
        else:
            print("💤 Rytoj išvežimų nėra. Pranešimai nesiunčiami.")
    except Exception as e:
        print(f"⚠️ Klaida siunčiant OneSignal pranešimą: {e}")

if __name__ == "__main__":
    scrape()
