"""
GitHub Actions robotas:
1. Nueina į grafikai.svara.lt
2. Surenka tikras datas
3. Išsaugo į data/grafikas.json
"""
import os
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
    print("Pradedamas duomenų surinkimas...")
    results = []
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        
        api_data = {}
        def on_response(response):
            if 'api/' in response.url and response.status == 200:
                try:
                    api_data[response.url] = response.json()
                except:
                    try:
                        t = response.text()
                        if t: api_data[response.url] = t
                    except: pass
        
        page.on("response", on_response)
        
        # Naršymas
        try:
            page.goto("https://grafikai.svara.lt/", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2000)
            
            # Paieška
            page.keyboard.press("Tab"); page.keyboard.press("Tab")
            page.keyboard.type(ADDRESS['region'], delay=60)
            page.wait_for_timeout(1000)
            page.keyboard.press("ArrowDown"); page.keyboard.press("Enter")
            
            page.keyboard.press("Tab")
            page.keyboard.type(ADDRESS['address'], delay=60)
            page.wait_for_timeout(1000)
            page.keyboard.press("ArrowDown"); page.keyboard.press("Enter")
            
            page.keyboard.press("Tab")
            page.keyboard.type(ADDRESS['houseNumber'], delay=60)
            page.wait_for_timeout(1000)
            page.keyboard.press("ArrowDown"); page.keyboard.press("Enter")
            
            # Ieškoti
            page.evaluate("Array.from(document.querySelectorAll('button')).find(el => el.textContent.trim() === 'Ieškoti').click()")
            page.wait_for_timeout(5000)
            
            # Kontraktai
            contracts_url = next((u for u in api_data if 'api/contracts?' in u), None)
            contracts = []
            if contracts_url and isinstance(api_data[contracts_url], dict):
                contracts = api_data[contracts_url].get('data', [])
            
            print(f"Rasta kontraktų: {len(contracts)}")
            
            # Spaudžiam "Išskleisti vežimo grafiką"
            btns = page.query_selector_all("button:has-text('Išskleisti vežimo grafiką')")
            contract_dates = {}
            
            for i, btn in enumerate(btns):
                urls_before = set(api_data.keys())
                try:
                    btn.click()
                    page.wait_for_timeout(2000)
                    new_urls = [u for u in api_data.keys() if u not in urls_before]
                    
                    found = []
                    for url in new_urls:
                        body = api_data[url]
                        if isinstance(body, list):
                            for item in body:
                                d = item.get('date', '') if isinstance(item, dict) else ''
                                if d: found.append(str(d)[:10])
                        elif isinstance(body, str):
                            found.extend(re.findall(r'(20\d{2}-\d{2}-\d{2})', body))
                    
                    if found:
                        contract_dates[i] = sorted(set(d for d in found if '20' in d))
                except: pass
            
            today_str = date.today().isoformat()
            for idx, c in enumerate(contracts):
                scraped = contract_dates.get(idx, [])
                results.append({
                    'description': c.get('descriptionFmt', 'Atliekos'),
                    'containerType': c.get('containerType', ''),
                    'dates': sorted(d for d in scraped if d >= today_str),
                    'hasRealDates': len(scraped) > 0
                })
                
        except Exception as e:
            print(f"Klaida: {e}")
        
        browser.close()
    
    # Išsaugojimas
    with open('grafikas.json', 'w', encoding='utf-8') as f:
        json.dump({'contracts': results, 'updated_at': date.today().isoformat()}, f, ensure_ascii=False, indent=2)
    print("Duomenys išsaugoti į grafikas.json")

if __name__ == "__main__":
    scrape()
