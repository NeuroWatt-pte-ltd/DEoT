from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import json
import re
from dotenv import load_dotenv

from utils.logger import setup_logger
from executors.executor import Executor
from visualization import MermaidGenerator


# Load environment variables
load_dotenv()


class DualEngineAnalyzer:
    """
    Main entry point for the dual-engine thinking analysis system.
    Integrates execution and visualization components into a cohesive analysis framework.
    """
    
    def __init__(
        self, 
        max_layer: int = None, 
        max_nodes: int = None, 
        platform: str = None, 
        model_name: str = None, 
        temperature: float = None,
        output_dir: str = None,
        enable_validation: bool = None  # Add validation mode parameter
    ):
        """
        Initialize dual engine analyzer with configuration parameters.
        Values from .env file take precedence over defaults.
        
        :param max_layer: Maximum depth of analysis layers
        :param max_nodes: Maximum number of analysis nodes
        :param platform: LLM platform to use (openai, perplexity)
        :param model_name: Name of the model to use
        :param temperature: Temperature setting for LLM generation
        :param output_dir: Directory for storing analysis outputs
        :param enable_validation: Whether to enable validation mode
        """
        self.logger = setup_logger("DualEngineAnalyzer")
        self.logger.debug("Initializing DualEngineAnalyzer...")
        
        # Get configurations from environment variables with fallbacks
        self.max_layer = max_layer or int(os.getenv("MAX_LAYER", 3))
        self.max_nodes = max_nodes or int(os.getenv("MAX_NODES", 15))
        self.platform = platform or os.getenv("LLM_PLATFORM", "openai")
        self.model_name = model_name or os.getenv("LLM_MODEL", "gpt-4o")
        self.temperature = temperature or float(os.getenv("LLM_TEMPERATURE", 0.3))
        self.output_dir = output_dir or os.getenv("OUTPUT_DIR", "output")
        self.enable_validation = enable_validation if enable_validation is not None else bool(os.getenv("ENABLE_VALIDATION", False))
        
        # Log configuration details
        self.logger.debug(f"Analysis parameters: Max Layer: {self.max_layer}, Max Nodes: {self.max_nodes}, Validation: {self.enable_validation}")
        
        # Initialize component services
        self.executor = Executor(
            max_layer=self.max_layer, 
            max_nodes=self.max_nodes, 
            platform=self.platform,
            model_name=self.model_name,
            temperature=self.temperature,
            enable_validation=self.enable_validation  # Pass validation mode to executor
        )
        
        # The visualizer will be initialized for each analysis with its specific output directory
        self.visualizer = None
        
        # Create main output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.logger.debug(f"Output directory: {self.output_dir}")
        
        self.logger.debug("DualEngineAnalyzer initialized successfully")
    
    def analyze(
        self, 
        query: str, 
        use_cache: bool = False,  # Parameter kept for backward compatibility but not used
        generate_visualization: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze a query using the dual-engine thinking approach.
        
        :param query: The user query to analyze
        :param use_cache: Ignored parameter (kept for compatibility)
        :param generate_visualization: Whether to generate visualization
            
        :return: Analysis result dictionary with final response and metadata
        """
        # Start the analysis process
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create analysis-specific directory
        analysis_dir = self._create_analysis_directory(analysis_id, query)
        
        self.logger.debug(f"Starting new analysis: {analysis_id}")
        self.logger.info("Starting new analysis")
        self.logger.info(f"Processing query: {query}")
        
        try:
            # Initialize visualizer with analysis directory
            self.visualizer = MermaidGenerator(output_dir=analysis_dir)
            
            # Log analysis configuration
            self.logger.debug(f"Analysis configuration: max_layer={self.max_layer}, max_nodes={self.max_nodes}, platform={self.platform}, model={self.model_name}")
            
            # 1. Process query with executor
            self.logger.debug("Starting query execution")
            execution_result = self.executor.process_query(query, analysis_dir)
            
            # Update analysis_id to match executor's ID
            analysis_id = execution_result.get("analysis_id", analysis_id)
            
            # Log execution completion
            node_count = len(execution_result.get("visualization_data", {}).get("nodes", []))
            edge_count = len(execution_result.get("visualization_data", {}).get("edges", []))
            stats = execution_result.get("stats", {})
            self.logger.debug(f"Execution completed with {node_count} nodes and {edge_count} edges. Max depth: {stats.get('max_depth', 0)}")
            
            # 2. Generate visualization if enabled
            visualization_data = None
            if generate_visualization:
                self.logger.debug("[VISUALIZE] Generating visualization")
                viz_data = execution_result.get("visualization_data", {})
                visualization_result = self.visualizer.generate(viz_data, analysis_id)
                
                visualization_data = {
                    "mermaid_file": visualization_result.get("mermaid_file", ""),
                    "mermaid_code": visualization_result.get("mermaid_code", ""),
                    "metadata": visualization_result.get("metadata", {})
                }
                
                # Log visualization completion
                self.logger.debug(f"Visualization generated with {len(viz_data.get('nodes', []))} nodes and {len(viz_data.get('edges', []))} edges")
            
            # 3. Prepare complete result
            result = {
                "analysis_id": analysis_id,
                "query": query,
                "optimized_query": execution_result.get("optimized_query", ""),
                "response": execution_result.get("final_response", ""),
                "stats": execution_result.get("stats", {}),
                "visualization": visualization_data,
                "output_directory": analysis_dir,
                "timestamp": datetime.now().isoformat()
            }
            
            # 4. Save result
            self._save_result(result, analysis_id, analysis_dir)
            
            # Log analysis completion
            response_length = len(result.get("response", ""))
            execution_time = (datetime.now() - datetime.fromisoformat(result["timestamp"])).total_seconds()
            self.logger.debug(f"Analysis completed with {response_length} chars response in {execution_time:.2f} seconds")
            
            return result
            
        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            self.logger.error(f"Error: {error_msg}", exc_info=True)
            
            # Log error details
            self.logger.error(f"Stack trace: {self._get_stack_trace(e)}", exc_info=True)
            
            return {
                "analysis_id": analysis_id,
                "query": query,
                "error": error_msg,
                "output_directory": analysis_dir,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_analysis_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent analysis history.
        
        :param limit: Maximum number of history items to return
        :return: List of recent analysis metadata
        """
        try:
            history = []
            analysis_dirs = self._get_analysis_directories()
            
            # Sort directories by modification time (newest first)
            analysis_dirs.sort(key=lambda d: os.path.getmtime(d), reverse=True)
            
            # Limit the number of directories
            analysis_dirs = analysis_dirs[:limit]
            
            for analysis_dir in analysis_dirs:
                try:
                    # Look for the main analysis file
                    analysis_id = os.path.basename(analysis_dir)
                    file_path = os.path.join(analysis_dir, f"{analysis_id}.json")
                    
                    if not os.path.exists(file_path):
                        # Try to find any .json file
                        json_files = [f for f in os.listdir(analysis_dir) if f.endswith('.json')]
                        if json_files:
                            file_path = os.path.join(analysis_dir, json_files[0])
                        else:
                            continue
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)
                        
                    # Include only necessary metadata
                    history.append({
                        "analysis_id": analysis_data.get("analysis_id", ""),
                        "query": analysis_data.get("query", ""),
                        "timestamp": analysis_data.get("timestamp", ""),
                        "directory": analysis_dir,
                        "file_path": file_path
                    })
                except Exception as e:
                    self.logger.warning(f"Failed to read analysis directory {analysis_dir}: {str(e)}")
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get analysis history: {str(e)}", exc_info=True)
            return []
    
    def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific analysis by ID.
        
        :param analysis_id: Analysis identifier
        :return: Analysis data dictionary or None if not found
        """
        try:
            # First try to find the analysis directory
            analysis_dir = os.path.join(self.output_dir, analysis_id)
            if os.path.isdir(analysis_dir):
                file_path = os.path.join(analysis_dir, f"{analysis_id}.json")
            else:
                # Fall back to old path format
                file_path = os.path.join(self.output_dir, f"{analysis_id}.json")
            
            if not os.path.exists(file_path):
                self.logger.warning(f"Analysis file not found for ID: {analysis_id}")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
                
            return analysis_data
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve analysis {analysis_id}: {str(e)}", exc_info=True)
            return None
    
    def _create_analysis_directory(self, analysis_id: str, query: str) -> str:
        """
        Create a directory for the specific analysis.
        
        :param analysis_id: Analysis identifier
        :param query: The user query
            
        :return: Path to the created directory
        """
        try:
            # Create a sanitized version of the query for the directory name
            query_part = self._sanitize_for_path(query)[:50]  # Limit length
            
            # Create directory name
            analysis_dir = os.path.join(self.output_dir, analysis_id)
            
            # Create the directory
            os.makedirs(analysis_dir, exist_ok=True)
            
            self.logger.debug(f"Created analysis directory: {analysis_dir}")
            return analysis_dir
            
        except Exception as e:
            self.logger.error(f"Failed to create analysis directory: {str(e)}", exc_info=True)
            # Fall back to the main output directory
            return self.output_dir
    
    def _sanitize_for_path(self, text: str) -> str:
        """
        Sanitize text to be used in file paths.
        
        :param text: Text to sanitize
        :return: Sanitized text
        """
        # Replace invalid path characters
        sanitized = re.sub(r'[\\/*?:"<>|]', '_', text)
        # Replace spaces and collapse multiple underscores
        sanitized = re.sub(r'\s+', '_', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        return sanitized.strip('_')
    
    def _save_result(self, result: Dict[str, Any], analysis_id: str, analysis_dir: str) -> str:
        """
        Save analysis result to a file.
        
        :param result: Analysis result dictionary
        :param analysis_id: Analysis identifier
        :param analysis_dir: Analysis directory
        :return: Path to the saved file
        """
        try:
            file_path = os.path.join(analysis_dir, f"{analysis_id}.json")
            
            # Add generation timestamps
            result["generated_at"] = {
                "start_time": result.get("timestamp"),
                "end_time": datetime.now().isoformat()
            }
            
            # Process mermaid_code, remove excessive line breaks
            if "visualization" in result and "mermaid_code" in result["visualization"]:
                result["visualization"]["mermaid_code"] = result["visualization"]["mermaid_code"].replace("\n\n", "\n")
            
            # Add detailed execution information
            result["execution_info"] = {
                "platform": self.platform,
                "model": self.model_name,
                "temperature": self.temperature,
                "max_layer": self.max_layer,
                "max_nodes": self.max_nodes
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
                
            self.logger.debug(f"Analysis result saved to {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Failed to save analysis result: {str(e)}", exc_info=True)
            return ""
    
    def _get_analysis_directories(self) -> List[str]:
        """
        Get list of analysis directories.
        
        :return: List of directory paths
        """
        try:
            dirs = []
            
            for item in os.listdir(self.output_dir):
                item_path = os.path.join(self.output_dir, item)
                if os.path.isdir(item_path) and item.startswith('analysis_'):
                    dirs.append(item_path)
                    
            return dirs
            
        except Exception as e:
            self.logger.error(f"Failed to list analysis directories: {str(e)}", exc_info=True)
            return []
    
    def _get_analysis_files(self) -> List[str]:
        """
        Get list of analysis output files (legacy method).
        
        :return: List of file paths
        """
        try:
            files = []
            
            # Check both top-level files and files in analysis directories
            for filename in os.listdir(self.output_dir):
                if filename.endswith('.json') and filename.startswith('analysis_'):
                    files.append(os.path.join(self.output_dir, filename))
                
                # Check if this is a directory
                dir_path = os.path.join(self.output_dir, filename)
                if os.path.isdir(dir_path) and filename.startswith('analysis_'):
                    for inner_file in os.listdir(dir_path):
                        if inner_file.endswith('.json'):
                            files.append(os.path.join(dir_path, inner_file))
                    
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to list analysis files: {str(e)}", exc_info=True)
            return []

    def _get_stack_trace(self, error: Exception) -> str:
        """
        Get formatted stack trace from exception.
        
        :param error: Exception to format
        :return: Formatted stack trace as string
        """
        import traceback
        return "".join(traceback.format_exception(type(error), error, error.__traceback__))


