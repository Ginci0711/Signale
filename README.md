# Gold / Silber / Krypto – Indikator-Signal-Tool

Ein Python-Kommandozeilen-Tool, das für Gold, Silber und die 10 wichtigsten
Kryptowährungen historische Kursdaten lädt, seit Jahren etablierte technische
Indikatoren berechnet und daraus **Kurz- (1 Monat), Mittel- (6 Monate) und
Langfrist-Signale (12–24 Monate)** ableitet – inklusive Backtest, wie gut das
jeweilige Signal in der Vergangenheit tatsächlich funktioniert hat.

> ⚠️ **Kein Finanzrat.** Alle Ausgaben sind rein technische Analyse
> historischer Kurse. Käufe/Verkäufe erfolgen ausschließlich auf eigenes
> Risiko. Historische Trefferquoten sind keine Garantie für die Zukunft.

## Enthaltene Assets

| Kürzel | Ticker (Yahoo Finance) |
|---|---|
| Gold | GLD (ETF) |
| Silber | SLV (ETF) |
| BTC, ETH, XRP, BNB, SOL, ADA, DOGE, TRX, LINK, DOT | `XXX-USD` |

Ticker lassen sich in `signale.py` im Dict `ASSETS` beliebig anpassen
(z. B. `GC=F`/`SI=F` für die Futures-Kontrakte statt der ETFs).

## Installation

```bash
pip install -r requirements.txt
```

## Nutzung

```bash
# Alle Assets, alle Horizonte, mit Backtest (Standard)
python signale.py

# Nur bestimmte Assets
python signale.py --assets BTC ETH Gold Silber

# Nur bestimmte Horizonte
python signale.py --horizonte kurz lang

# Anderer Betrachtungszeitraum für die Historie (Standard: 5 Jahre)
python signale.py --period 10y

# Ohne Backtest (schneller)
python signale.py --keine-backtests

# Ergebnisse zusätzlich als CSV
python signale.py --csv ergebnisse.csv
```

## Methodik

### Verwendete Indikatoren
- **SMA 50/200** – Golden Cross / Death Cross, Langfrist-Trend
- **EMA 20/50** – mittelfristiger Trend
- **RSI (14)** – Momentum, überkauft (>70) / überverkauft (<30)
- **MACD (12,26,9)** – Trend & Momentum
- **Bollinger Bänder (20,2)** – Volatilität, Mean-Reversion-Signale
- **Stochastik (14,3)** – Momentum, überkauft/überverkauft
- **ADX (14)** – Trendstärke; verstärkt oder schwächt andere Signale
- **ATR (14)** – Volatilität (nur zur Information/Risikoeinschätzung)

### Gewichtung je Horizont
- **Kurz (1 Monat):** RSI, Stochastik und Bollinger dominieren (Mean
  Reversion), MACD-Histogramm als Momentum-Bestätigung.
- **Mittel (6 Monate):** EMA20 vs. EMA50 und MACD-Kreuzung als Trendfolge,
  ADX verstärkt das Signal bei starkem Trend.
- **Lang (12–24 Monate):** Golden/Death Cross (SMA50 vs. SMA200) als
  Hauptsignal, Kurs relativ zu SMA200 als Bestätigung.

Jeder Indikator liefert einen Punktwert (positiv = bullish, negativ =
bearish). Die Summe wird auf eine Skala normiert und in eine Empfehlung
übersetzt: **STARKER KAUF / KAUF / NEUTRAL-HALTEN / VERKAUF / STARKER
VERKAUF**.

### Backtest
Für jeden Horizont wird über die gesamte geladene Historie geprüft: Immer
wenn die gleiche Signal-Logik in der Vergangenheit "bullisch" bzw.
"bearisch" stand – wie oft hatte der Kurs danach tatsächlich zugelegt bzw.
nachgegeben, und wie hoch war die durchschnittliche Rendite? Das macht
sichtbar, wie verlässlich die Indikator-Kombination für genau dieses Asset
in der Vergangenheit war – unterscheidet sich von Asset zu Asset teils
deutlich (Krypto reagiert z. B. oft anders als Gold).

## Grenzen
- Rein technische Analyse – fundamentale Faktoren (Zinsen, Regulierung,
  Nachrichtenlage etc.) fließen nicht ein.
- ADX-Berechnung ist eine vereinfachte (gleitender Durchschnitt statt
  Wilder-Glättung), Standard-Interpretation bleibt aber gültig.
- Historische Trefferquoten aus dem Backtest sind kein Versprechen für die
  Zukunft, besonders bei Kryptowährungen mit kürzerer Handelshistorie.
- Für Gold/Silber werden ETF-Kurse (GLD/SLV) statt Spotpreis verwendet –
  sehr nah am Spotpreis, aber nicht 1:1 identisch.
