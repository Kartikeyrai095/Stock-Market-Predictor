"""
Agent 8: Risk Management
Filters strategies through risk limits (position sizing, RR ratios, drawdown).
"""

from agents.base_agent import BaseAgent
from config import RISK_CONFIG

class RiskManagementAgent(BaseAgent):
    def __init__(self):
        super().__init__("RiskManagement")

    def initialize(self) -> bool:
        return True

    def execute(self, strategy: dict, current_portfolio_value: float = 1_000_000, **kwargs) -> dict:
        """
        Validates a strategy dictionary and adds position sizing.
        Returns a dictionary with passed status and modified parameters.
        """
        self.logger.info(f"Checking risk for {strategy.get('ticker')}")
        
        if not strategy or strategy.get("action") == "HOLD":
            return {"passed": False, "reason": "No action to manage", "strategy": strategy}
            
        action = strategy["action"]
        entry = strategy["entry_price"]
        stop = strategy["stop_loss"]
        target = strategy["target_price_1"]
        
        # 1. Check Risk-Reward Ratio
        risk = abs(entry - stop)
        reward = abs(target - entry)
        
        if risk == 0:
            return {"passed": False, "reason": "Zero risk calculated (bad stop loss)", "strategy": strategy}
            
        rr_ratio = reward / risk
        if rr_ratio < RISK_CONFIG["min_risk_reward_ratio"]:
            self.logger.warning(f"Strategy rejected. R:R {rr_ratio:.2f} < {RISK_CONFIG['min_risk_reward_ratio']}")
            return {"passed": False, "reason": f"R:R ratio {rr_ratio:.2f} too low", "strategy": strategy}

        # 2. Position Sizing
        # Max risk per trade: We'll risk 1% of portfolio value max per trade
        max_monetary_risk = current_portfolio_value * 0.01 
        
        # How many shares can we buy where (entry - stop) * shares <= max_monetary_risk?
        shares_based_on_risk = int(max_monetary_risk / risk)
        
        # Max absolute position size limit
        max_position_value = current_portfolio_value * RISK_CONFIG["max_position_pct"]
        shares_based_on_capital = int(max_position_value / entry)
        
        # Final shares is the minimum of the two constraints
        recommended_shares = min(shares_based_on_risk, shares_based_on_capital)
        total_investment = recommended_shares * entry
        
        if recommended_shares <= 0:
            return {"passed": False, "reason": "Position size calculation resulted in 0 shares", "strategy": strategy}

        # Validate confidence (proxy score from strategy directly for now)
        if hasattr(strategy, "total_score") and strategy["total_score"] < 2:
             return {"passed": False, "reason": "Signal confidence too low", "strategy": strategy}

        # Update strategy with risk constraints
        safe_strategy = strategy.copy()
        safe_strategy["risk_reward_ratio"] = round(rr_ratio, 2)
        safe_strategy["recommended_shares"] = recommended_shares
        safe_strategy["total_investment"] = round(total_investment, 2)
        safe_strategy["potential_loss"] = round(recommended_shares * risk, 2)
        
        self.logger.info(f"Risk check passed. Approved {recommended_shares} shares.")
        return {
            "passed": True,
            "strategy": safe_strategy
        }
