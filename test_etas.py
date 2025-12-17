#!/usr/bin/env python3
# ============================================================
# Aftershock Forecast Validation
# ============================================================

import math
from datetime import timedelta

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

# ------------------------------------------------------------
# Parameters
# ------------------------------------------------------------
CATALOG_PATH = "usgs_40yr.csv"
N_MAINSHOCKS = 20
RADIUS_KM = 250
M0 = 4.5
TARGET_MAG = 5.0
TIME_WINDOWS = [1, 7, 30]   # days
PROB_THRESHOLD = 0.5        # 50%

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------
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
    if abs(p - 1.0) < 1e-6:
        return K * math.log((c + T) / c)
    return K / (1 - p) * ((c + T)**(1 - p) - c**(1 - p))


def aki_b_value(mags, Mmin):
    mags = mags[mags >= Mmin]
    if len(mags) < 20:
        return 1.0
    return 0.4343 / (mags.mean() - Mmin)


def gr_tail(Mthr, b):
    if Mthr <= M0:
        return 1.0
    return 10 ** (-b * (Mthr - M0))


# ------------------------------------------------------------
# Load catalog
# ------------------------------------------------------------
df = pd.read_csv(CATALOG_PATH)
df["time"] = pd.to_datetime(df["time"], format="mixed", utc=True)
df = df.dropna(subset=["time", "mag", "lat", "lon"]).sort_values("time")

# ------------------------------------------------------------
# Select top-N mainshocks
# ------------------------------------------------------------
mainshocks = df.sort_values("mag", ascending=False).head(N_MAINSHOCKS)

results = []

# ------------------------------------------------------------
# Validation loop
# ------------------------------------------------------------
for _, ms in mainshocks.iterrows():
    t0 = ms["time"]
    lat0, lon0 = ms["lat"], ms["lon"]
    mag0 = ms["mag"]

    # regional catalog
    dist = haversine(lat0, lon0, df["lat"].values, df["lon"].values)
    regional = df[dist <= RADIUS_KM]

    # aftershocks only (exclude mainshock itself)
    after = regional[regional["time"] > t0]

    # estimate b-value
    b = aki_b_value(regional["mag"].values, M0)

    # fit Omori (simple fallback)
    days = (after["time"] - t0).dt.total_seconds() / 86400
    hist, _ = np.histogram(days, bins=np.arange(0, 31))
    t = np.arange(1, len(hist) + 1)

    try:
        popt, _ = curve_fit(
            omori_rate, t, hist,
            bounds=([0.01, 0.01, 0.8], [5.0, 5.0, 1.5])
        )
        K0, c, p = popt
    except:
        K0, c, p = 0.3, 0.5, 1.1

    # productivity scaling
    K = K0 * 10 ** (0.6 * (mag0 - 6.0))

    for T in TIME_WINDOWS:
        # model probability
        lam = integrate_omori(K, c, p, T) * gr_tail(TARGET_MAG, b)
        lam = min(lam, 2.0)
        prob = 1 - math.exp(-lam)

        predicted = prob >= PROB_THRESHOLD

        # observed reality
        observed = any(
            (after["time"] <= t0 + timedelta(days=T)) &
            (after["mag"] >= TARGET_MAG)
        )

        results.append({
            "mainshock_mag": round(mag0, 1),
            "window_days": T,
            "predicted_prob": round(prob, 3),
            "predicted_event": predicted,
            "observed_event": observed,
            "correct": predicted == observed
        })

# ------------------------------------------------------------
# Results summary
# ------------------------------------------------------------
res = pd.DataFrame(results)

print("\n=== VALIDATION SUMMARY ===\n")
for T in TIME_WINDOWS:
    subset = res[res["window_days"] == T]
    accuracy = subset["correct"].mean() * 100
    print(f"{T} days → accuracy: {accuracy:.1f}%")

print("\nDetailed results:")
print(res)
