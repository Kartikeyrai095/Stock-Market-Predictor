"""
Transformer Model implementation for time series.
"""
import tensorflow as tf
from tensorflow.keras import layers
import os
from config import TRANSFORMER_CONFIG, MODELS_DIR
from utils.logger import get_logger

logger = get_logger("Transformer_Model")

def transformer_encoder(inputs, head_size, num_heads, ff_dim, dropout=0):
    """A standard Transformer Encoder layer"""
    # Attention and Normalization
    x = layers.MultiHeadAttention(key_dim=head_size, num_heads=num_heads, dropout=dropout)(inputs, inputs)
    x = layers.Dropout(dropout)(x)
    x = layers.LayerNormalization(epsilon=1e-6)(x)
    res = x + inputs

    # Feed Forward Part
    x = layers.Conv1D(filters=ff_dim, kernel_size=1, activation="relu")(res)
    x = layers.Dropout(dropout)(x)
    x = layers.Conv1D(filters=inputs.shape[-1], kernel_size=1)(x)
    x = layers.LayerNormalization(epsilon=1e-6)(x)
    return x + res

class StockTransformer:
    def __init__(self, sequence_length=TRANSFORMER_CONFIG["lookback_days"], n_features=26): # 26 features by default
        self.seq_len = sequence_length
        self.n_features = n_features
        self.model = self._build_model()
        self.model_path = str(MODELS_DIR / "transformer_model.keras")

    def _build_model(self):
        inputs = tf.keras.Input(shape=(self.seq_len, self.n_features))
        x = inputs
        
        for _ in range(TRANSFORMER_CONFIG["num_encoder_layers"]):
            x = transformer_encoder(
                x, 
                TRANSFORMER_CONFIG["d_model"], 
                TRANSFORMER_CONFIG["num_heads"], 
                TRANSFORMER_CONFIG["dff"], 
                TRANSFORMER_CONFIG["dropout_rate"]
            )

        x = layers.GlobalAveragePooling1D(data_format="channels_first")(x)
        for dim in [64, 32]:
            x = layers.Dense(dim, activation="relu")(x)
            x = layers.Dropout(TRANSFORMER_CONFIG["dropout_rate"])(x)
            
        outputs = layers.Dense(1)(x)
        
        model = tf.keras.Model(inputs, outputs)
        optimizer = tf.keras.optimizers.Adam(learning_rate=TRANSFORMER_CONFIG["learning_rate"])
        model.compile(loss="mean_squared_error", optimizer=optimizer, metrics=["mae"])
        return model

    def train(self, X_train, y_train, X_val, y_val):
        logger.info(f"Training Transformer with input shape: {X_train.shape}")
        
        callbacks = [
            tf.keras.callbacks.EarlyStopping(patience=TRANSFORMER_CONFIG["patience"], restore_best_weights=True),
            tf.keras.callbacks.ModelCheckpoint(self.model_path, save_best_only=True)
        ]

        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=TRANSFORMER_CONFIG["epochs"],
            batch_size=TRANSFORMER_CONFIG["batch_size"],
            callbacks=callbacks,
            verbose=1
        )
        return history

    def predict(self, X):
        return self.model.predict(X)

    def load(self):
        if os.path.exists(self.model_path):
            self.model = tf.keras.saving.load_model(self.model_path)
            logger.info("Loaded Transformer model from disk")
            return self.model
        return None
