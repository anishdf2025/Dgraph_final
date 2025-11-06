# 📚 Legal Judgment Knowledge Graph System - Complete Technical Documentation

**Project**: Legal Judgment Database with RDF Generation and Dgraph Integration  
**Author**: Anish DF  
**Last Updated**: November 6, 2025  
**Version**: 2.1 - Citation-Title Unification Update

---

## 📑 Table of Contents

1. [System Overview](#system-overview)
2. [RDF File Handling - Complete Explanation](#rdf-file-handling---complete-explanation)
3. [Duplicate Prevention Strategy](#duplicate-prevention-strategy)
   - [Citation-Title Unification (CRITICAL Fix)](#citation-title-unification-critical-feature-)
4. [Entity Relationships Explained](#entity-relationships-explained)
5. [Upsert Mechanism in Dgraph](#upsert-mechanism-in-dgraph)
6. [File Structure & Connections](#file-structure--connections)
7. [How to Run the System](#how-to-run-the-system)
8. [Complete CLI Commands](#complete-cli-commands)
9. [Step-by-Step Workflow](#step-by-step-workflow)
10. [Recent Updates & Bug Fixes](#recent-updates--bug-fixes)
11. [Troubleshooting & FAQ](#troubleshooting--faq)

---

## 1. System Overview

### What Does This System Do?

This system converts legal judgment data into a **knowledge graph** stored in Dgraph. It handles:

1. **Excel → Elasticsearch**: Upload judgment data from Excel to Elasticsearch
2. **Elasticsearch → RDF**: Generate RDF triples for new documents only
3. **RDF → Dgraph**: Upload RDF to Dgraph using Docker Live Loader
4. **No Duplicates**: Smart entity linking prevents duplicate nodes
5. **Incremental Processing**: Only process new documents, link to existing entities

### Key Innovation: Stable Content-Based IDs

❌ **OLD Problem** (Counter-based IDs):
```
Batch 1: <judge1> = "Justice D. Y. Chandrachud"
Batch 2: <judge1> = "Justice Hemant Gupta"  ← CONFLICT! Same ID, different judge!
```

✅ **NEW Solution** (MD5 Hash-based IDs):
```
Batch 1: <judge_ea7adefd> = "Justice D. Y. Chandrachud"
Batch 2: <judge_ea7adefd> = "Justice D. Y. Chandrachud"  ← SAME ID!
         <judge_9c1212fb> = "Justice Hemant Gupta"        ← NEW ID!
```

**How it works:**
```python
# In utils.py
def create_node_id(node_type: str, unique_key: str = None) -> str:
    # Create MD5 hash of the unique content
    hash_value = hashlib.md5(unique_key.encode()).hexdigest()[:8]
    return f"{prefix}_{hash_value}"

# Example:
judge_id = create_node_id('judge', unique_key="Justice D. Y. Chandrachud")
# Returns: <judge_ea7adefd>
# Same input ALWAYS gives same ID!
```

---

## 2. RDF File Handling - Complete Explanation

### What is an RDF File?

RDF (Resource Description Framework) is a way to represent data as **triples**:

```rdf
<subject> <predicate> <object> .
```

**Example from our system:**
```rdf
<j_fbc6556f> <title> "M/s Rewa Tollway P. Ltd. v. State of Madhya Pradesh" .
<j_fbc6556f> <judged_by> <judge_ea7adefd> .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .
```

This means:
- Judgment `j_fbc6556f` has title "M/s Rewa Tollway..."
- Judgment `j_fbc6556f` was judged by `judge_ea7adefd`
- Judge `judge_ea7adefd` has name "Justice D. Y. Chandrachud"

### RDF File Lifecycle in Our System

#### Default Mode: Fresh RDF for Each Batch

```
┌─────────────────────────────────────────────────────────────┐
│                  RDF FILE LIFECYCLE                         │
└─────────────────────────────────────────────────────────────┘

Step 1: NEW DOCUMENTS DETECTED
        ↓
Elasticsearch has 3 new documents (processed_to_dgraph: false)

Step 2: GENERATE FRESH RDF FILE
        ↓
Create rdf/judgments.rdf with ONLY these 3 documents
┌──────────────────────────────────────────┐
│ rdf/judgments.rdf (FRESH - 150 triples)  │
├──────────────────────────────────────────┤
│ <j_doc001> <title> "Case 1" .           │
│ <j_doc001> <judged_by> <judge_ea7adefd> │
│ <j_doc002> <title> "Case 2" .           │
│ <j_doc002> <judged_by> <judge_ea7adefd> │  ← Same judge!
│ <j_doc003> <title> "Case 3" .           │
│ <judge_ea7adefd> <name> "Justice DYC" . │  ← Only ONE judge node
└──────────────────────────────────────────┘

Step 3: UPLOAD TO DGRAPH with UPSERT
        ↓
Docker command: dgraph live --files judgments.rdf --upsert-predicates judge_id,advocate_id,...

Dgraph checks:
- judge_ea7adefd already exists? → Link to existing node
- judge_ea7adefd is new? → Create new node
- Result: NO DUPLICATES!

Step 4: MARK AS PROCESSED IN ELASTICSEARCH
        ↓
Update all 3 documents: processed_to_dgraph = true

Step 5: CLEANUP (OPTIONAL)
        ↓
Backup: rdf/judgments_backup_20251106_130015.rdf
Delete: rdf/judgments.rdf (no longer needed, data in Dgraph)
```

### Why Fresh RDF Files (Not Append)?

**Append Mode Problems:**
```
Day 1: judgments.rdf (100 documents, 3000 triples)
Day 2: judgments.rdf (200 documents, 6000 triples)  ← Growing!
Day 3: judgments.rdf (300 documents, 9000 triples)  ← Too large!
Day 30: judgments.rdf (3000 documents, 90000 triples) ← Unmanageable!
```

**Fresh Mode Benefits:**
```
Day 1: judgments.rdf (3 new docs, 90 triples) → Upload → Cleanup
Day 2: judgments.rdf (5 new docs, 150 triples) → Upload → Cleanup
Day 3: judgments.rdf (2 new docs, 60 triples) → Upload → Cleanup
Day 30: judgments.rdf (4 new docs, 120 triples) → Upload → Cleanup
       ↑ ALWAYS SMALL AND CLEAN!
```

### RDF File Location

```
Dgraph_final/
├── rdf/                                  ← Dedicated RDF folder
│   ├── README.md                         ← Documentation
│   ├── judgments.rdf                     ← Active file (temporary)
│   ├── judgments_backup_20251106_120000.rdf  ← Backup 1
│   ├── judgments_backup_20251106_130000.rdf  ← Backup 2
│   └── judgments_backup_20251106_140000.rdf  ← Backup 3
```

**Configuration in `.env`:**
```properties
RDF_OUTPUT_FILE=rdf/judgments.rdf
```

**Code that ensures directory exists:**
```python
# In incremental_processor.py - _write_rdf_file()
output_file = Path(self.output_config['rdf_file'])

# Ensure parent directory exists (creates rdf/ if needed)
output_file.parent.mkdir(parents=True, exist_ok=True)

# Write the file
with open(output_file, mode, encoding="utf-8") as f:
    for line in self.rdf_lines:
        f.write(line + "\n")
```

---

## 3. Duplicate Prevention Strategy

### The Complete Picture: How We Prevent Duplicates

#### Level 1: Stable IDs (During RDF Generation)

**Location**: All relationship handlers (`relationships/*.py`)

```python
# In judge_relationship.py
def _get_or_create_judge_node(self, judge_name: str) -> str:
    # Create stable ID based on judge name
    judge_node = create_node_id('judge', unique_key=judge_name)
    
    # Check if we already created this judge in THIS RDF file
    if judge_node in self.judge_nodes:
        return judge_node  # Reuse existing node
    
    # Create new judge node
    self.judge_nodes[judge_node] = judge_name
    
    # Generate RDF triples for this judge
    self.rdf_lines.append(f'{judge_node} <dgraph.type> "Judge" .')
    self.rdf_lines.append(f'{judge_node} <judge_id> "{judge_node}" .')
    self.rdf_lines.append(f'{judge_node} <name> "{sanitize_string(judge_name)}" .')
    
    return judge_node
```

**Example:**
```
Document 1: Judge = "Justice D. Y. Chandrachud"
  → create_node_id('judge', "Justice D. Y. Chandrachud")
  → Returns: <judge_ea7adefd>
  → Creates judge node (FIRST TIME)

Document 2: Judge = "Justice D. Y. Chandrachud"  ← SAME JUDGE!
  → create_node_id('judge', "Justice D. Y. Chandrachud")
  → Returns: <judge_ea7adefd>  ← SAME ID!
  → Checks judge_nodes dict: already exists!
  → REUSES EXISTING NODE (doesn't create duplicate in RDF)

Document 3: Judge = "Justice Hemant Gupta"  ← DIFFERENT JUDGE
  → create_node_id('judge', "Justice Hemant Gupta")
  → Returns: <judge_9c1212fb>  ← NEW ID!
  → Creates new judge node
```

**Result in RDF file:**
```rdf
# Only TWO judge nodes created (no duplicates in RDF)
<judge_ea7adefd> <dgraph.type> "Judge" .
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .

<judge_9c1212fb> <dgraph.type> "Judge" .
<judge_9c1212fb> <judge_id> "judge_9c1212fb" .
<judge_9c1212fb> <name> "Justice Hemant Gupta" .

# Three judgments, but only two judge nodes
<j_doc001> <judged_by> <judge_ea7adefd> .
<j_doc002> <judged_by> <judge_ea7adefd> .  ← Reuses same judge!
<j_doc003> <judged_by> <judge_9c1212fb> .
```

#### Level 2: Upsert (During Dgraph Upload)

**Location**: `incremental_processor.py` - `_upload_to_dgraph()`

```python
def _upload_to_dgraph(self) -> None:
    # Build the Docker command with upsert predicates
    upsert_predicates = [
        "judgment_id",      # Unique judgment identifier
        "doc_id",          # Elasticsearch document ID
        "judge_id",        # Judge stable ID
        "advocate_id",     # Advocate stable ID
        "outcome_id",      # Outcome stable ID
        "case_duration_id" # Case duration stable ID
    ]
    
    command = [
        "docker", "exec", "-i", container_name,
        "dgraph", "live",
        "--files", "/dgraph/judgments.rdf",
        "--schema", "/dgraph/rdf.schema",
        "--alpha", f"{dgraph_host}",
        "--zero", f"{dgraph_zero}",
        "--upsert-predicates", ",".join(upsert_predicates)
    ]
```

**What `--upsert-predicates` does:**

```
When Dgraph receives:
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .

Dgraph checks:
1. Query: Does a node with judge_id="judge_ea7adefd" already exist?

   YES → UPDATE existing node (merge new predicates)
   NO  → CREATE new node

This is why we get NO DUPLICATES across batches!
```

**Schema Configuration** (`rdf.schema`):
```
judge_id: string @index(exact) @upsert .
           ↑                      ↑
           |                      └─ Enable upsert on this field
           └─ Make it searchable
```

#### Level 3: Cross-Batch Stability

**Scenario**: Process 2 batches with the same judge

**Batch 1** (Monday):
```rdf
# Fresh RDF file for Monday's 5 new documents
<j_doc001> <judged_by> <judge_ea7adefd> .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .

→ Upload to Dgraph
→ Dgraph creates: judge_ea7adefd node (UID: 0x123)
```

**Batch 2** (Tuesday):
```rdf
# Fresh RDF file for Tuesday's 3 new documents
<j_doc006> <judged_by> <judge_ea7adefd> .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .

→ Upload to Dgraph
→ Dgraph checks: judge_id="judge_ea7adefd" exists? YES (UID: 0x123)
→ Dgraph LINKS to existing node (doesn't create duplicate!)
```

**Result in Dgraph:**
```
Only ONE judge node (UID: 0x123):
{
  uid: 0x123
  judge_id: "judge_ea7adefd"
  name: "Justice D. Y. Chandrachud"
  ~judged_by: [
    { uid: 0x456, title: "Case from Monday" },
    { uid: 0x457, title: "Case from Monday" },
    { uid: 0x458, title: "Case from Monday" },
    { uid: 0x459, title: "Case from Monday" },
    { uid: 0x460, title: "Case from Monday" },
    { uid: 0x789, title: "Case from Tuesday" },  ← NEW!
    { uid: 0x790, title: "Case from Tuesday" },  ← NEW!
    { uid: 0x791, title: "Case from Tuesday" }   ← NEW!
  ]
}
```

### Why We Don't Leave Single Entities

❌ **Bad Approach** (leaving isolated entities):
```rdf
# Creating judge without linking to any judgment
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .
# ← ORPHAN NODE! No relationships! Useless!
```

✅ **Good Approach** (always create relationships):
```rdf
# Create judgment
<j_doc001> <title> "Case Title" .
<j_doc001> <dgraph.type> "Judgment" .

# Create judge
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .
<judge_ea7adefd> <dgraph.type> "Judge" .

# CREATE RELATIONSHIP (this is the key!)
<j_doc001> <judged_by> <judge_ea7adefd> .
           ↑              ↑
           |              └─ The judge (target)
           └─ The judgment (source)
```

**Why relationships are critical:**

1. **Graph Traversal**: You can query "all cases by Justice DYC"
2. **Data Integrity**: Every entity serves a purpose
3. **Query Performance**: Reverse edges (@reverse) enable fast lookups
4. **Meaningfulness**: Isolated nodes provide no value

### Citation-Title Unification (CRITICAL Feature) ⭐

**Problem Identified**: What if a citation later becomes an actual judgment (or vice versa)?

This was a **CRITICAL BUG** that caused duplicate nodes in Dgraph!

#### ❌ **The Problem (BEFORE FIX)**

```
Monday (Batch 1):
  Document A cites: "Kesavananda Bharati v. State of Kerala (1973) 4 SCC 225"
  
  citation_relationship.py:
    citation_node = create_node_id('judgment', unique_key=citation_title)
    → ID: <j_e0d69a27>  (based on TITLE)
  
  RDF: <j_e4195c44> <cites> <j_e0d69a27> .

Tuesday (Batch 2):
  Upload actual: "Kesavananda Bharati v. State of Kerala (1973) 4 SCC 225"
  doc_id: "xyz123"
  
  incremental_processor.py (OLD CODE):
    judgment_node = create_node_id('judgment', unique_key=doc_id)  # ❌ USED DOC_ID!
    → ID: <j_9f2a34bc>  (based on DOC_ID)
  
  RDF: <j_9f2a34bc> <title> "Kesavananda Bharati..." .

Result: TWO DIFFERENT NODES FOR SAME CASE! ❌❌❌
  - <j_e0d69a27> (citation node, title-based)
  - <j_9f2a34bc> (judgment node, doc_id-based)
```

**Root Cause**:
- Citations used `unique_key=title` → Hash of title
- Judgments used `unique_key=doc_id` → Hash of doc_id
- Same title → Different unique_key → Different hash → Different ID!

#### ✅ **The Solution (AFTER FIX)**

**Files Modified**:

1. **`utils.py`** - Unified prefix for citations and judgments:
   ```python
   node_type_map = {
       'judgment': 'j',
       'citation': 'j',  # ✅ Changed from 'c' to 'j' (unified!)
       'judge': 'judge',
       'advocate': 'adv',
       # ...
   }
   
   # Added title normalization
   normalized_key = unique_key.lower().strip()
   hash_value = hashlib.md5(normalized_key.encode()).hexdigest()[:8]
   ```

2. **`citation_relationship.py`** (Line ~73) - Use 'judgment' type:
   ```python
   # Changed from:
   # citation_node = create_node_id('citation', unique_key=citation_title)
   
   # To:
   citation_node = create_node_id('judgment', unique_key=citation_title)  # ✅
   ```

3. **`incremental_processor.py`** (Line ~210) - **⭐ CRITICAL FIX**:
   ```python
   # OLD (CAUSED DUPLICATES):
   # judgment_node = create_node_id('judgment', unique_key=doc_id)  # ❌
   
   # NEW (FIXED):
   # CRITICAL: Use TITLE (not doc_id) to create judgment node IDs
   # This ensures citations and actual judgments with same title get same ID
   # Citation: "Case X" → <j_abc123> (based on title hash)
   # Judgment: "Case X" → <j_abc123> (same ID!)
   # Result: Dgraph merges them via upsert (no duplicates!)
   judgment_node = create_node_id('judgment', unique_key=title)  # ✅
   ```

#### 🎉 **How It Works Now**

```
Monday (Batch 1):
  Document A cites: "Kesavananda Bharati v. State of Kerala (1973) 4 SCC 225"
  
  citation_relationship.py:
    citation_node = create_node_id('judgment', unique_key=citation_title)
    → normalize: "kesavananda bharati v. state of kerala (1973) 4 scc 225"
    → hash: "e0d69a27"
    → ID: <j_e0d69a27>  ✅
  
  RDF Generated:
    <j_e0d69a27> <title> "Kesavananda Bharati v. State of Kerala (1973) 4 SCC 225" .
    <j_e4195c44> <cites> <j_e0d69a27> .
  
  Dgraph: Creates node <j_e0d69a27>

Tuesday (Batch 2):
  Upload actual: "Kesavananda Bharati v. State of Kerala (1973) 4 SCC 225"
  doc_id: "xyz123"
  
  incremental_processor.py (NEW CODE):
    judgment_node = create_node_id('judgment', unique_key=title)  # ✅ USES TITLE!
    → normalize: "kesavananda bharati v. state of kerala (1973) 4 scc 225"
    → hash: "e0d69a27"  ← SAME HASH!
    → ID: <j_e0d69a27>  ← SAME ID! ✅✅✅
  
  RDF Generated:
    <j_e0d69a27> <title> "Kesavananda Bharati v. State of Kerala (1973) 4 SCC 225" .
    <j_e0d69a27> <doc_id> "xyz123" .
    <j_e0d69a27> <year> "1973" .
  
  Dgraph Upsert Query:
    query {
      q(func: eq(judgment_id, "j_e0d69a27")) {
        v as uid
      }
    }
    
    mutation {
      set {
        uid(v) <title> "Kesavananda Bharati..." .
        uid(v) <doc_id> "xyz123" .        # ✅ ADDED
        uid(v) <year> "1973" .            # ✅ ADDED
      }
    }
  
  Result: ONE NODE, UPDATED WITH NEW FIELDS! ✅
    <j_e0d69a27> {
      title: "Kesavananda Bharati v. State of Kerala (1973) 4 SCC 225"
      doc_id: "xyz123"          ← Added from Batch 2
      year: 1973                ← Added from Batch 2
      ~cites: [Document A]      ← Preserved from Batch 1
    }
```

#### 📊 **Verification**

**Test Results** (from `test_citation_unification.py`):
```
🎉 ALL TESTS PASSED!
======================================================================
✅ PASS - Citation-Judgment Unification
   Citation ID:  j_e0d69a27
   Judgment ID:  j_e0d69a27
   → IDs MATCH! Citation and judgment will merge in Dgraph!

✅ PASS - Real-World Scenario
   Batch 1 (Citation): <j_e0d69a27>
   Batch 2 (Judgment): <j_e0d69a27>
   → SAME ID! Dgraph merges automatically!

✅ PASS - Title Normalization
   'Case A v. Case B (2024) 5 SCC 123'     → j_136e32b4
   'case a v. case b (2024) 5 scc 123'     → j_136e32b4
   ' Case A v. Case B (2024) 5 SCC 123 '   → j_136e32b4
   'CASE A V. CASE B (2024) 5 SCC 123'     → j_136e32b4
   → All variations produce SAME ID!
```

#### 🎯 **Benefits**

1. **✅ No Duplicate Nodes**: Same title always gets same ID
2. **✅ Automatic Merging**: Dgraph upsert handles the rest
3. **✅ Bidirectional**: Works for citation→judgment AND judgment→citation
4. **✅ Data Enrichment**: Citation nodes gain full data when actual judgment uploaded
5. **✅ Relationship Preservation**: All citation relationships remain valid
6. **✅ Case Insensitive**: "Case A" and "case a" produce same ID
7. **✅ Whitespace Tolerant**: " Case A " and "Case A" produce same ID

#### 📖 **Additional Documentation**

- **Detailed Explanation**: See `CITATION_TITLE_UNIFICATION.md`
- **Fix Verification**: See `CITATION_TITLE_FIX_VERIFICATION.md`
- **Test Suite**: Run `python3 test_citation_unification.py`

#### ⚠️ **Important Notes**

**About `doc_id`**:
- ✅ Still tracked: `doc_id` is stored as a predicate: `<j_xxx> <doc_id> "xyz123" .`
- ✅ ES sync works: Elasticsearch tracking still functional
- ❌ Not used for ID: ID generation now uses **title only** for consistency

**Impact on Existing Data**:
- Old data: May have duplicates (generated before fix)
- New data: No duplicates (after fix applied)
- Recommendation: Re-upload data to clean up old duplicates

---

## 4. Entity Relationships Explained

### Complete Relationship Model

```
┌─────────────────────────────────────────────────────────────────────┐
│                     JUDGMENT (Central Node)                         │
│                 <j_fbc6556f> (type: Judgment)                       │
└────────────────────────┬────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬─────────────┬──────────────┐
         │               │               │             │              │
         ▼               ▼               ▼             ▼              ▼
    ┌────────┐     ┌──────────┐    ┌─────────┐   ┌────────┐    ┌──────────┐
    │ JUDGES │     │ADVOCATES │    │CITATIONS│   │OUTCOME │    │DURATION  │
    └────────┘     └──────────┘    └─────────┘   └────────┘    └──────────┘
```

### Relationship 1: Judgment → Judge

**Code Location**: `relationships/judge_relationship.py`

```python
def create_judge_relationships(self, judgment: JudgmentData) -> List[str]:
    relationship_triples = []
    
    # Parse judge names from the data
    judge_names = parse_list_data(judgment.judge_name)
    
    for judge_name in judge_names:
        if not judge_name or judge_name.lower() in ['nan', 'null']:
            continue
        
        # Get or create judge node (returns stable ID)
        judge_node = self._get_or_create_judge_node(judge_name)
        
        # Create relationship triple
        relationship_triples.append(
            format_rdf_triple(
                judgment.judgment_node,  # <j_fbc6556f>
                "judged_by",            # Predicate
                judge_node,             # <judge_ea7adefd>
                is_object_literal=False # It's a node reference, not a string
            )
        )
    
    return relationship_triples
```

**Generated RDF:**
```rdf
# Judgment node
<j_fbc6556f> <dgraph.type> "Judgment" .
<j_fbc6556f> <title> "M/s Rewa Tollway v. State of MP" .

# Judge node
<judge_ea7adefd> <dgraph.type> "Judge" .
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .

# RELATIONSHIP (connects them)
<j_fbc6556f> <judged_by> <judge_ea7adefd> .
```

**Reverse Query** (thanks to `@reverse` in schema):
```graphql
# Find all cases judged by Justice DYC
{
  judge(func: eq(name, "Justice D. Y. Chandrachud")) {
    name
    ~judged_by {  # ← Reverse edge!
      title
      year
    }
  }
}
```

### Relationship 2: Judgment → Advocates (Petitioner & Respondent)

**Code Location**: `relationships/advocate_relationship.py`

**Key Difference**: Advocates have **type** (petitioner vs respondent)

```python
def _get_or_create_petitioner_advocate_node(self, advocate_name: str) -> str:
    # Create UNIQUE KEY with type prefix
    unique_key = f"petitioner_{advocate_name}"
    advocate_node = create_node_id('petitioner_advocate', unique_key=unique_key)
    
    if advocate_node in self.petitioner_advocate_nodes:
        return advocate_node
    
    self.petitioner_advocate_nodes[advocate_node] = advocate_name
    
    # Create advocate node
    self.rdf_lines.append(f'{advocate_node} <dgraph.type> "Advocate" .')
    self.rdf_lines.append(f'{advocate_node} <advocate_id> "{advocate_node}" .')
    self.rdf_lines.append(f'{advocate_node} <name> "{sanitize_string(advocate_name)}" .')
    self.rdf_lines.append(f'{advocate_node} <advocate_type> "petitioner" .')
    
    return advocate_node
```

**Why separate unique keys?**

Mr. X can be:
- Petitioner advocate in Case A → `<petitioner_advocate_abc123>`
- Respondent advocate in Case B → `<respondant_advocate_def456>`

These are **different roles**, so we create **different nodes**!

**Generated RDF:**
```rdf
# Petitioner Advocate
<petitioner_advocate_463fad67> <dgraph.type> "Advocate" .
<petitioner_advocate_463fad67> <advocate_id> "petitioner_advocate_463fad67" .
<petitioner_advocate_463fad67> <name> "Mr. Mukul Rohatgi" .
<petitioner_advocate_463fad67> <advocate_type> "petitioner" .

# Respondent Advocate
<respondant_advocate_71f51151> <dgraph.type> "Advocate" .
<respondant_advocate_71f51151> <advocate_id> "respondant_advocate_71f51151" .
<respondant_advocate_71f51151> <name> "Mr. Tushar Mehta" .
<respondant_advocate_71f51151> <advocate_type> "respondant" .

# RELATIONSHIPS
<j_fbc6556f> <petitioner_represented_by> <petitioner_advocate_463fad67> .
<j_fbc6556f> <respondant_represented_by> <respondant_advocate_71f51151> .
```

### Relationship 3: Judgment → Citations

**Code Location**: `relationships/citation_relationship.py`

**Two types of citations:**

1. **Internal Citation**: Referenced judgment exists in our database
2. **External Citation**: Referenced judgment is from elsewhere

```python
def create_citation_relationships(self, judgment: JudgmentData) -> List[str]:
    relationship_triples = []
    citations = parse_list_data(judgment.raw_citations)
    
    for citation_title in citations:
        # Check if this citation matches an existing judgment title
        citation_lower = citation_title.lower().strip()
        
        if citation_lower in self.title_to_judgment_map:
            # INTERNAL CITATION: Link directly to existing judgment
            target_judgment = self.title_to_judgment_map[citation_lower]
            relationship_triples.append(
                format_rdf_triple(
                    judgment.judgment_node,
                    "cites",
                    target_judgment,  # <j_existing>
                    is_object_literal=False
                )
            )
            self.stats['title_matches'] += 1
        else:
            # EXTERNAL CITATION: Create citation node
            citation_node = self._get_or_create_citation_node(citation_title)
            relationship_triples.append(
                format_rdf_triple(
                    judgment.judgment_node,
                    "cites",
                    citation_node,  # <c_hash>
                    is_object_literal=False
                )
            )
            self.stats['citation_matches'] += 1
    
    return relationship_triples
```

**Example:**

```rdf
# Case A cites Case B (both in our database)
<j_case_a> <cites> <j_case_b> .  # ← Direct link!

# Case A cites external case
<j_case_a> <cites> <c_external_abc> .
<c_external_abc> <dgraph.type> "Judgment" .
<c_external_abc> <judgment_id> "c_external_abc" .
<c_external_abc> <title> "Some External Case (2020) 5 SCC 123" .
```

### Relationship 4: Judgment → Outcome

**Code Location**: `relationships/outcome_relationship.py`

**Simple 1:1 relationship:**

```python
def create_outcome_relationship(self, judgment: JudgmentData) -> List[str]:
    outcome_name = judgment.outcome.strip()
    
    if not outcome_name or outcome_name.lower() in ['nan', 'null', '']:
        return []
    
    # Get or create outcome node
    outcome_node = self._get_or_create_outcome_node(outcome_name)
    
    # Create relationship
    return [format_rdf_triple(
        judgment.judgment_node,
        "has_outcome",
        outcome_node,
        is_object_literal=False
    )]
```

**Generated RDF:**
```rdf
<outcome_ea9157af> <dgraph.type> "Outcome" .
<outcome_ea9157af> <outcome_id> "outcome_ea9157af" .
<outcome_ea9157af> <name> "Petitioner Won" .

<j_fbc6556f> <has_outcome> <outcome_ea9157af> .
```

**Typical outcomes:**
- "Petitioner Won"
- "Respondent Won"
- "Partially Allowed"
- "Dismissed"

### Relationship 5: Judgment → Case Duration

**Code Location**: `relationships/case_duration_relationship.py`

**Example:**
```rdf
<case_duration_628e8e7f> <dgraph.type> "CaseDuration" .
<case_duration_628e8e7f> <case_duration_id> "case_duration_628e8e7f" .
<case_duration_628e8e7f> <duration> "2019-03-15 to 2019-11-18" .

<j_fbc6556f> <has_case_duration> <case_duration_628e8e7f> .
```

---

## 5. Upsert Mechanism in Dgraph

### What is Upsert?

**UPSERT = UPDATE + INSERT**

If entity exists → UPDATE it  
If entity doesn't exist → INSERT it

### How Dgraph Upsert Works

#### Step 1: Schema Declaration

**File**: `rdf.schema`

```
# Make these fields upsert-able
judgment_id: string @index(exact) @upsert .
judge_id: string @index(exact) @upsert .
advocate_id: string @index(exact) @upsert .
outcome_id: string @index(exact) @upsert .
case_duration_id: string @index(exact) @upsert .

# @index(exact) = Makes field searchable by exact match
# @upsert = Enables upsert on this field
```

#### Step 2: Upload with Upsert Flag

**Command**:
```bash
dgraph live \
  --files /dgraph/judgments.rdf \
  --schema /dgraph/rdf.schema \
  --alpha dgraph-standalone:9080 \
  --zero dgraph-standalone:5080 \
  --upsert-predicates judgment_id,doc_id,judge_id,advocate_id,outcome_id,case_duration_id
```

#### Step 3: Dgraph Processing Logic

**Pseudocode of what Dgraph does:**

```python
for triple in rdf_file:
    subject = triple.subject      # <judge_ea7adefd>
    predicate = triple.predicate  # judge_id
    object = triple.object        # "judge_ea7adefd"
    
    if predicate in upsert_predicates:
        # Check if node exists
        existing_node = query(f"eq({predicate}, '{object}')")
        
        if existing_node:
            # UPDATE: Merge new predicates into existing node
            uid = existing_node.uid
            update_node(uid, triple.all_predicates)
        else:
            # INSERT: Create new node
            uid = create_new_node()
            add_predicate(uid, predicate, object)
    else:
        # Regular predicate: just add it
        add_predicate(subject_uid, predicate, object)
```

### Visual Example of Upsert in Action

**First Upload** (Monday):
```rdf
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .
```

**Dgraph state after upload:**
```
Node UID: 0x123
├─ judge_id: "judge_ea7adefd"
└─ name: "Justice D. Y. Chandrachud"
```

**Second Upload** (Tuesday):
```rdf
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .
<judge_ea7adefd> <phone> "+91-1234567890" .  ← NEW PREDICATE!
```

**Dgraph process:**
```
1. Check: Does judge_id="judge_ea7adefd" exist?
2. Found: UID 0x123
3. Action: MERGE new predicates into UID 0x123
```

**Dgraph state after upload:**
```
Node UID: 0x123  ← SAME UID (not a new node!)
├─ judge_id: "judge_ea7adefd"
├─ name: "Justice D. Y. Chandrachud"
└─ phone: "+91-1234567890"  ← ADDED!
```

### Why Upsert is Critical for Us

**Without Upsert** (BAD):
```
Batch 1: Creates judge_ea7adefd (UID: 0x123)
Batch 2: Creates judge_ea7adefd (UID: 0x789) ← DUPLICATE!
Result: 2 judges with same name! ❌
```

**With Upsert** (GOOD):
```
Batch 1: Creates judge_ea7adefd (UID: 0x123)
Batch 2: Links to judge_ea7adefd (UID: 0x123) ← REUSE!
Result: 1 judge, all cases linked correctly! ✅
```

---

## 6. File Structure & Connections

### Complete File Dependency Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ENTRY POINTS                                │
└─────────────────────────────────────────────────────────────────────┘

1. elasticsearch_upload.py        ← Upload Excel to Elasticsearch
2. fastapi_app.py                ← Start REST API server
3. incremental_processor.py      ← Manual processing script

        ↓ All depend on ↓

┌─────────────────────────────────────────────────────────────────────┐
│                       CORE MODULES                                  │
└─────────────────────────────────────────────────────────────────────┘

config.py ─────────────────┐
                           ├──→ ALL FILES (provides configuration)
models.py ─────────────────┤
                           │
utils.py ──────────────────┤
                           │
elasticsearch_handler.py ──┴──→ Data loading/tracking

        ↓

┌─────────────────────────────────────────────────────────────────────┐
│                   RELATIONSHIP HANDLERS                             │
│                  (relationships/ package)                           │
└─────────────────────────────────────────────────────────────────────┘

relationships/__init__.py
         ↓
    Imports all handlers:
         ├─ judge_relationship.py
         ├─ advocate_relationship.py
         ├─ outcome_relationship.py
         ├─ case_duration_relationship.py
         └─ citation_relationship.py

        ↓ Used by ↓

┌─────────────────────────────────────────────────────────────────────┐
│                     PROCESSING LAYER                                │
└─────────────────────────────────────────────────────────────────────┘

incremental_processor.py ──┐
                           ├──→ RDF Generation
auto_processor.py ─────────┤     (uses all handlers)
                           │
fastapi_app.py ────────────┘

        ↓ Outputs ↓

┌─────────────────────────────────────────────────────────────────────┐
│                         OUTPUT FILES                                │
└─────────────────────────────────────────────────────────────────────┘

rdf/judgments.rdf              ← RDF triples
rdf_generator.log              ← Processing logs
elasticsearch_upload.log       ← Upload logs
```

### Detailed File Descriptions

#### 1. **config.py** - Configuration Manager

**Purpose**: Centralized configuration from `.env` file

**Key Functions:**
```python
class Config:
    # Loads environment variables
    ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'http://localhost:9200')
    RDF_OUTPUT_FILE = os.getenv('RDF_OUTPUT_FILE', 'rdf/judgments.rdf')
    
    @classmethod
    def get_elasticsearch_config(cls) -> dict:
        return {
            'host': cls.ELASTICSEARCH_HOST,
            'index': cls.ELASTICSEARCH_INDEX,
            'timeout': cls.ELASTICSEARCH_TIMEOUT
        }
```

**Used By**: Every single file in the project

#### 2. **models.py** - Data Structures

**Purpose**: Define data classes for type safety

**Key Classes:**
```python
@dataclass
class JudgmentData:
    """Represents a single judgment"""
    idx: int
    title: str
    doc_id: str
    year: Optional[int]
    judge_name: str
    # ... more fields

@dataclass
class ProcessingStats:
    """Tracks processing statistics"""
    total_judgments: int = 0
    total_judges: int = 0
    # ... more counters
```

**Used By**: All processors and handlers

#### 3. **utils.py** - Utility Functions

**Purpose**: Shared helper functions

**Key Functions:**
```python
def create_node_id(node_type: str, unique_key: str = None) -> str:
    """Generate stable MD5-based node IDs"""
    hash_value = hashlib.md5(unique_key.encode()).hexdigest()[:8]
    return f"{prefix}_{hash_value}"

def format_rdf_triple(subject, predicate, obj, is_object_literal=True):
    """Format RDF triple correctly"""
    if is_object_literal:
        return f'{subject} <{predicate}> "{obj}" .'
    else:
        return f'{subject} <{predicate}> {obj} .'
```

**Used By**: All relationship handlers, processors

#### 4. **elasticsearch_handler.py** - ES Operations

**Purpose**: All Elasticsearch interactions

**Key Methods:**
```python
class ElasticsearchHandler:
    def load_unprocessed_documents(self) -> pd.DataFrame:
        """Fetch documents where processed_to_dgraph=false"""
        
    def mark_documents_as_processed(self, doc_ids: List[str]):
        """Update processed_to_dgraph=true"""
        
    def get_processing_counts(self) -> Dict[str, int]:
        """Get statistics"""
```

**Used By**: incremental_processor.py, fastapi_app.py

#### 5. **Relationship Handlers** (relationships/)

**Purpose**: Generate RDF for each entity type

**Pattern** (same for all handlers):
```python
class EntityRelationshipHandler:
    def __init__(self):
        self.entity_nodes = {}  # Track created nodes
        self.rdf_lines = []     # Collect RDF triples
        self.stats = {}         # Count statistics
    
    def create_relationships(self, judgment: JudgmentData) -> List[str]:
        """Generate relationship triples"""
        
    def _get_or_create_entity_node(self, entity_data: str) -> str:
        """Get existing or create new entity node"""
        
    def get_all_rdf_triples(self) -> List[str]:
        """Return all generated triples"""
```

**Used By**: incremental_processor.py

#### 6. **incremental_processor.py** - Core Processor

**Purpose**: Main RDF generation logic

**Workflow:**
```python
class IncrementalRDFProcessor:
    def process_incremental(self):
        # 1. Load unprocessed documents from ES
        df = self.es_handler.load_unprocessed_documents()
        
        # 2. Collect judgment data
        self._collect_judgment_data(df)
        
        # 3. Process all relationships
        self._process_judgments_and_relationships()
        
        # 4. Combine all triples
        self._combine_all_triples()
        
        # 5. Write RDF file
        self._write_rdf_file(append_mode=False)
        
        # 6. Upload to Dgraph
        self._upload_to_dgraph()
        
        # 7. Mark as processed
        self.es_handler.mark_documents_as_processed(doc_ids)
        
        # 8. Cleanup
        self._cleanup_rdf_file()
```

**Used By**: fastapi_app.py, auto_processor.py, manual scripts

#### 7. **fastapi_app.py** - REST API

**Purpose**: Web API for processing

**Key Endpoints:**
```python
@app.post("/process")
def process_documents():
    """Trigger incremental processing"""

@app.get("/status")
def get_status():
    """Check processing status"""

@app.get("/documents/unprocessed")
def get_unprocessed():
    """List unprocessed documents"""
```

**Starts**: Background auto-processor on startup

#### 8. **auto_processor.py** - Background Worker

**Purpose**: Automatic periodic processing

**Workflow:**
```python
class AutoProcessor:
    async def _check_and_process(self):
        while self.is_running:
            # Check for new documents
            counts = es_handler.get_processing_counts()
            
            if counts['unprocessed'] > 0:
                # Process them
                self._process_documents()
            
            # Wait before next check
            await asyncio.sleep(self.check_interval)
```

**Started By**: fastapi_app.py on startup

---

## 7. How to Run the System

### Prerequisites

1. **Docker** (for Dgraph)
2. **Python 3.8+**
3. **Elasticsearch** (running on localhost:9200)
4. **Python packages**:
   ```bash
   pip install fastapi uvicorn elasticsearch pandas python-dotenv openpyxl
   ```

### Step-by-Step Setup

#### Step 1: Start Dgraph

```bash
# Start Dgraph standalone container
docker run -it -p 8180:8080 -p 8181:8081 -p 8000:8000 \
  -v ~/dgraph_data:/dgraph \
  --name dgraph-standalone \
  dgraph/dgraph:v23.1.0

# Verify it's running
curl http://localhost:8180/health
```

**Expected output:**
```json
[{"instance":"zero","address":"dgraph-standalone:5080","status":"healthy"}]
```

#### Step 2: Start Elasticsearch

```bash
# If using Docker:
docker run -d -p 9200:9200 -e "discovery.type=single-node" \
  elasticsearch:8.11.0

# Verify
curl http://localhost:9200
```

#### Step 3: Upload Dgraph Schema

```bash
# Upload schema first time only
curl -X POST localhost:8180/alter -d @rdf.schema
```

**Or using file:**
```bash
curl -X POST localhost:8180/alter -d '
type Judgment {
  judgment_id
  title
  doc_id
  year
  cites
  judged_by
  petitioner_represented_by
  respondant_represented_by
  has_outcome
  has_case_duration
}

type Judge {
  judge_id
  name
}

type Advocate {
  advocate_id
  name
  advocate_type
}

type Outcome {
  outcome_id
  name
}

type CaseDuration {
  case_duration_id
  duration
}

judgment_id: string @index(exact) @upsert .
title: string @index(exact, term, fulltext) @upsert .
doc_id: string @index(exact) @upsert .
year: int @index(int) .
processed_timestamp: datetime @index(hour) .
cites: [uid] @reverse .
judged_by: [uid] @reverse .
petitioner_represented_by: [uid] @reverse .
respondant_represented_by: [uid] @reverse .
has_outcome: uid @reverse .
has_case_duration: uid @reverse .
judge_id: string @index(exact) @upsert .
name: string @index(exact, term, fulltext) @upsert .
advocate_id: string @index(exact) @upsert .
advocate_type: string @index(exact) .
outcome_id: string @index(exact) @upsert .
case_duration_id: string @index(exact) @upsert .
duration: string @index(exact, term) .
'
```

#### Step 4: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Minimal `.env`:**
```properties
ELASTICSEARCH_HOST=http://localhost:9200
ELASTICSEARCH_INDEX=graphdb
DGRAPH_HOST=dgraph-standalone:9080
DGRAPH_ZERO=dgraph-standalone:5080
RDF_OUTPUT_FILE=rdf/judgments.rdf
FASTAPI_PORT=8003
```

#### Step 5: Upload Data to Elasticsearch

```bash
# Upload Excel data to Elasticsearch
python3 elasticsearch_upload.py
```

**Expected output:**
```
✅ Connected to Elasticsearch at http://localhost:9200
📖 Loading Excel file: tests.xlsx
✅ Loaded 8 rows from Excel file
📋 Found 0 existing documents in index
📝 No 'doc_id' column in Excel; will let Elasticsearch assign IDs
📤 Starting bulk upload of 8 documents to index: graphdb
✅ Successfully uploaded 8 documents
```

---

## 8. Complete CLI Commands

### Start FastAPI Server with Auto-Processor

```bash
# Method 1: Using uvicorn directly
uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload

# Method 2: Using Python
python3 -m uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload

# Method 3: Direct Python execution
python3 fastapi_app.py
```

**Explanation of flags:**
- `--host 0.0.0.0`: Listen on all network interfaces (accessible from other machines)
- `--port 8003`: Use port 8003
- `--reload`: Auto-reload on code changes (development only)

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8003 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
2025-11-06 13:00:00,123 - INFO - 🚀 Auto-processor started (check interval: 60 seconds)
```

### Manual Processing Commands

```bash
# Process all unprocessed documents
python3 -c "
from incremental_processor import IncrementalRDFProcessor
processor = IncrementalRDFProcessor()
result = processor.process_incremental()
print(f\"Processed {result['documents_processed']} documents\")
"

# Process specific documents
python3 -c "
from incremental_processor import IncrementalRDFProcessor
processor = IncrementalRDFProcessor()
result = processor.process_incremental(doc_ids=['doc1', 'doc2'])
print(result)
"

# Force reprocess (even if marked as processed)
python3 -c "
from incremental_processor import IncrementalRDFProcessor
processor = IncrementalRDFProcessor()
result = processor.process_incremental(force_reprocess=True)
print(result)
"
```

### API Endpoints

#### 1. Check Server Health
```bash
curl http://localhost:8003/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-06T13:00:00.000000",
  "services": {
    "elasticsearch": "connected",
    "dgraph": "connected"
  }
}
```

#### 2. Get Processing Status
```bash
curl http://localhost:8003/status
```

**Response:**
```json
{
  "is_processing": false,
  "last_run": "2025-11-06T12:45:00.000000",
  "last_run_status": "success",
  "unprocessed_documents": 0,
  "processed_documents": 8,
  "total_documents": 8
}
```

#### 3. Trigger Manual Processing
```bash
# Process all unprocessed
curl -X POST http://localhost:8003/process \
  -H "Content-Type: application/json" \
  -d '{}'

# Process with options
curl -X POST http://localhost:8003/process \
  -H "Content-Type: application/json" \
  -d '{
    "force_reprocess": false,
    "auto_upload": true,
    "cleanup_rdf": true
  }'

# Process specific documents
curl -X POST http://localhost:8003/process \
  -H "Content-Type: application/json" \
  -d '{
    "doc_ids": ["doc123", "doc456"]
  }'
```

**Response:**
```json
{
  "status": "processing_started",
  "message": "Processing started in background",
  "documents_to_process": 3
}
```

#### 4. Get Unprocessed Documents List
```bash
curl http://localhost:8003/documents/unprocessed?limit=10
```

**Response:**
```json
{
  "unprocessed_documents": [
    {
      "doc_id": "doc123",
      "title": "Case Title 1"
    },
    {
      "doc_id": "doc456",
      "title": "Case Title 2"
    }
  ],
  "count": 2
}
```

#### 5. Get Document Counts
```bash
curl http://localhost:8003/documents/count
```

**Response:**
```json
{
  "total": 10,
  "processed": 8,
  "unprocessed": 2,
  "processing_rate": "80%"
}
```

#### 6. Mark Documents as Processed
```bash
curl -X POST http://localhost:8003/documents/mark-processed \
  -H "Content-Type: application/json" \
  -d '{
    "doc_ids": ["doc123", "doc456"]
  }'
```

#### 7. Reset Processed Status
```bash
# Reset specific documents
curl -X POST http://localhost:8003/documents/reset-processed \
  -H "Content-Type: application/json" \
  -d '{
    "doc_ids": ["doc123", "doc456"]
  }'

# Reset all documents
curl -X POST http://localhost:8003/documents/reset-processed \
  -H "Content-Type: application/json" \
  -d '{
    "all": true
  }'
```

### Dgraph Query Commands

#### Query all judgments
```bash
curl -X POST http://localhost:8180/query -d '{
  allJudgments(func: type(Judgment)) {
    uid
    judgment_id
    title
    year
  }
}'
```

#### Query specific judge
```bash
curl -X POST http://localhost:8180/query -d '{
  judge(func: eq(name, "Justice D. Y. Chandrachud")) {
    uid
    name
    ~judged_by {
      title
      year
    }
  }
}'
```

#### Count all entities
```bash
curl -X POST http://localhost:8180/query -d '{
  judgments(func: type(Judgment)) {
    count(uid)
  }
  judges(func: type(Judge)) {
    count(uid)
  }
  advocates(func: type(Advocate)) {
    count(uid)
  }
}'
```

---

## 9. Step-by-Step Workflow

### Complete End-to-End Example

#### Scenario: Adding 3 New Judgments

**Step 1: Start Services**
```bash
# Terminal 1: Start Dgraph
docker run -it -p 8180:8080 -p 8181:8081 -p 8000:8000 \
  -v ~/dgraph_data:/dgraph \
  --name dgraph-standalone \
  dgraph/dgraph:v23.1.0

# Terminal 2: Start FastAPI (with auto-processor)
cd /home/anish/Desktop/Anish/Dgraph_final
uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload
```

**Step 2: Prepare Excel Data**

Edit `tests.xlsx`:
```
| Title                  | Year | Judge_name              | ... |
|------------------------|------|-------------------------|-----|
| Case A v. Case B       | 2024 | Justice D. Y. C         | ... |
| Case C v. Case D       | 2024 | Justice D. Y. C         | ... |
| Case E v. Case F       | 2024 | Justice Hemant Gupta    | ... |
```

**Step 3: Upload to Elasticsearch**
```bash
# Terminal 3
python3 elasticsearch_upload.py
```

**Output:**
```
📖 Loading Excel file: tests.xlsx
✅ Loaded 3 rows from Excel file
📝 Uploading all rows; Elasticsearch will assign document IDs
📤 Starting bulk upload of 3 documents to index: graphdb
✅ Successfully uploaded 3 documents
```

**Step 4: Wait for Auto-Processing (or Trigger Manually)**

**Option A: Wait (auto-processor runs every 60 seconds)**
```
[Check Terminal 2 logs]
2025-11-06 13:01:00 - INFO - ⏱️  [Auto-Processor] Checking for new documents...
2025-11-06 13:01:01 - INFO - 📖 Found 3 unprocessed documents
2025-11-06 13:01:01 - INFO - 🔄 Processing unprocessed documents...
```

**Option B: Trigger manually**
```bash
curl -X POST http://localhost:8003/process
```

**Step 5: Monitor Processing**

Check status:
```bash
curl http://localhost:8003/status
```

**During processing:**
```json
{
  "is_processing": true,
  "current_progress": "Generating RDF triples..."
}
```

**After processing:**
```json
{
  "is_processing": false,
  "last_run_status": "success",
  "unprocessed_documents": 0,
  "processed_documents": 3
}
```

**Step 6: Verify RDF Generation**

Check the RDF folder:
```bash
ls -la rdf/
```

**Output:**
```
rdf/judgments_backup_20251106_130100.rdf  <- Backup created
rdf/README.md
```

Note: `judgments.rdf` was deleted after upload (cleanup mode)

**Step 7: Query Dgraph to Verify**

```bash
# Count judgments
curl -X POST http://localhost:8180/query -d '{
  count(func: type(Judgment)) {
    count(uid)
  }
}'
```

**Response:**
```json
{
  "data": {
    "count": [
      {
        "count": 3
      }
    ]
  }
}
```

**Query judge relationships:**
```bash
curl -X POST http://localhost:8180/query -d '{
  judge(func: eq(name, "Justice D. Y. Chandrachud")) {
    name
    ~judged_by {
      title
    }
  }
}'
```

**Response:**
```json
{
  "data": {
    "judge": [
      {
        "name": "Justice D. Y. Chandrachud",
        "~judged_by": [
          {"title": "Case A v. Case B"},
          {"title": "Case C v. Case D"}
        ]
      }
    ]
  }
}
```

✅ **Success!** 2 cases linked to same judge (no duplicate judge nodes!)

---

## 10. Recent Updates & Bug Fixes

### 🐛 Critical Bug Fix: Citation-Title Duplication (November 6, 2025)

**Issue Reported**: "Title agar citation me aya to usko different node create kar rha hai"  
(If a title appears as a citation, it was creating a different node)

#### The Problem

When a case was cited in one batch and then the actual judgment was uploaded in another batch, the system was creating **two different nodes** for the same case:

```
Batch 1 (Monday): Document A cites "Kesavananda Bharati v. State of Kerala"
  → Created node: <j_e0d69a27> (based on title hash)
  
Batch 2 (Tuesday): Upload actual "Kesavananda Bharati v. State of Kerala" 
  → Created node: <j_9f2a34bc> (based on doc_id hash)  ❌ DUPLICATE!
```

#### Root Cause

Three files were involved:

1. **`citation_relationship.py`**: Used `title` as `unique_key`
   ```python
   citation_node = create_node_id('judgment', unique_key=citation_title)
   ```

2. **`incremental_processor.py`**: Used `doc_id` as `unique_key` ❌
   ```python
   judgment_node = create_node_id('judgment', unique_key=doc_id)  # BUG!
   ```

3. **Result**: Same title → Different `unique_key` → Different hash → Different ID → Duplicate!

#### The Fix

**Modified Files:**

1. **`utils.py`** (Line ~155):
   ```python
   node_type_map = {
       'judgment': 'j',
       'citation': 'j',  # ✅ Unified prefix (was 'c' before)
       # ...
   }
   # Added title normalization (lowercase, strip whitespace)
   normalized_key = unique_key.lower().strip()
   ```

2. **`citation_relationship.py`** (Line ~73):
   ```python
   # Changed to use 'judgment' type instead of 'citation'
   citation_node = create_node_id('judgment', unique_key=citation_title)
   ```

3. **`incremental_processor.py`** (Line ~210) - **⭐ CRITICAL FIX**:
   ```python
   # OLD (caused duplicates):
   # judgment_node = create_node_id('judgment', unique_key=doc_id)
   
   # NEW (fixed):
   judgment_node = create_node_id('judgment', unique_key=title)  # ✅
   ```

#### Verification

**Test Results** (all passed ✅):
```bash
$ python3 test_citation_unification.py

🎉 ALL TESTS PASSED!
✅ Citation-Judgment Unification
✅ Real-World Scenario  
✅ Title Normalization
✅ Judge ID Consistency
```

**Real-World Test**:
```
Citation "Case A v. Case B"        → ID: j_136e32b4
Judgment "Case A v. Case B"        → ID: j_136e32b4  ✅ SAME!
Judgment "case a v. case b"        → ID: j_136e32b4  ✅ SAME! (normalized)
Judgment " Case A v. Case B "      → ID: j_136e32b4  ✅ SAME! (trimmed)
```

#### Impact & Benefits

**Before Fix**:
- ❌ Duplicate nodes for same case
- ❌ Data inconsistency
- ❌ Broken relationships
- ❌ Query confusion

**After Fix**:
- ✅ Single node per case (merged automatically)
- ✅ Data consistency maintained
- ✅ Relationships preserved
- ✅ Clean, accurate queries
- ✅ Case-insensitive matching
- ✅ Whitespace-tolerant matching

#### Additional Documentation

For complete details, see:
- **`CITATION_TITLE_UNIFICATION.md`** - Original strategy document
- **`CITATION_TITLE_FIX_VERIFICATION.md`** - Detailed fix verification
- **`test_citation_unification.py`** - Comprehensive test suite

---

### 📝 Other Recent Updates

#### Enhanced Logging
- Added detailed progress messages during RDF generation
- Clear status indicators for each processing phase
- Better error messages with context

#### Improved Error Handling
- Graceful handling of missing fields
- Better validation for list fields (citations, judges, advocates)
- Auto-recovery from common issues

#### Performance Optimizations
- Optimized title mapping for citation cross-references
- Reduced memory usage for large batches
- Faster MD5 hash generation with caching

#### Code Organization
- Modular relationship handlers (`relationships/` package)
- Cleaner separation of concerns
- Better code reusability

---

## 11. Troubleshooting & FAQ

### Common Issues

#### Issue 1: "No such file or directory: 'rdf/judgments.rdf'"

**Cause**: RDF directory doesn't exist

**Solution**: Directory is now auto-created, but if issue persists:
```bash
mkdir -p rdf
```

**Fixed in code** (`incremental_processor.py`):
```python
output_file.parent.mkdir(parents=True, exist_ok=True)
```

#### Issue 2: "Cannot connect to Elasticsearch"

**Check if ES is running:**
```bash
curl http://localhost:9200
```

**If not running, start it:**
```bash
docker run -d -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.11.0
```

#### Issue 3: "Cannot connect to Dgraph"

**Check if Dgraph is running:**
```bash
curl http://localhost:8180/health
```

**Check Docker container:**
```bash
docker ps | grep dgraph
```

**If not running, start it:**
```bash
docker run -it -p 8180:8080 -p 8181:8081 -p 8000:8000 \
  -v ~/dgraph_data:/dgraph \
  --name dgraph-standalone \
  dgraph/dgraph:v23.1.0
```

#### Issue 4: "Duplicate judges appearing in Dgraph"

**Cause**: Upsert not working properly

**Check schema:**
```bash
curl http://localhost:8180/alter -d '{schema{}}'
```

**Verify `judge_id` has `@upsert`**

**Re-upload schema if needed:**
```bash
curl -X POST localhost:8180/alter -d @rdf.schema
```

#### Issue 5: "Processing stuck at 'Uploading to Dgraph'"

**Check Docker container access:**
```bash
docker exec -it dgraph-standalone ls /dgraph/
```

**Should see:**
```
judgments.rdf
rdf.schema
```

**If files not appearing**, check volume mount:
```bash
docker inspect dgraph-standalone | grep -A 5 Mounts
```

### FAQ

#### Q: How do I reset everything and start fresh?

**A:**
```bash
# 1. Drop all Dgraph data
curl -X POST http://localhost:8180/alter -d '{"drop_all": true}'

# 2. Re-upload schema
curl -X POST http://localhost:8180/alter -d @rdf.schema

# 3. Reset Elasticsearch processed status
python3 -c "
from elasticsearch_handler import ElasticsearchHandler
es = ElasticsearchHandler()
es.reset_processed_status()
"

# 4. Process all documents
curl -X POST http://localhost:8003/process
```

#### Q: How do I process only specific documents?

**A:**
```bash
curl -X POST http://localhost:8003/process \
  -H "Content-Type: application/json" \
  -d '{
    "doc_ids": ["doc_id_1", "doc_id_2"]
  }'
```

#### Q: How do I keep RDF files without cleanup?

**A:**
```bash
curl -X POST http://localhost:8003/process \
  -H "Content-Type: application/json" \
  -d '{
    "cleanup_rdf": false
  }'
```

#### Q: Can I see what's in the RDF file before upload?

**A:**
```bash
# Set cleanup_rdf=false, then:
cat rdf/judgments.rdf | head -50
```

#### Q: How do I verify no duplicates exist?

**A:**
```bash
# Count judge nodes
curl -X POST http://localhost:8180/query -d '{
  judges(func: type(Judge)) {
    total: count(uid)
  }
}'

# List all judge names
curl -X POST http://localhost:8180/query -d '{
  judges(func: type(Judge)) {
    name
  }
}'
```

**Check for duplicate names manually**

#### Q: I have duplicate judgment nodes for same case. How do I fix this?

**A: This was a known bug (fixed in v2.1). Two scenarios:**

**Scenario 1: Old data (before fix)**
```bash
# You may have duplicates from before the fix was applied
# Solution: Re-upload all data after fix

# 1. Drop all data
curl -X POST http://localhost:8180/alter -d '{"drop_all": true}'

# 2. Re-upload schema
curl -X POST http://localhost:8180/alter -d @rdf.schema

# 3. Reset all documents to unprocessed
python3 -c "
from elasticsearch_handler import ElasticsearchHandler
es = ElasticsearchHandler()
es.reset_processed_status()
"

# 4. Reprocess everything with fix applied
curl -X POST http://localhost:8003/process
```

**Scenario 2: New data (after fix)**
```bash
# Verify fix is applied
grep -n "create_node_id('judgment', unique_key=title)" incremental_processor.py

# Should show line ~210 with title (not doc_id)
# If shows doc_id, the fix is not applied

# Run verification test
python3 test_citation_unification.py

# Should show: "🎉 ALL TESTS PASSED!"
```

**To check if you have duplicates:**
```graphql
{
  # Query for a specific title
  judgments(func: eq(title, "Your Case Title Here")) {
    uid
    judgment_id
    title
    doc_id
  }
}

# If returns MORE THAN 1 result → You have duplicates
```

#### Q: What's the difference between `doc_id` and `judgment_id`?

**A:**

- **`doc_id`**: 
  - Elasticsearch document ID (e.g., "ES_2024_001")
  - Used for tracking in Elasticsearch
  - Stored as a predicate in Dgraph: `<j_xxx> <doc_id> "ES_2024_001" .`
  - **NOT used for node ID generation** (after v2.1 fix)

- **`judgment_id`**:
  - Dgraph node ID (e.g., "j_e0d69a27")
  - Generated from MD5 hash of **title**
  - Used as the `uid` for the judgment node: `<j_e0d69a27>`
  - Ensures same title always gets same ID (prevents duplicates)

**Example:**
```rdf
<j_e0d69a27> <dgraph.type> "Judgment" .
<j_e0d69a27> <judgment_id> "j_e0d69a27" .           ← Node ID
<j_e0d69a27> <title> "Case A v. Case B" .            ← Used to generate ID
<j_e0d69a27> <doc_id> "ES_2024_001" .                ← ES tracking only
```

#### Q: Why did the system use doc_id before the fix?

**A: Historical reason + oversight:**

The original design used `doc_id` for judgment nodes because:
1. It was thought to be more "stable" (ES-assigned)
2. Each batch had unique doc_ids

**But this created a problem:**
- Citations don't have `doc_id` (they're not in ES yet)
- Citations use `title` to generate IDs
- Same case → Different unique_key → Different ID → **Duplicates!** ❌

**The fix:** Use `title` for both citations and judgments → Same ID → No duplicates ✅

#### Q: How do I add a new relationship type?

**A: Follow these steps:**

1. **Add to schema** (`rdf.schema`):
```
type Judgment {
  ...
  new_relationship  # Add here
}

type NewEntity {
  new_entity_id
  name
}

new_relationship: uid @reverse .
new_entity_id: string @index(exact) @upsert .
```

2. **Create handler** (`relationships/new_entity_relationship.py`):
```python
class NewEntityRelationshipHandler:
    def __init__(self):
        self.entity_nodes = {}
        self.rdf_lines = []
    
    def create_relationships(self, judgment):
        # Your logic here
        pass
```

3. **Import in `__init__.py`**:
```python
from .new_entity_relationship import NewEntityRelationshipHandler
```

4. **Use in processor** (`incremental_processor.py`):
```python
self.new_entity_handler = NewEntityRelationshipHandler()

# In _process_new_entity_relationships():
triples = self.new_entity_handler.create_relationships(judgment)
```

---

## Practical Example: How The System Works

Let's trace through a real example to understand the four key features:

### Scenario: Processing 3 New Judgments

**Initial State:**
- Elasticsearch: 3 new documents (processed_to_dgraph: false)
- Dgraph: Already has 5 judgments with Justice D. Y. Chandrachud as judge

**New Documents:**
```
Document A: Judge = "Justice D. Y. Chandrachud" (already exists in Dgraph)
Document B: Judge = "Justice D. Y. Chandrachud" (already exists in Dgraph)
Document C: Judge = "Justice Hemant Gupta" (new judge)
```

---

### Feature 1: ✅ Incremental Processing (Only New Documents)

**Function: `load_unprocessed_documents()`** in `elasticsearch_handler.py`

```python
def load_unprocessed_documents(self) -> pd.DataFrame:
    # Query Elasticsearch
    query = {
        "query": {
            "bool": {
                "must_not": [
                    {"term": {"processed_to_dgraph": True}}
                ]
            }
        }
    }
    
    # Execute search
    response = self.es.search(index=self.index_name, body=query)
    
    # Returns ONLY unprocessed documents
    return documents_dataframe
```

**Execution Trace:**
```
Step 1: Query Elasticsearch
  └─> SELECT * WHERE processed_to_dgraph = false
  
Step 2: Results Found
  ├─> Document A (doc_id: "abc123", title: "Case A v. Case B")
  ├─> Document B (doc_id: "def456", title: "Case C v. Case D")
  └─> Document C (doc_id: "ghi789", title: "Case E v. Case F")

Step 3: Skip Already Processed
  └─> 5 previous documents with processed_to_dgraph=true are IGNORED
  
Result: Returns DataFrame with 3 rows (only new documents)
```

**Why This Matters:**
- ❌ Without this: Would reprocess all 8 documents every time
- ✅ With this: Only processes 3 new documents (faster, efficient)

---

### Feature 2: ✅ Duplicate Prevention (Content-Based IDs)

**Function: `create_node_id()`** in `utils.py` + **`_get_or_create_judge_node()`** in `judge_relationship.py`

#### Part A: Generating Stable IDs

```python
# In utils.py
def create_node_id(node_type: str, unique_key: str = None) -> str:
    prefix = node_type_map[node_type]  # 'judge'
    hash_value = hashlib.md5(unique_key.encode()).hexdigest()[:8]
    return f"{prefix}_{hash_value}"
```

**Execution Trace for Document A:**
```
Step 1: Processing Document A
  └─> Judge Name: "Justice D. Y. Chandrachud"

Step 2: Generate Judge ID
  ├─> Input: node_type='judge', unique_key='Justice D. Y. Chandrachud'
  ├─> MD5 Hash: md5('Justice D. Y. Chandrachud') = 'ea7adefd92a1...'
  ├─> Take first 8 chars: 'ea7adefd'
  └─> Return: 'judge_ea7adefd'

Step 3: Document B encounters SAME judge
  ├─> Input: unique_key='Justice D. Y. Chandrachud'
  ├─> MD5 Hash: SAME = 'ea7adefd92a1...'
  └─> Return: 'judge_ea7adefd' ← SAME ID!

Step 4: Document C encounters DIFFERENT judge
  ├─> Input: unique_key='Justice Hemant Gupta'
  ├─> MD5 Hash: DIFFERENT = '9c1212fb45e2...'
  └─> Return: 'judge_9c1212fb' ← NEW ID!
```

#### Part B: Preventing Duplicates in RDF File

```python
# In judge_relationship.py
def _get_or_create_judge_node(self, judge_name: str) -> str:
    # Generate stable ID
    judge_node = create_node_id('judge', unique_key=judge_name)
    
    # Check if already created in THIS batch
    if judge_node in self.judge_nodes:
        return judge_node  # REUSE! Don't create duplicate
    
    # Create new judge node
    self.judge_nodes[judge_node] = judge_name
    self.rdf_lines.append(f'{judge_node} <dgraph.type> "Judge" .')
    self.rdf_lines.append(f'{judge_node} <judge_id> "{judge_node}" .')
    self.rdf_lines.append(f'{judge_node} <name> "{judge_name}" .')
    
    return judge_node
```

**Execution Trace:**
```
Processing Document A:
  ├─> create_node_id() → 'judge_ea7adefd'
  ├─> Check self.judge_nodes: {} (empty)
  ├─> NOT FOUND → Create judge node
  ├─> Add to self.judge_nodes: {'judge_ea7adefd': 'Justice D. Y. Chandrachud'}
  └─> Add RDF triples:
        <judge_ea7adefd> <dgraph.type> "Judge" .
        <judge_ea7adefd> <judge_id> "judge_ea7adefd" .
        <judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .

Processing Document B:
  ├─> create_node_id() → 'judge_ea7adefd' (SAME!)
  ├─> Check self.judge_nodes: {'judge_ea7adefd': '...'} 
  ├─> FOUND! → Return existing ID
  └─> NO NEW TRIPLES CREATED ← Prevented duplicate!

Processing Document C:
  ├─> create_node_id() → 'judge_9c1212fb' (DIFFERENT!)
  ├─> Check self.judge_nodes: {'judge_ea7adefd': '...'}
  ├─> NOT FOUND → Create new judge node
  └─> Add RDF triples:
        <judge_9c1212fb> <dgraph.type> "Judge" .
        <judge_9c1212fb> <judge_id> "judge_9c1212fb" .
        <judge_9c1212fb> <name> "Justice Hemant Gupta" .

Final RDF File:
  ├─> Only 2 judge nodes (not 3!)
  ├─> 3 judgment nodes
  └─> 3 relationships pointing to the 2 judges
```

**Generated RDF:**
```rdf
# Document A (Judgment)
<j_abc123> <dgraph.type> "Judgment" .
<j_abc123> <title> "Case A v. Case B" .

# Document B (Judgment)
<j_def456> <dgraph.type> "Judgment" .
<j_def456> <title> "Case C v. Case D" .

# Document C (Judgment)
<j_ghi789> <dgraph.type> "Judgment" .
<j_ghi789> <title> "Case E v. Case F" .

# Judge 1 (created for Document A, REUSED for Document B)
<judge_ea7adefd> <dgraph.type> "Judge" .
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .

# Judge 2 (created for Document C)
<judge_9c1212fb> <dgraph.type> "Judge" .
<judge_9c1212fb> <judge_id> "judge_9c1212fb" .
<judge_9c1212fb> <name> "Justice Hemant Gupta" .

# Relationships
<j_abc123> <judged_by> <judge_ea7adefd> .  ← Document A → Judge 1
<j_def456> <judged_by> <judge_ea7adefd> .  ← Document B → Judge 1 (SAME!)
<j_ghi789> <judged_by> <judge_9c1212fb> .  ← Document C → Judge 2
```

---

### Feature 3: ✅ Entity Linking (Links to Existing Entities)

**Function: `_upload_to_dgraph()`** in `incremental_processor.py`

**Dgraph Upsert Process:**

```python
def _upload_to_dgraph(self) -> None:
    upsert_predicates = [
        "judgment_id", "doc_id", "judge_id", 
        "advocate_id", "outcome_id", "case_duration_id"
    ]
    
    command = [
        "docker", "exec", "-i", "dgraph-standalone",
        "dgraph", "live",
        "--files", "/dgraph/judgments.rdf",
        "--upsert-predicates", ",".join(upsert_predicates)
    ]
    
    subprocess.run(command)
```

**Execution Trace:**

```
Before Upload - Dgraph State:
  └─> Existing Nodes:
       ├─> judge_ea7adefd (UID: 0x1a2b) - "Justice D. Y. Chandrachud"
       │    └─> ~judged_by: [5 previous judgments]
       └─> 15 other judges

Step 1: Upload New RDF File
  └─> Docker command executes dgraph live with --upsert-predicates

Step 2: Dgraph Processes judge_ea7adefd
  ├─> Reads: <judge_ea7adefd> <judge_id> "judge_ea7adefd" .
  ├─> Query: Does judge_id="judge_ea7adefd" exist?
  ├─> Result: YES! Found UID: 0x1a2b
  ├─> Action: UPDATE (merge predicates into existing node)
  └─> NO NEW NODE CREATED ← Linked to existing!

Step 3: Dgraph Processes judge_9c1212fb
  ├─> Reads: <judge_9c1212fb> <judge_id> "judge_9c1212fb" .
  ├─> Query: Does judge_id="judge_9c1212fb" exist?
  ├─> Result: NO! Not found
  ├─> Action: INSERT (create new node)
  └─> New UID assigned: 0x9f3c

Step 4: Dgraph Processes Relationships
  ├─> <j_abc123> <judged_by> <judge_ea7adefd>
  │    └─> Links Document A to EXISTING judge (UID: 0x1a2b)
  ├─> <j_def456> <judged_by> <judge_ea7adefd>
  │    └─> Links Document B to EXISTING judge (UID: 0x1a2b)
  └─> <j_ghi789> <judged_by> <judge_9c1212fb>
       └─> Links Document C to NEW judge (UID: 0x9f3c)

After Upload - Dgraph State:
  └─> Updated Nodes:
       ├─> judge_ea7adefd (UID: 0x1a2b) ← SAME UID!
       │    └─> ~judged_by: [5 old + 2 new = 7 judgments]
       ├─> judge_9c1212fb (UID: 0x9f3c) ← NEW!
       │    └─> ~judged_by: [1 judgment]
       └─> 15 other judges (unchanged)
```

**Visual Representation:**

```
┌─────────────────────────────────────────────────────────────┐
│               Before Upload (Dgraph State)                  │
└─────────────────────────────────────────────────────────────┘

Judge: Justice D. Y. Chandrachud (UID: 0x1a2b)
  └─> Judged Cases:
       ├─> "Previous Case 1" (2023)
       ├─> "Previous Case 2" (2023)
       ├─> "Previous Case 3" (2024)
       ├─> "Previous Case 4" (2024)
       └─> "Previous Case 5" (2024)

┌─────────────────────────────────────────────────────────────┐
│               After Upload (Dgraph State)                   │
└─────────────────────────────────────────────────────────────┘

Judge: Justice D. Y. Chandrachud (UID: 0x1a2b) ← SAME UID!
  └─> Judged Cases:
       ├─> "Previous Case 1" (2023)
       ├─> "Previous Case 2" (2023)
       ├─> "Previous Case 3" (2024)
       ├─> "Previous Case 4" (2024)
       ├─> "Previous Case 5" (2024)
       ├─> "Case A v. Case B" (2024)  ← NEW! Linked to existing
       └─> "Case C v. Case D" (2024)  ← NEW! Linked to existing

Judge: Justice Hemant Gupta (UID: 0x9f3c) ← NEW NODE!
  └─> Judged Cases:
       └─> "Case E v. Case F" (2024)  ← NEW!
```

**Why This Matters:**
- ❌ Without upsert: Would create duplicate "Justice D. Y. Chandrachud" nodes
- ✅ With upsert: New cases automatically link to existing judge node

---

### Feature 4: ✅ Clean Workspace (RDF Auto-Cleanup)

**Functions:** 
1. `_write_rdf_file()` - Writes fresh RDF
2. `_upload_to_dgraph()` - Uploads to Dgraph
3. `_cleanup_rdf_file()` - Backs up and deletes

**Execution Trace:**

```python
# In incremental_processor.py
def process_incremental(self, cleanup_rdf: bool = True):
    # ... processing steps ...
    
    # Step 1: Write fresh RDF file
    self._write_rdf_file(append_mode=False)
    
    # Step 2: Upload to Dgraph
    self._upload_to_dgraph()
    
    # Step 3: Cleanup (if enabled)
    if cleanup_rdf:
        self._cleanup_rdf_file()
```

#### Step 1: Write Fresh RDF File

```python
def _write_rdf_file(self, append_mode: bool = False) -> None:
    output_file = Path(self.output_config['rdf_file'])
    
    # Ensure directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write mode: 'w' (fresh) or 'a' (append)
    mode = 'a' if append_mode else 'w'
    
    with open(output_file, mode, encoding="utf-8") as f:
        for line in self.rdf_lines:
            f.write(line + "\n")
```

**Execution:**
```
Step 1: Check Directory
  ├─> Path: rdf/judgments.rdf
  ├─> Parent: rdf/
  ├─> exists? Yes
  └─> Continue

Step 2: Open File (mode='w' - fresh write)
  └─> This OVERWRITES any existing file

Step 3: Write All RDF Lines
  ├─> Line 1: <j_abc123> <dgraph.type> "Judgment" .
  ├─> Line 2: <j_abc123> <title> "Case A v. Case B" .
  ├─> ...
  └─> Line 50: <j_ghi789> <judged_by> <judge_9c1212fb> .

Result: rdf/judgments.rdf created with 50 triples
```

#### Step 2: Upload to Dgraph

```
Step 1: Execute Docker Command
  └─> dgraph live --files /dgraph/judgments.rdf --upsert-predicates ...

Step 2: Dgraph Processes File
  ├─> Reads all 50 triples
  ├─> Applies upsert logic
  └─> Updates/Creates nodes

Step 3: Upload Complete
  └─> All data now safely in Dgraph
```

#### Step 3: Cleanup RDF File

```python
def _cleanup_rdf_file(self) -> None:
    output_file = Path(self.output_config['rdf_file'])
    
    if not output_file.exists():
        return
    
    # Create backup with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"judgments_backup_{timestamp}.rdf"
    backup_path = output_file.parent / backup_name
    
    # Copy to backup
    shutil.copy2(output_file, backup_path)
    
    # Delete original
    output_file.unlink()
```

**Execution:**
```
Step 1: Check File Exists
  ├─> Path: rdf/judgments.rdf
  └─> Exists: Yes

Step 2: Generate Timestamp
  └─> datetime.now() = "2025-11-06 13:45:30"
  └─> Formatted: "20251106_134530"

Step 3: Create Backup Name
  └─> "judgments_backup_20251106_134530.rdf"

Step 4: Copy File
  ├─> Source: rdf/judgments.rdf
  ├─> Destination: rdf/judgments_backup_20251106_134530.rdf
  └─> Copy complete

Step 5: Delete Original
  └─> os.remove(rdf/judgments.rdf)

Final State:
  ├─> rdf/judgments.rdf ← DELETED
  └─> rdf/judgments_backup_20251106_134530.rdf ← BACKUP CREATED
```

**Workspace Timeline:**

```
Before Processing:
rdf/
  ├── README.md
  ├── judgments_backup_20251106_120000.rdf (old backup 1)
  └── judgments_backup_20251106_130000.rdf (old backup 2)

During Processing (after _write_rdf_file):
rdf/
  ├── README.md
  ├── judgments.rdf ← NEW FILE (50 triples)
  ├── judgments_backup_20251106_120000.rdf
  └── judgments_backup_20251106_130000.rdf

After Upload (data in Dgraph):
rdf/
  ├── README.md
  ├── judgments.rdf ← Still exists
  ├── judgments_backup_20251106_120000.rdf
  └── judgments_backup_20251106_130000.rdf

After Cleanup:
rdf/
  ├── README.md
  ├── judgments_backup_20251106_120000.rdf (old backup 1)
  ├── judgments_backup_20251106_130000.rdf (old backup 2)
  └── judgments_backup_20251106_134530.rdf ← NEW BACKUP
  
  judgments.rdf ← DELETED (data safe in Dgraph)
```

**Why This Matters:**
- ✅ Keeps workspace clean (no large RDF files lying around)
- ✅ Maintains history (timestamped backups)
- ✅ Data safety (backup before deletion)
- ✅ Fast processing (small RDF files every time)

---

### Complete Flow Summary

**Input:** 3 new documents in Elasticsearch

**Step-by-Step Execution:**

```
┌──────────────────────────────────────────────────────────┐
│  1. INCREMENTAL PROCESSING                               │
└──────────────────────────────────────────────────────────┘
load_unprocessed_documents()
  └─> Returns: 3 documents (ignores 5 already processed)

┌──────────────────────────────────────────────────────────┐
│  2. DUPLICATE PREVENTION                                 │
└──────────────────────────────────────────────────────────┘
For each document:
  create_node_id('judge', 'Justice D. Y. Chandrachud')
    └─> Returns: 'judge_ea7adefd' (SAME for Doc A & B)
  
  _get_or_create_judge_node('Justice D. Y. Chandrachud')
    ├─> Doc A: Creates node (first time)
    ├─> Doc B: Returns existing ID (no duplicate!)
    └─> Doc C: Creates new node for different judge

Result: 2 judge nodes in RDF (not 3)

┌──────────────────────────────────────────────────────────┐
│  3. ENTITY LINKING                                       │
└──────────────────────────────────────────────────────────┘
_upload_to_dgraph() with --upsert-predicates
  ├─> Dgraph checks: judge_ea7adefd exists? YES
  ├─> Action: Links to existing UID (0x1a2b)
  └─> Result: No duplicate judge in Dgraph

┌──────────────────────────────────────────────────────────┐
│  4. CLEAN WORKSPACE                                      │
└──────────────────────────────────────────────────────────┘
_cleanup_rdf_file()
  ├─> Backup: judgments_backup_20251106_134530.rdf
  └─> Delete: judgments.rdf

Final State:
  ├─> Elasticsearch: 3 docs marked as processed
  ├─> Dgraph: 3 new judgments linked to 1 existing + 1 new judge
  └─> Workspace: Clean (only backup files)
```

**Verification Commands:**

```bash
# 1. Check Elasticsearch processed status
curl -X POST http://localhost:9200/graphdb/_search -H 'Content-Type: application/json' -d '{
  "query": {"term": {"processed_to_dgraph": true}}
}'
# Returns: 8 documents (5 old + 3 new)

# 2. Query Dgraph for judge
curl -X POST http://localhost:8180/query -d '{
  judge(func: eq(judge_id, "judge_ea7adefd")) {
    name
    ~judged_by {
      title
      count(uid)
    }
  }
}'
# Returns: 7 cases (5 old + 2 new)

# 3. Check workspace
ls -la rdf/
# Shows: Only backup files, no judgments.rdf
```

---

## Summary

This system provides a complete solution for building a legal judgment knowledge graph with advanced features:

### ✅ Core Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Duplicate Prevention** | Content-based IDs + Dgraph upsert | ✅ Working |
| **Incremental Processing** | Only new documents processed | ✅ Working |
| **Entity Linking** | New judgments link to existing entities | ✅ Working |
| **Citation-Title Unification** | Citations and judgments merge automatically | ✅ Fixed (v2.1) |
| **Clean Workspace** | RDF files auto-cleaned after upload | ✅ Working |
| **API Access** | REST API for all operations | ✅ Working |
| **Auto-Processing** | Background worker for automatic updates | ✅ Working |
| **Stable IDs** | Same entity always gets same ID across batches | ✅ Working |
| **Relationship Management** | Modular handlers for each entity type | ✅ Working |

### 🔑 Key Innovations

1. **MD5 Hash-Based Stable IDs**  
   Same entity content → Same ID → No duplicates across batches
   ```python
   "Justice D. Y. Chandrachud" → <judge_ea7adefd> (always!)
   ```

2. **Title-Based Judgment IDs** (v2.1 Fix)  
   Citations and actual judgments use same ID generation
   ```python
   Citation: "Case X" → <j_abc123>
   Judgment: "Case X" → <j_abc123> (same!)
   Result: Merged by Dgraph upsert ✅
   ```

3. **Incremental Processing**  
   Only unprocessed documents → Faster, more efficient
   ```python
   5000 documents total, 10 new → Process only 10!
   ```

4. **Smart Entity Reuse**  
   Link to existing entities instead of creating duplicates
   ```python
   Judge already exists → Link to it, don't recreate
   ```

### 📊 System Architecture

```
┌─────────────────┐
│  Excel Files    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│ Elasticsearch   │◄─────┤ elasticsearch   │
│ (Data Store)    │      │ _upload.py      │
└────────┬────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│ FastAPI App     │◄─────┤ HTTP Requests   │
│ (REST API)      │      │ (Port 8003)     │
└────────┬────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│ Incremental     │◄─────┤ Relationship    │
│ Processor       │      │ Handlers        │
└────────┬────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐
│ RDF Generator   │
│ (judgments.rdf) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│ Dgraph Live     │◄─────┤ Docker          │
│ Loader (Upsert) │      │ Container       │
└────────┬────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Dgraph Database │
│ (Knowledge Graph│
└─────────────────┘
```

### 🚀 Quick Start Commands

```bash
# 1. Start infrastructure
docker run -it -p 8180:8080 -p 8181:8081 -v ~/dgraph_data:/dgraph dgraph/dgraph:v23.1.0
docker run -d -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.11.0

# 2. Upload schema
curl -X POST localhost:8180/alter -d @rdf.schema

# 3. Upload data to Elasticsearch
python3 elasticsearch_upload.py

# 4. Start FastAPI
uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload

# 5. Process documents
curl -X POST http://localhost:8003/process

# 6. Query results
curl -X POST http://localhost:8180/query -d '{
  allJudgments(func: type(Judgment)) {
    uid
    title
    judged_by { name }
  }
}'
```

### 📚 Additional Documentation

| Document | Purpose |
|----------|---------|
| `CITATION_TITLE_UNIFICATION.md` | Citation-title unification strategy |
| `CITATION_TITLE_FIX_VERIFICATION.md` | Detailed fix verification |
| `INCREMENTAL_PROCESSING_GUIDE.md` | Incremental processing deep dive |
| `test_citation_unification.py` | Comprehensive test suite |
| `querry_cli.txt` | Sample Dgraph queries |
| `docker_information.txt` | Docker setup details |
| `rdf/README.md` | RDF folder documentation |

### 🐛 Recent Bug Fixes (v2.1)

**Citation-Title Duplication** (November 6, 2025)
- **Issue**: Citations and judgments created different nodes for same case
- **Root Cause**: Different `unique_key` used (doc_id vs title)
- **Fix**: Changed judgment ID generation to use title (consistent with citations)
- **Impact**: All new uploads now prevent duplicates automatically
- **Verification**: All tests passing ✅

### 🔧 Support & Troubleshooting

**Log Files**:
- `rdf_generator.log` - Processing logs
- `elasticsearch_upload.log` - Upload logs

**Health Checks**:
```bash
# Check Elasticsearch
curl http://localhost:9200/_cluster/health

# Check Dgraph
curl http://localhost:8180/health

# Check FastAPI
curl http://localhost:8003/health
```

**Common Issues**: See [Troubleshooting & FAQ](#11-troubleshooting--faq) section above

---

**Version**: 2.1  
**Last Updated**: November 6, 2025  
**Status**: Production Ready ✅  
**License**: MIT  
**Author**: Anish DF
