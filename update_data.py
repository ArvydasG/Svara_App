"""
GitHub Actions robotas (PILDYMAS PAGAL INDEKSUS):
1. Kadangi 'placeholder' dingsta GitHub'e, naudojame eiliškumą.
2. Detaliai išveda HTML atributus pildymo metu.
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
    print("🚀 PALEIDŽIAMAS ROBOTAS-INDEKSAS...")
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
            print("⏳ Laukiama 10s, kol viskas pasikraus...")
            page.wait_for_timeout(10000)

            # Matomi laukai:
            # 0: Regionas
            # 1: Seniūnija (gali būti Gatvė, jei Seniūnijos nėra)
            # 2: Gatvė (arba Namo nr.)
            
            visible_inputs = page.locator("input:visible")
            count = visible_inputs.count()
            print(f"Iš viso matomų laukų: {count}")

            def fill_by_index(idx, val, label_for_log):
                print(f"🔍 Pildomas laukas Nr. {idx} ({label_for_log}) -> {val}")
                try:
                    inp = page.locator("input:visible").nth(idx)
                    # Debug: koks čia laukas iš tikrųjų?
                    html = inp.evaluate("el => el.outerHTML")
                    print(f"  Info: {html[:150]}...")
                    
                    inp.click()
                    inp.fill("")
                    page.wait_for_timeout(500)
                    page.keyboard.type(val, delay=150)
                    page.wait_for_timeout(8000) # Laukiam sąrašo
                    
                    # Spaudžiam pirmą elementą sąraše
                    item = page.locator(".v-list-item:visible, [role='option']:visible").first
                    if item.count() > 0:
                        item.click()
                        print(f"  ✅ Pasirinkta iš sąrašo.")
                    else:
                        print(f"  ⚠️ Sąrašo nėra, bandom Enter...")
                        page.keyboard.press("ArrowDown")
                        page.keyboard.press("Enter")
                    
                    page.wait_for_timeout(2000)
                    return True
                except Exception as e:
                    print(f"  ❌ Klaida ties lauku {idx}: {e}")
                    return False

            # --- PILDYMO EIGA ---
            # 1. VISADA Regionas
            fill_by_index(0, ADDRESS['region'], "Regionas")
            
            # Po Regiono užpildymo laukų skaičius gali pasikeisti!
            page.wait_for_timeout(3000)
            visible_inputs = page.locator("input:visible")
            count = visible_inputs.count()
            print(f"Laukų po Regiono: {count}")

            # 2. Gatvė (dažniausiai indeksas 1 arba 2)
            # Kauno m. sav. Seniūnijos dažnai nėra, todėl indeksas 1 bus Gatvė
            # Bet bandom rasti Gatvę bet kuriame likusiame lauke
            found_street = False
            for i in range(1, count):
                # Patikrinam ar tai ne Namo nr. (jis paprastai trumpesnis arba paskutinis)
                if i == count - 1: continue 
                if fill_by_index(i, ADDRESS['address'], "Gatvė?"):
                    found_street = True
                    break
            
            # 3. Namo numeris (PASKUTINIS matomas laukas)
            print(f"✍️ Namo numeris: {ADDRESS['houseNumber']}")
            try:
                last_inp = page.locator("input:visible").last
                last_inp.fill(ADDRESS['houseNumber'])
                page.wait_for_timeout(1000)
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
