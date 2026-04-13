"""
Agent 4: Backtesting
Uses pure Pandas to validate trading strategies against historical data.
"""

from agents.base_agent import BaseAgent
from config import BACKTEST_CONFIG
from database.db_manager import db
from database.models import MarketData
import pandas as pd

class BacktestingAgent(BaseAgent):
    def __init__(self):
        super().__init__("Backtesting")
        self.session = None

    def initialize(self) -> bool:
        try:
            self.session = db.get_session()
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False

    def execute(self, ticker: str, start_date=None, **kwargs) -> dict:
        """
        Runs a standard backtest on the given ticker using EMA fast/slow crossover 
        as a baseline strategy via Pandas.
        """
        if not self.session:
            self.initialize()
            
        start_date = start_date or BACKTEST_CONFIG["start_date"]
        self.logger.info(f"Running backtest for {ticker} from {start_date}")
        
        try:
            # 1. Fetch data
            query = self.session.query(MarketData)\
                .filter(MarketData.ticker == ticker)\
                .filter(MarketData.date >= start_date)\
                .order_by(MarketData.date.asc())
            
            df = pd.read_sql(query.statement, db.engine)
            
            if len(df) < 200: # Need enough data for EMAs
                return {"success": False, "error": "Insufficient data for backtesting"}
                
            df.set_index('date', inplace=True)
            
            # 2. Strategy: Setup Golden Cross / Death Cross as a baseline
            df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
            df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
            
            # Generate signals: 1 for Buy, -1 for Sell
            df['Signal'] = 0
            df.loc[df['EMA_21'] > df['EMA_50'], 'Signal'] = 1
            df.loc[df['EMA_21'] <= df['EMA_50'], 'Signal'] = 0
            
            # Daily returns
            df['Daily_Return'] = df['close'].pct_change()
            
            # Strategy returns (shifted by 1 to represent entering at close of signal day)
            df['Strategy_Return'] = df['Signal'].shift(1) * df['Daily_Return']
            
            # Account for transaction costs on signal swaps
            df['Trades'] = df['Signal'].diff().abs()
            transaction_cost = BACKTEST_CONFIG["transaction_cost_pct"]
            df['Strategy_Return'] -= df['Trades'] * transaction_cost
            
            # 3. Calculate portfolio metrics
            df['Equity_Curve'] = (1 + df['Strategy_Return'].fillna(0)).cumprod() * BACKTEST_CONFIG["initial_capital"]
            
            total_return_pct = (df['Equity_Curve'].iloc[-1] / BACKTEST_CONFIG["initial_capital"] - 1) * 100
            
            # Win rate (days with positive strategy return out of invested days)
            invested_days = df[df['Signal'].shift(1) == 1]
            win_days = invested_days[invested_days['Strategy_Return'] > 0]
            win_rate_pct = len(win_days) / len(invested_days) * 100 if len(invested_days) > 0 else 0
            
            # Drawdown
            df['Peak'] = df['Equity_Curve'].cummax()
            df['Drawdown'] = (df['Equity_Curve'] - df['Peak']) / df['Peak'] * 100
            max_drawdown_pct = abs(df['Drawdown'].min())
            
            # Sharpe Ratio
            risk_free_rate = 0.05 / 252 # Assumed 5% annual risk free rate
            excess_return = df['Strategy_Return'] - risk_free_rate
            sharpe_ratio = (excess_return.mean() / excess_return.std()) * (252 ** 0.5) if excess_return.std() != 0 else 0
            
            total_trades = df['Trades'].sum() / 2 # entry and exit counts as 1 trade roughly

            # Profit Factor
            gross_profits = df[df['Strategy_Return'] > 0]['Strategy_Return'].sum()
            gross_losses = abs(df[df['Strategy_Return'] < 0]['Strategy_Return'].sum())
            profit_factor = gross_profits / gross_losses if gross_losses != 0 else 0

            result = {
                "ticker": ticker,
                "strategy": "EMA_21_50_Cross (Pandas)",
                "start_balance": int(BACKTEST_CONFIG["initial_capital"]),
                "end_balance": int(df['Equity_Curve'].iloc[-1]),
                "total_return_pct": float(total_return_pct),
                "win_rate_pct": float(win_rate_pct),
                "max_drawdown_pct": float(max_drawdown_pct),
                "sharpe_ratio": float(sharpe_ratio),
                "total_trades": int(total_trades),
                "profit_factor": float(profit_factor)
            }
            
            self.logger.info(f"Backtest complete for {ticker}. Return: {result['total_return_pct']:.2f}%")
            return result
            
        except Exception as e:
            self.logger.error(f"Backtest error on {ticker}: {e}")
            return {"success": False, "error": str(e)}

    def __del__(self):
        if self.session:
            self.session.close()
