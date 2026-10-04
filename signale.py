#!/usr/bin/env python3
"""
Gold / Silber / Krypto – Indikator-basiertes Signal-Tool
==========================================================

WICHTIG: Dies ist KEINE Anlageberatung. Alle Signale basieren rein auf
technischer Analyse historischer Kursdaten. Käufe/Verkäufe erfolgen
ausschließlich auf eigenes Risiko. Vergangene Kursverläufe und
Indikator-Trefferquoten sind KEINE Garantie für die Zukunft.

Verwendete Indikatoren (alle seit Jahrzehnten etabliert):
  - SMA 50/200            -> Golden Cross / Death Cross (Langfrist-Trend)
  - EMA 20/50             -> mittelfristiger Trend
  - RSI (14)              -> Momentum, überkauft/überverkauft
  - MACD (12,26,9)        -> Trend & Momentum
  - Bollinger Bänder (20,2) -> Volatilität / Mean Reversion
  - Stochastik (14,3)     -> Momentum, überkauft/überverkauft
  - ADX (14)              -> Trendstärke (verstärkt/schwächt andere Signale)
  - ATR (14)              -> Volatilität (Info, für Risikoeinschätzung)

Horizonte:
  - kurz   (~1 Monat / 21 Handelstage)   -> Fokus: RSI, Stochastik, Bollinger, MACD
  - mittel (~6 Monate / 126 Handelstage) -> Fokus: EMA20/50, MACD, ADX
  - lang   (~12-24 Monate / 378 Tage)    -> Fokus: SMA50/200 (Golden/Death Cross), ADX

Nutzung:
    pip install -r requirements.txt
    python signale.py                         # alle Assets, alle Horizonte
    python signale.py --assets BTC ETH Gold    # nur bestimmte Assets
    python signale.py --horizonte kurz lang    # nur bestimmte Horizonte
    python signale.py --keine-backtests        # schneller, ohne Historien-Check
    python signale.py --csv ergebnisse.csv     # Ergebnisse zusätzlich als CSV speichern

Hinweis: Das Skript benötigt eine funktionierende Internetverbindung, da
die Kursdaten live über Yahoo Finance (yfinance) geladen werden.
"""

import argparse
import sys
from datetime import datetime

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("Bitte zuerst installieren: pip install -r requirements.txt")
    sys.exit(1)


# ---------------------------------------------------------------------------
# 1) Asset-Universum
# ---------------------------------------------------------------------------
# Gold/Silber über liquide ETFs (saubere Tagesdaten inkl. Volumen).
# Wer lieber die Futures-Kontrakte will: "GC=F" (Gold) / "SI=F" (Silber).
ASSETS = {
    "Gold":   "GLD",
    "Silber": "SLV",
    "BTC":    "BTC-USD",
    "ETH":    "ETH-USD",
    "XRP":    "XRP-USD",
    "BNB":    "BNB-USD",
    "SOL":    "SOL-USD",
    "ADA":    "ADA-USD",
    "DOGE":   "DOGE-USD",
    "TRX":    "TRX-USD",
    "LINK":   "LINK-USD",
    "DOT":    "DOT-USD",
}


# ---------------------------------------------------------------------------
# 2) Indikatoren
# ---------------------------------------------------------------------------
def sma(series, window):
    return series.rolling(window).mean()


def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))
    return result.fillna(50)


def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger(series, window=20, num_std=2):
    mid = sma(series, window)
    std = series.rolling(window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def stochastic(df, k_window=14, d_window=3):
    low_min = df["Low"].rolling(k_window).min()
    high_max = df["High"].rolling(k_window).max()
    k = 100 * (df["Close"] - low_min) / (high_max - low_min).replace(0, np.nan)
    d = k.rolling(d_window).mean()
    return k.fillna(50), d.fillna(50)


def atr(df, window=14):
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def adx(df, window=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_ = tr.rolling(window).mean()

    plus_di = 100 * (plus_dm.rolling(window).mean() / atr_.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(window).mean() / atr_.replace(0, np.nan))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_ = dx.rolling(window).mean()
    return adx_.fillna(0)


def add_indicators(df):
    df = df.copy()
    df["SMA50"] = sma(df["Close"], 50)
    df["SMA200"] = sma(df["Close"], 200)
    df["EMA20"] = ema(df["Close"], 20)
    df["EMA50"] = ema(df["Close"], 50)
    df["RSI"] = rsi(df["Close"], 14)
    df["MACD"], df["MACD_SIGNAL"], df["MACD_HIST"] = macd(df["Close"])
    df["BB_UPPER"], df["BB_MID"], df["BB_LOWER"] = bollinger(df["Close"])
    df["STOCH_K"], df["STOCH_D"] = stochastic(df)
    df["ADX"] = adx(df)
    df["ATR"] = atr(df)
    return df


# ---------------------------------------------------------------------------
# 3) Signal-Logik pro Horizont
# ---------------------------------------------------------------------------
def score_short(row):
    """Kurzfristig (~1 Monat): Momentum & Mean-Reversion."""
    s, detail = 0.0, {}
    if pd.notna(row["RSI"]):
        if row["RSI"] < 30:
            s += 2; detail["RSI(14)"] = f"{row['RSI']:.1f} -> überverkauft (bullish)"
        elif row["RSI"] > 70:
            s -= 2; detail["RSI(14)"] = f"{row['RSI']:.1f} -> überkauft (bearish)"
        else:
            detail["RSI(14)"] = f"{row['RSI']:.1f} -> neutral"
    if pd.notna(row["STOCH_K"]):
        if row["STOCH_K"] < 20:
            s += 1; detail["Stochastik"] = f"{row['STOCH_K']:.1f} -> überverkauft (bullish)"
        elif row["STOCH_K"] > 80:
            s -= 1; detail["Stochastik"] = f"{row['STOCH_K']:.1f} -> überkauft (bearish)"
        else:
            detail["Stochastik"] = f"{row['STOCH_K']:.1f} -> neutral"
    if pd.notna(row["BB_LOWER"]) and pd.notna(row["BB_UPPER"]):
        if row["Close"] <= row["BB_LOWER"]:
            s += 2; detail["Bollinger"] = "Kurs am/unter unterem Band -> bullish"
        elif row["Close"] >= row["BB_UPPER"]:
            s -= 2; detail["Bollinger"] = "Kurs am/über oberem Band -> bearish"
        else:
            detail["Bollinger"] = "innerhalb der Bänder -> neutral"
    if pd.notna(row["MACD_HIST"]):
        if row["MACD_HIST"] > 0:
            s += 1; detail["MACD-Histogramm"] = "positiv -> bullish"
        else:
            s -= 1; detail["MACD-Histogramm"] = "negativ -> bearish"
    return s, detail


def score_medium(row):
    """Mittelfristig (~6 Monate): Trendfolge, ADX verstärkt Signal."""
    s, detail = 0.0, {}
    if pd.notna(row["EMA20"]) and pd.notna(row["EMA50"]):
        if row["EMA20"] > row["EMA50"]:
            s += 2; detail["EMA20/50"] = "EMA20 > EMA50 -> Aufwärtstrend"
        else:
            s -= 2; detail["EMA20/50"] = "EMA20 < EMA50 -> Abwärtstrend"
    if pd.notna(row["MACD"]) and pd.notna(row["MACD_SIGNAL"]):
        if row["MACD"] > row["MACD_SIGNAL"]:
            s += 1; detail["MACD"] = "MACD > Signal-Linie -> bullish"
        else:
            s -= 1; detail["MACD"] = "MACD < Signal-Linie -> bearish"
    if pd.notna(row["ADX"]):
        if row["ADX"] > 25:
            s *= 1.5
            detail["ADX(14)"] = f"{row['ADX']:.1f} -> starker Trend (Signal verstärkt)"
        else:
            detail["ADX(14)"] = f"{row['ADX']:.1f} -> schwacher Trend"
    return s, detail


def score_long(row):
    """Langfristig (~12-24 Monate): Golden/Death Cross."""
    s, detail = 0.0, {}
    if pd.notna(row["SMA50"]) and pd.notna(row["SMA200"]):
        if row["SMA50"] > row["SMA200"]:
            s += 3; detail["SMA50/200"] = "Golden-Cross-Zustand -> langfristig bullish"
        else:
            s -= 3; detail["SMA50/200"] = "Death-Cross-Zustand -> langfristig bearish"
    if pd.notna(row["SMA200"]):
        if row["Close"] > row["SMA200"]:
            s += 1; detail["Kurs vs. SMA200"] = "über SMA200 -> bullish"
        else:
            s -= 1; detail["Kurs vs. SMA200"] = "unter SMA200 -> bearish"
    if pd.notna(row["ADX"]):
        tag = "Trend bestätigt" if row["ADX"] > 25 else "kein starker Trend"
        detail["ADX(14)"] = f"{row['ADX']:.1f} -> {tag}"
    return s, detail


HORIZONTE = {
    "kurz":   {"tage": 21,  "score_fn": score_short,  "max_abs": 6.0, "titel": "Kurzfristig (~1 Monat)"},
    "mittel": {"tage": 126, "score_fn": score_medium, "max_abs": 4.5, "titel": "Mittelfristig (~6 Monate)"},
    "lang":   {"tage": 378, "score_fn": score_long,   "max_abs": 4.0, "titel": "Langfristig (~12-24 Monate)"},
}


def to_label(score, max_abs):
    ratio = score / max_abs if max_abs else 0
    if ratio >= 0.5:
        return "STARKER KAUF"
    elif ratio >= 0.15:
        return "KAUF"
    elif ratio <= -0.5:
        return "STARKER VERKAUF"
    elif ratio <= -0.15:
        return "VERKAUF"
    return "NEUTRAL / HALTEN"


# ---------------------------------------------------------------------------
# 4) Backtest: Wie gut hat dieses Signal historisch funktioniert?
# ---------------------------------------------------------------------------
def backtest(df, horizon_tage, score_fn):
    rows = []
    close = df["Close"].values
    n = len(df)
    for i in range(n - horizon_tage):
        row = df.iloc[i]
        score, _ = score_fn(row)
        future_return = (close[i + horizon_tage] / close[i] - 1) * 100
        rows.append((score, future_return))
    bt = pd.DataFrame(rows, columns=["score", "future_return"])

    bullish = bt[bt["score"] > 0]
    bearish = bt[bt["score"] < 0]

    def safe_mean(s):
        return float(s.mean()) if len(s) else float("nan")

    return {
        "anzahl_bullische_signale": len(bullish),
        "trefferquote_bullish_%": safe_mean((bullish["future_return"] > 0) * 100),
        "avg_return_bullish_%": safe_mean(bullish["future_return"]),
        "anzahl_bearishe_signale": len(bearish),
        "trefferquote_bearish_%": safe_mean((bearish["future_return"] < 0) * 100),
        "avg_return_bearish_%": safe_mean(bearish["future_return"]),
    }


# ---------------------------------------------------------------------------
# 5) Datenabruf
# ---------------------------------------------------------------------------
def fetch_data(ticker, period="5y"):
    df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
    if df.empty:
        raise ValueError(f"Keine Daten für {ticker} erhalten.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna(subset=["Close"])


# ---------------------------------------------------------------------------
# 6) Ausgabe pro Asset
# ---------------------------------------------------------------------------
def analysiere_asset(name, ticker, period, horizonte, mit_backtest, csv_rows, json_result=None):
    print("\n" + "=" * 70)
    print(f"  {name}  ({ticker})")
    print("=" * 70)

    try:
        df = fetch_data(ticker, period)
    except Exception as e:
        print(f"  Fehler beim Laden: {e}")
        if json_result is not None:
            json_result[name] = {"ticker": ticker, "fehler": str(e)}
        return

    df = add_indicators(df)
    latest = df.iloc[-1]
    stand = df.index[-1].strftime("%Y-%m-%d")
    print(f"  Letzter Kurs: {latest['Close']:.4f}  (Stand: {stand})")

    asset_json = {
        "ticker": ticker,
        "letzter_kurs": round(float(latest["Close"]), 6),
        "stand": stand,
        "horizonte": {},
    }

    for key in horizonte:
        h = HORIZONTE[key]
        score, detail = h["score_fn"](latest)
        empfehlung = to_label(score, h["max_abs"])

        print(f"\n  --- {h['titel']} ---")
        print(f"  Empfehlung: {empfehlung}  (Score: {score:.1f} / max. {h['max_abs']:.1f})")
        for k, v in detail.items():
            print(f"      {k}: {v}")

        bt_result = {}
        if mit_backtest and len(df) > h["tage"] + 250:
            bt_result = backtest(df, h["tage"], h["score_fn"])
            print(f"  Historischer Backtest (gesamter geladener Zeitraum):")
            print(f"      Bullische Signale: {bt_result['anzahl_bullische_signale']} "
                  f"| Trefferquote (Kurs stieg danach): {bt_result['trefferquote_bullish_%']:.1f}% "
                  f"| Ø Rendite danach: {bt_result['avg_return_bullish_%']:.2f}%")
            print(f"      Bearishe Signale:  {bt_result['anzahl_bearishe_signale']} "
                  f"| Trefferquote (Kurs fiel danach):  {bt_result['trefferquote_bearish_%']:.1f}% "
                  f"| Ø Rendite danach: {bt_result['avg_return_bearish_%']:.2f}%")

        csv_rows.append({
            "Asset": name, "Ticker": ticker, "Horizont": h["titel"],
            "Score": round(score, 2), "Empfehlung": empfehlung,
            **bt_result,
        })

        asset_json["horizonte"][key] = {
            "titel": h["titel"],
            "score": round(float(score), 2),
            "max_score": h["max_abs"],
            "empfehlung": empfehlung,
            "details": detail,
            "backtest": bt_result,
        }

    if json_result is not None:
        json_result[name] = asset_json


# ---------------------------------------------------------------------------
# 7) CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Indikator-basierte Kauf-Signale für Gold, Silber & Top-Kryptos.")
    parser.add_argument("--assets", nargs="+", default=list(ASSETS.keys()),
                         help=f"Assets, Auswahl aus: {', '.join(ASSETS.keys())}")
    parser.add_argument("--horizonte", nargs="+", default=list(HORIZONTE.keys()),
                         choices=list(HORIZONTE.keys()), help="kurz / mittel / lang")
    parser.add_argument("--period", default="5y", help="Zeitraum der geladenen Historie (z.B. 2y, 5y, 10y, max)")
    parser.add_argument("--keine-backtests", action="store_true", help="Backtest-Berechnung überspringen (schneller)")
    parser.add_argument("--csv", default=None, help="Pfad zum Speichern der Ergebnisse als CSV")
    parser.add_argument("--json", default=None, help="Pfad zum Speichern der Ergebnisse als JSON (z.B. für die Web-/iPhone-Ansicht)")
    args = parser.parse_args()

    unbekannt = [a for a in args.assets if a not in ASSETS]
    if unbekannt:
        print(f"Unbekannte Assets: {unbekannt}. Verfügbar: {list(ASSETS.keys())}")
        sys.exit(1)

    print("#" * 70)
    print("# Gold / Silber / Krypto – Indikator-Signale")
    print(f"# Lauf: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("#")
    print("# HINWEIS: Keine Anlageberatung. Rein technische Analyse auf")
    print("# Basis historischer Kursdaten. Kauf/Verkauf auf eigenes Risiko.")
    print("#" * 70)

    csv_rows = []
    json_result = {} if args.json else None
    for name in args.assets:
        analysiere_asset(name, ASSETS[name], args.period, args.horizonte,
                          not args.keine_backtests, csv_rows, json_result)

    if args.csv and csv_rows:
        pd.DataFrame(csv_rows).to_csv(args.csv, index=False)
        print(f"\nErgebnisse gespeichert unter: {args.csv}")

    if args.json and json_result is not None:
        import json as _json
        payload = {
            "generiert_am": datetime.now().isoformat(timespec="seconds"),
            "assets": json_result,
        }
        with open(args.json, "w", encoding="utf-8") as f:
            _json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\nJSON gespeichert unter: {args.json}")


if __name__ == "__main__":
    main()
