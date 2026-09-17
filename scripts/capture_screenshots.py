import os
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 1440x900 viewport with 2x retina device scale factor for crystal clear resolution
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2
        )
        page = context.new_page()
        
        print("Navigating to http://localhost:8000...")
        page.goto("http://localhost:8000")
        page.wait_for_timeout(2000) # Wait for initial data fetch and icon rendering
        
        # 1. Dashboard screenshot
        print("Capturing dashboard.png...")
        page.screenshot(path=os.path.join(OUTPUT_DIR, "dashboard.png"))
        
        # 2. CRM Kanban screenshot
        print("Capturing crm-kanban.png...")
        page.click("#nav-crm")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "crm-kanban.png"))
        
        # 3. Composer screenshot
        print("Capturing composer.png...")
        page.click("#nav-composer")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "composer.png"))
        
        # 4. Dispatcher screenshot
        print("Capturing dispatcher.png...")
        page.click("#nav-campaign")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "dispatcher.png"))
        
        # 5. Settings Vault screenshot
        print("Capturing settings.png...")
        page.click("#nav-settings")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "settings.png"))
        
        browser.close()
        print(f"All screenshots successfully saved to {OUTPUT_DIR}!")

if __name__ == "__main__":
    capture()
