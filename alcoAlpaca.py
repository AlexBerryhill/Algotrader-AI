# ******************************************
# * alcoAlpaca.py
# * @brief Daily paper-trading check using MA crossover (% of capital)
# ******************************************/

import os
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
from datetime import datetime, timedelta

# === Setup ===
load_dotenv()
API_KEY    = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")
BASE_URL   = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")

api = REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

# === Strategy Params ===
TICKERS = ["AAPL", "MSFT", "TSLA"]
FAST, SLOW = 50, 100
BAR_LIMIT = 200
POSITION_PERCENT = 0.33  # 33% of account equity

def log_data(entries, filename="alco_log.parquet"):
    '''
    @brief Appends structured log entries to a Parquet file
    @param entries List of dicts, one per ticker
    @param filename Name of the parquet log file
    '''
    df = pd.DataFrame(entries)

    if os.path.exists(filename):
        old = pd.read_parquet(filename)
        df = pd.concat([old, df], ignore_index=True)

    df.to_parquet(filename, index=False)


def fetch_daily_ma(symbol):
    '''
    @brief Fetch daily bars and compute moving averages
    @param symbol Stock ticker symbol
    @return dict with 'ma_fast' and 'ma_slow' or None if insufficient data
    '''
    end_date = datetime.now()
    start_date = end_date - timedelta(days=(SLOW * 2))  # Fetch more than needed

    bars = api.get_bars(
        symbol,
        TimeFrame.Day,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        adjustment='raw',
        feed='iex'
    ).df

    if isinstance(bars.index, pd.MultiIndex):
        df = bars.xs(symbol, level=1)
    else:
        df = bars

    if df.empty or len(df) < SLOW:
        return None

    cols = {c.lower(): c for c in df.columns}
    close_col = cols.get("close")
    if not close_col:
        raise KeyError(f"No close column in bars; got {list(df.columns)}")

    close = df[close_col]
    ma_fast = close.rolling(FAST).mean().iat[-1]
    ma_slow = close.rolling(SLOW).mean().iat[-1]
    return {"ma_fast": ma_fast, "ma_slow": ma_slow}


def get_current_position(symbol):
    '''
    @brief Get current position quantity for a symbol
    @param symbol Stock ticker symbol
    @return int quantity (0 if no position)
    '''
    try:
        pos = api.get_position(symbol)
        return int(pos.qty)
    except:
        return 0

def get_equity():
    '''
    @brief Get current account equity
    @return float equity value
    '''
    account = api.get_account()
    return float(account.equity)

def get_last_price(symbol):
    '''
    @brief Get the latest trade price for a symbol
    @return float price
    '''
    quote = api.get_latest_trade(symbol)
    return float(quote.price)

def run_daily_check():
    '''
    @brief Main function to run daily MA crossover check and place orders
    '''
    equity = get_equity()
    log_entries = []
    timestamp = datetime.now().isoformat()

    for sym in TICKERS:
        try:
            mas = fetch_daily_ma(sym)
            if mas is None:
                log_entries.append({
                    "timestamp": timestamp,
                    "symbol": sym,
                    "equity": equity,
                    "message": "Insufficient data",
                    "success": False
                })
                continue

            pos_qty = get_current_position(sym)
            last_price = get_last_price(sym)
            buy_qty = int((POSITION_PERCENT * equity) // last_price)

            mf, ms = mas["ma_fast"], mas["ma_slow"]
            action, signal, success, message = None, None, False, ""

            if mf > ms and pos_qty == 0 and buy_qty > 0:
                signal = "BUY"
                action = f"BUY {buy_qty}"
                api.submit_order(symbol=sym, qty=buy_qty, side="buy",
                                 type="market", time_in_force="day")
                success, message = True, "Order submitted"

            elif mf < ms and pos_qty > 0:
                signal = "SELL"
                action = f"SELL {pos_qty}"
                api.submit_order(symbol=sym, qty=pos_qty, side="sell",
                                 type="market", time_in_force="day")
                success, message = True, "Order submitted"

            else:
                signal = "HOLD"
                action = "None"
                success = True
                message = "No trade needed"

            log_entries.append({
                "timestamp": timestamp,
                "symbol": sym,
                "equity": equity,
                "price": last_price,
                "ma_fast": mf,
                "ma_slow": ms,
                "position": pos_qty,
                "signal": signal,
                "action": action,
                "success": success,
                "message": message
            })

        except Exception as e:
            log_entries.append({
                "timestamp": timestamp,
                "symbol": sym,
                "equity": equity,
                "price": None,
                "ma_fast": None,
                "ma_slow": None,
                "position": None,
                "signal": None,
                "action": None,
                "success": False,
                "message": f"Exception: {e}"
            })

    log_data(log_entries)



if __name__ == "__main__":
    run_daily_check()
