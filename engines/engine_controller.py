from typing import Dict, Any, Optional 
import time 
from engines.base import BaseEngine
from utils import PromptCategory

class EngineController(BaseEngine):
    """Controls the evaluation of content to determine the next analysis step."""

    # Default values for fallback responses
    DEFAULT_DECISION = "BREADTH"
    DEFAULT_RESPONSE = {
        "decision": "BREADTH",
        "questions": [],
        "layer": 1,
        "analysis_focus": None
    }

    def __init__(
            self,
            name="EngineController",
            platform="openai",
            model_name="gpt-4o",
            temperature=0,
            max_layer: int = 3,
            max_retries: int = 3,
            retry_delay: float = 1.0
    ):
        """
        Initialize the EngineController.

        :param name: Engine name
        :param platform: LLM platform to use 
        :param model_name: Name of the model to use
        :param temperature: Temperature setting
        :param max_layer: Maximum analysis depth
        :param max_retries: Maximum number of retry attempts
        :param retry_delay: Delay between retries in seconds
        """

        super().__init__(name, platform, model_name, temperature)

        self.max_layer = max_layer 
        self.max_retries = max_retries
        self.retry_delaye = retry_delay 

        self.logger.debug(
            f"[INIT] EngineController initialized with "
            f"max_layer={max_layer}, max_retries={max_retries}, "
            f"retry_delay={retry_delay}"
        )

    def process(
            self, 
            content: str,
            original_query: str,
            further_query: Optional[str] = None,
            current_layer: int = 1
    ) -> Dict[str, Any]:
        """
        Process the given content and determine the next analysis step.

        :param content: The content to be evaluated, typically containing analysis details
        :param original_query; The orginal user query
        :param further_query: Any additional query for deeper analysis
        :param current_layer: the current depth of the analysis layer
        :return: A dictionary containing the decision, questions and layer information
        """

        try:
            self.logger.info(f"Processing layer {current_layer}/{self.max_layer}...")
            self.logger.debug(f"Content to evaluate: {content[:100]}")

            # Check if the maximum analysis depth has been reached 
            if current_layer >= self.max_layer:
                self.logger.info(f"Layer {current_layer} reached max_layer {self.max_layer}")
                return {
                    "decision": "COMPLETE",
                    "questions": [],
                    "layer": current_layer,
                    "analysis_focus": None
                }
            
            # Evaluation logic with retry mechanism 
            return self._evaluate_with_retry(content, original_query, further_query, current_layer)
        
        except Exception as e:
            self.logger.error(f"Failed to process layer {current_layer}: {str(e)}")
            return self.handle_error("controller_process", e)
        
    def _evaluate_with_retry(
            self,
            content: str, 
            original_query: str,
            further_query: Optional[str],
            current_layer: int 
    ) -> Dict[str, Any]:
        """
        Evaluate content with retry mechanism.

        :param content: Content to evaluate
        :param orignal_query: Original user query
        :param further_query: Additional query for deeper analysis
        :param current_layer: Current analysis layer
        :return: Evaluation decision
        """

        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Evaluation attempt {attempt + 1}/{self.max_retries}")

                response = self.process_with_prompts(
                    category=PromptCategory.ENGINE_CONTROLLER,
                    system_prompt_name="evaluate/system",
                    user_prompt_name="evaluate/user",
                    original_query=original_query,
                    further_query=further_query or "None",
                    current_layer=current_layer,
                    max_layer=self.max_layer,
                    content=content
                )

                self.logger.debug(f"Response: {response}")

                decision = self._parse_decision(response, current_layer)
                if decision.get("decision") not in {"BREADTH", "DEPTH", "COMPLETE"}:
                    raise ValueError(f"Invalid decision: {decision.get('decision')}")
                
                self.logger.info(f"Layer {current_layer}: {decision['decision']}")
                return decision 
            
            except Exception as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries} failed: {str(e)}"
                )

                if attempt < self.max_retries - 1:
                    self.logger.debug(f"Waiting {self.retry_delay} seconds before retry...")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error(
                        f"All {self.max_retries} attempts failed. "
                        f"Using default decision: {self.DEFAULT_DECISION}"
                    )
                    return {
                        **self.DEFAULT_RESPONSE,
                        "layer": current_layer
                    }
                
    def _parse_decision(self, response: str, current_layer: int) -> Dict[str, Any]:
        """
        Parse the LLM response into a structured decision dictionary.

        :param response: The raw response string from the LLM
        :param current_layer: The current layer number for fallback
        :return: A dictionary containing the decision, reasoning, questions, and layer information
        """

        try:
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            decision = {
                'layer': current_layer,
                'questions': [],
                'analysis_focus': None 
            }

            current_section = None 
            questions = []

            for line in lines:
                if line.startswith('Decision:'):
                    decision['decision'] = line.split(':', 1)[1].strip()
                    current_section = 'decision'
                elif line.startswith('Questions:'):
                    current_section = 'questions'
                elif line.startswith('Analysis Focus:'):
                    decision['analysis_focus'] = line.split(':', 1)[1].strip()
                    current_section = 'focus'
                elif current_section == 'questions' and line.startswith('- '):
                    questions.append(line[2:].strip())

            decision['questions'] = questions

            # Validate required fields 
            required_fields = {'decision', 'layer', 'questions', 'analysis_focus'}
            if not all(field in decision for field in required_fields):
                missing = required_fields - set(decision.keys())
                raise ValueError(f"Missing fields: {missing}")

            self.logger.info(f"Decision: {decision}")
            return decision
        
        except Exception as e:
            self.logger.error(f"Failed to parse decision: {str(e)}")
            self.logger.error(f"Response: {response}")
            return {
                **self.DEFAULT_RESPONSE,
                "layer": current_layer
            }

