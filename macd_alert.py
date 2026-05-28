import yfinance as yf
import requests
import os
import time

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

FAST_PERIOD   = 12
SLOW_PERIOD   = 26
SIGNAL_PERIOD = 9

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    print("✅ Telegram 送信完了")

def calculate_macd(close):
    ema_fast   = close.ewm(span=FAST_PERIOD,   adjust=False).mean()
    ema_slow   = close.ewm(span=SLOW_PERIOD,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=SIGNAL_PERIOD, adjust=False).mean()
    return macd_line, signal_line

def fetch_with_retry(retries=3):
    for i in range(retries):
        try:
            df = yf.Ticker("USDJPY=X").history(period="5d", interval="15m")
            if not df.empty:
                return df
        except Exception as e:
            print(f"取得失敗({i+1}/{retries}): {e}")
            time.sleep(10)
    return None

def check_crossover():
    print("📥 データ取得中...")
    df = fetch_with_retry()

    if df is None or len(df) < 40:
        print("⚠️ データ不足のためスキップ")
        return

    macd, signal = calculate_macd(df["Close"])

    prev_macd   = macd.iloc[-2]
    prev_signal = signal.iloc[-2]
    curr_macd   = macd.iloc[-1]
    curr_signal = signal.iloc[-1]
    price     = df["Close"].iloc[-1]
    timestamp = df.index[-1].strftime("%Y-%m-%d %H:%M")

    print(f"[{timestamp}] 価格:{price:.3f} MACD:{curr_macd:.5f} Signal:{curr_signal:.5f}")

    if prev_macd < prev_signal and curr_macd > curr_signal:
        send_telegram(
            f"📈 <b>ゴールデンクロス（買いシグナル）</b>\n"
            f"USD/JPY | {timestamp} UTC\n"
            f"価格: {price:.3f} 円\n"
            f"⬆️ MACDがシグナルを下から上に突き抜けました"
        )
    elif prev_macd > prev_signal and curr_macd < curr_signal:
        send_telegram(
            f"📉 <b>デッドクロス（売りシグナル）</b>\n"
            f"USD/JPY | {timestamp} UTC\n"
            f"価格: {price:.3f} 円\n"
            f"⬇️ MACDがシグナルを上から下に突き抜けました"
        )
    else:
        print("→ クロスなし")

if __name__ == "__main__":
    try:
        check_crossover()
    except Exception as e:
        print(f"⚠️ エラー（スキップ）: {e}")
