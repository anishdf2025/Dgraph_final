# 🚀 Quick Reference Guide - Legal Judgment Knowledge Graph

**Version**: 2.1 | **Last Updated**: November 6, 2025

---

## 📋 Table of Contents

1. [Essential Commands](#essential-commands)
2. [API Endpoints](#api-endpoints)
3. [Common Queries](#common-queries)
4. [File Structure](#file-structure)
5. [Troubleshooting Quick Fixes](#troubleshooting-quick-fixes)

---

## Essential Commands

### Start Services

```bash
# Start Dgraph
docker run -it -p 8180:8080 -p 8181:8081 -p 8000:8000 \
  -v ~/dgraph_data:/dgraph \
  --name dgraph-standalone \
  dgraph/dgraph:v23.1.0

# Start Elasticsearch
docker run -d -p 9200:9200 \
  -e "discovery.type=single-node" \
  --name elasticsearch \
  elasticsearch:8.11.0

# Start FastAPI
uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload
```

### Upload Data

```bash
# Upload schema to Dgraph
curl -X POST localhost:8180/alter -d @rdf.schema

# Upload Excel to Elasticsearch
python3 elasticsearch_upload.py

# Process documents (ES → RDF → Dgraph)
curl -X POST http://localhost:8003/process
```

### Check Status

```bash
# Check Dgraph
curl http://localhost:8180/health

# Check Elasticsearch
curl http://localhost:9200/_cluster/health

# Check FastAPI
curl http://localhost:8003/health

# Check processing status
curl http://localhost:8003/status
```

---

## API Endpoints

### Base URL: `http://localhost:8003`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Welcome message |
| `/health` | GET | System health check |
| `/status` | GET | Processing status |
| `/process` | POST | Process documents |
| `/documents/unprocessed` | GET | List unprocessed docs |
| `/documents/count` | GET | Get document counts |
| `/documents/mark-processed` | POST | Mark docs as processed |
| `/documents/reset-processed` | POST | Reset processed status |
| `/stats` | GET | Get processing statistics |

### Examples

```bash
# Process all unprocessed documents
curl -X POST http://localhost:8003/process

# Process specific documents
curl -X POST http://localhost:8003/process \
  -H "Content-Type: application/json" \
  -d '{
    "doc_ids": ["doc_123", "doc_456"]
  }'

# Force reprocess documents
curl -X POST http://localhost:8003/process \
  -H "Content-Type: application/json" \
  -d '{
    "force_reprocess": true
  }'

# Keep RDF files (don't cleanup)
curl -X POST http://localhost:8003/process \
  -H "Content-Type: application/json" \
  -d '{
    "cleanup_rdf": false
  }'

# Get unprocessed documents
curl http://localhost:8003/documents/unprocessed?limit=10

# Get document counts
curl http://localhost:8003/documents/count

# Reset all documents to unprocessed
curl -X POST http://localhost:8003/documents/reset-processed
```

---

## Common Queries

### Dgraph GraphQL Queries

**Query all judgments:**
```graphql
{
  allJudgments(func: type(Judgment)) {
    uid
    judgment_id
    title
    doc_id
    year
    judged_by {
      name
    }
    has_outcome {
      name
    }
  }
}
```

**Query specific judgment by title:**
```graphql
{
  judgment(func: eq(title, "Your Case Title Here")) {
    uid
    title
    doc_id
    year
    judged_by {
      name
    }
    cites {
      title
    }
    has_outcome {
      name
    }
  }
}
```

**Query all cases by a specific judge:**
```graphql
{
  judge(func: eq(name, "Justice D. Y. Chandrachud")) {
    name
    ~judged_by {
      title
      year
      has_outcome {
        name
      }
    }
  }
}
```

**Count total judgments:**
```graphql
{
  judgments(func: type(Judgment)) {
    total: count(uid)
  }
}
```

**Query with citation network:**
```graphql
{
  judgment(func: eq(title, "Case Title")) {
    uid
    title
    
    # Cases this judgment cites
    cites {
      title
    }
    
    # Cases that cite this judgment (reverse edge)
    ~cites {
      title
    }
  }
}
```

### Elasticsearch Queries

```bash
# Count all documents
curl -X GET "http://localhost:9200/graphdb/_count"

# Search by title
curl -X GET "http://localhost:9200/graphdb/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {
        "title": "your search term"
      }
    }
  }'

# Get unprocessed documents
curl -X GET "http://localhost:9200/graphdb/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "term": {
        "processed_to_dgraph": false
      }
    }
  }'
```

---

## File Structure

```
Dgraph_final/
├── 📄 Core Application Files
│   ├── fastapi_app.py              # REST API server
│   ├── incremental_processor.py    # RDF generator (main logic)
│   ├── elasticsearch_handler.py    # ES data operations
│   ├── utils.py                    # Helper functions (ID generation, etc.)
│   ├── config.py                   # Configuration management
│   └── models.py                   # Data models
│
├── 📦 Relationship Handlers
│   └── relationships/
│       ├── judge_relationship.py
│       ├── advocate_relationship.py
│       ├── citation_relationship.py
│       ├── outcome_relationship.py
│       └── case_duration_relationship.py
│
├── 📤 Upload Scripts
│   ├── elasticsearch_upload.py              # Upload Excel to ES
│   └── elasticsearch_upload_with_delay.py   # Upload with delay
│
├── 🗂️ Configuration
│   ├── .env                        # Environment variables
│   ├── .env.example                # Example config
│   └── rdf.schema                  # Dgraph schema
│
├── 📊 Data Files
│   ├── excel_2024_2025/FINAL/      # Excel data files
│   └── rdf/                        # Generated RDF files
│
├── 📚 Documentation
│   ├── DETAILED_README.md                      # Complete documentation
│   ├── QUICK_REFERENCE.md                      # This file
│   ├── CITATION_TITLE_UNIFICATION.md           # Unification strategy
│   ├── CITATION_TITLE_FIX_VERIFICATION.md      # Fix verification
│   ├── INCREMENTAL_PROCESSING_GUIDE.md         # Processing guide
│   └── docker_information.txt                  # Docker commands
│
└── 🧪 Tests
    └── test_citation_unification.py            # Test suite
```

---

## Troubleshooting Quick Fixes

### Issue: "Cannot connect to Elasticsearch"

```bash
# Check if running
curl http://localhost:9200

# If not, start it
docker run -d -p 9200:9200 \
  -e "discovery.type=single-node" \
  elasticsearch:8.11.0
```

### Issue: "Cannot connect to Dgraph"

```bash
# Check if running
docker ps | grep dgraph

# If not, start it
docker run -it -p 8180:8080 -p 8181:8081 \
  -v ~/dgraph_data:/dgraph \
  dgraph/dgraph:v23.1.0
```

### Issue: "Duplicate nodes in Dgraph"

```bash
# This was fixed in v2.1. To clean up old duplicates:

# 1. Verify fix is applied
grep "create_node_id('judgment', unique_key=title)" incremental_processor.py

# 2. Drop all data
curl -X POST http://localhost:8180/alter -d '{"drop_all": true}'

# 3. Re-upload schema
curl -X POST http://localhost:8180/alter -d @rdf.schema

# 4. Reset ES status
curl -X POST http://localhost:8003/documents/reset-processed

# 5. Reprocess everything
curl -X POST http://localhost:8003/process
```

### Issue: "RDF file not found"

```bash
# Create RDF directory
mkdir -p rdf

# Or check config
cat .env | grep RDF_OUTPUT_FILE
```

### Issue: "Processing stuck"

```bash
# Check logs
tail -f rdf_generator.log

# Check Docker container
docker exec -it dgraph-standalone ls /dgraph/

# Restart FastAPI
# Ctrl+C in terminal, then:
uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload
```

### Issue: "How to verify no duplicates exist?"

```bash
# Run test suite
python3 test_citation_unification.py

# Should show: "🎉 ALL TESTS PASSED!"

# Query Dgraph for specific title
curl -X POST http://localhost:8180/query -d '{
  judgments(func: eq(title, "Your Case Title")) {
    uid
    judgment_id
    title
  }
}' | jq

# If more than 1 result → duplicates exist
```

---

## Environment Variables

Key variables in `.env`:

```bash
# Elasticsearch
ELASTICSEARCH_HOST=http://localhost:9200
ELASTICSEARCH_INDEX=graphdb

# Dgraph
DGRAPH_HOST=dgraph-standalone:9080

# FastAPI
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8003

# RDF Output
RDF_OUTPUT_FILE=rdf/judgments.rdf
```

---

## Key Concepts

### Node ID Generation

```python
# Same content → Same ID (always!)
create_node_id('judge', unique_key="Justice D. Y. Chandrachud")
# Returns: <judge_ea7adefd>

# Normalization applied:
"Case A v. Case B"     → j_abc123
"case a v. case b"     → j_abc123  (same!)
" Case A v. Case B "   → j_abc123  (same!)
```

### Upsert Process

```
1. Generate RDF with stable IDs
2. Upload to Dgraph with --upsert-predicates
3. Dgraph checks: Does this ID exist?
   - YES → Update existing node
   - NO  → Create new node
4. Result: No duplicates!
```

### Incremental Processing

```
1. Query ES: SELECT * WHERE processed_to_dgraph = false
2. Process only unprocessed documents
3. Generate RDF for new documents only
4. Upload to Dgraph (links to existing entities)
5. Mark documents as processed in ES
```

---

## Common Workflows

### Full Reset & Reprocess

```bash
# 1. Drop Dgraph data
curl -X POST http://localhost:8180/alter -d '{"drop_all": true}'

# 2. Upload schema
curl -X POST http://localhost:8180/alter -d @rdf.schema

# 3. Reset ES status
curl -X POST http://localhost:8003/documents/reset-processed

# 4. Process all
curl -X POST http://localhost:8003/process
```

### Add New Data

```bash
# 1. Add to Excel file
# 2. Upload to ES
python3 elasticsearch_upload.py

# 3. Process (only new docs)
curl -X POST http://localhost:8003/process
```

### Query & Verify

```bash
# 1. Count nodes
curl -X POST http://localhost:8180/query -d '{
  judgments(func: type(Judgment)) { total: count(uid) }
  judges(func: type(Judge)) { total: count(uid) }
}'

# 2. Check specific case
curl -X POST http://localhost:8180/query -d '{
  q(func: eq(title, "Case Title")) {
    uid
    title
    judged_by { name }
    cites { title }
  }
}'
```

---

## Testing

```bash
# Run citation-title unification tests
python3 test_citation_unification.py

# Expected output:
# 🎉 ALL TESTS PASSED!
# ✅ Citation-Judgment Unification
# ✅ Real-World Scenario
# ✅ Title Normalization
```

---

## Additional Resources

- **Full Documentation**: `DETAILED_README.md`
- **Citation Fix Details**: `CITATION_TITLE_FIX_VERIFICATION.md`
- **Sample Queries**: `querry_cli.txt`
- **Docker Commands**: `docker_information.txt`

---

**Support**: Check logs in `rdf_generator.log` and `elasticsearch_upload.log`  
**Version**: 2.1  
**Author**: Anish DF
