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
            
            # --- SKAITYMAS IŠ LENTELĖS ---
            print("📊 Analizuojama lentelė...")
            rows = page.locator("table tbody tr").all()
            print(f"Rasta eilučių: {len(rows)}")
            
            for i, row in enumerate(rows):
                try:
                    cols = row.locator("td").all()
                    if len(cols) < 3: continue
                    
                    # Ištraukiame tekstą iš stulpelių
                    type_text = cols[0].inner_text().strip()
                    container_text = cols[1].inner_text().strip()
                    print(f"  [{i}] {type_text} ({container_text})")
                    
                    # Spaudžiame "Išskleisti" šiai eilutei
                    expand_btn = row.locator("button:has-text('Išskleisti')")
                    if expand_btn.count() > 0:
                        expand_btn.click()
                        page.wait_for_timeout(3000)
                    
                    final_results.append({
                        'description': type_text,
                        'containerType': container_text,
                        'dates': [], # Užpildysime vėliau iš captured_json
                        'hasRealDates': False
                    })
                except Exception as e:
                    print(f"  ❌ Klaida eilutėje {i}: {e}")

            # Išrenkame visas datas iš visų pagautų JSON atsakymų
            all_dates = []
            for data in captured_json:
                items = data if isinstance(data, list) else data.get('data', [])
                if isinstance(items, list):
                    for it in items:
                        if isinstance(it, dict):
                            d = it.get('date', '')
                            if d: all_dates.append(str(d)[:10])

            unique_dates = sorted(set(d for d in all_dates if re.match(r'20\d{2}-\d{2}-\d{2}', d)))
            today_str = date.today().isoformat()
            future_dates = [d for d in unique_dates if d >= today_str]
            
            # Priskiriame datas kiekvienam kontraktui (supaprastinta - visos datos visiems, nes jos ateina bendrai)
            for res in final_results:
                res['dates'] = future_dates
                res['hasRealDates'] = len(future_dates) > 0
            
        except Exception as e:
            print(f"❌ Nutiko klaida: {e}")
        
        browser.close()
    
    with open('grafikas.json', 'w', encoding='utf-8') as f:
        json.dump({'contracts': final_results, 'updated_at': date.today().isoformat()}, f, ensure_ascii=False, indent=2)
    print(f"✅ Baigta! Surinkta objektų: {len(final_results)}")

if __name__ == "__main__":
    scrape()
