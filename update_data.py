"""
GitHub Actions robotas (LANKSTUS VARIANTAS):
1. Protingai pildo laukus: jei Seniūnija dingsta, pildo Gatvę.
2. Naudoja tikrą paspaudimą ant sąrašo.
"""
import re
import json
from datetime import date
from playwright.sync_api import sync_playwright
ADDRESS = {
    'region': 'Kauno m. sav.',
    'ward': 'Aleksoto sen.', # Bus naudojama tik jei laukas egzistuoja
    'address': 'Seniavos pl.',
    'houseNumber': '56F',
}
def scrape():
    print("🚀 Paleidžiamas protingas duomenų surinkimas...")
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
            page.wait_for_timeout(5000)
            
            def fill_safely(placeholder_text, value):
                sel = f"input:visible[placeholder*='{placeholder_text}']"
                if page.locator(sel).count() > 0:
                    print(f"✍️ Pildoma: {placeholder_text} -> {value}")
                    page.locator(sel).click()
                    page.locator(sel).fill(value)
                    page.wait_for_timeout(4000)
                    
                    # Bandom spausti pirmą variantą sąraše
                    try:
                        option = page.locator("div.v-list-item").first
                        if option.is_visible():
                            option.click()
                            print(f"✅ Pasirinkta iš sąrašo")
                        else:
                            page.keyboard.press("ArrowDown")
                            page.keyboard.press("Enter")
                    except:
                        page.keyboard.press("ArrowDown")
                        page.keyboard.press("Enter")
                    page.wait_for_timeout(2000)
                    return True
                return False
            # 1. Regionas (Privalomas)
            fill_safely("Regionas", ADDRESS['region'])
            
            # 2. Seniūnija (Tik jei yra)
            if not fill_safely("Seniūnija", ADDRESS['ward']):
                print("ℹ️ Seniūnijos lauko nėra, praleidžiama.")
            
            # 3. Gatvė (Privaloma)
            fill_safely("Gatvė", ADDRESS['address'])
            
            # 4. Namo numeris
            print(f"✍️ Rašomas numeris: {ADDRESS['houseNumber']}")
            num_sel = "input:visible[placeholder*='Namo nr.']"
            page.wait_for_selector(num_sel)
            page.locator(num_sel).fill(ADDRESS['houseNumber'])
            page.wait_for_timeout(1000)
            
            print("🔍 Spaudžiama 'Ieškoti'...")
            page.locator("button:has-text('Ieškoti')").click()
            page.wait_for_timeout(15000)
            
            contracts_url = next((u for u in api_data if 'api/contracts?' in u), None)
            resp = api_data.get(contracts_url)
            contracts = resp.get('data', []) if (resp and isinstance(resp, dict)) else []
            
            print(f"📊 Rasta paslaugų: {len(contracts)}")
            
            if contracts:
                btns = page.query_selector_all("button:has-text('Išskleisti')")
                for btn in btns:
                    try: btn.click(); page.wait_for_timeout(4000)
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
            print(f"❌ Klaida: {e}")
        
        browser.close()
    
    with open('grafikas.json', 'w', encoding='utf-8') as f:
        json.dump({'contracts': results, 'updated_at': date.today().isoformat()}, f, ensure_ascii=False, indent=2)
    print(f"✅ Baigta! Įrašų kiekis: {len(results)}")
if __name__ == "__main__":
    scrape()
