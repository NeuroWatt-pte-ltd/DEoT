from typing import Dict, Any 
from engines.base import BaseEngine
from utils import PromptCategory

class DepthEngine(BaseEngine):
    """DepthEngine generates a single follow-up question to analyze the deeper implicationsor dimensions of a topic or event."""

    def __init__(
            self,
            name="DepthEngine",
            platform="openai",
            model_name="gpt-4o",
            temperature=0
    ):
        """Initialize the DepthEngine"""
        super().__init__(name, platform, model_name, temperature)
        self.logger.debug("DepthEngine initialized successfully")

    def process(
            self,
            content: str,
            original_query: str 
    ) -> Dict[str, Any]:
        """
        Generate follow-up question for deeper analysis.

        :param content: Content to analyze
        :param original_query: Original user query
        :return: A structured follow-up question
        """

        try:
            response = self.process_with_prompts(
                category=PromptCategory.DEPTH_ANALYSIS,
                system_prompt_name="generate/system",
                user_prompt_name="generate/user",
                content=content,
                original_query=original_query
            )

            follow_up_question = self._parse_question(response)
            self.logger.info("Successfully generated a follow-up question")
            self.logger.debug(f"Question: {follow_up_question}")

            return follow_up_question
        
        except Exception as e:
            return self.handle_error("generate", e)
        
    def _parse_question(self, response: str) -> Dict[str, Any]:
        """
        Parse the response from LLM into a structure follow-up question.

        :param response: Raw response from LLM
        :return: A follow-up question with its reasoning
        """

        try:
            question_data = {}

            # Split response into lines and extract details 
            lines = response.strip().split('\n')
            for line in lines:
                if line.startswith('Question:'):
                    question_data['question'] = line.split(':', 1)[1].strip()

            # Validate required fields 
            if 'question' not in question_data:
                self.logger.warning("Response is missing required question field")
                return {
                    "question": "What are the primary factors influencing this situation?"
                }
            
            return question_data
        
        except Exception as e:
            self.logger.error(f"Failed to parse the follow-up question: {str(e)}")
            return {
                "question": "What are the primary factors influencing this situation?"
            }




