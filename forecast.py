"""Fetch forecast and write data/forecast.json for scheduled runs."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

ROOT = Path(__file__).parent
OUT = ROOT / "data" / "forecast.json"
TZ = ZoneInfo("Europe/Berlin")
PEAKS = {
    "Großer Waldstein": {"lat": 50.1305, "lon": 11.8505, "elevation": 877},
    "Kösseine": {"lat": 50.0195, "lon": 11.9700, "elevation": 939},
}
HOURLY = [
    "temperature_2m", "dew_point_2m", "relative_humidity_2m",
    "cloud_cover", "cloud_cover_low", "visibility",
    "boundary_layer_height", "wind_speed_10m", "weather_code", "is_day",
]

def main():
    result = {"generated_at": datetime.now(TZ).isoformat(), "source": "Open-Meteo", "peaks": {}}
    for name, p in PEAKS.items():
        params = {
            "latitude": p["lat"], "longitude": p["lon"], "elevation": p["elevation"],
            "hourly": ",".join(HOURLY), "forecast_hours": 48,
            "timezone": "Europe/Berlin", "wind_speed_unit": "kmh",
        }
        r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=25)
        r.raise_for_status()
        result["peaks"][name] = {"elevation": p["elevation"], "hourly": r.json()["hourly"]}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
