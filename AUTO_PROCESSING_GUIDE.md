# 🚀 Automatic Processing Setup

## Overview
The FastAPI application now includes **automatic background processing** that continuously monitors Elasticsearch for new documents and automatically processes them to Dgraph.

## ✨ How It Works

1. **FastAPI starts** → Automatic processor starts in the background
2. **Every 60 seconds** (configurable) → Checks Elasticsearch for unprocessed documents
3. **If new documents found** → Automatically processes and uploads to Dgraph
4. **Documents marked as processed** → Won't be processed again

## 🎯 Quick Start

### 1. Start the FastAPI Server
```bash
cd /home/anish/Desktop/Anish/Dgraph_final
uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload
```

Or simply:
```bash
python3 fastapi_app.py
```

### 2. That's It! 🎉
Once the server starts, the automatic processor will:
- ✅ Start checking for new documents every 60 seconds
- ✅ Automatically process any new documents found
- ✅ Upload to Dgraph automatically
- ✅ Mark documents as processed in Elasticsearch

## ⚙️ Configuration

Edit `.env` to change the check interval:

```env
# Check for new documents every 30 seconds
AUTO_PROCESS_INTERVAL=30

# Check for new documents every 2 minutes
AUTO_PROCESS_INTERVAL=120

# Check for new documents every 5 minutes
AUTO_PROCESS_INTERVAL=300
```

## 📊 Monitor Automatic Processing

### Check Auto Processor Status
```bash
curl http://localhost:8003/auto-processor/status
```

**Response:**
```json
{
  "is_running": true,
  "is_processing": false,
  "check_interval": 60,
  "last_check": "2025-11-05T10:30:00",
  "last_process": "2025-11-05T10:28:00",
  "total_processed": 25
}
```

### Check Full System Stats
```bash
curl http://localhost:8003/stats
```

**Response includes auto processor info:**
```json
{
  "elasticsearch": {
    "total": 500,
    "processed": 475,
    "unprocessed": 25
  },
  "auto_processor": {
    "is_running": true,
    "total_processed": 150
  }
}
```

## 🔄 Workflow

### When You Add New Documents to Elasticsearch:

1. **Upload new documents** to Elasticsearch (using your upload script)
2. **Wait up to 60 seconds** (or your configured interval)
3. **Automatic processor detects** the new documents
4. **Processing starts automatically** in the background
5. **Documents are uploaded** to Dgraph
6. **Documents marked as processed** in Elasticsearch
7. **Check the logs** to see processing status

### Example Log Output:
```
2025-11-05 10:30:00 - INFO - 🚀 FastAPI application starting...
2025-11-05 10:30:00 - INFO - ✅ Configuration validated successfully
2025-11-05 10:30:00 - INFO - 🤖 Starting automatic document processor (interval: 60s)...
2025-11-05 10:30:00 - INFO - ✅ Automatic document processor started!
2025-11-05 10:31:00 - INFO - 📦 Found 5 new document(s) - Starting automatic processing...
2025-11-05 10:31:15 - INFO - ✅ Auto-processed 5 document(s) successfully!
2025-11-05 10:31:15 - INFO - 📊 Total documents auto-processed: 5
2025-11-05 10:32:00 - INFO - ✅ No new documents to process (checked at 10:32:00)
```

## 🎛️ API Endpoints

### Health Check
```bash
curl http://localhost:8003/health
```

### Auto Processor Status
```bash
curl http://localhost:8003/auto-processor/status
```

### Document Counts
```bash
curl http://localhost:8003/documents/count
```

### System Statistics (includes auto processor)
```bash
curl http://localhost:8003/stats
```

### Manual Processing (if needed)
```bash
curl -X POST http://localhost:8003/process \
  -H "Content-Type: application/json" \
  -d '{"doc_ids": null, "force_reprocess": false, "auto_upload": true}'
```

## 📝 Notes

- **Non-blocking**: Auto processing runs in the background, doesn't block API requests
- **Smart checking**: Only processes if new documents are found
- **Error recovery**: Continues running even if a processing attempt fails
- **Configurable interval**: Adjust check frequency based on your needs
- **No duplicate processing**: Documents are marked as processed to prevent reprocessing

## 🐛 Troubleshooting

### Check if auto processor is running:
```bash
curl http://localhost:8003/auto-processor/status | python3 -m json.tool
```

### View real-time logs:
The terminal where you run uvicorn will show all processing logs in real-time.

### Change check interval:
Edit `.env` and change `AUTO_PROCESS_INTERVAL`, then restart the server.

### Manually trigger processing:
Use the `/process` endpoint if you want to process immediately without waiting for the next check.

---

## 🎯 Summary

**Just start the FastAPI server and everything happens automatically!**

```bash
uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload
```

New documents added to Elasticsearch will be automatically:
1. Detected (every 60 seconds)
2. Processed (RDF generation)
3. Uploaded (to Dgraph)
4. Marked as processed (in Elasticsearch)

No manual intervention needed! 🚀
