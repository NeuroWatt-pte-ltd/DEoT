from typing import Union, Dict 
from datetime import datetime 
import pytz 
from agents.base import BaseAgent
from utils import PromptCategory

class NewsSearchAgent(BaseAgent):
    """NewsSearchAgent handles news search using Perplexity."""

    def __init__(self):
        """Initialize the NewsSearchAgent."""

        super().__init__(
            name="NewsSearchAgent",
            platform="perplexity",
            model_name="llama-3.1-sonar-small-128k-online",
            temperature=0
        )

        self.timezone = pytz.timezone('UTC')

    def process(self, query: str, count: int = 3) -> str:
        """
        Search for recent news about a topic.

        :param query: Search query string
        :param count: Number of news items to retrieve (default: 3)
        :return: Formatted string containing news search results and analysis 
        """

        # Process query 
        query = str(query).strip()

        # Get current date with timezone 
        now = datetime.now(self.timezone)
        today_date = now.strftime("%Y-%m-%d")

        return self.process_with_prompts(
            category=PromptCategory.NEWS_SEARCH,
            system_prompt_name="search/system",
            user_prompt_name="search/user",
            date=today_date,
            query=query,
            needed_count=count
        )
    
    
