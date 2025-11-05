# FastAPI Documentation for Legal Judgment RDF Generator

## 🚀 Quick Start

### Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

Or with uv (faster):
```bash
uv pip install -r requirements.txt
```

### Running the FastAPI Server

**Start the server:**
```bash
uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **Base URL:** http://localhost:8000
- **Interactive Docs (Swagger):** http://localhost:8000/docs
- **Alternative Docs (ReDoc):** http://localhost:8000/redoc

## 📡 API Endpoints

### 1. Health Check
**GET** `/health`

Check if the system is healthy and all connections are working.

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "elasticsearch_connected": true,
  "dgraph_configured": true,
  "timestamp": "2025-11-05T10:30:00"
}
```

---

### 2. Get Processing Status
**GET** `/status`

Get current processing status and last run information.

```bash
curl http://localhost:8000/status
```

**Response:**
```json
{
  "is_processing": false,
  "last_run": "2025-11-05T10:25:00",
  "last_run_status": "success",
  "last_run_stats": {
    "judgments": 150,
    "judges": 45,
    "total_triples": 2500
  },
  "current_progress": null
}
```

---

### 3. Process Documents (Main Endpoint)
**POST** `/process`

Process legal judgments from Elasticsearch and generate RDF.

**Request Body:**
```json
{
  "doc_ids": null,
  "force_reprocess": false,
  "auto_upload": true
}
```

**Parameters:**
- `doc_ids`: (Optional) Array of specific document IDs to process. If `null`, processes all unprocessed documents.
- `force_reprocess`: (Boolean) If `true`, reprocess documents even if already processed.
- `auto_upload`: (Boolean) If `true`, automatically upload to Dgraph after processing.

**Example - Process all unprocessed documents:**
```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{
    "doc_ids": null,
    "force_reprocess": false,
    "auto_upload": true
  }'
```

**Example - Process specific documents:**
```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{
    "doc_ids": ["Di8xUpoBv-NWr3guCpOQ", "Dy8xUpoBv-NWr3guCpOQ"],
    "force_reprocess": false,
    "auto_upload": true
  }'
```

**Response:**
```json
{
  "status": "accepted",
  "message": "Processing started in background",
  "job_id": "20251105103000",
  "timestamp": "2025-11-05T10:30:00"
}
```

---

### 4. Get Unprocessed Documents
**GET** `/documents/unprocessed?limit=100`

Get a list of documents that haven't been processed yet.

```bash
curl "http://localhost:8000/documents/unprocessed?limit=100"
```

**Response:**
```json
{
  "total": 25,
  "documents": [
    {
      "es_id": "Di8xUpoBv-NWr3guCpOQ",
      "doc_id": "Di8xUpoBv-NWr3guCpOQ",
      "title": "Sample Judgment Title 1"
    },
    {
      "es_id": "Dy8xUpoBv-NWr3guCpOQ",
      "doc_id": "Dy8xUpoBv-NWr3guCpOQ",
      "title": "Sample Judgment Title 2"
    }
  ]
}
```

---

### 5. Get Document Counts
**GET** `/documents/count`

Get counts of processed and unprocessed documents.

```bash
curl http://localhost:8000/documents/count
```

**Response:**
```json
{
  "total": 500,
  "processed": 475,
  "unprocessed": 25
}
```

---

### 6. Mark Documents as Processed
**POST** `/documents/mark-processed`

Manually mark specific documents as processed (useful for administrative tasks).

```bash
curl -X POST http://localhost:8000/documents/mark-processed \
  -H "Content-Type: application/json" \
  -d '["Di8xUpoBv-NWr3guCpOQ", "Dy8xUpoBv-NWr3guCpOQ"]'
```

**Response:**
```json
{
  "status": "success",
  "message": "Marked 2 documents as processed",
  "updated_count": 2,
  "doc_ids": ["Di8xUpoBv-NWr3guCpOQ", "Dy8xUpoBv-NWr3guCpOQ"]
}
```

---

### 7. Reset Processed Status
**POST** `/documents/reset-processed`

Reset processed status for documents (to allow reprocessing).

**Reset all documents:**
```bash
curl -X POST http://localhost:8000/documents/reset-processed
```

**Reset specific documents:**
```bash
curl -X POST http://localhost:8000/documents/reset-processed \
  -H "Content-Type: application/json" \
  -d '["Di8xUpoBv-NWr3guCpOQ"]'
```

**Response:**
```json
{
  "status": "success",
  "message": "Reset processed status for 1 documents",
  "reset_count": 1,
  "doc_ids": ["Di8xUpoBv-NWr3guCpOQ"]
}
```

---

### 8. Get System Statistics
**GET** `/stats`

Get overall system statistics including document counts and processing history.

```bash
curl http://localhost:8000/stats
```

**Response:**
```json
{
  "elasticsearch": {
    "total": 500,
    "processed": 475,
    "unprocessed": 25
  },
  "rdf_file": {
    "exists": true,
    "size_bytes": 1234567,
    "last_modified": "2025-11-05T10:25:00"
  },
  "last_processing": {
    "timestamp": "2025-11-05T10:25:00",
    "status": "success",
    "stats": {
      "judgments": 150,
      "judges": 45,
      "total_triples": 2500
    }
  }
}
```

---

## 🔄 Typical Workflow

### 1. **Check System Health**
```bash
curl http://localhost:8000/health
```

### 2. **Check for Unprocessed Documents**
```bash
curl http://localhost:8000/documents/count
```

### 3. **Process New Documents**
```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"doc_ids": null, "force_reprocess": false, "auto_upload": true}'
```

### 4. **Monitor Processing Status**
```bash
curl http://localhost:8000/status
```

### 5. **View Statistics**
```bash
curl http://localhost:8000/stats
```

---

## 🔧 Configuration

The API uses environment variables from `.env`:

```env
# Elasticsearch
ELASTICSEARCH_HOST=http://localhost:9200
ELASTICSEARCH_INDEX=graphdb

# Dgraph
DGRAPH_HOST=dgraph-standalone:9080
DGRAPH_ZERO=dgraph-standalone:5080

# Output
RDF_OUTPUT_FILE=judgments.rdf
RDF_SCHEMA_FILE=rdf.schema

# FastAPI
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
```

---

## 🐛 Troubleshooting

### Issue: "Processing is already in progress"
**Solution:** Wait for the current processing to complete, or check status with:
```bash
curl http://localhost:8000/status
```

### Issue: "Elasticsearch not connected"
**Solution:** 
1. Check if Elasticsearch is running: `curl http://localhost:9200`
2. Verify ELASTICSEARCH_HOST in `.env`

### Issue: "No unprocessed documents"
**Solution:** All documents are already processed. To reprocess:
```bash
curl -X POST http://localhost:8000/documents/reset-processed
```

---

## 📊 Python Client Example

```python
import requests

API_BASE = "http://localhost:8000"

# Check health
response = requests.get(f"{API_BASE}/health")
print(response.json())

# Process all unprocessed documents
response = requests.post(
    f"{API_BASE}/process",
    json={
        "doc_ids": None,
        "force_reprocess": False,
        "auto_upload": True
    }
)
print(response.json())

# Check status
response = requests.get(f"{API_BASE}/status")
print(response.json())

# Get statistics
response = requests.get(f"{API_BASE}/stats")
print(response.json())
```

---

## 🎯 Key Features

✅ **Incremental Processing**: Only processes new/unprocessed documents  
✅ **Automatic Tracking**: Marks documents as processed in Elasticsearch  
✅ **Background Processing**: Non-blocking API calls  
✅ **Real-time Status**: Monitor processing progress  
✅ **Flexible Control**: Process all or specific documents  
✅ **Force Reprocess**: Option to reprocess documents  
✅ **Auto Upload**: Automatic Dgraph upload after processing  

---

## 🚦 Status Codes

- `200`: Success
- `202`: Accepted (processing started)
- `409`: Conflict (already processing)
- `500`: Internal server error

---

## 📖 Interactive Documentation

Visit http://localhost:8000/docs for interactive API documentation where you can:
- View all endpoints
- Test API calls directly from browser
- See request/response schemas
- Download OpenAPI specification
