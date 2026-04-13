"""
Stock Market Predictor - Main Orchestrator
Coordinates all 10 agents to run the complete data -> prediction -> strategy pipeline.
"""

from utils.logger import get_logger
from agents.data_collection import DataCollectionAgent
from agents.data_processing import DataProcessingAgent
from agents.prediction import PredictionAgent
from agents.news_intelligence import NewsIntelligenceAgent
from agents.backtesting import BacktestingAgent
from agents.strategy import StrategyAgent
from agents.risk_management import RiskManagementAgent
from agents.recommendation import RecommendationAgent
from agents.self_learning import SelfLearningAgent
from agents.continuous_learning import ContinuousLearningAgent
from config import NIFTY_50
import time
import threading
import sys
import os

logger = get_logger("Orchestrator")

class StockMarketPredictorSystem:
    def __init__(self):
        self.logger = logger
        self.logger.info("Initializing multi-agent system components...")
        
        # Instantiate agents
        self.agent_data_col = DataCollectionAgent()
        self.agent_data_proc = DataProcessingAgent()
        self.agent_predict = PredictionAgent()
        self.agent_news = NewsIntelligenceAgent()
        self.agent_backtest = BacktestingAgent()
        self.agent_strategy = StrategyAgent()
        self.agent_risk = RiskManagementAgent()
        self.agent_rec = RecommendationAgent()
        self.agent_self_learn = SelfLearningAgent()
        self.agent_continuous = ContinuousLearningAgent(orchestrator=self)
        
        self._initialize_all()

    def _initialize_all(self):
        """Initializes dependencies and DB connections for all agents"""
        agents = [
            self.agent_data_col, self.agent_data_proc, self.agent_predict,
            self.agent_news, self.agent_backtest, self.agent_strategy,
            self.agent_risk, self.agent_rec, self.agent_self_learn,
            self.agent_continuous
        ]
        
        for agent in agents:
            if not agent.initialize():
                self.logger.error(f"Failed to initialize {agent.name}. Exiting.")
                sys.exit(1)
        self.logger.info("All 10 agents initialized successfully.")

    def run_full_pipeline(self, tickers=NIFTY_50[:5]): 
        """
        Runs the standard daily analysis pipeline for a given set of tickers.
        Note: Capped at 5 tickers by default here for demo speed.
        """
        self.logger.info(f"========== Starting Full Pipeline for {len(tickers)} assets ==========")
        
        # Step 1: Broad Market Sentiment
        news_result = self.agent_news.run()
        sentiment_data = news_result.get("data", {})
        
        # Step 2: Fetch overall data
        self.agent_data_col.run(mode="update", subset=tickers)
        
        # Process each ticker individually
        for ticker in tickers:
            self.logger.info(f"--- Processing {ticker} ---")
            
            # Step 3: Process Data
            proc_result = self.agent_data_proc.run(ticker=ticker)
            if not proc_result["success"] or proc_result["data"] is None or proc_result["data"].get("data") is None:
                self.logger.warning(f"Data processing failed for {ticker}. Skipping.")
                continue
                
            df = proc_result["data"]["data"]
            
            # Step 4: ML Prediction
            pred_result = self.agent_predict.run(df=df, ticker=ticker)
            pred_data = pred_result.get("data", {})
            
            # Step 5: Strategy Generation
            strat_result = self.agent_strategy.run(
                df=df, 
                ticker=ticker, 
                prediction_data=pred_data,
                sentiment_data=sentiment_data
            )
            
            if not strat_result["success"] or strat_result["data"].get("action") == "HOLD":
                self.logger.info(f"No actionable strategy for {ticker}.")
                continue
                
            raw_strategy = strat_result["data"]
            
            # Step 6: Risk Management
            # Assume local portfolio size of 10 Lakhs (1,000,000 INR)
            risk_result = self.agent_risk.run(strategy=raw_strategy, current_portfolio_value=1000000)
            
            # Step 7: Final Recommendation
            # Risk agent returns {"passed": True/False, "strategy": {...}} inside result["data"]
            risk_data = risk_result.get("data", {})
            if risk_data and risk_data.get("passed"):
                 self.agent_rec.run(risk_data=risk_data)
                 
        self.logger.info("========== Pipeline Execution Complete ==========")

    def run_self_learning_cycle(self):
        """Triggered by continuous learning daemon to grade past predictions"""
        self.agent_self_learn.run()
        
    def start_background_daemon(self):
        self.agent_continuous.run(mode="start")

def main():
    if not os.path.exists('data'):
        os.makedirs('data')
        
    system = StockMarketPredictorSystem()
    
    # Check args. If 'dashboard', skip terminal pipeline and let Flask run
    if len(sys.argv) > 1 and sys.argv[1] == "dashboard":
        logger.info("Starting up without running pipeline immediately because web server is taking over.")
        return

    # Start the continuous background monitoring
    system.start_background_daemon()
    
    # Run a full pass on top 5 NIFTY stocks as initial seed
    seed_stocks = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]
    
    try:
        system.run_full_pipeline(tickers=seed_stocks)
        
        logger.info("\nPipeline finished. The dashboard runs on a separate process.")
        logger.info("Use: `python dashboard/app.py` to view results.")
        
        # Keep main thread alive for daemon
        while True:
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        system.agent_continuous.run(mode="stop")
        
if __name__ == "__main__":
    main()
