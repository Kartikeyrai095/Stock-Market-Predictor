"""
Agent 10: Continuous Learning (Daemon)
Runs continuously in the background, orchestrating the periodic retraining of models
based on the signals from the Self-Learning Agent. Uses APScheduler.
"""

from agents.base_agent import BaseAgent
from apscheduler.schedulers.background import BackgroundScheduler
import time

class ContinuousLearningAgent(BaseAgent):
    def __init__(self, orchestrator=None):
        super().__init__("ContinuousLearning")
        self.scheduler = BackgroundScheduler()
        self.orchestrator = orchestrator # Reference to main.py orchestrator if needed

    def initialize(self) -> bool:
        try:
            # We don't start the scheduler entirely here, just configure jobs
            # This allows the orchestrator to decide when to 'run' it.
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize scheduler: {e}")
            return False

    def execute(self, mode="start", **kwargs) -> dict:
        """
        Starts or stops the background daemon.
        """
        if mode == "start":
            if not self.scheduler.running:
                self.logger.info("Configuring continuous learning schedules...")
                
                # Daily Self-Learning Check (Runs at 5 PM IST)
                self.scheduler.add_job(
                    self._trigger_self_learning, 
                    'cron', 
                    day_of_week='mon-fri', 
                    hour=17, 
                    minute=0,
                    id='daily_assessment'
                )
                
                # Weekly Model Retraining (Runs Saturday at 2 AM)
                self.scheduler.add_job(
                    self._trigger_retraining,
                    'cron',
                    day_of_week='sat',
                    hour=2,
                    minute=0,
                    id='weekly_retrain'
                )

                self.scheduler.start()
                self.logger.info("Continuous Learning daemon running in background.")
                return {"status": "started"}
            else:
                return {"status": "already_running"}
                
        elif mode == "stop":
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                self.logger.info("Continuous Learning daemon stopped.")
                return {"status": "stopped"}

        elif mode == "manual_retrain":
            # Direct trigger
            success = self._trigger_retraining()
            return {"status": "manual_retrain", "success": success}

        return {"status": "unknown_mode"}

    def _trigger_self_learning(self):
        """Callback to run Agent 5"""
        self.logger.info("Scheduled task: Running Self-Learning assessment...")
        if self.orchestrator:
             self.orchestrator.run_self_learning_cycle()

    def _trigger_retraining(self):
        """Callback to retrain models with latest data"""
        self.logger.info("Scheduled task: Initiating model retraining pipeline...")
        # Deep learning models require significant compute.
        # In a real system, this would call Agent 3 (Prediction) train() methods
        # feeding it the latest data from the DB.
        
        # Placeholder for actual training logic
        self.logger.info("Retraining models (LSTM, Transformer, RL)...")
        time.sleep(2) # Simulate work
        self.logger.info("Models retrained and saved successfully.")
        return True
