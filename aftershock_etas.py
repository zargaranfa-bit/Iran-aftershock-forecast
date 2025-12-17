#!/usr/bin/env python3
# ============================================================
# Iran Aftershock Forecast – Regional, USGS-inspired
# Omori + Gutenberg–Richter + productivity scaling
# ============================================================

import math
from datetime import timedelta

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from scipy.optimize import curve_fit

# ============================================================
# Constants (Iran-calibrated)
# ============================================================
M0 = 4.5                      # magnitude completeness
ALPHA = 0.9                   # productivity scaling (USGS-like)
DEFAULT_RADIUS_KM = 250       # regional influence
TIME_WINDOWS = [1, 7, 30]     # day, week, month
MAG_THRESHOLDS = [5.0, 5.5, 6.0, 6.5]
MAX_PROB = 0.97               # soft saturation (NOT lambda cap)

# ============================================================
# Utilities
# ============================================================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def omori_rate(t, K, c, p):
    return K / ((c + t) ** p)


def integrate_omori(K, c, p, T):
    if T <= 0 or K <= 0:
        return 0.0
    if abs(p - 1.0) < 1e-6:
        return K * math.log((c + T) / c)
    return K / (1 - p) * ((c + T)**(1 - p) - c**(1 - p))


def aki_b_value(mags, Mmin):
    mags = mags[mags >= Mmin]
    if len(mags) < 30:
        return 1.0
    return 0.4343 / (mags.mean() - Mmin)


def gr_tail_prob(Mthr, b):
    if Mthr <= M0:
        return 1.0
    return 10 ** (-b * (Mthr - M0))


# ============================================================
# Load catalog (compatible with your USGS downloader)
# ============================================================
@st.cache_data
def load_catalog(path):
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["time"], format="mixed", utc=True)
    return df.dropna(subset=["time", "mag", "lat", "lon"])


# ============================================================
# Regional selection
# ============================================================
def select_region(df, lat, lon, radius_km):
    d = haversine(lat, lon, df["lat"].values, df["lon"].values)
    return df[d <= radius_km]


# ============================================================
# Fit Omori parameters regionally
# ============================================================
def fit_omori(df, t0):
    df = df[df["time"] > t0]
    if len(df) < 20:
        return 0.3, 0.3, 1.1   # conservative fallback

    days = (df["time"] - t0).dt.total_seconds() / 86400.0
    hist, _ = np.histogram(days, bins=np.arange(0, 31))
    t = np.arange(1, len(hist) + 1)

    try:
        popt, _ = curve_fit(
            omori_rate, t, hist,
            bounds=([0.05, 0.01, 0.8], [10.0, 5.0, 1.6]),
            maxfev=20000
        )
        return popt
    except:
        return 0.3, 0.3, 1.1


# ============================================================
# Streamlit UI
# ============================================================
st.set_page_config("Iran Aftershock Forecast", layout="wide")
st.title("Aftershock Probability Forecast – Iran")

st.sidebar.header("Catalog")
csv_path = st.sidebar.text_input("USGS CSV path", "usgs_40yr.csv")

st.sidebar.header("Mainshock")
lat = st.sidebar.number_input("Latitude", value=35.69, format="%.2f")
lon = st.sidebar.number_input("Longitude", value=51.39, format="%.2f")
mag = st.sidebar.number_input("Magnitude", value=6.2, step=0.1, format="%.1f")

run = st.sidebar.button("Run Forecast")
if not run:
    st.stop()

# ============================================================
# Run model
# ============================================================
catalog = load_catalog(csv_path)
main_time = pd.Timestamp.utcnow()

regional = select_region(catalog, lat, lon, DEFAULT_RADIUS_KM)

b_val = aki_b_value(regional["mag"].values, M0)
K0, c, p = fit_omori(regional, main_time)

# === Productivity scaling (KEY FIX) ===
K = K0 * (10 ** (ALPHA * (mag - 6.0)))

# ============================================================
# Forecast
# ============================================================
rows = []

for T in TIME_WINDOWS:
    base_rate = integrate_omori(K, c, p, T)

    for Mthr in MAG_THRESHOLDS:
        lam = base_rate * gr_tail_prob(Mthr, b_val)

        # Soft probability saturation (not lambda cut!)
        prob = 1 - math.exp(-lam)
        prob = min(prob, MAX_PROB)

        rows.append({
            "Window": {1: "1 Day", 7: "1 Week", 30: "1 Month"}[T],
            "Magnitude": f"M ≥ {Mthr}",
            "Probability (%)": round(prob * 100, 1)
        })

df_out = pd.DataFrame(rows)

# ============================================================
# Text summary (USGS-like)
# ============================================================
st.subheader("Forecast Summary")

for T in ["1 Day", "1 Week", "1 Month"]:
    st.markdown(f"**Chance of ≥1 aftershock in the next {T.lower()}:**")
    subset = df_out[df_out["Window"] == T]
    for _, r in subset.iterrows():
        st.write(f"- {r['Magnitude']}: **{r['Probability (%)']}%**")
    st.write("")

# ============================================================
# Visualization
# ============================================================
chart = (
    alt.Chart(df_out)
    .mark_bar()
    .encode(
        x=alt.X("Window:N", sort=["1 Day", "1 Week", "1 Month"]),
        y=alt.Y("Probability (%):Q", scale=alt.Scale(domain=[0, 100])),
        color="Magnitude:N",
        tooltip=["Probability (%)"]
    )
    .properties(height=400)
)

st.subheader("Probability Comparison")
st.altair_chart(chart, use_container_width=True)

st.caption(
    "Probabilities are regional, time-dependent, and magnitude-scaled. "
    "Model inspired by USGS methodology (Omori + GR + productivity scaling). "
    "This is a probabilistic scientific forecast, not a prediction."
)
