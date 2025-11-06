#!/usr/bin/env python3
"""
Example: Incremental Processing Workflow

This script demonstrates how to use the incremental processing system
to add new documents to Dgraph while linking to existing entities.

Author: Anish
Date: November 2025
"""

import sys
from pathlib import Path
from incremental_processor import IncrementalRDFProcessor
from elasticsearch_handler import ElasticsearchHandler
from utils import setup_logging

logger = setup_logging()


def example_1_process_all_unprocessed():
    """
    Example 1: Process all unprocessed documents
    - Loads only documents where processed_to_dgraph=false
    - Generates RDF with proper entity linking
    - Appends to existing RDF file
    - Uploads to Dgraph with upsert
    - Marks documents as processed
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Process All Unprocessed Documents")
    print("=" * 70)
    
    processor = IncrementalRDFProcessor()
    result = processor.process_incremental(
        doc_ids=None,           # Process all unprocessed
        force_reprocess=False,  # Don't reprocess already processed docs
        auto_upload=True,       # Upload to Dgraph
        append_mode=True        # Append to existing RDF file
    )
    
    print(f"\n✅ Result: {result['status']}")
    print(f"📊 Documents processed: {result['documents_processed']}")
    print(f"📝 Documents marked as processed: {result.get('documents_marked', 0)}")
    
    if 'stats' in result:
        stats = result['stats']
        print(f"\n📈 Statistics:")
        print(f"   • Judgments: {stats['judgments']}")
        print(f"   • Judges: {stats['judges']}")
        print(f"   • Petitioner advocates: {stats['petitioner_advocates']}")
        print(f"   • Respondant advocates: {stats['respondant_advocates']}")
        print(f"   • Outcomes: {stats['outcomes']}")
        print(f"   • Citations: {stats['citations']}")
        print(f"   • Total triples: {stats['total_triples']}")


def example_2_process_specific_documents():
    """
    Example 2: Process specific documents by doc_id
    Useful when you want to reprocess specific documents
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Process Specific Documents")
    print("=" * 70)
    
    # First, let's see what documents are available
    es_handler = ElasticsearchHandler()
    unprocessed = es_handler.get_unprocessed_documents(limit=5)
    
    if not unprocessed:
        print("⚠️  No unprocessed documents found. Upload some documents first.")
        return
    
    print(f"\n📋 Found {len(unprocessed)} unprocessed documents:")
    for doc in unprocessed:
        print(f"   • {doc['doc_id']}: {doc['title'][:60]}...")
    
    # Process just the first 2 documents
    doc_ids_to_process = [doc['doc_id'] for doc in unprocessed[:2]]
    
    print(f"\n🔄 Processing {len(doc_ids_to_process)} specific documents...")
    
    processor = IncrementalRDFProcessor()
    result = processor.process_incremental(
        doc_ids=doc_ids_to_process,
        force_reprocess=False,
        auto_upload=True,
        append_mode=True
    )
    
    print(f"\n✅ Result: {result['status']}")
    print(f"📊 Documents processed: {result['documents_processed']}")


def example_3_check_processing_status():
    """
    Example 3: Check processing status
    Shows counts of processed vs unprocessed documents
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Check Processing Status")
    print("=" * 70)
    
    es_handler = ElasticsearchHandler()
    counts = es_handler.get_processing_counts()
    
    print(f"\n📊 Processing Status:")
    print(f"   • Total documents: {counts['total']}")
    print(f"   • Processed: {counts['processed']} ({counts['processed']/max(counts['total'], 1)*100:.1f}%)")
    print(f"   • Unprocessed: {counts['unprocessed']} ({counts['unprocessed']/max(counts['total'], 1)*100:.1f}%)")
    
    # Show some unprocessed documents
    if counts['unprocessed'] > 0:
        print(f"\n📋 Sample unprocessed documents:")
        unprocessed = es_handler.get_unprocessed_documents(limit=5)
        for i, doc in enumerate(unprocessed, 1):
            print(f"   {i}. {doc['doc_id']}: {doc['title'][:60]}...")


def example_4_reprocess_documents():
    """
    Example 4: Force reprocess documents
    Useful when you want to regenerate RDF for already processed documents
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Force Reprocess Documents")
    print("=" * 70)
    
    es_handler = ElasticsearchHandler()
    unprocessed = es_handler.get_unprocessed_documents(limit=1)
    
    if not unprocessed:
        print("⚠️  No documents available for this example.")
        return
    
    doc_id = unprocessed[0]['doc_id']
    print(f"\n🔄 Force reprocessing document: {doc_id}")
    
    processor = IncrementalRDFProcessor()
    result = processor.process_incremental(
        doc_ids=[doc_id],
        force_reprocess=True,   # Reprocess even if already processed
        auto_upload=True,
        append_mode=True
    )
    
    print(f"\n✅ Result: {result['status']}")
    print(f"📊 Document reprocessed successfully")


def example_5_fresh_start():
    """
    Example 5: Generate fresh RDF file (overwrite mode)
    Use this when you want to regenerate the entire RDF file from scratch
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Generate Fresh RDF File")
    print("=" * 70)
    print("⚠️  WARNING: This will overwrite the existing RDF file!")
    print("    Use this only when you want to regenerate everything from scratch.")
    
    response = input("\n❓ Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    # Reset all documents to unprocessed
    es_handler = ElasticsearchHandler()
    reset_count = es_handler.reset_processed_status()
    print(f"\n🔄 Reset {reset_count} documents to unprocessed status")
    
    # Process all documents with overwrite mode
    processor = IncrementalRDFProcessor()
    result = processor.process_incremental(
        doc_ids=None,
        force_reprocess=False,
        auto_upload=True,
        append_mode=False  # Overwrite existing RDF file
    )
    
    print(f"\n✅ Result: {result['status']}")
    print(f"📊 Documents processed: {result['documents_processed']}")
    print(f"📝 Fresh RDF file generated!")


def main():
    """Main function to run examples."""
    print("\n" + "=" * 70)
    print("INCREMENTAL PROCESSING EXAMPLES")
    print("=" * 70)
    print("\nChoose an example to run:")
    print("1. Process all unprocessed documents")
    print("2. Process specific documents")
    print("3. Check processing status")
    print("4. Force reprocess documents")
    print("5. Generate fresh RDF file (overwrite)")
    print("0. Exit")
    
    choice = input("\nEnter choice (0-5): ").strip()
    
    if choice == "1":
        example_1_process_all_unprocessed()
    elif choice == "2":
        example_2_process_specific_documents()
    elif choice == "3":
        example_3_check_processing_status()
    elif choice == "4":
        example_4_reprocess_documents()
    elif choice == "5":
        example_5_fresh_start()
    elif choice == "0":
        print("\n👋 Goodbye!")
        sys.exit(0)
    else:
        print("\n❌ Invalid choice")
        return
    
    # Ask if user wants to run another example
    print("\n" + "=" * 70)
    again = input("Run another example? (yes/no): ").strip().lower()
    if again == "yes":
        main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)
