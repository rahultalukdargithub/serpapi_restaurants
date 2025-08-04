from serpapi import GoogleSearch
import openpyxl
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

API_KEY = os.getenv("SERPAPI_KEY")


def geocode_with_nominatim(location):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": location,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "restaurant-scraper-bot"
    }

    response = requests.get(url, params=params, headers=headers).json()
    if response:
        lat = response[0]["lat"]
        lon = response[0]["lon"]
        print(f"Geocoded {location} to lat: {lat}, lon: {lon}")
        return float(lat), float(lon)
    else:
        return None, None



def create_excel_if_not_exists(filename):
    if not os.path.exists(filename):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Name", "Address", "Contact"])
        wb.save(filename)

def save_to_excel(filename, rows):
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    for row in rows:
        ws.append(row)
    wb.save(filename)


def scrape_by_location(location_name, limit=10):
    lat, lng = geocode_with_nominatim(location_name)
    if not lat or not lng:
        return [["❌ Could not geocode location: " + location_name]]

    all_data = []
    start = 0

    while len(all_data) < limit:
        params = {
            "engine": "google_maps",
            "q": "restaurants",
            "type": "search",
            "ll": f"@{lat},{lng},16z",
            "start": start,
            "google_domain": "google.co.in",
            "hl": "en",
            "api_key": API_KEY
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        places = results.get("local_results", [])

        if not places:
            break  # No more results

        for place in places:
            if len(all_data) >= limit:
                break
            name = place.get("title", "")
            address = place.get("address", "")
            phone = place.get("phone", "")
            all_data.append([name, address, phone])

        start += 20  # Go to next page if needed

    return all_data

def scrape_by_name(name):
    params = {
        "engine": "google_maps",
        "q": name,
        "type": "search",
        "api_key": API_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    place = results.get("local_results", [])[0] if results.get("local_results") else {}
    # print(place.get("title", ""), place.get("address", ""), place.get("phone", ""))
    return [[
        place.get("title", ""),
        place.get("address", ""),
        place.get("phone", "")
    ]]


