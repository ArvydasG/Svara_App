"""
GitHub Actions DEBUG robotas:
1. Daros ekranų kopijas kiekviename žingsnyje.
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
    print("🚀 PALEIDŽIAMAS DEBUG DUOMENŲ SURINKIMAS...")
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
            print("🔗 Jungiamasi prie grafikai.svara.lt...")
            page.goto("https://grafikai.svara.lt/", wait_until="networkidle", timeout=60000)
            page.screenshot(path="debug_1_start.png")
            
            def fill_and_snap(placeholder_text, value, name):
                sel = f"input:visible[placeholder*='{placeholder_text}']"
                page.wait_for_selector(sel, timeout=20000)
                page.locator(sel).fill(value)
                page.wait_for_timeout(2000)
                page.screenshot(path=f"debug_2_{name}_list.png")
                page.keyboard.press("ArrowDown")
                page.keyboard.press("Enter")
                page.wait_for_timeout(1000)

            fill_and_snap("Savivaldybė", ADDRESS['region'], "region")
            fill_and_snap("Gatvė", ADDRESS['address'], "street")
            fill_and_snap("numeris", ADDRESS['houseNumber'], "number")
            
            page.screenshot(path="debug_3_filled.png")
            print("🔍 Spaudžiamas 'Ieškoti'...")
            page.locator("button:has-text('Ieškoti')").click()
            
            page.wait_for_timeout(10000)
            page.screenshot(path="debug_4_results.png")
            
            # Tikriname ar atsirado mygtukas 'Išskleisti'
            expand_btns = page.query_selector_all("button:has-text('Išskleisti')")
            print(f"📊 Rasta 'Išskleisti' mygtukų: {len(expand_btns)}")
            
            # Jei nieko nerado, gal matosi klaidos pranešimas?
            if len(expand_btns) == 0:
                print("⚠️ Rezultatų lentele nebuvo rasta.")
            
        except Exception as e:
            print(f"❌ KLAIDA: {e}")
            page.screenshot(path="debug_error.png")
        
        browser.close()
    print("✅ Debug sesija baigta.")

if __name__ == "__main__":
    scrape()
