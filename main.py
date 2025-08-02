from fastapi import FastAPI, Query
from scraper import scrape_by_location, scrape_by_name, save_to_excel, create_excel_if_not_exists
from typing import Optional

app = FastAPI()
EXCEL_FILE = "restaurants.xlsx"
# create_excel_if_not_exists(EXCEL_FILE)

@app.get("/")
def welcome():
    return {"message": "Welcome to the Restaurant Scraper API!"}


@app.get("/scrape/location/")
def get_restaurants_by_location(location: str = Query(..., example="Kolkata, India"), limit: int = 10):
    # create_excel_if_not_exists(EXCEL_FILE)
    data = scrape_by_location(location, limit)
    # save_to_excel(EXCEL_FILE, data)
    return {"message": f"{len(data)} results saved for {location}", "data": data}



@app.get("/scrape/name/")
def get_restaurant_by_name(name: str):
    # create_excel_if_not_exists(EXCEL_FILE)
    data = scrape_by_name(name)
    # save_to_excel(EXCEL_FILE, data)
    return {"message": f"Details saved for: {name}", "data": data}

