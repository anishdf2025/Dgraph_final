#!/usr/bin/env python3
"""
Elasticsearch Data Handler for Legal Judgment Database

This module handles all Elasticsearch operations including data loading and processing.

Author: Anish
Date: November 2025
"""

import logging
from typing import List, Dict, Any
import pandas as pd
from elasticsearch import Elasticsearch

from config import config
from models import ElasticsearchDocument
from utils import setup_logging, validate_elasticsearch_connection, sanitize_string, parse_list_data


class ElasticsearchHandler:
    """
    Handles all Elasticsearch operations for the RDF generator.
    """
    
    def __init__(self):
        """Initialize the Elasticsearch handler."""
        self.logger = setup_logging()
        self.es_config = config.get_elasticsearch_config()
        
        # Initialize Elasticsearch client
        try:
            self.es = Elasticsearch([self.es_config['host']])
            
            if not validate_elasticsearch_connection(self.es, self.es_config['index']):
                raise ConnectionError(f"Cannot connect to Elasticsearch at {self.es_config['host']}")
                
            self.logger.info(f"✅ Connected to Elasticsearch at {self.es_config['host']}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Elasticsearch: {e}")
            raise
    
    def load_documents(self) -> pd.DataFrame:
        """
        Load and process documents from Elasticsearch.
        
        Returns:
            pd.DataFrame: Processed judgment documents
            
        Raises:
            Exception: If documents cannot be loaded
        """
        try:
            self.logger.info(f"📖 Loading data from Elasticsearch index: {self.es_config['index']}")
            
            # Query all documents from the index
            query = {
                "query": {
                    "match_all": {}
                },
                "size": config.MAX_DOCUMENTS
            }
            
            response = self.es.search(index=self.es_config['index'], body=query)
            hits = response['hits']['hits']
            
            if not hits:
                raise ValueError("No documents found in Elasticsearch index")
            
            # Process documents
            documents = []
            for hit in hits:
                doc = self._process_document(hit['_source'])
                documents.append(doc)
            
            df = pd.DataFrame([doc.__dict__ for doc in documents])
            
            self.logger.info(f"✅ Loaded {len(df)} documents from Elasticsearch")
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load data from Elasticsearch: {e}")
            raise
    
    def _process_document(self, raw_doc: Dict[str, Any]) -> ElasticsearchDocument:
        """
        Process a raw Elasticsearch document into a structured format.
        
        Args:
            raw_doc: Raw document from Elasticsearch
            
        Returns:
            ElasticsearchDocument: Processed document
        """
        # Extract and sanitize basic fields
        title = sanitize_string(raw_doc.get('title', 'Untitled'))
        doc_id = sanitize_string(raw_doc.get('doc_id', 'unknown'))
        case_duration = sanitize_string(raw_doc.get('case_duration', ''))
        outcome = sanitize_string(raw_doc.get('outcome', ''))
        
        # Handle year field
        year = raw_doc.get('year')
        if year is not None:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = None
        
        # Process list fields
        citations = self._process_list_field(raw_doc.get('citations', []))
        judges = self._process_list_field(raw_doc.get('judges', []))
        petitioner_advocates = self._process_list_field(raw_doc.get('petitioner_advocates', []))
        respondant_advocates = self._process_list_field(raw_doc.get('respondant_advocates', []))
        
        return ElasticsearchDocument(
            title=title,
            doc_id=doc_id,
            year=year,
            citations=citations,
            judges=judges,
            petitioner_advocates=petitioner_advocates,
            respondant_advocates=respondant_advocates,
            case_duration=case_duration,
            outcome=outcome
        )
    
    def _process_list_field(self, field_value: Any) -> List[str]:
        """
        Process a list field from Elasticsearch.
        
        Args:
            field_value: Field value (could be list, string, or None)
            
        Returns:
            List[str]: Processed list of strings
        """
        if isinstance(field_value, list):
            return [sanitize_string(item) for item in field_value if item]
        elif isinstance(field_value, str):
            return parse_list_data(field_value)
        else:
            return []
    
    def get_document_count(self) -> int:
        """
        Get the total number of documents in the index.
        
        Returns:
            int: Number of documents
        """
        try:
            result = self.es.count(index=self.es_config['index'])
            return result['count']
        except Exception as e:
            self.logger.error(f"Failed to get document count: {e}")
            return 0
