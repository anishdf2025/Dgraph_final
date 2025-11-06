# Incremental Processing Guide for Legal Judgment Knowledge Graph

## 📖 Overview

This guide explains how the system handles **incremental processing** of new legal judgments, ensuring that:
1. ✅ New documents are automatically detected
2. ✅ RDF is generated only for new documents
3. ✅ New documents link to existing entities (judges, advocates, outcomes)
4. ✅ No duplicate nodes are created in Dgraph

---

## 🔄 How Incremental Processing Works

### Step 1: Document Upload to Elasticsearch

When new judgments are uploaded to Elasticsearch (via `elasticsearch_upload.py`):

```python
# Upload new documents to Elasticsearch
python3 elasticsearch_upload.py
```

Each document gets:
- A unique `doc_id` field
- A `processed_to_dgraph: false` flag (initially unprocessed)
- All judgment metadata (title, year, judges, advocates, citations, etc.)

---

### Step 2: Automatic Detection of New Documents

The **IncrementalRDFProcessor** automatically detects unprocessed documents:

```python
# Only fetches documents where processed_to_dgraph == false
df = es_handler.load_unprocessed_documents()
```

**Query used internally:**
```json
{
  "query": {
    "bool": {
      "must_not": {
        "term": {"processed_to_dgraph": true}
      }
    }
  }
}
```

---

### Step 3: RDF Generation with Entity Linking

When generating RDF for new documents, the system:

#### A. Creates Stable Node IDs
```python
# Uses doc_id hash to create stable judgment node IDs
judgment_node = create_node_id('judgment', unique_key=doc_id)
# Example: <j_8d50e3ef>
```

#### B. Links to Existing Entities Using Upsert

**For Judges:**
```python
# If judge "Justice D. Y. Chandrachud" exists in Dgraph, link to it
# If not, create new judge node
judge_node = create_node_id('judge', unique_key=judge_name_hash)
```

**Example RDF:**
```rdf
<judge_abc123> <dgraph.type> "Judge" .
<judge_abc123> <judge_id> "judge_abc123" .
<judge_abc123> <name> "Justice D. Y. Chandrachud" .

# New judgment links to existing judge
<j_8d50e3ef> <judged_by> <judge_abc123> .
```

**For Advocates, Outcomes, and Case Durations:**
- Same upsert logic applies
- If entity exists (matched by `advocate_id`, `outcome_id`, etc.), link to it
- If not, create new entity node

#### C. Citation Cross-References

The system checks if cited judgments already exist:

```python
# Check if citation title matches existing judgment
if citation_title.lower() in self.title_to_judgment_map:
    # Link to existing judgment
    existing_judgment_node = self.title_to_judgment_map[citation_title]
    <j_new> <cites> <existing_judgment> .
else:
    # Create citation node (external reference)
    <j_new> <cites> <c_external> .
```

---

### Step 4: Append-Mode RDF Writing

Instead of overwriting, new RDF triples are **appended** to the existing file:

```python
# Open in append mode
with open("judgments.rdf", "a", encoding="utf-8") as f:
    f.write(f"\n# === Incremental update: {datetime.now().isoformat()} ===\n")
    for triple in new_triples:
        f.write(triple + "\n")
```

**RDF File Structure:**
```rdf
# Initial upload
<j_1> <judgment_id> "j_1" .
<judge1> <name> "Justice A. B. Smith" .
<j_1> <judged_by> <judge1> .

# === Incremental update: 2025-11-06T10:30:00 ===
<j_2> <judgment_id> "j_2" .
# Links to existing judge (no duplicate created)
<j_2> <judged_by> <judge1> .
```

---

### Step 5: Upsert Upload to Dgraph

The Dgraph Live Loader uses **upsert predicates** to avoid duplicates:

```bash
docker run --rm \
  --network dgraph-net \
  -v $(pwd):/data \
  dgraph/dgraph:v23.1.0 \
  dgraph live \
  --files /data/judgments.rdf \
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

**What this does:**
- If a node with `judge_id="judge_abc123"` already exists, **reuse it**
- If a node with `judgment_id="j_8d50e3ef"` already exists, **update it**
- New relationships are added without creating duplicate nodes

---

### Step 6: Mark Documents as Processed

After successful upload to Dgraph:

```python
# Update Elasticsearch to mark documents as processed
es_handler.mark_documents_as_processed(doc_ids)
```

**Elasticsearch Update:**
```json
{
  "doc": {
    "processed_to_dgraph": true,
    "processed_timestamp": "2025-11-06T10:30:00"
  }
}
```

---

## 🎯 Real-World Example

### Scenario: Adding a New Judgment

**Initial State:**
- Dgraph has 100 judgments
- Judge "Justice D. Y. Chandrachud" already exists in Dgraph
- 5 advocates already exist

**New Document Uploaded to Elasticsearch:**
```json
{
  "doc_id": "doc_2025_001",
  "title": "ABC Corp v. XYZ Ltd.",
  "year": 2025,
  "judges": ["Justice D. Y. Chandrachud", "Justice B. V. Nagarathna"],
  "petitioner_advocates": ["Mr. Harish Salve"],
  "respondant_advocates": ["Ms. Indira Jaising"],
  "outcome": "Petitioner Won",
  "case_duration": "2024-01-15 to 2025-02-20",
  "citations": ["Previous Case A", "Previous Case B"],
  "processed_to_dgraph": false
}
```

**What Happens:**

1. **RDF Generation:**
```rdf
# === Incremental update: 2025-11-06T10:30:00 ===

# New judgment node
<j_a1b2c3d4> <judgment_id> "j_a1b2c3d4" .
<j_a1b2c3d4> <title> "ABC Corp v. XYZ Ltd." .
<j_a1b2c3d4> <doc_id> "doc_2025_001" .
<j_a1b2c3d4> <year> "2025" .
<j_a1b2c3d4> <processed_timestamp> "2025-11-06T10:30:00" .
<j_a1b2c3d4> <dgraph.type> "Judgment" .

# Judge 1 (EXISTING - will be linked via upsert)
<judge_dychandrachud> <judge_id> "judge_dychandrachud" .
<judge_dychandrachud> <name> "Justice D. Y. Chandrachud" .

# Judge 2 (NEW - will be created)
<judge_bvnagarathna> <judge_id> "judge_bvnagarathna" .
<judge_bvnagarathna> <name> "Justice B. V. Nagarathna" .
<judge_bvnagarathna> <dgraph.type> "Judge" .

# Link judgment to judges
<j_a1b2c3d4> <judged_by> <judge_dychandrachud> .
<j_a1b2c3d4> <judged_by> <judge_bvnagarathna> .

# Advocates (existing advocate will be reused)
<petitioner_advocate_hsalve> <advocate_id> "petitioner_advocate_hsalve" .
<petitioner_advocate_hsalve> <name> "Mr. Harish Salve" .
<j_a1b2c3d4> <petitioner_represented_by> <petitioner_advocate_hsalve> .

<respondant_advocate_ijaising> <advocate_id> "respondant_advocate_ijaising" .
<respondant_advocate_ijaising> <name> "Ms. Indira Jaising" .
<j_a1b2c3d4> <respondant_represented_by> <respondant_advocate_ijaising> .

# Outcome (existing outcome will be reused)
<outcome_petitioner_won> <outcome_id> "outcome_petitioner_won" .
<outcome_petitioner_won> <name> "Petitioner Won" .
<j_a1b2c3d4> <has_outcome> <outcome_petitioner_won> .

# Citations (link if exists, else create citation node)
<c1> <title> "Previous Case A" .
<j_a1b2c3d4> <cites> <c1> .
```

2. **Dgraph Upsert:**
- `judge_dychandrachud` already exists → **reuse existing node**
- `judge_bvnagarathna` doesn't exist → **create new node**
- `petitioner_advocate_hsalve` exists → **reuse existing node**
- `outcome_petitioner_won` exists → **reuse existing node**

3. **Final Result in Dgraph:**
- 1 new judgment node created
- 1 new judge node created
- 2 links to existing judges
- 2 links to existing advocates
- 1 link to existing outcome
- **No duplicate nodes**

---

## 🔍 Querying After Incremental Update

### Query 1: Find All Cases Judged by Justice D. Y. Chandrachud

```graphql
{
  judge(func: eq(name, "Justice D. Y. Chandrachud")) {
    uid
    name
    
    ~judged_by {
      title
      year
      processed_timestamp
    }
  }
}
```

**Result:** Returns both **old judgments** and the **new judgment** (ABC Corp v. XYZ Ltd.)

### Query 2: Find Recently Processed Judgments

```graphql
{
  recentJudgments(func: type(Judgment), orderdesc: processed_timestamp, first: 10) {
    title
    year
    processed_timestamp
    
    judged_by {
      name
    }
  }
}
```

**Result:** Shows the 10 most recently added judgments with timestamps

---

## 📊 Monitoring Incremental Processing

### Check Processing Status

```python
from elasticsearch_handler import ElasticsearchHandler

es = ElasticsearchHandler()
counts = es.get_processing_counts()

print(f"Total documents: {counts['total']}")
print(f"Processed: {counts['processed']}")
print(f"Unprocessed: {counts['unprocessed']}")
```

### View Unprocessed Documents

```python
unprocessed = es.get_unprocessed_documents(limit=10)
for doc in unprocessed:
    print(f"{doc['doc_id']}: {doc['title']}")
```

---

## 🚀 Usage Examples

### Example 1: Manual Incremental Processing

```bash
# Process all unprocessed documents
python3 -c "
from incremental_processor import IncrementalRDFProcessor
processor = IncrementalRDFProcessor()
result = processor.process_incremental(
    append_mode=True,      # Append to existing RDF file
    auto_upload=True       # Upload to Dgraph and mark as processed
)
print(result)
"
```

### Example 2: Process Specific Documents

```bash
# Process only specific doc_ids
python3 -c "
from incremental_processor import IncrementalRDFProcessor
processor = IncrementalRDFProcessor()
result = processor.process_incremental(
    doc_ids=['doc_2025_001', 'doc_2025_002'],
    append_mode=True,
    auto_upload=True
)
print(result)
"
```

### Example 3: Using FastAPI

```bash
# Start FastAPI server
python3 fastapi_app.py

# Then use the API
curl -X POST "http://localhost:8003/process" \
  -H "Content-Type: application/json" \
  -d '{"force_reprocess": false}'

# Check status
curl "http://localhost:8003/status"

# Get unprocessed count
curl "http://localhost:8003/documents/count"
```

### Example 4: Automatic Background Processing

The auto-processor runs in the background and checks for new documents every N seconds:

```python
# Configured in .env
AUTO_PROCESS_INTERVAL=60  # Check every 60 seconds

# Starts automatically when FastAPI app runs
python3 fastapi_app.py
```

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
# Elasticsearch
ELASTICSEARCH_HOST=http://localhost:9200
ELASTICSEARCH_INDEX=graphdb

# Dgraph
DGRAPH_HOST=dgraph-standalone:9080
DGRAPH_ZERO=dgraph-standalone:5080

# Auto-processing interval (seconds)
AUTO_PROCESS_INTERVAL=60

# RDF file output
RDF_OUTPUT_FILE=judgments.rdf
RDF_SCHEMA_FILE=rdf.schema
```

---

## 🛠️ Troubleshooting

### Issue 1: Duplicate Nodes Being Created

**Cause:** Upsert predicates not properly configured

**Solution:**
1. Check `rdf.schema` has `@upsert` on unique fields
2. Verify Dgraph Live Loader uses `--upsertPredicate` flags
3. Ensure consistent node ID generation

### Issue 2: New Documents Not Linking to Existing Entities

**Cause:** Node IDs not matching

**Solution:**
- Use stable node ID generation based on entity names
- Verify `create_node_id()` uses `unique_key` parameter

```python
# Good: Stable ID based on name
judge_node = create_node_id('judge', unique_key=judge_name)

# Bad: Counter-based (not stable across runs)
judge_node = create_node_id('judge', counter=1)
```

### Issue 3: RDF File Growing Too Large

**Solution:** Periodically archive old RDF content

```bash
# Archive old RDF file
mv judgments.rdf judgments_archive_$(date +%Y%m%d).rdf

# Start fresh (next upload will create new file)
# Dgraph already has all the data, so this is safe
```

---

## 📈 Best Practices

1. **Always use append mode** for incremental updates:
   ```python
   processor.process_incremental(append_mode=True)
   ```

2. **Monitor unprocessed documents**:
   ```python
   counts = es_handler.get_processing_counts()
   ```

3. **Use background auto-processor** for continuous updates:
   - Set reasonable `AUTO_PROCESS_INTERVAL` (e.g., 60-300 seconds)
   - Monitor logs for errors

4. **Test with small batches** before bulk processing:
   ```python
   # Process just 5 documents first
   processor.process_incremental(doc_ids=doc_ids[:5])
   ```

5. **Backup Dgraph regularly**:
   ```bash
   # Export Dgraph data
   curl localhost:8180/admin/export
   ```

---

## 🎯 Summary

The incremental processing system ensures:
- ✅ **Efficiency**: Only new documents are processed
- ✅ **No Duplicates**: Upsert logic prevents duplicate nodes
- ✅ **Proper Linking**: New documents link to existing entities
- ✅ **Traceability**: Timestamps track when documents were processed
- ✅ **Automation**: Background processor handles new documents automatically

This approach allows the knowledge graph to grow continuously without manual intervention while maintaining data integrity and relationship consistency.
