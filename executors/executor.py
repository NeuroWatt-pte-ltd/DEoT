from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import json
from utils.logger import setup_logger
from prompters.input_prompter import InputPrompter
from prompters.task_prompter import TaskPrompter
from executors.node_generator import NodeGenerator
from executors.summary_manager import SummaryManager
from executors.response_handler import ResponseHandler
from executors.validation_service import ValidationService
from engines.engine_controller import EngineController
from engines.breadth_engine import BreadthEngine
from engines.depth_engine import DepthEngine


class ResourceManager:
    """Manages resources and limits during analysis."""
    def __init__(self, max_nodes: int = 50, max_layer: int = 5):
        self.max_nodes = max_nodes
        self.max_layer = max_layer
        self.current_nodes = 0

    def reset(self):
        """Reset current node count."""
        self.current_nodes = 0

    def increment_nodes(self):
        """Increment node count."""
        self.current_nodes += 1

    def can_add_node(self, layer: int) -> bool:
        """Check if adding a node is possible."""
        return (self.current_nodes < self.max_nodes and 
                layer <= self.max_layer)


class Executor:
    """Coordinates the dual-engine thinking analysis workflow."""

    def __init__(self, max_layer: int = 3, max_nodes: int = 15, platform="openai", model_name="gpt-4o", temperature=0.3, output_dir="output", enable_validation: bool = False):
        """
        Initialize Executor and its dependencies.
        
        :param max_layer: Maximum depth of analysis layers
        :param max_nodes: Maximum number of analysis nodes
        :param platform: LLM platform to use
        :param model_name: Name of the model to use
        :param temperature: Temperature setting for LLM generation
        :param output_dir: Directory for storing analysis outputs
        :param enable_validation: Whether to enable validation mode
        """
        self.logger = setup_logger("Executor")
        self.logger.debug("Initializing Executor...")
        
        # Configure output directory
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger.debug(f"Output directory: {self.output_dir}")
        
        # Initialize components
        self.input_prompter = InputPrompter()
        self.task_prompter = TaskPrompter()
        self.node_generator = NodeGenerator()
        self.summary_manager = SummaryManager()
        self.engine_controller = EngineController(max_layer=max_layer)
        self.breadth_engine = BreadthEngine()
        self.depth_engine = DepthEngine()
        self.response_handler = ResponseHandler(platform=platform, model_name=model_name, temperature=temperature)
        
        # Initialize validation service if enabled
        self.enable_validation = enable_validation
        self.validation_service = ValidationService() if enable_validation else None
        if enable_validation:
            self.logger.info("Validation mode enabled")
        
        # Initialize resource manager
        self.resource_manager = ResourceManager(max_nodes=max_nodes, max_layer=max_layer)
        
        # Initialize visualization data
        self.visualization_data = self._reset_visualization()
        
        self.logger.debug("All components initialized successfully")

    def process_query(self, query: str, analysis_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Process user query and generate complete analysis.
        
        :param query: Original user query
        :param analysis_dir: Specific directory for this analysis, if None one will be created
        :return: Dictionary containing analysis results and visualization data
        """
        try:
            # Create unique analysis ID
            analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.logger.info("Processing analysis")
            self.logger.debug(f"Processing analysis {analysis_id}")
            self.logger.info(f"Original query: {query}")
            
            # Create or use specified analysis directory
            if not analysis_dir:
                analysis_dir = os.path.join(self.output_dir, analysis_id)
                os.makedirs(analysis_dir, exist_ok=True)
                self.logger.debug(f"[DIR] Created analysis directory: {analysis_dir}")
            
            # Reset state for new analysis
            self.resource_manager.reset()
            self._reset_visualization()
            self.summary_manager.start_new_analysis(analysis_id)
            self.logger.debug("[RESET] Analysis state reset complete")

            # 1. Optimize query
            optimization_result = self.input_prompter.process(query)

            # 2. Break down tasks using Task Prompter
            tasks = self.task_prompter.process(optimization_result.get("optimized_query", query))

            # 3. Generate and process initial node
            initial_node_id = f"{analysis_id}_root"
            self.logger.debug(f"[NODE] Processing root node: {initial_node_id}")
            
            # Extract optimized query and original query
            optimized_query = optimization_result.get("optimized_query", query)
            original_query = optimization_result.get("original_query", query)
            modifications = optimization_result.get("modifications", [])

            # Create initial node with tasks
            initial_node = {
                "node_id": initial_node_id,
                "type": "ROOT",
                "layer": 1,
                "query": optimized_query,
                "original_query": original_query,
                "optimized_query_data": optimization_result,
                "tasks": tasks,
                "child_nodes": [],
                "timestamp": datetime.now().isoformat()
            }

            # 4. Process tasks and generate node summary
            node_data = self.node_generator.generate_node({
                'query': optimized_query,
                'node_id': initial_node_id,
                'layer': 1,
                'tasks': tasks,
                'context': {},
                'type': 'ROOT'
            })
            
            initial_node["node_summary"] = node_data.get('node_summary', '')
            
            # 5. Get engine controller decision
            decision = self.engine_controller.process(
                content=node_data.get('node_summary', ''),
                original_query=original_query,
                further_query=optimized_query,
                current_layer=1
            )
            
            # Update node with decision
            initial_node["type"] = decision.get("decision", "ROOT")
            initial_node["engine_decision"] = {
                "type": decision.get("decision", "ROOT"),
                "focus": decision.get("analysis_focus"),
                "questions": decision.get("questions", [])
            }

            # Count root node
            self.resource_manager.increment_nodes()
            self.logger.debug(f"[NODES] Root node created. Node count: 1/{self.resource_manager.max_nodes}")

            # 6. Process analysis tree
            self.logger.debug("[ANALYSIS] Starting analysis tree processing")
            self._process_node_children(initial_node, original_query, 1)
            self._add_to_visualization(initial_node)
            
            # Log analysis completion
            self.logger.info(f"[ANALYSIS] Analysis completed with {self.resource_manager.current_nodes} nodes at max depth {self._get_max_depth(initial_node)}")

            # Get analysis statistics
            summaries = self.summary_manager.get_summaries(analysis_id)
            stats = self.summary_manager.get_analysis_stats(analysis_id)
            self.logger.debug(f"[STATS] Analysis statistics completed")

            # Generate final response
            self.logger.info("Generating final response")
            final_response = self.response_handler.generate_response(
                original_query=original_query,
                summaries=summaries,
                stats=stats
            )
            self.logger.info(f"Response generated")
            
            # Prepare results
            result = {
                "analysis_id": analysis_id,
                "original_query": original_query,
                "optimized_query": optimized_query,
                "optimization_data": optimization_result,
                "final_response": final_response,
                "stats": stats,
                "visualization_data": self.visualization_data,
                "output_directory": analysis_dir,
                "timestamp": datetime.now().isoformat(),
                "analysis_metrics": {
                    "total_nodes": self.resource_manager.current_nodes,
                    "max_depth": self._get_max_depth(initial_node),
                    "max_nodes": self.resource_manager.max_nodes,
                    "max_layer": self.resource_manager.max_layer
                }
            }
            
            self.logger.debug(f"Analysis {analysis_id} completed successfully")
            self.logger.info(f"Analysis completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"[ERROR] Analysis failed: {str(e)}", exc_info=True)
            return {
                "analysis_id": f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "original_query": query,
                "error": str(e),
                "status": "failed",
                "output_directory": analysis_dir if 'analysis_dir' in locals() else None,
                "timestamp": datetime.now().isoformat()
            }

    def _validate_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate node content if validation is enabled.
        
        :param node_data: Node data to validate
        :return: Validated node data
        """
        if not self.enable_validation or not self.validation_service:
            # If validation is disabled, store summary and return node data
            node_data['validation_status'] = 'VALID'  # When validation is disabled, mark as VALID
            self.node_generator.store_node_summary(node_data)
            return node_data

        self.logger.info(f"[VALIDATE] Validating node: {node_data.get('node_id', 'unknown')}")
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            validation_result = self.validation_service.validate_node_content(node_data)
            
            if validation_result["validation_status"] == "VALID":
                self.logger.info(f"[VALIDATE] Node validation successful")
                # Store summary only after successful validation
                node_data['validation_status'] = 'VALID'
                self.node_generator.store_node_summary(node_data)
                return node_data
            else:
                retry_count += 1
                self.logger.warning(f"[VALIDATE] Node validation failed (attempt {retry_count}/{max_retries}): {validation_result.get('validation_results', [])}")
                
                if retry_count < max_retries:
                    # Try to regenerate the node content
                    self.logger.info(f"[REGENERATE] Attempting to regenerate node content (attempt {retry_count + 1})")
                    try:
                        # Extract the original query and context
                        query = node_data.get('query', '')
                        node_id = node_data.get('node_id', '')
                        layer = node_data.get('layer', 1)
                        node_type = node_data.get('type', 'BREADTH')
                        context = node_data.get('context', {})
                        
                        # Regenerate node with the same parameters
                        regenerated_data = self.node_generator.generate_node({
                            'query': query,
                            'node_id': node_id,
                            'layer': layer,
                            'context': context,
                            'type': node_type
                        })
                        
                        # Update node_data with regenerated content
                        node_data = regenerated_data
                        
                    except Exception as e:
                        self.logger.error(f"[REGENERATE] Failed to regenerate node content: {str(e)}", exc_info=True)
                        if retry_count == max_retries - 1:
                            node_data['validation_status'] = 'INVALID'
                            self.node_generator.store_node_summary(node_data)
                            return None
                else:
                    self.logger.error(f"[VALIDATE] All {max_retries} validation attempts failed")
                    node_data['validation_status'] = 'INVALID'
                    self.node_generator.store_node_summary(node_data)
                    return None

        return None

    def _process_node_children(self, node: Dict[str, Any], original_query: str, current_layer: int):
        """
        Process child nodes based on the parent node's decision.
        
        :param node: Parent node data
        :param original_query: Original user query
        :param current_layer: Current depth layer
        """
        # Check basic limits
        if current_layer >= self.resource_manager.max_layer:
            self.logger.debug(f"[LIMIT] Reached max layer {self.resource_manager.max_layer}, stopping generation")
            return

        if not self.resource_manager.can_add_node(current_layer):
            self.logger.debug(f"[LIMIT] Reached node limit ({self.resource_manager.current_nodes}/{self.resource_manager.max_nodes}), stopping generation")
            return

        node_type = node["engine_decision"]["type"]
        
        if node_type == "COMPLETE":
            self.logger.debug(f"[COMPLETE] Analysis complete for node {node['node_id']}")
            return
        
        if node_type == "BREADTH":
            self.logger.debug(f"[BREADTH] Processing breadth analysis for node {node['node_id']}")
            self._process_breadth_node(node, original_query, current_layer)
        elif node_type == "DEPTH":
            self.logger.debug(f"[DEPTH] Processing depth analysis for node {node['node_id']}")
            self._process_depth_node(node, original_query, current_layer)

    def _process_breadth_node(self, node: Dict[str, Any], original_query: str, current_layer: int):
        """
        Process breadth analysis node.
        
        :param node: Breadth node to process
        :param original_query: Original user query
        :param current_layer: Current depth layer
        """
        aspects = self.breadth_engine.process(
            node_summary=node.get('node_summary', ''),
            original_query=original_query
        )
        
        self.logger.info(f"[BREADTH] Generated {len(aspects)} aspects for analysis")
        
        for i, aspect in enumerate(aspects, 1):
            # Check if we can add a new node
            if not self.resource_manager.can_add_node(current_layer + 1):
                self.logger.debug(f"[LIMIT] Reached node limit ({self.resource_manager.current_nodes}/{self.resource_manager.max_nodes}), stopping generation")
                return
                
            child_node_id = f"{node['node_id']}_breadth_{i}"
            self.logger.debug(f"[BREADTH] Processing aspect {i}: {aspect.get('query', '')}")
            
            # Generate child node
            child_node = {
                "node_id": child_node_id,
                "type": "DEPTH",  # Child nodes of breadth nodes default to depth nodes
                "layer": current_layer + 1,
                "query": aspect.get('query', ''),
                "parent_id": node['node_id'],
                "child_nodes": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # 1. Task Decomposition
            tasks = self.task_prompter.process(aspect.get('query', ''))
            
            # 2. Generate node summary
            node_data = self.node_generator.generate_node({
                'query': aspect.get('query', ''),
                'node_id': child_node_id,
                'layer': current_layer + 1,
                'tasks': tasks,
                'context': {},
                'type': "DEPTH"
            })
            
            # 3. Validate node if validation is enabled
            if self.enable_validation:
                validated_data = self._validate_node(node_data)
                if not validated_data:
                    self.logger.warning(f"[VALIDATE] Skipping invalid node: {child_node_id}")
                    continue
                node_data = validated_data
            
            child_node["node_summary"] = node_data.get('node_summary', '')
            
            # 4. Get engine decision
            decision = self.engine_controller.process(
                content=node_data.get('node_summary', ''),
                original_query=original_query,
                further_query=aspect.get('query', ''),
                current_layer=current_layer + 1
            )
            
            # Update node type and decision information
            child_node["type"] = decision.get("decision", "DEPTH")
            child_node["engine_decision"] = {
                "type": decision.get("decision", "DEPTH"),
                "focus": decision.get("analysis_focus"),
                "questions": decision.get("questions", [])
            }
            
            # Increment node count
            self.resource_manager.increment_nodes()
            self.logger.debug(f"[NODES] Node created: {child_node_id}. Node count: {self.resource_manager.current_nodes}/{self.resource_manager.max_nodes}")
            
            # Process the child's children nodes
            self._process_node_children(child_node, original_query, current_layer + 1)
            
            # Add to parent node
            node["child_nodes"].append(child_node)

    def _process_depth_node(self, node: Dict[str, Any], original_query: str, current_layer: int):
        """
        Process depth analysis node.
        
        :param node: Depth node to process
        :param original_query: Original user query
        :param current_layer: Current depth layer
        """
        # Check if we can add a new node
        if not self.resource_manager.can_add_node(current_layer + 1):
            self.logger.debug(f"[LIMIT] Reached node limit ({self.resource_manager.current_nodes}/{self.resource_manager.max_nodes}), stopping generation")
            return
            
        follow_up = self.depth_engine.process(
            content=node.get('node_summary', ''),
            original_query=original_query
        )
        
        if follow_up and isinstance(follow_up, dict) and 'question' in follow_up:
            follow_up_query = follow_up.get('question', '')
            self.logger.info(f"Generated follow-up question: {follow_up_query}")
            
            child_node_id = f"{node['node_id']}_depth_1"
            
            # Generate child node
            child_node = {
                "node_id": child_node_id,
                "type": "BREADTH",  # Child nodes of depth nodes default to breadth nodes
                "layer": current_layer + 1,
                "query": follow_up_query,
                "parent_id": node['node_id'],
                "child_nodes": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # 1. Task Decomposition
            tasks = self.task_prompter.process(follow_up_query)
            
            # 2. Generate node summary
            node_data = self.node_generator.generate_node({
                'query': follow_up_query,
                'node_id': child_node_id,
                'layer': current_layer + 1,
                'tasks': tasks,
                'context': {},
                'type': "BREADTH"
            })
            
            # 3. Validate node if validation is enabled
            if self.enable_validation:
                validated_data = self._validate_node(node_data)
                if not validated_data:
                    self.logger.warning(f"[VALIDATE] Skipping invalid node: {child_node_id}")
                    return
                node_data = validated_data
            
            child_node["node_summary"] = node_data.get('node_summary', '')
            
            # 4. Get engine decision
            decision = self.engine_controller.process(
                content=node_data.get('node_summary', ''),
                original_query=original_query,
                further_query=follow_up_query,
                current_layer=current_layer + 1
            )
            
            # Update node type and decision information
            child_node["type"] = decision.get("decision", "BREADTH")
            child_node["engine_decision"] = {
                "type": decision.get("decision", "BREADTH"),
                "focus": decision.get("analysis_focus"),
                "questions": decision.get("questions", [])
            }
            
            # Increment node count
            self.resource_manager.increment_nodes()
            self.logger.debug(f"[NODES] Node created: {child_node_id}. Node count: {self.resource_manager.current_nodes}/{self.resource_manager.max_nodes}")
            
            # Process the child's children nodes
            self._process_node_children(child_node, original_query, current_layer + 1)
            
            # Add to parent node
            node["child_nodes"].append(child_node)

    def _add_to_visualization(self, node: Dict[str, Any]) -> None:
        """
        Add node to visualization data.
        
        :param node: Node data dictionary
        """
        try:
            if not node:
                return
                
            # Create a copy of the node to avoid modifying the original
            visualization_node = {
                "node_id": node.get("node_id", ""),
                "type": node.get("type", ""),
                "layer": node.get("layer", 0),
                "query": node.get("query", ""),
                "node_summary": node.get("node_summary", ""),
                "engine_decision": node.get("engine_decision", {})
            }
            
            # Special handling for original query if this is a root node
            if node.get("type") == "ROOT":
                visualization_node["original_query"] = node.get("original_query", "")
            
            # Check if the node already exists
            existing_nodes = [n for n in self.visualization_data["nodes"] 
                             if n.get("node_id") == visualization_node["node_id"]]
            
            if existing_nodes:
                # Update existing node
                index = self.visualization_data["nodes"].index(existing_nodes[0])
                self.visualization_data["nodes"][index] = visualization_node
                self.logger.debug(f"Updated existing node {visualization_node['node_id']}")
            else:
                # Add new node
                self.visualization_data["nodes"].append(visualization_node)
                self.logger.debug(f"Added new node {visualization_node['node_id']}")

            # Add parent edge
            if "parent_id" in node:
                edge = {
                    "source": node["parent_id"],
                    "target": node["node_id"],
                    "type": node.get("type", "unknown")
                }
                
                if edge not in self.visualization_data["edges"]:
                    self.visualization_data["edges"].append(edge)
                    self.logger.debug(f"Added parent edge: {edge}")

            # Recursively process child nodes
            for child in node.get("child_nodes", []):
                self._add_to_visualization(child)

        except Exception as e:
            self.logger.error(f"[VISUALIZATION ERROR] Failed to update visualization: {str(e)}", exc_info=True)

    def _reset_visualization(self) -> Dict[str, List]:
        """
        Reset visualization data structure.
        
        :return: Initialized visualization data dictionary
        """
        self.visualization_data = {
            "nodes": [],
            "edges": []
        }
        return self.visualization_data

    def get_visualization_data(self) -> Dict[str, List]:
        """
        Get current visualization data.
        
        :return: Visualization data dictionary
        """
        return self.visualization_data

    def get_node_summaries(self, analysis_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get node summaries for a specific analysis.
        
        :param analysis_id: Analysis identifier
        :return: Dictionary containing summaries and statistics
        """
        return self.summary_manager.get_summaries(analysis_id)
    
    def get_analysis_status(self) -> Dict[str, Any]:
        """
        Get status of current analysis process.
        
        :return: Dictionary containing analysis status
        """
        return {
            "current_nodes": self.resource_manager.current_nodes,
            "max_nodes": self.resource_manager.max_nodes,
            "max_layer": self.resource_manager.max_layer,
            "visualization_nodes": len(self.visualization_data["nodes"]),
            "visualization_edges": len(self.visualization_data["edges"]),
            "timestamp": datetime.now().isoformat()
        }

    def _get_max_depth(self, node: Dict[str, Any]) -> int:
        """Get the maximum depth of the analysis tree."""
        if not node.get("child_nodes"):
            return node.get("layer", 1)
        return max(self._get_max_depth(child) for child in node.get("child_nodes", []))


