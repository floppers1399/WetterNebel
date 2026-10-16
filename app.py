import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

TZ = ZoneInfo("Europe/Berlin")
DATA_FILE = Path(__file__).parent / "data" / "forecast.json"

PEAKS = {
    "Großer Waldstein": {
        "lat": 50.1305, "lon": 11.8505, "elevation": 877,
        "note": "Gipfelhöhe ca. 877 m ü. NHN",
    },
    "Kösseine": {
        "lat": 50.0195, "lon": 11.9700, "elevation": 939,
        "note": "Gipfelhöhe ca. 939 m ü. NHN",
    },
}

HOURLY = [
    "temperature_2m", "dew_point_2m", "relative_humidity_2m",
    "cloud_cover", "cloud_cover_low", "visibility",
    "boundary_layer_height", "wind_speed_10m", "weather_code", "is_day",
]

st.set_page_config(page_title="Wolkenmeer-Prognose | Fichtelgebirge", page_icon="🌫️", layout="wide")
st.title("🌫️ Wolkenmeer-Prognose")
st.caption("Großer Waldstein · Kösseine · 24-Stunden-Ausblick")

st.warning(
    "Prototyp mit Unsicherheit: Die Oberkante einer Nebelschicht wird von der Wetter-API "
    "nicht direkt und verlässlich geliefert. Die Höhenangabe unten ist daher nur eine "
    "heuristische Orientierung aus Grenzschichthöhe und Nebelindikatoren – kein Messwert "
    "und keine garantierte Nebeloberkante."
)

@st.cache_data(ttl=30 * 60, show_spinner=False)
def get_forecast(name: str, lat: float, lon: float, elevation: int) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "elevation": elevation,
        "hourly": ",".join(HOURLY),
        "forecast_hours": 48,
        "timezone": "Europe/Berlin",
        "wind_speed_unit": "kmh",
    }
    response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=25)
    response.raise_for_status()
    payload = response.json()
    hourly = payload["hourly"]
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"])
    df["peak"] = name
    df["peak_elevation"] = elevation
    df["visibility_km"] = df["visibility"] / 1000
    df["dewpoint_spread"] = df["temperature_2m"] - df["dew_point_2m"]

    # Heuristic only. Boundary-layer height is NOT the same as fog-top height.
    # We only show a broad indicative range when near-saturation and low-cloud
    # indicators support a fog/low-stratus scenario.
    humid = (df["relative_humidity_2m"] >= 92) & (df["dewpoint_spread"] <= 1.8)
    low_cloud = (df["cloud_cover_low"] >= 60) | (df["cloud_cover"] >= 85)
    calm_enough = df["wind_speed_10m"] <= 22
    indicators = humid & low_cloud & calm_enough
    pbl = df["boundary_layer_height"].clip(lower=100, upper=1200)
    estimate = elevation + (pbl * 0.35)
    df["fog_top_estimate_m"] = estimate.where(indicators)
    df["fog_top_low_m"] = (estimate - 250).where(indicators)
    df["fog_top_high_m"] = (estimate + 250).where(indicators)
    df["fog_signal"] = indicators
    df["summit_above_estimate"] = df["fog_top_high_m"] < elevation
    return df

def load_data():
    frames = []
    errors = []
    for name, p in PEAKS.items():
        try:
            frames.append(get_forecast(name, p["lat"], p["lon"], p["elevation"]))
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    if frames:
        return pd.concat(frames, ignore_index=True), errors
    return pd.DataFrame(), errors

with st.spinner("Hole aktuelle Wettermodelldaten …"):
    all_data, errors = load_data()

if all_data.empty:
    st.error("Die Wetterdaten konnten nicht abgerufen werden. Prüfe die Internetverbindung und versuche es erneut.")
    for error in errors:
        st.caption(error)
    st.stop()

now = pd.Timestamp(datetime.now(TZ).replace(tzinfo=None))
future = all_data[all_data["time"] >= now].copy()
if future.empty:
    future = all_data.copy()
start = future["time"].min()
window = future[future["time"] < start + pd.Timedelta(hours=24)].copy()
if window.empty:
    window = future.head(24).copy()

st.caption(f"Letzter Abruf: {datetime.now(TZ).strftime('%d.%m.%Y, %H:%M')} Uhr · Quelle: Open-Meteo")
if errors:
    st.warning("Nicht alle Gipfel konnten geladen werden: " + " | ".join(errors))

# Summary cards: compare the next 24 hours, with emphasis on daytime.
daylight = window[window["is_day"] == 1]
scoring = daylight if not daylight.empty else window
cards = st.columns(2)
for col, (name, peak) in zip(cards, PEAKS.items()):
    data = scoring[scoring["peak"] == name]
    with col:
        st.subheader(name)
        st.metric("Gipfelhöhe", f'{peak["elevation"]} m')
        if data.empty:
            st.info("Für diesen Gipfel liegen keine Daten vor.")
            continue
        signal_hours = int(data["fog_signal"].sum())
        visible = data["visibility_km"].median()
        st.metric("Stunden mit Nebelindikatoren", f"{signal_hours} / {len(data)}")
        st.metric("Mittlere Modell-Sichtweite", f"{visible:.1f} km" if pd.notna(visible) else "keine Angabe")
        if signal_hours:
            est = data.loc[data["fog_signal"], "fog_top_estimate_m"].median()
            lo = data.loc[data["fog_signal"], "fog_top_low_m"].median()
            hi = data.loc[data["fog_signal"], "fog_top_high_m"].median()
            st.write(f"**Grobe Höhenorientierung:** {est:.0f} m ü. NHN")
            st.caption(f"Heuristischer Bereich: {lo:.0f}–{hi:.0f} m ü. NHN (mindestens ±250 m; tatsächliche Abweichung kann größer sein).")
            if est < peak["elevation"] - 250:
                st.success("Indizien sprechen eher dafür, dass der Gipfel über einer tiefen Nebel-/Stratusschicht liegen könnte.")
            elif est > peak["elevation"] + 250:
                st.info("Indizien sprechen eher gegen einen Gipfel oberhalb der geschätzten Schicht.")
            else:
                st.warning("Grenzbereich: Schon kleine Modellfehler können die Einschätzung umkehren.")
        else:
            st.info("Keine ausreichend starken Nebelindikatoren – eine Nebeloberkante wird nicht geschätzt.")

st.divider()
st.subheader("24-Stunden-Verlauf")
chart = go.Figure()
for name in PEAKS:
    d = window[window["peak"] == name]
    if d.empty:
        continue
    chart.add_trace(go.Scatter(
        x=d["time"], y=d["fog_top_estimate_m"], mode="lines+markers",
        name=f"{name}: geschätzte Nebeloberkante",
        connectgaps=False,
        hovertemplate="%{x|%a %H:%M}<br>Heuristische Höhe: %{y:.0f} m<extra></extra>",
    ))
chart.add_hline(y=PEAKS["Großer Waldstein"]["elevation"], line_dash="dash",
                annotation_text="Waldstein 877 m", annotation_position="top left")
chart.add_hline(y=PEAKS["Kösseine"]["elevation"], line_dash="dot",
                annotation_text="Kösseine 939 m", annotation_position="bottom right")
chart.update_layout(
    xaxis_title="Ortszeit (Europe/Berlin)", yaxis_title="Höhe über NHN (m)",
    hovermode="x unified", legend_title="Kurven", height=470,
    margin=dict(l=10, r=10, t=25, b=10),
)
st.plotly_chart(chart, use_container_width=True)

st.subheader("Stündliche Modelldaten")
show = window[[
    "time", "peak", "temperature_2m", "relative_humidity_2m",
    "cloud_cover", "cloud_cover_low", "visibility_km",
    "boundary_layer_height", "fog_top_estimate_m",
]].copy()
show = show.rename(columns={
    "time": "Zeit", "peak": "Gipfel", "temperature_2m": "Temp. °C",
    "relative_humidity_2m": "Feuchte %", "cloud_cover": "Bewölkung %",
    "cloud_cover_low": "Tiefe Wolken %", "visibility_km": "Sichtweite km",
    "boundary_layer_height": "Grenzschichthöhe m", "fog_top_estimate_m": "Heuristik: Oberkante m",
})
st.dataframe(show, use_container_width=True, hide_index=True)

with st.expander("Wie ist die Schätzung zu verstehen?"):
    st.markdown("""
- **Nebelindikatoren:** relative Feuchte mindestens 92 %, Temperatur-Taupunkt-Abstand höchstens 1,8 °C,
  viel tiefe/gesamte Bewölkung und Wind bis 22 km/h.
- **Höhenheuristik:** Gipfelhöhe plus 35 % der modellierten Grenzschichthöhe; als grober Bereich werden ±250 m angezeigt.
- **Wichtige Grenze:** Die atmosphärische Grenzschichthöhe ist nicht die Nebeloberkante. Die Formel ist ein bewusst grober Prototyp, keine validierte meteorologische Methode.
- **Kein Schätzwert** bedeutet, dass die Kriterien nicht erfüllt wurden – nicht, dass garantiert kein Nebel vorhanden ist.
- Für eine belastbarere Version sollten wir Modellprofile/Vertikalprofile und lokale Webcams oder Beobachtungen einbeziehen und die Trefferquote gegen vergangene Tage prüfen.
""")
st.caption("Wetterdaten: Open-Meteo Forecast API. Bitte die Nutzungsbedingungen und Attribution der Datenquelle beachten.")
