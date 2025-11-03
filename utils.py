#!/usr/bin/env python3
"""
Utilities for Legal Judgment Database

This module contains utility functions and helper methods used throughout the application.

Author: Anish
Date: November 2025
"""

import logging
import sys
import json
import ast
import re
from typing import List, Any, Dict
import pandas as pd
from pathlib import Path

from config import config


def setup_logging() -> logging.Logger:
    """
    Set up logging configuration.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    log_config = config.get_logging_config()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_config['level']),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_config['file']),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def sanitize_string(value: Any) -> str:
    """
    Sanitize and validate string values.
    
    Args:
        value: Input value to sanitize
        
    Returns:
        Sanitized string
    """
    if pd.isna(value) or value is None:
        return ""
    
    return str(value).strip().replace('"', '\\"')


def parse_list_data(raw_data: str) -> List[str]:
    """
    Parse list data from various formats (citations, judges, advocates).
    
    Args:
        raw_data: Raw string data
        
    Returns:
        List of parsed strings
    """
    items = []
    
    if not raw_data or raw_data.lower() in ['nan', '[]', '{}', 'null']:
        return items
    
    # If it's already a list (from Elasticsearch), convert to strings
    if isinstance(raw_data, list):
        return [str(item).strip() for item in raw_data if item and str(item).strip()]
    
    try:
        # Case 1: JSON-like format with dict
        if raw_data.startswith('{') or 'cited_cases' in raw_data:
            if not raw_data.startswith('{'):
                raw_data = '{' + raw_data + '}'
            cleaned_data = raw_data.replace("'", '"')
            data_dict = json.loads(cleaned_data)
            items = data_dict.get("cited_cases", [])
        
        # Case 2: Python-style list
        elif raw_data.startswith('['):
            cleaned_data = raw_data
            cleaned_data = cleaned_data.replace('\\"', '"')
            cleaned_data = cleaned_data.replace('\\n', ' ')
            cleaned_data = cleaned_data.replace('\\t', ' ')
            
            try:
                items = ast.literal_eval(cleaned_data)
            except (ValueError, SyntaxError):
                # Fallback: regex parsing
                pattern = r'"([^"]*)"'
                items = re.findall(pattern, cleaned_data)
        
        # Case 3: Comma-separated values
        elif ',' in raw_data:
            items = [item.strip().strip('"\'') for item in raw_data.split(',')]
        
        # Case 4: Single item
        else:
            items = [raw_data.strip().strip('"\'')]
            
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not parse list data '{raw_data[:100]}...': {e}")
        items = []
    
    # Clean and filter items
    cleaned_items = []
    for item in items:
        if item and str(item).strip() and str(item).strip().lower() not in ['nan', 'null', '']:
            cleaned_items.append(str(item).strip())
    
    return cleaned_items


def validate_elasticsearch_connection(es_client, index_name: str) -> bool:
    """
    Validate Elasticsearch connection and index existence.
    
    Args:
        es_client: Elasticsearch client instance
        index_name: Name of the index to check
        
    Returns:
        bool: True if connection and index are valid
    """
    try:
        # Check connection
        if not es_client.ping():
            return False
        
        # Check if index exists
        if not es_client.indices.exists(index=index_name):
            logger = logging.getLogger(__name__)
            logger.error(f"Index '{index_name}' does not exist")
            return False
        
        return True
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Elasticsearch validation failed: {e}")
        return False


def create_node_id(node_type: str, counter: int) -> str:
    """
    Create a standardized node ID.
    
    Args:
        node_type: Type of node (judgment, judge, advocate, etc.)
        counter: Counter value
        
    Returns:
        str: Formatted node ID
    """
    node_type_map = {
        'judgment': 'j',
        'citation': 'c',
        'judge': 'judge',
        'petitioner_advocate': 'petitioner_advocate',
        'respondant_advocate': 'respondant_advocate',
        'outcome': 'outcome',
        'case_duration': 'case_duration'
    }
    
    prefix = node_type_map.get(node_type, node_type)
    return f"{prefix}{counter}"


def format_rdf_triple(subject: str, predicate: str, obj: str, is_object_literal: bool = True) -> str:
    """
    Format an RDF triple.
    
    Args:
        subject: Subject of the triple
        predicate: Predicate of the triple
        obj: Object of the triple
        is_object_literal: Whether object is a literal (quoted) or reference
        
    Returns:
        str: Formatted RDF triple
    """
    if is_object_literal:
        return f'<{subject}> <{predicate}> "{obj}" .'
    else:
        return f'<{subject}> <{predicate}> <{obj}> .'


def print_processing_summary(stats: Dict, output_file: str) -> None:
    """
    Print processing summary.
    
    Args:
        stats: Processing statistics dictionary
        output_file: Output file path
    """
    print("\n" + "=" * 70)
    print(f"✅ RDF file generated successfully in Dgraph Live format!")
    print(f"📁 Output file: {output_file}")
    print(f"📊 Total judgments: {stats.get('total_judgments', 0)}")
    print(f"👨‍⚖️ Total judges: {stats.get('total_judges', 0)}")
    print(f"👨‍💼 Total petitioner advocates: {stats.get('total_petitioner_advocates', 0)}")
    print(f"👨‍💼 Total respondant advocates: {stats.get('total_respondant_advocates', 0)}")
    print(f"⚖️ Total outcomes: {stats.get('total_outcomes', 0)}")
    print(f"📅 Total case durations: {stats.get('total_case_durations', 0)}")
    print(f"🔗 Total RDF triples: {stats.get('total_triples', 0)}")
    print("=" * 70)
    print("🚀 Ready to upload to Dgraph using:")
    print(f"   dgraph live --files {output_file} --schema {config.RDF_SCHEMA_FILE}")
    print("=" * 70)
