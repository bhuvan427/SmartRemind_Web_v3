from datetime import time
from math import radians, sin, cos, sqrt, atan2


def distance_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = radians(lat1), radians(lat2)
    dp, dl = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dp/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2
    return 2*R*atan2(sqrt(a), sqrt(1-a))


def evaluate_reminder(r, lat, lon, weather, battery, now):
    dist = distance_m(lat, lon, r["latitude"], r["longitude"])
    location_ok = dist <= float(r["radius_m"])
    weather_ok = True if not r.get("weather_condition") else bool(weather) and weather.lower() == r["weather_condition"].lower()
    battery_ok = True if r.get("battery_threshold") is None else (battery is not None and battery <= int(r["battery_threshold"]))
    # Time window handling: support start-only, end-only or both. Empty/None means ignored.
    time_ok = True
    start, end = r.get("time_start"), r.get("time_end")
    if start or end:
        try:
            current = now.time()
            if start and end:
                s = time.fromisoformat(start); e = time.fromisoformat(end)
                time_ok = s <= current <= e if s <= e else (current >= s or current <= e)
            elif start:
                s = time.fromisoformat(start)
                time_ok = current >= s
            else:
                e = time.fromisoformat(end)
                time_ok = current <= e
        except Exception:
            time_ok = False

    # Alert tiers based on proximity: <=200m => 2 alerts, <=1000m => 1 alert, else 0
    alert_count = 0
    if dist <= 200:
        alert_count = 2
    elif dist <= 1000:
        alert_count = 1

    triggered = (alert_count > 0) and weather_ok and battery_ok and time_ok
    checks = {"location": location_ok, "weather": weather_ok, "battery": battery_ok, "time": time_ok}
    message = f"You're within {round(dist)} m of {r['place_name']}. {r['task_name']}"
    return {"triggered": triggered, "distance_m": round(dist, 1), "checks": checks, "message": message, "alert_count": alert_count}
