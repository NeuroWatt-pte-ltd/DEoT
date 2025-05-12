from agents.base import BaseAgent
from utils import PromptCategory

class HistoryAnalyzerAgent(BaseAgent):
    """HistoryAnalyzerAgent provides historical analysis of events."""

    def __init__(self):
        """Initialize the HistoryAnalyzerAgent."""

        super().__init__(
            name="HistoryAnalyzerAgent",
            platform="openai",
            model_name="gpt-4o",
            temperature=0 
        )

    def process(self, event: str):
        """
        Analyze an event by comparing it with historical parallels.

        :param event: The event to analyze
        :return: Analysis including historical parallels and insights
        """

        return self.process_with_prompts(
            category=PromptCategory.HISTORY_ANALYZER,
            system_prompt_name="analyze/system",
            user_prompt_name="analyze/user",
            event=event 
        )
    
    
    
