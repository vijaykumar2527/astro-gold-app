import streamlit as st
import datetime
import swisseph as swe
import pandas as pd
import math

st.set_page_config(page_title="ASTRO GOLD - HOROSCOPE", layout="wide")

# --- कस्टम सीएसएस (नक्षत्र गोल्ड जैसा हुबहू लुक) ---
st.markdown("""
<style>
    .main-title {
        color: #8B2500;
        font-weight: 800;
        font-size: 26px;
        letter-spacing: 1px;
        margin-bottom: 15px;
    }
    .card-box {
        border: 1px solid #d3d9de;
        border-radius: 6px;
        padding: 10px 14px;
        background-color: #f7f9fa;
        margin-bottom: 12px;
        font-size: 13px;
    }
    .card-header {
        font-weight: bold;
        color: #1a4d80;
        border-bottom: 1px solid #e1e4e8;
        padding-bottom: 4px;
        margin-bottom: 6px;
        text-transform: uppercase;
        font-size: 13px;
    }
    .dataframe {
        font-size: 12px !important;
    }
    div[data-testid="stHorizontalBlock"] {
        align-items: flex-start;
    }
</style>
""", unsafe_allow_html=True)

# सॉफ्टवेयर का नाम (आप इसे जब चाहें बदल सकते हैं)
APP_TITLE = "ASTRO GOLD - HOROSCOPE"
st.markdown(f'<div class="main-title">{APP_TITLE}</div>', unsafe_allow_html=True)

# --- ज्योतिषीय डेटा कॉन्फिगरेशन ---
SIGN_NAMES_SHORT = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
SIGN_LORDS = ["Ma", "Ve", "Me", "Mo", "Su", "Me", "Ve", "Ma", "Ju", "Sa", "Sa", "Ju"]

NAK_LORDS = [
    "Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me",
    "Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me",
    "Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"
]

DASHA_YEARS = {
    "Ke": 7, "Ve": 20, "Su": 6, "Mo": 10, "Ma": 7,
    "Ra": 18, "Ju": 16, "Sa": 19, "Me": 17
}
PLANET_ORDER = ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"]

WEEKDAYS = ["Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Su"]  # सोमवार=Mo ... रविवार=Su

# --- इनपुट सेक्शन (Birth Data Entry) ---
with st.expander("📝 जन्म विवरण (Birth Data Entry)", expanded=True):
    c1, c2, c3, c4, c5 = st.columns([1.5, 1.2, 1.0, 1.0, 1.0])
    with c1:
        name = st.text_input("Name", value="ABCD")
    with c2:
        dob = st.date_input("Date", value=datetime.date(2010, 5, 30))
    with c3:
        tob = st.time_input("Time", value=datetime.time(14, 5))
    with c4:
        lat = st.number_input("Lat (N)", value=28.4000, format="%.4f")
    with c5:
        lon = st.number_input("Lon (E)", value=77.3000, format="%.4f")

# --- हेल्पर फंक्शन्स ---
def deg_to_dms(deg):
    deg = deg % 30.0
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(round((((deg - d) * 60) - m) * 60))
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        d += 1
    return f"{d:02d}-{m:02d}-{s:02d}"

def get_sub_and_subsub(nak_lord, deg_in_nak):
    nak_span = 13.0 + 20.0 / 60.0
    start_idx = PLANET_ORDER.index(nak_lord)
    
    current_span = 0.0
    sl_planet = nak_lord
    deg_in_sub = 0.0
    sub_span_len = 0.0
    
    # 1. Sub-Lord निकालना
    for i in range(9):
        p = PLANET_ORDER[(start_idx + i) % 9]
        span = (DASHA_YEARS[p] / 120.0) * nak_span
        if current_span <= deg_in_nak < (current_span + span):
            sl_planet = p
            deg_in_sub = deg_in_nak - current_span
            sub_span_len = span
            break
        current_span += span
        
    # Sub Lord Percentage
    sl_percent = (deg_in_sub / sub_span_len * 100.0) if sub_span_len > 0 else 0.0
    
    # 2. Sub-Sub Lord निकालना
    ssl_start_idx = PLANET_ORDER.index(sl_planet)
    current_ssl_span = 0.0
    ssl_planet = sl_planet
    for i in range(9):
        p_ssl = PLANET_ORDER[(ssl_start_idx + i) % 9]
        ssl_span = (DASHA_YEARS[p_ssl] / 120.0) * sub_span_len
        if current_ssl_span <= deg_in_sub < (current_ssl_span + ssl_span):
            ssl_planet = p_ssl
            break
        current_ssl_span += ssl_span
        
    return sl_planet, ssl_planet, sl_percent

def calc_kp_point(deg):
    deg = deg % 360.0
    sign_idx = int(deg // 30)
    nak_span = 13.0 + 20.0 / 60.0
    nak_idx = int(deg // nak_span)
    deg_in_nak = deg % nak_span
    
    sign_name = SIGN_NAMES_SHORT[sign_idx]
    rl = SIGN_LORDS[sign_idx]
    stl = NAK_LORDS[nak_idx]
    sl, ssl, sl_pct = get_sub_and_subsub(stl, deg_in_nak)
    dms = deg_to_dms(deg)
    
    return {
        "deg": deg,
        "Sign": sign_name,
        "D-M-S": dms,
        "RL": rl,
        "STL": stl,
        "SL": sl,
        "SSL": ssl,
        "SL%": f"{sl_pct:.2f}"
    }

def get_house_for_planet(planet_deg, cusps_deg):
    """कस्प डिग्रियों के आधार पर भाव संख्या निर्धारित करना"""
    for i in range(12):
        c_start = cusps_deg[i]
        c_end = cusps_deg[(i + 1) % 12]
        if c_start < c_end:
            if c_start <= planet_deg < c_end:
                return i + 1
        else:  # जब भाव 360/0 डिग्री क्रॉस करता है
            if planet_deg >= c_start or planet_deg < c_end:
                return i + 1
    return 1

# --- खगोलीय गणना ---
local_dt = datetime.datetime.combine(dob, tob)
utc_dt = local_dt - datetime.timedelta(hours=5.5)  # IST Standard Timezone
dec_hour = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, dec_hour)

# KP Ayanamsa
swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)

# भाव कस्प (Placidus 'P')
raw_cusps, ascmc = swe.houses_ex(jd, lat, lon, b'P', swe.FLG_SIDEREAL)
cusps_deg = [raw_cusps[i] for i in range(1, 13)] if len(raw_cusps) == 13 else list(raw_cusps[:12])

# ग्रह सूची
planets_map = {
    "Su": swe.SUN, "Mo": swe.MOON, "Ma": swe.MARS, "Me": swe.MERCURY,
    "Ju": swe.JUPITER, "Ve": swe.VENUS, "Sa": swe.SATURN, "Ra": swe.MEAN_NODE
}

planet_results = {}
for code, pid in planets_map.items():
    res, _ = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL | swe.FLG_SWIEPH)
    p_deg = res[0]
    p_spd = res[3]
    info = calc_kp_point(p_deg)
    info["is_retro"] = (p_spd < 0)
    info["code"] = code
    planet_results[code] = info

# Ketu गणना (राहु से 180°)
ketu_deg = (planet_results["Ra"]["deg"] + 180.0) % 360.0
k_info = calc_kp_point(ketu_deg)
k_info["is_retro"] = True
k_info["code"] = "Ke"
planet_results["Ke"] = k_info

# ग्रहों के भाव (House Placement)
for p_code, p_data in planet_results.items():
    p_data["Hse"] = get_house_for_planet(p_data["deg"], cusps_deg)

# भाव कस्प विवरण
cusp_results = []
cusp_labels = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th"]
for i in range(12):
    c_info = calc_kp_point(cusps_deg[i])
    c_info["Cusp"] = cusp_labels[i]
    cusp_results.append(c_info)

# Ruling Planets गणना
day_lord = WEEKDAYS[dob.weekday()]
lagna_info = cusp_results[0]
moon_info = planet_results["Mo"]

# विंशोत्तरी महादशा
moon_deg = planet_results["Mo"]["deg"]
nak_span = 13.0 + 20.0 / 60.0
deg_in_nak = moon_deg % nak_span
balance_fraction = 1.0 - (deg_in_nak / nak_span)
birth_nak_lord = planet_results["Mo"]["STL"]
balance_years = DASHA_YEARS[birth_nak_lord] * balance_fraction

start_dasha_idx = PLANET_ORDER.index(birth_nak_lord)
curr_date = dob + datetime.timedelta(days=int(balance_years * 365.25))

dasa_table = [{"D": birth_nak_lord, "Ending Date": curr_date.strftime("%d/%m/%Y")}]
for i in range(1, 9):
    p_d = PLANET_ORDER[(start_dasha_idx + i) % 9]
    curr_date = curr_date + datetime.timedelta(days=int(DASHA_YEARS[p_d] * 365.25))
    dasa_table.append({"D": p_d, "Ending Date": curr_date.strftime("%d/%m/%Y")})

# --- लेआउट रेंडरिंग (3 कॉलम लेआउट) ---
row1_col1, row1_col2, row1_col3 = st.columns([1.3, 1.3, 1.0])

# १. Ruling Planets बॉक्स
with row1_col1:
    st.markdown(f"""
    <div class="card-box">
        <div class="card-header">RULING PLANETS | Time: {tob.strftime('%H:%M:%S')} Date: {dob.strftime('%d-%m-%Y')}</div>
        <table style="width:100%; border:none; font-size:12px;">
            <tr><td><b>Lagna Rashi Lord:</b> {lagna_info['RL']}</td><td><b>Moon Rashi Lord:</b> {moon_info['RL']}</td></tr>
            <tr><td><b>Lagna Star Lord:</b> {lagna_info['STL']}</td><td><b>Moon Star Lord:</b> {moon_info['STL']}</td></tr>
            <tr><td><b>Lagna Sub Lord:</b> {lagna_info['SL']}</td><td><b>Day Lord:</b> {day_lord}</td></tr>
        </table>
        <div style="margin-top:6px; color:#8B2500; font-weight:bold;">
            RULING: {lagna_info['RL']}, {lagna_info['STL']}, {lagna_info['SL']}, {moon_info['RL']}, {moon_info['STL']}, {day_lord}
        </div>
    </div>
    """, unsafe_allow_html=True)

# २. Lagna Spashta & Bhav Chalit बॉक्स
with row1_col2:
    st.markdown(f"""
    <div class="card-box" style="text-align:center;">
        <div class="card-header">LAGNA SPASHTA (लग्न कुंडली)</div>
        <div style="font-weight:bold; color:#1a4d80; padding:4px 0;">
            लग्न भाव (Ascendant): {lagna_info['Sign']} ({lagna_info['D-M-S']})
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # भाव चलित में ग्रह
    chalit_data = []
    for h in range(1, 13):
        occupants = [p for p, data in planet_results.items() if data["Hse"] == h]
        chalit_data.append({
            "भाव (House)": f"भाव {h}",
            "उपस्थित ग्रह (Planets)": ", ".join(occupants) if occupants else "-"
        })
    df_chalit = pd.DataFrame(chalit_data[2:7])  # भाव ३ से भाव ७ (प्रीव्यू जैसा)
    st.dataframe(df_chalit, hide_index=True, use_container_width=True)

# ३. विंशोत्तरी दशा
with row1_col3:
    st.markdown("""<div class="card-header">Vimshottari Dasa</div>""", unsafe_allow_html=True)
    df_dasa = pd.DataFrame(dasa_table)
    st.dataframe(df_dasa, hide_index=True, use_container_width=True, height=190)

# --- टेबल्स सेक्शन ---
t_col1, t_col2 = st.columns([1.6, 1.4])

with t_col1:
    st.markdown('<div class="card-header">PLANETARY POSITION</div>', unsafe_allow_html=True)
    planet_rows = []
    p_order_display = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]
    for p in p_order_display:
        d = planet_results[p]
        p_name = p + (" (R)" if d["is_retro"] and p not in ["Ra", "Ke"] else (" (R)" if p in ["Ra", "Ke"] else ""))
        planet_rows.append({
            "Planet": p_name,
            "Sign": d["Sign"],
            "D-M-S": d["D-M-S"],
            "RL": d["RL"],
            "STL": d["STL"],
            "SL": d["SL"],
            "SSL": d["SSL"],
            "Hse": d["Hse"]
        })
    st.dataframe(pd.DataFrame(planet_rows), hide_index=True, use_container_width=True)

with t_col2:
    st.markdown('<div class="card-header">CUSPAL POSITION</div>', unsafe_allow_html=True)
    cusp_rows = []
    for c in cusp_results:
        cusp_rows.append({
            "Cusp": c["Cusp"],
            "Sign": c["Sign"],
            "D-M-S": c["D-M-S"],
            "RL": c["RL"],
            "STL": c["STL"],
            "SL": c["SL"],
            "SSL": c["SSL"],
            "SL %": c["SL%"]
        })
    st.dataframe(pd.DataFrame(cusp_rows), hide_index=True, use_container_width=True)

# --- एक्शन बटन (Bhav Phal, KP Significators, आदि) ---
st.write("")
b1, b2, b3, b4 = st.columns(4)
with b1:
    st.button("📊 KP Significators", use_container_width=True)
with b2:
    st.button("🔍 Event Finder", use_container_width=True)
with b3:
    st.button("📜 Bhav Phal", use_container_width=True)
with b4:
    st.button("⏳ Dasa Phal", use_container_width=True)
