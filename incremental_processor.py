#!/usr/bin/env python3
"""
Incremental RDF Processor for Legal Judgment Database

This module processes only unprocessed documents from Elasticsearch,
generates RDF files, uploads to Dgraph, and marks documents as processed.

Features:
- Process only new/unprocessed documents
- Mark documents as processed automatically
- Support for specific document ID processing
- Force reprocess option

Author: Anish
Date: November 2025
"""

import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from config import config
from models import JudgmentData, ProcessingStats
from elasticsearch_handler import ElasticsearchHandler
from utils import setup_logging, sanitize_string, parse_list_data, create_node_id, format_rdf_triple, print_processing_summary

# Import relationship handlers
from relationships import (
    JudgeRelationshipHandler,
    AdvocateRelationshipHandler,
    OutcomeRelationshipHandler,
    CaseDurationRelationshipHandler,
    CitationRelationshipHandler
)


class IncrementalRDFProcessor:
    """
    Incremental RDF Processor that only processes unprocessed documents.
    """
    
    def __init__(self):
        """Initialize the Incremental RDF Processor."""
        self.logger = setup_logging()
        self.output_config = config.get_output_config()
        self.processing_config = config.get_processing_config()
        
        # Initialize relationship handlers
        self.judge_handler = JudgeRelationshipHandler()
        self.advocate_handler = AdvocateRelationshipHandler()
        self.outcome_handler = OutcomeRelationshipHandler()
        self.case_duration_handler = CaseDurationRelationshipHandler()
        self.citation_handler = CitationRelationshipHandler()
        
        # Initialize data structures
        self.rdf_lines: List[str] = []
        self.judgment_data: List[JudgmentData] = []
        self.title_to_judgment_map: Dict[str, str] = {}
        self.processed_doc_ids: List[str] = []
        
        # Initialize statistics
        self.stats = ProcessingStats()
        
        self.logger.info("🔄 Incremental RDF Processor initialized")
    
    def process_incremental(
        self, 
        doc_ids: Optional[List[str]] = None,
        force_reprocess: bool = False,
        auto_upload: bool = True,
        append_mode: bool = False,
        cleanup_rdf: bool = True
    ) -> Dict:
        """
        Process documents incrementally (only unprocessed ones).
        
        Each run creates a FRESH RDF file with only the new documents.
        Dgraph upsert handles linking to existing nodes automatically.
        
        Args:
            doc_ids: Optional list of specific document IDs to process
            force_reprocess: If True, reprocess even if already processed
            auto_upload: If True, automatically upload to Dgraph
            append_mode: If True, append to existing RDF file (default: False - create fresh file)
            cleanup_rdf: If True, delete RDF file after successful upload (default: True)
            
        Returns:
            Dictionary with processing statistics
        """
        try:
            self.logger.info("🚀 Starting incremental RDF processing...")
            self.logger.info(f"   • Processing mode: {'Specific documents' if doc_ids else 'All unprocessed'}")
            self.logger.info(f"   • Force reprocess: {force_reprocess}")
            self.logger.info(f"   • Auto upload: {auto_upload}")
            
            # Initialize Elasticsearch handler
            es_handler = ElasticsearchHandler()
            
            # Load documents based on mode
            if doc_ids:
                self.logger.info(f"📖 Loading {len(doc_ids)} specific documents...")
                if force_reprocess:
                    # Reset processed status for these documents first
                    es_handler.reset_processed_status(doc_ids)
                df = es_handler.load_documents(doc_ids=doc_ids)
                self.processed_doc_ids = doc_ids
            else:
                # Load only unprocessed documents
                self.logger.info("📖 Loading unprocessed documents...")
                df = es_handler.load_unprocessed_documents()
                
                if df.empty:
                    self.logger.info("✅ No unprocessed documents found. All documents are up to date!")
                    return {
                        "status": "success",
                        "message": "No unprocessed documents",
                        "documents_processed": 0,
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Extract ES IDs for marking as processed later
                # Note: We'll need to track the ES _id values
                # For now, we'll use doc_id as proxy
                self.processed_doc_ids = df['doc_id'].tolist()
            
            self.logger.info(f"✅ Found {len(df)} documents to process")
            
            # Process documents
            self._collect_judgment_data(df)
            self._process_judgments_and_relationships()
            self._combine_all_triples()
            self._calculate_final_stats()
            self._write_rdf_file(append_mode=append_mode)
            
            # Upload to Dgraph if enabled
            if auto_upload:
                self._upload_to_dgraph()
                
                # Mark documents as processed only after successful upload
                self.logger.info("📝 Marking documents as processed in Elasticsearch...")
                updated_count = es_handler.mark_documents_as_processed(self.processed_doc_ids)
                self.logger.info(f"✅ Marked {updated_count} documents as processed")
                
                # Clean up RDF file after successful upload
                if cleanup_rdf:
                    self._cleanup_rdf_file()
            
            # Print summary
            self._print_summary()
            
            # Return statistics
            return {
                "status": "success",
                "message": f"Successfully processed {self.stats.total_judgments} documents",
                "documents_processed": self.stats.total_judgments,
                "documents_marked": updated_count if auto_upload else 0,
                "stats": {
                    "judgments": self.stats.total_judgments,
                    "judges": self.stats.total_judges,
                    "petitioner_advocates": self.stats.total_petitioner_advocates,
                    "respondant_advocates": self.stats.total_respondant_advocates,
                    "outcomes": self.stats.total_outcomes,
                    "case_durations": self.stats.total_case_durations,
                    "citations": self.stats.total_citations,
                    "total_triples": self.stats.total_triples
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Incremental processing failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "documents_processed": 0,
                "timestamp": datetime.now().isoformat()
            }
    
    def _collect_judgment_data(self, df) -> None:
        """
        First pass: Collect all judgment data and build mappings.
        
        Args:
            df: DataFrame containing Elasticsearch data
        """
        self.logger.info("🔄 First pass: Collecting judgment data and building mappings...")
        
        for idx, row in df.iterrows():
            # Extract basic data
            title = sanitize_string(row.get('title', 'Untitled'))
            doc_id = sanitize_string(row.get('doc_id', 'unknown'))
            year = row.get('year') if row.get('year') is not None else None
            case_duration = sanitize_string(row.get('case_duration', ''))
            outcome = sanitize_string(row.get('outcome', ''))
            
            # Process list fields
            citations = row.get('citations', []) if isinstance(row.get('citations'), list) else parse_list_data(str(row.get('citations', '')))
            judges = row.get('judges', []) if isinstance(row.get('judges'), list) else parse_list_data(str(row.get('judges', '')))
            petitioner_advocates = row.get('petitioner_advocates', []) if isinstance(row.get('petitioner_advocates'), list) else parse_list_data(str(row.get('petitioner_advocates', '')))
            respondant_advocates = row.get('respondant_advocates', []) if isinstance(row.get('respondant_advocates'), list) else parse_list_data(str(row.get('respondant_advocates', '')))
            
            # Use doc_id to create stable, unique judgment node IDs
            judgment_node = create_node_id('judgment', unique_key=doc_id)
            
            # Create judgment data object
            judgment_data = JudgmentData(
                idx=idx,
                title=title,
                doc_id=doc_id,
                year=year,
                raw_citations=str(citations),
                judge_name=str(judges),
                petitioner_advocate=str(petitioner_advocates),
                respondant_advocate=str(respondant_advocates),
                case_duration=case_duration,
                outcome=outcome,
                judgment_node=judgment_node
            )
            
            self.judgment_data.append(judgment_data)
            
            # Build title mapping for cross-referencing
            if title:
                self.title_to_judgment_map[title.lower()] = judgment_node
        
        # Set title mapping for citation handler
        self.citation_handler.set_title_mapping(self.title_to_judgment_map)
        
        self.stats.total_judgments = len(self.judgment_data)
        self.logger.info(f"✅ Collected {self.stats.total_judgments} judgments and built mappings")
    
    def _process_judgments_and_relationships(self) -> None:
        """
        Second pass: Generate RDF triples for all entities and relationships using modular handlers.
        """
        self.logger.info("🔄 Second pass: Processing judgments using modular relationship handlers...")
        
        for judgment in self.judgment_data:
            self.logger.info(f"✓ Processing judgment {judgment.idx + 1}: {judgment.title[:50]}...")
            
            # Create judgment triples
            self._create_judgment_triples(judgment)
            
            # Use modular handlers for relationships
            self._process_judge_relationships(judgment)
            self._process_advocate_relationships(judgment)
            self._process_outcome_relationships(judgment)
            self._process_case_duration_relationships(judgment)
            self._process_citation_relationships(judgment)
    
    def _create_judgment_triples(self, judgment: JudgmentData) -> None:
        """Create RDF triples for a judgment with timestamp."""
        from datetime import datetime
        
        node = judgment.judgment_node
        
        judgment_triples = [
            format_rdf_triple(node, 'judgment_id', node),
            format_rdf_triple(node, 'title', judgment.title),
            format_rdf_triple(node, 'doc_id', judgment.doc_id),
            format_rdf_triple(node, 'dgraph.type', 'Judgment'),
            format_rdf_triple(node, 'processed_timestamp', datetime.now().isoformat())
        ]
        
        if judgment.year is not None:
            judgment_triples.append(format_rdf_triple(node, 'year', str(judgment.year)))
        
        self.rdf_lines.extend(judgment_triples)
    
    def _process_judge_relationships(self, judgment: JudgmentData) -> None:
        """Process judge relationships using the dedicated handler."""
        try:
            relationship_triples = self.judge_handler.create_judge_relationships(judgment)
        except Exception as e:
            self.logger.error(f"❌ Error processing judge relationships for {judgment.title}: {e}")
    
    def _process_advocate_relationships(self, judgment: JudgmentData) -> None:
        """Process advocate relationships using the dedicated handler."""
        try:
            relationship_triples = self.advocate_handler.create_advocate_relationships(judgment)
        except Exception as e:
            self.logger.error(f"❌ Error processing advocate relationships for {judgment.title}: {e}")
    
    def _process_outcome_relationships(self, judgment: JudgmentData) -> None:
        """Process outcome relationships using the dedicated handler."""
        try:
            relationship_triples = self.outcome_handler.create_outcome_relationship(judgment)
        except Exception as e:
            self.logger.error(f"❌ Error processing outcome relationships for {judgment.title}: {e}")
    
    def _process_case_duration_relationships(self, judgment: JudgmentData) -> None:
        """Process case duration relationships using the dedicated handler."""
        try:
            relationship_triples = self.case_duration_handler.create_case_duration_relationship(judgment)
        except Exception as e:
            self.logger.error(f"❌ Error processing case duration relationships for {judgment.title}: {e}")
    
    def _process_citation_relationships(self, judgment: JudgmentData) -> None:
        """Process citation relationships using the dedicated handler."""
        try:
            relationship_triples = self.citation_handler.create_citation_relationships(judgment)
        except Exception as e:
            self.logger.error(f"❌ Error processing citation relationships for {judgment.title}: {e}")
    
    def _combine_all_triples(self) -> None:
        """Combine all RDF triples from different handlers."""
        self.logger.info("🔄 Combining RDF triples from all relationship handlers...")
        
        # Get triples from each handler
        judge_triples = self.judge_handler.get_all_rdf_triples()
        advocate_triples = self.advocate_handler.get_all_rdf_triples()
        outcome_triples = self.outcome_handler.get_all_rdf_triples()
        case_duration_triples = self.case_duration_handler.get_all_rdf_triples()
        citation_triples = self.citation_handler.get_all_rdf_triples()
        
        # Get relationship triples by re-processing
        all_relationship_triples = []
        for judgment in self.judgment_data:
            all_relationship_triples.extend(self.judge_handler.create_judge_relationships(judgment))
            all_relationship_triples.extend(self.advocate_handler.create_advocate_relationships(judgment))
            all_relationship_triples.extend(self.outcome_handler.create_outcome_relationship(judgment))
            all_relationship_triples.extend(self.case_duration_handler.create_case_duration_relationship(judgment))
            all_relationship_triples.extend(self.citation_handler.create_citation_relationships(judgment))
        
        # Combine all triples
        self.rdf_lines.extend(judge_triples)
        self.rdf_lines.extend(advocate_triples)
        self.rdf_lines.extend(outcome_triples)
        self.rdf_lines.extend(case_duration_triples)
        self.rdf_lines.extend(citation_triples)
        self.rdf_lines.extend(all_relationship_triples)
        
        self.logger.info(f"✅ Combined {len(self.rdf_lines)} total RDF triples")
    
    def _calculate_final_stats(self) -> None:
        """Calculate final processing statistics from all handlers."""
        judge_stats = self.judge_handler.get_statistics()
        advocate_stats = self.advocate_handler.get_statistics()
        outcome_stats = self.outcome_handler.get_statistics()
        case_duration_stats = self.case_duration_handler.get_statistics()
        citation_stats = self.citation_handler.get_statistics()
        
        self.stats.total_judges = judge_stats['total_judges']
        self.stats.total_petitioner_advocates = advocate_stats['total_petitioner_advocates']
        self.stats.total_respondant_advocates = advocate_stats['total_respondant_advocates']
        self.stats.total_outcomes = outcome_stats['total_outcomes']
        self.stats.total_case_durations = case_duration_stats['total_case_durations']
        self.stats.total_citations = citation_stats['total_citations']
        self.stats.total_triples = len(self.rdf_lines)
        
        self.stats.judge_relationships = judge_stats['judge_relationships']
        self.stats.petitioner_advocate_relationships = advocate_stats['petitioner_advocate_relationships']
        self.stats.respondant_advocate_relationships = advocate_stats['respondant_advocate_relationships']
        self.stats.outcome_relationships = outcome_stats['outcome_relationships']
        self.stats.case_duration_relationships = case_duration_stats['case_duration_relationships']
        self.stats.citation_matches = citation_stats['citation_matches']
        self.stats.title_matches = citation_stats['title_matches']
    
    def _write_rdf_file(self, append_mode: bool = False) -> None:
        """
        Write RDF triples to output file.
        
        Args:
            append_mode: If True, append to existing file instead of overwriting
        """
        try:
            output_file = Path(self.output_config['rdf_file'])
            mode = "a" if append_mode else "w"
            action = "Appending to" if append_mode else "Writing"
            
            self.logger.info(f"💾 {action} RDF file: {output_file}")
            
            with open(output_file, mode, encoding="utf-8") as f:
                # Add separator comment for append mode
                if append_mode:
                    from datetime import datetime
                    f.write(f"\n# === Incremental update: {datetime.now().isoformat()} ===\n")
                
                for line in self.rdf_lines:
                    f.write(line + "\n")
            
            self.logger.info(f"✅ RDF file written successfully ({len(self.rdf_lines)} triples)")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to write RDF file: {e}")
            raise
    
    def _upload_to_dgraph(self) -> None:
        """
        Upload RDF file to Dgraph using Docker Live Loader.
        Uses upsert predicates to avoid duplicate nodes and properly link new documents to existing entities.
        """
        try:
            self.logger.info("🚀 Starting Dgraph Live Loader upload...")
            self.logger.info("   ℹ️  Using upsert mode to link new documents with existing nodes")
            
            current_dir = Path.cwd().absolute()
            
            # Get configuration
            dgraph_config = config.get_dgraph_config()
            docker_config = config.get_docker_config()
            output_config = config.get_output_config()
            
            # Build command with all upsert predicates
            # This ensures that when new documents reference existing entities (judges, advocates, etc.),
            # they link to the existing nodes instead of creating duplicates
            live_cmd = [
                "docker", "run", "--rm",
                "--network", docker_config['network'],
                "-v", f"{current_dir}:/data",
                docker_config['dgraph_image'],
                "dgraph", "live",
                "--files", f"/data/{output_config['rdf_file']}",
                "--schema", f"/data/{output_config['schema_file']}",
                "--alpha", dgraph_config['host'],
                "--zero", dgraph_config['zero'],
                # Upsert predicates ensure no duplicates for these unique identifiers
                "--upsertPredicate", "judgment_id",  # Link new citations to existing judgments
                "--upsertPredicate", "doc_id",        # Prevent duplicate documents
                "--upsertPredicate", "judge_id",      # Link to existing judges
                "--upsertPredicate", "advocate_id",   # Link to existing advocates
                "--upsertPredicate", "outcome_id",    # Link to existing outcomes
                "--upsertPredicate", "case_duration_id"  # Link to existing case durations
            ]
            
            self.logger.info("   🔗 Upsert predicates enabled for: judgment_id, doc_id, judge_id, advocate_id, outcome_id, case_duration_id")
            
            result = subprocess.run(live_cmd, capture_output=True, text=True, check=True)
            
            self.logger.info("✅ Data loaded successfully into Dgraph!")
            self.logger.info("   ℹ️  New documents are now linked to existing nodes (judges, advocates, etc.)")
            self.logger.info(f"📤 Upload output: {result.stdout}")
            
            if result.stderr:
                self.logger.warning(f"⚠️ Upload warnings: {result.stderr}")
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Error occurred during Dgraph live load: {e}")
            if e.stdout:
                self.logger.error(f"📤 Stdout: {e.stdout}")
            if e.stderr:
                self.logger.error(f"📤 Stderr: {e.stderr}")
            raise
        except Exception as e:
            self.logger.error(f"❌ Unexpected error during Dgraph upload: {e}")
            raise
    
    def _cleanup_rdf_file(self) -> None:
        """
        Clean up RDF file after successful upload to keep workspace clean.
        The file is backed up with timestamp before deletion.
        """
        try:
            output_file = Path(self.output_config['rdf_file'])
            
            if not output_file.exists():
                self.logger.info("ℹ️  No RDF file to clean up")
                return
            
            # Create backup with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = output_file.parent / f"{output_file.stem}_backup_{timestamp}{output_file.suffix}"
            
            # Move file to backup
            import shutil
            shutil.move(str(output_file), str(backup_file))
            
            self.logger.info(f"🗑️  RDF file backed up to: {backup_file}")
            self.logger.info(f"✅ Workspace cleaned - RDF file removed")
            self.logger.info(f"   ℹ️  Data is safely stored in Dgraph. RDF backup available if needed.")
            
        except Exception as e:
            self.logger.warning(f"⚠️  Failed to clean up RDF file: {e}")
            self.logger.info("   ℹ️  This is not critical - RDF file can be manually deleted")
    
    def _print_summary(self) -> None:
        """Print processing summary."""
        stats_dict = {
            'total_judgments': self.stats.total_judgments,
            'total_judges': self.stats.total_judges,
            'total_petitioner_advocates': self.stats.total_petitioner_advocates,
            'total_respondant_advocates': self.stats.total_respondant_advocates,
            'total_outcomes': self.stats.total_outcomes,
            'total_case_durations': self.stats.total_case_durations,
            'total_triples': self.stats.total_triples
        }
        
        print_processing_summary(stats_dict, self.output_config['rdf_file'])
        
        print("\n" + "=" * 70)
        print("🔄 INCREMENTAL PROCESSING COMPLETED")
        print("=" * 70)
        print(f"✅ Processed {self.stats.total_judgments} new/updated documents")
        print(f"📊 Generated {self.stats.total_triples} RDF triples")
        print(f"📝 Documents marked as processed in Elasticsearch")
        print("=" * 70)


def main():
    """Main function for standalone execution."""
    try:
        if not config.validate():
            sys.exit(1)
        
        processor = IncrementalRDFProcessor()
        result = processor.process_incremental()
        
        print("\n" + "=" * 70)
        print("📊 PROCESSING RESULT")
        print("=" * 70)
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        print(f"Documents processed: {result['documents_processed']}")
        print("=" * 70)
        
    except Exception as e:
        logger = setup_logging()
        logger.error(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
