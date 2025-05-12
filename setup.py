from setuptools import setup, find_packages

setup(
    name="deot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "openai>=1.0.0",
        "python-dotenv>=0.19.0",
        "requests>=2.26.0",
        "mermaid-cli>=0.1.0",
        "argparse>=1.4.0",
    ],
    entry_points={
        'console_scripts': [
            'deot=deot.cli:main',
        ],
    },
    author="NeuroWatt",
    author_email="your.email@example.com",
    description="Dual Engines of Thought - A framework for complex analytical thinking",
    long_description=open("README.md", encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/NeuroWatt-pte-ltd/DEoT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.9",
    keywords="ai, analysis, thinking, framework, llm",
    project_urls={
        "Bug Reports": "https://github.com/NeuroWatt-pte-ltd/DEoT/issues",
        "Source": "https://github.com/NeuroWatt-pte-ltd/DEoT",
    },
) 