# 📝 Changelog - Legal Judgment Knowledge Graph System

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.0] - 2025-11-06

### 🐛 Fixed - CRITICAL BUG: Citation-Title Duplication

**Issue**: When a case was cited in one batch and the actual judgment was uploaded in another batch, the system created **two different nodes** for the same case, causing data duplication and broken relationships.

**Root Cause**: 
- Citations used `unique_key=title` for node ID generation
- Judgments used `unique_key=doc_id` for node ID generation
- Same case → Different unique_key → Different hash → Different ID → **DUPLICATES!**

**Files Modified**:

1. **`utils.py`** (Line ~155)
   - ✅ Unified prefix: Changed `'citation': 'c'` to `'citation': 'j'`
   - ✅ Added title normalization: `normalized_key = unique_key.lower().strip()`
   - ✅ Applied normalization before hashing

2. **`citation_relationship.py`** (Line ~73)
   - ✅ Changed to use `'judgment'` type instead of `'citation'`
   - ✅ Ensures citations use same node type as judgments

3. **`incremental_processor.py`** (Line ~210) - **⭐ CRITICAL FIX**
   - ❌ Old: `judgment_node = create_node_id('judgment', unique_key=doc_id)`
   - ✅ New: `judgment_node = create_node_id('judgment', unique_key=title)`
   - ✅ Now uses title (consistent with citations)

**Impact**:
- ✅ Citations and judgments with same title now produce **same ID**
- ✅ Dgraph automatically merges them via upsert
- ✅ No more duplicate nodes for same case
- ✅ Relationships preserved across batch uploads

**Verification**:
- ✅ All tests passing (`test_citation_unification.py`)
- ✅ Real-world scenario tested and verified
- ✅ Title normalization working (case-insensitive, whitespace-tolerant)

**Documentation Added**:
- `CITATION_TITLE_UNIFICATION.md` - Detailed strategy document
- `CITATION_TITLE_FIX_VERIFICATION.md` - Complete fix verification
- `test_citation_unification.py` - Comprehensive test suite

### 📚 Added

- **Quick Reference Guide** (`QUICK_REFERENCE.md`)
  - Essential commands for common operations
  - API endpoint reference
  - Common Dgraph queries
  - Troubleshooting quick fixes
  
- **Enhanced Documentation** (Updated `DETAILED_README.md`)
  - Added detailed section on Citation-Title Unification
  - Added "Recent Updates & Bug Fixes" section
  - Updated FAQ with new questions about the fix
  - Added verification instructions

- **Test Suite** (`test_citation_unification.py`)
  - Citation-Judgment unification tests
  - Real-world scenario simulation
  - Title normalization tests
  - Judge ID consistency tests

### 🔧 Changed

- **Version**: Updated to 2.1.0
- **Documentation**: Comprehensive updates across all README files
- **Logging**: Enhanced logging for debugging ID generation

### 🎯 Technical Details

**Before Fix**:
```
Citation "Case X" → unique_key: "Case X" → ID: <j_abc123>
Judgment "Case X" → unique_key: "doc_id_123" → ID: <j_xyz789>
Result: 2 different nodes ❌
```

**After Fix**:
```
Citation "Case X" → unique_key: "Case X" → ID: <j_abc123>
Judgment "Case X" → unique_key: "Case X" → ID: <j_abc123>
Result: 1 merged node ✅
```

---

## [2.0.0] - 2025-11-05

### 🎉 Added

- **Complete system documentation** (`DETAILED_README.md`)
  - RDF file handling explanation
  - Duplicate prevention strategy
  - Entity relationships documentation
  - Upsert mechanism in Dgraph
  - File structure & connections
  - CLI commands reference
  - Step-by-step workflow guide
  - Troubleshooting & FAQ

- **Incremental Processing Guide** (`INCREMENTAL_PROCESSING_GUIDE.md`)
  - Detailed explanation of incremental processing
  - Entity linking mechanism
  - Batch processing workflow
  - Real-world examples

- **Practical Examples**
  - Example scripts showing system usage
  - Execution traces for key features
  - Real-world scenario walkthroughs

### 🔧 Changed

- **Architecture**: Modular relationship handlers
  - Separate handlers for judges, advocates, citations, outcomes, case duration
  - Each handler can be tested independently
  - Cleaner code organization

- **ID Generation**: MD5 hash-based stable IDs
  - Content-based IDs instead of counter-based
  - Prevents conflicts across batches
  - Ensures consistency

---

## [1.0.0] - 2025-11-01

### 🎉 Initial Release

#### Core Features

- **FastAPI Application** (`fastapi_app.py`)
  - REST API for document processing
  - Health check endpoints
  - Status monitoring
  - Background task processing

- **Incremental Processor** (`incremental_processor.py`)
  - Process only unprocessed documents
  - Generate RDF files
  - Upload to Dgraph with upsert
  - Mark documents as processed

- **Elasticsearch Handler** (`elasticsearch_handler.py`)
  - Load documents from Elasticsearch
  - Track processing status
  - Query unprocessed documents
  - Update document metadata

- **RDF Generation**
  - Create RDF triples from judgment data
  - Support for multiple entity types (judges, advocates, etc.)
  - Citation relationships
  - Outcome and case duration tracking

- **Dgraph Integration**
  - Upload RDF via Docker Live Loader
  - Upsert mechanism for duplicate prevention
  - Schema management
  - Query support

#### Entity Types Supported

- **Judgment**: Main entity with title, doc_id, year
- **Judge**: Judges who decided cases
- **Advocate**: Petitioner and respondent advocates
- **Citation**: References to other cases
- **Outcome**: Case outcomes (petitioner won, respondent won, etc.)
- **Case Duration**: Duration information

#### Configuration

- Environment variable based configuration (`.env`)
- Configurable Elasticsearch host and index
- Configurable Dgraph host
- Adjustable processing parameters

---

## Upgrade Guide

### Upgrading to 2.1.0 from 2.0.0

**⚠️ Important**: This version includes a critical bug fix that changes how judgment node IDs are generated.

**If you have existing data**:

1. **Backup your data**:
   ```bash
   # Export from Dgraph
   docker exec dgraph-standalone dgraph export -f /dgraph/backup
   ```

2. **Drop existing data** (recommended for clean state):
   ```bash
   curl -X POST http://localhost:8180/alter -d '{"drop_all": true}'
   ```

3. **Re-upload schema**:
   ```bash
   curl -X POST http://localhost:8180/alter -d @rdf.schema
   ```

4. **Reset Elasticsearch status**:
   ```bash
   curl -X POST http://localhost:8003/documents/reset-processed
   ```

5. **Reprocess all documents**:
   ```bash
   curl -X POST http://localhost:8003/process
   ```

**Verification**:

```bash
# Run tests
python3 test_citation_unification.py

# Should show: "🎉 ALL TESTS PASSED!"

# Check for duplicates
curl -X POST http://localhost:8180/query -d '{
  judgments(func: type(Judgment)) {
    title
    count(uid)
  }
}'
```

---

## Known Issues

### [2.1.0]

- **None**: All known issues resolved

### [2.0.0]

- ❌ **Citation-Title Duplication** (FIXED in 2.1.0)
  - Citations and judgments created different nodes for same case
  - Fixed by using title-based IDs for both

---

## Future Plans

### Planned for 2.2.0

- [ ] **Advanced Query Interface**
  - Web-based query builder
  - Saved query templates
  - Export query results

- [ ] **Batch Upload Optimization**
  - Parallel processing for large batches
  - Progress tracking UI
  - Resume interrupted uploads

- [ ] **Enhanced Analytics**
  - Citation network visualization
  - Judge statistics dashboard
  - Case outcome trends

- [ ] **Data Validation**
  - Pre-upload validation
  - Data quality checks
  - Automatic correction suggestions

### Planned for 3.0.0

- [ ] **Machine Learning Integration**
  - Case similarity detection
  - Outcome prediction
  - Entity extraction from case text

- [ ] **Multi-language Support**
  - Hindi language support
  - Regional language support
  - Translation services

- [ ] **Advanced Security**
  - User authentication
  - Role-based access control
  - Audit logging

---

## Migration Notes

### From 1.0.0 to 2.0.0

- **Breaking Change**: ID generation changed from counter-based to hash-based
- **Action Required**: Full data re-upload recommended
- **Benefit**: Stable IDs across batches, no conflicts

### From 2.0.0 to 2.1.0

- **Breaking Change**: Judgment IDs now use title instead of doc_id
- **Action Required**: Full data re-upload recommended to eliminate duplicates
- **Benefit**: No duplicate nodes for citations vs judgments

---

## Contributors

- **Anish DF** - Initial work and all updates

---

## License

This project is licensed under the MIT License.

---

## Support

For issues, questions, or contributions:
- Check logs: `rdf_generator.log`, `elasticsearch_upload.log`
- Review documentation: `DETAILED_README.md`, `QUICK_REFERENCE.md`
- Run tests: `python3 test_citation_unification.py`

**Last Updated**: November 6, 2025  
**Current Version**: 2.1.0  
**Status**: Production Ready ✅
