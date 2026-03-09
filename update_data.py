"""
GitHub Actions robotas (VIZUALI DIAGNOSTIKA):
1. Daro nuotraukas po kiekvieno žingsnio.
2. Naudoja 1 TAB po Regiono.
3. Išsaugo puslapio vaizdą po paieškos.
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
    print("🚀 PALEIDŽIAMAS VIZUALUS ROBOTAS-DETEKTYVAS...")
    results = []
    
    # Sukuriame aplanką nuotraukoms, jei jo nėra
    if not os.path.exists('debug'):
        os.makedirs('debug')

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800},
            locale="lt-LT"
        )
        page = context.new_page()
        
        api_data = {}
        def handle_response(r):
            if 'api/' in r.url and r.status == 200:
                try:
                    api_data[r.url] = r.json()
                except: pass
        page.on("response", handle_response)
        
        try:
            print("🔗 Jungiamasi prie https://grafikai.svara.lt/ ...")
            page.goto("https://grafikai.svara.lt/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(10000)
            page.screenshot(path="debug/1_pradzia.png")

            # 1. Regionas
            print(f"🔍 Pildomas Regionas: {ADDRESS['region']}...")
            inp = page.locator("input:visible").first
            inp.click()
            page.keyboard.type(ADDRESS['region'], delay=150)
            page.wait_for_timeout(7000)
            
            options = page.locator("[role='option']:visible, [class*='-option']:visible").first
            if options.count() > 0:
                options.click()
                print("  ✅ Regionas parinktas.")
            else:
                page.keyboard.press("ArrowDown")
                page.keyboard.press("Enter")
                print("  ✅ Regionas parinktas (Enter).")
                
            page.wait_for_timeout(3000)
            page.screenshot(path="debug/2_po_regiono.png")
            
            # 2. TAB iki Gatvės
            print("⌨️ TAB iki Gatvės...")
            page.keyboard.press("Tab")
            page.wait_for_timeout(1000)
            
            # Rašom Gatvę
            print(f"✍️ Gatvė: {ADDRESS['address']}...")
            page.keyboard.type(ADDRESS['address'], delay=120)
            page.wait_for_timeout(8000)
            
            options = page.locator("[role='option']:visible, [class*='-option']:visible").first
            if options.count() > 0:
                options.click()
                print("  ✅ Gatvė parinkta.")
            else:
                page.keyboard.press("ArrowDown")
                page.keyboard.press("Enter")
                print("  ✅ Gatvė parinkta (Enter).")
            
            page.wait_for_timeout(2000)
            page.screenshot(path="debug/3_po_gatves.png")
            
            # 3. Namo numeris
            print(f"✍️ Namo numeris: {ADDRESS['houseNumber']}...")
            page.keyboard.press("Tab")
            page.wait_for_timeout(1000)
            page.keyboard.type(ADDRESS['houseNumber'], delay=150)
            page.wait_for_timeout(1000)
            page.screenshot(path="debug/4_pries_paieska.png")
            
            print("🔍 Spaudžiama 'Ieškoti'...")
            page.locator("button:has-text('Ieškoti')").first.click()
            
            print("⏳ Laukiama rezultatų (20s)...")
            page.wait_for_timeout(20000)
            page.screenshot(path="debug/5_rezultatai.png")
            
            # Išsaugojam tekstą patikrai
            with open('debug/page_text.txt', 'w', encoding='utf-8') as f:
                f.write(page.inner_text("body"))

            contracts_url = next((u for u in api_data if 'api/contracts?' in u), None)
            resp = api_data.get(contracts_url)
            contracts = resp.get('data', []) if (resp and isinstance(resp, dict)) else []
            
            print(f"📊 Rezultatas: rasta {len(contracts)} kontraktų.")
            
            if contracts:
                btns = page.query_selector_all("button:has-text('Išskleisti')")
                for btn in btns:
                    try: 
                        btn.click()
                        page.wait_for_timeout(4000)
                    except: pass
                
                all_dates = []
                for url, body in api_data.items():
                    if not body or 'contracts' in url: continue
                    it_list = body if isinstance(body, list) else body.get('data', []) if isinstance(body, dict) else []
                    if isinstance(it_list, list):
                        for it in it_list:
                            d = it.get('date', '') if isinstance(it, dict) else ''
                            if d: all_dates.append(str(d)[:10])

                unique_dates = sorted(set(d for d in all_dates if re.match(r'20\d{2}-\d{2}-\d{2}', d)))
                today_str = date.today().isoformat()
                
                for c in contracts:
                    results.append({
                        'description': c.get('descriptionFmt', 'Atliekos'),
                        'containerType': c.get('containerType', ''),
                        'dates': sorted([d for d in unique_dates if d >= today_str]),
                        'hasRealDates': len(unique_dates) > 0
                    })
            
        except Exception as e:
            print(f"❌ Nutiko klaida: {e}")
            page.screenshot(path="debug/error.png")
        
        browser.close()
    
    with open('grafikas.json', 'w', encoding='utf-8') as f:
        json.dump({'contracts': results, 'updated_at': date.today().isoformat()}, f, ensure_ascii=False, indent=2)
    print("✅ Baigta! Diagnostikos failai - 'debug' aplanke.")

if __name__ == "__main__":
    scrape()
