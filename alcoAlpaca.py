# ******************************************
# * alcoAlpaca.py
# * @brief Daily paper-trading check using MA crossover (% of capital)
# ******************************************/

import os
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd

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

def fetch_daily_ma(symbol):
    '''
    @brief Fetch daily bars and compute moving averages
    @param symbol Stock ticker symbol
    @return dict with 'ma_fast' and 'ma_slow' or None if insufficient data
    '''
    
    bars = api.get_bars(symbol, TimeFrame.Day, limit=BAR_LIMIT, adjustment='raw').df

    if isinstance(bars.index, pd.MultiIndex):
        df = bars.xs(symbol, level=1)
    else:
        df = bars

    if df.empty or len(df) <  SLOW:
        return None

    close = df['close']
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
    for sym in TICKERS:
        mas = fetch_daily_ma(sym)
        if mas is None:
            print(f"{sym}: insufficient data. Skipping.")
            continue

        pos_qty = get_current_position(sym)
        last_price = get_last_price(sym)
        buy_qty = int((POSITION_PERCENT * equity) // last_price)

        mf, ms = mas["ma_fast"], mas["ma_slow"]
        try:
            if mf > ms and pos_qty == 0 and buy_qty > 0:
                print(f"{sym}: MA{FAST}({mf:.2f}) > MA{SLOW}({ms:.2f}); BUY {buy_qty}")
                api.submit_order(symbol=sym, qty=buy_qty, side="buy",
                                 type="market", time_in_force="day")

            elif mf < ms and pos_qty > 0:
                print(f"{sym}: MA{FAST}({mf:.2f}) < MA{SLOW}({ms:.2f}); SELL {pos_qty}")
                api.submit_order(symbol=sym, qty=pos_qty, side="sell",
                                 type="market", time_in_force="day")

            else:
                print(f"{sym}: no action (MA{FAST}={mf:.2f}, MA{SLOW}={ms:.2f}, pos={pos_qty})")

        except Exception as e:
            print(f"{sym}: ERROR placing order → {e}")

if __name__ == "__main__":
    run_daily_check()
