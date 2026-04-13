"""
Reinforcement Learning trading agent using Stable Baselines 3.
Requires a custom Gymnasium environment.
"""

import os
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from config import RL_CONFIG, MODELS_DIR
from utils.logger import get_logger

logger = get_logger("RL_Model")

class StockTradingEnv(gym.Env):
    """
    Custom Environment that follows gym interface.
    The agent learns when to Buy (0), Sell (1), or Hold (2).
    """
    metadata = {'render.modes': ['human']}

    def __init__(self, df):
        super(StockTradingEnv, self).__init__()
        self.df = df
        self.reward_range = (-np.inf, np.inf)

        # Actions: 0 = Buy, 1 = Sell, 2 = Hold
        self.action_space = spaces.Discrete(3)

        # Observation space: Contains technical indicators and price history
        # Shape depends on the columns in df (assume they are normalized)
        self.obs_shape = len(self.df.columns)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.obs_shape,), dtype=np.float32
        )

        self.initial_capital = RL_CONFIG["initial_capital"]
        self.transaction_cost = RL_CONFIG["transaction_cost"]
        
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.balance = self.initial_capital
        self.net_worth = self.initial_capital
        self.shares_held = 0
        self.current_step = 0
        
        return self._next_observation(), {}

    def _next_observation(self):
        # Return row data
        obs = self.df.iloc[self.current_step].values
        return obs.astype(np.float32)

    def step(self, action):
        self.current_step += 1
        
        if self.current_step >= len(self.df) - 1:
            truncated = True
            terminated = True
        else:
            truncated = False
            terminated = False

        current_price = self.df.iloc[self.current_step]['Close']
        if pd.isna(current_price): # Saftey net
            current_price = self.df.iloc[self.current_step-1]['Close']
            
        reward = 0
        
        if action == 0: # Buy
            if self.balance > 0:
                shares_bought = self.balance // current_price
                cost = shares_bought * current_price * (1 + self.transaction_cost)
                if self.balance >= cost:
                    self.balance -= cost
                    self.shares_held += shares_bought
        elif action == 1: # Sell
            if self.shares_held > 0:
                revenue = self.shares_held * current_price * (1 - self.transaction_cost)
                self.balance += revenue
                self.shares_held = 0
        # action == 2 (Hold) does nothing directly
        
        # Calculate new net worth
        prev_net_worth = self.net_worth
        self.net_worth = self.balance + (self.shares_held * current_price)
        
        # Reward is change in net worth, scaled down
        reward = (self.net_worth - prev_net_worth) * RL_CONFIG["reward_scaling"]
        
        # Penalty if we lose money overall
        if self.net_worth < self.initial_capital:
            reward -= 0.1

        obs = self._next_observation()
        info = {
            'step': self.current_step,
            'net_worth': self.net_worth,
            'balance': self.balance,
            'shares_held': self.shares_held
        }
        
        return obs, reward, terminated, truncated, info


class RLAgent:
    def __init__(self):
        self.model_path = str(MODELS_DIR / "ppo_trading_agent.zip")
        self.model = None

    def train(self, df):
        if df is None or len(df) < 100:
            logger.warning("Not enough data to train RL agent.")
            return
            
        logger.info(f"Training PPO RL agent on {len(df)} samples")
        
        # Gym requires the env to be wrapped
        env = DummyVecEnv([lambda: StockTradingEnv(df)])
        
        if os.path.exists(self.model_path):
            self.model = PPO.load(self.model_path, env=env)
        else:
            self.model = PPO("MlpPolicy", env, verbose=1, learning_rate=RL_CONFIG["learning_rate"])
            
        self.model.learn(total_timesteps=RL_CONFIG["total_timesteps"])
        self.model.save(self.model_path)
        logger.info("RL training complete and model saved.")

    def predict_action(self, obs):
        if not self.model:
            self.load()
        if self.model:
            action, _states = self.model.predict(obs, deterministic=True)
            return action
        return 2 # Hold if no model
        
    def load(self):
        if os.path.exists(self.model_path):
            self.model = PPO.load(self.model_path)
            return True
        return False
