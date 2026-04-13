"""
Abstract Base Class for all Agents in the system.
Defines the standard interface and shared utilities.
"""

from abc import ABC, abstractmethod
import time
from traceback import format_exc
from utils.logger import get_agent_logger

class BaseAgent(ABC):
    """
    Abstract Base Class that all multi-agent components must inherit from.
    Ensures a unified interface for orchestration.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_agent_logger(self.name)
        self.is_running = False
        self.last_run_time = None
        self.status = "INITIALIZED"

    @abstractmethod
    def initialize(self) -> bool:
        """
        Setup database connections, load models, initialize APIs.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> dict:
        """
        The core work payload of the agent.
        Takes optional arguments based on the orchestration flow.
        Returns a dictionary with result data.
        """
        pass

    def run(self, **kwargs) -> dict:
        """
        Wrapped execution with error handling, timing, and state management.
        The orchestrator calls this, not `execute` directly.
        """
        self.is_running = True
        self.status = "RUNNING"
        start_time = time.time()
        
        self.logger.info(f"Starting execution of {self.name}")
        
        result = {
            "agent": self.name,
            "success": False,
            "data": None,
            "error": None,
            "execution_time_sec": 0
        }
        
        try:
            output = self.execute(**kwargs)  # Forward all kwargs to execute()
            result["success"] = True
            result["data"] = output
            self.status = "IDLE"
            self.logger.info(f"{self.name} completed successfully.")
            
        except Exception as e:
            self.status = "ERROR"
            self.logger.error(f"Error in {self.name} execution: {str(e)}")
            self.logger.debug(format_exc())
            result["error"] = str(e)
            
        finally:
            end_time = time.time()
            self.is_running = False
            self.last_run_time = end_time
            result["execution_time_sec"] = round(end_time - start_time, 3)
            
        return result

    def get_status(self) -> dict:
        """Return the current health/state of the agent"""
        return {
            "name": self.name,
            "status": self.status,
            "is_running": self.is_running,
            "last_run_time": self.last_run_time
        }
