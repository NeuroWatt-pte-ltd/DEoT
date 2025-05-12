from agents.base import BaseAgent
from utils import PromptCategory

class ReasoningAgent(BaseAgent):
    """ReasoningAgent provides direct LLM reasoning and responses."""

    def __init__(self):
        """Initialize the ReasoningAgent."""

        super().__init__(
            name="ReasoningAgent",
            platform="openai",
            model_name="gpt-4o",
            temperature=0
        )

    def process(self, query: str) -> str:
        """
        Process a reasoning query.

        :param query: The query to analyze
        :return: Reasoned response from LLM
        """

        return self.process_with_prompts(
            category=PromptCategory.REASONING,
            system_prompt_name="reason/system",
            user_prompt_name="reason/user",
            query=query 
        )
    