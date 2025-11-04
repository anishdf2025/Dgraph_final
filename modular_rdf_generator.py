#!/usr/bin/env python3
"""
Modular RDF Generator for Legal Judgment Database

This module generates RDF files using separate modular relationship handlers.
Each relationship type is handled by a dedicated module that can be debugged independently.

Features:
- Modular relationship handlers
- Individual debugging capability
- Same logic as original RDF generator
- Easy to expand with new relationship types
- Clean separation of concerns

Author: Anish
Date: November 2025
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

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


class ModularRDFGenerator:
    """
    Modular RDF Generator using separate relationship handlers.
    
    This class processes Elasticsearch data and generates RDF files using
    dedicated handlers for each relationship type.
    """
    
    def __init__(self):
        """Initialize the Modular RDF Generator."""
        self.logger = setup_logging()
        self.es_handler = ElasticsearchHandler()
        self.output_config = config.get_output_config()
        
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
        
        # Initialize statistics
        self.stats = ProcessingStats()
        
        self.logger.info("🚀 Modular RDF Generator initialized with separate relationship handlers")
    
    def generate_rdf(self) -> None:
        """
        Main method to generate RDF file using modular relationship handlers.
        
        Raises:
            Exception: If any step in the process fails
        """
        try:
            self.logger.info("🔄 Starting modular RDF generation process...")
            
            # Load data from Elasticsearch
            df = self.es_handler.load_documents()
            
            # Two-pass processing
            self._collect_judgment_data(df)
            self._process_judgments_and_relationships()
            
            # Combine all RDF triples
            self._combine_all_triples()
            
            # Calculate statistics and write output
            self._calculate_final_stats()
            self._write_rdf_file()
            
            # Print summary
            self._print_summary()
            
            self.logger.info("🎉 Modular RDF generation completed successfully!")
            
        except Exception as e:
            self.logger.error(f"💥 Modular RDF generation failed: {e}")
            raise
    
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
            
            judgment_node = create_node_id('judgment', idx + 1)
            
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
        """Create RDF triples for a judgment."""
        node = judgment.judgment_node
        
        judgment_triples = [
            format_rdf_triple(node, 'judgment_id', node),
            format_rdf_triple(node, 'title', judgment.title),
            format_rdf_triple(node, 'doc_id', judgment.doc_id),
            format_rdf_triple(node, 'dgraph.type', 'Judgment')
        ]
        
        if judgment.year is not None:
            judgment_triples.append(format_rdf_triple(node, 'year', str(judgment.year)))
        
        self.rdf_lines.extend(judgment_triples)
    
    def _process_judge_relationships(self, judgment: JudgmentData) -> None:
        """Process judge relationships using the dedicated handler."""
        try:
            relationship_triples = self.judge_handler.create_judge_relationships(judgment)
            # Note: Judge node triples are handled internally by the handler
        except Exception as e:
            self.logger.error(f"❌ Error processing judge relationships for {judgment.title}: {e}")
    
    def _process_advocate_relationships(self, judgment: JudgmentData) -> None:
        """Process advocate relationships using the dedicated handler."""
        try:
            relationship_triples = self.advocate_handler.create_advocate_relationships(judgment)
            # Note: Advocate node triples are handled internally by the handler
        except Exception as e:
            self.logger.error(f"❌ Error processing advocate relationships for {judgment.title}: {e}")
    
    def _process_outcome_relationships(self, judgment: JudgmentData) -> None:
        """Process outcome relationships using the dedicated handler."""
        try:
            relationship_triples = self.outcome_handler.create_outcome_relationship(judgment)
            # Note: Outcome node triples are handled internally by the handler
        except Exception as e:
            self.logger.error(f"❌ Error processing outcome relationships for {judgment.title}: {e}")
    
    def _process_case_duration_relationships(self, judgment: JudgmentData) -> None:
        """Process case duration relationships using the dedicated handler."""
        try:
            relationship_triples = self.case_duration_handler.create_case_duration_relationship(judgment)
            # Note: Case duration node triples are handled internally by the handler
        except Exception as e:
            self.logger.error(f"❌ Error processing case duration relationships for {judgment.title}: {e}")
    
    def _process_citation_relationships(self, judgment: JudgmentData) -> None:
        """Process citation relationships using the dedicated handler."""
        try:
            relationship_triples = self.citation_handler.create_citation_relationships(judgment)
            # Note: Citation node triples are handled internally by the handler
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
        
        # Get relationship triples by re-processing (they return relationship triples)
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
        # Get stats from each handler
        judge_stats = self.judge_handler.get_statistics()
        advocate_stats = self.advocate_handler.get_statistics()
        outcome_stats = self.outcome_handler.get_statistics()
        case_duration_stats = self.case_duration_handler.get_statistics()
        citation_stats = self.citation_handler.get_statistics()
        
        # Combine statistics
        self.stats.total_judges = judge_stats['total_judges']
        self.stats.total_petitioner_advocates = advocate_stats['total_petitioner_advocates']
        self.stats.total_respondant_advocates = advocate_stats['total_respondant_advocates']
        self.stats.total_outcomes = outcome_stats['total_outcomes']
        self.stats.total_case_durations = case_duration_stats['total_case_durations']
        self.stats.total_citations = citation_stats['total_citations']
        self.stats.total_triples = len(self.rdf_lines)
        
        # Additional relationship stats
        self.stats.judge_relationships = judge_stats['judge_relationships']
        self.stats.petitioner_advocate_relationships = advocate_stats['petitioner_advocate_relationships']
        self.stats.respondant_advocate_relationships = advocate_stats['respondant_advocate_relationships']
        self.stats.outcome_relationships = outcome_stats['outcome_relationships']
        self.stats.case_duration_relationships = case_duration_stats['case_duration_relationships']
        self.stats.citation_matches = citation_stats['citation_matches']
        self.stats.title_matches = citation_stats['title_matches']
    
    def _write_rdf_file(self) -> None:
        """Write RDF triples to output file."""
        try:
            output_file = Path(self.output_config['rdf_file'])
            self.logger.info(f"💾 Writing RDF file: {output_file}")
            
            with open(output_file, "w", encoding="utf-8") as f:
                for line in self.rdf_lines:
                    f.write(line + "\n")
            
            self.logger.info(f"✅ RDF file written successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to write RDF file: {e}")
            raise
    
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
        
        # Print modular handler statistics
        print("\n" + "=" * 70)
        print("📊 MODULAR HANDLER STATISTICS")
        print("=" * 70)
        print(f"👨‍⚖️ Judge relationships: {self.stats.judge_relationships}")
        print(f"👨‍💼 Petitioner advocate relationships: {self.stats.petitioner_advocate_relationships}")
        print(f"👨‍💼 Respondant advocate relationships: {self.stats.respondant_advocate_relationships}")
        print(f"⚖️ Outcome relationships: {self.stats.outcome_relationships}")
        print(f"📅 Case duration relationships: {self.stats.case_duration_relationships}")
        print(f"🔗 Citation matches (external): {self.stats.citation_matches}")
        print(f"🔗 Title matches (internal): {self.stats.title_matches}")
        print("=" * 70)
        print("🔧 Debug individual handlers:")
        print("   • python3 relationships/judge_relationship.py")
        print("   • python3 relationships/advocate_relationship.py")
        print("   • python3 relationships/outcome_relationship.py")
        print("   • python3 relationships/case_duration_relationship.py")
        print("   • python3 relationships/citation_relationship.py")
        print("=" * 70)


def main():
    """Main function to run the modular RDF generator."""
    try:
        # Validate configuration
        if not config.validate():
            sys.exit(1)
        
        # Generate RDF using modular approach
        generator = ModularRDFGenerator()
        generator.generate_rdf()
        
    except Exception as e:
        logger = setup_logging()
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
