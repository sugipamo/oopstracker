# OOPStracker

**AI Agent Code Loop Detection and Prevention Library**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-76%25-green.svg)](https://pytest.org/)

OOPStracker is a lightweight Python library designed to detect and prevent code duplication in AI agent-generated code, helping to avoid infinite loops and redundant code generation.

## Features

- 🔍 **High-Performance Similarity Detection**: SimHash + BK-tree for O(log n) search performance
- ⚡ **FastAPI Server**: RESTful API with <1 second response time for 10,000+ records
- 💾 **SQLite Storage**: Lightweight database with SimHash indexing
- 🔄 **Duplicate Prevention**: Detect and prevent redundant code generation
- 🛠️ **CLI Interface**: Command-line tools for file scanning and management
- 🎯 **Evocraft Integration**: Specialized support for Evocraft AI workflows
- 📈 **Generation Statistics**: Track and analyze code generation patterns
- 🚀 **Scalable Architecture**: Designed for 10,000+ code records with sub-second search

## Installation

```bash
# Install from source (PyPI package coming soon)
git clone https://github.com/evocoder/oopstracker.git
cd oopstracker
uv install
```

## Quick Start

### Basic Usage

```python
from oopstracker import SimHashSimilarityDetector, CodeRecord

# Initialize high-performance similarity detector
detector = SimHashSimilarityDetector(threshold=5)

# Add code records
code = '''
def hello():
    print("Hello, world!")
'''

record = CodeRecord(code_content=code, function_name="hello")
detector.add_record(record)

# Search for similar code
query_code = '''
def hello():
    # Added comment
    print("Hello, world!")
'''

result = detector.find_similar(query_code)
if result.is_duplicate:
    print("⚠️ Similar code detected!")
    for match in result.matched_records:
        print(f"   Similar to: {match.function_name} (score: {match.similarity_score:.3f})")
else:
    print("✅ No similar code found")
```

### CLI Usage

```bash
# Check a code snippet
uv run oopstracker check "def hello(): print('Hello')"

# Register a code snippet
uv run oopstracker register "def hello(): print('Hello')" --function-name hello

# Scan a Python file
uv run oopstracker scan my_file.py

# List all registered code
uv run oopstracker list

# Clear memory
uv run oopstracker clear
```

### FastAPI Server Usage

```bash
# Start the high-performance API server
uv run python -m oopstracker.api_server

# Or run with custom settings
uv run python -c "from oopstracker.api_server import run_server; run_server(host='0.0.0.0', port=8000)"
```

```python
# Use the API client
import asyncio
from oopstracker.examples.fastapi_client_example import OOPSTrackerClient

async def example():
    async with OOPSTrackerClient() as client:
        # Insert code
        result = await client.insert_code(
            "def hello(): print('Hello')",
            function_name="hello"
        )
        print(f"Inserted: {result['id']}")
        
        # Search for similar code
        search_result = await client.search_similar("def hello(): print('Hi')")
        print(f"Found {len(search_result['results'])} similar results")
        print(f"Search time: {search_result['search_time_ms']:.2f} ms")

asyncio.run(example())
```

### Evocraft Integration

```python
from oopstracker.examples.evocraft_integration import EvocraftCodeGuard

# Initialize guard for Evocraft workflows
guard = EvocraftCodeGuard(db_path="evocraft_memory.db")

# Check before generation
prompt = "Create a function to calculate fibonacci numbers"
context = {"language": "python", "style": "recursive"}

if guard.check_before_generation(prompt, context):
    generated_code = '''
    def fibonacci(n):
        if n <= 1:
            return n
        return fibonacci(n-1) + fibonacci(n-2)
    '''
    guard.register_generation(prompt, generated_code, context)

# Get generation statistics
stats = guard.get_generation_stats()
print(f"Total generations: {stats['total_generations']}")
```

## Architecture

### Core Components

- **CodeMemory**: Main interface for code registration and duplicate detection
- **CodeNormalizer**: AST-based code normalization and cleaning
- **CodeSimilarityDetector**: Similarity analysis using various algorithms
- **DatabaseManager**: SQLite operations and schema management

### Data Models

- **CodeRecord**: Represents stored code with metadata
- **SimilarityResult**: Results of duplicate detection analysis
- **DatabaseConfig**: Database configuration and settings

## Development

### Prerequisites

- Python 3.8.1+
- UV package manager

### Setup

```bash
git clone https://github.com/evocoder/oopstracker.git
cd oopstracker
uv install --dev
```

### Running Tests

```bash
uv run pytest tests/ -v --cov=src/oopstracker
```

### Code Quality

```bash
# Format code
uv run black src/ tests/

# Sort imports
uv run isort src/ tests/

# Type checking
uv run mypy src/

# Linting
uv run flake8 src/ tests/
```

## Use Cases

### AI Agent Development
- Prevent infinite loops in code generation
- Detect redundant function implementations
- Track generation patterns for optimization

### Code Review
- Identify duplicate code in pull requests
- Maintain code quality standards
- Enforce DRY principles

### Educational Tools
- Teach code similarity concepts
- Demonstrate refactoring opportunities
- Analyze coding patterns

## Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed development plans:

- **v0.1.0**: Core functionality with SHA-256 similarity detection ✅
- **v0.2.0**: Enhanced Evocraft integration with context-aware detection
- **v0.3.0**: Advanced similarity algorithms (SimHash, AST structure comparison)
- **v0.4.0**: Framework-agnostic generalization and plugin architecture
- **v1.0.0**: Production-ready release with enterprise features

## Contributing

We welcome contributions! Please see our [contributing guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/evocoder/oopstracker/issues)
- **Discussions**: [GitHub Discussions](https://github.com/evocoder/oopstracker/discussions)
- **Documentation**: [ReadTheDocs](https://oopstracker.readthedocs.io/)

## Acknowledgments

- Created for the Evocraft AI development ecosystem
- Inspired by the need for intelligent code generation loop prevention
- Built with modern Python development practices using UV and pytest

---

*OOPStracker: Preventing AI agents from going in circles, one duplicate at a time.*
