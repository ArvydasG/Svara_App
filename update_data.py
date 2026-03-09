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
            
        except Exception as e:
            print(f"❌ Nutiko klaida: {e}")
        
        browser.close()
    
    with open('grafikas.json', 'w', encoding='utf-8') as f:
        json.dump({'contracts': final_results, 'updated_at': date.today().isoformat()}, f, ensure_ascii=False, indent=2)
    print(f"✅ Baigta lentelės analizė! Surinkta objektų: {len(final_results)}")
    
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
