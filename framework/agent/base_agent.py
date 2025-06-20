# -*- coding: utf-8 -*-

# 请帮忙实现一个ai智能体类（BaseAgent），它的能力要求如下：
# - 会将传统Langchain概念中的agent、tool、chain三个概念都统一到agent之上（不需要体现这一点）
# - 具备run这个运行方法，运行过程中会有如下特性：
#   - 维护与流转status、context、resp这三个运行时对象，并且以生成器为形式进行返回（yield出去）
#   - 提供prehandle，posthandle这样的生命周期阶段
#   - 提供重试机制（整体重试），提供容错方法
# - 允许在agent中，简易方便地调用另一个agent（视作一个sub agent执行），也就是yield from other_agent
# - 支持同步or异步调用

import os
import time

import sys
sys.path.append(".")

import traceback
import logging
from logging import getLogger
import asyncio
from typing import Dict, Any, Generator, Optional, Union
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

class AgentStatus(Enum):
    """Status enum for agent execution."""
    READY = "ready"
    RUNNING = "running"
    MESSAGE = "message"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    ROLLBACK = "rollback"
    CLEAR = "clear"
    FINISHED = "finished"

class BaseAgent:
    """
    Base agent class for synchronous execution.
    Provides runtime management, lifecycle hooks, and retry mechanism.
    """
    
    def __init__(self, context: Dict[str, Any] = None, max_retries: int = 2, name: str = None):
        """
        Initialize the base agent.
        
        Args:
            context: Initial context for the agent execution
            max_retries: Maximum number of retries for the agent execution
            name: The name of the agent
        """
        self.name = name or self.__class__.__name__
        self.max_retries = max_retries
        self.status = AgentStatus.READY
        self.context = context or {}
        self.resp = None
    
    def run(self) -> Generator[Dict[str, Any], None, None]:
        """
        Synchronous run method for the agent.
        
        Yields:
            Runtime state updates during execution
            
        Returns:
            Final execution result
        """
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                # Update status
                self.status = AgentStatus.RUNNING
                
                # Yield initial state
                yield self._get_state()
                
                # Prehandle phase
                logger.info(f"Agent {self.name}: Starting prehandle phase")
                self._prehandle()
                yield self._get_state()
                
                # Main execution
                logger.info(f"Agent {self.name}: Starting main execution")
                yield_results = self._execute()
                for yield_result in yield_results:
                    self.resp = yield_result
                    yield self._get_state()
                
                # Posthandle phase
                logger.info(f"Agent {self.name}: Starting posthandle phase")
                self._posthandle()
                yield self._get_state()
                
                # Success
                self.status = AgentStatus.SUCCESS
                logger.info(f"Agent {self.name}: Execution completed successfully")
                yield self._get_state()
                
            except Exception as e:
                retry_count += 1
                self.status = AgentStatus.FAILED
                error_msg = f"Error in agent {self.name}: {str(e)}"
                self.context["error"] = error_msg
                self.context["error_traceback"] = traceback.format_exc()
                
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                
                # Try error recovery
                try:
                    self._error_handler(e)
                except Exception as recovery_error:
                    logger.error(f"Error in error handler for {self.name}: {str(recovery_error)}")
                    logger.error(traceback.format_exc())
                
                # Check if we should retry
                if retry_count <= self.max_retries:
                    self.status = AgentStatus.RETRYING
                    logger.info(f"Agent {self.name}: Retrying ({retry_count}/{self.max_retries})")
                    # yield self._get_state()
                else:
                    logger.error(f"Agent {self.name}: Max retries exceeded")
                    logger.error(traceback.format_exc())
                    yield self._get_state() 
                    return 

            self.status = AgentStatus.FINISHED
            yield self._get_state()
            return
    
    def _get_state(self) -> Dict[str, Any]:
        """Get the current state of the agent."""
        return {
            "agent": self.name,
            "status": self.status.value,
            "context": self.context,
            "resp": self.resp
        }
    
    # Lifecycle methods (to be overridden by subclasses)
    def _prehandle(self) -> None:
        """Synchronous prehandle step - override in subclasses for custom behavior."""
        pass
    
    def _execute(self) -> Any:
        """
        Main synchronous execution logic - must be implemented by subclasses.
        Returns the execution result.
        """
        raise NotImplementedError("Subclasses must implement _execute method")
    
    def _posthandle(self) -> None:
        """Synchronous posthandle step - override in subclasses for custom behavior."""
        pass
    
    def _error_handler(self, error: Exception) -> None:
        """
        Synchronous error handler - override in subclasses for custom error handling.
        Args:
            error: The exception that was raised
        """
        pass


class BaseAsyncAgent:
    """
    Base agent class for asynchronous execution.
    Provides runtime management, lifecycle hooks, and retry mechanism.
    """
    
    def __init__(self, context: Dict[str, Any] = None, max_retries: int = 3, name: str = None):
        """
        Initialize the base agent.
        
        Args:
            context: Initial context for the agent execution
            max_retries: Maximum number of retries for the agent execution
            name: The name of the agent
        """
        self.name = name or self.__class__.__name__
        self.max_retries = max_retries
        self.status = AgentStatus.READY
        self.context = context or {}
        self.resp = None
        
    async def run(self):
        """
        Async implementation of the run method.
        
        Yields:
            Runtime state updates during execution
            
        Returns:
            Final execution result
        """
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                # Update status
                self.status = AgentStatus.RUNNING
                
                # Yield initial state
                yield self._get_state()
                
                # Prehandle phase
                logger.info(f"Agent {self.name}: Starting prehandle phase")
                await self._prehandle()
                yield self._get_state()
                
                # Main execution
                logger.info(f"Agent {self.name}: Starting main execution")
                yield_results = await self._execute()
                for yield_result in yield_results:
                    self.resp = yield_result
                    yield self._get_state()
                
                # Posthandle phase
                logger.info(f"Agent {self.name}: Starting posthandle phase")
                await self._posthandle()
                yield self._get_state()
                
                # Success
                self.status = AgentStatus.SUCCESS
                logger.info(f"Agent {self.name}: Execution completed successfully")
                yield self._get_state()
                
            except Exception as e:
                retry_count += 1
                self.status = AgentStatus.FAILED
                error_msg = f"Error in agent {self.name}: {str(e)}"
                self.context["error"] = error_msg
                self.context["error_traceback"] = traceback.format_exc()
                
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                
                # Try error recovery
                try:
                    await self._error_handler(e)
                except Exception as recovery_error:
                    logger.error(f"Error in error handler for {self.name}: {str(recovery_error)}")
                    logger.error(traceback.format_exc())
                
                # Check if we should retry
                if retry_count <= self.max_retries:
                    self.status = AgentStatus.RETRYING
                    logger.info(f"Agent {self.name}: Retrying ({retry_count}/{self.max_retries})")
                    # yield self._get_state()
                else:
                    logger.error(f"Agent {self.name}: Max retries exceeded")
                    logger.error(traceback.format_exc())
                    yield self._get_state()
                    return
            
            self.status = AgentStatus.FINISHED
            yield self._get_state()
            return
    
    def _get_state(self) -> Dict[str, Any]:
        """Get the current state of the agent."""
        return {
            "agent": self.name,
            "status": self.status.value,
            "context": self.context,
            "resp": self.resp
        }
    
    # Lifecycle methods (to be overridden by subclasses)
    async def _prehandle(self) -> None:
        """Async prehandle step - override in subclasses for custom behavior."""
        pass
    
    async def _execute(self) -> Any:
        """
        Main async execution logic - must be implemented by subclasses.
        Returns the execution result.
        """
        raise NotImplementedError("Subclasses must implement _execute method")
    
    async def _posthandle(self) -> None:
        """Async posthandle step - override in subclasses for custom behavior."""
        pass
    
    async def _error_handler(self, error: Exception) -> None:
        """
        Async error handler - override in subclasses for custom error handling.
        Args:
            error: The exception that was raised
        """
        pass