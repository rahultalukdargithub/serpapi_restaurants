# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager
# from playwright.sync_api import sync_playwright
# import time
# import re


from bs4 import BeautifulSoup
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------- LINK FETCH (from your backend) ----------
def scrape_zomato_link(city, area=None, no_of_restaurants=1000, timeout=30):
    """Get Zomato restaurant links from your Railway backend."""
    city = city.strip().lower().replace(" ", "-")
    area = area.strip().lower().replace(" ", "-") if area else None

    # Remove trailing slash OR remove leading slash below to avoid double-slash
    base_url = "https://serpapiperpeteer-production.up.railway.app"

    try:
        if area:
            url = f"{base_url}/api/data/location?city={city}&area={area}&limit={no_of_restaurants}"
        else:
            url = f"{base_url}/api/data/location?city={city}&limit={no_of_restaurants}"

        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        payload = r.json()
        data = payload.get("data", [])

        # DEBUG: tell us immediately if we got nothing
        if not data:
            print(f"[WARN] Backend returned 0 links for city='{city}', area='{area}'. URL={url}")
        else:
            # normalize: ensure absolute URLs
            data = [u if u.startswith("http") else f"https://www.zomato.com{u}" for u in data]
        return data

    except Exception as e:
        print(f"[ERROR] Failed to fetch links from backend: {e}")
        return []


# ---------- DETAILS FETCH (direct to Zomato) ----------
from curl_cffi import requests as cf
import time, random, re

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

BASE_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": "https://www.zomato.com/",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}

def _parse_jsonld(soup: BeautifulSoup):
    """Find JSON-LD with Restaurant info (handles list and @graph)."""
    for tag in soup.find_all("script", type="application/ld+json"):
        text = (tag.string or "").strip()
        if not text:
            continue
        try:
            obj = json.loads(text)
        except Exception:
            continue

        candidates = []
        if isinstance(obj, list):
            candidates = obj
        elif isinstance(obj, dict):
            if "@graph" in obj and isinstance(obj["@graph"], list):
                candidates = obj["@graph"]
            else:
                candidates = [obj]

        for it in candidates:
            t = it.get("@type")
            if t in ("Restaurant", "LocalBusiness"):
                return it
    return None

def _fallbacks(soup: BeautifulSoup):
    """Fallbacks when JSON-LD is missing/incomplete."""
    # Name fallback
    name = None
    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(strip=True) or None

    # Address fallback: look for a 'address' microdata or obvious selector
    address = None
    addr = soup.select_one("[itemprop='streetAddress']") or soup.find("address")
    if addr:
        address = addr.get_text(" ", strip=True)

    # Phone fallback from tel: link
    phone = None
    tel = soup.select_one("a[href^='tel:']")
    if tel:
        phone = tel.get_text(strip=True) or tel.get("href", "").replace("tel:", "")

    return name, address, phone

def get_info(url, timeout=60, max_retries=3, proxy=None):
    with cf.Session() as s:
        s.headers.update(BASE_HEADERS)
        if proxy:
            s.proxies = {"http": proxy, "https": proxy}

        for attempt in range(1, max_retries + 1):
            try:
                r = s.get(url, timeout=timeout, impersonate="chrome124", allow_redirects=True)
                # Detect blocks
                if r.status_code in (403, 429):
                    time.sleep(1.5 * attempt + random.random())
                    continue

                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")

                data = _parse_jsonld(soup)
                if data:
                    addr = data.get("address") or {}
                    name = data.get("name")
                    address = (addr.get("streetAddress")
                               or addr.get("addressLocality")
                               or addr.get("addressRegion")
                               or addr.get("addressCountry"))
                    phone = (data.get("telephone") or "NA").strip()
                else:
                    # Use fallbacks if JSON-LD not found
                    name, address, phone = _fallbacks(soup)
                    phone = phone or "NA"

                if not any([name, address, phone]):
                    # maybe blocked by interstitial
                    title = soup.title.get_text(strip=True) if soup.title else ""
                    if "Access denied" in title or "Just a moment" in r.text:
                        time.sleep(1.5 * attempt + random.random())
                        continue
                    # otherwise, treat as no data found
                    return None

                return {"Name": name, "Address": address, "Phone": phone}

            except Exception:
                time.sleep(1.5 * attempt + random.random())
        return None


def get_restaurant_info(urls, workers=8):
    if not urls:
        print("[WARN] No URLs provided to get_restaurant_info()")
        return []

    out = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(get_info, u): u for u in urls}
        for fut in as_completed(futs):
            info = fut.result()
            if info:
                out.append([info["Name"], info["Address"], info["Phone"]])
    return out


def scrapper(city, area, no_of_restaurants):
    urls = scrape_zomato_link(city, area, no_of_restaurants)
    print("Fetched links:", len(urls))
    print(urls)
    if not urls:
        # Early return to make the problem obvious
        return []
    return get_restaurant_info(urls, workers=8)























# def scrape_zomato_links(city="bangalore", area=None, no_of_restaurants=1000):
#     city = city.strip().lower().replace(" ", "-")
#     area = area.strip().lower().replace(" ", "-") if area else None

#     if area:
#         location_path = f"{city}/{area}-restaurants"
#     else:
#         location_path = f"{city}/restaurants"

#     options = Options()
#     options.add_argument("--headless=new")
#     options.add_argument("--disable-gpu")
#     options.add_argument("--window-size=1920,1080")
#     options.add_argument("--disable-blink-features=AutomationControlled")
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

#     category_ids = [None, 1, 3]
#     all_links = set()

#     for category_id in category_ids:
#         base_url = f"https://www.zomato.com/{location_path}"
#         if category_id:
#             base_url += f"?category={category_id}"

#         print(f"\n[INFO] Starting scrape: {base_url}")
#         driver.get(base_url)

#         driver.execute_script("window.scrollTo(0, 300)")
#         time.sleep(3)

#         wait = WebDriverWait(driver, 20)
#         try:
#             # For delivery category, wait for any React block
#             if category_id == 1:
#                 wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='sc-']")))
#                 time.sleep(5)

#             # Then wait for links
#             wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href]")))
#         except:
#             print(f"[WARN] Retry: Waiting extra for {base_url}")
#             time.sleep(7)
#             soup_retry = BeautifulSoup(driver.page_source, 'html.parser')
#             if not soup_retry.find_all('a', href=True):
#                 print(f"[ERROR] Still no cards loaded. Skipping: {base_url}")
#                 continue

           
        
#         restaurant_links = set()
#         repeat_count = 0
#         max_repeat_limit = 8

#         while True:
#             driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#             time.sleep(5)

#             soup = BeautifulSoup(driver.page_source, 'html.parser')
#             links_on_page = set()
#             for tag in soup.find_all('a', href=True):
#                 href = tag['href']
#                 if not href.startswith("/"):
#                     continue

#                 # Category-aware link filtering
#                 if category_id == 1:
#                     if "/order" in href or "/menu" in href or "/restaurant" in href:
#                         links_on_page.add("https://www.zomato.com" + href)
#                 else:
#                     if f"/{city}/" in href and "/info" in href:
#                         links_on_page.add("https://www.zomato.com" + href)

#             old_count = len(restaurant_links)
#             restaurant_links.update(links_on_page)
#             new_count = len(restaurant_links)

#             print(f"[CATEGORY {category_id or 'default'}] Collected: {new_count}")

#             if new_count >= no_of_restaurants:
#                 print("[✅] Target reached in this category.")
#                 break

#             if new_count == old_count:
#                 repeat_count += 1
#             else:
#                 repeat_count = 0

#             if repeat_count >= max_repeat_limit:
#                 print("[⚠️] No new links found after scrolling. Moving to next category.")
#                 break

#         all_links.update(restaurant_links)
#         if len(all_links) >= no_of_restaurants:
#             print("[✅] Target reached .")
#             break 

#     driver.quit()
#     return list(all_links)[:no_of_restaurants]

# from playwright.async_api import async_playwright
# from bs4 import BeautifulSoup

# async def scrape_zomato_link(city, area=None, no_of_restaurants=1000):
#     city = city.strip().lower().replace(" ", "-")
#     area = area.strip().lower().replace(" ", "-") if area else None
#     location_path = f"{city}/{area}-restaurants" if area else f"{city}/restaurants"

#     category_ids = [None, 1, 3]
#     all_links = set()

#     async with async_playwright() as p:
#         browser = await p.firefox.launch(headless=True)
#         context = await browser.new_context(
#             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
#             viewport={"width": 1280, "height": 800},
#             locale="en-US"
#         )
#         page = await context.new_page()

#         for category_id in category_ids:
#             base_url = f"https://www.zomato.com/{location_path}"
#             if category_id:
#                 base_url += f"?category={category_id}"

#             print(f"[INFO] Starting scrape: {base_url}")
#             await page.goto(base_url, timeout=60000)
#             await page.wait_for_timeout(3000)

#             if category_id == 1:
#                 try:
#                     await page.wait_for_selector("div[class*='sc-']", timeout=15000)
#                     await page.wait_for_timeout(5000)
#                 except:
#                     print("[WARN] Delivery content load failed.")

#             restaurant_links = set()
#             repeat_count = 0
#             max_repeat_limit = 8

#             while True:
#                 await page.mouse.wheel(0, 50000)
#                 await page.wait_for_timeout(5000)

#                 html = await page.content()
#                 soup = BeautifulSoup(html, "html.parser")
#                 links_on_page = set()

#                 for tag in soup.find_all('a', href=True):
#                     href = tag['href']
#                     if not href.startswith("/"):
#                         continue

#                     if category_id == 1:
#                         if any(x in href for x in ["/order", "/menu", "/restaurant"]):
#                             links_on_page.add("https://www.zomato.com" + href)
#                     else:
#                         if f"/{city}/" in href and "/info" in href:
#                             links_on_page.add("https://www.zomato.com" + href)

#                 old_count = len(restaurant_links)
#                 restaurant_links.update(links_on_page)
#                 new_count = len(restaurant_links)

#                 print(f"[CATEGORY {category_id or 'default'}] Collected: {new_count}")

#                 if new_count >= no_of_restaurants:
#                     print("[✅] Target reached in this category.")
#                     break

#                 if new_count == old_count:
#                     repeat_count += 1
#                 else:
#                     repeat_count = 0

#                 if repeat_count >= max_repeat_limit:
#                     print("[⚠️] No new links found after scrolling. Moving to next category.")
#                     break

#             all_links.update(restaurant_links)
#             if len(all_links) >= no_of_restaurants:
#                 print("[✅] Global target reached.")
#                 break

#         await browser.close()

#     return list(all_links)








