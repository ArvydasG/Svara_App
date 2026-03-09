"""
GitHub Actions robotas (SUPER STABILUS):
1. Pataisyti visi laukų pavadinimai (Regionas, Gatvė, Namo nr.).
2. Automatiškai praleidžia Seniūniją, jei ji dingsta.
3. Tikslus pasirinkimas iš sąrašo.
"""
import re
import json
from datetime import date
from playwright.sync_api import sync_playwright

ADDRESS = {
    'region': 'Kauno m. sav.',
    'ward': 'Aleksoto sen.',
    'address': 'Seniavos pl.',
    'houseNumber': '56F',
}

def scrape():
    print("🚀 Pradedamas galutinis duomenų surinkimas...")
    results = []
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        
        api_data = {}
        page.on("response", lambda r: api_data.update({r.url: (r.json() if 'api/' in r.url and r.status == 200 else None)}) if 'api/' in r.url else None)
        
        try:
            print("🔗 Jungiamasi prie https://grafikai.svara.lt/ ...")
            page.goto("https://grafikai.svara.lt/", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            
            def fill_and_click_first(placeholder, value):
                sel = f"input:visible[placeholder*='{placeholder}']"
                if page.locator(sel).count() > 0:
                    print(f"✍️ Pildoma: {placeholder} -> {value}")
                    page.locator(sel).click()
                    page.locator(sel).fill(value)
                    page.wait_for_timeout(3000) # Laukiam kol iššoks sąrašas
                    
                    # Spaudžiame pirmą pasirodžiusį elementą sąraše
                    try:
                        # V-list-item yra standartinis Vuetify sąrašo elementas
                        first_item = page.locator("div.v-list-item:visible").first
                        if first_item.count() > 0:
                            first_item.click()
                            print(f"✅ Pasirinkta iš sąrašo.")
                        else:
                            page.keyboard.press("ArrowDown")
                            page.keyboard.press("Enter")
                    except:
                        page.keyboard.press("ArrowDown")
                        page.keyboard.press("Enter")
                    page.wait_for_timeout(1500)
                    return True
                return False

            # Eiliškumas pagal jūsų nuotraukas:
            fill_and_click_first("Regionas", ADDRESS['region'])
            
            # Jei yra Seniūnija - pildom, jei ne - einam toliau
            if not fill_and_click_first("Seniūnija", ADDRESS['ward']):
                print("ℹ️ Seniūnijos lauko nėra (Kauno m. sav. tai normalu), tęsiama...")
            
            fill_and_click_first("Gatvė", ADDRESS['address'])
            
            print(f"✍️ Rašomas numeris: {ADDRESS['houseNumber']}")
            num_sel = "input:visible[placeholder*='Namo nr.']"
            page.wait_for_selector(num_sel)
            page.locator(num_sel).fill(ADDRESS['houseNumber'])
            page.wait_for_timeout(1000)
            
            print("🔍 Spaudžiama 'Ieškoti'...")
            page.locator("button:has-text('Ieškoti')").click()
            page.wait_for_timeout(12000)
            
            contracts_url = next((u for u in api_data if 'api/contracts?' in u), None)
            resp = api_data.get(contracts_url)
            contracts = resp.get('data', []) if (resp and isinstance(resp, dict)) else []
            
            print(f"📊 Rasta paslaugų: {len(contracts)}")
            
            if contracts:
                btns = page.query_selector_all("button:has-text('Išskleisti')")
                for btn in btns:
                    try: btn.click(); page.wait_for_timeout(3000)
                    except: pass
                
                all_dates = []
                for body in api_data.values():
                    if not body: continue
                    items = body if isinstance(body, list) else body.get('data', []) if isinstance(body, dict) else []
                    for it in (items if isinstance(items, list) else []):
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
    print(f"✅ Baigta! Išsaugojame {len(results)} įrašus.")

if __name__ == "__main__":
    scrape()
