from typing import Union, Dict 
from datetime import datetime
import pytz 
from agents.base import BaseAgent
from utils import PromptCategory

class InfoSearchAgent(BaseAgent):
    """InforSearchAgent handles supplementary information search using Perplexity."""

    def __init__(self):
        """Initialize the InfoSearchAgent."""

        super().__init__(
            name="InfoSearchAgent",
            platform="perplexity",
            model_name="llama-3.1-sonar-small-128k-online",
            temperature=0
        )

        self.timezone = pytz.timezone('UTC')
    
    def process(self, query: Union[str, Dict]) -> str:
        """
        Search for comprehensive information about a topic.

        :param query: Search query string or dict with query information
        :return: Formatted string containign search results and analysis
        """

        # Process query
        if isinstance(query, dict):
            query = query.get('query', '')
        query = str(query).strip()

        # Get current date with timezone 
        now = datetime.now(self.timezone)
        today_date = now.strftime("%Y-%m-%d")

        return self.process_with_prompts(
            category=PromptCategory.INFO_SEARCH,
            system_prompt_name="search/system",
            user_prompt_name="search/user",
            date=today_date,
            query=query 
        )
    
    
