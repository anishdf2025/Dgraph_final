#!/usr/bin/env python3
"""
Citation Relationship Handler for Legal Judgment Database

This module handles the creation of citation nodes and their relationships with judgments.
It also handles cross-references between existing judgments.

Author: Anish
Date: November 2025
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from models import JudgmentData
from utils import setup_logging, sanitize_string, parse_list_data, create_node_id, format_rdf_triple


class CitationRelationshipHandler:
    """
    Handles citation nodes and relationships for RDF generation.
    """
    
    def __init__(self, title_to_judgment_map: Dict[str, str] = None):
        """Initialize the Citation Relationship Handler."""
        self.logger = setup_logging()
        self.rdf_lines: List[str] = []
        self.citation_map: Dict[str, str] = {}  # Maps citation_title -> stable node_id
        self.title_to_judgment_map: Dict[str, str] = title_to_judgment_map or {}
        self.stats = {
            'total_citations': 0,
            'citation_relationships': 0,
            'title_matches': 0,
            'citation_matches': 0,
            'total_triples': 0
        }
        
        self.logger.info("🔗 Citation Relationship Handler initialized")
    
    def set_title_mapping(self, title_to_judgment_map: Dict[str, str]) -> None:
        """
        Set or update the title to judgment mapping for cross-references.
        
        Args:
            title_to_judgment_map: Mapping of judgment titles to judgment node IDs
        """
        self.title_to_judgment_map = title_to_judgment_map
        self.logger.info(f"📋 Updated title mapping with {len(title_to_judgment_map)} judgments")
    
    def create_citation_relationships(self, judgment: JudgmentData) -> List[str]:
        """
        Create citation nodes and relationships for a single judgment.
        
        Args:
            judgment: JudgmentData object containing judgment information
            
        Returns:
            List[str]: RDF triples for citation relationships
        """
        relationship_triples = []
        citations = parse_list_data(judgment.raw_citations)
        
        if not citations:
            self.logger.debug(f"⚠️ No citations for judgment: {judgment.title[:50]}...")
            return relationship_triples
        
        self.logger.info(f"🔄 Processing {len(citations)} citations for: {judgment.title[:50]}...")
        
        for citation in citations:
            citation_clean = sanitize_string(citation)
            if not citation_clean:
                continue
            
            citation_lower = citation_clean.lower()
            
            # Check if this citation matches an existing judgment title
            if citation_lower in self.title_to_judgment_map:
                existing_judgment_node = self.title_to_judgment_map[citation_lower]
                relationship_triple = format_rdf_triple(judgment.judgment_node, 'cites', existing_judgment_node, False)
                relationship_triples.append(relationship_triple)
                self.stats['title_matches'] += 1
                self.stats['citation_relationships'] += 1
                
                self.logger.info(f"✓ Found title match - {judgment.judgment_node} -> {existing_judgment_node}")
            else:
                # Create citation node for external reference
                citation_node = self._get_or_create_citation_node(citation_clean)
                relationship_triple = format_rdf_triple(judgment.judgment_node, 'cites', citation_node, False)
                relationship_triples.append(relationship_triple)
                self.stats['citation_matches'] += 1
                self.stats['citation_relationships'] += 1
                
                self.logger.info(f"✓ Created citation relationship: {judgment.judgment_node} -> {citation_node}")
        
        return relationship_triples
    
    def _get_or_create_citation_node(self, citation_title: str) -> str:
        """
        Get existing citation node or create a new one using stable content-based ID.
        
        Args:
            citation_title: Title of the cited judgment
            
        Returns:
            str: Citation node identifier (stable across batches)
        """
        if citation_title in self.citation_map:
            return self.citation_map[citation_title]
        
        # Create stable citation node ID based on citation title
        # This ensures same citation always gets same ID across different batches
        # Using 'judgment' type since citations are also judgments
        citation_node = create_node_id('citation', unique_key=citation_title)
        self.citation_map[citation_title] = citation_node
        
        # Add citation node properties
        citation_triples = [
            format_rdf_triple(citation_node, 'dgraph.type', 'Judgment'),
            format_rdf_triple(citation_node, 'judgment_id', citation_node),
            format_rdf_triple(citation_node, 'title', citation_title)
        ]
        
        self.rdf_lines.extend(citation_triples)
        self.stats['total_citations'] += 1
        
        self.logger.info(f"📄 Created citation node: {citation_node} for '{citation_title[:50]}...'")
        return citation_node
    
    def get_all_rdf_triples(self) -> List[str]:
        """
        Get all RDF triples generated by this handler.
        
        Returns:
            List[str]: All RDF triples
        """
        return self.rdf_lines
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get processing statistics.
        
        Returns:
            Dict[str, int]: Statistics dictionary
        """
        self.stats['total_triples'] = len(self.rdf_lines)
        return self.stats.copy()
    
    def reset(self) -> None:
        """Reset the handler for a new processing session."""
        self.rdf_lines.clear()
        self.citation_map.clear()
        self.citation_counter = 1
        self.stats = {
            'total_citations': 0,
            'citation_relationships': 0,
            'title_matches': 0,
            'citation_matches': 0,
            'total_triples': 0
        }
        self.logger.info("🔄 Citation Relationship Handler reset")


def debug_citation_relationships(judgments: List[JudgmentData]) -> None:
    """
    Debug function to test citation relationships independently.
    
    Args:
        judgments: List of JudgmentData objects
    """
    print("🐛 DEBUG: Testing Citation Relationships")
    print("=" * 50)
    
    # Create title mapping for cross-references
    title_mapping = {}
    for judgment in judgments:
        title_mapping[judgment.title.lower()] = judgment.judgment_node
    
    handler = CitationRelationshipHandler(title_mapping)
    all_relationship_triples = []
    
    for judgment in judgments:
        print(f"\n🔄 Processing: {judgment.title[:50]}...")
        citations = parse_list_data(judgment.raw_citations) if hasattr(judgment, 'raw_citations') else []
        print(f"   Citations: {len(citations)} found")
        relationship_triples = handler.create_citation_relationships(judgment)
        all_relationship_triples.extend(relationship_triples)
    
    # Get all triples
    all_triples = handler.get_all_rdf_triples() + all_relationship_triples
    stats = handler.get_statistics()
    
    # Print results
    print(f"\n📊 Results:")
    print(f"   • Total citations created: {stats['total_citations']}")
    print(f"   • Total citation relationships: {stats['citation_relationships']}")
    print(f"   • Title matches (internal refs): {stats['title_matches']}")
    print(f"   • Citation matches (external refs): {stats['citation_matches']}")
    print(f"   • Total RDF triples: {len(all_triples)}")
    
    print(f"\n📝 Sample triples:")
    for i, triple in enumerate(all_triples[:8]):
        print(f"   {i+1}. {triple}")
    
    if len(all_triples) > 8:
        print(f"   ... and {len(all_triples) - 8} more triples")
    
    return all_triples


if __name__ == "__main__":
    # Test with sample data
    sample_judgments = [
        JudgmentData(
            idx=0,
            title="Sample Judgment 1",
            judgment_node="<j1>",
            raw_citations='["External Case A v. External Case B", "Sample Judgment 2"]'  # One external, one internal
        ),
        JudgmentData(
            idx=1,
            title="Sample Judgment 2",
            judgment_node="<j2>",
            raw_citations='["Sample Judgment 1", "External Case C v. External Case D"]'  # One internal, one external
        ),
        JudgmentData(
            idx=2,
            title="Sample Judgment 3",
            judgment_node="<j3>",
            raw_citations='["External Case E v. External Case F"]'  # Only external
        )
    ]
    
    debug_citation_relationships(sample_judgments)
