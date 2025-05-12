import json
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Dict, Any, List
from utils.logger import setup_logger


class MermaidGenerator:
    """Generates Mermaid diagram representations of the dual-engine analysis process."""

    def __init__(self, output_dir: str = "output"):
        """
        Initialize the MermaidGenerator.
        
        :param output_dir: Directory to save generated diagrams
        """
        self.logger = setup_logger("MermaidGenerator")
        self.logger.debug("[INIT] Initializing MermaidGenerator...")
        
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # Define node styles based on node types
        self.node_styles = {
            'BREADTH': 'fill:#e6f7ff,stroke:#0066cc',
            'DEPTH': 'fill:#f0f7ff,stroke:#003366',
            'COMPLETE': 'fill:#f6ffed,stroke:#52c41a',
            'ROOT': 'fill:#e1f5fe,stroke:#000',
            'ERROR': 'fill:#ffebee,stroke:red'
        }

        self.logger.debug(f"[INIT] MermaidGenerator initialized with output_dir={output_dir}")

    def _sanitize_content(self, content: Any) -> str:
        """
        Sanitize content for Mermaid diagram.
        
        :param content: Content to sanitize (can be string, dict, or other types)
        :return: Sanitized string
        """
        try:
            if not content:
                return ""
                
            # Convert content to string if it's not already
            if isinstance(content, dict):
                # If it's a dictionary, try to get a meaningful string representation
                if 'name' in content:
                    content = str(content['name'])
                elif 'query' in content:
                    content = str(content['query'])
                else:
                    content = str(content)
            else:
                content = str(content)
                
            # First pass: Remove markdown formatting
            content = (content
                .replace('**', '')
                .replace('*', '')
                .replace('###', '')
                .replace('####', '')
                .replace('#', ''))

            # Second pass: Handle Mermaid special characters
            content = (content
                .replace('{{', '')
                .replace('}}', '')
                .replace('(', '')
                .replace(')', '')
                .replace('[', '')
                .replace(']', '')
                .replace('{', '')
                .replace('}', '')
                .replace(':', ': ')  # Add space after colons
                .replace('\n', '<br>')
                .replace('"', "'")
                .replace('&', 'and'))

            # Remove extra whitespace
            content = ' '.join(content.split())

            # Remove URLs
            content = re.sub(r'http[s]?://\S+', '', content)

            return content.strip()

        except Exception as e:
            self.logger.error(f"[SANITIZE ERROR] Failed to sanitize content: {str(e)}", exc_info=True)
            return "Error sanitizing content"

    def _generate_flowchart(self, data: Dict[str, Any]) -> str:
        """
        Generate Mermaid flowchart code.
        
        :param data: Visualization data containing nodes and edges
        :return: Mermaid flowchart code as string
        """
        try:
            lines = ["flowchart TB"]
            style_lines = []
            subgraph_lines = []
            decision_lines = []
            extra_nodes = []  # Store extra nodes (like original query nodes)
            extra_edges = []  # Store extra connections

            # Track layers for subgraphs
            layer_nodes = {}

            # First pass: Organize nodes by layer
            for node in data.get('nodes', []):
                layer = node.get('layer', 0)
                if layer not in layer_nodes:
                    layer_nodes[layer] = []
                layer_nodes[layer].append(node)

            # Add nodes layer by layer
            for layer, nodes in sorted(layer_nodes.items()):
                subgraph_id = f"Layer_{layer}"
                subgraph_lines.append(f"    subgraph {subgraph_id}[Layer {layer}]")
                
                # Add original query node in the first layer
                if layer == 1:
                    # Find root node
                    for node in nodes:
                        node_id = node.get('node_id', '')
                        if not node_id:
                            continue

                        # Handle root node, find original query
                        if node.get('type') == 'ROOT':
                            # Check various possible locations for original query
                            original_query = ""
                            
                            # Directly check node's original_query property
                            if 'original_query' in node:
                                original_query = node.get('original_query', '')
                            # Check optimized_query_data dictionary
                            elif isinstance(node.get('optimized_query_data'), dict):
                                original_query = node.get('optimized_query_data', {}).get('original_query', '')
                            
                            if original_query:
                                # Create original query node ID
                                original_query_id = f"{node_id}_original"
                                
                                # Get optimized query
                                optimized_query = node.get('query', '') or node.get('optimized_query', '')
                                if not optimized_query and isinstance(node.get('optimized_query_data'), dict):
                                    optimized_query = node.get('optimized_query_data', {}).get('optimized_query', '')
                                
                                # Add original query node
                                original_content = f"User Query: '{self._sanitize_content(original_query)}'"
                                extra_nodes.append(f"        {original_query_id}[\"{original_content}\"]")
                                
                                # Add arrow from original query to optimized query
                                extra_edges.append(f"    {original_query_id} -->|OPTIMIZE| {node_id}")
                                
                                # Set original query node style
                                style_lines.append(f"style {original_query_id} fill:#fff0f6,stroke:#eb2f96")
                                
                                # Modify root node content to show only optimized query
                                if optimized_query:
                                    node['node_content'] = f"Optimized Query: '{self._sanitize_content(optimized_query)}'"
                
                # Process each node
                for node in nodes:
                    node_id = node.get('node_id', '')
                    if not node_id:
                        continue

                    # Get node content
                    if 'node_content' in node:
                        node_content = node['node_content']
                    else:
                        query = node.get('query', '')
                        node_summary = node.get('node_summary', '')
                        if query:
                            node_content = self._sanitize_content(query)
                        elif node_summary:
                            node_content = self._sanitize_content(node_summary)
                        else:
                            node_content = node_id.split('_')[-1]
                    
                    if not node_content:
                        node_content = "..."

                    node_type = node.get('type', 'UNKNOWN')

                    # Select node shape based on type
                    if node_type == 'BREADTH':
                        node_def = f"        {node_id}[{node_content}]"
                    elif node_type == 'DEPTH':
                        node_def = f"        {node_id}({node_content})"
                    elif node_type == 'COMPLETE':
                        node_def = f"        {node_id}{{{node_content}}}"
                    else:
                        node_def = f"        {node_id}[{node_content}]"

                    subgraph_lines.append(node_def)

                    # Add style based on node type
                    node_style = self.node_styles.get(node_type, "fill:white,stroke:#000")
                    style_lines.append(f"style {node_id} {node_style}")
                
                # Add extra nodes in the first layer (original query)
                if layer == 1:
                    subgraph_lines.extend(extra_nodes)
                
                subgraph_lines.append("    end")

            # Add edges
            edge_lines = []
            
            # Add arrow from original query to optimized query
            edge_lines.extend(extra_edges)
            
            # Add other edges
            for edge in data.get('edges', []):
                source = edge.get('source', '')
                target = edge.get('target', '')
                
                if not source or not target:
                    continue
                    
                if edge.get('type') in ['BREADTH', 'DEPTH']:
                    edge_lines.append(f"    {source} -->|{edge.get('type')}| {target}")
                else:
                    edge_lines.append(f"    {source} --> {target}")

            # Combine all sections
            return "\n".join(
                lines + 
                [""] +  # Empty line for readability
                subgraph_lines +
                [""] +  # Empty line for readability
                edge_lines +
                [""] +  # Empty line for readability
                decision_lines +
                [""] +  # Empty line for readability
                style_lines
            )

        except Exception as e:
            self.logger.error(f"[FLOWCHART ERROR] Failed to generate flowchart: {str(e)}", exc_info=True)
            return "flowchart TB\n    error[\"Error generating flowchart\"]"

    def generate(self, visualization_data: Dict[str, Any], analysis_id: str) -> Dict[str, Any]:
        """
        Generate Mermaid diagram and save to files.
        
        :param visualization_data: Dictionary containing nodes and edges
        :param analysis_id: Unique identifier for the analysis
        :return: Dictionary with file paths and metadata
        """
        try:
            self.logger.debug(f"[GENERATE] Generating Mermaid diagram for analysis {analysis_id}...")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Generate file paths in the output directory
            mermaid_file = os.path.join(self.output_dir, f"{analysis_id}.mmd")
            metadata_file = os.path.join(self.output_dir, f"{analysis_id}_metadata.json")

            mermaid_code = self._generate_flowchart(visualization_data)
            
            # Prepare metadata
            metadata = {
                'analysis_id': analysis_id,
                'timestamp': timestamp,
                'total_nodes': len(visualization_data.get('nodes', [])),
                'total_edges': len(visualization_data.get('edges', [])),
                'node_types': self._count_node_types(visualization_data.get('nodes', [])),
                'max_depth': self._calculate_max_depth(visualization_data.get('nodes', [])),
                'mermaid_file': mermaid_file
            }

            # Write files
            with open(mermaid_file, 'w', encoding='utf-8') as f:
                f.write(mermaid_code)

            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"[GENERATE] Mermaid diagram saved to {mermaid_file}")
            
            return {
                'mermaid_file': mermaid_file,
                'metadata_file': metadata_file,
                'metadata': metadata,
                'mermaid_code': mermaid_code
            }

        except Exception as e:
            self.logger.error(f"[GENERATE ERROR] Failed to generate files: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def open_diagram(self, mermaid_file: str) -> bool:
        """
        Open the generated Mermaid diagram with the default application.
        
        :param mermaid_file: Path to the Mermaid file
        :return: True if successful, False otherwise
        """
        try:
            if not os.path.exists(mermaid_file):
                self.logger.error(f"[OPEN ERROR] Mermaid file does not exist: {mermaid_file}")
                return False
                
            self.logger.debug(f"[OPEN] Opening Mermaid diagram: {mermaid_file}")
            
            # Read the Mermaid file content
            with open(mermaid_file, 'r', encoding='utf-8') as f:
                mermaid_code = f.read()
            
            # Create an HTML file with Mermaid renderer
            html_file = mermaid_file.replace('.mmd', '.html')
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DEoT Analysis Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .mermaid {{
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-top: 20px;
            overflow-x: auto;
        }}
        h1 {{
            color: #333;
        }}
        .info {{
            margin-bottom: 20px;
            color: #666;
        }}
    </style>
</head>
<body>
    <h1>DEoT Analysis Visualization</h1>
    <div class="info">
        <p>File: {os.path.basename(mermaid_file)}</p>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="mermaid">
{mermaid_code}
    </div>
</body>
</html>
            """
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            self.logger.debug(f"[OPEN] Created HTML file: {html_file}")
            
            # Open the HTML file with default browser
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['open', html_file])
            elif sys.platform == 'win32':  # Windows
                os.startfile(html_file)
            else:  # Linux
                subprocess.run(['xdg-open', html_file])
                
            print(f"Visualization opened in browser: {html_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"[OPEN ERROR] Failed to open diagram: {str(e)}", exc_info=True)
            print(f"Error opening diagram: {str(e)}")
            print(f"You can manually open the file: {mermaid_file}")
            return False

    def _count_node_types(self, nodes: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Count occurrences of each node type.
        
        :param nodes: List of node dictionaries
        :return: Dictionary with counts of each node type
        """
        type_counts = {}
        for node in nodes:
            node_type = node.get('type', 'UNKNOWN')
            type_counts[node_type] = type_counts.get(node_type, 0) + 1
        return type_counts

    def _calculate_max_depth(self, nodes: List[Dict[str, Any]]) -> int:
        """
        Calculate maximum depth/layer of the flowchart.
        
        :param nodes: List of node dictionaries
        :return: Maximum layer value
        """
        return max((node.get('layer', 0) for node in nodes), default=0)

    def convert_executor_data(self, executor_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert executor result to a format suitable for visualization.
        This method can be used when the executor output needs transformation.
        
        :param executor_result: The result dictionary from Executor.process_query()
        :return: Dictionary with nodes and edges ready for visualization
        """
        try:
            # In our current implementation, executor already outputs
            # properly formatted visualization_data
            visualization_data = executor_result.get('visualization_data', {})
            if not visualization_data or not isinstance(visualization_data, dict):
                self.logger.warning("[CONVERT] Empty or invalid visualization data in executor result")
                return {'nodes': [], 'edges': []}
                
            return visualization_data
            
        except Exception as e:
            self.logger.error(f"[CONVERT ERROR] Failed to convert executor data: {str(e)}", exc_info=True)
            return {'nodes': [], 'edges': []}

    def _generate_node_id(self, node_data: Dict[str, Any]) -> str:
        """
        Generate a unique ID from node data.
        
        :param node_data: Node data dictionary
        :return: Generated node ID
        """
        # First use the node's own ID if available
        if node_id := node_data.get('node_id'):
            return node_id
        
        # If no ready-made ID, generate based on analysis ID and node type
        analysis_id = node_data.get('analysis_id', '')
        parent_id = node_data.get('parent_id', '')
        node_type = node_data.get('type', '').lower()
        node_index = node_data.get('index', '1')  # Default to 1 to avoid empty index
        
        if parent_id:
            # Generate ID for child nodes
            return f"{parent_id}_{node_type}_{node_index}"
        else:
            # Root node
            return f"{analysis_id}_root"

    def _generate_edge_label(self, source_id: str, target_id: str) -> str:
        """
        Extract operation type from the target_id.
        
        :param source_id: Source node ID
        :param target_id: Target node ID
        :return: Edge label
        """
        if "_depth_" in target_id.lower():
            return "DEPTH"
        elif "_breadth_" in target_id.lower():
            return "BREADTH"
        else:
            # Default label or from data
            return ""


