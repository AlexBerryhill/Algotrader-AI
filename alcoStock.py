from alpaca_trade_api import REST
from dotenv import load_dotenv
import backtrader as bt
import yfinance as yf
import pandas as pd
import os

class MA_Crossover(bt.Strategy):
    params = (('fast', 50), ('slow', 200),)

    def __init__(self):
        self.moving_averages = {}
        for d in self.datas:
            ma_fast = bt.ind.SMA(d.close, period=self.p.fast)
            ma_slow = bt.ind.SMA(d.close, period=self.p.slow)
            self.moving_averages[d._name] = (ma_fast, ma_slow)

    def next(self):
        for i, d in enumerate(self.datas):
            pos = self.getposition(d).size
            ma_fast, ma_slow = self.moving_averages[d._name]

            if not pos and ma_fast[0] > ma_slow[0]:
                self.buy(data=d)
            elif pos and ma_fast[0] < ma_slow[0]:
                self.close(data=d)


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


#  Optimization
# do_optimization = False

# if do_optimization:
#     cerebro = bt.Cerebro(optreturn=False)
#     cerebro.optstrategy(
#         MA_Crossover,
#         fast=range(20, 100, 10),
#         slow=range(100, 300, 50),
#     )
#     cerebro.adddata(data)
#     cerebro.broker.set_cash(10000)
#     cerebro.addsizer(bt.sizers.PercentSizer, percents=100)
#     opt_results = cerebro.run(maxcpus=4)
    
#     for strat in opt_results:
#         strategy_instance = strat[0]
#         start_cash = strategy_instance.broker.startingcash
#         end_value = strategy_instance.broker.getvalue()

#         data = strategy_instance.datas[0]
#         start_date = data.datetime.date(0)
#         end_date = data.datetime.date(-1)
#         years = (end_date - start_date).days / 365.25

#         total_return = end_value / start_cash
#         apr = (total_return) ** (1 / years) - 1

#         print(f"Params: fast={strategy_instance.params.fast}, slow={strategy_instance.params.slow} => APR: {apr*100:.2f}%")
# else:
#     cerebro = bt.Cerebro()
#     cerebro.addstrategy(MA_Crossover)
#     cerebro.adddata(data)
#     cerebro.broker.set_cash(10000)
#     cerebro.addsizer(bt.sizers.PercentSizer, percents=100)
#     initial_cash = cerebro.broker.get_cash()
#     results = cerebro.run()
#     final_value = cerebro.broker.getvalue()
#     print(f"Final Portfolio Value: {final_value:.2f}")
#     total_return = final_value / initial_cash - 1
#     years = 6
#     apr = (1 + total_return) ** (1 / years) - 1
#     print(f"Average APR: {apr * 100:.2f}%")
#     cerebro.plot()
print("Backtest completed successfully.")

    
# # === Step 4: Alpaca Live Trade Example ===
# load_dotenv()
# api_key = os.getenv('ALPACA_API_KEY')
# secret_key = os.getenv('ALPACA_SECRET_KEY')

# if api_key and secret_key:
#     alpaca = REST(api_key, secret_key, base_url='https://paper-api.alpaca.markets')
#     alpaca.submit_order(
#         symbol='AAPL',
#         qty=10,
#         side='buy',
#         type='market',
#         time_in_force='gtc'
#     )
#     print("Market order submitted to Alpaca.")
# else:
#     print("Alpaca API keys not found in .env.")
