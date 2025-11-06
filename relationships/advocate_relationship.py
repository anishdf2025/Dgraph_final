#!/usr/bin/env python3
"""
Advocate Relationship Handler for Legal Judgment Database

This module handles the creation of advocate nodes (both petitioner and respondent) 
and their relationships with judgments.

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


class AdvocateRelationshipHandler:
    """
    Handles advocate nodes and relationships for RDF generation.
    """
    
    def __init__(self):
        """Initialize the Advocate Relationship Handler."""
        self.logger = setup_logging()
        self.rdf_lines: List[str] = []
        self.petitioner_advocate_map: Dict[str, str] = {}  # Maps name -> stable node_id
        self.respondant_advocate_map: Dict[str, str] = {}  # Maps name -> stable node_id
        self.stats = {
            'total_petitioner_advocates': 0,
            'total_respondant_advocates': 0,
            'petitioner_advocate_relationships': 0,
            'respondant_advocate_relationships': 0,
            'total_triples': 0
        }
        
        self.logger.info("👨‍💼 Advocate Relationship Handler initialized")
    
    def create_advocate_relationships(self, judgment: JudgmentData) -> List[str]:
        """
        Create advocate nodes and relationships for a single judgment.
        
        Args:
            judgment: JudgmentData object containing judgment information
            
        Returns:
            List[str]: RDF triples for advocate relationships
        """
        relationship_triples = []
        
        # Process petitioner advocates
        petitioner_triples = self._create_petitioner_advocate_relationships(judgment)
        relationship_triples.extend(petitioner_triples)
        
        # Process respondant advocates  
        respondant_triples = self._create_respondant_advocate_relationships(judgment)
        relationship_triples.extend(respondant_triples)
        
        return relationship_triples
    
    def _create_petitioner_advocate_relationships(self, judgment: JudgmentData) -> List[str]:
        """Create petitioner advocate relationships."""
        relationship_triples = []
        petitioner_advocates = parse_list_data(judgment.petitioner_advocate)
        
        self.logger.info(f"🔄 Processing {len(petitioner_advocates)} petitioner advocates for: {judgment.title[:50]}...")
        
        for advocate_name in petitioner_advocates:
            advocate_clean = sanitize_string(advocate_name)
            if not advocate_clean:
                continue
            
            # Get or create petitioner advocate node
            advocate_node = self._get_or_create_petitioner_advocate_node(advocate_clean)
            
            # Create relationship
            relationship_triple = format_rdf_triple(judgment.judgment_node, 'petitioner_represented_by', advocate_node, False)
            relationship_triples.append(relationship_triple)
            self.stats['petitioner_advocate_relationships'] += 1
            
            self.logger.info(f"✓ Created petitioner advocate relationship: {judgment.judgment_node} -> {advocate_node}")
        
        return relationship_triples
    
    def _create_respondant_advocate_relationships(self, judgment: JudgmentData) -> List[str]:
        """Create respondant advocate relationships."""
        relationship_triples = []
        respondant_advocates = parse_list_data(judgment.respondant_advocate)
        
        self.logger.info(f"🔄 Processing {len(respondant_advocates)} respondant advocates for: {judgment.title[:50]}...")
        
        for advocate_name in respondant_advocates:
            advocate_clean = sanitize_string(advocate_name)
            if not advocate_clean:
                continue
            
            # Get or create respondant advocate node
            advocate_node = self._get_or_create_respondant_advocate_node(advocate_clean)
            
            # Create relationship
            relationship_triple = format_rdf_triple(judgment.judgment_node, 'respondant_represented_by', advocate_node, False)
            relationship_triples.append(relationship_triple)
            self.stats['respondant_advocate_relationships'] += 1
            
            self.logger.info(f"✓ Created respondant advocate relationship: {judgment.judgment_node} -> {advocate_node}")
        
        return relationship_triples
    
    def _get_or_create_petitioner_advocate_node(self, advocate_name: str) -> str:
        """
        Get existing petitioner advocate node or create a new one using stable content-based ID.
        
        Args:
            advocate_name: Name of the advocate
            
        Returns:
            str: Advocate node identifier (stable across batches)
        """
        if advocate_name in self.petitioner_advocate_map:
            return self.petitioner_advocate_map[advocate_name]
        
        # Create stable advocate node ID based on name + type
        # This ensures same advocate always gets same ID across different batches
        unique_key = f"petitioner_{advocate_name}"
        advocate_node = create_node_id('petitioner_advocate', unique_key=unique_key)
        self.petitioner_advocate_map[advocate_name] = advocate_node
        
        # Add advocate node properties
        advocate_triples = [
            format_rdf_triple(advocate_node, 'dgraph.type', 'Advocate'),
            format_rdf_triple(advocate_node, 'advocate_id', advocate_node),
            format_rdf_triple(advocate_node, 'name', advocate_name),
            format_rdf_triple(advocate_node, 'advocate_type', 'petitioner')
        ]
        
        self.rdf_lines.extend(advocate_triples)
        self.stats['total_petitioner_advocates'] += 1
        
        self.logger.info(f"📄 Created petitioner advocate node: {advocate_node} for '{advocate_name}'")
        return advocate_node
    
    def _get_or_create_respondant_advocate_node(self, advocate_name: str) -> str:
        """
        Get existing respondant advocate node or create a new one using stable content-based ID.
        
        Args:
            advocate_name: Name of the advocate
            
        Returns:
            str: Advocate node identifier (stable across batches)
        """
        if advocate_name in self.respondant_advocate_map:
            return self.respondant_advocate_map[advocate_name]
        
        # Create stable advocate node ID based on name + type
        # This ensures same advocate always gets same ID across different batches
        unique_key = f"respondant_{advocate_name}"
        advocate_node = create_node_id('respondant_advocate', unique_key=unique_key)
        self.respondant_advocate_map[advocate_name] = advocate_node
        
        # Add advocate node properties
        advocate_triples = [
            format_rdf_triple(advocate_node, 'dgraph.type', 'Advocate'),
            format_rdf_triple(advocate_node, 'advocate_id', advocate_node),
            format_rdf_triple(advocate_node, 'name', advocate_name),
            format_rdf_triple(advocate_node, 'advocate_type', 'respondant')
        ]
        
        self.rdf_lines.extend(advocate_triples)
        self.stats['total_respondant_advocates'] += 1
        
        self.logger.info(f"📄 Created respondant advocate node: {advocate_node} for '{advocate_name}'")
        return advocate_node
    
    def get_all_rdf_triples(self) -> List[str]:
        """Get all RDF triples generated by this handler."""
        return self.rdf_lines
    
    def get_statistics(self) -> Dict[str, int]:
        """Get processing statistics."""
        self.stats['total_triples'] = len(self.rdf_lines)
        return self.stats.copy()
    
    def reset(self) -> None:
        """Reset the handler for a new processing session."""
        self.rdf_lines.clear()
        self.petitioner_advocate_map.clear()
        self.respondant_advocate_map.clear()
        self.petitioner_advocate_counter = 1
        self.respondant_advocate_counter = 1
        self.stats = {
            'total_petitioner_advocates': 0,
            'total_respondant_advocates': 0,
            'petitioner_advocate_relationships': 0,
            'respondant_advocate_relationships': 0,
            'total_triples': 0
        }
        self.logger.info("🔄 Advocate Relationship Handler reset")


def debug_advocate_relationships(judgments: List[JudgmentData]) -> None:
    """
    Debug function to test advocate relationships independently.
    
    Args:
        judgments: List of JudgmentData objects
    """
    print("🐛 DEBUG: Testing Advocate Relationships")
    print("=" * 50)
    
    handler = AdvocateRelationshipHandler()
    all_relationship_triples = []
    
    for judgment in judgments:
        print(f"\n🔄 Processing: {judgment.title[:50]}...")
        relationship_triples = handler.create_advocate_relationships(judgment)
        all_relationship_triples.extend(relationship_triples)
    
    # Get all triples
    all_triples = handler.get_all_rdf_triples() + all_relationship_triples
    stats = handler.get_statistics()
    
    # Print results
    print(f"\n📊 Results:")
    print(f"   • Total petitioner advocates: {stats['total_petitioner_advocates']}")
    print(f"   • Total respondant advocates: {stats['total_respondant_advocates']}")
    print(f"   • Petitioner relationships: {stats['petitioner_advocate_relationships']}")
    print(f"   • Respondant relationships: {stats['respondant_advocate_relationships']}")
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
            petitioner_advocate='["Mr. John Doe", "Ms. Jane Smith"]',
            respondant_advocate='["Mr. Bob Wilson", "Ms. Alice Brown"]'
        ),
        JudgmentData(
            idx=1,
            title="Sample Judgment 2",
            judgment_node="<j2>", 
            petitioner_advocate='["Mr. John Doe", "Ms. Carol Davis"]',
            respondant_advocate='["Mr. David Lee"]'
        )
    ]
    
    debug_advocate_relationships(sample_judgments)
