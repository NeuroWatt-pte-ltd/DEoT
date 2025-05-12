import json
from typing import Dict, Any
from prompters.base import BasePrompter
from utils import PromptCategory

class InputPrompter(BasePrompter):
    """InputPrompter handles initial prompt engineering and input optimization."""

    def __init__(self):
        """Initialize InputPrompter."""

        super().__init__(
            name="InputPrompter",
            platform="openai",
            model_name = "gpt-4o",
            temperature=0
        )

        self.logger.debug("InputPrompter initialized for query optimization")

    def process(self, user_input: str) -> Dict[str, Any]:
        """
        Process and optimize the user input.

        :param user_input: Original user query
        :return: Dictionary containing optimized query and extracted elements
        """

        self.logger.info(f"Starting input optimization for: {user_input}")

        try:
            # Process input optimization
            response = self.process_with_prompts(
                category=PromptCategory.BASE_PROMPTER,
                system_prompt_name="input_optimization/system",
                user_prompt_name="input_optimization/user",
                input=user_input
            )

            # Parse and validate response
            optimization_result = self.parse_json_response(response, "optimization")
            self._validate_optimization(optimization_result)

            self.logger.info("Input optimization completed successfully.")

            return optimization_result
        
        except Exception as e:
            self.logger.error(f"Failed to optimize input: {str(e)}", exc_info=True)
            return self._handle_optimization_error(user_input, str(e))
        
    def _validate_optimization(self, optimization_result: Dict[str, Any]) -> None:
        """
        Validate the optimization result.

        :param optimization_result: A dictionary containing the optimization result
        """

        required_keys = {"optimized_query", "original_query", "modifications"}

        if not all(key in optimization_result for key in required_keys):
            raise ValueError("Missing required key in optimization result")
        
        if not optimization_result["optimized_query"].strip():
            raise ValueError("Optimized query is empty")

        if not optimization_result["original_query"].strip():
            raise ValueError("Original query is missing")

        if not isinstance(optimization_result["modifications"], list):
            raise ValueError("Modifications must be a list")
        
        self.logger.debug(f"Optimized query: {optimization_result['optimized_query']}")
        self.logger.debug(f"Original query: {optimization_result['original_query']}")
        self.logger.debug(f"Modifications: {json.dumps(optimization_result['modifications'], indent=2)}")

    def _handle_optimization_error(
            self,
            original_input: str,
            error_message: str 
    ) -> Dict[str, Any]:
        """
        Handle optimization errors by attempting to get correction suggestion.

        :param original_input: The original user_query
        :param error_message: The error message from the failed attempt
        :return: Dict containing optimization result wit herror handling information
        """

        self.logger.warning(f"Handling optimization error: {error_message}")

        try:
            response = self.process_with_prompts(
                category=PromptCategory.BASE_PROMPTER,
                system_prompt_name="error_handling/system",
                user_prompt_name="error_handling/user",
                original_query=original_input,
                error_message=error_message
            )

            result = self.parse_json_response(response, "error_handling")
            required_keys = {"optimized_query", "original_query", "modifications", "error_handling"}
            if not all(key in result for key in required_keys):
                raise ValueError("Missing required keys in error handling result")
            
            return result 
        
        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")
            return self.handle_error('Input optimization', e)