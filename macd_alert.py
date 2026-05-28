import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

# ─────────────────────────────────────────
# Telegram 設定（GitHub Secrets から取得）
# ─────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# ─────────────────────────────────────────
# MACD パラメータ（標準値）
# ─────────────────────────────────────────
FAST_PERIOD   = 12
SLOW_PERIOD   = 26
SIGNAL_PERIOD = 9


def send_telegram(message: str) -> None:
    """Telegram に通知を送る"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    res = requests.post(url, json=payload, timeout=10)
    res.raise_for_status()
    print("✅ Telegram 通知送信完了")


def calculate_macd(close: pd.Series):
    """EMA ベースで MACD とシグナル線を計算"""
    ema_fast   = close.ewm(span=FAST_PERIOD,   adjust=False).mean()
    ema_slow   = close.ewm(span=SLOW_PERIOD,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=SIGNAL_PERIOD, adjust=False).mean()
    return macd_line, signal_line


def check_crossover() -> None:
    """USD/JPY 15分足データを取得し、MACD クロスを検出して通知"""

    print("📥 USD/JPY 15分足データ取得中...")
    ticker = yf.Ticker("USDJPY=X")
    df = ticker.history(period="5d", interval="15m")

    if df.empty or len(df) < SLOW_PERIOD + SIGNAL_PERIOD + 5:
        print("⚠️ データが不足しています。スキップします。")
        return

    macd, signal = calculate_macd(df["Close"])

    # 直前の確定足（-2）と最新足（-1）を比較
    prev_macd   = macd.iloc[-2]
    prev_signal = signal.iloc[-2]
    curr_macd   = macd.iloc[-1]
    curr_signal = signal.iloc[-1]

    price     = df["Close"].iloc[-1]
    timestamp = df.index[-1].strftime("%Y-%m-%d %H:%M")

    print(f"[{timestamp}] 価格: {price:.3f}  MACD: {curr_macd:.5f}  Signal: {curr_signal:.5f}")

    # ── ゴールデンクロス（下から上） ──────────────
    if prev_macd < prev_signal and curr_macd > curr_signal:
        msg = (
            f"📈 <b>MACD ゴールデンクロス ／ 買いシグナル</b>\n\n"
            f"通貨ペア : USD/JPY\n"
            f"時刻     : {timestamp} (UTC)\n"
            f"現在値   : {price:.3f} 円\n"
            f"MACD     : {curr_macd:.5f}\n"
            f"シグナル : {curr_signal:.5f}\n\n"
            f"⬆️ MACD がシグナルを <b>下から上</b> に突き抜けました"
        )
        send_telegram(msg)

    # ── デッドクロス（上から下） ──────────────────
    elif prev_macd > prev_signal and curr_macd < curr_signal:
        msg = (
            f"📉 <b>MACD デッドクロス ／ 売りシグナル</b>\n\n"
            f"通貨ペア : USD/JPY\n"
            f"時刻     : {timestamp} (UTC)\n"
            f"現在値   : {price:.3f} 円\n"
            f"MACD     : {curr_macd:.5f}\n"
            f"シグナル : {curr_signal:.5f}\n\n"
            f"⬇️ MACD がシグナルを <b>上から下</b> に突き抜けました"
        )
        send_telegram(msg)

    else:
        print("→ クロスなし。次の足を待ちます。")


if __name__ == "__main__":
    try:
        check_crossover()
    except Exception as e:
        print(f"⚠️ エラー発生（スキップ）: {e}")
