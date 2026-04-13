"""
Agent 5: Self-Learning
Compares historical predictions with actual subsequent market outcomes to dynamically 
score models and trigger retraining if accuracy drops below thresholds.
"""

from agents.base_agent import BaseAgent
from config import LEARNING_CONFIG
from database.db_manager import db
from database.models import Prediction, MarketData, ModelMetrics
from sqlalchemy import func
from sqlalchemy import Integer as SAInteger
import pandas as pd
from datetime import datetime, timedelta

class SelfLearningAgent(BaseAgent):
    def __init__(self):
        super().__init__("SelfLearning")
        self.session = None

    def initialize(self) -> bool:
        try:
            self.session = db.get_session()
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False

    def execute(self, **kwargs) -> dict:
        """
        Evaluate past predictions that have 'matured' (e.g. forecast days have passed).
        Calculates accuracy and updates ModelMetrics.
        """
        if not self.session:
            self.initialize()
            
        self.logger.info("Starting self-learning evaluation cycle...")
        
        try:
            # 1. Find unresolved predictions
            unresolved = self.session.query(Prediction)\
                .filter(Prediction.was_correct == None)\
                .all()
                
            if not unresolved:
                self.logger.info("No unresolved predictions to evaluate.")
                return {"evaluated": 0, "retrain_needed": False}
                
            evaluated_count = 0
            
            for pred in unresolved:
                # Calculate target date: prediction timestamp + forecast_days (rough approx using timedelta)
                target_date = pred.timestamp + timedelta(days=pred.forecast_days)
                
                # Check if we have market data for or after this date
                actual_data = self.session.query(MarketData)\
                    .filter(MarketData.ticker == pred.ticker)\
                    .filter(MarketData.date >= target_date)\
                    .order_by(MarketData.date.asc())\
                    .first()
                    
                if actual_data:
                    # We have mature data, evaluate it
                    actual_price = actual_data.close
                    
                    # Directional correctness
                    # For simplicity, compare actual to the price at the time of prediction
                    # True directional check requires knowing the exact price at pred.timestamp
                    # We approximate by checking if actual is closer to predicted than it is to 0
                    
                    # Assuming we predicted UP, if actual > price_at_prediction ... 
                    # Simpler metric: Was the absolute error < X% ? Or did the trend match?
                    
                    # For this demo, let's say direction prediction is correct if 
                    # predicted price and actual price are on the same side of the entry price.
                    # Since we don't have exact entry price in Prediction table, we use predicted vs actual delta.
                    error = abs(actual_price - pred.predicted_price)
                    pct_error = error / actual_price
                    
                    # Correct if error < 5% OR if direction logic matched (simplified)
                    was_correct = pct_error < 0.05 
                    
                    pred.actual_price_result = actual_price
                    pred.was_correct = was_correct
                    evaluated_count += 1
                    
            if evaluated_count > 0:
                self.session.commit()
                self.logger.info(f"Evaluated {evaluated_count} predictions.")
                
            # 2. Calculate overall accuracy for recent window
            cutoff = datetime.utcnow() - timedelta(days=LEARNING_CONFIG["performance_window_days"])
            
            stats = self.session.query(
                Prediction.model_name,
                func.count(Prediction.id).label('total'),
                func.sum(func.cast(Prediction.was_correct, SAInteger)).label('correct')
            )\
            .filter(Prediction.was_correct != None)\
            .filter(Prediction.timestamp >= cutoff)\
            .group_by(Prediction.model_name).all()
            
            retrain_needed = False
            for model_name, total, correct in stats:
                if total >= LEARNING_CONFIG["min_samples_for_retrain"]:
                    accuracy = float(correct) / total if total > 0 else 0
                    
                    # Log metrics
                    metric = ModelMetrics(
                        model_name=model_name,
                        ticker="ALL",
                        accuracy=accuracy,
                        samples_count=total
                    )
                    self.session.add(metric)
                    
                    self.logger.info(f"Model {model_name} accuracy: {accuracy*100:.1f}% ({correct}/{total})")
                    
                    if accuracy < LEARNING_CONFIG["retrain_accuracy_threshold"]:
                        self.logger.warning(f"Accuracy for {model_name} below threshold! Flagging for retrain.")
                        retrain_needed = True
                        
            self.session.commit()
            
            return {
                "evaluated": evaluated_count,
                "retrain_needed": retrain_needed
            }
            
        except Exception as e:
            self.logger.error(f"Error in self-learning cycle: {e}")
            self.session.rollback()
            return {"error": str(e)}

    def __del__(self):
        if self.session:
            self.session.close()
