from typing import Dict, Any, List 
from engines.base import BaseEngine
from utils import PromptCategory

class BreadthEngine(BaseEngine):
    """
    BreadthEngine analyzes the broader impact dimensions of a topic or event.
    It identifies different aspcets that might be affected and generate queries for each aspect.
    """

    def __init__(
          self, 
          name="BreadthEngine",
          platform="openai",
          model_name="gpt-4o",
          temperature=0,
          max_aspects: int =3  
    ):
        """Initialize the BreadthEngine"""
        super().__init__(
            name,
            platform,
            model_name,
            temperature
        )

        self.max_aspects = max_aspects 
        self.logger.debug(f"BreadthEngine initialized with max_aspects = {max_aspects}")

    def process(
            self, 
            node_summary: str,
            original_query: str, 
            max_aspects: int = None 
    ) -> List[Dict[str, Any]]:
        """
        Analyze content for braoder impact aspects.

        :param node_summary: Summary of the node to analyze 
        :param original_query: Original user query 
        :param max_aspects: Maximum number of aspects to analyze
        :return: List of impact aspects with their details
        """

        try:
            # Use provided max_aspects or fall back to instance attribute 
            if max_aspects is None:
                max_aspects = self.max_aspects
            
            response = self.process_with_prompts(
                category=PromptCategory.BREADTH_ANALYSIS,
                system_prompt_name="analyze/system",
                user_prompt_name="analyze/user",
                content=node_summary,
                original_query=original_query,
                max_aspects=max_aspects
            )

            aspects = self._parse_aspects(response)
            self.logger.info(f"Identified {len(aspects)} impact aspects")
            self.logger.debug(f"Aspects: {aspects}")

            return aspects
        
        except Exception as e:
            return self.handle_error("analyze", e)
        
    def _parse_aspects(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse the response from LLM into structured impact aspects.

        :param response: Raw response from LLM
        :retrun: List of impact aspects with their details
        """

        try:
            # Split response into aspect blocks
            blocks = response.strip().split("\n\n")
            aspects = []

            for block in blocks:
                if not block.strip():
                    continue
            
                try:
                    lines = block.strip().split("\n")
                    aspect = {}

                    for line in lines:
                        if line.startswith("Aspect:"):
                            aspect['name'] = line.split(':', 1)[1].strip()
                        elif line.startswith('Query:'):
                            aspect['query'] = line.split(':', 1)[1].strip()

                    # Validate required fields 
                    if all(field in aspect for field in {'name', 'query'}):
                        aspects.append(aspect)
                
                except Exception as e:
                    self.logger.warning(f"Failed to parse aspcet block: {str(e)}")
                    continue 

            if not aspects:
                self.logger.warning("No valid aspects found in response")
                return []
            
            return aspects 
        
        except Exception as e:
            self.logger.error(f"Failed to parse aspects: {str(e)}")
            return []
        
        