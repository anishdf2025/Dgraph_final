# 🎯 Practical Example: Step-by-Step Walkthrough

**Real-world scenario demonstrating duplicate prevention across multiple batches**

---

## 📋 Scenario Overview

We'll upload legal judgments in 3 batches over time and observe how the system prevents duplicates.

### Dataset

**Batch 1 (January)**: 3 initial judgments
**Batch 2 (March)**: 2 new judgments with overlapping entities  
**Batch 3 (June)**: 1 judgment with citations to previous cases

---

## 📊 Batch 1: Initial Upload (January)

### Input Data (Excel)

```
┌──────────────────────────────────────────────────────────────────┐
│ DOC_ID │ TITLE              │ JUDGE                  │ YEAR    │
├────────┼────────────────────┼────────────────────────┼─────────┤
│ DOC001 │ Case Alpha         │ Justice D. Y. Chandra  │ 2020    │
│ DOC002 │ Case Beta          │ Justice Hemant Gupta   │ 2021    │
│ DOC003 │ Case Gamma         │ Justice D. Y. Chandra  │ 2022    │
└──────────────────────────────────────────────────────────────────┘
```

### Step 1: Upload to Elasticsearch

```bash
python3 elasticsearch_upload.py
```

**Elasticsearch State**:
```json
[
  {
    "doc_id": "DOC001",
    "title": "Case Alpha",
    "judges": ["Justice D. Y. Chandra"],
    "year": 2020,
    "processed_to_dgraph": false
  },
  {
    "doc_id": "DOC002",
    "title": "Case Beta",
    "judges": ["Justice Hemant Gupta"],
    "year": 2021,
    "processed_to_dgraph": false
  },
  {
    "doc_id": "DOC003",
    "title": "Case Gamma",
    "judges": ["Justice D. Y. Chandra"],
    "year": 2022,
    "processed_to_dgraph": false
  }
]
```

### Step 2: Process Documents (ES → RDF → Dgraph)

```bash
curl -X POST http://localhost:8003/process
```

### Behind the Scenes

#### A. Load Unprocessed Documents
```python
# elasticsearch_handler.py
df = es_handler.load_unprocessed_documents()
# Result: 3 documents loaded
```

#### B. First Pass - Collect Judgment Data
```python
# incremental_processor.py - _collect_judgment_data()

# Document 1: Case Alpha
title_1 = "Case Alpha"
judgment_node_1 = create_node_id('judgment', unique_key="Case Alpha")
# Hash calculation:
#   normalize: "case alpha"
#   MD5: "case alpha" → "a1b2c3d4..."
#   truncate: "a1b2c3d4"
#   format: "j_a1b2c3d4"

title_to_judgment_map["case alpha"] = "j_a1b2c3d4"

# Document 2: Case Beta
title_2 = "Case Beta"
judgment_node_2 = create_node_id('judgment', unique_key="Case Beta")
# Result: "j_e5f6g7h8"

title_to_judgment_map["case beta"] = "j_e5f6g7h8"

# Document 3: Case Gamma
title_3 = "Case Gamma"
judgment_node_3 = create_node_id('judgment', unique_key="Case Gamma")
# Result: "j_i9j0k1l2"

title_to_judgment_map["case gamma"] = "j_i9j0k1l2"

# Final title_to_judgment_map:
{
  "case alpha": "j_a1b2c3d4",
  "case beta": "j_e5f6g7h8",
  "case gamma": "j_i9j0k1l2"
}
```

#### C. Second Pass - Process Judge Relationships
```python
# judge_relationship.py - create_judge_relationships()

# Processing Case Alpha
judge_name = "Justice D. Y. Chandra"
if judge_name not in judge_map:
    judge_node = create_node_id('judge', unique_key=judge_name)
    # Hash calculation:
    #   normalize: "justice d. y. chandra"
    #   MD5: "ea7adefd..."
    #   Result: "judge_ea7adefd"
    
    judge_map["Justice D. Y. Chandra"] = "judge_ea7adefd"
    
    # Create judge RDF triples
    rdf_lines.append('<judge_ea7adefd> <dgraph.type> "Judge" .')
    rdf_lines.append('<judge_ea7adefd> <judge_id> "judge_ea7adefd" .')
    rdf_lines.append('<judge_ea7adefd> <name> "Justice D. Y. Chandra" .')

# Create relationship
rdf_lines.append('<j_a1b2c3d4> <judged_by> <judge_ea7adefd> .')

# Processing Case Beta
judge_name = "Justice Hemant Gupta"
if judge_name not in judge_map:
    judge_node = create_node_id('judge', unique_key=judge_name)
    # Result: "judge_9c1212fb"
    
    judge_map["Justice Hemant Gupta"] = "judge_9c1212fb"
    
    # Create judge RDF triples
    rdf_lines.append('<judge_9c1212fb> <dgraph.type> "Judge" .')
    rdf_lines.append('<judge_9c1212fb> <judge_id> "judge_9c1212fb" .')
    rdf_lines.append('<judge_9c1212fb> <name> "Justice Hemant Gupta" .')

# Create relationship
rdf_lines.append('<j_e5f6g7h8> <judged_by> <judge_9c1212fb> .')

# Processing Case Gamma
judge_name = "Justice D. Y. Chandra"
if judge_name in judge_map:
    # FOUND IN MAP! Reuse existing node ID
    judge_node = judge_map["Justice D. Y. Chandra"]  # "judge_ea7adefd"
    
    # NO NEW JUDGE TRIPLES CREATED (already exists in this batch)

# Create relationship
rdf_lines.append('<j_i9j0k1l2> <judged_by> <judge_ea7adefd> .')

# Final judge_map:
{
  "Justice D. Y. Chandra": "judge_ea7adefd",
  "Justice Hemant Gupta": "judge_9c1212fb"
}
```

#### D. Generated RDF File (rdf/judgments.rdf)
```rdf
# Judgment Nodes
<j_a1b2c3d4> <dgraph.type> "Judgment" .
<j_a1b2c3d4> <judgment_id> "j_a1b2c3d4" .
<j_a1b2c3d4> <title> "Case Alpha" .
<j_a1b2c3d4> <doc_id> "DOC001" .
<j_a1b2c3d4> <year> "2020" .
<j_a1b2c3d4> <processed_timestamp> "2025-01-15T10:30:00" .

<j_e5f6g7h8> <dgraph.type> "Judgment" .
<j_e5f6g7h8> <judgment_id> "j_e5f6g7h8" .
<j_e5f6g7h8> <title> "Case Beta" .
<j_e5f6g7h8> <doc_id> "DOC002" .
<j_e5f6g7h8> <year> "2021" .
<j_e5f6g7h8> <processed_timestamp> "2025-01-15T10:30:01" .

<j_i9j0k1l2> <dgraph.type> "Judgment" .
<j_i9j0k1l2> <judgment_id> "j_i9j0k1l2" .
<j_i9j0k1l2> <title> "Case Gamma" .
<j_i9j0k1l2> <doc_id> "DOC003" .
<j_i9j0k1l2> <year> "2022" .
<j_i9j0k1l2> <processed_timestamp> "2025-01-15T10:30:02" .

# Judge Nodes (only 2 created for 3 judgments!)
<judge_ea7adefd> <dgraph.type> "Judge" .
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandra" .

<judge_9c1212fb> <dgraph.type> "Judge" .
<judge_9c1212fb> <judge_id> "judge_9c1212fb" .
<judge_9c1212fb> <name> "Justice Hemant Gupta" .

# Relationships
<j_a1b2c3d4> <judged_by> <judge_ea7adefd> .
<j_e5f6g7h8> <judged_by> <judge_9c1212fb> .
<j_i9j0k1l2> <judged_by> <judge_ea7adefd> .
```

**Key Observation**: Only 2 judge nodes created despite 3 judgments!

#### E. Upload to Dgraph
```bash
docker run --rm \
  --network dgraph-net \
  -v $(pwd):/data \
  dgraph/dgraph:v23.1.0 \
  dgraph live \
  --files /data/rdf/judgments.rdf \
  --schema /data/rdf.schema \
  --alpha dgraph-standalone:9080 \
  --zero dgraph-standalone:5080 \
  --upsertPredicate judgment_id \
  --upsertPredicate judge_id
```

#### F. Mark Documents as Processed
```python
# elasticsearch_handler.py
es_handler.mark_documents_as_processed(["DOC001", "DOC002", "DOC003"])
```

**Elasticsearch State After Processing**:
```json
[
  {
    "doc_id": "DOC001",
    "processed_to_dgraph": true  // ← Changed!
  },
  {
    "doc_id": "DOC002",
    "processed_to_dgraph": true  // ← Changed!
  },
  {
    "doc_id": "DOC003",
    "processed_to_dgraph": true  // ← Changed!
  }
]
```

### Dgraph State After Batch 1

**Query to verify**:
```graphql
{
  allJudgments(func: type(Judgment)) {
    uid
    title
    judgment_id
    judged_by {
      name
      judge_id
    }
  }
  
  allJudges(func: type(Judge)) {
    uid
    name
    judge_id
    count_cases: count(~judged_by)
  }
}
```

**Result**:
```json
{
  "data": {
    "allJudgments": [
      {
        "uid": "0x1001",
        "title": "Case Alpha",
        "judgment_id": "j_a1b2c3d4",
        "judged_by": [
          {
            "name": "Justice D. Y. Chandra",
            "judge_id": "judge_ea7adefd"
          }
        ]
      },
      {
        "uid": "0x1002",
        "title": "Case Beta",
        "judgment_id": "j_e5f6g7h8",
        "judged_by": [
          {
            "name": "Justice Hemant Gupta",
            "judge_id": "judge_9c1212fb"
          }
        ]
      },
      {
        "uid": "0x1003",
        "title": "Case Gamma",
        "judgment_id": "j_i9j0k1l2",
        "judged_by": [
          {
            "name": "Justice D. Y. Chandra",
            "judge_id": "judge_ea7adefd"
          }
        ]
      }
    ],
    "allJudges": [
      {
        "uid": "0x2001",
        "name": "Justice D. Y. Chandra",
        "judge_id": "judge_ea7adefd",
        "count_cases": 2  // ← Judged 2 cases
      },
      {
        "uid": "0x2002",
        "name": "Justice Hemant Gupta",
        "judge_id": "judge_9c1212fb",
        "count_cases": 1  // ← Judged 1 case
      }
    ]
  }
}
```

**Summary**:
- ✅ 3 judgment nodes created
- ✅ 2 judge nodes created (NOT 3!)
- ✅ 3 relationships established
- ✅ No duplicates within batch

---

## 📊 Batch 2: Incremental Upload (March)

**Time elapsed**: 2 months

### Input Data (Excel)

```
┌──────────────────────────────────────────────────────────────────┐
│ DOC_ID │ TITLE              │ JUDGE                  │ YEAR    │
├────────┼────────────────────┼────────────────────────┼─────────┤
│ DOC004 │ Case Delta         │ Justice D. Y. Chandra  │ 2023    │
│ DOC005 │ Case Epsilon       │ Justice S. A. Nazeer   │ 2023    │
└──────────────────────────────────────────────────────────────────┘
```

**Note**: "Justice D. Y. Chandra" also appeared in Batch 1!

### Step 1: Upload to Elasticsearch

```bash
python3 elasticsearch_upload.py
```

**New Elasticsearch Documents**:
```json
[
  {
    "doc_id": "DOC004",
    "title": "Case Delta",
    "judges": ["Justice D. Y. Chandra"],
    "year": 2023,
    "processed_to_dgraph": false  // ← New document
  },
  {
    "doc_id": "DOC005",
    "title": "Case Epsilon",
    "judges": ["Justice S. A. Nazeer"],
    "year": 2023,
    "processed_to_dgraph": false  // ← New document
  }
]
```

### Step 2: Process Documents

```bash
curl -X POST http://localhost:8003/process
```

### Behind the Scenes

#### A. Load Unprocessed Documents
```python
# Only loads DOC004 and DOC005 (processed_to_dgraph == false)
df = es_handler.load_unprocessed_documents()
# Result: 2 documents loaded
```

#### B. First Pass - NEW Hash Maps Created
```python
# NEW title_to_judgment_map (Batch 2 scope - independent!)
title_to_judgment_map = {}

# Document 1: Case Delta
judgment_node_1 = create_node_id('judgment', unique_key="Case Delta")
# Result: "j_m3n4o5p6"

title_to_judgment_map["case delta"] = "j_m3n4o5p6"

# Document 2: Case Epsilon
judgment_node_2 = create_node_id('judgment', unique_key="Case Epsilon")
# Result: "j_q7r8s9t0"

title_to_judgment_map["case epsilon"] = "j_q7r8s9t0"

# Final title_to_judgment_map (Batch 2):
{
  "case delta": "j_m3n4o5p6",
  "case epsilon": "j_q7r8s9t0"
}
# Note: Does NOT include Batch 1 judgments!
```

#### C. Second Pass - NEW Judge Map Created
```python
# NEW judge_map (Batch 2 scope - independent!)
judge_map = {}

# Processing Case Delta
judge_name = "Justice D. Y. Chandra"  # SAME as Batch 1!
if judge_name not in judge_map:
    judge_node = create_node_id('judge', unique_key=judge_name)
    # Hash calculation (SAME algorithm):
    #   normalize: "justice d. y. chandra"
    #   MD5: "ea7adefd..."
    #   Result: "judge_ea7adefd"  ← SAME ID as Batch 1!
    
    judge_map["Justice D. Y. Chandra"] = "judge_ea7adefd"
    
    # Create judge RDF triples (will be duplicate in RDF file)
    rdf_lines.append('<judge_ea7adefd> <dgraph.type> "Judge" .')
    rdf_lines.append('<judge_ea7adefd> <judge_id> "judge_ea7adefd" .')
    rdf_lines.append('<judge_ea7adefd> <name> "Justice D. Y. Chandra" .')

# Create relationship
rdf_lines.append('<j_m3n4o5p6> <judged_by> <judge_ea7adefd> .')

# Processing Case Epsilon
judge_name = "Justice S. A. Nazeer"  # NEW judge
if judge_name not in judge_map:
    judge_node = create_node_id('judge', unique_key=judge_name)
    # Result: "judge_4f5e6d7c"
    
    judge_map["Justice S. A. Nazeer"] = "judge_4f5e6d7c"
    
    # Create judge RDF triples
    rdf_lines.append('<judge_4f5e6d7c> <dgraph.type> "Judge" .')
    rdf_lines.append('<judge_4f5e6d7c> <judge_id> "judge_4f5e6d7c" .')
    rdf_lines.append('<judge_4f5e6d7c> <name> "Justice S. A. Nazeer" .')

# Create relationship
rdf_lines.append('<j_q7r8s9t0> <judged_by> <judge_4f5e6d7c> .')

# Final judge_map (Batch 2):
{
  "Justice D. Y. Chandra": "judge_ea7adefd",  # ← SAME ID as Batch 1!
  "Justice S. A. Nazeer": "judge_4f5e6d7c"    # ← NEW
}
```

#### D. Generated RDF File (FRESH FILE - Batch 2 only)
```rdf
# Judgment Nodes (Batch 2 only)
<j_m3n4o5p6> <dgraph.type> "Judgment" .
<j_m3n4o5p6> <judgment_id> "j_m3n4o5p6" .
<j_m3n4o5p6> <title> "Case Delta" .
<j_m3n4o5p6> <doc_id> "DOC004" .
<j_m3n4o5p6> <year> "2023" .
<j_m3n4o5p6> <processed_timestamp> "2025-03-20T14:15:00" .

<j_q7r8s9t0> <dgraph.type> "Judgment" .
<j_q7r8s9t0> <judgment_id> "j_q7r8s9t0" .
<j_q7r8s9t0> <title> "Case Epsilon" .
<j_q7r8s9t0> <doc_id> "DOC005" .
<j_q7r8s9t0> <year> "2023" .
<j_q7r8s9t0> <processed_timestamp> "2025-03-20T14:15:01" .

# Judge Nodes
<judge_ea7adefd> <dgraph.type> "Judge" .  # ← DUPLICATE triple from Batch 1!
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandra" .

<judge_4f5e6d7c> <dgraph.type> "Judge" .  # ← NEW judge
<judge_4f5e6d7c> <judge_id> "judge_4f5e6d7c" .
<judge_4f5e6d7c> <name> "Justice S. A. Nazeer" .

# Relationships
<j_m3n4o5p6> <judged_by> <judge_ea7adefd> .
<j_q7r8s9t0> <judged_by> <judge_4f5e6d7c> .
```

**Critical Observation**: RDF contains duplicate `<judge_ea7adefd>` triples!

#### E. Upload to Dgraph (Upsert Magic!)
```bash
# Same command, fresh RDF file
docker run --rm \
  --network dgraph-net \
  -v $(pwd):/data \
  dgraph/dgraph:v23.1.0 \
  dgraph live \
  --files /data/rdf/judgments.rdf \
  --schema /data/rdf.schema \
  --alpha dgraph-standalone:9080 \
  --zero dgraph-standalone:5080 \
  --upsertPredicate judgment_id \
  --upsertPredicate judge_id  # ← CRITICAL!
```

**What Happens in Dgraph**:
```
1. Process: <judge_ea7adefd> <judge_id> "judge_ea7adefd"
   ├─ Check: Does a node with judge_id="judge_ea7adefd" exist?
   ├─ Result: YES! (from Batch 1, UID: 0x2001)
   └─ Action: MERGE with existing node (upsert)
   
2. Process: <judge_4f5e6d7c> <judge_id> "judge_4f5e6d7c"
   ├─ Check: Does a node with judge_id="judge_4f5e6d7c" exist?
   ├─ Result: NO
   └─ Action: CREATE new node (UID: 0x2003)

3. Process: <j_m3n4o5p6> <judged_by> <judge_ea7adefd>
   ├─ judge_ea7adefd resolves to UID: 0x2001 (existing!)
   └─ Create edge: 0x1004 → judged_by → 0x2001
```

### Dgraph State After Batch 2

**Query**:
```graphql
{
  allJudges(func: type(Judge)) {
    uid
    name
    judge_id
    count_cases: count(~judged_by)
    cases: ~judged_by {
      title
    }
  }
}
```

**Result**:
```json
{
  "data": {
    "allJudges": [
      {
        "uid": "0x2001",  // ← SAME UID as Batch 1!
        "name": "Justice D. Y. Chandra",
        "judge_id": "judge_ea7adefd",
        "count_cases": 3,  // ← Increased from 2 to 3!
        "cases": [
          {"title": "Case Alpha"},    // ← Batch 1
          {"title": "Case Gamma"},    // ← Batch 1
          {"title": "Case Delta"}     // ← Batch 2 (NEW!)
        ]
      },
      {
        "uid": "0x2002",
        "name": "Justice Hemant Gupta",
        "judge_id": "judge_9c1212fb",
        "count_cases": 1,
        "cases": [
          {"title": "Case Beta"}
        ]
      },
      {
        "uid": "0x2003",  // ← NEW JUDGE
        "name": "Justice S. A. Nazeer",
        "judge_id": "judge_4f5e6d7c",
        "count_cases": 1,
        "cases": [
          {"title": "Case Epsilon"}  // ← Batch 2
        ]
      }
    ]
  }
}
```

**Summary**:
- ✅ Judge "D. Y. Chandra" has SAME UID (0x2001) - NO DUPLICATE!
- ✅ New case "Delta" linked to existing judge
- ✅ New judge "S. A. Nazeer" created
- ✅ Total judges: 3 (not 4!)

---

## 📊 Batch 3: Citation Relationships (June)

**Time elapsed**: 3 months since Batch 2

### Input Data (Excel)

```
┌────────────────────────────────────────────────────────────────────────┐
│ DOC_ID │ TITLE           │ JUDGE               │ CITATIONS              │
├────────┼─────────────────┼─────────────────────┼────────────────────────┤
│ DOC006 │ Case Zeta       │ Justice H. Gupta    │ ["Case Alpha",         │
│        │                 │                     │  "Case Delta"]         │
└────────────────────────────────────────────────────────────────────────┘
```

**Note**: Cites cases from Batch 1 and Batch 2!

### Processing

```bash
python3 elasticsearch_upload.py
curl -X POST http://localhost:8003/process
```

### Behind the Scenes - Citation Processing

```python
# First Pass: Create judgment node
judgment_node = create_node_id('judgment', unique_key="Case Zeta")
# Result: "j_u1v2w3x4"

title_to_judgment_map["case zeta"] = "j_u1v2w3x4"

# Second Pass: Process citations
citations = ["Case Alpha", "Case Delta"]

for citation in citations:
    citation_lower = citation.lower()  # "case alpha", "case delta"
    
    # Check if citation matches existing judgment (internal reference)
    if citation_lower in title_to_judgment_map:
        # NOT FOUND in title_to_judgment_map (only has Batch 3 judgments)
        pass
    
    # Create citation node
    citation_node = create_node_id('judgment', unique_key=citation)
    # "Case Alpha" → "j_a1b2c3d4" (SAME as Batch 1!)
    # "Case Delta" → "j_m3n4o5p6" (SAME as Batch 2!)
    
    # Create relationship
    rdf_lines.append('<j_u1v2w3x4> <cites> <j_a1b2c3d4> .')
    rdf_lines.append('<j_u1v2w3x4> <cites> <j_m3n4o5p6> .')
```

### Generated RDF (Batch 3)

```rdf
# New Judgment
<j_u1v2w3x4> <dgraph.type> "Judgment" .
<j_u1v2w3x4> <judgment_id> "j_u1v2w3x4" .
<j_u1v2w3x4> <title> "Case Zeta" .
<j_u1v2w3x4> <doc_id> "DOC006" .

# Citation Nodes (duplicates from previous batches!)
<j_a1b2c3d4> <dgraph.type> "Judgment" .
<j_a1b2c3d4> <judgment_id> "j_a1b2c3d4" .
<j_a1b2c3d4> <title> "Case Alpha" .

<j_m3n4o5p6> <dgraph.type> "Judgment" .
<j_m3n4o5p6> <judgment_id> "j_m3n4o5p6" .
<j_m3n4o5p6> <title> "Case Delta" .

# Citation Relationships
<j_u1v2w3x4> <cites> <j_a1b2c3d4> .
<j_u1v2w3x4> <cites> <j_m3n4o5p6> .
```

### Dgraph After Upload (Upsert)

```
1. Process: <j_a1b2c3d4> (duplicate from Batch 1)
   ├─ judgment_id="j_a1b2c3d4" already exists
   └─ MERGE with existing node (no duplicate!)

2. Process: <j_m3n4o5p6> (duplicate from Batch 2)
   ├─ judgment_id="j_m3n4o5p6" already exists
   └─ MERGE with existing node (no duplicate!)

3. Process: <j_u1v2w3x4> <cites> <j_a1b2c3d4>
   ├─ Creates edge from Zeta → Alpha
   └─ Links NEW judgment to OLD judgment!
```

### Final Dgraph Query

```graphql
{
  zeta: judgment(func: eq(title, "Case Zeta")) {
    title
    judgment_id
    cites {
      title
      doc_id
      year
    }
  }
  
  alpha: judgment(func: eq(title, "Case Alpha")) {
    title
    judgment_id
    doc_id
    cited_by: ~cites {
      title
    }
  }
}
```

**Result**:
```json
{
  "data": {
    "zeta": [
      {
        "title": "Case Zeta",
        "judgment_id": "j_u1v2w3x4",
        "cites": [
          {
            "title": "Case Alpha",
            "doc_id": "DOC001",
            "year": 2020
          },
          {
            "title": "Case Delta",
            "doc_id": "DOC004",
            "year": 2023
          }
        ]
      }
    ],
    "alpha": [
      {
        "title": "Case Alpha",
        "judgment_id": "j_a1b2c3d4",
        "doc_id": "DOC001",
        "cited_by": [
          {
            "title": "Case Zeta"  // ← Successfully linked!
          }
        ]
      }
    ]
  }
}
```

---

## 📊 Final Statistics

### Across All 3 Batches

| Metric | Value |
|--------|-------|
| Total Documents Uploaded | 6 |
| Total Judgments Created | 6 |
| Total Unique Judges | 3 |
| Judge Appearances | 5 |
| Potential Duplicates (without hash system) | 2 |
| Actual Duplicates (with hash system) | 0 |
| Storage Savings | 40% for judges |

### Node Count Verification

```graphql
{
  judgment_count(func: type(Judgment)) {
    count(uid)
  }
  judge_count(func: type(Judge)) {
    count(uid)
  }
}
```

**Result**:
```json
{
  "data": {
    "judgment_count": [{"count": 6}],
    "judge_count": [{"count": 3}]
  }
}
```

✅ **Perfect!** No duplicate nodes created across 3 separate batch uploads!

---

## 🎯 Key Learnings from This Example

### 1. Within-Batch Deduplication
- **Batch 1**: "Justice D. Y. Chandra" appeared in 2 judgments
- **Result**: Only 1 judge node created in RDF
- **Mechanism**: `judge_map` prevented duplicate creation

### 2. Cross-Batch Deduplication
- **Batch 1**: Created `<judge_ea7adefd>`
- **Batch 2**: Created `<judge_ea7adefd>` again (duplicate triple in RDF)
- **Result**: Dgraph upsert merged into same node
- **Mechanism**: Same hash ID + upsert predicate

### 3. Citation-Title Unification
- **Batch 3**: Created citation nodes for "Case Alpha" and "Case Delta"
- **Result**: Linked to actual judgment nodes (not duplicates)
- **Mechanism**: Citations use 'judgment' type, same hash calculation

### 4. Fresh RDF Each Batch
- Each batch creates a fresh RDF file (not append)
- May contain duplicate triples from previous batches
- Dgraph upsert handles deduplication automatically

### 5. Elasticsearch Tracking
- `processed_to_dgraph` flag prevents reprocessing
- Each batch only processes new documents
- Maintains clean separation between batches

---

## ✅ Verification Checklist

After running all 3 batches:

- [ ] Only 3 judge nodes exist (not 5)
- [ ] Judge "D. Y. Chandra" has 3 cases linked
- [ ] Citation relationships work correctly
- [ ] No duplicate judgment nodes
- [ ] All documents marked as processed in Elasticsearch
- [ ] RDF file cleaned up after upload

---

**End of Practical Example** 🎯

This demonstrates the complete duplicate prevention system in action!
