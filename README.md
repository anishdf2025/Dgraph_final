# Legal Judgment Database - RDF Generator

A best practices implementation for generating RDF files from Elasticsearch data containing legal judgments, citations, judges, advocates, outcomes, and case durations.

## 🏗️ Architecture

### Clean Code Structure
```
├── .env                      # Environment configuration
├── config.py                 # Configuration management
├── models.py                 # Data models and classes
├── utils.py                  # Utility functions
├── elasticsearch_handler.py  # Elasticsearch data operations
├── rdf_generator.py          # Main RDF generator
├── elasticsearch_upload.py   # Upload Excel to Elasticsearch
├── live_upload.py           # Upload RDF to Dgraph
└── rdf.schema               # Dgraph schema definition
```

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv pip install python-dotenv elasticsearch pandas openpyxl
```

### 2. Configuration
Edit `.env` file for your environment:
```env
ELASTICSEARCH_HOST=http://localhost:9200
ELASTICSEARCH_INDEX=graphdb
RDF_OUTPUT_FILE=judgments.rdf
```

### 3. Generate RDF from Elasticsearch
```bash
python3 rdf_generator.py
```

### 4. Upload to Dgraph
```bash
python3 live_upload.py
```

## 📊 Data Flow

```
Excel → Elasticsearch → RDF Generator → Dgraph
  ↓           ↓              ↓           ↓
 .xlsx    graphdb index   judgments.rdf  Graph DB
```

## 🔧 Components

### Configuration Management (`config.py`)
- Environment variable handling with `.env` support
- Centralized configuration validation
- Type-safe configuration access

### Data Models (`models.py`)
- `JudgmentData`: Judgment information structure
- `ProcessingStats`: Processing statistics tracking
- `ElasticsearchDocument`: Clean document structure
- `NodeMapping`: Node relationship mappings

### Elasticsearch Handler (`elasticsearch_handler.py`)
- Connection management and validation
- Document loading and processing
- List field parsing optimization
- Error handling and logging

### Utilities (`utils.py`)
- Logging configuration
- String sanitization
- List data parsing (citations, judges, advocates)
- RDF triple formatting
- Node ID generation

### RDF Generator (`rdf_generator.py`)
- Clean separation of concerns
- Two-pass processing (data collection → relationship creation)
- Optimized node creation and mapping
- Comprehensive statistics tracking

## 🎯 Features

### Best Practices Implementation
- ✅ Environment-based configuration
- ✅ Separation of concerns
- ✅ Type hints and documentation
- ✅ Error handling and logging
- ✅ Clean code architecture
- ✅ Optimized performance

### Data Processing
- ✅ Multiple judges per judgment
- ✅ Multiple advocates (petitioner/respondant)
- ✅ Outcome and case duration nodes
- ✅ Citation cross-referencing
- ✅ Title-based judgment linking

### Output Format
- ✅ Dgraph Live Loader compatible
- ✅ Simple sequential node IDs
- ✅ Proper RDF triple formatting
- ✅ Schema validation ready

## 📈 Performance Optimizations

1. **Direct Elasticsearch Integration**: No Excel file processing overhead
2. **Optimized List Parsing**: Handles both array and string formats
3. **Efficient Node Mapping**: Prevents duplicate node creation
4. **Batch Processing**: Configurable batch sizes
5. **Memory Management**: Streaming document processing

## 🔍 Usage Examples

### Query Examples for Generated Data

**Find Petitioner Won Cases:**
```graphql
{
  petitioner_won_cases(func: eq(name, "Petitioner Won")) {
    name
    ~has_outcome {
      title
      petitioner_represented_by {
        name
      }
    }
  }
}
```

**Find Judges and Their Cases:**
```graphql
{
  judges(func: has(judge_id)) {
    name
    ~judged_by {
      title
      has_outcome {
        name
      }
    }
  }
}
```

## 🛠️ Development

### Adding New Features
1. Update models in `models.py`
2. Add processing logic in `rdf_generator.py`
3. Update schema in `rdf.schema`
4. Add configuration in `.env`

### Environment Variables
See `.env` file for all available configuration options.

## 📝 Logs

Application logs are written to `rdf_generator.log` with detailed processing information.

## 🎉 Results

- **Input**: 7 legal judgments from Elasticsearch
- **Output**: 314 RDF triples
- **Nodes**: 56 total (7 judgments + 18 judges + 22 advocates + 2 outcomes + 7 case durations)
- **Relationships**: All properly linked with semantic predicates

Both versions generate compatible RDF output for Dgraph.
