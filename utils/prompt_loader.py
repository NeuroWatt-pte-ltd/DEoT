import yaml
from enum import Enum 
from typing import Optional 
from pathlib import Path
from utils.logger import setup_logger

class PromptCategory(Enum):
    """Enum class representing different categories of prompts."""
    BASE_PROMPTER = "base_prompter"  
    PLANNER = "planner"
    ERROR_HANDLING = "error_handling" 
    NEWS_SEARCH = "news_search"  
    EVENT_EXTRACTOR = "event_extractor" 
    HISTORY_ANALYZER = "history_analyzer"  
    REASONING = "reasoning" 
    INFO_SEARCH = "info_search"  
    VALIDATION = "validation" 
    EXECUTOR_SERVICE = "executor_service"  
    ENGINE_CONTROLLER = "engine_controller"  
    BREADTH_ANALYSIS = "breadth_analysis"  
    DEPTH_ANALYSIS = "depth_analysis" 
    RESPONSE = "response" 

class PromptLoader:
    """Central loader for all prompts in the system."""

    # Holds the singleton instance and tracks wheter the instance is initialized
    _instance = None 
    _initialized = False 

    def __new__(cls):
        """Ensure the class is a singleton by controlling instance creation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, prompthub_path: Optional[str] = None):
        """
        Initialized the PromptLoader by loading prompt templates from a YAML file.

        :param prompthu_path: Optional path to the YAML file containing prompts
        """
        # Skip initialization if already done 
        if self._initialized:
            return 
        
        # Set up logger 
        self.logger = setup_logger("PromptLoader")
        self.logger.debug("[INIT] Initializing PromptLoader...")

        try:
            if prompthub_path is None: 
                prompthub_path = Path("config/prompthub.yaml")

            # Load pompts from the specified YAML file
            with open(prompthub_path, 'r', encoding='utf-8') as f:
                self.prompts = yaml.safe_load(f)
            
            # Mark initialized as complete
            self._initialized = True
            self.logger.debug(f"[INIT] Suceesfully loaded prompts from {prompthub_path}")
        
        except Exception as e:
            self.logger.error(f"[INIT ERROR] Failed to initialize PromptLoader: {str(e)}", exc_info=True)

    def get_prompt(self, category: PromptCategory, prompt_name: str, **kwargs) -> str:
        """
        Retrieve and format a prompt template by category and name.

        :param category: The category of the prompt
        :param prompt_name: The specific prompt name withih the category, using '/' for nested prompts"
        return: The formatted prompt string
        """
        try:
            # Log the request for the prompt
            self.logger.debug(f"Getting prompt - category: {category.value}, name: {prompt_name}")

            # Navigate through the nested prompt names to find the template
            parts = prompt_name.split('/')
            prompt_template = self.prompts[category.value]

            for part in parts:
                prompt_template = prompt_template[part]
            
            # Ensure the retrieved value is a string 
            if not isinstance(prompt_template, str):
                raise ValueError(f"Prompt at path '{prompt_name}' is not a string")
            
            # Format the prompt with provided variables if any
            result = prompt_template.format(**kwargs) if kwargs else prompt_template
            self.logger.debug(f"Successfully retrieved and formatted prompt.")

            return result 
    
        except KeyError as e:
            self.logger.error(f"[PROMPT ERROR] Prompt not found: category={category.value}, name={prompt_name}", exc_info=True)
            raise ValueError(f"Prompt not found: category={category.value}, name={prompt_name}")
        
        except Exception as e:
            self.logger.error(f"[PROMPT ERROR] Failed to retrieve prompt: {str(e)}", exc_info=True)
            raise 


