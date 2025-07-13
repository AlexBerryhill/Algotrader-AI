# ******************************************
# * alcoAlpaca.py
# * @author Alex Berryhill
# * @brief Live paper‐trading loop using MA crossover
# ******************************************/

import os
import time
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd

MINUTE = 60  # seconds in a minute
HOUR = MINUTE*60  # seconds in an hour

# 1) Load Alpaca paper‐API credentials
load_dotenv()  # expects .env with APCA_API_KEY_ID, APCA_API_SECRET_KEY
API_KEY    = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")
BASE_URL   = os.getenv(
    "APCA_API_BASE_URL",
    "https://paper-api.alpaca.markets"
)

api = REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

# 2) Strategy parameters & universe
TICKERS = ["AAPL", "MSFT", "TSLA"]
FAST, SLOW = 50, 100          # Params from testing
BAR_LIMIT = 200               # how many minutes of history

def fetch_latest_ma(symbol):
    """
    @brief Pull the last BAR_LIMIT one‐minute bars & compute MA50/MA100
    @param[in] symbol Ticker symbol
    @return dict with 'ma_fast', 'ma_slow' or None if insufficient data
    """
    bars = api.get_bars(
        symbol,
        TimeFrame.Minute,
        limit=BAR_LIMIT,
        adjustment='raw'
    ).df

    # Unwrap MultiIndex if present
    if isinstance(bars.index, pd.MultiIndex):
        df = bars.xs(symbol, level=1)
    else:
        df = bars

    # 1) No data at all?
    if df.empty:
        return None

    # 2) Not enough history for your slow MA?
    if len(df) < SLOW:
        return None

    # 3) Figure out real 'close' column name
    cols = {c.lower(): c for c in df.columns}
    close_col = cols.get("close")
    if not close_col:
        raise KeyError(f"No close column in bars; got {list(df.columns)}")

    close = df[close_col]
    ma_fast = close.rolling(FAST).mean().iat[-1]
    ma_slow = close.rolling(SLOW).mean().iat[-1]

    return {"ma_fast": ma_fast, "ma_slow": ma_slow}


def run_paper_loop():
    """
    @brief Infinite loop: every minute, compute signals & submit paper orders
    """
    print("Starting paper-trade loop.  Press Ctrl+C to stop.")
    while True:
        for sym in TICKERS:
            mas = fetch_latest_ma(sym)

            # skip if we didn't get enough data
            if mas is None:
                print(f"{sym}: insufficient data (market closed or warmup). Skipping.")
                time.sleep(HOUR)
                continue

            pos_qty = get_current_position(sym)
            mf, ms = mas["ma_fast"], mas["ma_slow"]
            try:
                if mf > ms and pos_qty == 0:
                    print(f"{sym}: MA50({mf:.2f}) > MA100({ms:.2f}); BUY 1")
                    api.submit_order(symbol=sym, qty=1, side="buy",
                                    type="market", time_in_force="day")

                elif mf < ms and pos_qty > 0:
                    print(f"{sym}: MA50({mf:.2f}) < MA100({ms:.2f}); SELL {pos_qty}")
                    api.submit_order(symbol=sym, qty=pos_qty, side="sell",
                                    type="market", time_in_force="day")

                else:
                    print(f"{sym}: no action (MA50={mf:.2f},MA100={ms:.2f},pos={pos_qty})")
            except Exception as e:
                print(f"Error placing order for {sym}: {e}")
                continue

        time.sleep(MINUTE)



def get_current_position(symbol):
    """
    @brief Returns current long qty (0 if flat)
    @param[in] symbol Ticker symbol
    @return int qty
    """
    try:
        pos = api.get_position(symbol)
        return int(pos.qty)
    except Exception:
        return 0

if __name__ == "__main__":
    try:
        run_paper_loop()
    except KeyboardInterrupt:
        print("\nPaper-trade loop stopped by user.")
