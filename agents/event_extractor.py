from agents.base import BaseAgent
from utils import PromptCategory

class EventExtractorAgent(BaseAgent):
    """EventExtractorAgent is responsible for extracting key events and information from news articles."""

    def __init__(self):
        """Initialize the EventExtractorAgent."""
        super().__init__(
            name="EventExtractorAgent",
            platform="openai",
            model_name="gpt-4o",
            temperature=0
        )

    def process(self, text: str) -> str:
        """
        Extract key events from the provided text.

        :param text: The news articles or text to analyze
        :return: A string containing the extracted events and information
        """

        return self.process_with_prompts(
            category=PromptCategory.EVENT_EXTRACTOR,
            system_prompt_name="extract/system",
            user_prompt_name="extract/user",
            text=text 
        )
    