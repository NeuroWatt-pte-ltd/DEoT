#!/usr/bin/env python3
"""
DEoT (Dual Engines of Thought) - A dual-engine thinking framework

Main entry point for the CLI application
"""
import argparse
import os
import json
import subprocess
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional

from analyzers.dual_engine_analyzer import DualEngineAnalyzer
from utils.logger import setup_logger

# Setup logging
logger = setup_logger("CLI")

def analyze_command(args):
    """Execute the analyze command"""
    logger.info(f"Starting analysis for query: {args.query}")
    
    try:
        # Initialize the analyzer
        analyzer = DualEngineAnalyzer(
            max_layer=args.max_layer,
            max_nodes=args.max_nodes,
            platform=args.platform,
            model_name=args.model,
            temperature=args.temperature,
            output_dir=args.output_dir,
            enable_validation=args.enable_validation
        )
        
        # Execute analysis
        result = analyzer.analyze(
            query=args.query,
            use_cache=False,  # Cache functionality has been removed
            generate_visualization=True
        )
        
        # Get analysis ID
        analysis_id = result.get("analysis_id", "unknown")
        output_dir = result.get("output_directory", "")
        
        # Output results
        print(f"\nAnalysis completed (ID: {analysis_id})")
        print(f"Results saved to: {output_dir}")
        print("\nAnalysis response:")
        print("-" * 80)
        print(result.get("response", "No response generated"))
        print("-" * 80)
        
        # Add validation status to output if validation is enabled
        if args.enable_validation:
            stats = result.get("stats", {})
            validation_passed = stats.get("validation_passed", 0)
            validation_failed = stats.get("validation_failed", 0)
            print("\nValidation Statistics:")
            print(f"Nodes passed validation: {validation_passed}")
            print(f"Nodes failed validation: {validation_failed}")
            print("-" * 80)
        
        # Visualization prompt
        if result.get("visualization", {}).get("mermaid_file"):
            mermaid_file = result["visualization"]["mermaid_file"]
            print(f"\nVisualization chart generated: {mermaid_file}")
            print(f"Use the following command to view the chart: deot open {analysis_id}")
        
        return 0
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
        return 1

def list_command(args):
    """List historical analyses"""
    try:
        # Initialize the analyzer
        analyzer = DualEngineAnalyzer(output_dir=args.output_dir)
        
        # Get analysis history
        history = analyzer.get_analysis_history(limit=args.limit)
        
        if not history:
            print("No analysis records found")
            return 0
            
        # Display history
        print(f"\nFound {len(history)} analysis records:")
        print("-" * 80)
        print(f"{'ID':<25} | {'Date':<20} | {'Query':<50}")
        print("-" * 80)
        
        for item in history:
            # Format timestamp
            timestamp = item.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(timestamp)
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                formatted_time = timestamp
                
            # Truncate query text
            query = item.get("query", "")
            if len(query) > 47:
                query = query[:47] + "..."
                
            # Output record
            print(f"{item.get('analysis_id', ''):<25} | {formatted_time:<20} | {query:<50}")
            
        print("-" * 80)
        print("Use 'deot view <analysis_id>' to view a specific analysis")
        print("Use 'deot open <analysis_id>' to open the chart")
        
        return 0
    except Exception as e:
        logger.error(f"Error listing history: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
        return 1

def view_command(args):
    """View a specific analysis"""
    try:
        # Initialize the analyzer
        analyzer = DualEngineAnalyzer(output_dir=args.output_dir)
        
        # Get analysis
        analysis = analyzer.get_analysis(args.analysis_id)
        
        if not analysis:
            print(f"Analysis ID not found: {args.analysis_id}")
            return 1
            
        # Output analysis details
        print(f"\nAnalysis details (ID: {args.analysis_id})")
        print("-" * 80)
        print(f"Query: {analysis.get('query', 'No query')}")
        print(f"Time: {analysis.get('timestamp', 'Unknown')}")
        print(f"Stats: Node count: {analysis.get('stats', {}).get('node_count', 0)}, "
              f"Max depth: {analysis.get('stats', {}).get('max_depth', 0)}")
        print("-" * 80)
        print("Analysis response:")
        print(analysis.get("response", "No response"))
        print("-" * 80)
        
        # Chart information
        if analysis.get("visualization", {}).get("mermaid_file"):
            mermaid_file = analysis["visualization"]["mermaid_file"]
            print(f"\nVisualization chart: {mermaid_file}")
            print(f"Use the following command to open the chart: deot open {args.analysis_id}")
            
        return 0
    except Exception as e:
        logger.error(f"Error viewing analysis: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
        return 1

def open_command(args):
    """Open analysis chart"""
    try:
        # Initialize the analyzer
        analyzer = DualEngineAnalyzer(output_dir=args.output_dir)
        
        # Get analysis
        analysis = analyzer.get_analysis(args.analysis_id)
        
        if not analysis:
            print(f"Analysis ID not found: {args.analysis_id}")
            return 1
            
        # Ensure chart exists
        if not analysis.get("visualization", {}).get("mermaid_file"):
            print(f"This analysis has no chart")
            return 1
            
        # Get chart file path
        mermaid_file = analysis["visualization"]["mermaid_file"]
        if not os.path.exists(mermaid_file):
            print(f"Chart file does not exist: {mermaid_file}")
            return 1
            
        # Use MermaidGenerator to open the chart
        from visualization.mermaid_generator import MermaidGenerator
        generator = MermaidGenerator(output_dir=args.output_dir)
        success = generator.open_diagram(mermaid_file)
        
        if not success:
            print(f"Could not open chart. You can manually open the file: {mermaid_file}")
            
        return 0
    except Exception as e:
        logger.error(f"Error opening chart: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
        return 1

def main():
    """Main function"""
    # Create main parser
    parser = argparse.ArgumentParser(
        description="DEoT (Dual Engines of Thought) - A dual-engine thinking framework",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Add global options
    parser.add_argument('--output-dir', default='output', help='Output directory')
    
    # Create subcommand parsers
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Get default values from environment variables
    default_max_layer = int(os.getenv("MAX_LAYER", "3"))
    default_max_nodes = int(os.getenv("MAX_NODES", "15"))
    default_platform = os.getenv("PLATFORM", "openai")
    default_model = os.getenv("MODEL_NAME", "gpt-4")
    default_temperature = float(os.getenv("TEMPERATURE", "0.3"))
    
    # analyze command
    parser_analyze = subparsers.add_parser('analyze', help='Analyze a query')
    parser_analyze.add_argument('query', help='Query to analyze')
    parser_analyze.add_argument('--max-layer', type=int, default=default_max_layer, 
                               help=f'Maximum analysis layers (default: {default_max_layer} from env)')
    parser_analyze.add_argument('--max-nodes', type=int, default=default_max_nodes,
                               help=f'Maximum nodes (default: {default_max_nodes} from env)')
    parser_analyze.add_argument('--platform', default=default_platform,
                               help=f'LLM platform (default: {default_platform} from env)')
    parser_analyze.add_argument('--model', default=default_model,
                               help=f'Model name (default: {default_model} from env)')
    parser_analyze.add_argument('--temperature', type=float, default=default_temperature,
                               help=f'Temperature setting (default: {default_temperature} from env)')
    parser_analyze.add_argument('--enable-validation', action='store_true', 
                               help='Enable validation mode')
    parser_analyze.set_defaults(func=analyze_command)
    
    # list command
    parser_list = subparsers.add_parser('list', help='List historical analyses')
    parser_list.add_argument('--limit', type=int, default=10, help='Maximum display count')
    parser_list.set_defaults(func=list_command)
    
    # view command
    parser_view = subparsers.add_parser('view', help='View a specific analysis')
    parser_view.add_argument('analysis_id', help='Analysis ID')
    parser_view.set_defaults(func=view_command)
    
    # open command
    parser_open = subparsers.add_parser('open', help='Open analysis chart')
    parser_open.add_argument('analysis_id', help='Analysis ID')
    parser_open.set_defaults(func=open_command)
    
    # Parse command line arguments
    args = parser.parse_args()
    
    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return 0
    
    # Execute corresponding command
    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())


