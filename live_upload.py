import subprocess

# Define the docker live loader command
live_cmd = [
    "docker", "run", "--rm",
    "--network", "dgraph-net",
    "-v", "/home/anish/Desktop/Anish/Dgraph_final:/data",
    "dgraph/dgraph:v23.1.0",
    "dgraph", "live",
    "--files", "/data/judgments.rdf",
    "--schema", "/data/rdf.schema",
    "--alpha", "dgraph-standalone:9080",
    "--zero", "dgraph-standalone:5080",
    "--upsertPredicate", "judgment_id"
]

try:
    print("🚀 Running Dgraph Live Loader...")
    subprocess.run(live_cmd, check=True)
    print("✅ Data loaded successfully into Dgraph!")
except subprocess.CalledProcessError as e:
    print("❌ Error occurred during Dgraph live load:")
    print(e)
