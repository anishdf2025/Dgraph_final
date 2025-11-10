# 🔄 Complete Guide: Duplicate Prevention & Hash-Based ID System

**Last Updated**: November 6, 2025  
**Version**: 2.1  
**Author**: Anish DF

---

## 📋 Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [The Duplicate Challenge](#2-the-duplicate-challenge)
3. [Hash-Based Solution Architecture](#3-hash-based-solution-architecture)
4. [How Hash IDs Are Generated](#4-how-hash-ids-are-generated)
5. [Different Entity Types & Their Hash Maps](#5-different-entity-types--their-hash-maps)
6. [RDF File Generation Process](#6-rdf-file-generation-process)
7. [Multi-Batch Processing & Upsert Mechanism](#7-multi-batch-processing--upsert-mechanism)
8. [Citation-Title Unification (Critical Feature)](#8-citation-title-unification-critical-feature)
9. [File-by-File Explanation](#9-file-by-file-explanation)
10. [Real-World Scenarios](#10-real-world-scenarios)
11. [Verification & Testing](#11-verification--testing)

---

## 1. Problem Statement

### What Problem Are We Solving?

When processing legal judgments in multiple batches, we need to ensure:

1. ✅ **No Duplicate Nodes**: Same entity (judge, advocate, case) should create only ONE node
2. ✅ **Stable References**: Entity referenced in Batch 1 should link to same entity in Batch 2
3. ✅ **Cross-Batch Relationships**: New documents should link to existing entities
4. ✅ **Citation Unification**: Cited cases and actual cases with same title should be ONE node

### Why Is This Hard?

```
❌ PROBLEM WITH COUNTER-BASED IDs:

Batch 1:
  <judge1> = "Justice D. Y. Chandrachud"
  <judge2> = "Justice Hemant Gupta"

Batch 2: (New batch, counters reset!)
  <judge1> = "Justice S. A. Nazeer"  ← CONFLICT! Same ID, different person!
  <judge2> = "Justice D. Y. Chandrachud"  ← DUPLICATE! Already exists as judge1 in Batch 1
```

---

## 2. The Duplicate Challenge

### Scenario: Multi-Batch Document Upload

#### Initial Upload (Batch 1)

```
Excel File 1:
  - Case A: Judged by "Justice D. Y. Chandrachud"
  - Case B: Judged by "Justice Hemant Gupta"
  - Case C: Judged by "Justice D. Y. Chandrachud" (same judge!)
```

#### New Upload (Batch 2) - 30 Days Later

```
Excel File 2:
  - Case D: Judged by "Justice D. Y. Chandrachud" (same judge from Batch 1!)
  - Case E: Judged by "Justice S. A. Nazeer" (new judge)
  - Case D cites "Case A" from Batch 1
```

### What Should Happen?

```
✅ EXPECTED BEHAVIOR:

Dgraph After Batch 1:
  <judge_ea7adefd> "Justice D. Y. Chandrachud"
  <judge_9c1212fb> "Justice Hemant Gupta"
  <j_abc12345> "Case A" → judged_by → <judge_ea7adefd>
  <j_def67890> "Case B" → judged_by → <judge_9c1212fb>
  <j_ghi11223> "Case C" → judged_by → <judge_ea7adefd>

Dgraph After Batch 2:
  <judge_ea7adefd> "Justice D. Y. Chandrachud" ← SAME NODE (not duplicated!)
  <judge_9c1212fb> "Justice Hemant Gupta"
  <judge_4f5e6d7c> "Justice S. A. Nazeer" ← NEW NODE
  <j_abc12345> "Case A"
  <j_def67890> "Case B"
  <j_ghi11223> "Case C"
  <j_jkl44556> "Case D" → judged_by → <judge_ea7adefd> ← Links to existing judge!
  <j_jkl44556> → cites → <j_abc12345> ← Links to existing case!
```

---

## 3. Hash-Based Solution Architecture

### Core Principle: Content-Based Identifiers

Instead of sequential counters, we use **MD5 hashes of content** to create stable IDs.

```python
# Same content → Same hash → Same ID → No duplicates!

"Justice D. Y. Chandrachud" → MD5 → "ea7adefd" → <judge_ea7adefd>
"Justice D. Y. Chandrachud" → MD5 → "ea7adefd" → <judge_ea7adefd> (SAME!)
```

### Why MD5 Hash?

1. **Deterministic**: Same input always produces same output
2. **Collision-Resistant**: Different inputs almost never produce same hash
3. **Stable Across Batches**: Same entity always gets same ID
4. **Compact**: 8-character truncated hash is short and readable

---

## 4. How Hash IDs Are Generated

### Location: `utils.py` → `create_node_id()` Function

```python
def create_node_id(node_type: str, counter: int = None, unique_key: str = None) -> str:
    """
    Create a standardized node ID using content-based hashing.
    
    CRITICAL FEATURES:
    1. Citations and judgments use SAME prefix 'j' (for unification)
    2. Normalizes input before hashing (lowercase, strip whitespace)
    3. Uses MD5 hash truncated to 8 characters
    4. Ensures same content → same ID across all batches
    
    Args:
        node_type: Type of node (judgment, citation, judge, advocate, etc.)
        unique_key: Content to hash (e.g., title for judgments, name for judges)
        
    Returns:
        str: Stable hash-based node ID (e.g., "judge_ea7adefd")
    """
    
    # Define node type prefixes
    node_type_map = {
        'judgment': 'j',
        'citation': 'j',  # ← UNIFIED! Citations use same prefix as judgments
        'judge': 'judge',
        'petitioner_advocate': 'petitioner_advocate',
        'respondant_advocate': 'respondant_advocate',
        'outcome': 'outcome',
        'case_duration': 'case_duration'
    }
    
    prefix = node_type_map.get(node_type, node_type)
    
    # Use hash-based ID if unique_key provided
    if unique_key:
        import hashlib
        
        # STEP 1: Normalize the unique_key
        normalized_key = unique_key.lower().strip()
        
        # STEP 2: Create MD5 hash
        hash_obj = hashlib.md5(normalized_key.encode())
        
        # STEP 3: Truncate to 8 characters
        hash_short = hash_obj.hexdigest()[:8]
        
        # STEP 4: Return formatted ID
        return f"{prefix}_{hash_short}"
    
    # Fallback to counter (backward compatibility)
    if counter is not None:
        return f"{prefix}{counter}"
    
    raise ValueError("Either counter or unique_key must be provided")
```

### Step-by-Step Example

```python
# Example: Creating Judge Node ID

Input: "Justice D. Y. Chandrachud"

Step 1 - Normalize:
  "justice d. y. chandrachud"  # Lowercase, stripped

Step 2 - Hash:
  MD5("justice d. y. chandrachud") = "ea7adefd123abc456def789..." (32 chars)

Step 3 - Truncate:
  "ea7adefd"  # First 8 characters

Step 4 - Format:
  "judge_ea7adefd"  # Final node ID

✅ Result: <judge_ea7adefd>
```

### Why Normalization?

```python
# WITHOUT normalization - DUPLICATES!
"Justice D. Y. Chandrachud" → hash1 → <judge_abc123>
"justice d. y. chandrachud" → hash2 → <judge_def456>  # DUPLICATE!
"  Justice D. Y. Chandrachud  " → hash3 → <judge_ghi789>  # DUPLICATE!

# WITH normalization - NO DUPLICATES!
"Justice D. Y. Chandrachud" → normalize → hash → <judge_ea7adefd>
"justice d. y. chandrachud" → normalize → hash → <judge_ea7adefd>  # SAME!
"  Justice D. Y. Chandrachud  " → normalize → hash → <judge_ea7adefd>  # SAME!
```

---

## 5. Different Entity Types & Their Hash Maps

### 5.1 Judgment Nodes (Cases)

**Hash Key**: Case Title  
**Prefix**: `j`  
**Location**: `incremental_processor.py` (Line 210)

```python
# Creating judgment node
judgment_node = create_node_id('judgment', unique_key=title)

# Example:
title = "M.C. Mehta v. Kamal Nath [2000] 6 SCC 213"
judgment_node = create_node_id('judgment', unique_key=title)
# Result: <j_8d50e3ef>
```

**RDF Output**:
```rdf
<j_8d50e3ef> <dgraph.type> "Judgment" .
<j_8d50e3ef> <judgment_id> "j_8d50e3ef" .
<j_8d50e3ef> <title> "M.C. Mehta v. Kamal Nath [2000] 6 SCC 213" .
<j_8d50e3ef> <doc_id> "DOC001" .
<j_8d50e3ef> <year> "2000" .
```

**Hash Map**: `title_to_judgment_map` in `IncrementalRDFProcessor`
```python
self.title_to_judgment_map: Dict[str, str] = {}
# Structure:
{
  "m.c. mehta v. kamal nath [2000] 6 scc 213": "j_8d50e3ef",
  "indian council for enviro v. union of india": "j_9a1b2c3d"
}
```

---

### 5.2 Judge Nodes

**Hash Key**: Judge Name  
**Prefix**: `judge`  
**Location**: `relationships/judge_relationship.py`

```python
# Creating judge node
judge_node = create_node_id('judge', unique_key=judge_name)

# Example:
judge_name = "Justice D. Y. Chandrachud"
judge_node = create_node_id('judge', unique_key=judge_name)
# Result: <judge_ea7adefd>
```

**RDF Output**:
```rdf
<judge_ea7adefd> <dgraph.type> "Judge" .
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .

# Relationship
<j_8d50e3ef> <judged_by> <judge_ea7adefd> .
```

**Hash Map**: `judge_map` in `JudgeRelationshipHandler`
```python
self.judge_map: Dict[str, str] = {}
# Structure:
{
  "Justice D. Y. Chandrachud": "judge_ea7adefd",
  "Justice Hemant Gupta": "judge_9c1212fb"
}
```

**Key Feature**: Only stores judges seen in CURRENT batch
- Batch 1: Creates `judge_map` for Batch 1 judges
- Batch 2: Creates NEW `judge_map` for Batch 2 judges
- Dgraph upsert merges duplicates automatically!

---

### 5.3 Advocate Nodes (Petitioner & Respondent)

**Hash Key**: Advocate Name + Type  
**Prefix**: `petitioner_advocate` or `respondant_advocate`  
**Location**: `relationships/advocate_relationship.py`

```python
# Creating petitioner advocate node
advocate_node = create_node_id('petitioner_advocate', unique_key=advocate_name)

# Example:
advocate_name = "Mr. M. C. Mehta"
advocate_node = create_node_id('petitioner_advocate', unique_key=advocate_name)
# Result: <petitioner_advocate_abc12345>
```

**RDF Output**:
```rdf
<petitioner_advocate_abc12345> <dgraph.type> "Advocate" .
<petitioner_advocate_abc12345> <advocate_id> "petitioner_advocate_abc12345" .
<petitioner_advocate_abc12345> <name> "Mr. M. C. Mehta" .
<petitioner_advocate_abc12345> <advocate_type> "petitioner" .

# Relationship
<j_8d50e3ef> <petitioner_represented_by> <petitioner_advocate_abc12345> .
```

**Hash Maps**: Two separate maps for petitioner and respondent
```python
self.petitioner_advocate_map: Dict[str, str] = {}
self.respondant_advocate_map: Dict[str, str] = {}
```

**Why Separate Types?**
```
Same lawyer can represent:
  - Petitioner in Case A → <petitioner_advocate_abc123>
  - Respondent in Case B → <respondant_advocate_def456>

Different roles = Different nodes (by design)
```

---

### 5.4 Outcome Nodes

**Hash Key**: Outcome Name  
**Prefix**: `outcome`  
**Location**: `relationships/outcome_relationship.py`

```python
# Creating outcome node
outcome_node = create_node_id('outcome', unique_key=outcome_name)

# Example:
outcome_name = "Petition Allowed"
outcome_node = create_node_id('outcome', unique_key=outcome_name)
# Result: <outcome_7f8e9d0a>
```

**RDF Output**:
```rdf
<outcome_7f8e9d0a> <dgraph.type> "Outcome" .
<outcome_7f8e9d0a> <outcome_id> "outcome_7f8e9d0a" .
<outcome_7f8e9d0a> <name> "Petition Allowed" .

# Relationship
<j_8d50e3ef> <has_outcome> <outcome_7f8e9d0a> .
```

**Hash Map**: `outcome_map` in `OutcomeRelationshipHandler`
```python
self.outcome_map: Dict[str, str] = {}
# Structure:
{
  "Petition Allowed": "outcome_7f8e9d0a",
  "Petition Dismissed": "outcome_1a2b3c4d"
}
```

---

### 5.5 Case Duration Nodes

**Hash Key**: Duration String  
**Prefix**: `case_duration`  
**Location**: `relationships/case_duration_relationship.py`

```python
# Creating case duration node
duration_node = create_node_id('case_duration', unique_key=duration_info)

# Example:
duration_info = "2 years 3 months"
duration_node = create_node_id('case_duration', unique_key=duration_info)
# Result: <case_duration_5b6c7d8e>
```

**RDF Output**:
```rdf
<case_duration_5b6c7d8e> <dgraph.type> "CaseDuration" .
<case_duration_5b6c7d8e> <case_duration_id> "case_duration_5b6c7d8e" .
<case_duration_5b6c7d8e> <duration> "2 years 3 months" .

# Relationship
<j_8d50e3ef> <has_case_duration> <case_duration_5b6c7d8e> .
```

---

### 5.6 Citation Nodes (External References)

**Hash Key**: Citation Title  
**Prefix**: `j` (UNIFIED with judgments!)  
**Location**: `relationships/citation_relationship.py`

```python
# Creating citation node (uses 'judgment' type for unification!)
citation_node = create_node_id('judgment', unique_key=citation_title)

# Example:
citation_title = "Indian Council for Enviro v. Union of India"
citation_node = create_node_id('judgment', unique_key=citation_title)
# Result: <j_9a1b2c3d>
```

**RDF Output**:
```rdf
<j_9a1b2c3d> <dgraph.type> "Judgment" .
<j_9a1b2c3d> <judgment_id> "j_9a1b2c3d" .
<j_9a1b2c3d> <title> "Indian Council for Enviro v. Union of India" .

# Relationship
<j_8d50e3ef> <cites> <j_9a1b2c3d> .
```

**Hash Map**: `citation_map` in `CitationRelationshipHandler`
```python
self.citation_map: Dict[str, str] = {}
# Structure:
{
  "indian council for enviro v. union of india": "j_9a1b2c3d",
  "external case title": "j_4e5f6a7b"
}
```

---

## 6. RDF File Generation Process

### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Load Unprocessed Documents from Elasticsearch      │
└─────────────────────────────────────────────────────────────┘
         │
         ├─ Query: processed_to_dgraph == false
         ├─ Result: DataFrame with 5 new documents
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: First Pass - Collect Judgment Data & Build Maps    │
└─────────────────────────────────────────────────────────────┘
         │
         ├─ For each document:
         │   ├─ Create judgment node ID (hash of title)
         │   ├─ Add to title_to_judgment_map
         │   └─ Store JudgmentData object
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Second Pass - Process Relationships                │
└─────────────────────────────────────────────────────────────┘
         │
         ├─ For each judgment:
         │   │
         │   ├─ Create Judgment Triples
         │   │   ├─ <j_hash> <dgraph.type> "Judgment"
         │   │   ├─ <j_hash> <title> "..."
         │   │   └─ <j_hash> <doc_id> "..."
         │   │
         │   ├─ Process Judge Relationships
         │   │   ├─ Parse judge names
         │   │   ├─ For each judge:
         │   │   │   ├─ Check judge_map (seen in this batch?)
         │   │   │   ├─ If yes: Reuse node ID
         │   │   │   ├─ If no: Create new node ID (hash of name)
         │   │   │   │   ├─ Create judge triples
         │   │   │   │   └─ Add to judge_map
         │   │   │   └─ Create relationship triple
         │   │   └─ Return relationship triples
         │   │
         │   ├─ Process Advocate Relationships
         │   │   └─ Similar to judges
         │   │
         │   ├─ Process Outcome Relationships
         │   │   └─ Similar to judges
         │   │
         │   ├─ Process Case Duration Relationships
         │   │   └─ Similar to judges
         │   │
         │   └─ Process Citation Relationships
         │       ├─ Parse citations
         │       ├─ For each citation:
         │       │   ├─ Check title_to_judgment_map (internal ref?)
         │       │   ├─ If yes: Link to existing judgment
         │       │   ├─ If no: Create citation node (hash of title)
         │       │   └─ Create relationship triple
         │       └─ Return relationship triples
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Combine All RDF Triples                            │
└─────────────────────────────────────────────────────────────┘
         │
         ├─ Judgment triples
         ├─ Judge triples + relationships
         ├─ Advocate triples + relationships
         ├─ Outcome triples + relationships
         ├─ Case duration triples + relationships
         └─ Citation triples + relationships
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Write RDF File (Fresh, Not Append)                 │
└─────────────────────────────────────────────────────────────┘
         │
         ├─ File: rdf/judgments.rdf
         ├─ Mode: Write (overwrite)
         └─ Content: All triples from this batch
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Upload to Dgraph with Upsert                       │
└─────────────────────────────────────────────────────────────┘
         │
         ├─ Command: dgraph live --files ... --upsertPredicate ...
         ├─ Upsert predicates:
         │   ├─ judgment_id (merge judgments with same ID)
         │   ├─ judge_id (merge judges with same ID)
         │   ├─ advocate_id (merge advocates with same ID)
         │   ├─ outcome_id (merge outcomes with same ID)
         │   └─ case_duration_id (merge durations with same ID)
         │
         └─ Dgraph automatically merges duplicates!
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: Mark Documents as Processed in Elasticsearch       │
└─────────────────────────────────────────────────────────────┘
         │
         ├─ Update: processed_to_dgraph = true
         └─ For: doc_ids in this batch
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 8: Clean Up RDF File (Optional)                       │
└─────────────────────────────────────────────────────────────┘
         │
         ├─ Backup: rdf/judgments_backup_20251106_123456.rdf
         └─ Delete: rdf/judgments.rdf
```

---

## 7. Multi-Batch Processing & Upsert Mechanism

### How Upsert Works in Dgraph

**Upsert Predicate**: A field that Dgraph uses to identify unique nodes

```rdf
# Schema (rdf.schema)
judge_id: string @index(exact) @upsert .
```

When uploading with `--upsertPredicate judge_id`:
1. Dgraph checks if a node with this `judge_id` already exists
2. If YES: Updates existing node (merges properties)
3. If NO: Creates new node

### Example: Multi-Batch Judge Processing

#### Batch 1 RDF:
```rdf
<judge_ea7adefd> <dgraph.type> "Judge" .
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .
<j_abc12345> <judged_by> <judge_ea7adefd> .
```

**Dgraph After Batch 1**:
```
Node UID: 0x1234
  dgraph.type: "Judge"
  judge_id: "judge_ea7adefd"
  name: "Justice D. Y. Chandrachud"
  ~judged_by: [0x5678]  # Reverse edge to judgment
```

#### Batch 2 RDF (30 days later):
```rdf
<judge_ea7adefd> <dgraph.type> "Judge" .
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .  # ← SAME ID!
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .
<j_def67890> <judged_by> <judge_ea7adefd> .
```

**Dgraph After Batch 2**:
```
Node UID: 0x1234  ← SAME NODE!
  dgraph.type: "Judge"
  judge_id: "judge_ea7adefd"
  name: "Justice D. Y. Chandrachud"
  ~judged_by: [0x5678, 0x9ABC]  # ← NEW judgment added!
```

### Key Points:

1. **Same Hash ID**: Both batches use `<judge_ea7adefd>` (content-based)
2. **Upsert Merges**: Dgraph recognizes same `judge_id`, uses same UID
3. **Relationships Accumulate**: New `judged_by` relationships added to existing node
4. **No Duplicates**: One judge, multiple judgments linked!

---

## 8. Citation-Title Unification (Critical Feature)

### The Problem

```
❌ WITHOUT UNIFICATION:

Batch 1: Upload Case A
  - Creates: <j_abc123> "Case A"

Batch 2: Upload Case B (cites Case A)
  - Creates: <c_def456> "Case A"  # ← DUPLICATE!
  - Relationship: <j_xyz789> → cites → <c_def456>
  
Result: Two nodes for same case! (j_abc123 and c_def456)
```

### The Solution

**Key Change**: Citations use `'judgment'` type (not `'citation'`)

**File**: `relationships/citation_relationship.py` (Line 73)

```python
# OLD (caused duplicates):
citation_node = create_node_id('citation', unique_key=citation_title)
# Result: <c_def456>

# NEW (prevents duplicates):
citation_node = create_node_id('judgment', unique_key=citation_title)
# Result: <j_abc123>  ← SAME as actual judgment!
```

### Unified Prefix in `utils.py`

```python
node_type_map = {
    'judgment': 'j',
    'citation': 'j',  # ← UNIFIED! Citations use same prefix
    'judge': 'judge',
    # ...
}
```

### Result

```
✅ WITH UNIFICATION:

Batch 1: Upload Case A
  - Creates: <j_abc123> "Case A"

Batch 2: Upload Case B (cites Case A)
  - Creates: <j_abc123> "Case A"  # ← SAME ID!
  - Relationship: <j_xyz789> → cites → <j_abc123>
  
Dgraph Upsert: Recognizes same judgment_id, merges into one node!

Result: ONE node for Case A, properly linked!
```

---

## 9. File-by-File Explanation

### 9.1 `utils.py` - Hash ID Generator

**Purpose**: Core utility for creating stable hash-based IDs

**Key Functions**:

#### `create_node_id()`
- **Input**: Node type + unique key (content)
- **Process**:
  1. Normalize unique key (lowercase, strip)
  2. Generate MD5 hash
  3. Truncate to 8 characters
  4. Format with prefix
- **Output**: Stable node ID

**Critical Section**:
```python
# Lines 140-165
node_type_map = {
    'judgment': 'j',
    'citation': 'j',  # ← UNIFICATION!
    # ...
}

if unique_key:
    normalized_key = unique_key.lower().strip()  # ← NORMALIZATION
    hash_obj = hashlib.md5(normalized_key.encode())
    hash_short = hash_obj.hexdigest()[:8]  # ← TRUNCATION
    return f"{prefix}_{hash_short}"  # ← FORMATTING
```

---

### 9.2 `incremental_processor.py` - Main Orchestrator

**Purpose**: Coordinates entire RDF generation and upload process

**Key Methods**:

#### `process_incremental()`
- Loads unprocessed documents
- Orchestrates all processing steps
- Uploads to Dgraph
- Marks documents as processed

#### `_collect_judgment_data()` (Line 180)
```python
# CRITICAL: Use TITLE for judgment node IDs
judgment_node = create_node_id('judgment', unique_key=title)

# Build title mapping for cross-references
self.title_to_judgment_map[title.lower()] = judgment_node
```

**Why Title (not doc_id)?**
- Citations only have title (no doc_id)
- Using title ensures citations and judgments unify
- Same title → Same hash → Same ID → Dgraph merges!

#### `_process_judgments_and_relationships()` (Line 227)
- Delegates to specialized handlers
- Each handler manages its own hash map
- Collects all RDF triples

#### `_upload_to_dgraph()` (Line 410)
```python
# Upsert predicates for duplicate prevention
live_cmd = [
    "dgraph", "live",
    "--upsertPredicate", "judgment_id",
    "--upsertPredicate", "judge_id",
    "--upsertPredicate", "advocate_id",
    # ...
]
```

**Hash Maps**:
```python
self.title_to_judgment_map: Dict[str, str] = {}
# Example:
{
  "case a title": "j_abc123",
  "case b title": "j_def456"
}
```

---

### 9.3 `relationships/judge_relationship.py`

**Purpose**: Handle judge nodes and relationships

**Key Methods**:

#### `create_judge_relationships()`
```python
for judge_name in judges:
    judge_node = self._get_or_create_judge_node(judge_clean)
    relationship_triple = format_rdf_triple(
        judgment.judgment_node, 
        'judged_by', 
        judge_node, 
        False
    )
```

#### `_get_or_create_judge_node()`
```python
if judge_name in self.judge_map:
    return self.judge_map[judge_name]  # Reuse from this batch

# Create new node with stable hash ID
judge_node = create_node_id('judge', unique_key=judge_name)
self.judge_map[judge_name] = judge_node

# Generate RDF triples
judge_triples = [
    format_rdf_triple(judge_node, 'dgraph.type', 'Judge'),
    format_rdf_triple(judge_node, 'judge_id', judge_node),
    format_rdf_triple(judge_node, 'name', judge_name)
]
```

**Hash Map Scope**:
- ❌ NOT persistent across batches
- ✅ Unique to current processing session
- ✅ Dgraph upsert handles cross-batch merging

**Hash Map Structure**:
```python
self.judge_map: Dict[str, str] = {}
# Example:
{
  "Justice D. Y. Chandrachud": "judge_ea7adefd",
  "Justice Hemant Gupta": "judge_9c1212fb"
}
```

---

### 9.4 `relationships/citation_relationship.py`

**Purpose**: Handle citation nodes and cross-references

**Key Methods**:

#### `create_citation_relationships()`
```python
for citation in citations:
    citation_lower = citation_clean.lower()
    
    # Check if citation matches existing judgment (internal reference)
    if citation_lower in self.title_to_judgment_map:
        existing_judgment_node = self.title_to_judgment_map[citation_lower]
        relationship_triple = format_rdf_triple(
            judgment.judgment_node, 
            'cites', 
            existing_judgment_node, 
            False
        )
        self.stats['title_matches'] += 1
    else:
        # Create citation node for external reference
        citation_node = self._get_or_create_citation_node(citation_clean)
        relationship_triple = format_rdf_triple(
            judgment.judgment_node, 
            'cites', 
            citation_node, 
            False
        )
        self.stats['citation_matches'] += 1
```

#### `_get_or_create_citation_node()` (Line 73)
```python
# CRITICAL: Uses 'judgment' type (not 'citation') for unification
citation_node = create_node_id('judgment', unique_key=citation_title)
```

**Why `'judgment'` type?**
1. Citations and judgments should be same entity
2. Same title → Same hash → Same ID
3. Dgraph upsert merges them automatically
4. No duplicates when citation becomes actual judgment!

**Hash Maps**:
```python
# Passed from IncrementalRDFProcessor
self.title_to_judgment_map: Dict[str, str] = {}
# Maps ALL judgments in this batch

# Created within this handler
self.citation_map: Dict[str, str] = {}
# Maps external citations created in this batch
```

---

### 9.5 `relationships/advocate_relationship.py`

**Purpose**: Handle advocate nodes (petitioner & respondent)

**Key Feature**: Separate hash maps for different advocate types

```python
self.petitioner_advocate_map: Dict[str, str] = {}
self.respondant_advocate_map: Dict[str, str] = {}
```

**Why Separate?**
- Same person can represent different sides in different cases
- Different roles = Different nodes (by design)

---

### 9.6 `relationships/outcome_relationship.py`

**Purpose**: Handle outcome nodes

**Characteristics**:
- Limited set of outcomes ("Petition Allowed", "Dismissed", etc.)
- High reuse across cases
- Hash-based IDs ensure deduplication

---

### 9.7 `relationships/case_duration_relationship.py`

**Purpose**: Handle case duration nodes

**Characteristics**:
- Duration strings ("2 years 3 months")
- Hash-based IDs for deduplication

---

### 9.8 `elasticsearch_handler.py`

**Purpose**: Interface with Elasticsearch

**Key Methods**:

#### `load_unprocessed_documents()`
```python
query = {
    "query": {
        "bool": {
            "must": [
                {"term": {"processed_to_dgraph": False}}
            ]
        }
    }
}
```

#### `mark_documents_as_processed()`
```python
# Update documents after successful Dgraph upload
for doc_id in doc_ids:
    es.update(
        index=self.index_name,
        id=doc_id,
        body={"doc": {"processed_to_dgraph": True}}
    )
```

---

### 9.9 `config.py`

**Purpose**: Configuration management

**Key Configuration**:
```python
# Elasticsearch
ELASTICSEARCH_HOST = "http://localhost:9200"
ELASTICSEARCH_INDEX = "graphdb"

# Dgraph
DGRAPH_HOST = "dgraph-standalone:9080"
DGRAPH_ZERO = "dgraph-standalone:5080"

# Output
RDF_OUTPUT_FILE = "rdf/judgments.rdf"
RDF_SCHEMA_FILE = "rdf.schema"
```

---

## 10. Real-World Scenarios

### Scenario 1: Judge Appears in Multiple Batches

#### Batch 1 (January):
```python
# Document 1
title = "Case A"
judge_name = "Justice D. Y. Chandrachud"

# Processing:
judge_node = create_node_id('judge', unique_key="Justice D. Y. Chandrachud")
# Result: <judge_ea7adefd>

# RDF:
<judge_ea7adefd> <dgraph.type> "Judge" .
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .
<j_abc123> <judged_by> <judge_ea7adefd> .
```

#### Batch 2 (March):
```python
# Document 10
title = "Case J"
judge_name = "Justice D. Y. Chandrachud"  # SAME JUDGE

# Processing:
judge_node = create_node_id('judge', unique_key="Justice D. Y. Chandrachud")
# Result: <judge_ea7adefd>  ← SAME ID!

# RDF:
<judge_ea7adefd> <dgraph.type> "Judge" .
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .
<j_xyz789> <judged_by> <judge_ea7adefd> .
```

#### Dgraph After Upload:
```
# Upsert recognizes same judge_id
Node UID: 0x1234  # Same node for both batches
  dgraph.type: "Judge"
  judge_id: "judge_ea7adefd"
  name: "Justice D. Y. Chandrachud"
  ~judged_by: [0x5678, 0x9ABC]  # Both judgments linked
```

**Result**: ✅ One judge node, two judgments linked!

---

### Scenario 2: Citation Becomes Actual Judgment

#### Batch 1 (Upload Case B, which cites Case A):
```python
# Case B cites "Case A" (which doesn't exist in DB yet)
title_b = "Case B"
citations = ["Case A"]

# Processing citation:
citation_node = create_node_id('judgment', unique_key="Case A")
# Result: <j_abc123>

# RDF:
<j_abc123> <dgraph.type> "Judgment" .
<j_abc123> <judgment_id> "j_abc123" .
<j_abc123> <title> "Case A" .
<j_def456> <cites> <j_abc123> .
```

**Dgraph After Batch 1**:
```
Node UID: 0x1111
  dgraph.type: "Judgment"
  judgment_id: "j_abc123"
  title: "Case A"
  ~cites: [0x2222]  # Cited by Case B
```

#### Batch 2 (Upload actual Case A):
```python
# Now uploading the actual Case A judgment
title_a = "Case A"  # SAME TITLE as citation!

# Processing judgment:
judgment_node = create_node_id('judgment', unique_key="Case A")
# Result: <j_abc123>  ← SAME ID as citation!

# RDF:
<j_abc123> <dgraph.type> "Judgment" .
<j_abc123> <judgment_id> "j_abc123" .
<j_abc123> <title> "Case A" .
<j_abc123> <doc_id> "DOC005" .  # Now has doc_id!
<j_abc123> <year> "2020" .
<j_abc123> <judged_by> <judge_xyz> .
```

**Dgraph After Batch 2**:
```
Node UID: 0x1111  # SAME node!
  dgraph.type: "Judgment"
  judgment_id: "j_abc123"
  title: "Case A"
  doc_id: "DOC005"  # ← NEW property added
  year: "2020"  # ← NEW property added
  judged_by: [0x3333]  # ← NEW relationship added
  ~cites: [0x2222]  # ← OLD relationship preserved
```

**Result**: ✅ Citation and judgment merged into ONE node!

---

### Scenario 3: Multiple Cases Judged by Same Judge

#### Batch 1 (3 Cases, Same Judge):
```python
# Processing within SAME batch
cases = [
    {"title": "Case A", "judge": "Justice D. Y. Chandrachud"},
    {"title": "Case B", "judge": "Justice D. Y. Chandrachud"},
    {"title": "Case C", "judge": "Justice D. Y. Chandrachud"}
]

# First case creates judge node
judge_node = create_node_id('judge', unique_key="Justice D. Y. Chandrachud")
judge_map["Justice D. Y. Chandrachud"] = "judge_ea7adefd"

# RDF for judge (created once):
<judge_ea7adefd> <dgraph.type> "Judge" .
<judge_ea7adefd> <judge_id> "judge_ea7adefd" .
<judge_ea7adefd> <name> "Justice D. Y. Chandrachud" .

# Second case reuses from judge_map
judge_node = judge_map["Justice D. Y. Chandrachud"]  # "judge_ea7adefd"

# Third case also reuses
judge_node = judge_map["Justice D. Y. Chandrachud"]  # "judge_ea7adefd"

# RDF relationships (created three times):
<j_case_a> <judged_by> <judge_ea7adefd> .
<j_case_b> <judged_by> <judge_ea7adefd> .
<j_case_c> <judged_by> <judge_ea7adefd> .
```

**Result**: ✅ One judge node triple, three relationship triples!

---

### Scenario 4: Case Cites Multiple Cases

#### Batch 1:
```python
title = "Case D"
citations = ["Case A", "Case B", "Case C"]

# All three exist in this batch
title_to_judgment_map = {
    "case a": "j_abc123",
    "case b": "j_def456",
    "case c": "j_ghi789"
}

# Processing:
# Citation 1: "Case A"
if "case a" in title_to_judgment_map:
    # Internal reference
    <j_case_d> <cites> <j_abc123> .

# Citation 2: "Case B"
if "case b" in title_to_judgment_map:
    # Internal reference
    <j_case_d> <cites> <j_def456> .

# Citation 3: "Case C"
if "case c" in title_to_judgment_map:
    # Internal reference
    <j_case_d> <cites> <j_ghi789> .
```

**Result**: ✅ Three citation relationships, all internal!

---

## 11. Verification & Testing

### How to Verify No Duplicates

#### Method 1: Count Nodes by Type

```python
# In Dgraph Ratel (http://localhost:8050)

{
  allJudges(func: type(Judge)) {
    count(uid)
  }
}

# Result:
{
  "data": {
    "allJudges": [
      {
        "count": 15  # Total unique judges
      }
    ]
  }
}
```

#### Method 2: Check Specific Judge

```python
{
  judge(func: eq(name, "Justice D. Y. Chandrachud")) {
    uid
    name
    judge_id
    ~judged_by {
      count(uid)
      title
    }
  }
}

# Result:
{
  "data": {
    "judge": [
      {
        "uid": "0x1234",
        "name": "Justice D. Y. Chandrachud",
        "judge_id": "judge_ea7adefd",
        "~judged_by": [
          {"count": 25}  # 25 cases judged by this judge
        ]
      }
    ]
  }
}
```

If this query returns multiple results → DUPLICATE DETECTED!

#### Method 3: Check Citation Unification

```python
{
  case(func: eq(title, "Case A")) {
    uid
    title
    judgment_id
    doc_id
    ~cites {
      count(uid)
      title
    }
  }
}

# Result (CORRECT):
{
  "data": {
    "case": [
      {
        "uid": "0x5678",
        "title": "Case A",
        "judgment_id": "j_abc123",
        "doc_id": "DOC001",  # Has doc_id (actual judgment)
        "~cites": [
          {"count": 3},  # Cited by 3 cases
          {"title": "Case B"},
          {"title": "Case D"},
          {"title": "Case F"}
        ]
      }
    ]
  }
}

# Result (DUPLICATE - INCORRECT):
{
  "data": {
    "case": [
      {
        "uid": "0x5678",
        "title": "Case A",
        "judgment_id": "j_abc123",
        "doc_id": "DOC001"
      },
      {
        "uid": "0x9999",  # ← DUPLICATE NODE!
        "title": "Case A",
        "judgment_id": "c_abc123",  # ← Different ID!
        "doc_id": null  # ← No doc_id (citation)
      }
    ]
  }
}
```

---

## 🎯 Summary

### Key Principles

1. **Content-Based IDs**: Hash of content (title/name) → Stable IDs
2. **Normalization**: Lowercase, strip whitespace before hashing
3. **Unification**: Citations and judgments use same prefix (`j`)
4. **Hash Maps**: Track entities within each batch
5. **Dgraph Upsert**: Merges nodes with same ID across batches
6. **No Append Mode**: Fresh RDF file each batch, Dgraph handles merging

### Files & Responsibilities

| File | Purpose | Hash Maps |
|------|---------|-----------|
| `utils.py` | Hash ID generation | None |
| `incremental_processor.py` | Orchestration | `title_to_judgment_map` |
| `judge_relationship.py` | Judge nodes | `judge_map` |
| `advocate_relationship.py` | Advocate nodes | `petitioner_advocate_map`, `respondant_advocate_map` |
| `outcome_relationship.py` | Outcome nodes | `outcome_map` |
| `case_duration_relationship.py` | Duration nodes | `case_duration_map` |
| `citation_relationship.py` | Citation nodes | `citation_map` |

### Flow Summary

```
1. Load unprocessed documents
2. Create judgment nodes (hash of title)
3. Build title mapping
4. Process relationships:
   - Check hash map (batch scope)
   - If exists: Reuse ID
   - If not: Create new ID (hash of content)
5. Generate RDF (fresh file)
6. Upload to Dgraph (upsert enabled)
7. Dgraph merges duplicates automatically
8. Mark documents as processed
```

### Critical Insights

✅ **Hash maps are batch-scoped** (not persistent)  
✅ **Dgraph upsert handles cross-batch merging**  
✅ **Same content → Same hash → Same ID → No duplicates**  
✅ **Citations and judgments unified by design**  

---

**End of Document** 📚
