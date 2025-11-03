#!/usr/bin/env python3
"""
RDF Generator for Legal Judgment Database (Refactored)

This module generates RDF files from Elasticsearch data containing legal judgments, citations,
judges, advocates, outcomes, and case durations in a format compatible with Dgraph Live Loader.

Features:
- Clean separation of concerns
- Environment-based configuration
- Optimized data processing
- Best practices implementation

Author: Anish
Date: November 2025
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

from config import config
from models import JudgmentData, ProcessingStats, NodeMapping
from elasticsearch_handler import ElasticsearchHandler
from utils import setup_logging, sanitize_string, parse_list_data, create_node_id, format_rdf_triple, print_processing_summary


class RDFGenerator:
    """
    RDF Generator for Legal Judgment Database.
    
    This class processes Elasticsearch data and generates RDF files compatible with Dgraph Live Loader.
    """
    
    def __init__(self):
        """Initialize the RDF Generator."""
        self.logger = setup_logging()
        self.es_handler = ElasticsearchHandler()
        self.output_config = config.get_output_config()
        
        # Initialize data structures
        self.rdf_lines: List[str] = []
        self.judgment_data: List[JudgmentData] = []
        self.node_mappings = NodeMapping(
            citation_map={},
            title_to_judgment_map={},
            judge_map={},
            petitioner_advocate_map={},
            respondant_advocate_map={},
            outcome_map={},
            case_duration_map={}
        )
        
        # Initialize counters
        self.counters = {
            'citation': 1,
            'judge': 1,
            'petitioner_advocate': 1,
            'respondant_advocate': 1,
            'outcome': 1,
            'case_duration': 1
        }
        
        # Initialize statistics
        self.stats = ProcessingStats()
        
        self.logger.info("🚀 RDF Generator initialized with Elasticsearch backend")
    
    def generate_rdf(self) -> None:
        """
        Main method to generate RDF file from Elasticsearch data.
        
        Raises:
            Exception: If any step in the process fails
        """
        try:
            self.logger.info("🔄 Starting RDF generation process...")
            
            # Load data from Elasticsearch
            df = self.es_handler.load_documents()
            
            # Two-pass processing
            self._collect_judgment_data(df)
            self._process_judgments_and_relationships()
            
            # Calculate statistics and write output
            self._calculate_final_stats()
            self._write_rdf_file()
            
            # Print summary
            self._print_summary()
            
            self.logger.info("🎉 RDF generation completed successfully!")
            
        except Exception as e:
            self.logger.error(f"💥 RDF generation failed: {e}")
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
                self.node_mappings.title_to_judgment_map[title.lower()] = judgment_node
        
        self.stats.total_judgments = len(self.judgment_data)
        self.logger.info(f"✅ Collected {self.stats.total_judgments} judgments and built mappings")
    
    def _process_judgments_and_relationships(self) -> None:
        """
        Second pass: Generate RDF triples for all entities and relationships.
        """
        self.logger.info("🔄 Second pass: Processing judgments and creating relationships...")
        
        for judgment in self.judgment_data:
            self.logger.info(f"✓ Processing judgment {judgment.idx + 1}: {judgment.title[:50]}...")
            
            # Create judgment triples
            self._create_judgment_triples(judgment)
            
            # Create all relationships
            self._create_judge_relationships(judgment)
            self._create_advocate_relationships(judgment)
            self._create_outcome_relationship(judgment)
            self._create_case_duration_relationship(judgment)
            self._create_citation_relationships(judgment)
    
    def _create_judgment_triples(self, judgment: JudgmentData) -> None:
        """Create RDF triples for a judgment."""
        node = judgment.judgment_node
        
        self.rdf_lines.extend([
            format_rdf_triple(node, 'judgment_id', node),
            format_rdf_triple(node, 'title', judgment.title),
            format_rdf_triple(node, 'doc_id', judgment.doc_id),
            format_rdf_triple(node, 'dgraph.type', 'Judgment')
        ])
        
        if judgment.year is not None:
            self.rdf_lines.append(format_rdf_triple(node, 'year', str(judgment.year)))
    
    def _create_judge_relationships(self, judgment: JudgmentData) -> None:
        """Create judge nodes and relationships."""
        judges = parse_list_data(judgment.judge_name)
        
        for judge_name in judges:
            if not judge_name:
                continue
            
            judge_node = self._get_or_create_node('judge', judge_name, {
                'judge_id': lambda node: node,
                'name': lambda _: judge_name,
                'dgraph.type': lambda _: 'Judge'
            })
            
            self.rdf_lines.append(format_rdf_triple(judgment.judgment_node, 'judged_by', judge_node, False))
            self.stats.judge_relationships += 1
    
    def _create_advocate_relationships(self, judgment: JudgmentData) -> None:
        """Create advocate nodes and relationships."""
        # Petitioner advocates
        petitioner_advocates = parse_list_data(judgment.petitioner_advocate)
        for advocate_name in petitioner_advocates:
            if not advocate_name:
                continue
            
            advocate_node = self._get_or_create_node('petitioner_advocate', advocate_name, {
                'advocate_id': lambda node: node,
                'name': lambda _: advocate_name,
                'advocate_type': lambda _: 'Petitioner',
                'dgraph.type': lambda _: 'Advocate'
            })
            
            self.rdf_lines.append(format_rdf_triple(judgment.judgment_node, 'petitioner_represented_by', advocate_node, False))
            self.stats.petitioner_advocate_relationships += 1
        
        # Respondant advocates
        respondant_advocates = parse_list_data(judgment.respondant_advocate)
        for advocate_name in respondant_advocates:
            if not advocate_name:
                continue
            
            advocate_node = self._get_or_create_node('respondant_advocate', advocate_name, {
                'advocate_id': lambda node: node,
                'name': lambda _: advocate_name,
                'advocate_type': lambda _: 'Respondant',
                'dgraph.type': lambda _: 'Advocate'
            })
            
            self.rdf_lines.append(format_rdf_triple(judgment.judgment_node, 'respondant_represented_by', advocate_node, False))
            self.stats.respondant_advocate_relationships += 1
    
    def _create_outcome_relationship(self, judgment: JudgmentData) -> None:
        """Create outcome node and relationship."""
        if not judgment.outcome or judgment.outcome.lower() == 'nan':
            return
        
        outcome_node = self._get_or_create_node('outcome', judgment.outcome, {
            'outcome_id': lambda node: node,
            'name': lambda _: judgment.outcome,
            'dgraph.type': lambda _: 'Outcome'
        })
        
        self.rdf_lines.append(format_rdf_triple(judgment.judgment_node, 'has_outcome', outcome_node, False))
        self.stats.outcome_relationships += 1
    
    def _create_case_duration_relationship(self, judgment: JudgmentData) -> None:
        """Create case duration node and relationship."""
        if not judgment.case_duration or judgment.case_duration.lower() == 'nan':
            return
        
        duration_node = self._get_or_create_node('case_duration', judgment.case_duration, {
            'case_duration_id': lambda node: node,
            'duration': lambda _: judgment.case_duration,
            'dgraph.type': lambda _: 'CaseDuration'
        })
        
        self.rdf_lines.append(format_rdf_triple(judgment.judgment_node, 'has_case_duration', duration_node, False))
        self.stats.case_duration_relationships += 1
    
    def _create_citation_relationships(self, judgment: JudgmentData) -> None:
        """Create citation nodes and relationships."""
        citations = parse_list_data(judgment.raw_citations)
        
        for citation in citations:
            citation_lower = citation.lower()
            
            # Check for title matches first
            if citation_lower in self.node_mappings.title_to_judgment_map:
                existing_judgment_node = self.node_mappings.title_to_judgment_map[citation_lower]
                self.rdf_lines.append(format_rdf_triple(judgment.judgment_node, 'cites', existing_judgment_node, False))
                self.stats.title_matches += 1
            else:
                # Create citation node
                citation_node = self._get_or_create_node('citation', citation, {
                    'judgment_id': lambda node: node,
                    'title': lambda _: citation,
                    'dgraph.type': lambda _: 'Judgment'
                })
                
                self.rdf_lines.append(format_rdf_triple(judgment.judgment_node, 'cites', citation_node, False))
                self.stats.citation_matches += 1
    
    def _get_or_create_node(self, node_type: str, key: str, properties: Dict) -> str:
        """
        Get existing node or create a new one.
        
        Args:
            node_type: Type of node
            key: Unique key for the node
            properties: Properties to set if creating new node
            
        Returns:
            str: Node identifier
        """
        mapping_attr = f"{node_type}_map"
        if hasattr(self.node_mappings, mapping_attr):
            node_map = getattr(self.node_mappings, mapping_attr)
        else:
            node_map = self.node_mappings.citation_map  # fallback
        
        if key in node_map:
            return node_map[key]
        
        # Create new node
        node_id = create_node_id(node_type, self.counters[node_type])
        node_map[key] = node_id
        self.counters[node_type] += 1
        
        # Add node properties
        for prop, value_func in properties.items():
            value = value_func(node_id)
            self.rdf_lines.append(format_rdf_triple(node_id, prop, value))
        
        self.logger.info(f"📄 Created {node_type} node: {node_id} for '{key[:50]}...'")
        return node_id
    
    def _calculate_final_stats(self) -> None:
        """Calculate final processing statistics."""
        self.stats.total_judges = self.counters['judge'] - 1
        self.stats.total_petitioner_advocates = self.counters['petitioner_advocate'] - 1
        self.stats.total_respondant_advocates = self.counters['respondant_advocate'] - 1
        self.stats.total_outcomes = self.counters['outcome'] - 1
        self.stats.total_case_durations = self.counters['case_duration'] - 1
        self.stats.total_citations = self.counters['citation'] - 1
        self.stats.total_triples = len(self.rdf_lines)
    
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


def main():
    """Main function to run the RDF generator."""
    try:
        # Validate configuration
        if not config.validate():
            sys.exit(1)
        
        # Generate RDF
        generator = RDFGenerator()
        generator.generate_rdf()
        
    except Exception as e:
        logger = setup_logging()
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
