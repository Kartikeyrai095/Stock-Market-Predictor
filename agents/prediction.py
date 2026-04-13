"""
Agent 3: Prediction Agent
Uses LSTM, Transformer, and RL models to make predictions based on processed data.
Logs predictions to the database for self-learning.
"""

from agents.base_agent import BaseAgent
from models.lstm_model import StockLSTM
from models.transformer_model import StockTransformer
from models.rl_agent import RLAgent
from utils.data_utils import create_sequences
from database.db_manager import db
from database.models import Prediction
import numpy as np

class PredictionAgent(BaseAgent):
    def __init__(self):
        super().__init__("Prediction")
        self.lstm = StockLSTM()
        self.transformer = StockTransformer()
        self.rl = RLAgent()
        self.session = None
        self.models_loaded = False

    def initialize(self) -> bool:
        try:
            self.session = db.get_session()
            self.lstm.load()
            self.transformer.load()
            self.rl.load()
            self.models_loaded = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False

    def execute(self, df, ticker: str, **kwargs) -> dict:
        """
        Takes a processed dataframe (from DataProcessingAgent) and generates predictions.
        """
        if not self.models_loaded:
            self.initialize()
            
        if df is None or df.empty or len(df) < 60:
            self.logger.warning(f"Not enough data to predict for {ticker}")
            return {"predicted": False, "reason": "Insufficient Data"}

        self.logger.info(f"Generating predictions for {ticker}")
        
        try:
            # We assume df has been normalized by DataProcessingAgent.
            # Convert to numpy array
            data_arr = df.values
            
            # Predict uses the last 'seq_len' days
            seq_len = 60
            recent_data = data_arr[-seq_len:]
            
            # Shape for LSTM/Transformer: (1, seq_len, n_features)
            recent_data_reshaped = np.expand_dims(recent_data, axis=0)
            
            predictions = {
                "LSTM": None,
                "Transformer": None,
                "RL_Action": None
            }

            # 1. LSTM Prediction
            if self.lstm.model is not None:
                lstm_pred = self.lstm.predict(recent_data_reshaped)
                predictions["LSTM"] = float(lstm_pred[0][0])

            # 2. Transformer Prediction
            if self.transformer.model is not None:
                tf_pred = self.transformer.predict(recent_data_reshaped)
                predictions["Transformer"] = float(tf_pred[0][0])
                
            # 3. RL Prediction (takes the single most recent row)
            if self.rl.model is not None:
                latest_obs = data_arr[-1]
                rl_action = self.rl.predict_action(latest_obs)
                predictions["RL_Action"] = int(rl_action) # 0=Buy, 1=Sell, 2=Hold
                
            # Calculate an ensemble prediction
            # Default weights: 60% Transformer, 40% LSTM (assuming Transformer is better suited long term)
            ensemble_pred = None
            if predictions["LSTM"] and predictions["Transformer"]:
                ensemble_pred = (predictions["Transformer"] * 0.6) + (predictions["LSTM"] * 0.4)
                predictions["Ensemble"] = ensemble_pred
                
                # Determine direction assuming predict contains future price logic
                current_scaled_price = data_arr[-1][0] # Assuming Close is column 0
                direction = "UP" if ensemble_pred > current_scaled_price else "DOWN"
                
                # Save prediction to DB for later scoring
                self._save_prediction(ticker, "Ensemble", ensemble_pred, direction, 0.75) # 0.75 is dummy confidence

            return {
                "ticker": ticker,
                "predicted": True,
                "results": predictions
            }

        except Exception as e:
            self.logger.error(f"Error predicting for {ticker}: {e}")
            return {"predicted": False, "reason": str(e)}

    def _save_prediction(self, ticker, model_name, price, direction, confidence):
        if not self.session:
            return
            
        record = Prediction(
            ticker=ticker,
            model_name=model_name,
            forecast_days=5,
            predicted_price=price,
            predicted_direction=direction,
            confidence=confidence
        )
        self.session.add(record)
        self.session.commit()

    def __del__(self):
        if self.session:
            self.session.close()
