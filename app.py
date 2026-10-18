import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

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
def get_weather(lat, lon, elev):
    params={"latitude":lat,"longitude":lon,"elevation":elev,
    "hourly":"temperature_2m,dew_point_2m,relative_humidity_2m,cloud_cover,cloud_cover_low,wind_speed_10m,precipitation_probability",
    "daily":"sunrise,sunset","forecast_days":3,"timezone":TZ,"wind_speed_unit":"kmh"}
    r=requests.get("https://api.open-meteo.com/v1/forecast",params=params,timeout=20)
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

st.markdown('<div class="eyebrow">FICHTELGEBIRGE · FOTOWETTER</div>',unsafe_allow_html=True)
st.title("Wolkenmeer")
st.markdown("**Weniger Zahlen. Mehr Klarheit für deine Fototour.**")
st.caption("Wetterdaten von Open-Meteo · automatisch aktualisiert etwa alle 15 Minuten")

with st.container(border=True):
    site=st.selectbox("Standort",list(SITES.keys()))
    period=st.radio("Vorhersage",["24 Stunden","48 Stunden"],horizontal=True)
cfg=SITES[site]
st.caption(f"{cfg['kind']} · {cfg['elev']} m ü. NHN")

try:
    with st.spinner("Wetterdaten werden geladen …"):
        data=get_weather(cfg["lat"],cfg["lon"],cfg["elev"])
except Exception as e:
    st.error("Wetterdaten sind momentan nicht erreichbar. Bitte später erneut versuchen.")
    st.stop()

h=pd.DataFrame(data["hourly"])
h["time"]=pd.to_datetime(h["time"])
h["spread"]=h["temperature_2m"]-h["dew_point_2m"]
h["score"]=h.apply(score,axis=1)
now=pd.Timestamp.now(tz=TZ).tz_localize(None).floor("h")
f=h[h["time"]>=now].head(48 if period=="48 Stunden" else 24).copy()
if f.empty: f=h.head(24).copy()
best=f.sort_values("score",ascending=False).iloc[0]
s=int(best["score"]); status,emoji=label(s)
besttime=best["time"].strftime("%a, %H:%M")
st.markdown(f'<div class="hero"><div class="eyebrow">DEINE FOTOCHANCE</div><h2>{emoji} {status}</h2><p>Beste modellierte Stunde: <b>{besttime} Uhr</b></p></div>',unsafe_allow_html=True)

a,b,c=st.columns(3)
a.metric("Nebel-Index",f"{s}/100")
b.metric("Temperatur",f"{best['temperature_2m']:.1f} °C")
c.metric("Taupunktabstand",f"{best['spread']:.1f} °C")
with st.expander("Wie ist der Nebel-Index gemeint?"):
    st.write("Der Index ist eine vereinfachte Heuristik aus Taupunktabstand, Luftfeuchte, tiefer Bewölkung und Wind. Er ist keine statistisch kalibrierte Wahrscheinlichkeit. Ein echtes Wolkenmeer hängt zusätzlich von Temperaturinversion und Wolkenhöhe ab.")

st.subheader("Die nächsten Stunden")
fig=go.Figure()
fig.add_trace(go.Scatter(x=f["time"],y=f["score"],mode="lines+markers",line=dict(color="#6E8668",width=3,shape="spline"),marker=dict(size=4,color="#28483A"),fill="tozeroy",fillcolor="rgba(110,134,104,.15)",hovertemplate="%{x|%a %H:%M}<br>Index %{y}/100<extra></extra>"))
fig.add_hrect(y0=75,y1=100,fillcolor="rgba(91,145,102,.10)",line_width=0)
fig.add_hrect(y0=50,y1=75,fillcolor="rgba(215,168,91,.10)",line_width=0)
fig.update_layout(height=250,margin=dict(l=0,r=5,t=8,b=0),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="DM Sans",color="#738076",size=11),xaxis=dict(showgrid=False,tickformat="%Hh"),yaxis=dict(range=[0,100],gridcolor="#e5e7dd",title="Index / 100"),showlegend=False)
st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

st.subheader("Beste Zeitfenster")
top=f.sort_values("score",ascending=False).head(4).sort_values("time")
for _,r in top.iterrows():
    lab,em=label(int(r["score"]))
    st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;background:#fffdf7;border:1px solid #e5e7dd;border-radius:14px;padding:12px 14px;margin:7px 0"><div><b style="color:#28483A">{em} {r['time'].strftime('%a · %H:%M')}</b><div style="font-size:.8rem;color:#738076">{lab} · {r['temperature_2m']:.1f} °C · Wind {r['wind_speed_10m']:.0f} km/h</div></div><b style="font-size:1.1rem;color:#28483A">{int(r['score'])}<span style="font-size:.7rem;color:#738076">/100</span></b></div>""",unsafe_allow_html=True)

x,y=st.columns(2)
with x:
    fig1=go.Figure(go.Scatter(x=f["time"],y=f["spread"],mode="lines",line=dict(color="#B58A50",width=3),fill="tozeroy",fillcolor="rgba(181,138,80,.12)"))
    fig1.update_layout(title="Taupunktabstand",height=220,margin=dict(l=0,r=0,t=35,b=0),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(color="#738076",size=10),xaxis=dict(showgrid=False,tickformat="%Hh"),yaxis=dict(gridcolor="#e5e7dd",title="°C"))
    st.plotly_chart(fig1,use_container_width=True,config={"displayModeBar":False})
with y:
    fig2=go.Figure(go.Scatter(x=f["time"],y=f["cloud_cover_low"],mode="lines",line=dict(color="#6E8668",width=3),fill="tozeroy",fillcolor="rgba(110,134,104,.12)"))
    fig2.update_layout(title="Tiefe Bewölkung",height=220,margin=dict(l=0,r=0,t=35,b=0),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(color="#738076",size=10),xaxis=dict(showgrid=False,tickformat="%Hh"),yaxis=dict(gridcolor="#e5e7dd",title="%",range=[0,100]))
    st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})

st.subheader("Sonnenlicht heute")
daily=pd.DataFrame(data["daily"])
st.metric("Sonnenaufgang",pd.to_datetime(daily.iloc[0]["sunrise"]).strftime("%H:%M"))
st.metric("Sonnenuntergang",pd.to_datetime(daily.iloc[0]["sunset"]).strftime("%H:%M"))

with st.expander("Stündliche Wetterdetails"):
    view=f[["time","temperature_2m","dew_point_2m","relative_humidity_2m","cloud_cover","cloud_cover_low","wind_speed_10m","precipitation_probability","score"]].copy()
    view.columns=["Zeit","Temp °C","Taupunkt °C","Luftfeuchte %","Bewölkung %","Tiefe Wolken %","Wind km/h","Regenrisiko %","Nebel-Index"]
    view["Zeit"]=view["Zeit"].dt.strftime("%a %H:%M")
    st.dataframe(view,use_container_width=True,hide_index=True)
    st.download_button("CSV herunterladen",view.to_csv(index=False).encode("utf-8-sig"),file_name="wolkenmeer-prognose.csv",mime="text/csv",use_container_width=True)

st.subheader("Deine drei Standorte")
for name,sitecfg in SITES.items():
    st.markdown(f'<div style="display:flex;justify-content:space-between;background:{"#E7EEE2" if name==site else "#fffdf7"};border:1px solid #e5e7dd;border-radius:12px;padding:12px 14px;margin:6px 0"><b style="color:#28483A">{name}</b><span style="color:#738076">{sitecfg["elev"]} m · {sitecfg["kind"]}</span></div>',unsafe_allow_html=True)
st.markdown("---")
st.caption("Wichtig: Der Nebel-Index ist ein grober Modellindikator, keine Prozentwahrscheinlichkeit und keine Garantie für ein Wolkenmeer. Quelle: Open-Meteo Forecast API.")
