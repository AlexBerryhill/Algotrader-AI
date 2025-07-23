from alpaca_trade_api import REST
from dotenv import load_dotenv
import backtrader as bt
import yfinance as yf
import pandas as pd

class MA_Crossover(bt.Strategy):
    params = (('fast', 50), ('slow', 100),)

    def __init__(self):
        # map each data feed name → (fastMA, slowMA)
        self.mas = {
            d._name: (
                bt.ind.SMA(d.close, period=self.p.fast),
                bt.ind.SMA(d.close, period=self.p.slow)
            )
            for d in self.datas
        }

    def next(self):
        for d in self.datas:
            pos = self.getposition(d).size
            ma_f, ma_s = self.mas[d._name]
            if not pos and ma_f[0] > ma_s[0]:
                self.buy(data=d)
            elif pos and ma_f[0] < ma_s[0]:
                self.close(data=d)

def run_backtest(fast, slow, feeds, starting_cash=10_000):
    cerebro = bt.Cerebro()
    cerebro.broker.set_cash(starting_cash)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=33)
    cerebro.addstrategy(MA_Crossover, fast=fast, slow=slow)
    for feed in feeds.values():
        cerebro.adddata(feed)
    strat = cerebro.run()[0]       # real Strategy instance!
    return strat.broker.getvalue()

if __name__ == '__main__':
    tickers = ['AAPL','MSFT','TSLA']
    raw = yf.download(
        tickers,
        start='2018-01-01', end='2024-01-01',
        auto_adjust=False,
        group_by='ticker', threads=True
    )

    feeds = {}
    for t in tickers:
        df = raw[t][['Open','High','Low','Close','Volume']].copy()
        feeds[t] = bt.feeds.PandasData(dataname=df, name=t)

    fasts = range(10, 101, 10)
    slows = range(100, 301, 50)
    pairs = [(f, s) for f in fasts for s in slows if f < s]

    results = []
    for fast, slow in pairs:
        val = run_backtest(fast, slow, feeds)
        results.append({'fast': fast, 'slow': slow, 'value': val})
        print(f"fast={fast:3d} slow={slow:3d} → {val:,.2f}")

    best = max(results, key=lambda x: x['value'])
    print("\nBEST:", best)

    # rerun best for plotting
    final_val = run_backtest(best['fast'], best['slow'], feeds)
    print(f"Final Value (best params): {final_val:,.2f}")

tickers = ['AAPL', 'MSFT', 'TSLA']
data_feeds = {}

for ticker in tickers:
    df = yf.download(ticker, start='2018-01-01', end='2024-01-01')

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

    data = bt.feeds.PandasData(dataname=df, name=ticker)
    data_feeds[ticker] = data


cerebro = bt.Cerebro()
cerebro.addstrategy(MA_Crossover)
cerebro.broker.set_cash(10000)
cerebro.addsizer(bt.sizers.PercentSizer, percents=33)

for feed in data_feeds.values():
    cerebro.adddata(feed)

initial_cash = cerebro.broker.get_cash()
results = cerebro.run()
final_value = cerebro.broker.getvalue()
print(f"Final Portfolio Value: {final_value:.2f}")
total_return = final_value / initial_cash - 1
years = 6

apr = (1 + total_return) ** (1 / years) - 1
print(f"Average APR: {apr * 100:.2f}%")
cerebro.plot()