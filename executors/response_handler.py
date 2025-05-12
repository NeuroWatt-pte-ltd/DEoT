from typing import Dict, Any 
from datetime import datetime 
import json
from utils import setup_logger, LLMLoader, PromptCategory, PromptLoader

class ResponseHandler:
    """Handler for generating the final response by integrating analysis results from multiple nodes."""

    def __init__(self, platform="openai", model_name="gpt-4o", temperature=0):
        """Initialize the response handler."""

        self.logger = setup_logger("ResponseHandler")
        self.logger.debug("Initializing ResponseHandler")

        self.llm_loader = LLMLoader()
        self.platform = platform
        self.model_name = model_name
        self.temperature = temperature

        # Initialize prompt loader
        self.prompt_loader = PromptLoader()
        self.logger.debug("ResponseHandler initialized successfully")

    def generate_response(
            self,
            original_query: str,
            summaries: Dict[str, Any],
            stats: Dict[str, Any]
    ) -> str:
        """
        Generate the final comprehensive response.

        :param original_query: The original user query
        :param summaries: Summary collection from SummaryManager
        :param stats: Analysis statistics
        :return: The generated comprehensive response text
        """

        try:
            # Get node summaries from the summary data
            node_summaries = summaries.get("node_summaries", [])
            self.logger.debug(f"Processing {len(node_summaries)} node summaries")

            # Sort summaries by layer
            node_summaries = sorted(node_summaries, key=lambda x: (x.get("layer", 0), x.get("timestamp", "")))
            
            # Try with decreasing number of nodes in case of token limit errors
            max_retries = 5
            nodes_to_use = len(node_summaries)
            
            for retry in range(max_retries):
                try:
                    # Use a subset of nodes if we've had to retry
                    current_nodes = node_summaries[:nodes_to_use]
                    self.logger.debug(f"[RESPONSE] Attempt {retry+1}: Using {len(current_nodes)} of {len(node_summaries)} nodes")
                    
                    # Format node summaries for LLM use
                    formatted_summaries = []
                    
                    for summary in current_nodes:
                        node_id = summary.get("node_id", "unknown")
                        layer = summary.get("layer", 0)
                        node_type = summary.get("node_type", "Unknown")
                        content = summary.get("content", "").strip()
                        
                        if content:
                            # Add node identifier and summary content
                            formatted_summary = (
                                f"--- Node {node_id} (Layer {layer}, Type: {node_type}) ---\n"
                                f"{content}\n"
                            )
                            formatted_summaries.append(formatted_summary)
                            self.logger.debug(f"[RESPONSE] Added node summary {node_id}")
                        else:
                            self.logger.warning(f"[RESPONSE] Node {node_id} has no summary content")
                    
                    combined_summaries = "\n".join(formatted_summaries)
                    
                    # Get prompts using PromptLoader
                    system_prompt = self.prompt_loader.get_prompt(
                        category=PromptCategory.RESPONSE,
                        prompt_name="final_response/system"
                    )
                    
                    user_prompt = self.prompt_loader.get_prompt(
                        category=PromptCategory.RESPONSE,
                        prompt_name="final_response/user",
                        original_query=original_query,
                        node_summaries=combined_summaries,
                        total_nodes=stats.get("total_nodes", 0),
                        max_depth=stats.get("max_depth", 0),
                        breadth_analyses=stats.get("breadth_analyses", 0),
                        depth_analyses=stats.get("depth_analyses", 0)
                    )

                    # Generate response using LLMLoader 
                    self.logger.info("Generating final response")
                    self.logger.debug(f"System Prompt: {system_prompt}")
                    self.logger.debug(f"User Prompt: {user_prompt}")

                    response = self.llm_loader.chat(
                        platform=self.platform,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model_name=self.model_name,
                        temperature=self.temperature
                    )

                    self.logger.debug(f"Response: {response}")

                    return response 
                
                except Exception as e:
                    error_msg = str(e).lower()
                    # Check if this is a token limit error
                    if "context_length_exceeded" in error_msg:
                        self.logger.warning(f"[TOKEN ERROR] Context length exceeded with {nodes_to_use} nodes: {str(e)}")
                        
                        # Reduce the number of nodes for the next attempt
                        nodes_to_use = max(1, nodes_to_use - 1)
                        
                        if retry == max_retries - 1:
                            # Last attempt failed
                            self.logger.error("[RETRY EXHAUSTED] Could not generate response within token limits")
                            return "I apologize, but your query resulted in a very comprehensive analysis that exceeds my processing limits. Please try a more specific query or break your question into smaller parts."
                    else:
                        # Not a token limit error, reraise
                        raise

            # Should not reach here, but just in case
            return "Unable to generate a response due to technical limitations. Please try a different query."

        except Exception as e:
            self.logger.error(f"[GENERATE ERROR] Failed to generate response: {str(e)}", exc_info=True)
            return f"An error occurred during analysis. Please try your query again. Error details: {str(e)}"

