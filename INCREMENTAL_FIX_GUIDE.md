# 🔧 Incremental Processing Fix - No Data Loss!

## 🎯 Problem Solved

**Before:** When new documents came, the system would:
- ❌ Create new RDF file from scratch
- ❌ Generate new node IDs (j1, j2, j3...)
- ❌ Replace old data in Dgraph
- ❌ Lose previously processed documents

**After:** Now the system:
- ✅ Uses stable, unique IDs based on `doc_id`
- ✅ Only processes NEW documents
- ✅ Properly upserts to Dgraph (updates existing, adds new)
- ✅ Preserves all previously processed data

## 🔑 Key Changes Made

### 1. **Stable Node IDs**
Instead of sequential IDs (j1, j2, j3...), we now use:
```
j_8f3a7b2c  (hash of doc_id)
```

This ensures:
- Same document = Same node ID always
- No conflicts when processing incrementally
- Proper upsert behavior in Dgraph

### 2. **Multiple Upsert Predicates**
The upload now uses multiple upsert predicates:
```bash
--upsertPredicate doc_id
--upsertPredicate judge_id
--upsertPredicate advocate_id
--upsertPredicate outcome_id
--upsertPredicate case_duration_id
```

This ensures:
- Documents are matched by `doc_id`
- Judges, advocates, outcomes are reused if they already exist
- No duplicate nodes in Dgraph

### 3. **Updated Schema**
All ID fields now have `@upsert` directive:
```
judgment_id: string @index(exact) @upsert .
doc_id: string @index(exact) @upsert .
judge_id: string @index(exact) @upsert .
advocate_id: string @index(exact) @upsert .
outcome_id: string @index(exact) @upsert .
case_duration_id: string @index(exact) @upsert .
```

## 🚀 How It Works Now

### Scenario 1: First Run (No existing data)
```
Elasticsearch: 100 documents
Dgraph: Empty

→ Process: All 100 documents
→ Result: 100 documents in Dgraph
```

### Scenario 2: New Documents Added
```
Elasticsearch: 100 old + 25 new = 125 total
Dgraph: 100 documents (from first run)

→ Process: Only 25 new documents
→ Result: 125 documents in Dgraph (100 old + 25 new)
→ Old data: PRESERVED ✅
```

### Scenario 3: Document Updated in Elasticsearch
```
Elasticsearch: Document X updated
Dgraph: Old version of Document X

→ Process: Document X (detected as unprocessed after reset)
→ Result: Document X UPDATED in Dgraph (upserted)
→ Other documents: UNCHANGED ✅
```

## 📊 Example Flow

### Step 1: Initial Data
```bash
# Start FastAPI
uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload

# Auto processor runs every 60 seconds
# Finds 3 documents in Elasticsearch
# Processes them with IDs:
#   j_a1b2c3d4 (doc_id: "ABC123")
#   j_e5f6g7h8 (doc_id: "DEF456")
#   j_i9j0k1l2 (doc_id: "GHI789")
```

### Step 2: New Documents Added
```bash
# New document added to Elasticsearch (doc_id: "JKL012")
# Auto processor detects it in next check (60 seconds)
# Processes with ID: j_m3n4o5p6
# 
# Dgraph now has:
#   j_a1b2c3d4 (ABC123) ← OLD, preserved
#   j_e5f6g7h8 (DEF456) ← OLD, preserved
#   j_i9j0k1l2 (GHI789) ← OLD, preserved
#   j_m3n4o5p6 (JKL012) ← NEW, added
```

### Step 3: More New Documents
```bash
# 2 more documents added (doc_ids: "MNO345", "PQR678")
# Auto processor detects and processes
#
# Dgraph now has:
#   j_a1b2c3d4 (ABC123) ← OLD
#   j_e5f6g7h8 (DEF456) ← OLD
#   j_i9j0k1l2 (GHI789) ← OLD
#   j_m3n4o5p6 (JKL012) ← OLD
#   j_s7t8u9v0 (MNO345) ← NEW
#   j_w1x2y3z4 (PQR678) ← NEW
```

## ✅ Verification

### Check that old data is preserved:
```bash
# Count documents before adding new ones
curl http://localhost:8003/stats

# Add new documents to Elasticsearch
# ... (your upload process)

# Wait for auto-processing (60 seconds)

# Check stats again - total should increase, not replace
curl http://localhost:8003/stats
```

### Query Dgraph to verify:
```graphql
{
  countJudgments(func: type(Judgment)) {
    total: count(uid)
  }
}
```

The count should **increase** with each new batch, not stay the same!

## 🎯 Key Benefits

1. **No Data Loss**: Old documents remain in Dgraph
2. **Efficient Processing**: Only processes new documents
3. **Automatic Deduplication**: Same judge/advocate/outcome reused
4. **Stable References**: Citations work correctly across batches
5. **True Incremental**: Can run indefinitely, adding data over time

## 🔄 Workflow Summary

```
┌─────────────────────────────────────────┐
│  New Document Added to Elasticsearch   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Auto Processor Detects (every 60s)    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Generate RDF with Unique Hash ID       │
│  (j_hash based on doc_id)               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Upload to Dgraph with Upsert           │
│  (updates if exists, adds if new)       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Mark Document as Processed             │
│  (won't be processed again)             │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Old Data: PRESERVED ✅                 │
│  New Data: ADDED ✅                     │
└─────────────────────────────────────────┘
```

## 🧪 Testing the Fix

1. **Start fresh (optional):**
```bash
# Reset all processed flags
curl -X POST http://localhost:8003/documents/reset-processed
```

2. **Process initial batch:**
```bash
# Will process all documents
# Note the count
curl http://localhost:8003/stats
```

3. **Add new documents to Elasticsearch:**
```bash
# Use your elasticsearch_upload.py or similar
python3 elasticsearch_upload.py
```

4. **Wait 60 seconds** (or check interval you configured)

5. **Verify increment:**
```bash
# Count should have INCREASED, not replaced
curl http://localhost:8003/stats
```

## 📝 Important Notes

- **First Time:** If you've already processed documents with old sequential IDs (j1, j2...), you may want to clear Dgraph and start fresh for consistency
- **Hash Stability:** The hash is based on `doc_id`, so same document always gets same node ID
- **Upsert Behavior:** If a document is updated in Elasticsearch, reset its processed flag to reprocess with same node ID (updates in Dgraph)

## 🎉 Result

**Your system now works like a true incremental database!**

- Add new documents anytime
- They'll be automatically detected and processed
- Old data is never lost
- System can run indefinitely
- No manual intervention needed

Perfect for continuous data ingestion! 🚀
