#!/usr/bin/env python3
"""
Generate RDF for legal judgments and citations in simple format compatible with dgraph live.
This script creates nodes with simple names (j1, j2, c1, c2) but with angle brackets 
required by dgraph live tool.
"""

import pandas as pd
import json
import ast

# Read the Excel file
print("📖 Loading Excel file...")
df = pd.read_excel("/home/anish/Desktop/Anish/Dgraph_final/excel_2024_2025/FINAL/5_sample/tests.xlsx")

print(f"✅ Loaded {len(df)} rows from Excel file")

# Initialize RDF generation
rdf_lines = []
citation_map = {}  # Maps citation text to citation node name
title_to_judgment_map = {}  # Maps title text to judgment node name
judgment_data = []  # Store all judgment data for two-pass processing
citation_counter = 1

# First pass: Collect all judgment data and titles
print("🔄 First pass: Collecting all judgment titles...")
for idx, row in df.iterrows():
    title = str(row.get('Title', 'Untitled')).strip()
    doc_id = str(row.get('doc_id', 'unknown')).strip()
    year = row.get('Year')
    raw_citations = str(row.get('Citation', '[]')).strip()
    
    judgment_node = f"j{idx+1}"
    
    # Store judgment data for second pass
    judgment_data.append({
        'idx': idx,
        'title': title,
        'doc_id': doc_id,
        'year': year,
        'raw_citations': raw_citations,
        'judgment_node': judgment_node
    })
    
    # Map title to judgment node for cross-referencing
    title_to_judgment_map[title.lower()] = judgment_node
    
print(f"✅ Collected {len(judgment_data)} judgments and their titles")

# Second pass: Generate RDF with title-citation cross-referencing
print("🔄 Second pass: Processing judgments and citations...")
for judgment in judgment_data:
    idx = judgment['idx']
    title = judgment['title']
    doc_id = judgment['doc_id']
    year = judgment['year']
    raw_citations = judgment['raw_citations']
    judgment_node = judgment['judgment_node']
    
    print(f"✓ Processing judgment {idx + 1}: {title[:50]}...")
    print(f"  📄 Doc ID: {doc_id}, Year: {year}")

    # Parse citations
    citations = []
    
    # Case 1: JSON-like format with dict
    if raw_citations.startswith('{') or 'cited_cases' in raw_citations:
        try:
            if not raw_citations.startswith('{'):
                raw_citations = '{' + raw_citations + '}'
            citation_data = json.loads(raw_citations.replace("'", '"'))
            citations = citation_data.get("cited_cases", [])
        except Exception as e:
            print(f"  ⚠ Warning: Could not parse JSON citations: {e}")
            citations = []

    # Case 2: plain Python-style list
    elif raw_citations.startswith('['):
        try:
            citations = ast.literal_eval(raw_citations)
        except Exception as e:
            print(f"  ⚠ Warning: Could not parse list citations: {e}")
            citations = []

    # Strip whitespace and escape quotes in titles
    citations = [c.strip() for c in citations if c.strip()]
    escaped_title = title.replace('"', '\\"')
    
    print(f"  → Found {len(citations)} citations")

    # Generate main judgment triples (angle brackets required for dgraph live)
    rdf_lines.append(f'<{judgment_node}> <judgment_id> "{judgment_node}" .')
    rdf_lines.append(f'<{judgment_node}> <title> "{escaped_title}" .')
    rdf_lines.append(f'<{judgment_node}> <doc_id> "{doc_id}" .')
    if year is not None:
        rdf_lines.append(f'<{judgment_node}> <year> "{year}" .')
    rdf_lines.append(f'<{judgment_node}> <dgraph.type> "Judgment" .')

    # Process citations with title-judgment cross-referencing
    title_matches = 0
    citation_matches = 0
    
    for citation in citations:
        escaped_citation = citation.replace('"', '\\"')
        citation_lower = citation.lower()
        
        # ENHANCED LOGIC: Check if citation matches an existing judgment title
        if citation_lower in title_to_judgment_map:
            # Citation matches a judgment title - link to existing judgment
            existing_judgment_node = title_to_judgment_map[citation_lower]
            rdf_lines.append(f'<{judgment_node}> <cites> <{existing_judgment_node}> .')
            title_matches += 1
            print(f"    🎯 Title match: '{citation}' → {existing_judgment_node}")
        else:
            # Citation doesn't match any title - handle as regular citation
            if citation in citation_map:
                citation_node = citation_map[citation]
                citation_matches += 1
            else:
                # Create new citation node
                citation_node = f"c{citation_counter}"
                citation_map[citation] = citation_node
                citation_counter += 1
                
                # Add citation node triples (with angle brackets)
                rdf_lines.append(f'<{citation_node}> <judgment_id> "{citation_node}" .')
                rdf_lines.append(f'<{citation_node}> <title> "{escaped_citation}" .')
                rdf_lines.append(f'<{citation_node}> <dgraph.type> "Judgment" .')
            
            # Add citation relationship
            rdf_lines.append(f'<{judgment_node}> <cites> <{citation_node}> .')
    
    if title_matches > 0 or citation_matches > 0:
        print(f"  📊 Relationships: {title_matches} title matches, {citation_matches} citation matches")

# Calculate statistics
total_title_matches = len([line for line in rdf_lines if 'cites> <j' in line])
total_citation_matches = len([line for line in rdf_lines if 'cites> <c' in line])

# Write RDF file in dgraph live compatible format
output_file = "judgments_simple_dgraph_format.rdf"
with open(output_file, "w", encoding="utf-8") as f:
    for line in rdf_lines:
        f.write(line + "\n")

print("\n" + "=" * 70)
print(f"✅ RDF file generated successfully in dgraph live format!")
print(f"📁 Output file: {output_file}")
print(f"📊 Total judgments: {len(judgment_data)}")
print(f"🔗 Total RDF triples: {len(rdf_lines)}")
print(f"🎯 Unique citations: {citation_counter - 1}")
print(f"🔗 Title-to-judgment matches: {total_title_matches}")
print(f"🔗 Regular citation matches: {total_citation_matches}")
print("=" * 70)
print("🎯 Format features:")
print("   • Simple node names: j1, j2, j3... for judgments")
print("   • Simple node names: c1, c2, c3... for citations")
print("   • Angle brackets around node names (required by dgraph live)")
print("   • Clean, readable format based on sud.rdf style")
print("   • Title-citation cross-referencing for better linkage")
print("✨ No dummy nodes - uses simple sequential identifiers")
print("🔧 Generated in dgraph live compatible format")
print("🔍 Enhanced with title-citation matching logic")
print("=" * 70)
print("🚀 Ready to upload to Dgraph using:")
print("   sudo docker run --rm --network dgraph-net \\")
print("     -v /home/anish/Desktop/Anish/DGRAPH:/data dgraph/dgraph:v23.1.0 \\")
print("     dgraph live --files /data/judgments_simple_dgraph_format.rdf \\")
print("     --schema /data/schema_upsert_dedup.schema \\")
print("     --alpha dgraph-standalone:9080 --zero dgraph-standalone:5080 \\")
print("     --upsertPredicate judgment_id")
print("=" * 70)
