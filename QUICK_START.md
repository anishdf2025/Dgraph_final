# 🚀 Quick Start: Incremental Processing with Clean RDF Files

## How It Works Now

When new documents are added to Elasticsearch, the system:

1. ✅ **Detects** only unprocessed documents (`processed_to_dgraph: false`)
2. ✅ **Creates** a fresh RDF file with ONLY the new documents
3. ✅ **Uploads** to Dgraph (automatically links to existing judges, advocates, etc.)
4. ✅ **Marks** documents as processed in Elasticsearch
5. ✅ **Cleans up** - backs up and deletes the RDF file

**Result:** Clean workspace, all data in Dgraph, proper linking to existing nodes!

---

## 🎯 Workflow Example

### Step 1: Upload New Judgments to Elasticsearch

```bash
# Edit your Excel file with new judgments
# Then upload to Elasticsearch
python3 elasticsearch_upload.py
```

Output:
```
✅ Found 5 new documents (not already in ES)
✅ Successfully uploaded 5 documents to Elasticsearch
```

### Step 2: Process New Documents to Dgraph

**Option A: Manual Processing**

```bash
python3 -c "
from incremental_processor import IncrementalRDFProcessor
processor = IncrementalRDFProcessor()
result = processor.process_incremental()
print(result)
"
```

**Option B: Using FastAPI**

```bash
# Start the API server (in one terminal)
python3 fastapi_app.py

# Process new documents (in another terminal)
curl -X POST "http://localhost:8003/process"
```

**Option C: Automatic Background Processing**

The FastAPI server automatically checks for new documents every 60 seconds (configurable in `.env`).

```bash
# Just start the server and it runs automatically
python3 fastapi_app.py
```

### Step 3: What Happens

```
📖 Loading unprocessed documents from Elasticsearch...
✅ Found 5 documents to process

🔄 First pass: Collecting judgment data...
✅ Collected 5 judgments

🔄 Second pass: Processing relationships...
✓ Processing judgment 1: ABC Corp v. XYZ Ltd.
✓ Processing judgment 2: DEF Inc v. GHI Ltd.
...

💾 Writing RDF file: judgments.rdf
✅ RDF file written successfully (150 triples)

🚀 Starting Dgraph Live Loader upload...
   🔗 Upsert predicates enabled (will link to existing nodes)
✅ Data loaded successfully into Dgraph!
   ℹ️  New documents are now linked to existing nodes

📝 Marking documents as processed in Elasticsearch...
✅ Marked 5 documents as processed

🗑️  RDF file backed up to: judgments_backup_20251106_143000.rdf
✅ Workspace cleaned - RDF file removed
   ℹ️  Data is safely stored in Dgraph
```

---

## 📊 Query Your Data in Dgraph

After processing, query the graph:

### Find All Cases by a Judge

```graphql
{
  judge(func: eq(name, "Justice D. Y. Chandrachud")) {
    uid
    name
    
    # All cases judged (old + new)
    ~judged_by {
      title
      year
      processed_timestamp
    }
  }
}
```

### Find Recent Judgments

```graphql
{
  recentJudgments(func: type(Judgment), orderdesc: processed_timestamp, first: 10) {
    title
    year
    processed_timestamp
    
    judged_by { name }
    has_outcome { name }
  }
}
```

---

## 🔧 Configuration

Edit `.env` file:

```bash
# Auto-processing interval (seconds)
AUTO_PROCESS_INTERVAL=60  # Check every 60 seconds

# RDF output file (temporary, gets cleaned up)
RDF_OUTPUT_FILE=judgments.rdf

# Elasticsearch settings
ELASTICSEARCH_HOST=http://localhost:9200
ELASTICSEARCH_INDEX=graphdb

# Dgraph settings
DGRAPH_HOST=dgraph-standalone:9080
```

---

## 💡 Key Features

### 1. **Automatic Entity Linking**

When you add a new judgment with "Justice D. Y. Chandrachud":
- If this judge already exists in Dgraph → **Links to existing node**
- If this is a new judge → **Creates new node**

**No duplicates!** The `--upsertPredicate` in Dgraph ensures this.

### 2. **Clean Workspace**

After each upload:
- RDF file is backed up with timestamp
- Original RDF file is deleted
- Workspace stays clean

**Example backups:**
```
judgments_backup_20251106_143000.rdf
judgments_backup_20251106_150030.rdf
judgments_backup_20251106_153045.rdf
```

### 3. **Incremental Only**

Only processes documents where `processed_to_dgraph: false`

Check status:
```bash
curl http://localhost:8003/documents/count
```

Response:
```json
{
  "total": 150,
  "processed": 145,
  "unprocessed": 5
}
```

---

## 🛠️ Common Tasks

### Check Unprocessed Documents

```python
from elasticsearch_handler import ElasticsearchHandler

es = ElasticsearchHandler()
unprocessed = es.get_unprocessed_documents(limit=10)

for doc in unprocessed:
    print(f"{doc['doc_id']}: {doc['title']}")
```

### Force Reprocess Specific Documents

```python
from incremental_processor import IncrementalRDFProcessor

processor = IncrementalRDFProcessor()
result = processor.process_incremental(
    doc_ids=['doc_2025_001', 'doc_2025_002'],
    force_reprocess=True
)
```

### Keep RDF File (Don't Delete)

```python
processor = IncrementalRDFProcessor()
result = processor.process_incremental(
    cleanup_rdf=False  # Keep the RDF file
)
```

---

## ❓ FAQ

**Q: What if Dgraph is down during processing?**
A: The RDF file won't be deleted. You can manually upload it later:
```bash
docker run --rm --network dgraph-net \
  -v $(pwd):/data dgraph/dgraph:v23.1.0 \
  dgraph live --files /data/judgments.rdf \
  --schema /data/rdf.schema \
  --alpha dgraph-standalone:9080 \
  --zero dgraph-standalone:5080 \
  --upsertPredicate judgment_id \
  --upsertPredicate doc_id \
  --upsertPredicate judge_id \
  --upsertPredicate advocate_id \
  --upsertPredicate outcome_id \
  --upsertPredicate case_duration_id
```

**Q: Can I restore from a backup RDF file?**
A: Yes, just rename it back:
```bash
mv judgments_backup_20251106_143000.rdf judgments.rdf
# Then upload manually
```

**Q: How do I see processing history?**
A: Check the timestamps in Dgraph:
```graphql
{
  recentlyAdded(func: type(Judgment), orderdesc: processed_timestamp, first: 20) {
    title
    processed_timestamp
  }
}
```

**Q: What if I want to rebuild everything from scratch?**
A: Reset all documents and reprocess:
```python
from elasticsearch_handler import ElasticsearchHandler
from incremental_processor import IncrementalRDFProcessor

# Reset all to unprocessed
es = ElasticsearchHandler()
es.reset_processed_status()

# Process all
processor = IncrementalRDFProcessor()
processor.process_incremental()
```

---

## 🎉 Summary

Your workflow is now:

1. **Add new judgments** to Excel → Upload to Elasticsearch
2. **Run processor** (manual, API, or automatic)
3. **Done!** New documents in Dgraph, properly linked, workspace clean

No manual RDF management needed! 🚀
