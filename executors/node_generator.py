from typing import Dict, Any, List 
from datetime import datetime
from utils import setup_logger
from prompters import TaskPrompter
from executors import SummaryManager
from agents import (
    EventExtractorAgent,
    HistoryAnalyzerAgent,
    InfoSearchAgent,
    NewsSearchAgent,
    ReasoningAgent
)

class NodeGenerator:
    """
    NodeGenerator handls the generation and processing of analysis nodes.
    It coordinates task decomposition, execution, and results intergration.
    """

    # Define agent mapping 
    AGENT_MAPPING = {
        'event_extractor': (EventExtractorAgent, lambda agent, input_data: agent.process(input_data)),
        'history_analyzer': (HistoryAnalyzerAgent, lambda agent, input_data: agent.process(input_data)),
        'info_search': (InfoSearchAgent, lambda agent, input_data: agent.process(input_data)),
        'news_search': (NewsSearchAgent, lambda agent, input_data: agent.process(*NodeGenerator._parse_news_input(input_data))),
        'reasoning': (ReasoningAgent, lambda agent, input_data: agent.process(input_data))
    }

    def __init__(self):
        """Initialize NodeGenerator with required components."""
        
        self.logger = setup_logger("NodeGenerator")
        self.task_prompter = TaskPrompter()
        self.summary_manager = SummaryManager()

        self.logger.debug("[INIT] NodeGeneratory initialized successfully.")
    
    def generate_node(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a node from input data.

        :param input_data: Dictionary containing query and context information
        :return: Dictionary containing node generation results
        """

        try:
            # Extract key parameters
            query = input_data.get('query', '')
            node_id = input_data.get('node_id', f"node_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            layer = input_data.get('layer', 1)
            context = input_data.get('context', {})
            node_type = input_data.get('type', 'BREADTH')  # Default to BREADTH if not specified

            self.logger.debug(f"Generating node {node_id} at layer {layer}")

            # Step 1: Task Decomposition 
            tasks = self._decompose_tasks(query)

            # Step 2: Task execution
            execution_results = self._execute_tasks(tasks, query)

            # Step 3: Generate Summary
            summary = self._generate_summary(execution_results, query)
            self.logger.debug(f"Generated summary for node {node_id}")

            # Prepare response
            node_data = {
                'node_id': node_id,
                'layer': layer,
                'query': query,
                'tasks': tasks,
                'detailed_results': execution_results,
                'node_summary': summary,
                'timestamp': datetime.now().isoformat(),
                'context': context,
                'type': node_type
            }

            return node_data 
        
        except Exception as e:
            self.logger.error(f"[GENERATE ERROR] Failed to generate node {node_id}: {str(e)}", exc_info=True)
            return {
                'node_id': node_id,
                'error': str(e),
                'status': 'failed',
                'timestamp': datetime.now().isoformat()
            }
        
    def _decompose_tasks(self, query: str) -> List[Dict[str, Any]]:
        """
        Decompose query into tasks.

        :param query: User query to decompose
        :return: List of tasks
        """

        try:
            return self.task_prompter.process(query)
        except Exception as e:
            self.logger.error(f"Task decomposition failed: {str(e)}", exc_info=True)
            raise 

    def _execute_tasks(self, tasks: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Execute tasks using appropriate agents.

        :param tasks: List of tasks to execute
        :param query: Original query
        :return: List of task execution results
        """

        results = []

        for task in tasks:
            try:
                # Handle both string and dictionary tasks
                if isinstance(task, str):
                    task_id = f"task_{len(results) + 1}"
                    agent_name = "info_search"  # Default to info_search for string tasks
                    task_input = task
                else:
                    task_id = task.get('id', f"task_{len(results) + 1}")
                    agent_name = task.get('name', '').lower()
                    task_input = task.get('input', '')

                self.logger.debug(f"Executing task {task_id} with agent {agent_name}")

                # Execute task using mapping 
                result = self._execute_single_task(agent_name, task_input)

                # Format result
                formatted_result = {
                    'task_id': task_id, 
                    'agent': agent_name,
                    'input': task_input, 
                    'result': result,
                    'status': 'success',
                    'timestamp': datetime.now().isoformat()
                }

                results.append(formatted_result)
                self.logger.debug(f"Task {task_id} executed successfully")
            
            except Exception as e:
                task_id = f"task_{len(results) + 1}" if isinstance(task, str) else task.get('id', 'unknown')
                agent_name = "info_search" if isinstance(task, str) else task.get('name', '')
                task_input = task if isinstance(task, str) else task.get('input', '')
                
                self.logger.error(f"[EXECUTE ERROR] Task {task_id} execution failed: {str(e)}", exc_info=True)
                results.append({
                    'task_id': task_id,
                    'agent': agent_name,
                    'input': task_input,
                    'result': f"Error: {str(e)}",
                    'status': 'failed',
                    'timestamp': datetime.now().isoformat()
                })
        
        return results

    def _execute_single_task(self, agent_name: str, task_input: str) -> Any:
        """Execute a single task with the appropriate agent."""

        if agent_name not in self.AGENT_MAPPING:
            self.logger.warning(f"Unknown agent type: {agent_name}")
            return f"Error: Unknown agent type '{agent_name}'"
        
        AgentClass, process_func = self.AGENT_MAPPING[agent_name]
        agent = AgentClass()
        return process_func(agent, task_input)
    

    @staticmethod
    def _parse_news_input(task_input: str) -> tuple:
        """Parse input for news search agent."""
        if ',' in task_input:
            query_part, count_part = task_input.split(',', 1)
            try:
                count = int(count_part.strip())
            except ValueError:
                count = 3
            search_query = query_part.strip()
        else:
            search_query = task_input
            count = 3
        return search_query, count
    
    def _generate_summary(self, execution_results: List[Dict[str, Any]], original_query: str) -> str:
        """
        Generate a summary from execution results.

        :param execution_results: List of task execution results
        :param original_query: Original query
        :return: Summary text
        """

        try:
            # Count successfull and failed tasks
            successful = sum(1 for result in execution_results if result.get('status') == 'success')
            failed = len(execution_results) - successful

            # Extract key findings and evidence from all results
            all_findings = []
            evidence_points = []

            for result in execution_results:
                result_text = result.get('result', '')
                agent = result.get('agent', '')

                # Extract findings and evidence 
                findings = self._extract_key_points(result_text) 
                all_findings.extend(findings[:2]) # Take top 2 findings

                # Get a piece of evidence if available
                if findings and len(findings) > 0:
                    evidence = self._extract_evidence(result_text)
                    if evidence:
                        evidence_points.append(evidence)

            # Generate the comprehensive analysis
            comprehensive_analysis = self._generate_comprehensive_analysis(
                all_findings,
                evidence_points,
                original_query
            )

                        # Create summary format
            summary = f"""[NODE SUMMARY]
TASK EXECUTION OVERVIEW:
- Total Tasks: {len(execution_results)}
- Successful: {successful}
- Failed: {failed}

COMPREHENSIVE ANALYSIS:
{comprehensive_analysis}
[END NODE SUMMARY]"""
            
            return summary 
        
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {str(e)}", exc_info=True)
            return f"[NODE SUMMARY]\nError generating summary: {str(e)}\n[END NODE SUMMARY]"
    
    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from text."""
        
        sentences = text.split('.')
        return [s.strip() + '.' for s in sentences[:3] if s.strip()]
    
    def _extract_evidence(self, text: str) -> str:
        """Extract a piece of evidence from test."""

        sentences = text.split('.')
        if len(sentences) >= 3:
            return sentences[len(sentences)//2].strip() + '.'
        elif sentences:
            return sentences[0].strip() + '.'
        return ""
    
    def _generate_comprehensive_analysis(
            self,
            findings: List[str],
            evidence: List[str],
            query: str 
    ) -> str:
        """
        Generate a comprehensive analysis in paragraph form.

        :param findings: List of key findings
        :param evidence: List of evidence points
        :param query: Original query
        :return: Comprehensive analysis text
        """

        # Deduplicate findings and evidence
        unique_findings = list(set(findings))
        unique_evidence = list(set(evidence))

        # Create first paragraph with findings 
        if len(unique_findings) >= 3:
            first_para = ' '.join(unique_findings[:3])
        else:
            first_para = ' '.join(unique_findings) if unique_findings else f"Analysis of '{query}' yielded limited results."
        
        # Create second paragraph with evidence and implications
        if unique_evidence:
            second_para = ' '.join(unique_evidence[:2])
            second_para += f" These findings have significant implications for understanding {query}."
        else:
            second_para = f"Further investigation is needed to fully understand the implications of {query}."
        
        # Create final paragraph with conclusion
        final_para = f"In conclusion, the analysis of '{query}' reveals important patterns and connections that provide valuable insights into this topic."
        
        # Combine paragraphs
        return f"{first_para}\n\n{second_para}\n\n{final_para}"
    
    def store_node_summary(self, node_data: Dict[str, Any]) -> None:
        """
        Store the node summary in the SummaryManager.
        This method should be called after node validation passes.

        :param node_data: Complete node data dictionary
        """
        try:
            if not node_data or 'node_summary' not in node_data:
                self.logger.warning("Cannot store summary: Invalid node data")
                return

            # Get validation status from node_data if available
            validation_status = node_data.get('validation_status', 'VALID' if not node_data.get('validation_service') else 'UNKNOWN')

            self.summary_manager.add_node_summary(
                summary=node_data['node_summary'],
                node_id=node_data['node_id'],
                layer=node_data['layer'],
                node_type=node_data['type'],
                validation_status=validation_status
            )
            self.logger.debug(f"Stored summary for node {node_data['node_id']} with validation status: {validation_status}")

        except Exception as e:
            self.logger.error(f"Failed to store summary: {str(e)}", exc_info=True)
            
        


