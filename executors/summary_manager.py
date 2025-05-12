from typing import Dict, Any, Optional 
from datetime import datetime 
from utils import setup_logger

class SummaryManager:
    """
    SummaryManager handles the storage and retrieval of analysis summaries.
    It maintains summaries across different analysis sessions.
    """

    _instance = None 
    _initialized = False 

    def __new__(cls):
        """Implement singleton pattern"""

        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance 
    
    def __init__(self):
        """Initialize the summary manager state"""

        # Skip initialization if already done 
        if self._initialized:
            return 
        
        self.logger = setup_logger("SummaryManager")
        self.logger.debug("Initializing SummaryManager...")
        self._summaries = {}
        self._current_analysis_id = None 

        # Mark initialization as complete 
        self._initialized = True 
        self.logger.debug("SummaryManager initialized successsfully")

    def start_new_analysis(self, analysis_id: str) -> None:
        """
        Start a news analysis session.

        :param analysis_id: Unique identifier for the analysis
        """

        self.logger.info(f"Starting new analysis with ID: {analysis_id}")
        self._current_analysis_id = analysis_id
        self._summaries[analysis_id] = {
            'node_summaries': [],
            'timestamp': datetime.now().isoformat(),
            'metadata': {},
            'stats': {
                'total_nodes': 0,
                'breadth_analyses': 0,
                'depth_analyses': 0,
                'max_depth': 0,
                'validation_failed': 0,
                'validation_passed': 0
            }
        }

    def _extract_summary_content(self, summary: str) -> str:
        """
        Extract summary content, removing markers.

        :param summary: Raw summary text
        :return: Cleaned summary content
        """

        if '[NODE SUMMARY]' in summary and '[END NODE SUMMARY]' in summary:
            start_idx = summary.find('[NODE SUMMARY]') + len('[NODE SUMMARY]')
            end_idx = summary.find('[END NODE SUMMARY]')
            return summary[start_idx:end_idx].strip()
        
        return summary.strip()
    
    def add_node_summary(
            self,
            summary: str, 
            node_id: str,
            layer: int,
            node_type: str = None,
            category: str = None,
            metadata: Dict[str, Any] = None,
            validation_status: str = None
    ) -> None:
        """
        Add a node summary, storing only the actual content.

        :param summary: Summary content to add
        :param node_id: Node identifier
        :param layer: Layer number of the node
        :param node_type: Type of node (BREADTH, DEPTH, etc)
        :param category: Category of the summary 
        :param metadata: Additional metadata for the summary
        :param validation_status: Status of node validation (VALID/INVALID)
        """

        if not self._current_analysis_id:
            self.logger.warning("[ADD] No current analysis ID set. Call start_new_analysis first.")
            return 
        
        analysis_data = self._summaries[self._current_analysis_id]
        clean_summary = self._extract_summary_content(summary)

        if clean_summary:
            summary_entry = {
                'content': clean_summary,
                'node_id': node_id,
                'layer': layer,
                'node_type': node_type,
                'category': category,
                'timestamp': datetime.now().isoformat(),
                'validation_status': validation_status
            }

            # Add metadata if provided
            if metadata:
                summary_entry['metadata'] = metadata

            analysis_data['node_summaries'].append(summary_entry)

            # Update statistics 
            analysis_data['stats']['total_nodes'] += 1
            analysis_data['stats']['max_depth'] = max(analysis_data['stats']['max_depth'], layer)

            if node_type == 'BREADTH':
                analysis_data['stats']['breadth_analyses'] += 1
            elif node_type == 'DEPTH':
                analysis_data['stats']['depth_analyses'] += 1

            # Update validation statistics
            if validation_status == 'VALID':
                analysis_data['stats']['validation_passed'] += 1
            elif validation_status == 'INVALID':
                analysis_data['stats']['validation_failed'] += 1

            self.logger.info(f"Added summary for node {node_id} at layer {layer} with validation status: {validation_status}")
        
        else:
            self.logger.warning(f"Empty summary for node {node_id}, not added")

    def get_summaries(self, analysis_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all summaries for the specific analysis.

        :param analysis_id: Optional analysis identifieer
        :return: Dictionary containing summaries and metadata 
        """

        aid = analysis_id or self._current_analysis_id

        if not aid:
            self.logger.warning("No analysis ID provided or set as current")
            return {'node_summaries': [], 'stats': {}}
        
        if aid not in self._summaries:
            self.logger.warning(f"Analysis ID {aid} not found")
            return {'node_summaries': [], 'stats': {}}
        
        # Sort summaries by layer first, then by timestamp
        summaries = self._summaries[aid]['node_summaries']
        sorted_summaries = sorted(
            summaries, 
            key=lambda x: (x.get('layer', 0), x.get('timestamp', ''))
        )

        return {
            'node_summaries': sorted_summaries,
            'timestamp': self._summaries[aid]['timestamp'],
            'metadata': self._summaries[aid]['metadata'],
            'stats': self._summaries[aid]['stats']
        }
    
    def get_formatted_summaries(self, analysis_id: Optional[str] = None) -> str:
        """
        Get formatted summary content for easier reading.

        :param analysis_id: Optional analysis identifier
        :return: Formatted summary string
        """
        summaries = self.get_summaries(analysis_id)
        formatted_summaries = []

        for summary in summaries['node_summaries']:
            node_id = summary.get('node_id', '?')
            layer = summary.get('layer', '?')
            node_type = summary.get('node_type', 'Unknown')
            category = summary.get('category', 'Unknown')
            validation_status = summary.get('validation_status', 'Unknown')
            content = summary.get('content', '').strip()

            if content:
                # Format each node summary with its metadata
                formatted_summary = (
                    f"=== Node {node_id} (Layer {layer}, Type: {node_type}, Category: {category}, Validation: {validation_status}) ===\n"
                    f"{content}\n"
                )
                formatted_summaries.append(formatted_summary)

        if not formatted_summaries:
            return '[No summaries available]'
            
        # Add statistics at the end
        stats = summaries['stats']
        stats_text = (
            f"\n=== Analysis Statistics ===\n"
            f"Total Nodes: {stats.get('total_nodes', 0)}\n"
            f"Maximum Depth: {stats.get('max_depth', 0)}\n"
            f"Breadth Analyses: {stats.get('breadth_analyses', 0)}\n"
            f"Depth Analyses: {stats.get('depth_analyses', 0)}\n"
            f"Validation Passed: {stats.get('validation_passed', 0)}\n"
            f"Validation Failed: {stats.get('validation_failed', 0)}\n"
        )
        
        return "\n".join(formatted_summaries) + stats_text
    
    def get_analysis_stats(self, analysis_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get analysis statistics.
        
        :param analysis_id: Optional analysis identifier
        :return: Dictionary with analysis statistics
        """
        aid = analysis_id or self._current_analysis_id
        
        if not aid or aid not in self._summaries:
            self.logger.warning(f"[STATS] Analysis ID {aid} not found")
            return {
                'total_nodes': 0,
                'max_depth': 0,
                'breadth_analyses': 0,
                'depth_analyses': 0
            }
            
        return self._summaries[aid]['stats']
    
    def clear_analysis(self, analysis_id: Optional[str] = None) -> None:
        """
        Clear summaries for the specified analysis.

        :param analysis_id: Optional analysis identifier to clear
        """
        aid = analysis_id or self._current_analysis_id
        if aid in self._summaries:
            self.logger.info(f"[CLEAR] Clearing analysis data for ID: {aid}")
            del self._summaries[aid]
        else:
            self.logger.warning(f"[CLEAR] Analysis ID {aid} not found, nothing to clear")
    
    def get_current_analysis_id(self) -> Optional[str]:
        """
        Get the current analysis ID.
        
        :return: Current analysis ID or None if not set
        """
        return self._current_analysis_id






