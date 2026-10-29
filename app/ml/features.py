
import numpy as np
import pandas as pd

WEATHER = ["temperature_c", "cloud_cover_pct", "precipitation_mm", "wind_speed_kmh", "shortwave_radiation_w_m2"]

def sun_position(idx_utc: pd.DatetimeIndex, lat: float, lon: float):
    """Return (cos zenith, solar azimuth in radians clockwise from north)."""
    d = idx_utc.dayofyear.values; h = (idx_utc.hour + idx_utc.minute / 60).values
    g = 2 * np.pi / 365 * (d - 1 + (h - 12) / 24)
    eot = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g) - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    dec = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
           + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    ha = np.radians((h * 60 + eot + 4 * lon) / 4 - 180); la = np.radians(lat)
    cz = np.sin(la) * np.sin(dec) + np.cos(la) * np.cos(dec) * np.cos(ha)
    az = np.arctan2(np.sin(ha) * np.cos(dec), np.cos(ha) * np.cos(dec) * np.sin(la) - np.sin(dec) * np.cos(la)) + np.pi
    return cz, az

def poa_estimate(ghi, cz, az, tilt_deg, panel_az_deg):
    """Irradiance on a tilted plane (Erbs diffuse split + isotropic sky). 0 = north, 90 = east."""
    ghi, cz, az = np.asarray(ghi, float), np.asarray(cz, float), np.asarray(az, float)
    czc = np.clip(cz, 0.05, None)
    kt = np.clip(ghi / (1361 * czc), 0, 1.0)
    fd = np.where(kt <= 0.22, 1 - 0.09 * kt, np.where(kt <= 0.8, 0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4, 0.165))
    t, pa = np.radians(tilt_deg), np.radians(panel_az_deg)
    sinz = np.sqrt(np.clip(1 - cz**2, 0, 1))
    cos_aoi = np.clip(np.cos(t) * cz + np.sin(t) * sinz * np.cos(az - pa), 0, None)
    beam = ghi * (1 - fd) * np.minimum(cos_aoi / czc, 3.0)
    diffuse = ghi * fd * (1 + np.cos(t)) / 2
    ground = ghi * 0.2 * (1 - np.cos(t)) / 2
    return np.where(cz > 0.05, beam + diffuse + ground, 0.0)

def make_features(weather: pd.DataFrame, lat: float, lon: float, tz: str, orientation: dict) -> pd.DataFrame:
    """`weather` is indexed by naive-UTC hour-END labels and has the WEATHER columns."""
    df = weather[WEATHER].copy()
    mid = df.index - pd.Timedelta(minutes=30)
    local = mid.tz_localize("UTC").tz_convert(tz)
    lh = local.hour + local.minute / 60
    cz, az = sun_position(mid, lat, lon)
    df["cos_zenith"] = cz
    df["clearness"] = np.clip(df.shortwave_radiation_w_m2 / (1361 * np.clip(cz, 0.05, None)), 0, 1.5)
    df["hod_sin"], df["hod_cos"] = np.sin(2 * np.pi * lh / 24), np.cos(2 * np.pi * lh / 24)
    doy = local.dayofyear
    df["doy_sin"], df["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    df["poa_est"] = poa_estimate(df.shortwave_radiation_w_m2, cz, az, orientation["tilt_deg"], orientation["panel_azimuth_deg"])
    df["daylight"] = cz > 0.05
    return df