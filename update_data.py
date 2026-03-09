"""
GitHub Actions robotas (TIKSLUS TAB):
1. Po Regiono spaudžia TAB tik 1 kartą, nes Seniūnija dingsta.
2. Pildo Gatvę ir Numerį per klaviatūrą.
"""
import re
import json
from datetime import date
from playwright.sync_api import sync_playwright

ADDRESS = {
    'region': 'Kauno m. sav.',
    'address': 'Seniavos pl.',
    'houseNumber': '56F',
}

def scrape():
    print("🚀 PALEIDŽIAMAS „VIENO TAB“ ROBOTAS...")
    results = []
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800},
            locale="lt-LT"
        )
        page = context.new_page()
        
        api_data = {}
        page.on("response", lambda r: api_data.update({r.url: (r.json() if 'api/' in r.url and r.status == 200 else None)}) if 'api/' in r.url else None)
        
        try:
            print("🔗 Jungiamasi prie https://grafikai.svara.lt/ ...")
            page.goto("https://grafikai.svara.lt/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(10000)

            def fill_react_select_first(val):
                print(f"🔍 Pildomas Regionas...")
                try:
                    inp = page.locator("input:visible").first
                    inp.click()
                    inp.fill("")
                    page.wait_for_timeout(500)
                    page.keyboard.type(val, delay=150)
                    page.wait_for_timeout(7000)
                    
                    fallback = page.locator("[role='option']:visible, [class*='-option']:visible").first
                    if fallback.count() > 0:
                        fallback.click()
                        print("  ✅ Regionas parinktas.")
                    else:
                        page.keyboard.press("ArrowDown")
                        page.keyboard.press("Enter")
                        print("  ✅ Regionas parinktas (Enter).")
                    return True
                except Exception as e:
                    print(f"  ❌ Klaida Regionui: {e}")
                    return False

            # --- EIGA ---
            fill_react_select_first(ADDRESS['region'])
            page.wait_for_timeout(3000)
            
            # 2. VARTOTOJO PATIKSLINIMAS: TIK VIENAS TAB!
            print("⌨️ TAB iki Gatvės (Seniūnija dingsta)...")
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
            
            # 3. Namo Nr.
            print(f"✍️ Namo numeris: {ADDRESS['houseNumber']}...")
            page.keyboard.press("Tab")
            page.wait_for_timeout(500)
            page.keyboard.type(ADDRESS['houseNumber'], delay=150)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2000)
            
            print("🔍 Ieškome...")
            page.locator("button:has-text('Ieškoti')").first.click()
            page.wait_for_timeout(15000)
            
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
        
        browser.close()
    
    with open('grafikas.json', 'w', encoding='utf-8') as f:
        json.dump({'contracts': results, 'updated_at': date.today().isoformat()}, f, ensure_ascii=False, indent=2)
    print("✅ Baigta!")

if __name__ == "__main__":
    scrape()
