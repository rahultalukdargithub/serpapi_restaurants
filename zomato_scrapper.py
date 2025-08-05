from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup

def scrape_zomato_links(city="bangalore", area=None, no_of_restaurants=1000):
    city = city.strip().lower().replace(" ", "-")
    area = area.strip().lower().replace(" ", "-") if area else None

    if area:
        location_path = f"{city}/{area}-restaurants"
    else:
        location_path = f"{city}/restaurants"

    options = Options()
    options.add_argument("--headless")  # NOT --headless=new
    options.add_argument("--no-sandbox")  # 🔥 Absolutely required for Docker
    options.add_argument("--disable-dev-shm-usage")  # 🔥 Prevent /dev/shm crashes
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")


    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    category_ids = [None, 1, 3]
    all_links = set()

    for category_id in category_ids:
        base_url = f"https://www.zomato.com/{location_path}"
        if category_id:
            base_url += f"?category={category_id}"

        print(f"\n[INFO] Starting scrape: {base_url}")
        driver.get(base_url)

        driver.execute_script("window.scrollTo(0, 300)")
        time.sleep(3)

        wait = WebDriverWait(driver, 20)
        try:
            # For delivery category, wait for any React block
            if category_id == 1:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='sc-']")))
                time.sleep(5)

            # Then wait for links
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href]")))
        except:
            print(f"[WARN] Retry: Waiting extra for {base_url}")
            time.sleep(7)
            soup_retry = BeautifulSoup(driver.page_source, 'html.parser')
            if not soup_retry.find_all('a', href=True):
                print(f"[ERROR] Still no cards loaded. Skipping: {base_url}")
                continue

           
        
        restaurant_links = set()
        repeat_count = 0
        max_repeat_limit = 8

        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            links_on_page = set()
            for tag in soup.find_all('a', href=True):
                href = tag['href']
                if not href.startswith("/"):
                    continue

                # Category-aware link filtering
                if category_id == 1:
                    if "/order" in href or "/menu" in href or "/restaurant" in href:
                        links_on_page.add("https://www.zomato.com" + href)
                else:
                    if f"/{city}/" in href and "/info" in href:
                        links_on_page.add("https://www.zomato.com" + href)

            old_count = len(restaurant_links)
            restaurant_links.update(links_on_page)
            new_count = len(restaurant_links)

            print(f"[CATEGORY {category_id or 'default'}] Collected: {new_count}")

            if new_count >= no_of_restaurants:
                print("[✅] Target reached in this category.")
                break

            if new_count == old_count:
                repeat_count += 1
            else:
                repeat_count = 0

            if repeat_count >= max_repeat_limit:
                print("[⚠️] No new links found after scrolling. Moving to next category.")
                break

        all_links.update(restaurant_links)
        if len(all_links) >= no_of_restaurants:
            print("[✅] Target reached .")
            break 

    driver.quit()
    return list(all_links)[:no_of_restaurants]




headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

def get_info(url):
    """Extract restaurant name, address, and telephone from JSON-LD."""
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'lxml')
        scripts = soup.find_all('script', type='application/ld+json')
        if len(scripts) < 2:
            return None

        data = json.loads(scripts[1].string)
        name = data.get('name', None)
        address = data.get('address', {}).get('streetAddress', None)
        phone = data.get('telephone', "NA").strip()
        
        return {
            'Name': name,
            'Address': address,
            'Phone': phone
        }

    except Exception as e:
        print(f"[ERROR] {url} — {e}")
        return None

def get_restaurant_info(url_list, save=True):
    """Process multiple restaurant URLs and optionally save to CSV."""
    data = []
    for url in url_list:
        info = get_info(url)
        if info:
            data.append([
                info['Name'],
                info['Address'],
                info['Phone']
            ])

    return data


def scrapper(city , area , no_of_restaurants):
    urls = scrape_zomato_links(city, area, no_of_restaurants)
    return get_restaurant_info(urls, save=True)



