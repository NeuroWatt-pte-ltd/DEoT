import os 
import json 
import requests 
from typing import Dict, Any, Optional 
from llama_index.llms.openai import OpenAI 
from llama_index.core.llms import ChatMessage, MessageRole 
from openai import OpenAI as PerplexityClient 
from utils.logger import setup_logger

class OpenAIHandler:
    """OpenAIHandler handles interactions with OpenAI model."""

    def __init__(self, temperature=0, model_name="gpt-4o"):
        """
        Initialize the OpenAIHandler.

        :param temperature: Temperature
        :param model_name: The name of the model
        """

        self.logger = setup_logger("OpenAIHandler")
        self.logger.debug(f"Initializing OpenAIHandler with model {model_name}")

        self.client = OpenAI(
            temperature=temperature,
            model_name=model_name,
            api_keys=os.getenv("OPENAI_API_KEY")
        )

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        Get the response from openai model.
        
        :param system_prompt: The system prompt content 
        :param user_prompt: The user prompt content
        :return: The response content from the model
        """

        # Create message list using ChatMessage
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=user_prompt)
        ]

        # Get response from model
        response = self.client.chat(messages)

        return response.message.content.strip()
    
class PerplexityHandler:
    """PerpelxityHandler handles interaction with Perplexity."""

    def __init__(self, temperature=0, model_name="llama-3.1-sonar-small-128k-online"):
        """
        Initialize the PerplexityHandler.

        :param temperature: Temperature
        :param model_name: The name of the model
        """

        self.logger = setup_logger("PerplexityHandler")
        self.logger.debug(f"Initializing PerplexityHandler with model {model_name}")

        self.client = PerplexityClient(
            api_key=os.getenv("PERPLEXITY_API_KEY"),
            base_url="https://api.perplexity.ai"
        )

        self.model = model_name
        self.temperature = temperature

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        Get the response from Perplexity model.

        :param system_prompt
        :param user_prompt: The user prompt content
        :return: THe response content from the model
        """

        # Create message list
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature
        )

        return response.choices[0].message.content.strip()
    
class LLMLoader:
    """LLMLoader provides a unified interface to handle interactions with different LLM models."""

    _instance = None
    _initialized = False 

    def __new__(cls):
        """Singleton pattern implemention."""

        if cls._instance is None: 
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the LLMLoader."""

        if self._initialized:
            return 
        
        self.logger = setup_logger("LLMLoader")
        self._initialized = True 
    
    def get_llm(self, platform: str, **kwargs) -> Any:
        """
        Get the appropriate LLM handler for the specified platform.
        
        :param platform: 'openai' or 'perplexity'
        :param **kwargs: Additional arguments for platform-specific initialization
        :return: An instance of the appropriate LLM handler
        :raises ValueError: If the platform is not supported
        """
        if platform.lower() == 'openai':
            return OpenAIHandler(**kwargs)
        elif platform.lower() == 'perplexity':
            return PerplexityHandler(**kwargs)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    def chat(self, platform: str, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        Get chat response from the specified platform.
        
        :param platform: 'openai' or 'perplexity'
        :param system_prompt: The system prompt content
        :param user_prompt: The user prompt content
        :param **kwargs: Additional arguments for platform-specific initialization
        :return: The response content from the selected platform
        """

        handler = self.get_llm(platform, **kwargs)
        return handler.chat(system_prompt, user_prompt)
    
        