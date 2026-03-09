"""
GitHub Actions robotas (REACT-SELECT SPECIALISTAS):
1. Atpažįsta React-Select ID (pvz. react-select-3-input).
2. Tiksliai randa parinktis pagal ID (react-select-3-option-0).
3. Naudoja indeksus, nes placeholderiai dingsta.
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
    print("🚀 PALEIDŽIAMAS REACT-SELECT EKSPERTAS...")
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
            print("⏳ Laukiama 10s...")
            page.wait_for_timeout(10000)

            def fill_react_select(idx, val, label):
                print(f"🔍 Pildomas {label} (Laukas Nr. {idx})...")
                try:
                    inp = page.locator("input:visible").nth(idx)
                    input_id = inp.get_attribute("id") or ""
                    print(f"  ID: {input_id}")
                    
                    inp.click()
                    inp.fill("")
                    page.wait_for_timeout(500)
                    page.keyboard.type(val, delay=150)
                    page.wait_for_timeout(7000) # Laukiam sąrašo
                    
                    # React-Select magija: parinktys turi ID, prasidedantį tuo pačiu prefixu
                    id_prefix = input_id.replace("-input", "")
                    if id_prefix:
                        option_sel = f"[id^='{id_prefix}-option-']"
                        options = page.locator(option_sel)
                        if options.count() > 0:
                            print(f"  ✅ Rasta {options.count()} parinkčių pagal ID. Spaudžiame pirmą.")
                            options.first.click()
                            page.wait_for_timeout(2000)
                            return True
                    
                    # Jei ID magija nesuveikė, bandom standartinius selektorius
                    # Fix: .css-*-option yra nevalidus CSS. Naudojame [class*='-option']
                    fallback = page.locator("[role='option']:visible, [class*='-option']:visible").first
                    if fallback.count() > 0:
                        fallback.click()
                        print("  ✅ Pasirinkta per fallback selektorių.")
                        page.wait_for_timeout(2000)
                        return True
                        
                    print("  ⚠️ Sąrašo nepavyko rasti, bandom Enter...")
                    page.keyboard.press("ArrowDown")
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(2000)
                    return True
                except Exception as e:
                    print(f"  ❌ Klaida: {e}")
                    return False

            # --- PILDYMO EIGA (NUO GALO) ---
            # 1. Regionas (Visada pirmas)
            fill_react_select(0, ADDRESS['region'], "Regionas")
            page.wait_for_timeout(5000)
            
            # Po Regiono atsiranda kiti laukai.
            # Dažniausiai struktūra: [Regionas, Seniūnija, Gatvė, Namo Nr.] (4 laukai)
            # Arba: [Regionas, Gatvė, Namo Nr.] (3 laukai)
            # Kadangi mums Seniūnijos nereikia, mes pildome:
            # - Paskutinį (Namo Nr.)
            # - Priešpaskutinį (Gatvė)
            
            visible_count = page.locator("input:visible").count()
            print(f"Matomų laukų po Regiono: {visible_count}")
            
            # Pildome Gatvę (Priešpaskutinis laukas, t.y. index -2)
            street_idx = visible_count - 2
            if street_idx > 0:
                fill_react_select(street_idx, ADDRESS['address'], "Gatvė")
                page.wait_for_timeout(3000)
            
            print(f"✍️ Namo numeris (Paskutinis laukas): {ADDRESS['houseNumber']}")
            try:
                num_input = page.locator("input:visible").last
                num_input.click()
                num_input.fill("")
                num_input.type(ADDRESS['houseNumber'], delay=100)
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)
                print("  ✅ Numeris įrašytas.")
            except: pass

            print("🔍 Spaudžiama 'Ieškoti'...")
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
    print(f"✅ Baigta! Išsaugojame {len(results)} įrašus.")

if __name__ == "__main__":
    scrape()
