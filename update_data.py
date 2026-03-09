"""
GitHub Actions robotas (SUPER STABILUS):
1. Išvengia paslėptų laukų problemos
2. Imituoja žmogaus spausdinimą
3. Surenka duomenis net esant lėtam internetui
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
    print("🚀 Paleidžiamas itin stabilus duomenų surinkimas...")
    results = []
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        
        api_data = {}
        page.on("response", lambda r: api_data.update({r.url: r.json()}) if 'api/' in r.url and r.status == 200 else None)
        
        try:
            print("🔗 Jungiamasi prie grafikai.svara.lt...")
            page.goto("https://grafikai.svara.lt/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            
            def fill_safely(placeholder_text, value):
                print(f"✍️ Pildoma: {placeholder_text} -> {value}")
                # Naudojame :visible filtrą, kad neliestų paslėptų laukų
                sel = f"input:visible[placeholder*='{placeholder_text}']"
                page.wait_for_selector(sel, timeout=20000)
                page.locator(sel).click()
                page.locator(sel).fill("") # Išvalom jei kas buvo
                page.type(sel, value, delay=100) # Lėtas spausdinimas
                page.wait_for_timeout(2500)
                page.keyboard.press("ArrowDown")
                page.wait_for_timeout(800)
                page.keyboard.press("Enter")
                page.wait_for_timeout(1000)

            fill_safely("Savivaldybė", ADDRESS['region'])
            fill_safely("Gatvė", ADDRESS['address'])
            fill_safely("numeris", ADDRESS['houseNumber'])
            
            print("🔍 Ieškoma šiukšlių vežimo grafikų...")
            page.locator("button:has-text('Ieškoti')").click()
            page.wait_for_timeout(12000) # Reikia laiko visoms užklausoms
            
            # Ieškome kontraktų
            contracts_url = next((u for u in api_data if 'api/contracts?' in u), None)
            contracts = api_data.get(contracts_url, {}).get('data', []) if contracts_url else []
            print(f"📊 Rasta paslaugų: {len(contracts)}")
            
            if contracts:
                btns = page.query_selector_all("button:has-text('Išskleisti')")
                for i, btn in enumerate(btns):
                    try:
                        btn.click(); page.wait_for_timeout(2500)
                    except: pass
                
                # Surenkame visas gautas datas
                all_dates = []
                for body in api_data.values():
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
    print(f"✅ Baigta! Išsaugota įrašų: {len(results)}")

if __name__ == "__main__":
    scrape()
