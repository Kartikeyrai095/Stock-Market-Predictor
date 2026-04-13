"""
TensorFlow LSTM Model for stock prediction.
"""

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import os
from config import LSTM_CONFIG, MODELS_DIR
from utils.logger import get_logger

logger = get_logger("LSTM_Model")

class StockLSTM:
    def __init__(self, sequence_length=LSTM_CONFIG["lookback_days"], n_features=len(LSTM_CONFIG["features"])):
        self.seq_len = sequence_length
        self.n_features = n_features
        self.model = self._build_model()
        self.model_path = str(MODELS_DIR / "lstm_model.keras")

    def _build_model(self):
        """Builds a stacked LSTM network"""
        model = Sequential([
            Input(shape=(self.seq_len, self.n_features)),
            LSTM(LSTM_CONFIG["lstm_units"][0], return_sequences=True),
            Dropout(LSTM_CONFIG["dropout_rate"]),
            LSTM(LSTM_CONFIG["lstm_units"][1], return_sequences=False),
            Dropout(LSTM_CONFIG["dropout_rate"]),
            Dense(32, activation='relu'),
            Dense(1) # Predicting a single continuous continuous value (e.g. price)
        ])
        
        optimizer = tf.keras.optimizers.Adam(learning_rate=LSTM_CONFIG["learning_rate"])
        # We predict continuous price so MSE loss is standard
        model.compile(optimizer=optimizer, loss='mean_squared_error', metrics=['mae'])
        return model

    def train(self, X_train, y_train, X_val, y_val):
        """Trains the model with early stopping"""
        logger.info(f"Training LSTM with input shape: {X_train.shape}")
        
        early_stopping = EarlyStopping(
            monitor='val_loss', 
            patience=LSTM_CONFIG["patience"], 
            restore_best_weights=True
        )
        
        checkpoint = ModelCheckpoint(
            self.model_path, 
            save_best_only=True, 
            monitor='val_loss'
        )

        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=LSTM_CONFIG["epochs"],
            batch_size=LSTM_CONFIG["batch_size"],
            callbacks=[early_stopping, checkpoint],
            verbose=1
        )
        
        logger.info("LSTM Training completed.")
        return history

    def predict(self, X):
        """Generates predictions"""
        return self.model.predict(X)

    def load(self):
        """Load pretrained model"""
        if os.path.exists(self.model_path):
            self.model = tf.keras.saving.load_model(self.model_path)
            logger.info("Loaded LSTM model from disk")
            return self.model
        return None
