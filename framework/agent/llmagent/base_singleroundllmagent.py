# -*- coding: utf-8 -*-

# 好的，继承上面的同步的baseagent，我需要实现BaseSingleRoundLLMAgent，它的描述是：
# 1 只需要支持同步调用
# 2 支持大模型调用，使用openai的sdk进行大模型调用；只支持单轮的大模型调用，也就是只需要systemp和userp
# 3 初始化时，可以输入这些字段控制：
# systemp_template, userp_template：他们将会被使用format(**self.context)形式来转化为真正的systemp和userp来进入大模型进行调用。
# output_schema：如果是None，则进行正常的大模型返回；如果不是None，则需要强制让模型输出为这个格式的json（可以使用function call来进行）
# default_input：字典形式表达的入参缺省值。在_prehandle中，如果context字段中没有对应的入参，则使用这里的缺省值填入避免错误。
# 4 支持流式输出和非流式输出两种

import os
import time

import sys
sys.path.append(".")

import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

import json
from typing import Dict, Any, Generator, Optional, List, Union
import openai
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from framework.agent.base_agent import BaseAgent, AgentStatus

class BaseSingleRoundLLMAgent(BaseAgent):
    """
    Base agent for single-round LLM interactions.
    Supports synchronous OpenAI API calls with templated prompts and optional output schema.
    """
    
    def __init__(
        self,
        context: Dict[str, Any] = None,
        client = None,
        systemp_template: str = "",
        userp_template: str = "",
        output_schema: Optional[Dict[str, Any]] = None,
        default_input: Dict[str, Any] = None,
        max_retries: int = 3,
        name: str = None,
        stream: bool = False,
        model: str = "gpt-4-turbo",
        extra_args: Dict[str, Any] = None,
    ):
        """
        Initialize the LLM agent.
        
        Args:
            context: Initial context for the agent execution
            systemp_template: Template string for system prompt
            userp_template: Template string for user prompt
            output_schema: JSON schema for enforcing structured output
            default_input: Default values for context fields
            max_retries: Maximum number of retries for the agent execution
            name: The name of the agent
            stream: Whether to use streaming API
            model: OpenAI model to use
            extra_args: Additional arguments to pass to the OpenAI API call
        """
        super().__init__(context=context, max_retries=max_retries, name=name)
        self.systemp_template = systemp_template
        self.userp_template = userp_template
        self.output_schema = output_schema
        self.default_input = default_input or {}
        self.stream = stream
        self.model = model
        self.extra_args = extra_args or {}
        if client is None:
            self.client = OpenAI()
        else:
            self.client = client
        
        # Store prompt templates and final prompts
        self.context["systemp_template"] = systemp_template
        self.context["userp_template"] = userp_template
        self.context["systemp"] = ""
        self.context["userp"] = ""
        
        # Store raw LLM response
        self.context["llm_response"] = None
        
    def _deep_update_context(self, default_dict: Dict[str, Any], target_dict: Dict[str, Any]) -> None:
        """
        Recursively update target_dict with values from default_dict if keys are missing.
        Creates nested dictionaries as needed.
        
        Args:
            default_dict: Dictionary with default values
            target_dict: Dictionary to update (self.context)
        """
        for key, value in default_dict.items():
            if key not in target_dict:
                target_dict[key] = value
                logger.info(f"Agent {self.name}: Applied default value for '{key}'")
            elif isinstance(value, dict) and isinstance(target_dict[key], dict):
                # Recursively update nested dictionaries
                self._deep_update_context(value, target_dict[key])
            elif isinstance(value, dict) and target_dict[key] is None:
                # If target value is None but default is a dict, replace with default
                target_dict[key] = value
                logger.info(f"Agent {self.name}: Replaced None value with default dict for '{key}'")
    
    def _prehandle(self) -> None:
        """
        Preprocess the context data and prepare prompts for LLM call.
        Apply default values for missing context fields.
        """
        # Apply default input values recursively
        self._deep_update_context(self.default_input, self.context)
        
        # Format the prompt templates using the context
        try:
            self.context["systemp"] = self.systemp_template.format(**self.context)
            self.context["userp"] = self.userp_template.format(**self.context)
            logger.info(f"Agent {self.name}: Successfully formatted prompts")
        except KeyError as e:
            logger.error(f"Agent {self.name}: Missing context key for prompt template: {e}")
            # Still raise the exception so it's caught in the run method
            raise ValueError(f"Missing required context field for prompt template: {e}")
        except Exception as e:
            logger.error(f"Agent {self.name}: Error formatting prompts: {e}")
            # Still raise the exception so it's caught in the run method
            raise ValueError(f"Error formatting prompts: {e}")
    
    def _execute(self) -> Any:
        """
        Execute the LLM call and process the response.
        Returns the processed LLM response.
        """
        messages = [
            {"role": "system", "content": self.context["systemp"]},
            {"role": "user", "content": self.context["userp"]}
        ]
        logger.info(self.context["userp"])
        
        # Prepare function call configuration if output_schema is provided
        functions = None
        function_call = None
        
        if self.output_schema:
            function_name = "json_format_response"
            functions = [
                {
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "description": "The response using well-structured JSON.",
                        "parameters": self.output_schema
                    }
                }
            ]
            function_call = {"type": "function", "function": {"name": function_name}}
        
        # Make the API call and let exceptions propagate to be caught in run()
        if self.stream:
            yield self._handle_streaming_response(messages, functions, function_call)
        else:
            yield self._handle_normal_response(messages, functions, function_call)
    
    def _handle_normal_response(
        self, 
        messages: List[Dict[str, str]], 
        functions: Optional[List[Dict[str, Any]]], 
        function_call: Optional[Dict[str, str]]
    ) -> Any:
        """
        Handle non-streaming LLM response.
        """
        # Prepare API call parameters
        api_params = {
            "model": self.model,
            "messages": messages,
            **self.extra_args  # Include extra arguments
        }
        
        # Add function call parameters if provided
        if functions:
            api_params["tools"] = functions
            api_params["tool_choice"] = function_call
        
        # Make the API call - let exceptions propagate
        response = self.client.chat.completions.create(**api_params)
        
        # Store the full raw response in context
        self.context["llm_response"] = response
        
        # Process the response based on whether function call was used
        if self.output_schema:
            try:
                if response.choices[0].message.function_call:
                    # Extract and parse the function call arguments
                    function_args = response.choices[0].message.function_call.arguments
                    parsed_result = json.loads(function_args)
                    return parsed_result
                else:
                    parsed_result = json.loads(response.choices[0].message.content)
                    return parsed_result
            except json.JSONDecodeError as e:
                    logger.error(f"Agent {self.name}: Failed to parse function call result: {e}")
                    # Let the exception propagate
                    raise RuntimeError(f"Failed to parse function call result: {e}")
        else:
            # Return the content directly if no function call was used
            return response.choices[0].message.content
    
    def _handle_streaming_response(
        self, 
        messages: List[Dict[str, str]], 
        functions: Optional[List[Dict[str, Any]]], 
        function_call: Optional[Dict[str, str]]
    ) -> Generator[Dict[str, Any], None, Any]:
        """
        Handle streaming LLM response.
        Yields partial responses and returns the final complete response.
        """
        # Prepare API call parameters
        api_params = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            **self.extra_args  # Include extra arguments
        }
        
        # Add function call parameters if provided
        if functions:
            api_params["tools"] = functions
            api_params["tool_choice"] = function_call
        
        # Initialize collectors for streaming response
        content_collector = ""
        function_args_collector = ""
        is_function_call = False
        
        # Make the streaming API call - let exceptions propagate
        stream = self.client.chat.completions.create(**api_params)
        
        # Process the streaming response
        for chunk in stream:
            delta = chunk.choices[0].delta
            
            # Check if this is a function call response
            if hasattr(delta, 'function_call') and delta.function_call:
                is_function_call = True
                
                # Extract and accumulate function call arguments
                if hasattr(delta.function_call, 'arguments') and delta.function_call.arguments:
                    function_args_collector += delta.function_call.arguments
                    
                    # Update context with current state and yield it
                    self.context["llm_streaming_response"] = function_args_collector
                    yield self._get_state()
            
            # Handle regular content
            elif hasattr(delta, 'content') and delta.content:
                content_collector += delta.content
                
                # Update context with current state and yield it
                self.context["llm_streaming_response"] = content_collector
                yield self._get_state()
        
        # Process the final complete response
        if is_function_call and self.output_schema:
            try:
                # Parse the complete function arguments JSON
                final_result = json.loads(function_args_collector)
            except json.JSONDecodeError as e:
                logger.error(f"Agent {self.name}: Failed to parse function call streaming result: {e}")
                # Let the exception propagate
                raise RuntimeError(f"Failed to parse function call streaming result: {e}")
        else:
            final_result = content_collector
        
        # Store the complete response in context
        self.context["llm_response"] = final_result
        
        return final_result
    
    def run(self) -> Generator[Dict[str, Any], None, None]:
        """
        Override the run method to handle streaming responses differently.
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
                
                # Handle streaming and non-streaming differently
                if self.stream:
                    # 逻辑有误，要重写，暂时不用流式llm
                    # For streaming, _execute returns a generator
                    streaming_gen = self._execute()
                    
                    # Yield each streaming state
                    for state in streaming_gen:
                        # state is already passed through _get_state in _handle_streaming_response
                        yield state
                    
                    # Get the final result
                    self.resp = self.context.get("llm_response")
                else:
                    # For non-streaming, get the result directly
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
                logger.info(f"Agent {self.name} resp: {self.resp}")
                yield self._get_state()
                
            except Exception as e:
                retry_count += 1
                self.status = AgentStatus.FAILED
                error_msg = f"Error in agent {self.name}: {str(e)}"
                self.context["error"] = error_msg
                self.context["error_traceback"] = traceback.format_exc()
                
                # 只打日志，不重新抛出异常
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                
                # Try error recovery
                try:
                    self._error_handler(e)
                except Exception as recovery_error:
                    logger.error(f"Error in error handler for {self.name}: {str(recovery_error)}")
                
                # Check if we should retry
                if retry_count <= self.max_retries:
                    self.status = AgentStatus.RETRYING
                    logger.info(f"Agent {self.name}: Retrying ({retry_count}/{self.max_retries})")
                    # yield self._get_state()
                else:
                    logger.error(f"Agent {self.name}: Max retries exceeded")
                    yield self._get_state()
                    return
            
            self.status = AgentStatus.FINISHED
            yield self._get_state()
            return