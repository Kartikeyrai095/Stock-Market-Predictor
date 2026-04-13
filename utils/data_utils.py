"""
Data fetching and transformation utility module.
Provides static helpers for yfinance, nsepython, dates, and normalization.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Union, List
from utils.logger import get_logger

try:
    from nsepython import nse_quote_meta
    HAS_NSEPYTHON = True
except ImportError:
    HAS_NSEPYTHON = False

logger = get_logger("DataUtils")

def fetch_historical_daily(ticker: str, period: str = "5y") -> pd.DataFrame:
    """
    Fetch historical daily data from Yahoo Finance.
    
    Args:
        ticker (str): Ticker symbol. Needs '.NS' or '.BO' suffix.
        period (str): Valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
        
    Returns:
        pd.DataFrame with DataTimeIndex and columns [Open, High, Low, Close, Volume, Adj Close]
    """
    logger.info(f"Fetching historical data for {ticker} (Period: {period})")
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        
        if df.empty:
            logger.warning(f"No data found for {ticker}")
            return df
            
        # Clean up columns depending on what yfinance returns
        if "Dividends" in df.columns:
            df.drop(columns=["Dividends"], inplace=True)
        if "Stock Splits" in df.columns:
            df.drop(columns=["Stock Splits"], inplace=True)
            
        return df
        
    except Exception as e:
        logger.error(f"YFinance error for {ticker}: {str(e)}")
        return pd.DataFrame()

def fetch_live_quote(base_ticker: str) -> dict:
    """
    Fetch near-live stock quote strictly using NSEPython (no '.NS' suffix required).
    
    Args:
        base_ticker (str): Raw stock symbol, e.g., 'RELIANCE'
    """
    if not HAS_NSEPYTHON:
        logger.warning("nsepython not installed, falling back to yfinance (delayed)")
        return fetch_live_quote_yf(f"{base_ticker}.NS")

    try:
        meta = nse_quote_meta(base_ticker)
        # Parse standard response from NSE
        if not meta or 'priceInfo' not in meta:
            return {}
            
        p_info = meta['priceInfo']
        return {
            "symbol": meta.get('symbol', base_ticker),
            "timestamp": meta.get('lastUpdateTime', ''),
            "lastPrice": p_info.get('lastPrice', 0.0),
            "closePrice": p_info.get('close', 0.0),
            "open": p_info.get('open', 0.0),
            "intraDayHighLow": p_info.get('intraDayHighLow', {}),
            "pChange": p_info.get('pChange', 0.0),
            "lastUpdateTime": meta.get('lastUpdateTime', '')
        }
    except Exception as e:
        logger.error(f"nsepython error for {base_ticker}: {str(e)}")
        return fetch_live_quote_yf(f"{base_ticker}.NS") # Fallback

def fetch_live_quote_yf(ticker: str) -> dict:
    """Fallback using Yahoo finance for near-live (delayed)"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        return {
            "symbol": ticker.replace(".NS", ""),
            "lastPrice": info.last_price,
            "closePrice": info.previous_close,
            "open": info.open,
            "pChange": ((info.last_price / info.previous_close) - 1) * 100 if info.previous_close else 0.0
        }
    except Exception as e:
        logger.error(f"YF Live Quote Error for {ticker}: {e}")
        return {}

def normalize_features(df: pd.DataFrame, columns_to_normalize: List[str]) -> pd.DataFrame:
    """
    Applies Min-Max scaling to specified columns in a DataFrame.
    Note: For production ML, you should fit the scaler on the train set only,
    then transform test sets. This is just a basic utility.
    """
    df_norm = df.copy()
    for col in columns_to_normalize:
        if col in df_norm.columns:
            min_val = df_norm[col].min()
            max_val = df_norm[col].max()
            if max_val > min_val:
                df_norm[f"{col}_norm"] = (df_norm[col] - min_val) / (max_val - min_val)
            else:
                df_norm[f"{col}_norm"] = 0.5
    return df_norm

def create_sequences(data: np.ndarray, seq_length: int, forecast_steps: int = 1):
    """
    Creates overlapping windows (sequences) for time-series forecasting (LSTM/Transformer).
    
    Args:
        data: numpy array of shape (num_samples, num_features)
        seq_length: e.g., 60 days of lookback
        forecast_steps: e.g., predict 5 days ahead (we take the final day's price usually)
        
    Returns:
        X: (num_samples - seq_length - forecast_steps, seq_length, num_features)
        y: target array
    """
    X = []
    y = []

    # Assuming target is the first column (e.g. Close Price)
    target_idx = 0 

    for i in range(len(data) - seq_length - forecast_steps + 1):
        X.append(data[i : i + seq_length])
        
        # Target is the value *after* the sequence + forecast steps
        # E.g. If predicting 5 days out, y is data[i + seq_length + 4]
        target_value = data[i + seq_length + forecast_steps - 1, target_idx]
        y.append(target_value)

    return np.array(X), np.array(y)
