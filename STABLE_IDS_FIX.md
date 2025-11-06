# ✅ Fixed: Stable IDs Across Batches

## Problem Statement

**Original Issue:**
When processing multiple batches of documents, counter-based IDs caused conflicts:

```
Batch 1 (Documents 1-5):
  <judge1> = "Justice A"
  <advocate1> = "Mr. X"
  <c1> = "Case Alpha"

Batch 2 (Documents 6-10):  ❌ CONFLICT!
  <judge1> = "Justice B"     ← Different person, same ID!
  <advocate1> = "Ms. Y"      ← Different person, same ID!
  <c1> = "Case Beta"         ← Different case, same ID!
```

**Result:** Dgraph would overwrite existing nodes with new data, causing data corruption!

---

## Solution: Content-Based Stable IDs

Now ALL entities use **stable, content-based IDs** (like judgments already did):

```
Batch 1 (Documents 1-5):
  <judge_a1b2c3d4> = "Justice A"        (hash of "Justice A")
  <petitioner_advocate_x7y8z9a0> = "Mr. X"
  <citation_d4e5f6g7> = "Case Alpha"

Batch 2 (Documents 6-10):  ✅ NO CONFLICT!
  <judge_e8f9g0h1> = "Justice B"        (hash of "Justice B")
  <judge_a1b2c3d4> = "Justice A"        ← REUSES existing!
  <petitioner_advocate_x7y8z9a0> = "Mr. X"  ← REUSES existing!
```

---

## Implementation Details

### 1. Judge IDs

**Before:**
```python
judge_node = create_node_id('judge', self.judge_counter)  # <judge1>, <judge2>, ...
self.judge_counter += 1
```

**After:**
```python
judge_node = create_node_id('judge', unique_key=judge_name)  # <judge_a1b2c3d4>
# Same judge always gets same ID!
```

**Example:**
```python
"Justice D. Y. Chandrachud" → <judge_8f3e2a9c>  (always!)
"Justice B. V. Nagarathna"  → <judge_1d7c5f2e>  (always!)
```

### 2. Advocate IDs

**Before:**
```python
advocate_node = create_node_id('petitioner_advocate', counter)  # <petitioner_advocate1>, ...
```

**After:**
```python
unique_key = f"petitioner_{advocate_name}"
advocate_node = create_node_id('petitioner_advocate', unique_key=unique_key)
# <petitioner_advocate_7a2b3c4d>
```

**Why add type prefix?**
Same person can be petitioner in one case and respondent in another!

```python
"Mr. Harish Salve" as petitioner → <petitioner_advocate_9f4e8a2c>
"Mr. Harish Salve" as respondent → <respondant_advocate_5c1d7b3a>
```

### 3. Outcome IDs

**Before:**
```python
outcome_node = create_node_id('outcome', counter)  # <outcome1>, <outcome2>, ...
```

**After:**
```python
outcome_node = create_node_id('outcome', unique_key=outcome_name)
# <outcome_e8f2a3b1>
```

**Example:**
```python
"Petitioner Won"  → <outcome_7a1b2c3d>  (always!)
"Respondent Won"  → <outcome_4e5f6g7h>  (always!)
"Dismissed"       → <outcome_8i9j0k1l>  (always!)
```

### 4. Case Duration IDs

**Before:**
```python
duration_node = create_node_id('case_duration', counter)  # <case_duration1>, ...
```

**After:**
```python
duration_node = create_node_id('case_duration', unique_key=duration_info)
# <case_duration_3f7e9a2c>
```

**Example:**
```python
"2021-01-05 to 2021-06-30" → <case_duration_5b8c2e1f>  (always!)
"2022-03-15 to 2023-02-20" → <case_duration_7d3f9a4e>  (always!)
```

### 5. Citation IDs

**Before:**
```python
citation_node = create_node_id('c', counter)  # <c1>, <c2>, ...
```

**After:**
```python
citation_node = create_node_id('citation', unique_key=citation_title)
# <citation_9e2f3a4b>
```

**Example:**
```python
"Mohd. Yusuf v. Rajkumar [2020]" → <citation_8d3e2f1a>  (always!)
"Ravinder Kaur Grewal v. Manjit" → <citation_4c7b1e9f>  (always!)
```

---

## How Hash-Based IDs Work

```python
def create_node_id(node_type: str, unique_key: str) -> str:
    import hashlib
    
    # Example: "Justice D. Y. Chandrachud"
    hash_obj = hashlib.md5(unique_key.encode())
    hash_full = hash_obj.hexdigest()  # "8f3e2a9c1b7d5f4e..."
    hash_short = hash_full[:8]         # "8f3e2a9c"
    
    return f"{prefix}_{hash_short}"    # "judge_8f3e2a9c"
```

**Properties:**
- ✅ **Deterministic**: Same input always produces same output
- ✅ **Unique**: Different inputs produce different outputs (collision-free for our use case)
- ✅ **Stable**: ID never changes across batches
- ✅ **Short**: 8-character hash keeps IDs manageable

---

## Complete Example: Multiple Batches

### Initial State (Batch 1 - 3 documents)

```rdf
# Document 1
<j_doc001> <title> "Case A" .
<j_doc001> <judged_by> <judge_8f3e2a9c> .
<judge_8f3e2a9c> <name> "Justice D. Y. Chandrachud" .

# Document 2
<j_doc002> <title> "Case B" .
<j_doc002> <judged_by> <judge_8f3e2a9c> .  ← REUSES same judge!
<j_doc002> <petitioner_represented_by> <petitioner_advocate_7a2b3c4d> .
<petitioner_advocate_7a2b3c4d> <name> "Mr. Harish Salve" .

# Document 3
<j_doc003> <title> "Case C" .
<j_doc003> <has_outcome> <outcome_7a1b2c3d> .
<outcome_7a1b2c3d> <name> "Petitioner Won" .
```

**Upload to Dgraph** → Successful!

### New Batch (Batch 2 - 2 more documents)

```rdf
# Document 4
<j_doc004> <title> "Case D" .
<j_doc004> <judged_by> <judge_8f3e2a9c> .  ← SAME ID as Batch 1!
<j_doc004> <judged_by> <judge_1d7c5f2e> .  ← New judge
<judge_8f3e2a9c> <name> "Justice D. Y. Chandrachud" .  ← Upsert matches existing!
<judge_1d7c5f2e> <name> "Justice B. V. Nagarathna" .   ← Creates new

# Document 5
<j_doc005> <title> "Case E" .
<j_doc005> <petitioner_represented_by> <petitioner_advocate_7a2b3c4d> .  ← SAME ID!
<petitioner_advocate_7a2b3c4d> <name> "Mr. Harish Salve" .  ← Upsert matches existing!
<j_doc005> <has_outcome> <outcome_7a1b2c3d> .  ← SAME ID!
<outcome_7a1b2c3d> <name> "Petitioner Won" .  ← Upsert matches existing!
```

**Upload to Dgraph** → Successful!

**Result in Dgraph:**
```
Nodes Created:
  - 5 Judgment nodes (j_doc001 to j_doc005)
  - 2 Judge nodes (judge_8f3e2a9c, judge_1d7c5f2e)
  - 1 Advocate node (petitioner_advocate_7a2b3c4d)
  - 1 Outcome node (outcome_7a1b2c3d)

Relationships:
  - judge_8f3e2a9c is linked to 3 cases (doc001, doc002, doc004)
  - judge_1d7c5f2e is linked to 1 case (doc004)
  - petitioner_advocate_7a2b3c4d is linked to 2 cases (doc002, doc005)
  - outcome_7a1b2c3d is linked to 2 cases (doc003, doc005)

✅ NO DUPLICATES!
✅ PROPER LINKING!
✅ CONSISTENT IDs!
```

---

## Testing the Fix

### Test Script

```python
# test_stable_ids.py
from relationships import JudgeRelationshipHandler
from models import JudgmentData

# Batch 1
handler1 = JudgeRelationshipHandler()
judgment1 = JudgmentData(
    idx=0,
    title="Case A",
    judgment_node="<j1>",
    judge_name='["Justice D. Y. Chandrachud"]'
)
handler1.create_judge_relationships(judgment1)
triples1 = handler1.get_all_rdf_triples()
print("Batch 1:")
for t in triples1:
    print(f"  {t}")

# Batch 2 (new handler instance, simulating fresh RDF file)
handler2 = JudgeRelationshipHandler()
judgment2 = JudgmentData(
    idx=1,
    title="Case B",
    judgment_node="<j2>",
    judge_name='["Justice D. Y. Chandrachud"]'  # SAME JUDGE!
)
handler2.create_judge_relationships(judgment2)
triples2 = handler2.get_all_rdf_triples()
print("\nBatch 2:")
for t in triples2:
    print(f"  {t}")

# Verify same judge gets same ID
print("\n✅ Test Result:")
if "judge_8f3e2a9c" in " ".join(triples1) and "judge_8f3e2a9c" in " ".join(triples2):
    print("SUCCESS: Same judge has consistent ID across batches!")
else:
    print("FAIL: IDs are not consistent!")
```

**Expected Output:**
```
Batch 1:
  <judge_8f3e2a9c> <dgraph.type> "Judge" .
  <judge_8f3e2a9c> <judge_id> "judge_8f3e2a9c" .
  <judge_8f3e2a9c> <name> "Justice D. Y. Chandrachud" .

Batch 2:
  <judge_8f3e2a9c> <dgraph.type> "Judge" .
  <judge_8f3e2a9c> <judge_id> "judge_8f3e2a9c" .
  <judge_8f3e2a9c> <name> "Justice D. Y. Chandrachud" .

✅ Test Result:
SUCCESS: Same judge has consistent ID across batches!
```

---

## Benefits

### 1. **Data Integrity**
- ✅ No overwriting of existing entities
- ✅ No orphaned relationships
- ✅ Consistent graph structure

### 2. **True Incremental Processing**
- ✅ Each batch can be processed independently
- ✅ Fresh RDF file for each batch
- ✅ Dgraph upsert handles merging automatically

### 3. **Easier Debugging**
- ✅ Same entity always has same ID
- ✅ Easy to trace relationships
- ✅ IDs are meaningful (contain hash of content)

### 4. **Performance**
- ✅ Smaller RDF files (only new documents)
- ✅ Faster uploads
- ✅ Clean workspace

---

## Migration Notes

If you have existing data with counter-based IDs:

**Option 1: Fresh Start (Recommended)**
```python
# Reset all documents to unprocessed
from elasticsearch_handler import ElasticsearchHandler
es = ElasticsearchHandler()
es.reset_processed_status()

# Drop and recreate Dgraph database
# Then reprocess all documents with new stable IDs
```

**Option 2: Incremental Migration**
- Existing nodes will remain with old IDs
- New nodes will use stable IDs
- Both will coexist (not ideal, but works)

---

## Summary

| Entity | Old ID Format | New ID Format | Example |
|--------|---------------|---------------|---------|
| Judge | `<judge1>` | `<judge_8f3e2a9c>` | Hash of judge name |
| Petitioner Advocate | `<petitioner_advocate1>` | `<petitioner_advocate_7a2b>` | Hash of "petitioner_Name" |
| Respondent Advocate | `<respondant_advocate1>` | `<respondant_advocate_5c1d>` | Hash of "respondant_Name" |
| Outcome | `<outcome1>` | `<outcome_7a1b2c3d>` | Hash of outcome name |
| Case Duration | `<case_duration1>` | `<case_duration_5b8c2e1f>` | Hash of duration string |
| Citation | `<c1>` | `<citation_9e2f3a4b>` | Hash of citation title |
| Judgment | `<j_[hash]>` | `<j_[hash]>` | Hash of doc_id (unchanged) |

**Result:** Truly incremental processing with clean RDF files and no data corruption! 🎉
