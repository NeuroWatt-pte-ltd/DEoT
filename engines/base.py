from typing import Dict, Any 
from abc import ABC, abstractmethod 
from utils import setup_logger, LLMLoader, PromptCategory, PromptLoader

class BaseEngine(ABC):
    """
    BaseEngine is the abstract base class for all engines.
    It provides common functionality for engine initializations and operations.
    """

    def __init__(
            self, 
            name: str = "BaseEngine",
            platform: str = "openai",
            model_name: str = "gpt-4o",
            temperature: float = 0
    ):
        """
        Initialize BaseEngine.

        :param name: Name of the engine
        :param platform: LLM platform to use 
        :param model_name: Name of the model to use 
        :param temperature: Temperature
        """

        self.name = name
        self.platform = platform
        self.model_name = model_name
        self.temperature = temperature

        self.logger = setup_logger(f"{self.name}")
        self.logger.debug(f"Initializing {self.name}")

        self.llm_loader = LLMLoader()
        self.prompt_loader = PromptLoader()

        self.logger.debug(f"{self.name} initialized successfully")

    def process_with_prompts(
            self,
            category: PromptCategory,
            system_prompt_name: str,
            user_prompt_name: str,
            **prompt_kwargs
    ) -> str:
        """
        Common processing flow using prompts and LLM.

        :param category: Prompt category
        :param system_prompt_name: Name of the system prompt
        :param user_prompt_name: Name of the user prompt
        :param prompt_kwargs: Additional keyword arguments for prompt formatting 
        """

        try:
            # Get prompts 
            system_prompt =  self.prompt_loader.get_prompt(
                category,
                system_prompt_name
            )

            user_prompt = self.prompt_loader.get_prompt(
                category,
                user_prompt_name,
                **prompt_kwargs
            )

            self.logger.debug(f"System Prompt: {system_prompt}")
            self.logger.debug(f"User Prompt: {user_prompt}")

            # Get response from LLM
            try:
                response = self.llm_loader.chat(
                    platform=self.platform,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model_name=self.model_name,
                    temperature=self.temperature
                )

            except Exception as e:
                self.logger.error("Failed to get response", exc_info=True)
                raise 
        
            return response 
        
        except Exception as e:
            return self.handle_error("prompt_processing", e)
        
    @abstractmethod
    def process(self, *args, **kwargs):
        """
        Process inputs according to the engine's specific functionality.
        All engine subclass must implement this method.

        :return: Processing result
        """
        
        pass

    def handle_error(self, operation: str, error: Exception) -> Dict[str, Any]:
        """
        Standardized error handling for engines.

        :param operation: The operation that failed
        :param error: The exception that was raised
        :return: Standardized error response
        """

        error_msg = str(error)
        self.logger.error(f"Error: {error_msg}", exc_info=True)

        return {
            "success": False,
            "error": error_msg,
            "engine": self.name,
            "operation": operation
        }

