import math
from datetime import datetime,date,timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="Wolkenmeer & Fotografie",page_icon="📷",layout="wide")
TZ=ZoneInfo("Europe/Berlin")
SITES={"Großer Waldstein":{"lat":50.117,"lon":11.858,"elev":877},"Kösseine":{"lat":50.012,"lon":11.982,"elev":939},"Kirchenlamitz":{"lat":50.151,"lon":11.946,"elev":590}}
st.title("📷 Wolkenmeer & Astro-Fotografie")
st.markdown("### Wetter- und Himmelsplanung auf einen Blick")
st.caption("Großer Waldstein · Kösseine · Kirchenlamitz | Nebel · Sonnenlicht · Milchstraße · Polarlicht")
st.warning("Die Nebel-% ist eine modellbasierte Schätzung aus Wetterindikatoren, keine vor Ort kalibrierte Trefferwahrscheinlichkeit. Sie beschreibt nebelbegünstigte Bedingungen, nicht garantiert ein Wolkenmeer oder die genaue Nebeloberkante.")
with st.sidebar:
    sites=st.multiselect("Standorte",list(SITES),default=list(SITES))
    hours=st.selectbox("Zeitraum",["24 Stunden","48 Stunden","72 Stunden"])
    hours={"24 Stunden":24,"48 Stunden":48,"72 Stunden":72}[hours]

@st.cache_data(ttl=900)
def weather(lat,lon,elev,hours):
    p={"latitude":lat,"longitude":lon,"elevation":elev,"timezone":"Europe/Berlin","forecast_days":3,
    "hourly":"temperature_2m,relative_humidity_2m,dew_point_2m,cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,visibility,wind_speed_10m,wind_gusts_10m,precipitation_probability,pressure_msl,boundary_layer_height,is_day",
    "daily":"sunrise,sunset,sunshine_duration,daylight_duration,uv_index_max","wind_speed_unit":"kmh"}
    d=requests.get("https://api.open-meteo.com/v1/forecast",params=p,timeout=20);d.raise_for_status();j=d.json()
    h=pd.DataFrame(j["hourly"]).head(hours);h["time"]=pd.to_datetime(h["time"]);h["taupunktabstand"]=h.temperature_2m-h.dew_point_2m
    return h,pd.DataFrame(j["daily"])

def fog(r):
    vals=[r.get("taupunktabstand"),r.get("relative_humidity_2m"),r.get("cloud_cover_low"),r.get("cloud_cover"),r.get("wind_speed_10m")]
    if any(pd.isna(x) for x in vals): return pd.Series([None,"Daten fehlen"])
    spread,rh,low,total,wind=vals
    s=(30 if spread<=1.5 else 20 if spread<=3 else 8 if spread<=5 else 0)
    s+=(25 if rh>=95 else 18 if rh>=90 else 8 if rh>=85 else 0)
    s+=(20 if low>=70 else 12 if low>=45 else 0)
    s+=(10 if wind<=12 else 5 if wind<=20 else 0)
    s+=(10 if total>=70 else 4 if total>=45 else 0)
    return pd.Series([min(100,s),"Hoch" if s>=70 else "Mittel" if s>=48 else "Gering"])

def sunrise_sunset(lat,lon,day):
    def calc(rise):
        n=day.timetuple().tm_yday; lng=lon/15
        t=n+((6-lng)/24 if rise else (18-lng)/24); M=.9856*t-3.289
        L=(M+1.916*math.sin(math.radians(M))+.020*math.sin(math.radians(2*M))+282.634)%360
        ra=math.degrees(math.atan(.91764*math.tan(math.radians(L))))%360
        ra+=math.floor(L/90)*90-math.floor(ra/90)*90;ra/=15
        sd=.39782*math.sin(math.radians(L));cd=math.cos(math.asin(sd))
        ch=(math.cos(math.radians(90.833))-sd*math.sin(math.radians(50)))/(cd*math.cos(math.radians(50)))
        if abs(ch)>1:return None
        H=(360-math.degrees(math.acos(ch)) if rise else math.degrees(math.acos(ch)))/15
        ut=(H+ra-.06571*t-6.622-lng)%24
        return (datetime.combine(day,datetime.min.time(),tzinfo=ZoneInfo("UTC"))+timedelta(hours=ut)).astimezone(TZ)
    return calc(True),calc(False)

@st.cache_data(ttl=300)
def kp_data():
    for url in ["https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json","https://services.swpc.noaa.gov/products/planetary-k-index.json"]:
        try:
            j=requests.get(url,timeout=8);j.raise_for_status(); rows=j.json()
            df=pd.DataFrame(rows[1:],columns=rows[0]); col=next((x for x in df if "kp" in x.lower()),None)
            if col:
                df["Kp"]=pd.to_numeric(df[col],errors="coerce")
                return df.dropna(subset=["Kp"]).tail(12)
        except Exception: pass
    return pd.DataFrame()

if not sites: st.info("Bitte Standort auswählen.");st.stop()
for name in sites:
    loc=SITES[name]
    st.divider(); st.header(f"📍 {name}")
    try: h,daily=weather(loc["lat"],loc["lon"],loc["elev"],hours)
    except Exception as e: st.error(f"Wetterdaten nicht abrufbar: {e}");continue
    h[["Nebelwahrscheinlichkeit (Schätzwert %) ","Nebel-Einschätzung"]]=h.apply(fog,axis=1)
    sr,ss=sunrise_sunset(loc["lat"],loc["lon"],date.today())
    c=st.columns(4);c[0].metric("Gipfelhöhe",f'{loc["elev"]} m');c[1].metric("Sonnenaufgang ca.",sr.strftime("%H:%M") if sr else "—");c[2].metric("Sonnenuntergang ca.",ss.strftime("%H:%M") if ss else "—");c[3].metric("Taupunktabstand aktuell",f'{h.iloc[0]["taupunktabstand"]:.1f} °C')
    best=h.dropna(subset=["Nebelwahrscheinlichkeit (Schätzwert %) "]).sort_values("Nebelwahrscheinlichkeit (Schätzwert %) ",ascending=False).head(1)
    if len(best):
        r=best.iloc[0];st.info(f'**Höchster Nebel-Schätzwert:** {r["Nebelwahrscheinlichkeit (Schätzwert %) "]:.0f}% ({r["Nebel-Einschätzung"]}) um {r["time"].strftime("%a %H:%M")}. Berechnet aus Taupunktabstand, Feuchte, tiefer und gesamter Bewölkung sowie Wind.' )
    st.caption("Interpretation: Ein kleiner Temperatur-Taupunkt-Abstand zeigt feuchte, fast gesättigte Luft. Zusammen mit tiefer Bewölkung kann Nebel wahrscheinlicher sein. Für ein Wolkenmeer muss die Wolkenschicht unter dem Gipfel liegen – das kann diese einfache Rechnung nicht sicher erkennen.")
    st.plotly_chart(px.line(h,x="time",y=["temperature_2m","dew_point_2m"],title="Temperatur und Taupunkt",labels={"time":"Ortszeit","value":"°C","variable":"Kurve"}),use_container_width=True)
    st.plotly_chart(px.line(h,x="time",y=["Nebelwahrscheinlichkeit (Schätzwert %) ","cloud_cover","cloud_cover_low"],title="Geschätzte Nebelwahrscheinlichkeit und Bewölkung",labels={"time":"Ortszeit","value":"Score / %","variable":"Messgröße"}),use_container_width=True)
    view=h[["time","temperature_2m","dew_point_2m","taupunktabstand","relative_humidity_2m","cloud_cover","cloud_cover_low","cloud_cover_mid","cloud_cover_high","visibility","wind_speed_10m","wind_gusts_10m","boundary_layer_height","precipitation_probability","Nebelwahrscheinlichkeit (Schätzwert %) ","Nebel-Einschätzung"]].rename(columns={"time":"Zeit","temperature_2m":"Temperatur °C","dew_point_2m":"Taupunkt °C","taupunktabstand":"Temp.-Taupunkt °C","relative_humidity_2m":"Feuchte %","cloud_cover":"Bewölkung %","cloud_cover_low":"Tiefe Wolken %","cloud_cover_mid":"Mittlere Wolken %","cloud_cover_high":"Hohe Wolken %","visibility":"Sichtweite m","wind_speed_10m":"Wind km/h","wind_gusts_10m":"Böen km/h","boundary_layer_height":"Grenzschichthöhe m","precipitation_probability":"Niederschlagschance %"})
    st.subheader("Stündliche Fotografie-Daten")
    st.dataframe(view,use_container_width=True,hide_index=True)
    st.subheader("Milchstraße / Nachtfotografie")
    night=h[h["is_day"]==0]
    if len(night):
        clear=(night["cloud_cover"]<=25).mean()*100
        st.metric("Nachtstunden mit höchstens 25 % Wolken",f"{clear:.0f}%")
    st.caption("Für Milchstraßenfotos zusätzlich Mondphase/-stand, astronomische Dunkelheit und Lichtverschmutzung prüfen. Diese Version berechnet noch keine exakte Sichtbarkeit des galaktischen Zentrums.")
    st.subheader("Tägliche Sonnen- und Lichtdaten");st.dataframe(daily,use_container_width=True,hide_index=True)

st.divider(); st.header("🌌 Polarlicht-Monitor für Kirchenlamitz / Fichtelgebirge")
kp=kp_data()
if kp.empty: st.warning("NOAA-Kp-Daten momentan nicht erreichbar.")
else:
    last=kp.iloc[-1];a,b=st.columns(2);a.metric("Letzter Kp-Wert",f'{last["Kp"]:.1f}');b.metric("Einordnung","Geomagnetischer Sturm möglich" if last["Kp"]>=5 else "In Nordbayern meist geringe Chance")
    st.dataframe(kp,use_container_width=True,hide_index=True)
st.caption("Polarlicht-Chance in % wäre ohne lokale Sichtungsdaten, Echtzeit-Sonnenwind und Wolken-/Horizontmodell irreführend. Der Kp-Wert ist deshalb ein Aktivitätsindikator, kein lokaler Prozentwert. Für Kirchenlamitz: Wolkenlücken, Dunkelheit und freier Nordhorizont prüfen.")
