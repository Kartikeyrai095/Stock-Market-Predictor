"""
Agent 1: Data Collection
Responsible for fetching historical and live stock data, options, and mutual funds.
Saves data into the SQLite database or caching layer.
"""

from agents.base_agent import BaseAgent
from config import ALL_STOCKS, INDICES
from utils.data_utils import fetch_historical_daily, fetch_live_quote
from database.db_manager import db
from database.models import Asset, MarketData
from sqlalchemy.orm import Session
import pandas as pd
from datetime import datetime

class DataCollectionAgent(BaseAgent):
    
    def __init__(self):
        super().__init__("DataCollection")
        self.session = None

    def initialize(self) -> bool:
        try:
            self.session = db.get_session()
            self._ensure_assets_exist()
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False

    def _ensure_assets_exist(self):
        """Seed the Assets table with the universe if it's empty"""
        count = self.session.query(Asset).count()
        if count == 0:
            self.logger.info("Seeding Assets table with stock universe...")
            for ticker in ALL_STOCKS:
                asset = Asset(
                    ticker=ticker,
                    name=ticker.replace(".NS", ""),
                    asset_type="Equity",
                    sector="Unknown" # Can be updated later with yf.info
                )
                self.session.add(asset)
                
            for name, ticker in INDICES.items():
                asset = Asset(
                    ticker=ticker,
                    name=name,
                    asset_type="Index",
                    sector="Market"
                )
                self.session.add(asset)
            self.session.commit()

    def execute(self, mode="historical", subset=None, **kwargs) -> dict:
        """
        Main execution payload.
        Args:
            mode: 'historical' (5y backfill), 'update' (recent days), 'live' (current quote)
            subset: List of tickers to process, defaults to ALL_STOCKS
        """
        if not self.session:
            self.initialize()
            
        tickers_to_process = subset if subset else ALL_STOCKS
        results = {"successful": 0, "failed": 0, "mode": mode}
        
        self.logger.info(f"Starting Data Collection. Mode: {mode}. Tickers: {len(tickers_to_process)}")
        
        for ticker in tickers_to_process:
            try:
                if mode in ["historical", "update"]:
                    period = "5y" if mode == "historical" else "1mo"
                    df = fetch_historical_daily(ticker, period=period)
                    
                    if not df.empty:
                        self._save_historical_to_db(ticker, df)
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                        
                elif mode == "live":
                    # Real-time quote check
                    base_ticker = ticker.replace(".NS", "")
                    quote = fetch_live_quote(base_ticker)
                    if quote:
                        # For live we might just want to store in a fast cache 
                        # rather than DB, but we return it here for now
                        pass
                        
            except Exception as e:
                self.logger.error(f"Error processing {ticker}: {e}")
                results["failed"] += 1
                
        self.logger.info(f"Data Collection complete. Success: {results['successful']}, Failed: {results['failed']}")
        return results

    def _save_historical_to_db(self, ticker: str, df: pd.DataFrame):
        """Saves or updates daily market data in SQLite"""
        # We only want to insert new rows to avoid duplicates
        # First, get the latest date we have for this ticker
        latest_record = self.session.query(MarketData)\
            .filter(MarketData.ticker == ticker)\
            .order_by(MarketData.date.desc())\
            .first()
            
        latest_date = latest_record.date if latest_record else None
        
        new_records = []
        for index, row in df.iterrows():
            # index is typically pd.Timestamp with timezone info
            # Convert to naive datetime for SQLite
            naive_date = index.tz_convert(None).to_pydatetime()
            
            if latest_date is None or naive_date > latest_date:
                record = MarketData(
                    ticker=ticker,
                    date=naive_date,
                    open=float(row.get('Open', 0)),
                    high=float(row.get('High', 0)),
                    low=float(row.get('Low', 0)),
                    close=float(row.get('Close', 0)),
                    volume=int(row.get('Volume', 0)),
                    adjusted_close=float(row.get('Adj Close', row.get('Close', 0)))
                )
                new_records.append(record)
                
        if new_records:
            self.session.bulk_save_objects(new_records)
            self.session.commit()
            self.logger.debug(f"Inserted {len(new_records)} new records for {ticker}")

    def __del__(self):
        if self.session:
            self.session.close()
