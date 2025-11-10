# 📚 Legal Judgment Knowledge Graph System - Deep Technical Documentation

**Project**: Legal Judgment Database with RDF Generation and Dgraph Integration  
**Author**: Anish DF  
**Last Updated**: November 6, 2025  
**Version**: 2.1 - Citation-Title Unification Fix

---

## 📋 Quick Navigation

- [System Architecture & Pipeline Flow](#-1-system-architecture--pipeline-flow)
- [Complete File Structure & Responsibilities](#-2-complete-file-structure--responsibilities)
- [Duplicate Prevention - Deep Dive](#-3-duplicate-prevention---deep-dive)
- [Hash-Based Node ID Generation](#-4-hash-based-node-id-generation)
- [Entity Relationships - How They Work](#-5-entity-relationships---how-they-work)
- [RDF File Generation & Management](#-6-rdf-file-generation--management)
- [Dgraph Upsert Mechanism](#-7-dgraph-upsert-mechanism)
- [Incremental Processing Workflow](#-8-incremental-processing-workflow)
- [Citation-Title Unification Fix](#-9-citation-title-unification-fix)
- [Real-World Examples](#-10-real-world-examples)
- [Troubleshooting & FAQ](#-11-troubleshooting--faq)
- [Changelog](#-12-changelog)

---

## �️ 1. System Architecture & Pipeline Flow

### 🎯 Overview: What This System Does

This system builds a **Legal Judgment Knowledge Graph** by converting Excel data through multiple stages into a queryable graph database. Let's understand the complete data flow:

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌──────────┐
│   Excel     │ ──> │  Elasticsearch   │ ──> │  RDF File   │ ──> │  Dgraph  │
│   (.xlsx)   │     │  (Index: graphdb)│     │ (judgments  │     │  (Graph  │
│             │     │                  │     │     .rdf)   │     │   DB)    │
└─────────────┘     └──────────────────┘     └─────────────┘     └──────────┘
     STAGE 1              STAGE 2                 STAGE 3           STAGE 4
```

---

### 📊 Stage 1: Excel → Elasticsearch

**File Responsible**: `elasticsearch_upload.py`

**What Happens**:
1. Reads Excel file with columns: title, doc_id, year, citations, judges, etc.
2. Converts each row into a JSON document
3. Adds metadata: `processed_to_dgraph: false` (tracking flag)
4. Uploads to Elasticsearch index `graphdb`

**Key Logic**:
```python
# In elasticsearch_upload.py
def _prepare_document(self, row):
    return {
        "title": row['title'],
        "doc_id": row['doc_id'],  # Unique identifier
        "year": row['year'],
        "citations": parse_list(row['citations']),  # Convert to list
        "judges": parse_list(row['judges']),
        "petitioner_advocates": parse_list(row['petitioner_advocate']),
        "respondant_advocates": parse_list(row['respondant_advocate']),
        "outcome": row['outcome'],
        "case_duration": row['case_duration'],
        "processed_to_dgraph": False  # ← NOT YET PROCESSED
    }
```

**Why Elasticsearch First?**
- ✅ **Deduplication**: Checks if `doc_id` already exists (no re-upload)
- ✅ **Processing Tracking**: Marks documents as processed/unprocessed
- ✅ **Query Power**: Fast search and filtering
- ✅ **Incremental Updates**: Only process new documents

---

### 📊 Stage 2: Elasticsearch → RDF Generation

**File Responsible**: `incremental_processor.py`

**What Happens**:
1. Fetches ONLY unprocessed documents (`processed_to_dgraph: false`)
2. For each document, generates RDF triples
3. Creates stable node IDs using MD5 hashing
4. Links entities (judges, advocates, citations)
5. Writes RDF to `judgments.rdf`

**Key Process Flow**:

```python
# In incremental_processor.py
def process_incremental(self):
    # STEP 1: Fetch only unprocessed documents
    df = self.es_handler.load_unprocessed_documents()
    
    # STEP 2: Collect all judgment data
    self._collect_judgment_data(df)
    
    # STEP 3: Process relationships (judges, advocates, citations)
    self._process_judgments_and_relationships()
    
    # STEP 4: Combine all RDF triples
    self._combine_all_triples()
    
    # STEP 5: Write to judgments.rdf
    self._write_rdf_file()
    
    # STEP 6: Upload to Dgraph (if auto_upload=True)
    self._upload_to_dgraph()
    
    # STEP 7: Mark documents as processed in Elasticsearch
    self.es_handler.mark_documents_as_processed(doc_ids)
```

---

### 📊 Stage 3: RDF File Structure

**File Generated**: `judgments.rdf`

**What is RDF?**
RDF (Resource Description Framework) = Graph data in text format

**Structure**:
```rdf
# Node definition (Subject-Predicate-Object triples)
<j_abc123> <dgraph.type> "Judgment" .
<j_abc123> <judgment_id> "j_abc123" .
<j_abc123> <title> "Case X v. Case Y" .
<j_abc123> <doc_id> "DOC001" .
<j_abc123> <year> "2024"^^<xs:int> .

# Relationship (links to other nodes)
<j_abc123> <judged_by> <judge_xyz789> .
<j_abc123> <cites> <j_def456> .
```

**Each Triple Means**:
- `<j_abc123>` = **Node ID** (subject)
- `<judged_by>` = **Relationship** (predicate)
- `<judge_xyz789>` = **Target Node** (object)

---

### 📊 Stage 4: RDF → Dgraph Upload

**File Responsible**: `incremental_processor.py` (calls Docker command)

**What Happens**:
1. Docker Live Loader reads `judgments.rdf`
2. **Upsert Logic**: If node ID exists, MERGE data; else CREATE new
3. All triples loaded into Dgraph graph database
4. Relationships connected automatically

**Docker Command Used**:
```bash
docker exec -i dgraph dgraph live \
    --schema /dgraph/rdf.schema \
    --files /dgraph/judgments.rdf \
    --dgraph dgraph-standalone:9080 \
    --zero dgraph-standalone:5080
```

**What is Upsert?**
- If `<judge_abc>` exists → Update attributes
- If `<judge_abc>` doesn't exist → Create new node
- **Key**: Same ID = Same node (no duplicates!)

---

### 🔄 Complete Pipeline Flow (Visual)

```
┌──────────────────────────────────────────────────────────────────┐
│                      INITIAL UPLOAD                               │
└──────────────────────────────────────────────────────────────────┘

1️⃣ Excel (5 judgments)
   ├─ DOC001, DOC002, DOC003, DOC004, DOC005
   │
   ↓ [elasticsearch_upload.py]
   │
2️⃣ Elasticsearch (5 documents, all processed_to_dgraph=false)
   │
   ↓ [incremental_processor.py]
   │
3️⃣ RDF Generation
   ├─ Create judgment nodes: j_hash1, j_hash2, j_hash3, j_hash4, j_hash5
   ├─ Create judge nodes: judge_hash_chandrachud, judge_hash_gupta
   ├─ Create advocate nodes: advocate_hash_rohatgi, advocate_hash_salve
   ├─ Create citation links: j_hash1 → j_hash2, j_hash3 → j_hash1
   │
   ↓ Write to judgments.rdf
   │
4️⃣ Dgraph Upload (Upsert)
   ├─ All nodes created in Dgraph
   ├─ All relationships connected
   │
   ↓ Mark documents as processed
   │
5️⃣ Elasticsearch (5 documents, all processed_to_dgraph=true)


┌──────────────────────────────────────────────────────────────────┐
│                    INCREMENTAL UPDATE (3 NEW CASES)              │
└──────────────────────────────────────────────────────────────────┘

1️⃣ Excel (3 new judgments)
   ├─ DOC006, DOC007, DOC008
   │
   ↓ [elasticsearch_upload.py]
   │
2️⃣ Elasticsearch (3 NEW documents, processed_to_dgraph=false)
   │
   ↓ [incremental_processor.py - ONLY fetches unprocessed]
   │
3️⃣ RDF Generation
   ├─ Create NEW judgment nodes: j_hash6, j_hash7, j_hash8
   ├─ REUSE existing judge: judge_hash_chandrachud (same hash!)
   ├─ Create NEW advocate: advocate_hash_singhvi
   ├─ Link to EXISTING judgment: j_hash6 → j_hash1 (citation)
   │
   ↓ Write to judgments.rdf (only 3 new + relationships)
   │
4️⃣ Dgraph Upload (Upsert)
   ├─ j_hash6, j_hash7, j_hash8 → NEW nodes created
   ├─ judge_hash_chandrachud → ALREADY EXISTS, no duplicate!
   ├─ advocate_hash_singhvi → NEW node created
   ├─ Citation link j_hash6 → j_hash1 → CONNECTED (j_hash1 exists)
   │
   ↓ Mark documents as processed
   │
5️⃣ Elasticsearch (8 total, 3 new marked processed_to_dgraph=true)
```

---

### 🎯 Key Innovations

1. **Incremental Processing**: Only new documents processed (not all)
2. **Stable Hash IDs**: Same entity → Same ID → No duplicates
3. **Entity Reuse**: Existing judges/advocates automatically linked
4. **Citation Linking**: New cases link to old cases via shared IDs
5. **Tracking State**: Elasticsearch marks processed documents

---

## 📂 2. Complete File Structure & Responsibilities

### 📁 Core System Files

#### 1️⃣ **`config.py`** - Configuration Manager
**Purpose**: Centralized configuration for all settings

**What It Does**:
- Loads environment variables from `.env` file
- Provides default values if `.env` not found
- Manages Elasticsearch, Dgraph, FastAPI settings

**Key Configuration**:
```python
class Config:
    # Elasticsearch
    ELASTICSEARCH_HOST = 'http://localhost:9200'
    ELASTICSEARCH_INDEX = 'graphdb'
    
    # Dgraph
    DGRAPH_HOST = 'dgraph-standalone:9080'
    
    # Files
    RDF_OUTPUT_FILE = 'judgments.rdf'
    RDF_SCHEMA_FILE = 'rdf.schema'
```

**Used By**: ALL other files import config settings

---

#### 2️⃣ **`models.py`** - Data Models
**Purpose**: Define data structures used throughout the system

**Key Classes**:
```python
@dataclass
class JudgmentData:
    """Single judgment with all metadata"""
    idx: int
    title: str
    doc_id: str
    year: Optional[int]
    raw_citations: str
    judge_name: str
    petitioner_advocate: str
    respondant_advocate: str
    case_duration: str
    outcome: str
    judgment_node: str  # Node ID (e.g., <j_abc123>)

@dataclass
class ProcessingStats:
    """Statistics for RDF generation"""
    total_judgments: int = 0
    total_judges: int = 0
    total_citations: int = 0
    total_triples: int = 0
```

**Used By**: `incremental_processor.py`, relationship handlers

---

#### 3️⃣ **`utils.py`** - Core Utilities
**Purpose**: **MOST IMPORTANT** - Hash generation and helper functions

**Key Functions**:

##### A. **`create_node_id()`** - Hash-Based ID Generation
```python
def create_node_id(node_type: str, counter: int = None, unique_key: str = None) -> str:
    """
    Generate stable, content-based node IDs using MD5 hashing.
    
    Args:
        node_type: 'judgment', 'judge', 'advocate', 'outcome', 'case_duration'
        counter: (DEPRECATED) Old counter-based system
        unique_key: Unique content to hash (title, name, etc.)
    
    Returns:
        Node ID like <j_abc12345> or <judge_xyz78901>
    """
    
    # Define prefixes for each type
    prefix_map = {
        'judgment': 'j',           # <j_xxxxx>
        'judge': 'judge',          # <judge_xxxxx>
        'petitioner_advocate': 'adv_pet',  # <adv_pet_xxxxx>
        'respondant_advocate': 'adv_res',  # <adv_res_xxxxx>
        'outcome': 'outcome',      # <outcome_xxxxx>
        'case_duration': 'case_dur'  # <case_dur_xxxxx>
    }
    
    prefix = prefix_map.get(node_type, node_type)
    
    if unique_key:
        # NORMALIZE: lowercase + strip whitespace
        normalized_key = unique_key.strip().lower()
        
        # CREATE MD5 HASH
        hash_object = hashlib.md5(normalized_key.encode('utf-8'))
        hash_value = hash_object.hexdigest()[:8]  # First 8 chars
        
        return f"{prefix}_{hash_value}"
    
    # Fallback: counter-based (old system)
    return f"{prefix}{counter}"
```

**Example Usage**:
```python
# Same input ALWAYS produces same output
create_node_id('judge', unique_key='Justice D. Y. Chandrachud')
# → <judge_1dc1b645>

create_node_id('judge', unique_key='Justice D. Y. Chandrachud')
# → <judge_1dc1b645>  (SAME HASH!)

create_node_id('judgment', unique_key='Case X v. Case Y')
# → <j_a3f2e8d9>
```

##### B. **`sanitize_string()`** - Clean Input
```python
def sanitize_string(value: Any) -> str:
    """Remove special characters, escape quotes"""
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip().replace('"', '\\"')
```

##### C. **`parse_list_data()`** - Parse Citations/Judges
```python
def parse_list_data(raw_data: str) -> List[str]:
    """
    Convert string representations of lists to actual lists
    
    Examples:
        "['Citation 1', 'Citation 2']" → ['Citation 1', 'Citation 2']
        "Justice A, Justice B" → ['Justice A', 'Justice B']
    """
```

##### D. **`format_rdf_triple()`** - Create RDF Lines
```python
def format_rdf_triple(subject: str, predicate: str, obj: str, is_literal: bool = True) -> str:
    """
    Format RDF triple: <subject> <predicate> <object> .
    
    Examples:
        format_rdf_triple('<j_123>', 'title', 'Case X v. Y', is_literal=True)
        → '<j_123> <title> "Case X v. Y" .'
        
        format_rdf_triple('<j_123>', 'judged_by', '<judge_456>', is_literal=False)
        → '<j_123> <judged_by> <judge_456> .'
    """
```

**Used By**: ALL processing and relationship files

---

#### 4️⃣ **`elasticsearch_handler.py`** - Elasticsearch Interface
**Purpose**: Manage all Elasticsearch operations

**Key Methods**:

##### A. **`load_unprocessed_documents()`**
```python
def load_unprocessed_documents(self) -> pd.DataFrame:
    """
    Fetch ONLY documents where processed_to_dgraph = false
    
    Query:
        {
          "query": {
            "bool": {
              "must_not": [
                {"term": {"processed_to_dgraph": true}}
              ]
            }
          }
        }
    
    Returns: DataFrame with unprocessed documents only
    """
```

##### B. **`mark_documents_as_processed()`**
```python
def mark_documents_as_processed(self, doc_ids: List[str]) -> int:
    """
    Update documents in Elasticsearch: processed_to_dgraph = true
    
    Process:
        1. For each doc_id in list
        2. Update: {"doc": {"processed_to_dgraph": true}}
        3. Return count of updated documents
    """
```

##### C. **`get_processing_counts()`**
```python
def get_processing_counts(self) -> Dict[str, int]:
    """
    Return statistics:
        - total_documents
        - processed_documents
        - unprocessed_documents
    """
```

**Used By**: `incremental_processor.py`, `fastapi_app.py`

---

#### 5️⃣ **`incremental_processor.py`** - RDF Generator (CORE ENGINE)
**Purpose**: **MAIN FILE** - Orchestrates entire RDF generation process

**Workflow**:

##### Phase 1: Data Collection
```python
def _collect_judgment_data(self, df) -> None:
    """
    Convert DataFrame rows to JudgmentData objects
    
    For each row:
        1. Create stable judgment node ID using doc_id hash
        2. Parse citations, judges, advocates
        3. Store in self.judgments_data list
    
    Example:
        doc_id='DOC001', title='Case X v. Y'
        → judgment_node = create_node_id('judgment', unique_key=title)
        → judgment_node = <j_a3f2e8d9>
    """
```

##### Phase 2: Judgment Triples Creation
```python
def _create_judgment_triples(self, judgment: JudgmentData) -> None:
    """
    Create RDF triples for judgment node
    
    Output:
        <j_abc123> <dgraph.type> "Judgment" .
        <j_abc123> <judgment_id> "j_abc123" .
        <j_abc123> <title> "Case X v. Y" .
        <j_abc123> <doc_id> "DOC001" .
        <j_abc123> <year> "2024"^^<xs:int> .
    """
```

##### Phase 3: Relationship Processing
```python
def _process_judge_relationships(self, judgment: JudgmentData) -> None:
    """
    Create judge nodes and link to judgment
    
    Process:
        1. Parse judge names from judgment.judge_name
        2. For each judge:
            a. Generate judge node ID using name hash
            b. Check if judge already exists (via dict)
            c. Create judge triples if new
            d. Create relationship: judgment → judged_by → judge
    """
```

**Similar methods**:
- `_process_advocate_relationships()` - Petitioner & Respondent
- `_process_outcome_relationships()` - Link to outcome
- `_process_case_duration_relationships()` - Link to duration
- `_process_citation_relationships()` - **MOST COMPLEX** - Link to cited cases

##### Phase 4: RDF Compilation
```python
def _combine_all_triples(self) -> None:
    """
    Collect all RDF triples from:
        - Judgment nodes
        - Judge nodes
        - Advocate nodes
        - Outcome nodes
        - Case duration nodes
        - Citation nodes
        - All relationships
    
    Write to: judgments.rdf
    """
```

**Used By**: `fastapi_app.py`, command-line execution

---

### 📁 Relationship Handlers (`relationships/` folder)

#### 6️⃣ **`judge_relationship.py`**
**Purpose**: Handle judge nodes and relationships

**Key Logic**:
```python
class JudgeRelationshipHandler:
    def __init__(self):
        self.judge_nodes = {}  # Cache: name → node_id
        self.judge_triples = []
        
    def create_judge_relationships(self, judgment: JudgmentData) -> List[str]:
        """
        For each judge in judgment:
            1. Get or create judge node
            2. Create relationship triple
        
        Returns: List of relationship triples
        """
        judges = parse_list_data(judgment.judge_name)
        relationships = []
        
        for judge_name in judges:
            # Generate stable node ID
            judge_node = self._get_or_create_judge_node(judge_name)
            
            # Create relationship
            triple = format_rdf_triple(
                judgment.judgment_node,  # <j_abc123>
                'judged_by',
                judge_node,              # <judge_xyz789>
                is_literal=False
            )
            relationships.append(triple)
        
        return relationships
    
    def _get_or_create_judge_node(self, judge_name: str) -> str:
        """
        Check cache first, create if new
        
        Process:
            1. Generate hash: judge_hash = md5(judge_name)
            2. Check if judge_hash in self.judge_nodes
            3. If YES: return existing node_id
            4. If NO: create new node, add to cache, return node_id
        """
        # Generate node ID
        judge_node = create_node_id('judge', unique_key=judge_name)
        
        # Check cache
        if judge_name in self.judge_nodes:
            return judge_node  # Already exists, no new triples
        
        # NEW JUDGE - Create triples
        self.judge_nodes[judge_name] = judge_node
        self.judge_triples.extend([
            format_rdf_triple(judge_node, 'dgraph.type', 'Judge', False),
            format_rdf_triple(judge_node, 'judge_id', judge_node[1:-1]),  # Remove < >
            format_rdf_triple(judge_name, 'name', judge_name)
        ])
        
        return judge_node
```

**Used By**: `incremental_processor.py`

---

#### 7️⃣ **`advocate_relationship.py`**
**Purpose**: Handle petitioner and respondent advocate nodes

**Key Difference**: TWO types of advocates:
- `petitioner_advocate` → `<adv_pet_xxxxx>`
- `respondant_advocate` → `<adv_res_xxxxx>`

**Logic**: Same as judge_relationship.py but for two advocate types

---

#### 8️⃣ **`outcome_relationship.py`**
**Purpose**: Handle case outcome nodes

**Outcomes**: "Allowed", "Dismissed", "Partly Allowed", etc.

**Logic**: Same hash-based approach for outcome names

---

#### 9️⃣ **`case_duration_relationship.py`**
**Purpose**: Handle case duration nodes

**Duration Format**: "2 years 3 months", "1 year", etc.

**Logic**: Same hash-based approach for duration strings

---

#### 🔟 **`citation_relationship.py`** - MOST COMPLEX
**Purpose**: Handle citation relationships between judgments

**Challenge**: A citation might be:
1. **External citation** (not in database) → Create placeholder node
2. **Internal citation** (already exists) → Link to existing node

**Key Logic**:
```python
class CitationRelationshipHandler:
    def __init__(self, title_to_judgment_map: Dict[str, str] = None):
        self.title_to_judgment_map = title_to_judgment_map or {}
        self.citation_nodes = {}
        
    def create_citation_relationships(self, judgment: JudgmentData) -> List[str]:
        """
        For each cited case:
            1. Check if cited case exists in database (via title map)
            2. If EXISTS: Link to existing judgment node
            3. If NOT EXISTS: Create placeholder citation node
        """
        citations = parse_list_data(judgment.raw_citations)
        relationships = []
        
        for citation_title in citations:
            # Check if this citation is an existing judgment
            if citation_title in self.title_to_judgment_map:
                # INTERNAL REFERENCE - Link to existing judgment
                cited_node = self.title_to_judgment_map[citation_title]
                self.stats['title_matches'] += 1
            else:
                # EXTERNAL CITATION - Create placeholder node
                cited_node = self._get_or_create_citation_node(citation_title)
            
            # Create relationship
            triple = format_rdf_triple(
                judgment.judgment_node,  # <j_abc123>
                'cites',
                cited_node,              # <j_def456> or existing judgment
                is_literal=False
            )
            relationships.append(triple)
        
        return relationships
```

**Used By**: `incremental_processor.py`

---

### 📁 API & Automation Files

#### 1️⃣1️⃣ **`fastapi_app.py`** - REST API Server
**Purpose**: Provide web API for processing and status

**Key Endpoints**:
- `POST /process` - Trigger RDF generation and upload
- `GET /status` - Check processing status
- `GET /documents/unprocessed` - List unprocessed documents
- `POST /documents/mark-processed` - Manually mark documents

**Used By**: External clients, web dashboard

---

#### 1️⃣2️⃣ **`auto_processor.py`** - Background Processor
**Purpose**: Automatically check for new documents every N seconds

**Logic**:
```python
async def _check_and_process(self):
    while self.is_running:
        # Check for unprocessed documents
        unprocessed = es_handler.get_unprocessed_documents()
        
        if unprocessed:
            # Process them
            processor.process_incremental()
        
        # Wait N seconds
        await asyncio.sleep(self.check_interval)
```

---

#### 1️⃣3️⃣ **`elasticsearch_upload.py`** - Excel → Elasticsearch
**Purpose**: Upload new judgments from Excel to Elasticsearch

**Process**:
1. Read Excel file
2. Check which doc_ids already exist in Elasticsearch
3. Upload only NEW documents
4. Set `processed_to_dgraph: false` for all new documents

---

### 📁 Schema File

#### **`rdf.schema`** - Dgraph Schema Definition
**Purpose**: Define node types, predicates, and indexes for Dgraph

**Content**:
```graphql
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

# Predicates with indexes and upsert
judgment_id: string @index(exact) @upsert .
title: string @index(exact, term, fulltext) @upsert .
doc_id: string @index(exact) @upsert .
judge_id: string @index(exact) @upsert .
name: string @index(exact, term, fulltext) @upsert .
```

**Key Annotations**:
- `@index(exact)` - Enable exact match queries
- `@upsert` - **CRITICAL** - Enable duplicate prevention
- `@reverse` - Enable reverse queries (e.g., which judgments cite this case?)

---

### 🎯 File Interaction Map

```
┌─────────────────┐
│ fastapi_app.py  │ ← API entry point
└────────┬────────┘
         │
         ↓
┌─────────────────────────┐
│ incremental_processor.py│ ← Main orchestrator
└────────┬────────────────┘
         │
         ├─→ elasticsearch_handler.py ← Fetch unprocessed docs
         ├─→ utils.py ← create_node_id() for hashing
         ├─→ models.py ← JudgmentData structure
         │
         ├─→ relationships/judge_relationship.py
         ├─→ relationships/advocate_relationship.py
         ├─→ relationships/outcome_relationship.py
         ├─→ relationships/case_duration_relationship.py
         └─→ relationships/citation_relationship.py
                 │
                 └─→ All output combined → judgments.rdf
```

---

## 🔒 3. Duplicate Prevention - Deep Dive

```bash
# Dgraph
docker run -it -p 8180:8080 -p 8181:8081 -p 8000:8000 \
  -v ~/dgraph_data:/dgraph \
  --name dgraph-standalone \
  dgraph/dgraph:v23.1.0

# Elasticsearch
docker run -d -p 9200:9200 \
  -e "discovery.type=single-node" \
  --name elasticsearch \
  elasticsearch:8.11.0
```

### Step-by-Step Setup

**1. Upload Schema to Dgraph**
```bash
curl -X POST localhost:8180/alter -d @rdf.schema
```

**2. Upload Data to Elasticsearch**
```bash
python3 elasticsearch_upload.py
```

**3. Start FastAPI Server**
```bash
uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload
```

**4. Process Documents**
```bash
curl -X POST http://localhost:8003/process
```

**5. Query Results**
```bash
curl -X POST http://localhost:8180/query -d '{
  allJudgments(func: type(Judgment)) {
    uid
    title
    judged_by { name }
  }
}'
```

---

## 📄 3. RDF File Handling

### What is RDF?

RDF (Resource Description Framework) represents data as triples:

```rdf
<subject> <predicate> <object> .
```

**Example**:
```rdf
<j_abc123> <title> "Case A v. Case B" .
<j_abc123> <judged_by> <judge_1dc1b645> .
<judge_1dc1b645> <name> "Justice D. Y. Chandrachud" .
```

### RDF Generation Process

```
1. Load unprocessed documents from Elasticsearch
2. Generate stable IDs (MD5 hash of title)
3. Create RDF triples for entities and relationships
4. Write to rdf/judgments.rdf
5. Upload to Dgraph with upsert
6. Mark documents as processed
7. Cleanup RDF file (backup created)
```

---

## 🔒 4. Duplicate Prevention

### The Problem (Before v2.1)

```
Monday: Document cites "Case X"
  → Created node: <j_abc123> (based on title)

Tuesday: Upload actual "Case X" judgment
  → Created node: <j_xyz789> (based on doc_id)  ❌ DUPLICATE!
```

### The Solution (v2.1 Fix)

**Three files modified**:

1. **`utils.py`** (Line ~155):
   ```python
   node_type_map = {
       'judgment': 'j',
       'citation': 'j',  # ✅ Unified prefix
       # ...
   }
   normalized_key = unique_key.lower().strip()  # ✅ Normalization
   ```

2. **`citation_relationship.py`** (Line ~73):
   ```python
   citation_node = create_node_id('judgment', unique_key=citation_title)
   ```

3. **`incremental_processor.py`** (Line ~210):
   ```python
   # ✅ CRITICAL FIX: Use title instead of doc_id
   judgment_node = create_node_id('judgment', unique_key=title)
   ```

**Result**:
```
Monday: Citation "Case X" → <j_abc123>
Tuesday: Judgment "Case X" → <j_abc123>  ✅ SAME ID!
Dgraph merges them automatically!
```

---

## �� 5. Entity Relationships

### Complete Relationship Model

```
                    JUDGMENT (Central Node)
                           │
      ┌────────────────────┼────────────────────┐
      │         │          │          │         │
   JUDGES   ADVOCATES  CITATIONS  OUTCOME   DURATION
```

### Example: Judge Relationship

**Code** (`relationships/judge_relationship.py`):
```python
def create_judge_relationships(self, judgment: JudgmentData) -> List[str]:
    judge_names = parse_list_data(judgment.judge_name)
    
    for judge_name in judge_names:
        judge_node = self._get_or_create_judge_node(judge_name)
        relationship_triples.append(
            format_rdf_triple(
                judgment.judgment_node,  # <j_abc123>
                "judged_by",
                judge_node,  # <judge_1dc1b645>
                is_object_literal=False
            )
        )
```

**Generated RDF**:
```rdf
<j_abc123> <judged_by> <judge_1dc1b645> .
<judge_1dc1b645> <name> "Justice D. Y. Chandrachud" .
```

### Reverse Query Support

Thanks to `@reverse` in schema:
```graphql
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

---

## 🔄 6. Upsert Mechanism

### How Dgraph Upsert Works

```python
# Upload with upsert predicates
dgraph live --files judgments.rdf \
  --upsert-predicates "judgment_id,doc_id,judge_id,advocate_id,outcome_id,case_duration_id"
```

### Upsert Process

```
1. Dgraph receives RDF triple with ID
2. Query: Does this ID exist?
   - YES → Update existing node (merge)
   - NO  → Create new node
3. Result: No duplicates!
```

**Example**:
```rdf
# Batch 1
<judge_1dc1b645> <name> "Justice D. Y. Chandrachud" .

# Batch 2 (same judge in different case)
<judge_1dc1b645> <name> "Justice D. Y. Chandrachud" .

# Result: ONE node (updated, not duplicated)
```

---

## 📂 7. File Structure

```
Dgraph_final/
├── 📄 Core Application
│   ├── fastapi_app.py              # REST API server
│   ├── incremental_processor.py    # RDF generator
│   ├── elasticsearch_handler.py    # ES operations
│   ├── utils.py                    # ID generation, helpers
│   ├── config.py                   # Configuration
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
│   ├── elasticsearch_upload.py
│   └── elasticsearch_upload_with_delay.py
│
├── 🗂️ Configuration
│   ├── .env                        # Environment variables
│   └── rdf.schema                  # Dgraph schema
│
├── 📊 Data
│   ├── excel_2024_2025/FINAL/      # Excel files
│   └── rdf/                        # Generated RDF files
│
└── 📚 Documentation
    └── README.md                   # This file
```

---

## ⌨️ 8. CLI Commands

### Service Management

```bash
# Start Dgraph
docker run -it -p 8180:8080 -p 8181:8081 -v ~/dgraph_data:/dgraph dgraph/dgraph:v23.1.0

# Start Elasticsearch
docker run -d -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.11.0

# Start FastAPI
uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload
```

### Data Operations

```bash
# Upload schema
curl -X POST localhost:8180/alter -d @rdf.schema

# Upload Excel to ES
python3 elasticsearch_upload.py

# Process documents
curl -X POST http://localhost:8003/process

# Reset everything
curl -X POST http://localhost:8180/alter -d '{"drop_all": true}'
curl -X POST http://localhost:8003/documents/reset-processed
```

### Health Checks

```bash
# Check Dgraph
curl http://localhost:8180/health

# Check Elasticsearch
curl http://localhost:9200/_cluster/health

# Check FastAPI
curl http://localhost:8003/health
```

---

## 🌐 9. API Reference

### Base URL: `http://localhost:8003`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Welcome message |
| `/health` | GET | System health |
| `/status` | GET | Processing status |
| `/process` | POST | Process documents |
| `/documents/unprocessed` | GET | List unprocessed docs |
| `/documents/count` | GET | Document counts |
| `/documents/mark-processed` | POST | Mark as processed |
| `/documents/reset-processed` | POST | Reset status |

### Examples

**Process All Unprocessed**:
```bash
curl -X POST http://localhost:8003/process
```

**Process Specific Documents**:
```bash
curl -X POST http://localhost:8003/process \
  -H "Content-Type: application/json" \
  -d '{"doc_ids": ["doc_123", "doc_456"]}'
```

**Keep RDF Files** (don't cleanup):
```bash
curl -X POST http://localhost:8003/process \
  -H "Content-Type: application/json" \
  -d '{"cleanup_rdf": false}'
```

---

## 🔍 10. Common Queries

### Query All Judgments

```graphql
{
  allJudgments(func: type(Judgment)) {
    uid
    judgment_id
    title
    doc_id
    year
    judged_by { name }
    has_outcome { name }
  }
}
```

### Query Specific Judgment

```graphql
{
  judgment(func: eq(title, "Your Case Title")) {
    uid
    title
    year
    judged_by { name }
    cites { title }
    ~cites { title }  # Cases citing this one
  }
}
```

### Query Cases by Judge

```graphql
{
  judge(func: eq(name, "Justice D. Y. Chandrachud")) {
    name
    ~judged_by {
      title
      year
      has_outcome { name }
    }
  }
}
```

### Count Total Judgments

```graphql
{
  judgments(func: type(Judgment)) {
    total: count(uid)
  }
}
```

---

## 📋 11. Workflow Guide

### Incremental Processing Flow

```
1. New documents added to Elasticsearch
   └─> processed_to_dgraph: false

2. FastAPI /process endpoint called
   └─> Loads only unprocessed documents

3. Generate RDF with stable IDs
   ├─> Judgment IDs: MD5(title)
   ├─> Judge IDs: MD5(judge_name)
   └─> Links to existing entities

4. Upload to Dgraph with upsert
   └─> Merges with existing nodes

5. Mark documents as processed
   └─> processed_to_dgraph: true

6. Cleanup RDF file
   └─> Backup created, original removed
```

### Adding New Data

```bash
# 1. Add to Excel file
# 2. Upload to Elasticsearch
python3 elasticsearch_upload.py

# 3. Process (automatic incremental)
curl -X POST http://localhost:8003/process

# Done! New data linked to existing entities
```

---

## 🆕 12. Recent Updates & Bug Fixes

### v2.1.0 (November 6, 2025)

#### 🐛 CRITICAL BUG FIX: Citation-Title Duplication

**Issue**: Citations and judgments created different nodes for same case

**Root Cause**:
- Citations: `unique_key=title` → Hash of title
- Judgments: `unique_key=doc_id` → Hash of doc_id
- Same case → Different keys → Different IDs → **DUPLICATES!**

**Solution**:
```python
# incremental_processor.py (Line ~210)
# OLD: judgment_node = create_node_id('judgment', unique_key=doc_id)
# NEW:
judgment_node = create_node_id('judgment', unique_key=title)  # ✅ FIXED
```

**Impact**:
- ✅ No more duplicates
- ✅ Citations and judgments merge automatically
- ✅ All tests passing

**Verification**:
```bash
python3 test_citation_unification.py
# Expected: 🎉 ALL TESTS PASSED!
```

---

## �� 13. Troubleshooting & FAQ

### Common Issues

#### "Cannot connect to Elasticsearch"
```bash
# Check if running
curl http://localhost:9200

# Start if needed
docker run -d -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.11.0
```

#### "Cannot connect to Dgraph"
```bash
# Check if running
docker ps | grep dgraph

# Start if needed
docker run -it -p 8180:8080 -p 8181:8081 -v ~/dgraph_data:/dgraph dgraph/dgraph:v23.1.0
```

#### "Duplicate nodes in Dgraph"
```bash
# Fixed in v2.1. To clean up old duplicates:
# 1. Verify fix applied
grep "create_node_id('judgment', unique_key=title)" incremental_processor.py

# 2. Drop and re-upload
curl -X POST http://localhost:8180/alter -d '{"drop_all": true}'
curl -X POST http://localhost:8180/alter -d @rdf.schema
curl -X POST http://localhost:8003/documents/reset-processed
curl -X POST http://localhost:8003/process
```

### FAQ

**Q: What's the difference between `doc_id` and `judgment_id`?**

A:
- `doc_id`: Elasticsearch document ID (for tracking)
- `judgment_id`: Dgraph node ID (based on title hash)
  
```rdf
<j_abc123> <judgment_id> "j_abc123" .  # Node ID (title-based)
<j_abc123> <doc_id> "ES_2024_001" .    # ES tracking only
```

**Q: How do I verify no duplicates exist?**

A:
```bash
# Run tests
python3 test_citation_unification.py

# Query Dgraph for specific title
curl -X POST http://localhost:8180/query -d '{
  judgments(func: eq(title, "Your Case Title")) {
    uid
    judgment_id
  }
}'
# If > 1 result → duplicates exist
```

**Q: How do I reset everything?**

A:
```bash
# 1. Drop Dgraph data
curl -X POST http://localhost:8180/alter -d '{"drop_all": true}'

# 2. Re-upload schema
curl -X POST http://localhost:8180/alter -d @rdf.schema

# 3. Reset ES status
curl -X POST http://localhost:8003/documents/reset-processed

# 4. Reprocess
curl -X POST http://localhost:8003/process
```

---

## 📜 14. Changelog

### [2.1.0] - 2025-11-06

#### Fixed
- **CRITICAL**: Citation-title duplication bug
  - Changed judgment IDs to use title (consistent with citations)
  - Modified `incremental_processor.py`, `utils.py`, `citation_relationship.py`
  - All tests passing

#### Added
- Comprehensive test suite (`test_citation_unification.py`)
- Enhanced documentation (this README)
- Title normalization (case-insensitive, whitespace-tolerant)

### [2.0.0] - 2025-11-05

#### Added
- Complete system documentation
- Incremental processing guide
- Modular relationship handlers
- MD5 hash-based stable IDs
- FastAPI REST API

### [1.0.0] - 2025-11-01

#### Initial Release
- Basic RDF generation
- Elasticsearch integration
- Dgraph upload via Live Loader
- Entity relationships (judges, advocates, citations, outcomes, case duration)

---

## 📊 Summary

### ✅ Features

| Feature | Status | Description |
|---------|--------|-------------|
| Duplicate Prevention | ✅ Working | Content-based IDs + upsert |
| Incremental Processing | ✅ Working | Only new documents |
| Entity Linking | ✅ Working | Reuse existing entities |
| Citation-Title Unification | ✅ Fixed (v2.1) | No more duplicates |
| REST API | ✅ Working | FastAPI with all endpoints |
| Auto-Processing | ✅ Working | Background worker |

### 🚀 Quick Commands

```bash
# Start services
docker run -it -p 8180:8080 -p 8181:8081 -v ~/dgraph_data:/dgraph dgraph/dgraph:v23.1.0
docker run -d -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.11.0
uvicorn fastapi_app:app --host 0.0.0.0 --port 8003 --reload

# Upload schema
curl -X POST localhost:8180/alter -d @rdf.schema

# Upload and process data
python3 elasticsearch_upload.py
curl -X POST http://localhost:8003/process

# Query
curl -X POST http://localhost:8180/query -d '{allJudgments(func: type(Judgment)) {title}}'
```

---

## 📖 Additional Resources

- **RDF Schema**: `rdf.schema` - Complete schema definition
- **Sample Queries**: `querry_cli.txt` - Ready-to-use queries
- **Docker Commands**: `docker_information.txt` - Setup reference
- **Test Suite**: `test_citation_unification.py` - Verification tests
- **Configuration**: `.env.example` - Environment variables

---

**Version**: 2.1.0  
**Status**: Production Ready ✅  
**License**: MIT  
**Author**: Anish DF  
**Last Updated**: November 6, 2025

For issues or questions, check logs: `rdf_generator.log`, `elasticsearch_upload.log`
