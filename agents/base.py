from abc import ABC, abstractmethod
from utils import setup_logger, LLMLoader, PromptCategory, PromptLoader
from typing import Any

class BaseAgent(ABC):
    """
    Base class for all agents in the system.
    Provides common functionality and defines the interface that all agents must implement.
    """

    def __init__(
            self, 
            name: str,
            platform: str = "openai",
            model_name: str = "gpt-4o",
            temperature: float = 0
    ):
        """
        Initialize the base agent.

        :param name: Agent name
        :param platform: LLM platform
        :param model_name: Model name
        :param temperature: Temperature setting
        """
        
        self.name = name 
        self.logger = setup_logger(self.name)
        self.logger.debug(f"[INIT] Initializing {self.name}")

        # Initialize components
        self.llm_loader = LLMLoader()
        self.prompt_loader = PromptLoader()

        self.platform = platform
        self.model_name = model_name
        self.temperature = temperature

        self.logger.debug(f"[INIT] {self.name} initialized successsfully.") 

    def process_with_prompts(
            self,
            category: PromptCategory,
            system_prompt_name: str,
            user_prompt_name: str,
            **prompt_kwargs
    ) -> str:
        """
        Common processing flow using prompts and LLM.

        :param input_data: Input data to process
        :param category: Prompt category
        :param system_prompt_name: Name of the system prompt
        :param user_prompt_name: Name of the user prompt
        :param prompt_kwargs: Additional keyword arguments for prompt formatting
        :return: Processing result
        """

        try:
            self.logger.info(f"Starting {self.name} processing...")

            # Get prompts 
            system_prompt = self.prompt_loader.get_prompt(category, system_prompt_name)
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
                self.logger.error(f"Failed to get response: {str(e)}", exc_info=True)
                raise 

            self.logger.info(f"Successfully completed {self.name} processing.")
            self.logger.debug(f"Processing Result: {response}")

            return response 
        
        except Exception as e:
            return self.handle_error(e)
        
    @abstractmethod
    def process(self, input_data: Any) -> str:
        """
        Process input data and return a result.
        All agent subclass must implement this method.

        :param input_data: The input data to process
        :return: Processing result
        """

        pass 

    def handle_error(self, error: Exception) -> str:
        """
        Handle exceptions and return an error message.

        :param error: The exception that occurred
        :return: Error message
        """

        self.logger.error(f"Error: {str(error)}", exc_info=True)
        return f"Error occurred: {str(error)}"
    

