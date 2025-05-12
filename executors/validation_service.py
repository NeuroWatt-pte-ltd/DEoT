from datetime import datetime
import time
from typing import Dict, Any, Optional
from utils.logger import setup_logger
from utils.llm_loader import LLMLoader
from utils.prompt_loader import PromptLoader, PromptCategory

class ValidationService:
    """
    ValidationService handles fact-checking using LLMLoader for verification.
    """
    init_count = 0

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize ValidationService.

        :param max_retries: Maximum number of retry attempts
        :param retry_delay: Delay between retries in seconds
        """
        ValidationService.init_count += 1
        self.logger = setup_logger("ValidationService")
        self.logger.info(f"[INIT] Initializing ValidationService... (Init Count: {ValidationService.init_count})")

        # Initialize LLMLoader
        self.llm_loader = LLMLoader()

        # Initialize prompt loader
        self.prompt_loader = PromptLoader()

        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.logger.info("[INIT] ValidationService initialized successfully.")

    def validate_node_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the node content using LLMLoader.

        :param content: Task execution results (dictionary) to validate
        :return: Dictionary containing validation results and validated content
        """
        self.logger.info("[VALIDATE] Starting content validation...")

        try:
            # Ensure content is in dictionary format and contains all required fields
            if isinstance(content, str):
                content = {
                    'detailed_results': content,
                    'layer_summary': '',
                    'raw_results': [],
                    'categories': {},
                    'analysis_content': {}
                }
            else:
                # Ensure all required fields exist
                content.setdefault('detailed_results', '')
                content.setdefault('layer_summary', '')
                content.setdefault('raw_results', [])
                content.setdefault('categories', {})
                content.setdefault('analysis_content', {})

            # Prepare validation content
            validation_content = (
                "[CONTENT TO VALIDATE]\n"
                "DETAILED RESULTS:\n"
                f"{content['detailed_results']}\n\n"
                "LAYER SUMMARY:\n"
                f"{content.get('node_summary', '')}\n"
                "[END CONTENT TO VALIDATE]"
            )

            current_date = datetime.now().strftime("%Y-%m-%d")
            system_prompt = self.prompt_loader.get_prompt(
                category=PromptCategory.VALIDATION,
                prompt_name="fact_check/system",
                current_date=current_date
            )
            user_prompt = self.prompt_loader.get_prompt(
                category=PromptCategory.VALIDATION,
                prompt_name="fact_check/user",
                summary=validation_content
            )

            self.logger.debug(f"System Prompt: {system_prompt}")
            self.logger.debug(f"User Prompt: {user_prompt}")

            # Validation process
            for attempt in range(self.max_retries):
                try:
                    # Use LLMLoader for validation
                    response = self.llm_loader.chat(
                        platform="perplexity",
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model_name="llama-3.1-sonar-large-128k-online",
                        temperature=0
                    )
                    
                    raw_response = response.strip()
                    self.logger.info(f"[VALIDATE] Complete LLM Response:\n{'-'*50}\n{raw_response}\n{'-'*50}")

                    validation_result = self._parse_validation_response(raw_response)
                    if validation_result:
                        self.logger.info("[VALIDATE] Content validation completed successfully")
                    
                        # Create complete validation result with original content
                        result = {
                            "validation_status": validation_result.get("status", "VALID"),
                            "content": content,
                            "validation_results": validation_result.get("issues", []),
                            "validation_evidence": validation_result.get("evidence", [])
                        }
                    
                        return result

                    self.logger.warning(f"[VALIDATE] Attempt {attempt + 1} failed to parse response")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)

                except Exception as e:
                    self.logger.warning(f"[VALIDATE] Attempt {attempt + 1} failed: {str(e)}", exc_info=True)
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue

            # If all retries fail, return failed validation result
            self.logger.error("[VALIDATE] All validation attempts failed")
            return self._generate_failed_validation()

        except Exception as e:
            self.logger.error(f"[VALIDATE ERROR] Validation failed: {str(e)}", exc_info=True)
            return self._generate_failed_validation(str(e))

    def _parse_validation_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse the validation response.

        :param response: Raw response from LLM
        :return: Structured validation results or None if parsing fails
        """
        try:
            if '[SUMMARY VALIDATION]' not in response or '[END SUMMARY VALIDATION]' not in response:
                return None

            # Extract validation section
            validation_section = response.split('[SUMMARY VALIDATION]')[1].split('[END SUMMARY VALIDATION]')[0].strip()
            
            # Parse validation results
            result = {
                "status": "INVALID",
                "issues": [],
                "evidence": []
            }

            current_list = None
            for line in validation_section.split('\n'):
                line = line.strip()
                if not line:
                    continue

                if line.startswith('STATUS:'):
                    result["status"] = line.split(':', 1)[1].strip()
                elif line.startswith('ISSUES:'):
                    current_list = result["issues"]
                elif line.startswith('EVIDENCE:'):
                    current_list = result["evidence"]
                elif line.startswith('-') and current_list is not None:
                    current_list.append(line[1:].strip())

            return result

        except Exception as e:
            self.logger.error(f"[PARSE] Failed to parse validation response: {str(e)}")
            return None

    def _generate_failed_validation(self, error_msg: str = None) -> Dict[str, Any]:
        """
        Generate a failed validation result.

        :param error_msg: Optional error message
        :return: Failed validation dictionary
        """
        return {
            "validation_status": "FAILED",
            "content": {
                "detailed_results": "",
                "layer_summary": "",
                "raw_results": [],
                "categories": {},
                "analysis_content": {}
            },
            "validation_results": [],
            "validation_evidence": [],
            "error": error_msg or "Failed to get valid response after all retries"
        }
