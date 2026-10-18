import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Wolkenmeer · Fichtelgebirge", page_icon="🌫️", layout="centered")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;600;700;800&display=swap');
:root{--forest:#28483A;--moss:#6E8668;--cream:#F6F4EC;--ink:#26352D;--muted:#738076}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.stApp{background:var(--cream);color:var(--ink)}
.block-container{max-width:760px;padding-top:1.2rem;padding-bottom:3rem}
h1,h2,h3{font-family:'Manrope',sans-serif!important;color:var(--forest);letter-spacing:-.03em}
h1{font-size:2rem!important}
[data-testid="stMetric"]{background:#fffdf7;border:1px solid #e5e7dd;border-radius:16px;padding:12px}
[data-testid="stMetricLabel"]{color:#738076!important;font-size:.78rem!important}
[data-testid="stMetricValue"]{color:#28483A!important;font-size:1.3rem!important}
.stButton>button{border-radius:12px;background:#fffdf7;color:#28483A;border:1px solid #d4ddcf;font-weight:600}
.eyebrow{color:#71806e;font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase}
.hero{background:linear-gradient(135deg,#294b3b,#54765a);color:#fffdf7;border-radius:22px;padding:22px;margin:.4rem 0 1rem}
.hero .eyebrow{color:#d1dfcf}.hero h2{color:#fffdf7!important;margin:.4rem 0!important}.hero p{color:#e4ebe0}
</style>
""", unsafe_allow_html=True)

SITES = {
    "Großer Waldstein": {"lat":50.117,"lon":11.858,"elev":877,"kind":"Gipfel"},
    "Kösseine": {"lat":50.012,"lon":11.982,"elev":939,"kind":"Gipfel"},
    "Kirchenlamitz": {"lat":50.151,"lon":11.946,"elev":590,"kind":"Ort"},
}
TZ="Europe/Berlin"

@st.cache_data(ttl=900)
def get_open_meteo(lat, lon, elev):
    params={"latitude":lat,"longitude":lon,"elevation":elev,
    "hourly":"temperature_2m,dew_point_2m,relative_humidity_2m,cloud_cover,cloud_cover_low,wind_speed_10m,precipitation_probability",
    "daily":"sunrise,sunset","forecast_days":3,"timezone":TZ,"wind_speed_unit":"kmh"}
    r=requests.get("https://api.open-meteo.com/v1/forecast",params=params,timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=900)
def get_metno(lat, lon, elev):
    # Yr / MET Norway Locationforecast, separate forecast provider
    url=f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}&altitude={elev}"
    headers={"User-Agent":"WolkenmeerFotografie/2.0 contact=forecast-dashboard"}
    r=requests.get(url,headers=headers,timeout=20)
    r.raise_for_status()
    return r.json()

def score(r):
    spread=r["temperature_2m"]-r["dew_point_2m"]
    s=0
    s += 36 if spread<=1.5 else 27 if spread<=3 else 15 if spread<=5 else 6 if spread<=7 else 0
    rh=r["relative_humidity_2m"]
    s += 24 if rh>=95 else 19 if rh>=90 else 11 if rh>=85 else 5 if rh>=80 else 0
    low=r["cloud_cover_low"]
    s += 17 if 20<=low<=85 else 10 if low>85 else 8 if low>=10 else 0
    wind=r["wind_speed_10m"]
    s += 15 if wind<=8 else 10 if wind<=15 else 4 if wind<=22 else 0
    if r["cloud_cover"]>=95: s-=8
    return max(0,min(100,int(s)))

def label(s):
    return ("Gute Bedingungen","🟢") if s>=75 else ("Möglich","🟡") if s>=50 else ("Eher ungünstig","⚪")

def metno_frame(payload):
    rows=[]
    for item in payload["properties"]["timeseries"]:
        t=pd.to_datetime(item["time"]).tz_convert(TZ).tz_localize(None)
        d=item["data"]
        instant=d.get("instant",{}).get("details",{})
        next1=d.get("next_1_hours",{}).get("details",{})
        # MET Norway does not always provide low-cloud fraction, so cloud total is used as a cautious proxy.
        rows.append({
            "time":t,
            "temperature_2m":instant.get("air_temperature"),
            "dew_point_2m":instant.get("dew_point_temperature"),
            "relative_humidity_2m":instant.get("relative_humidity"),
            "cloud_cover":instant.get("cloud_area_fraction"),
            "cloud_cover_low":instant.get("cloud_area_fraction_low",instant.get("cloud_area_fraction")),
            "wind_speed_10m":instant.get("wind_speed"),
            "precipitation_probability":next1.get("probability_of_precipitation"),
        })
    df=pd.DataFrame(rows)
    for c in ["temperature_2m","dew_point_2m","relative_humidity_2m","cloud_cover","cloud_cover_low","wind_speed_10m","precipitation_probability"]:
        if c not in df: df[c]=float("nan")
    return df

st.markdown('<div class="eyebrow">FICHTELGEBIRGE · FOTOWETTER</div>',unsafe_allow_html=True)
st.title("Wolkenmeer")
st.markdown("**Nur dann losfahren, wenn Nebel und Licht zusammenpassen.**")
st.caption("Mehrere Wettermodelle · naturfarbenes, handyfreundliches Dashboard")

with st.container(border=True):
    site=st.selectbox("Standort",list(SITES.keys()))
    period=st.radio("Vorhersage",["24 Stunden","48 Stunden"],horizontal=True)
cfg=SITES[site]
st.caption(f"{cfg['kind']} · {cfg['elev']} m ü. NHN")

with st.spinner("Wettermodelle werden abgefragt …"):
    frames={}
    errors={}
    try:
        j=get_open_meteo(cfg["lat"],cfg["lon"],cfg["elev"])
        a=pd.DataFrame(j["hourly"])
        a["time"]=pd.to_datetime(a["time"])
        frames["Open-Meteo"]=a
        daily=pd.DataFrame(j["daily"])
    except Exception as e:
        errors["Open-Meteo"]=type(e).__name__
        daily=None
    try:
        j2=get_metno(cfg["lat"],cfg["lon"],cfg["elev"])
        frames["MET Norway / Yr"]=metno_frame(j2)
    except Exception as e:
        errors["MET Norway / Yr"]=type(e).__name__

if not frames:
    st.error("Die Wetteranbieter sind momentan nicht erreichbar. Bitte später erneut versuchen.")
    st.stop()

# Use Open-Meteo hourly times as the base grid; align other providers by nearest hour.
primary=next(iter(frames.values())).copy()
now=pd.Timestamp.now(tz=TZ).tz_localize(None).floor("h")
forecast=primary[primary["time"]>=now].head(48 if period=="48 Stunden" else 24).copy()
if forecast.empty: forecast=primary.head(24).copy()

# Compute provider-specific indices, then average available indices per hour.
provider_scores=[]
for provider,df in frames.items():
    df=df.copy()
    df["time"]=pd.to_datetime(df["time"]).dt.floor("h")
    df["spread"]=df["temperature_2m"]-df["dew_point_2m"]
    df["score"]=df.apply(lambda r: score(r) if pd.notna(r.get("temperature_2m")) and pd.notna(r.get("dew_point_2m")) and pd.notna(r.get("relative_humidity_2m")) and pd.notna(r.get("cloud_cover_low")) and pd.notna(r.get("wind_speed_10m")) and pd.notna(r.get("cloud_cover")) else float("nan"),axis=1)
    provider_scores.append((provider,df[["time","score","temperature_2m","dew_point_2m","relative_humidity_2m","cloud_cover","cloud_cover_low","wind_speed_10m","precipitation_probability"]]))
forecast["time"]=pd.to_datetime(forecast["time"]).dt.floor("h")
aligned=[]
for provider,df in provider_scores:
    tmp=forecast[["time"]].merge(df,on="time",how="left")
    tmp=tmp.rename(columns={c:f"{c}__{provider}" for c in tmp.columns if c!="time"})
    aligned.append(tmp)
for tmp in aligned:
    forecast=forecast.merge(tmp,on="time",how="left",suffixes=("","_dup"))
score_cols=[]
for provider,_ in provider_scores:
    col=f"score__{provider}"
    if col in forecast.columns: score_cols.append(col)
if not score_cols:
    forecast["avg_score"]=forecast.apply(score,axis=1)
else:
    forecast["avg_score"]=forecast[score_cols].mean(axis=1)
    # Single provider fallback when only one model supplied complete values.
    forecast["avg_score"]=forecast["avg_score"].fillna(forecast.apply(score,axis=1))
forecast["avg_score"]=forecast["avg_score"].round().clip(0,100)
forecast["spread"]=forecast["temperature_2m"]-forecast["dew_point_2m"]

# Astronomical practical window: only rank daylight-edge periods from 60 min before sunrise to 120 min after,
# plus 120 min before sunset to sunset. Sunrise/sunset from Open-Meteo daily forecast.
if daily is not None and not daily.empty:
    daily["date"]=pd.to_datetime(daily["time"]).dt.date
    daily["sunrise_dt"]=pd.to_datetime(daily["sunrise"])
    daily["sunset_dt"]=pd.to_datetime(daily["sunset"])
    eligible=pd.Series(False,index=forecast.index)
    for _,day in daily.iterrows():
        sr=day["sunrise_dt"]; ss=day["sunset_dt"]
        eligible |= ((forecast["time"]>=sr-pd.Timedelta(minutes=60)) & (forecast["time"]<=sr+pd.Timedelta(minutes=150)))
        eligible |= ((forecast["time"]>=ss-pd.Timedelta(minutes=150)) & (forecast["time"]<=ss+pd.Timedelta(minutes=15)))
    forecast["photo_window"]=eligible
else:
    forecast["photo_window"]=forecast["time"].dt.hour.between(5,9) | forecast["time"].dt.hour.between(16,21)

photo=forecast[forecast["photo_window"]]
if photo.empty: photo=forecast
best=photo.sort_values("avg_score",ascending=False).iloc[0]
s=int(best["avg_score"]); status,emoji=label(s)
besttime=best["time"].strftime("%a, %H:%M")

st.markdown(f'<div class="hero"><div class="eyebrow">NEBEL + FOTOLICHT</div><h2>{emoji} {status}</h2><p>Bestes Zeitfenster mit Tagesrandlicht: <b>{besttime} Uhr</b></p></div>',unsafe_allow_html=True)
m1,m2,m3=st.columns(3)
m1.metric("Modell-Mittel",f"{s}/100")
m2.metric("Temperatur",f"{best['temperature_2m']:.1f} °C" if pd.notna(best["temperature_2m"]) else "—")
m3.metric("Taupunktabstand",f"{best['spread']:.1f} °C" if pd.notna(best["spread"]) else "—")

with st.expander("Wie wird das Mittel gebildet?"):
    st.write("Für jeden Anbieter wird ein vereinfachter Nebel-Index aus Taupunktabstand, Luftfeuchte, tiefer Bewölkung und Wind berechnet. Danach wird der Mittelwert der verfügbaren Anbieter-Indizes pro Stunde angezeigt. Das ist ein Modell-Konsens, keine statistisch kalibrierte Nebelwahrscheinlichkeit. Open-Meteo und MET Norway/Yr sind die derzeit eingebundenen Quellen; fehlende Modellstunden werden nicht künstlich ergänzt.")
with st.expander("Anbieterstatus"):
    for name in frames: st.write(f"✅ {name}: Daten geladen")
    for name,err in errors.items(): st.write(f"⚠️ {name}: momentan nicht verfügbar ({err})")

st.subheader("Nebel-Chance während des Fotolichts")
fig=go.Figure()
fig.add_trace(go.Scatter(x=forecast["time"],y=forecast["avg_score"],mode="lines+markers",line=dict(color="#6E8668",width=3,shape="spline"),marker=dict(size=4,color="#28483A"),fill="tozeroy",fillcolor="rgba(110,134,104,.15)",hovertemplate="%{x|%a %H:%M}<br>Modell-Mittel %{y}/100<extra></extra>"))
# Shade practical sunrise/sunset windows.
for _,r in forecast[forecast["photo_window"]].iterrows():
    fig.add_vrect(x0=r["time"],x1=r["time"]+pd.Timedelta(hours=1),fillcolor="rgba(215,168,91,.10)",line_width=0)
fig.update_layout(height=250,margin=dict(l=0,r=5,t=8,b=0),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="DM Sans",color="#738076",size=11),xaxis=dict(showgrid=False,tickformat="%Hh"),yaxis=dict(range=[0,100],gridcolor="#e5e7dd",title="Index / 100"),showlegend=False)
st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
st.caption("Gold hinterlegte Zeitabschnitte markieren grob Sonnenaufgangs-/Sonnenuntergangsfenster. Die lokale Horizontlinie kann das tatsächliche Licht verschieben.")

st.subheader("Beste Fotofenster")
top=photo.sort_values("avg_score",ascending=False).head(5).sort_values("time")
for _,r in top.iterrows():
    lab,em=label(int(r["avg_score"]))
    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;background:#fffdf7;border:1px solid #e5e7dd;border-radius:14px;padding:12px 14px;margin:7px 0"><div><b style="color:#28483A">{em} {r["time"].strftime("%a · %H:%M")}</b><div style="font-size:.8rem;color:#738076">{lab} · {r["temperature_2m"]:.1f} °C · Wind {r["wind_speed_10m"]:.0f} km/h</div></div><b style="font-size:1.1rem;color:#28483A">{int(r["avg_score"])}<span style="font-size:.7rem;color:#738076">/100</span></b></div>',unsafe_allow_html=True)

st.subheader("Nebel-Obergrenze")
st.write("Mit normalen Wettervorhersagen lässt sich eine echte Obergrenze der Nebelschicht nicht zuverlässig bestimmen. Als praktische Hilfe zeigt die App daher stattdessen einen **konservativen Deckel** für den angezeigten Index.")
cap=st.slider("Maximal angezeigter Nebel-Index",min_value=20,max_value=100,value=80,step=5,help="Begrenzt nur den angezeigten Index, nicht die Wetterdaten. Kein physikalischer Grenzwert für Wolkenhöhe.")
forecast["capped_score"]=forecast["avg_score"].clip(upper=cap)
st.caption(f"Der angezeigte Wert wird auf höchstens {cap}/100 begrenzt. Der ungekappte Modell-Mittelwert bleibt in der Detailtabelle sichtbar.")
figcap=go.Figure(go.Scatter(x=forecast["time"],y=forecast["capped_score"],mode="lines+markers",line=dict(color="#B58A50",width=3),fill="tozeroy",fillcolor="rgba(181,138,80,.12)",hovertemplate="%{x|%a %H:%M}<br>Begrenzter Index %{y}/100<extra></extra>"))
figcap.update_layout(height=220,margin=dict(l=0,r=0,t=8,b=0),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="DM Sans",color="#738076",size=11),xaxis=dict(showgrid=False,tickformat="%Hh"),yaxis=dict(range=[0,100],gridcolor="#e5e7dd",title="Index / 100"),showlegend=False)
st.plotly_chart(figcap,use_container_width=True,config={"displayModeBar":False})

st.subheader("Standort")
for name,sc in SITES.items():
    st.markdown(f'<div style="display:flex;justify-content:space-between;background:{"#E7EEE2" if name==site else "#fffdf7"};border:1px solid #e5e7dd;border-radius:12px;padding:12px 14px;margin:6px 0"><b style="color:#28483A">{name}</b><span style="color:#738076">{sc["elev"]} m · {sc["kind"]}</span></div>',unsafe_allow_html=True)

with st.expander("Stündliche Wetterdetails & CSV"):
    view=forecast[["time","avg_score","capped_score","temperature_2m","dew_point_2m","relative_humidity_2m","cloud_cover","cloud_cover_low","wind_speed_10m","precipitation_probability"]].copy()
    view.columns=["Zeit","Modell-Mittel","Begrenzter Index","Temp °C","Taupunkt °C","Luftfeuchte %","Bewölkung %","Tiefe Wolken %","Wind km/h","Regenrisiko %"]
    view["Zeit"]=view["Zeit"].dt.strftime("%a %H:%M")
    st.dataframe(view,use_container_width=True,hide_index=True)
    st.download_button("CSV herunterladen",view.to_csv(index=False).encode("utf-8-sig"),file_name="wolkenmeer-multi-modell.csv",mime="text/csv",use_container_width=True)

st.markdown("---")
st.caption("Hinweis: Der Index ist ein grober Modell-Konsens, keine Prozentwahrscheinlichkeit. Für ein echtes Wolkenmeer sind Inversionshöhe, Wolkenuntergrenze und lokales Relief entscheidend. Datenquellen: Open-Meteo und MET Norway/Yr.")
