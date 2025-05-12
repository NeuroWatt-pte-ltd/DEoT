import json 
from typing import List, Dict, Any
from prompters.base import BasePrompter
from utils import PromptCategory

class TaskPrompter(BasePrompter):
    """
    TaskPrompter handles task decomposition and validation.
    It breaks down user input into specific tasks and assigns them to appropriate agents.
    """

    def __init__(self):
        """Initialize TaskPrompter."""

        super().__init__(
            name="TaskPrompter",
            platform="openai",
            model_name = "gpt-4o",
            temperature=0
        )

        self.logger.debug("TaskPrompter initialized for task decomposition")

    def process(self, user_input: str) -> List[Dict[str, Any]]:
        """
        Process the user input and decompose it into tasks.

        :param user_input: The user query to analyze
        :return: A list of validated tasks with agent assignments
        """

        self.logger.info("Analyzing Task...")
        self.logger.debug(f"Analyzing task for input: {user_input}")

        try:
            # Step 1: Generate task decomposition
            decomposition = self._generate_decomposition(user_input)
            self.logger.info("Task decomposition generated successfully.")
            self.logger.debug(f"Decomposition Result: {json.dumps(decomposition, indent=2)}")

            # Step 2: Validate the generated task decomposition 
            validation_result = self._validate_plan(user_input, decomposition)
            self.logger.debug(f"Validation result: {validation_result}")

            if validation_result['is_valid']:
                self.logger.debug("Validation succeeded. Returning decomposition.")
                return decomposition
            
            # If validation fails, retry with feedback
            self.logger.warning("Validation failed. Retrying with feedback...")
            return self._retry_decomposition(user_input, validation_result['feedback'], decomposition)
        
        except Exception as e:
            self.logger.error("Failed to analyze task.", exc_info=True)
            return self.handle_error('Task decomposition', e)
        
    def _generate_decomposition(self, user_input: str) -> List[Dict[str, Any]]:
        """
        Generate task decomposition using the LLM.

        :param user_input: The input query
        :return: A list of decomposed tasks represented as dictionaries
        """
        self.logger.info("Generating task decomposition...")

        try:
            response = self.process_with_prompts(
                category=PromptCategory.PLANNER,
                system_prompt_name="task_decomposition/system",
                user_prompt_name="task_decomposition/user",
                input=user_input
            )

            self.logger.debug("Received task decomposition plan from LLM")
            self.logger.debug(f"Decomposition response content: {response}")
            
            return self.parse_json_response(response, "decomposition")
        
        except Exception as e:
            self.logger.error("Failed to generate task decomposition", exc_info=True)
            raise Exception(f"Error in task decomposition: {str(e)}")
        
    def _validate_plan(
            self,
            user_input: str,
            decomposition: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate the task decomposition.

        :param user_input: The input query
        :param decomposition: A list of decomposed tasks to validate
        :return: Validation result including  validity and feedback
        """

        self.logger.info("Starting task validation...")
        
        try:
            response = self.process_with_prompts(
                category=PromptCategory.PLANNER,
                system_prompt_name="plan_validator/system",
                user_prompt_name="plan_validator/user",
                query=user_input,
                task_plan=json.dumps(decomposition, indent=2)
            )

            self.logger.debug("Received task validation result from LLM.")
            validation_result = self._parse_validation_response(response)
            self.logger.debug(f"Validation Result: {validation_result}")

            return validation_result
    
        except Exception as e:
            self.logger.error("Task validation process encountered an error", exc_info=True)
            raise Exception(f"Error in task validation: {str(e)}")
        
    def _parse_validation_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM's validation response into a structured format.

        :param response: raw response from LLM
        :return: Dictionary containing validation status and feedback
        """

        self.logger.debug(f"Parsing validation response: {response}")
        success_message = "The plan satisfies completeness and non-redundancy."
        is_valid = success_message in response 
        return {
            'is_valid': is_valid,
            'feedback': None if is_valid else response 
        }
    
    def _retry_decomposition(
            self,
            user_input: str,
            feedback: str,
            original_decomposition: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Retry task decomposition using feedback from validation.

        :param user_input: The input query
        :param feedback: Feedback from the validation process
        :param original_decompositon: The original decomposition that failed validation
        """

        self.logger.debug("Retrying decomposition with feedback...")

        try:
            response = self.process_with_prompts(
                category=PromptCategory.PLANNER,
                system_prompt_name="retry/system",
                user_prompt_name="retry/user",
                query=user_input,
                feedback=feedback,
                original_response=json.dumps(original_decomposition, indent=2)
            )

            return self.parse_json_response(response, "retry_decomposition")
        
        except Exception as e:
            self.logger.error("Failed to retry decomposition", exc_info=True)
            raise Exception(f"Error in retry decomposition: {str(e)}")


