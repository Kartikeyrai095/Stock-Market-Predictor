"""
Technical Indicators Calculation Module.
Calculates a standardized set of indicators for ML inputs using the `ta` library.
"""

import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator, ROCIndicator
from ta.trend import EMAIndicator, ADXIndicator, CCIIndicator, MACD
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice, MFIIndicator, ChaikinMoneyFlowIndicator
from utils.logger import get_logger

logger = get_logger("Indicators")

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies the full suite of technical indicators needed for the Prediction Agent.
    """
    if df is None or df.empty:
        logger.warning("Empty dataframe provided for indicators.")
        return df

    try:
        # Require essential columns
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                return df

        # Make a copy to avoid SettingWithCopyWarning if it's a slice
        data = df.copy()

        # Momentum
        data["RSI"] = RSIIndicator(close=data["Close"], window=14).rsi()
        macd = MACD(close=data["Close"], window_slow=26, window_fast=12, window_sign=9)
        data["MACD"] = macd.macd()
        data["MACD_signal"] = macd.macd_signal()
        data["MACD_hist"] = macd.macd_diff()
        stoch = StochasticOscillator(high=data["High"], low=data["Low"], close=data["Close"], window=14, smooth_window=3)
        data["Stoch_K"] = stoch.stoch()
        data["Stoch_D"] = stoch.stoch_signal()
        data["CCI"] = CCIIndicator(high=data["High"], low=data["Low"], close=data["Close"], window=20).cci()
        data["Williams_R"] = WilliamsRIndicator(high=data["High"], low=data["Low"], close=data["Close"], lbp=14).williams_r()
        data["ROC"] = ROCIndicator(close=data["Close"], window=10).roc()
        
        # Trend / Moving Averages
        data["EMA_9"] = EMAIndicator(close=data["Close"], window=9).ema_indicator()
        data["EMA_21"] = EMAIndicator(close=data["Close"], window=21).ema_indicator()
        data["EMA_50"] = EMAIndicator(close=data["Close"], window=50).ema_indicator()
        data["EMA_200"] = EMAIndicator(close=data["Close"], window=200).ema_indicator()
        adx = ADXIndicator(high=data["High"], low=data["Low"], close=data["Close"], window=14)
        data["ADX"] = adx.adx()
        
        # Volatility
        bb = BollingerBands(close=data["Close"], window=20, window_dev=2)
        data["BB_upper"] = bb.bollinger_hband()
        data["BB_middle"] = bb.bollinger_mavg()
        data["BB_lower"] = bb.bollinger_lband()
        data["ATR"] = AverageTrueRange(high=data["High"], low=data["Low"], close=data["Close"], window=14).average_true_range()
        
        # Volume
        data["OBV"] = OnBalanceVolumeIndicator(close=data["Close"], volume=data["Volume"]).on_balance_volume()
        # VWAP typically uses typical price over a cumulative period, the ta library provides it
        data["VWAP"] = VolumeWeightedAveragePrice(high=data["High"], low=data["Low"], close=data["Close"], volume=data["Volume"], window=14).volume_weighted_average_price()
        data["MFI"] = MFIIndicator(high=data["High"], low=data["Low"], close=data["Close"], volume=data["Volume"], window=14).money_flow_index()

        # Fill NaNs created by lagging indicators (or drop them later in DataProcessingAgent)
        return data

    except Exception as e:
        logger.error(f"Failed to calculate indicators: {str(e)}")
        return df
