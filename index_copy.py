from elasticsearch import Elasticsearch

# ----------------------------
# Config
# ----------------------------
ES_HOST = "http://localhost:9200"
SOURCE_INDEX = "graphdb"
DEST_INDEX = "graphdb_copy"

# ----------------------------
# Connect to Elasticsearch
# ----------------------------
es = Elasticsearch(ES_HOST)

# ----------------------------
# Step 1: Get original settings & mappings
# ----------------------------
if not es.indices.exists(index=SOURCE_INDEX):
    raise Exception(f"❌ Source index '{SOURCE_INDEX}' does not exist.")

source_settings = es.indices.get(index=SOURCE_INDEX)[SOURCE_INDEX]
settings = source_settings.get("settings", {}).get("index", {})
mappings = source_settings.get("mappings", {})

# Remove properties Elasticsearch doesn't allow when creating new index
for key in ["uuid", "version", "creation_date"]:
    settings.pop(key, None)

# ----------------------------
# Step 2: Create destination index with same settings & mappings
# ----------------------------
if es.indices.exists(index=DEST_INDEX):
    print(f"⚠️ Index '{DEST_INDEX}' already exists. Skipping creation.")
else:
    es.indices.create(
        index=DEST_INDEX,
        body={
            "settings": {"number_of_shards": settings.get("number_of_shards", 1),
                         "number_of_replicas": settings.get("number_of_replicas", 1)},
            "mappings": mappings
        }
    )
    print(f"✅ Created new index '{DEST_INDEX}' with same mappings & settings as '{SOURCE_INDEX}'")

# ----------------------------
# Step 3: Copy all data (Reindex API)
# ----------------------------
print(f"🚀 Copying data from '{SOURCE_INDEX}' → '{DEST_INDEX}'...")
response = es.reindex(
    body={
        "source": {"index": SOURCE_INDEX},
        "dest": {"index": DEST_INDEX}
    },
    wait_for_completion=True,
    request_timeout=1800
)
print("✅ Reindex completed:", response)

# ----------------------------
# Step 4: Verify document count
# ----------------------------
src_count = es.count(index=SOURCE_INDEX)["count"]
dst_count = es.count(index=DEST_INDEX)["count"]
print(f"📊 Source: {src_count} docs | Copy: {dst_count} docs")
