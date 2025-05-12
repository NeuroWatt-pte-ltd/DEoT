# DEoT: Dual Engines of Thought

A novel framework for complex analytical thinking using dual engines: breadth engine and depth engine analysis.

## Overview

DEoT (Dual Engines of Thought) is a framework for complex analytical thinking that combines two complementary "engines" of analysis:

1. **Breadth Engine**: Identifies multiple perspectives and dimensions of an issue
2. **Depth Engine**: Deepens the analysis by focusing on specific aspects and generating follow-up questions

The framework dynamically switches between these engines based on the content being analyzed, allowing for comprehensive exploration of complex topics.

## Features

- **Dual-engine thinking**: Combines breadth and depth analysis
- **Dynamic engine selection**: Automatically selects the appropriate engine for each analysis stage
- **Visualization**: Generates Mermaid diagrams to show the thought process
- **Command-line interface**: Easy to use through a simple CLI
- **Modular design**: Extensible components for custom implementations

## Installation

### Requirements

- Python 3.9+
- OpenAI API key 
- Perplexity API key

### Installation Methods

#### Method 1: Direct Installation
```bash
# Clone the repository
git clone https://github.com/NeuroWatt-pte-ltd/DEoT.git
cd DEoT

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

#### Method 2: Install as a Package
```bash
# Clone the repository
git clone https://github.com/NeuroWatt-pte-ltd/DEoT.git
cd DEoT

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install the package
pip install -e .  # Development mode
# or
pip install .     # Regular installation
```

### Configuration

1. Copy the example environment file:
```bash
cp .env_example .env
```

2. Edit `.env` and add your API keys:
```env
OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
```

## Usage

### Using as a Package (deot command)

```bash
# Run an analysis
deot analyze "What is the impact of quantum computing on cryptography?"

# List previous analyses
deot list

# View a specific analysis result
deot view analysis_20230615_123456

# Open the visualization diagram
deot open analysis_20230615_123456
```

### Using Directly (python main.py)

```bash
# Run an analysis
python main.py analyze "What is the impact of quantum computing on cryptography?"

# List previous analyses
python main.py list

# View a specific analysis result
python main.py view analysis_20230615_123456

# Open the visualization diagram
python main.py open analysis_20230615_123456
```

## Examples

### Basic Analysis

```bash
python main.py analyze "What are the potential impacts of AI regulation on innovation?"
```

### In-depth Analysis

```bash
python main.py analyze "What are the geopolitical implications of rare earth mineral shortages?" --max-layer 4 --max-nodes 25 --temperature 0.3 --model gpt-4o
```

## Framework Architecture

DEoT consists of several key components:

1. **Engine Controller**: Determines which engine to use at each step
2. **Breadth Engine**: Identifies multiple aspects of an issue
3. **Depth Engine**: Deepens analysis on specific aspects
4. **Executor**: Coordinates the analysis process
5. **Visualizer**: Generates diagrams of the thought process

## Visualization

DEoT generates Mermaid diagrams to visualize the thinking process. These diagrams show:

- The original and optimized query
- Different layers of analysis
- Connections between ideas
- Engine decisions at each step


## License

This project is licensed under the [Apache License 2.0](./LICENSE).



