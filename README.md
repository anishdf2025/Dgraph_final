# Legal Judgment Knowledge Graph System - Complete Documentation

**Project**: Legal Judgment Database with RDF Generation and Graph Database Integration  
**Author**: Anish DF  
**Last Updated**: November 5, 2025  
**Version**: 2.0

---

## 📑 Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Data Flow](#data-flow)
6. [Core Components](#core-components)
7. [Configuration Management](#configuration-management)
8. [API Endpoints](#api-endpoints)
9. [Installation & Setup](#installation--setup)
10. [Usage Guide](#usage-guide)
11. [Data Models](#data-models)
12. [Relationship Handlers](#relationship-handlers)
13. [Auto-Processing System](#auto-processing-system)
14. [Troubleshooting](#troubleshooting)
15. [Best Practices](#best-practices)

---

## 🎯 Overview

This project is a **comprehensive legal judgment knowledge graph system** that processes legal case data from Excel files, stores it in Elasticsearch, generates RDF (Resource Description Framework) triples, and uploads them to Dgraph for graph-based querying and analysis.

### Key Features

- ✅ **Excel to Elasticsearch**: Upload legal judgments from Excel spreadsheets
- ✅ **Automatic RDF Generation**: Convert structured legal data to RDF triples
- ✅ **Graph Database Integration**: Store and query data in Dgraph
- ✅ **REST API**: FastAPI-based API for all operations
- ✅ **Auto-Processing**: Automatic background processing of new documents
- ✅ **Modular Architecture**: Clean separation of concerns with relationship handlers
- ✅ **Incremental Processing**: Only process new/updated documents
- ✅ **Health Monitoring**: Built-in health checks for all services

### What Problem Does It Solve?

Legal judgments contain complex relationships between:
- **Judges** who presided over cases
- **Advocates** representing petitioners and respondents
- **Citations** referencing previous judgments
- **Outcomes** (Petitioner Won / Respondent Won)
- **Case Durations** (filing date to judgment date)

Traditional relational databases struggle with these interconnected relationships. This system uses a **graph database** to represent and query these relationships naturally.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│              (Swagger UI / REST API Clients)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FastAPI Application                        │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐   │
│  │   Health    │  │  Document   │  │   Auto-Processing    │   │
│  │   Checks    │  │  Processing │  │   Background Task    │   │
│  └─────────────┘  └─────────────┘  └──────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┴──────────────────┐
          ▼                                     ▼
┌─────────────────────┐              ┌─────────────────────┐
│   Elasticsearch     │              │   Dgraph Database   │
│   (Document Store)  │              │   (Graph Database)  │
│                     │              │                     │
│  • Index: graphdb   │              │  • Schema: RDF      │
│  • Port: 9200       │              │  • Port: 9080/5080  │
│  • JSON Documents   │              │  • RDF Triples      │
└─────────────────────┘              └─────────────────────┘
          ▲                                     ▲
          │                                     │
┌─────────┴─────────┐              ┌───────────┴──────────┐
│  Excel Upload     │              │  RDF Generator       │
│  elasticsearch_   │              │  modular_rdf_        │
│  upload.py        │              │  generator.py        │
└───────────────────┘              └──────────────────────┘
```

### Component Interaction Flow

1. **Excel Upload**: User uploads Excel file → Elasticsearch (via `elasticsearch_upload.py`)
2. **Auto-Detection**: FastAPI background task detects new documents every 60 seconds
3. **RDF Generation**: Incremental processor generates RDF triples from new documents
4. **Graph Upload**: RDF triples uploaded to Dgraph via Docker container
5. **Status Update**: Documents marked as "processed" in Elasticsearch

---

## 🔧 Technology Stack

### Backend Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.11+ | Core programming language |
| **FastAPI** | 0.104.0+ | REST API framework |
| **Elasticsearch** | 8.x | Document storage and search |
| **Dgraph** | v23.1.0 | Graph database |
| **Docker** | Latest | Container orchestration |
| **Uvicorn** | Latest | ASGI server |

### Python Libraries

```
fastapi>=0.104.0
uvicorn>=0.24.0
elasticsearch>=8.11.0
pandas>=2.1.3
openpyxl>=3.1.2
python-dotenv>=1.0.0
```

### Infrastructure

- **Operating System**: Linux (Ubuntu/Debian)
- **Shell**: Bash
- **Docker Network**: `dgraph-net`
- **Virtual Environment**: `.venv`

---

## 📂 Project Structure

```
/home/anish/Desktop/Anish/Dgraph_final/
│
├── 📄 Core Application Files
│   ├── fastapi_app.py              # Main FastAPI application (11 endpoints)
│   ├── incremental_processor.py    # Incremental RDF processing with modular handlers
│   ├── auto_processor.py           # Background auto-processing task
│   ├── elasticsearch_upload.py     # Excel to Elasticsearch uploader
│   └── elasticsearch_handler.py    # Elasticsearch connection handler
│
├── 📊 Data Models & Utilities
│   ├── models.py                   # Pydantic data models
│   ├── utils.py                    # Utility functions (logging, parsing)
│   └── config.py                   # Configuration management
│
├── 🔗 Relationship Handlers
│   └── relationships/
│       ├── __init__.py
│       ├── judge_relationship.py       # Judge-judgment relationships
│       ├── advocate_relationship.py    # Advocate-judgment relationships
│       ├── outcome_relationship.py     # Outcome-judgment relationships
│       ├── case_duration_relationship.py  # Duration relationships
│       └── citation_relationship.py    # Citation cross-references
│
├── ⚙️ Configuration Files
│   ├── .env                        # Environment variables (NOT in Git)
│   ├── rdf.schema                  # Dgraph schema definition
│   └── docker_information.txt      # Docker setup commands
│
├── 📁 Data Files
│   ├── excel_2024_2025/            # Excel data files
│   │   └── FINAL/
│   │       └── 5_sample/
│   │           └── tests.xlsx      # Sample legal judgments
│   ├── judgments.rdf               # Generated RDF output
│   └── elasticsearch_upload.log    # Upload logs
│
└── 📚 Documentation
    └── PROJECT_DOCUMENTATION.md    # This file

```

---

## 🔄 Data Flow

### Complete Processing Pipeline

```
Step 1: Excel Upload
┌──────────────────┐
│  tests.xlsx      │  (Excel file with legal judgments)
│  - Title         │
│  - Judges        │
│  - Advocates     │
│  - Citations     │
│  - Outcomes      │
│  - Dates         │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  elasticsearch_upload.py                 │
│  • Reads Excel file                      │
│  • Parses each row                       │
│  • Uploads to Elasticsearch              │
└────────┬─────────────────────────────────┘
         │
         ▼
Step 2: Document Storage
┌──────────────────────────────────────────┐
│  Elasticsearch (Index: graphdb)          │
│  {                                       │
│    "_id": "doc_123",                     │
│    "title": "Case Title",                │
│    "judges": ["Judge 1", "Judge 2"],     │
│    "processed": false                    │
│  }                                       │
└────────┬─────────────────────────────────┘
         │
         ▼
Step 3: Auto-Detection (Every 60s)
┌──────────────────────────────────────────┐
│  auto_processor.py                       │
│  • Counts total documents                │
│  • Counts processed documents            │
│  • If difference > 0: trigger processing │
└────────┬─────────────────────────────────┘
         │
         ▼
Step 4: RDF Generation
┌──────────────────────────────────────────┐
│  incremental_processor.py                │
│  • Loads unprocessed documents           │
│  • Uses modular relationship handlers    │
│  • Generates RDF triples                 │
│  • Combines all relationships            │
└────────┬─────────────────────────────────┘
         │
         ▼
Step 5: Relationship Processing
┌──────────────────────────────────────────┐
│  Relationship Handlers                   │
│  ├── JudgeRelationship                   │
│  ├── AdvocateRelationship                │
│  ├── OutcomeRelationship                 │
│  ├── CaseDurationRelationship            │
│  └── CitationRelationship                │
└────────┬─────────────────────────────────┘
         │
         ▼
Step 6: RDF Output
┌──────────────────────────────────────────┐
│  judgments.rdf                           │
│  <j_123> <title> "Case Title" .          │
│  <j_123> <judged_by> <judge1> .          │
│  <judge1> <name> "Judge Name" .          │
└────────┬─────────────────────────────────┘
         │
         ▼
Step 7: Graph Database Upload
┌──────────────────────────────────────────┐
│  Dgraph Live Loader (Docker)             │
│  • Reads judgments.rdf                   │
│  • Applies rdf.schema                    │
│  • Uploads to Dgraph                     │
└────────┬─────────────────────────────────┘
         │
         ▼
Step 8: Status Update
┌──────────────────────────────────────────┐
│  Update Elasticsearch                    │
│  { "processed": true }                   │
└──────────────────────────────────────────┘
```

---

## 🧩 Core Components

### 1. FastAPI Application (`fastapi_app.py`)

**Purpose**: Main REST API server providing all endpoints for system interaction.

**Key Features**:
- 11 REST endpoints
- Swagger UI documentation at `/docs`
- Background auto-processing task
- Health check monitoring
- CORS enabled

**Startup Process**:
1. Validates configuration
2. Checks Elasticsearch connection
3. Starts auto-processing background task
4. Listens on port 8003

### 2. Elasticsearch Handler (`elasticsearch_handler.py`)

**Purpose**: Manages all Elasticsearch interactions.

**Key Responsibilities**:
- Connection validation
- Document loading (filtered by `processed` field)
- Field parsing (handles both arrays and strings)
- Error handling and retries

**Important Methods**:
```python
def connect(self) -> bool
def load_documents(self, batch_size: int) -> List[Dict]
def _parse_list_field(self, field: str) -> List[str]
```

### 3. Incremental Processor (`incremental_processor.py`)

**Purpose**: Orchestrates the incremental RDF generation process.

**Processing Flow**:
1. Load unprocessed documents from Elasticsearch
2. Build title mappings for citation cross-references
3. Process each judgment through relationship handlers
4. Combine RDF triples from all handlers
5. Write to `judgments.rdf` file
6. Upload to Dgraph via Docker
7. Mark documents as processed

**Configuration**:
- **Batch Processing**: Configurable batch sizes
- **Auto Upload**: Optional automatic Dgraph upload
- **Force Reprocess**: Ability to reprocess all documents

**Two-Pass Processing**:

**Pass 1**: Data Collection
- Collect all judgment data from Elasticsearch
- Build title-to-ID mappings for citation cross-references
- Create node ID counters for each entity type

**Pass 2**: Relationship Creation (via Modular Handlers)
- Process judges (via `JudgeRelationshipHandler`)
- Process advocates - petitioner & respondent (via `AdvocateRelationshipHandler`)
- Process outcomes (via `OutcomeRelationshipHandler`)
- Process case durations (via `CaseDurationRelationshipHandler`)
- Process citations with cross-references (via `CitationRelationshipHandler`)

**Output Statistics**:
- Total judgments processed
- Total judges, advocates, outcomes, durations, citations
- Total RDF triples generated
- Processing time and performance metrics

### 4. Auto Processor (`auto_processor.py`)

**Purpose**: Background task that automatically processes new documents.

**How It Works**:
1. Runs every 60 seconds (configurable via `AUTO_PROCESS_INTERVAL`)
2. Counts total documents in Elasticsearch
3. Counts processed documents
4. If new documents found: triggers processing
5. Logs all activity

**Benefits**:
- Zero manual intervention required
- Real-time processing of uploaded documents
- System stays synchronized automatically

### 5. Excel Upload (`elasticsearch_upload.py`)

**Purpose**: Upload legal judgment data from Excel to Elasticsearch.

**Features**:
- **Hardcoded Excel Path**: User-specific file location
- **Column Mapping**: Automatically maps Excel columns to Elasticsearch fields
- **Data Validation**: Validates required fields
- **Batch Upload**: Efficient bulk upload

**Excel File Structure**:
```
| Title | Judges | Petitioner Advocates | Respondent Advocates | Citations | Outcome | Filing Date | Judgment Date |
```

**Default Excel Path**:
```python
DEFAULT_EXCEL_PATH = '/home/anish/Desktop/Anish/Dgraph_final/excel_2024_2025/FINAL/5_sample/tests.xlsx'
```

---

## ⚙️ Configuration Management

### Environment Variables (`.env`)

```bash
# Elasticsearch Configuration
ELASTICSEARCH_HOST=http://localhost:9200
ELASTICSEARCH_INDEX=graphdb
ELASTICSEARCH_TIMEOUT=30

# Dgraph Configuration
DGRAPH_HOST=dgraph-standalone
DGRAPH_ZERO=dgraph-standalone:5080

# FastAPI Configuration
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8003
FASTAPI_RELOAD=true

# Processing Configuration
AUTO_PROCESS_INTERVAL=60

# Docker Configuration
DOCKER_NETWORK=dgraph-net
DGRAPH_IMAGE=dgraph/dgraph:v23.1.0
```

### Configuration Class (`config.py`)

**Purpose**: Centralized configuration management with validation.

**Key Features**:
- Type-safe configuration access
- Environment variable loading with defaults
- Configuration validation on startup
- Grouped configuration getters

**Usage Example**:
```python
from config import config

# Access individual config
es_host = config.ELASTICSEARCH_HOST
api_port = config.FASTAPI_PORT

# Get grouped config
es_config = config.get_elasticsearch_config()
# Returns: {'host': 'http://localhost:9200', 'index': 'graphdb', 'timeout': 30}
```

### Configuration Best Practices

✅ **DO**:
- Keep `.env` file out of Git (security)
- Use environment-specific values
- Validate configuration on startup
- Use type hints for all config variables

❌ **DON'T**:
- Hardcode credentials in source code
- Commit `.env` to Git
- Use production credentials in development
- Mix user-specific paths with shared config

---

## 🌐 API Endpoints

### Base URL: `http://localhost:8003`

### 1. Health Check
```http
GET /health
```
**Response**:
```json
{
  "status": "healthy",
  "elasticsearch_connected": true,
  "dgraph_configured": true
}
```

### 2. Process All Documents
```http
POST /process
```
**Query Parameters**:
- `force` (optional): Reprocess all documents

**Response**:
```json
{
  "status": "processing_complete",
  "documents_processed": 8,
  "rdf_triples": 331,
  "rdf_file": "judgments.rdf"
}
```

### 3. Process Specific Document
```http
POST /process/document/{doc_id}
```
**Response**: Similar to `/process`

### 4. Upload Excel to Elasticsearch
```http
POST /upload-excel
```
**Request Body**:
```json
{
  "file_path": "/path/to/excel.xlsx"
}
```

### 5. Reset All Documents
```http
POST /reset
```
**Response**:
```json
{
  "status": "reset_complete",
  "documents_reset": 8
}
```

### 6. Get Statistics
```http
GET /stats
```
**Response**:
```json
{
  "total_documents": 8,
  "processed_documents": 8,
  "unprocessed_documents": 0,
  "processing_enabled": true
}
```

### 7. Check Processing Status
```http
GET /processing/status
```

### 8. Enable/Disable Auto-Processing
```http
POST /processing/enable
POST /processing/disable
```

### 9. Trigger Manual Processing
```http
POST /processing/trigger
```

### 10. Get All Judgments
```http
GET /judgments
```
**Response**: List of all judgment documents

### 11. Get Document Count
```http
GET /documents/count
```
**Response**:
```json
{
  "total": 8,
  "processed": 8,
  "unprocessed": 0
}
```

---

## 🛠️ Installation & Setup

### Prerequisites

1. **Docker** with Dgraph running
2. **Python 3.11+**
3. **Elasticsearch 8.x** running on port 9200
4. **Virtual environment** (recommended)

### Step 1: Clone and Setup

```bash
# Navigate to project directory
cd /home/anish/Desktop/Anish/Dgraph_final

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

Create `.env` file:
```bash
cp .env.example .env
nano .env
```

Update with your settings.

### Step 3: Start Dgraph (Docker)

```bash
# Create Docker network
docker network create dgraph-net

# Start Dgraph Zero
docker run -d -p 5080:5080 --network dgraph-net --name dgraph-zero \
  dgraph/dgraph:v23.1.0 dgraph zero --my=dgraph-zero:5080

# Start Dgraph Alpha
docker run -d -p 8080:8080 -p 9080:9080 --network dgraph-net --name dgraph-standalone \
  -v ~/dgraph:/dgraph dgraph/dgraph:v23.1.0 dgraph alpha \
  --my=dgraph-standalone:7080 --zero=dgraph-zero:5080
```

### Step 4: Start Elasticsearch

```bash
# If using Docker
docker run -d -p 9200:9200 -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

### Step 5: Start FastAPI Application

```bash
uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload
```

### Step 6: Access Swagger UI

Open browser: `http://localhost:8003/docs`

---

## 📖 Usage Guide

### Scenario 1: Upload New Judgments

1. **Prepare Excel file** with judgment data
2. **Upload to Elasticsearch**:
   ```bash
   python3 elasticsearch_upload.py
   ```
3. **Wait 60 seconds** - Auto-processor will detect and process
4. **Check results** at `/stats` endpoint

### Scenario 2: Manual Processing

```bash
# Via API
curl -X POST http://localhost:8003/process

# View generated RDF
cat judgments.rdf
```

### Scenario 3: Reset and Reprocess

```bash
# Reset all documents
curl -X POST http://localhost:8003/reset

# Reprocess with force flag
curl -X POST http://localhost:8003/process?force=true
```

### Scenario 4: Query Dgraph

Access Dgraph Ratel UI: `http://localhost:8000`

**Example Query**:
```graphql
{
  all_judgments(func: has(title)) {
    title
    judged_by {
      name
    }
    has_outcome {
      name
    }
  }
}
```

---

## 📊 Data Models

### Judgment Document (Elasticsearch)

```json
{
  "_id": "YC-EU5oBv-NWr3guLJNd",
  "title": "A @ K v. The State of Uttarakhand",
  "judges": ["Justice Krishna Murari", "Justice P. S. Narasimha"],
  "petitioner_advocates": ["Mr. Sidharth Luthra"],
  "respondent_advocates": ["Mr. Maninder Singh", "Mr. Vikramjit Banerjee"],
  "citations": ["State of Uttarakhand v. Harpal Singh (2021)"],
  "outcome": "Petitioner Won",
  "filing_date": "2022-02-11",
  "judgment_date": "2022-09-21",
  "processed": true,
  "processed_at": "2025-11-05T10:39:44"
}
```

### RDF Triple Format

```rdf
# Judgment Node
<j_79a3da7a> <title> "A @ K v. The State of Uttarakhand" .
<j_79a3da7a> <dgraph.type> "Judgment" .

# Judge Node
<judge1> <name> "Justice Krishna Murari" .
<judge1> <judge_id> "judge1" .
<judge1> <dgraph.type> "Judge" .

# Relationship
<j_79a3da7a> <judged_by> <judge1> .
```

---

## 🔗 Relationship Handlers

### 1. Judge Relationship Handler

**File**: `relationships/judge_relationship.py`

**Purpose**: Creates judge nodes and links them to judgments.

**Process**:
1. Parse judges list from document
2. Generate unique judge node ID
3. Create judge RDF triples
4. Create `judged_by` relationship

**Output Example**:
```rdf
<judge1> <name> "Justice Krishna Murari" .
<j_123> <judged_by> <judge1> .
```

### 2. Advocate Relationship Handler

**File**: `relationships/advocate_relationship.py`

**Purpose**: Creates advocate nodes for both petitioners and respondents.

**Two Types**:
- **Petitioner Advocates**: `petitioner_represented_by`
- **Respondent Advocates**: `respondant_represented_by`

**Output Example**:
```rdf
<petitioner_advocate1> <name> "Mr. Sidharth Luthra" .
<j_123> <petitioner_represented_by> <petitioner_advocate1> .
```

### 3. Outcome Relationship Handler

**File**: `relationships/outcome_relationship.py`

**Purpose**: Creates outcome nodes (reused across judgments).

**Two Outcomes**:
- `outcome1`: "Petitioner Won"
- `outcome2`: "Respondent Won"

**Output Example**:
```rdf
<outcome1> <name> "Petitioner Won" .
<j_123> <has_outcome> <outcome1> .
```

### 4. Case Duration Relationship Handler

**File**: `relationships/case_duration_relationship.py`

**Purpose**: Creates case duration nodes with filing and judgment dates.

**Calculates**:
- Duration in days
- Filing date
- Judgment date

**Output Example**:
```rdf
<case_duration1> <duration_text> "2022-02-11 to 2022-09-21" .
<case_duration1> <duration_days> "222" .
<j_123> <has_case_duration> <case_duration1> .
```

### 5. Citation Relationship Handler

**File**: `relationships/citation_relationship.py`

**Purpose**: Creates citation nodes and cross-references to cited judgments.

**Two Types of Relationships**:
1. **Citation Node**: Creates node for citation text
2. **Title Match**: Links to actual judgment if found

**Output Example**:
```rdf
<c1> <citation_text> "State of Uttarakhand v. Harpal Singh" .
<j_123> <cites> <c1> .
<j_123> <references> <j_456> .  # If title match found
```

---

## 🤖 Auto-Processing System

### How It Works

```python
# auto_processor.py

class AutoProcessor:
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.running = False
    
    async def start(self):
        while self.running:
            # Count documents
            total = await count_total_documents()
            processed = await count_processed_documents()
            
            # If new documents found
            if total > processed:
                await process_documents()
            
            # Wait for next check
            await asyncio.sleep(self.check_interval)
```

### Configuration

Set check interval in `.env`:
```bash
AUTO_PROCESS_INTERVAL=60  # Check every 60 seconds
```

### Monitoring

Check auto-processing status:
```bash
curl http://localhost:8003/processing/status
```

Enable/Disable:
```bash
curl -X POST http://localhost:8003/processing/enable
curl -X POST http://localhost:8003/processing/disable
```

---

## 🐛 Troubleshooting

### Issue 1: API Shows "Unhealthy"

**Symptoms**: `/health` endpoint returns `"status": "unhealthy"`

**Causes**:
- Elasticsearch not running
- Dgraph not configured
- Network connectivity issues

**Solutions**:
```bash
# Check Elasticsearch
curl http://localhost:9200

# Check Dgraph
curl http://localhost:8080/health

# Restart services
docker restart dgraph-standalone
```

### Issue 2: No Documents Being Processed

**Symptoms**: Documents uploaded but not processed

**Causes**:
- Auto-processing disabled
- Documents already marked as processed
- Processing interval too long

**Solutions**:
```bash
# Check status
curl http://localhost:8003/processing/status

# Enable auto-processing
curl -X POST http://localhost:8003/processing/enable

# Trigger manual processing
curl -X POST http://localhost:8003/processing/trigger

# Force reprocess all
curl -X POST http://localhost:8003/process?force=true
```

### Issue 3: Excel Upload Fails

**Symptoms**: `elasticsearch_upload.py` throws errors

**Causes**:
- Wrong Excel file path
- Elasticsearch connection failure
- Invalid Excel format

**Solutions**:
```bash
# Check Excel path in elasticsearch_upload.py
DEFAULT_EXCEL_PATH = '/correct/path/to/tests.xlsx'

# Verify Elasticsearch connection
curl http://localhost:9200/graphdb/_count

# Check Excel file format (required columns)
# Title, Judges, Petitioner Advocates, Respondent Advocates, Citations, Outcome, Filing Date, Judgment Date
```

### Issue 4: Dgraph Upload Fails

**Symptoms**: RDF generated but not uploaded to Dgraph

**Causes**:
- Docker container not running
- Network issues
- Schema mismatch

**Solutions**:
```bash
# Check Dgraph containers
docker ps | grep dgraph

# Restart Dgraph
docker restart dgraph-standalone dgraph-zero

# Verify schema
cat rdf.schema

# Manual upload
docker run -it --rm --network dgraph-net \
  -v /home/anish/Desktop/Anish/Dgraph_final:/data \
  dgraph/dgraph:v23.1.0 dgraph live \
  --files /data/judgments.rdf \
  --schema /data/rdf.schema \
  --alpha dgraph-standalone:9080 \
  --zero dgraph-standalone:5080
```

### Issue 5: Port Already in Use

**Symptoms**: Cannot start FastAPI - port 8003 in use

**Solutions**:
```bash
# Find process using port
lsof -i :8003

# Kill process
kill -9 <PID>

# Or use different port
uvicorn fastapi_app:app --host 0.0.0.0 --port 8004
```

---

## ✅ Best Practices

### 1. Configuration Management

✅ **DO**:
- Use `.env` for environment-specific configuration
- Keep user-specific paths hardcoded (like Excel file location)
- Validate configuration on startup
- Use type hints for all config variables

❌ **DON'T**:
- Commit `.env` to version control
- Hardcode credentials in source code
- Mix configuration types (shared vs. user-specific)

### 2. Data Processing

✅ **DO**:
- Use incremental processing (only new documents)
- Mark documents as processed after successful upload
- Log all processing steps
- Handle errors gracefully

❌ **DON'T**:
- Process already-processed documents unnecessarily
- Skip error handling
- Ignore processing statistics

### 3. API Design

✅ **DO**:
- Use appropriate HTTP methods (GET, POST, PUT, DELETE)
- Return meaningful status codes
- Provide clear error messages
- Document all endpoints in Swagger

❌ **DON'T**:
- Return generic error messages
- Use GET for operations that modify data
- Skip input validation

### 4. Docker & Deployment

✅ **DO**:
- Use Docker networks for container communication
- Mount volumes for persistent data
- Use specific image versions (not `latest`)
- Monitor container health

❌ **DON'T**:
- Use host networking unnecessarily
- Skip volume mounts (data will be lost)
- Run containers as root unnecessarily

### 5. Code Organization

✅ **DO**:
- Separate concerns (models, handlers, utilities)
- Use modular design (relationship handlers)
- Write type hints for all functions
- Keep functions focused and small

❌ **DON'T**:
- Put all code in one file
- Mix business logic with API endpoints
- Skip documentation

---

## 📈 Performance Optimization

### Current Performance

- **Processing Speed**: ~331 RDF triples in < 2 seconds
- **Document Count**: Handles 1000+ judgments efficiently
- **Memory Usage**: Minimal (streaming document processing)
- **API Response Time**: < 500ms for most endpoints

### Optimization Tips

1. **Batch Processing**: Process documents in batches of 100
2. **Caching**: Cache title mappings for citation lookups
3. **Async Operations**: Use async/await for I/O operations
4. **Connection Pooling**: Reuse Elasticsearch connections
5. **Index Optimization**: Create indexes on `processed` field

---

## 🔮 Future Enhancements

### Planned Features

1. **Web UI Dashboard**: Real-time monitoring and statistics
2. **Advanced Querying**: Graph-based judgment analysis
3. **Bulk Upload**: Support for multiple Excel files
4. **Notification System**: Email/Slack alerts for processing completion
5. **Backup & Restore**: Automated backup of graph data
6. **User Authentication**: API key-based access control
7. **Rate Limiting**: Prevent API abuse
8. **Export Functionality**: Export graphs to various formats

---

## 📞 Support & Contact

For questions, issues, or contributions:

- **Author**: Anish DF
- **Email**: anishdf2025@example.com
- **Repository**: github.com/anishdf2025/Dgraph_final

---

## 📄 License

This project is proprietary and confidential. All rights reserved.

---

## 🙏 Acknowledgments

- **Dgraph Team**: For the excellent graph database
- **FastAPI Team**: For the modern API framework
- **Elasticsearch Team**: For the powerful search engine

---

**Last Updated**: November 5, 2025  
**Version**: 2.0  
**Status**: Production Ready ✅
