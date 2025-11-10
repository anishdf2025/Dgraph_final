# 🚀 Quick Reference: Duplicate Prevention System

**Quick lookup guide for developers**  
**For detailed explanations, see: DUPLICATE_HANDLING_DETAILED.md**

---

## 🎯 Core Concept

```
Same Content → Same Hash → Same ID → No Duplicates
```

---

## 📚 Hash ID Generation

### Function Signature
```python
# Location: utils.py (line ~140)
def create_node_id(node_type: str, unique_key: str) -> str:
    """
    Creates stable hash-based node IDs
    
    Returns: "<prefix>_<8-char-hash>"
    Example: "judge_ea7adefd"
    """
```

### Node Type Mapping
| Node Type | Prefix | Hash Key |
|-----------|--------|----------|
| Judgment | `j` | Title |
| Citation | `j` | Title (unified!) |
| Judge | `judge` | Judge name |
| Petitioner Advocate | `petitioner_advocate` | Advocate name |
| Respondent Advocate | `respondant_advocate` | Advocate name |
| Outcome | `outcome` | Outcome name |
| Case Duration | `case_duration` | Duration string |

### Examples
```python
# Judgment
create_node_id('judgment', unique_key="Case A Title")
# → "j_abc12345"

# Judge
create_node_id('judge', unique_key="Justice D. Y. Chandrachud")
# → "judge_ea7adefd"

# Citation (uses 'judgment' type for unification!)
create_node_id('judgment', unique_key="Case A Title")
# → "j_abc12345" (SAME as judgment!)
```

---

## 🗺️ Hash Maps by File

### incremental_processor.py
```python
self.title_to_judgment_map: Dict[str, str]
# Example:
{
  "case a title": "j_abc12345",
  "case b title": "j_def67890"
}
```

### judge_relationship.py
```python
self.judge_map: Dict[str, str]
# Example:
{
  "Justice D. Y. Chandrachud": "judge_ea7adefd",
  "Justice Hemant Gupta": "judge_9c1212fb"
}
```

### citation_relationship.py
```python
self.citation_map: Dict[str, str]
# Example:
{
  "external case title": "j_xyz789"
}
```

### advocate_relationship.py
```python
self.petitioner_advocate_map: Dict[str, str]
self.respondant_advocate_map: Dict[str, str]
```

---

## 🔄 Processing Flow

```
1. Load unprocessed documents from Elasticsearch
   └─ Query: processed_to_dgraph == false

2. First Pass: Collect judgment data
   ├─ Create judgment nodes (hash of title)
   └─ Build title_to_judgment_map

3. Second Pass: Process relationships
   ├─ For each judgment:
   │  ├─ Check hash map (seen in this batch?)
   │  ├─ If yes: Reuse node ID
   │  └─ If no: Create new ID (hash of content)
   └─ Generate RDF triples

4. Write RDF file (fresh, not append)

5. Upload to Dgraph (with upsert)
   └─ Upsert predicates: judgment_id, judge_id, etc.

6. Mark documents as processed

7. Clean up RDF file (optional)
```

---

## 🎯 Critical Points

### ✅ DO's
- Use title (not doc_id) for judgment node IDs
- Normalize before hashing (lowercase, strip)
- Use 'judgment' type for citations (unification!)
- Let Dgraph upsert handle cross-batch merging
- Create fresh RDF file each batch

### ❌ DON'Ts
- Don't use counter-based IDs
- Don't persist hash maps between batches
- Don't use 'citation' type for citations
- Don't append to RDF file (use fresh file)
- Don't skip normalization

---

## 🔍 Verification Queries

### Check for Duplicate Judges
```graphql
{
  judges(func: eq(name, "Justice D. Y. Chandrachud")) {
    uid
    name
    judge_id
  }
}
# Expected: ONE result
# If multiple results: DUPLICATE DETECTED!
```

### Check Citation Unification
```graphql
{
  case(func: eq(title, "Case A")) {
    uid
    title
    judgment_id
    doc_id  # Should have value if actual judgment
    ~cites  # Should show citing cases
  }
}
# Expected: ONE result with doc_id
# If multiple results: DUPLICATE DETECTED!
```

---

## 📁 File Locations

### Core Hash Logic
- `utils.py` (line 140-165): `create_node_id()`

### Hash Map Usage
- `incremental_processor.py` (line 210): Judgment IDs
- `judge_relationship.py` (line 55): Judge nodes
- `citation_relationship.py` (line 73): Citation nodes
- `advocate_relationship.py`: Advocate nodes
- `outcome_relationship.py`: Outcome nodes
- `case_duration_relationship.py`: Duration nodes

### Upsert Configuration
- `rdf.schema`: Upsert directives
- `incremental_processor.py` (line 410): Upload command

---

## 🐛 Common Issues

### Issue: Same judge appears twice in Dgraph
**Cause**: Normalization not applied  
**Fix**: Check `utils.py` line 152 (normalize before hash)

### Issue: Citation and judgment are separate nodes
**Cause**: Citation uses 'citation' type instead of 'judgment'  
**Fix**: Check `citation_relationship.py` line 73

### Issue: Judges duplicated across batches
**Cause**: Upsert not enabled  
**Fix**: Check upload command has `--upsertPredicate judge_id`

---

## 📊 Statistics

### Typical Dataset (10,000 judgments)
- Unique judges: ~200
- Unique advocates: ~500
- Unique outcomes: ~10
- Unique durations: ~100

### Storage Savings
- Without hash system: ~15% duplicate nodes
- With hash system: 0% duplicate nodes
- Savings: 1,000+ duplicate nodes prevented

---

## 🔗 Related Documents

- **DUPLICATE_HANDLING_DETAILED.md**: Complete technical explanation
- **HASH_SYSTEM_VISUAL_GUIDE.md**: Visual diagrams and flow charts
- **README.md**: System overview and usage guide
- **CHANGELOG.md**: Version history and bug fixes

---

## 💡 Quick Tips

1. **Same title? Same ID!**
   - Citations and judgments with same title get same hash

2. **Hash maps are temporary**
   - Created fresh for each batch
   - Dgraph upsert handles cross-batch merging

3. **Always normalize**
   - Lowercase and strip whitespace before hashing
   - Prevents "Justice ABC" vs "justice abc" duplicates

4. **Trust the upsert**
   - Same ID in different batches → Dgraph merges automatically
   - No need for complex coordination

5. **Check the schema**
   - `@upsert` directive is critical
   - Without it, duplicates will occur

---

**Last Updated**: November 6, 2025  
**Version**: 2.1
