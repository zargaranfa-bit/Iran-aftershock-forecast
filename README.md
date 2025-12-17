# Iran Aftershock Probability Forecast

A scientific, USGS-inspired aftershock probability forecasting tool
calibrated for Iranian seismicity using 40 years of USGS earthquake data.

This project provides **probabilistic aftershock forecasts**
(not deterministic predictions) based on classical seismological laws.

---

## Overview

This repository contains two main components:

1. **Data collection** from the USGS earthquake catalog (1985–2024)  
2. **Aftershock probability forecasting** using:
   - Modified Omori Law (temporal decay)
   - Gutenberg–Richter law (magnitude distribution)
   - Regional spatial filtering
   - Magnitude-dependent productivity scaling

The methodology is inspired by operational approaches used by **USGS**,
but implemented independently and simplified for transparency and validation.

---

## Scientific Background

### 1. Modified Omori Law
Models the decay of aftershock rate with time:

```
λ(t) = K / (c + t)^p
```

### 2. Gutenberg–Richter Law
Models magnitude distribution of earthquakes:

```
P(M >= M_thr) = 10^(-b(M_thr - M0))
```

### 3. Probability Model
The probability of **at least one aftershock** in a time window T is:

```
P = 1 - exp(-λ)
```

where λ is the expected number of aftershocks above a magnitude threshold.

---

## Data Source

- **USGS Earthquake Catalog**  
- Time span: **1985–2024**  
- Region: Iran and surrounding area  
- Data collected via USGS FDSN API

---

## Repository Structure

```
earthquake_forecast/
│── aftershock_forecast.py   # Streamlit forecasting app
│── download_usgs.py         # USGS data downloader
│── validation_test.py       # Historical validation script
│── requirements.txt
│── README.md
```

---

## Usage

### 1. Download earthquake catalog

```
python download_usgs.py --start-year 1985 --end-year 2024 --out usgs_40yr.csv
```

### 2. Run aftershock forecast app

```
streamlit run aftershock_forecast.py
```

---

## Model Validation

The model was validated using the 20 largest earthquakes
in the 40-year catalog.

```
Time Window | Accuracy
------------|----------
1 Day       | ~60%
7 Days      | ~70%
30 Days     | ~70%
```

These results indicate that the model performs significantly better than random guessing
and captures meaningful aftershock behavior.

---

## Important Notes

- Forecasts are probabilistic, not deterministic  
- Probabilities should not be summed across time windows  
- Results are regionally calibrated for Iranian seismicity  
- This tool is for scientific and educational purposes  

---

## References

```
- Utsu, T., Ogata, Y., & Matsu’ura, R. S. (1995)
- Gutenberg, B., & Richter, C. F. (1944)
- Aki, K. (1965)
- USGS Aftershock Forecasting Methodology
```

---

## License

MIT License

