import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import (add_log, create_reminder, delete_place, delete_reminder,
                      init_db, list_logs, list_places, list_reminders,
                      mark_triggered, save_place)
from context_engine import evaluate_reminder

load_dotenv()
BASE = Path(__file__).resolve().parent
app = FastAPI(title="SmartRemind", version="3.0.0")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

class ReminderIn(BaseModel):
    task_name: str = Field(min_length=1, max_length=200)
    place_name: str = Field(min_length=1, max_length=255)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_m: float = Field(default=500, gt=0, le=50000)
    weather_condition: Optional[str] = None
    battery_threshold: Optional[int] = Field(default=None, ge=0, le=100)
    time_start: Optional[str] = None
    time_end: Optional[str] = None

class PlaceIn(BaseModel):
    place_name: str = Field(min_length=1, max_length=255)
    place_type: Optional[str] = None
    village: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

class ContextIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    weather: Optional[str] = None
    battery: Optional[int] = Field(default=None, ge=0, le=100)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse(BASE / "templates" / "index.html")

@app.get("/api/reminders")
def reminders():
    return list_reminders()

@app.post("/api/reminders")
def add_reminder(item: ReminderIn):
    return create_reminder(item.model_dump())

@app.delete("/api/reminders/{reminder_id}")
def remove_reminder(reminder_id: int):
    if not delete_reminder(reminder_id):
        raise HTTPException(404, "Reminder not found")
    return {"ok": True}

@app.get("/api/places")
def places():
    return list_places()

@app.post("/api/places")
def add_place(item: PlaceIn):
    return save_place(item.model_dump())

@app.delete("/api/places/{place_id}")
def remove_place(place_id: int):
    if not delete_place(place_id):
        raise HTTPException(404, "Place not found")
    return {"ok": True}

@app.get("/api/logs")
def logs():
    return list_logs(100)

@app.post("/api/context")
def context(ctx: ContextIn):
    reminders = list_reminders(active_only=True)
    results = []
    for r in reminders:
        result = evaluate_reminder(r, ctx.latitude, ctx.longitude, ctx.weather, ctx.battery, datetime.now())
        results.append({"id": r["id"], "task_name": r["task_name"], **result})
        # Avoid repeated notifications while the browser polls every few seconds.
        new_trigger = False
        if result["triggered"]:
            last = r.get("last_triggered_at")
            seconds = (datetime.now() - last).total_seconds() if last else 999999
            if seconds >= 300:
                add_log(r["id"], r["task_name"], result["message"], result["distance_m"])
                mark_triggered(r["id"])
                new_trigger = True
        results[-1]["new_trigger"] = new_trigger
    return {"results": results, "checked_at": datetime.now().isoformat()}

async def nominatim(params):
    headers = {"User-Agent": "SmartRemind/3.0 prototype (context-aware reminder app)"}
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        response = await client.get("https://nominatim.openstreetmap.org/" + params.pop("endpoint"), params=params)
    if response.status_code != 200:
        raise HTTPException(502, "OpenStreetMap location service unavailable")
    return response.json()

@app.get("/api/reverse-geocode")
async def reverse_geocode(lat: float, lon: float):
    data = await nominatim({"endpoint": "reverse", "lat": lat, "lon": lon, "format": "jsonv2", "zoom": 18, "addressdetails": 1})
    address = data.get("address", {})
    place = address.get("village") or address.get("town") or address.get("city") or address.get("municipality") or address.get("suburb") or address.get("county") or "Unknown place"
    return {"place": place, "village": address.get("village", ""), "city": address.get("city") or address.get("town") or "", "district": address.get("state_district") or address.get("county") or "", "state": address.get("state") or "", "country": address.get("country") or "", "display_name": data.get("display_name", place)}

@app.get("/api/geocode")
async def geocode(q: str):
    if len(q.strip()) < 2:
        return []
    data = await nominatim({"endpoint": "search", "q": q.strip(), "format": "jsonv2", "addressdetails": 1, "limit": 5, "countrycodes": "in"})
    results = []
    for item in data:
        a = item.get("address", {})
        place = a.get("village") or a.get("town") or a.get("city") or a.get("municipality") or item.get("name") or q
        results.append({"place": place, "display_name": item.get("display_name", place), "village": a.get("village", ""), "city": a.get("city") or a.get("town") or "", "district": a.get("state_district") or a.get("county") or "", "state": a.get("state") or "", "country": a.get("country") or "", "latitude": float(item["lat"]), "longitude": float(item["lon"])})
    return results

@app.get("/api/weather")
async def weather(lat: float, lon: float):
    params = {"latitude": lat, "longitude": lon, "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m", "hourly": "precipitation_probability", "forecast_days": 1, "timezone": "auto"}
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
    if response.status_code != 200:
        raise HTTPException(502, "Weather service unavailable")
    data = response.json(); current = data.get("current", {}); code = int(current.get("weather_code", 0))
    probs = data.get("hourly", {}).get("precipitation_probability", [])
    return {"temperature": current.get("temperature_2m"), "humidity": current.get("relative_humidity_2m"), "apparent_temperature": current.get("apparent_temperature"), "wind_speed": current.get("wind_speed_10m"), "weather_code": code, "condition": weather_label(code), "rain_probability": max(probs[:3] or [0]), "timezone": data.get("timezone")}

def weather_label(code: int) -> str:
    if code == 0: return "Clear"
    if code in (1, 2, 3): return "Cloudy"
    if code in (45, 48): return "Fog"
    if code in (51, 53, 55, 56, 57): return "Drizzle"
    if code in (61, 63, 65, 66, 67, 80, 81, 82): return "Rain"
    if code in (71, 73, 75, 77, 85, 86): return "Snow"
    if code in (95, 96, 99): return "Thunderstorm"
    return "Unknown"
