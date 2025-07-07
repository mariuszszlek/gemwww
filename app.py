# app.py
# ------------------------------------------------------------------------------
# pip install yfinance pandas matplotlib flask
# ------------------------------------------------------------------------------

import os
import matplotlib

# włącz backend non-GUI do zapisu plików
matplotlib.use("Agg")

from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from flask import Flask, render_template, send_file

# ETF-y i ich nazwy
TICKERS = {
    "CSPX.L": "iShares Core S&P 500 UCITS ETF (Acc)",
    "IWDA.AS": "iShares Core MSCI World UCITS ETF (Acc)",
    "VUTY.L": "Vanguard USD Treasury Bond UCITS ETF (Acc)",
}

# Katalog na wykresy
DATA_DIR = os.path.join(os.path.dirname(__file__), "static", "images")
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)


def fetch_history(ticker: str, period: str = "1y") -> pd.Series:
    """
    Pobiera historyczne ceny; najpierw próbuje 'Adj Close', 
    a jeśli go nie ma — bierze 'Close'.
    """
    try:
        df = yf.Ticker(ticker).history(period=period)
        if df.empty:
            raise ValueError(f"Brak danych dla {ticker}")
        # fallback dla kolumny
        if "Adj Close" in df.columns:
            return df["Adj Close"]
        return df["Close"]
    except Exception as e:
        raise RuntimeError(f"Błąd pobierania {ticker}: {e}")


def calc_momentum(series: pd.Series) -> float:
    """
    Oblicza 12-miesięczne momentum: (ostatnia / pierwsza) - 1.
    """
    if len(series) < 2:
        return float("nan")
    return series.iloc[-1] / series.iloc[0] - 1.0


def generate_return_plot(prices: dict) -> str:
    """
    Rysuje skumulowane zwroty [%] od dnia startu i zapisuje PNG.
    """
    plt.figure(figsize=(12, 6))
    for ticker, series in prices.items():
        returns = (series / series.iloc[0] - 1) * 100
        plt.plot(series.index, returns, label=ticker)
    plt.title("12-miesięczne zwroty procentowe ETF-ów")
    plt.xlabel("Data")
    plt.ylabel("Zwrot [%]")
    plt.legend()
    fname = "returns.png"
    path = os.path.join(DATA_DIR, fname)
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return fname


def gem_recommendation(momentums: dict) -> (str, str):
    """
    Wybiera aktywo wg strategii GEM:
      - spośród CSPX.L i IWDA.AS z najwyższym momentum > 0
      - inaczej VUTY.L
      - jeśli brak danych → pusta rekomendacja
    """
    eq = {t: momentums[t] for t in ("CSPX.L", "IWDA.AS") if t in momentums}
    if eq:
        best = max(eq, key=eq.get)
        if eq[best] > 0:
            return best, f"{TICKERS[best]} miał najwyższy zwrot: {eq[best]:.1%}"
    if "VUTY.L" in momentums:
        # jeśli były akcje, wypisz ich zwroty; inaczej inny komunikat
        if eq:
            msg = (
                "Brak dodatnich zwrotów akcji ("
                + ", ".join(f"{t}: {v:.1%}" for t, v in eq.items())
                + ") → obligacje."
            )
        else:
            msg = "Brak danych dla akcji → rekomendacja obligacji."
        return "VUTY.L", msg
    return "", "Brak danych do wygenerowania rekomendacji."


@app.route("/")
def index():
    errors = []
    prices = {}
    momentums = {}

    # 1) pobierz dane + momentum
    for t in TICKERS:
        try:
            s = fetch_history(t, period="1y")
            prices[t] = s
            momentums[t] = calc_momentum(s)
        except Exception as e:
            errors.append(str(e))

    # 2) rekomendacja GEM
    rec_t, reason = gem_recommendation(momentums)

    # 3) wykres zwrotów
    returns_img = generate_return_plot(prices) if prices else ""

    return render_template(
        "index.html",
        title="Rekomendacje Inwestycyjne GEM",
        recommendation=(rec_t, TICKERS.get(rec_t, "")),
        reason=reason,
        tickers=TICKERS,
        momentums=momentums,
        returns_img=returns_img,
        errors=errors,
    )


@app.route("/image/<filename>")
def image(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return "Not found", 404
    return send_file(path, mimetype="image/png")


if __name__ == "__main__":
    app.run(debug=True)
