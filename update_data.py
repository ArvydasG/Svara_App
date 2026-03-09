"""
GitHub Actions robotas (DIAGNOSTINIS):
1. Skenuoja visą HTML struktūrą.
2. Tikrina ar nėra Cloudflare/Captcha blokavimo.
3. Išveda visus matomus elementus į log'us.
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
    print("🚀 PALEIDŽIAMAS SUPER-DETEKTYVAS (DIAGNOSTIKA)...")
    results = []
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        # Bandom dar labiau "žmogišką" naršyklę
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
            # Naudojame domcontentloaded, kad neužstrigtume ties lėtais tracker'iais
            page.goto("https://grafikai.svara.lt/", wait_until="domcontentloaded", timeout=60000)
            print("⏳ Laukiama 10s, kol pasikraus JavaScript dalys...")
            page.wait_for_timeout(10000)

            # --- DIAGNOSTIKA ---
            print("\n--- 🕵️‍♂️ PUSLAPIO ANALIZĖ ---")
            html_content = page.content()
            print(f"Puslapio ilgis: {len(html_content)} simbolių")
            
            if "Verify you are human" in html_content or "Cloudflare" in html_content or "checking your browser" in html_content:
                print("🚨 BLOKAVIMAS: Aptikta botų apsauga (Cloudflare/Captcha)!")
            elif "403 Forbidden" in html_content:
                print("🚨 BLOKAVIMAS: Serveris grąžino 403 (Forbidden)!")
            else:
                print("✅ Blokavimo ženklų nepastebėta.")

            # Išvardinam visus inputus
            inputs = page.locator("input").all()
            print(f"Rasta input'ų: {len(inputs)}")
            for i, inp in enumerate(inputs):
                try: 
                    p = inp.get_attribute("placeholder") or "be pavadinimo"
                    v = inp.is_visible()
                    print(f"  [{i}] Placeholder: '{p}', Matomas: {v}")
                except: pass
            
            # Išvardinam visus mygtukus
            btns = page.locator("button").all()
            print(f"Rasta mygtukų: {len(btns)}")
            for i, btn in enumerate(btns):
                try: 
                    t = btn.inner_text() or "be teksto"
                    print(f"  [{i}] Tekstas: '{t.strip()[:30]}'")
                except: pass
            print("--- ANALIZĖS PABAIGA ---\n")
            # --------------------

            def fill_and_click_first(placeholder_text, value):
                print(f"🔍 Ieškoma lauko: {placeholder_text}...")
                try:
                    # Naudojame lankstų paieškos būdą
                    locator = page.locator(f"input[placeholder*='{placeholder_text}' i]").first
                    
                    if locator.count() > 0:
                        print(f"✍️ Pildoma: {placeholder_text} -> {value}")
                        locator.click(force=True)
                        locator.fill("")
                        page.wait_for_timeout(500)
                        page.keyboard.type(value, delay=100)
                        page.wait_for_timeout(8000) # Laukiam sąrašo
                        
                        # Ieškome pasirodžiusio sąrašo
                        items = page.locator(".v-list-item:visible, [role='option']:visible").first
                        if items.count() > 0:
                            items.click()
                            print(f"✅ Pasirinkta iš sąrašo.")
                        else:
                            print(f"⚠️ Sąrašas neatsirado, naudojama 'Enter'...")
                            page.keyboard.press("ArrowDown")
                            page.keyboard.press("Enter")
                        
                        page.wait_for_timeout(2000)
                        return True
                    else:
                        print(f"ℹ️ Laukas '{placeholder_text}' nerastas.")
                        return False
                except Exception as e:
                    print(f"ℹ️ Klaida ties {placeholder_text}: {str(e)[:50]}")
                    return False

            # Pildymas
            fill_and_click_first("Regionas", ADDRESS['region'])
            fill_and_click_first("Seniūnija", ADDRESS['ward'])
            fill_and_click_first("Gatvė", ADDRESS['address'])
            
            print(f"✍️ Namo numeris: {ADDRESS['houseNumber']}")
            try:
                num_input = page.locator("input[placeholder*='Namo' i]").first
                if num_input.count() > 0:
                    num_input.fill(ADDRESS['houseNumber'])
                else:
                    print("⚠️ Numerio laukas nerastas, bandom paskutinį input.")
                    page.locator("input").last.fill(ADDRESS['houseNumber'])
            except: pass

            print("� Spaudžiama 'Ieškoti'...")
            search_btn = page.locator("button:has-text('Ieškoti')").first
            if search_btn.count() > 0:
                search_btn.click()
            else:
                page.keyboard.press("Enter")
            
            page.wait_for_timeout(15000)
            
            contracts_url = next((u for u in api_data if 'api/contracts?' in u), None)
            resp = api_data.get(contracts_url)
            contracts = resp.get('data', []) if (resp and isinstance(resp, dict)) else []
            
            print(f"📊 Rezultatas: rasta {len(contracts)} kontraktų.")
            
        except Exception as e:
            print(f"❌ KRITIŠKA KLAIDA: {e}")
        
        browser.close()
    
    with open('grafikas.json', 'w', encoding='utf-8') as f:
        json.dump({'contracts': results, 'updated_at': date.today().isoformat()}, f, ensure_ascii=False, indent=2)
    print("🏁 Diagnostika baigta.")

if __name__ == "__main__":
    scrape()
