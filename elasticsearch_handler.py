#!/usr/bin/env python3
"""
Elasticsearch Data Handler for Legal Judgment Database

This module handles all Elasticsearch operations including data loading and processing.

Author: Anish
Date: November 2025
"""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from elasticsearch import Elasticsearch

from config import config
from models import ElasticsearchDocument
from utils import setup_logging, validate_elasticsearch_connection, sanitize_string, parse_list_data


class ElasticsearchHandler:
    """
    Handles all Elasticsearch operations for the RDF generator.
    """
    
    def __init__(self, index_name: Optional[str] = None, doc_ids: Optional[List[str]] = None):
        """Initialize the Elasticsearch handler.

        Args:
            index_name: Optional ES index name to override config (default: config index)
            doc_ids: Optional list of document ids to limit loading to specific documents
        """
        self.logger = setup_logging()
        self.es_config = config.get_elasticsearch_config()

        # Allow overriding index and optional specific doc ids
        self.index_name = index_name or self.es_config['index']
        self.doc_ids = doc_ids
        self._index_field_names: Dict[str, List[str]] = {}
        
        # Initialize Elasticsearch client
        try:
            self.es = Elasticsearch([self.es_config['host']])
            
            if not validate_elasticsearch_connection(self.es, self.index_name):
                raise ConnectionError(f"Cannot connect to Elasticsearch at {self.es_config['host']} or index '{self.index_name}' missing")
                
            self.logger.info(f"✅ Connected to Elasticsearch at {self.es_config['host']} (index: {self.index_name})")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Elasticsearch: {e}")
            raise
    
    def _get_index_fields(self, index: str) -> List[str]:
        """
        Retrieve field names for an index (cached).
        """
        if index in self._index_field_names:
            return self._index_field_names[index]

        try:
            mapping = self.es.indices.get_mapping(index=index)
            # mapping structure: {index: {"mappings": {"properties": {...}}}}
            props = {}
            for idx_name, m in mapping.items():
                mp = m.get('mappings', {}).get('properties', {})
                props.update(mp)
            field_names = list(props.keys())
            self._index_field_names[index] = field_names
            return field_names
        except Exception:
            return []
    
    def load_documents(self, index_name: Optional[str] = None, doc_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Load and process documents from Elasticsearch.

        If doc_ids is provided (list of document _id values), use mget to fetch only those documents.
        Otherwise, perform a match_all search limited by config.MAX_DOCUMENTS.

        Args:
            index_name: Optional index name to override the handler's index
            doc_ids: Optional list of document ids to fetch

        Returns:
            pd.DataFrame: Processed judgment documents

        Raises:
            Exception: If documents cannot be loaded
        """
        try:
            index = index_name or self.index_name
            ids_to_fetch = doc_ids or self.doc_ids

            self.logger.info(f"📖 Loading data from Elasticsearch index: {index}")

            documents = []

            index_fields = self._get_index_fields(index)

            if ids_to_fetch:
                # Use mget to fetch specific documents by their ES _id
                self.logger.info(f"🔎 Fetching {len(ids_to_fetch)} specific document(s) by doc_id")
                mget_body = {"ids": ids_to_fetch}
                response = self.es.mget(body=mget_body, index=index)
                docs = response.get('docs', [])
                hits = [doc for doc in docs if doc.get('found')]

                if not hits:
                    raise ValueError("No documents found for the provided doc_id(s) in Elasticsearch index")

                for doc in hits:
                    src = doc.get('_source', {}) or {}
                    es_id = doc.get('_id')
                    documents.append(self._process_document(src, es_id, index_fields))

            else:
                # Query all documents from the index
                query = {
                    "query": {
                        "match_all": {}
                    },
                    "size": config.MAX_DOCUMENTS
                }
                response = self.es.search(index=index, body=query)
                hits = response['hits']['hits']

                if not hits:
                    raise ValueError("No documents found in Elasticsearch index")

                # Process documents
                for hit in hits:
                    src = hit.get('_source', {}) or {}
                    es_id = hit.get('_id')
                    documents.append(self._process_document(src, es_id, index_fields))

            df = pd.DataFrame([doc.__dict__ for doc in documents])

            self.logger.info(f"✅ Loaded {len(df)} documents from Elasticsearch")
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load data from Elasticsearch: {e}")
            raise
    
    def _process_document(self, raw_doc: Dict[str, Any], es_id: Optional[str] = None, index_fields: Optional[List[str]] = None) -> ElasticsearchDocument:
        """
        Process a raw Elasticsearch document into a structured format.

        This version uses exact field names from the index mapping (index_fields)
        rather than a predefined set of aliases. If a canonical field name
        (e.g. 'title', 'doc_id', 'citations') exists in index_fields it will be
        used; otherwise the field will be considered missing. For doc_id, if no
        matching field is found, ES document _id (es_id) is used as fallback.
        """
        index_fields = index_fields or []

        # Canonical names we expect in the index mapping
        canonical_fields = {
            'title': 'title',
            'doc_id': 'doc_id',
            'year': 'year',
            'citations': 'citations',
            'judges': 'judges',
            'petitioner_advocates': 'petitioner_advocates',
            'respondant_advocates': 'respondant_advocates',
            'outcome': 'outcome',
            'case_duration': 'case_duration'
        }

        # Helper to get value only if the exact field exists in index mapping
        def get_exact(field_name: str):
            if field_name in index_fields and field_name in raw_doc:
                return raw_doc.get(field_name)
            # If index_fields don't include the canonical name, do not fallback to aliases
            return None

        # Resolve values using exact field names from index mapping
        title_val = get_exact(canonical_fields['title']) or 'Untitled'
        docid_val = get_exact(canonical_fields['doc_id'])
        if not docid_val and es_id:
            docid_val = es_id
        case_duration_val = get_exact(canonical_fields['case_duration']) or ''
        outcome_val = get_exact(canonical_fields['outcome']) or ''

        # Year handling
        year_raw = get_exact(canonical_fields['year'])
        year = None
        if year_raw is not None:
            try:
                year = int(year_raw)
            except (ValueError, TypeError):
                year = None

        # Process list fields (only if exact field exists)
        citations_raw = get_exact(canonical_fields['citations']) or []
        judges_raw = get_exact(canonical_fields['judges']) or []
        petitioner_raw = get_exact(canonical_fields['petitioner_advocates']) or []
        respondant_raw = get_exact(canonical_fields['respondant_advocates']) or []

        citations = self._process_list_field(citations_raw)
        judges = self._process_list_field(judges_raw)
        petitioner_advocates = self._process_list_field(petitioner_raw)
        respondant_advocates = self._process_list_field(respondant_raw)

        # Sanitize title and other strings
        title = sanitize_string(title_val)
        doc_id = sanitize_string(docid_val) if docid_val is not None else sanitize_string(es_id or 'unknown')
        case_duration = sanitize_string(case_duration_val)
        outcome = sanitize_string(outcome_val)

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
    
    def get_unprocessed_documents(self, limit: int = 100) -> List[Dict[str, str]]:
        """
        Get list of unprocessed documents from Elasticsearch.
        
        Args:
            limit: Maximum number of documents to return
            
        Returns:
            List of dictionaries with doc_id and title of unprocessed documents
        """
        try:
            query = {
                "query": {
                    "bool": {
                        "must_not": {
                            "term": {"processed_to_dgraph": True}
                        }
                    }
                },
                "size": limit,
                "_source": ["doc_id", "title"]
            }
            
            response = self.es.search(index=self.index_name, body=query)
            hits = response['hits']['hits']
            
            documents = []
            for hit in hits:
                doc_id = hit.get('_id')
                source = hit.get('_source', {})
                documents.append({
                    "es_id": doc_id,
                    "doc_id": source.get('doc_id', doc_id),
                    "title": source.get('title', 'Untitled')
                })
            
            self.logger.info(f"Found {len(documents)} unprocessed documents")
            return documents
            
        except Exception as e:
            self.logger.error(f"Failed to get unprocessed documents: {e}")
            return []
    
    def get_processing_counts(self) -> Dict[str, int]:
        """
        Get counts of processed and unprocessed documents.
        
        Returns:
            Dictionary with counts
        """
        try:
            # Total documents
            total_query = {"query": {"match_all": {}}}
            total_response = self.es.count(index=self.index_name, body=total_query)
            total_count = total_response['count']
            
            # Processed documents
            processed_query = {
                "query": {
                    "term": {"processed_to_dgraph": True}
                }
            }
            processed_response = self.es.count(index=self.index_name, body=processed_query)
            processed_count = processed_response['count']
            
            # Unprocessed documents
            unprocessed_count = total_count - processed_count
            
            return {
                "total": total_count,
                "processed": processed_count,
                "unprocessed": unprocessed_count
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get processing counts: {e}")
            return {"total": 0, "processed": 0, "unprocessed": 0}
    
    def mark_documents_as_processed(self, doc_ids: List[str]) -> int:
        """
        Mark specific documents as processed in Elasticsearch.
        
        Args:
            doc_ids: List of document IDs (ES _id values) to mark as processed
            
        Returns:
            Number of documents updated
        """
        try:
            from datetime import datetime
            
            updated_count = 0
            for doc_id in doc_ids:
                try:
                    # Update document with processed flag and timestamp
                    self.es.update(
                        index=self.index_name,
                        id=doc_id,
                        body={
                            "doc": {
                                "processed_to_dgraph": True,
                                "processed_timestamp": datetime.now().isoformat()
                            }
                        }
                    )
                    updated_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to update document {doc_id}: {e}")
            
            self.logger.info(f"✅ Marked {updated_count} documents as processed")
            return updated_count
            
        except Exception as e:
            self.logger.error(f"Failed to mark documents as processed: {e}")
            return 0
    
    def reset_processed_status(self, doc_ids: Optional[List[str]] = None) -> int:
        """
        Reset processed status for documents (for reprocessing).
        
        Args:
            doc_ids: Optional list of document IDs. If not provided, resets all documents.
            
        Returns:
            Number of documents reset
        """
        try:
            if doc_ids:
                # Reset specific documents
                reset_count = 0
                for doc_id in doc_ids:
                    try:
                        self.es.update(
                            index=self.index_name,
                            id=doc_id,
                            body={
                                "doc": {
                                    "processed_to_dgraph": False
                                }
                            }
                        )
                        reset_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to reset document {doc_id}: {e}")
                
                self.logger.info(f"✅ Reset processed status for {reset_count} documents")
                return reset_count
            else:
                # Reset all documents using update_by_query
                query = {
                    "script": {
                        "source": "ctx._source.processed_to_dgraph = false",
                        "lang": "painless"
                    },
                    "query": {
                        "match_all": {}
                    }
                }
                
                response = self.es.update_by_query(
                    index=self.index_name,
                    body=query
                )
                
                reset_count = response.get('updated', 0)
                self.logger.info(f"✅ Reset processed status for {reset_count} documents")
                return reset_count
                
        except Exception as e:
            self.logger.error(f"Failed to reset processed status: {e}")
            return 0
    
    def load_unprocessed_documents(self) -> pd.DataFrame:
        """
        Load only unprocessed documents from Elasticsearch.
        
        Returns:
            pd.DataFrame: Processed unprocessed judgment documents
        """
        try:
            self.logger.info(f"📖 Loading unprocessed documents from Elasticsearch index: {self.index_name}")
            
            # Query for unprocessed documents
            query = {
                "query": {
                    "bool": {
                        "must_not": {
                            "term": {"processed_to_dgraph": True}
                        }
                    }
                },
                "size": config.MAX_DOCUMENTS
            }
            
            response = self.es.search(index=self.index_name, body=query)
            hits = response['hits']['hits']
            
            if not hits:
                self.logger.info("No unprocessed documents found")
                return pd.DataFrame()
            
            index_fields = self._get_index_fields(self.index_name)
            
            documents = []
            for hit in hits:
                src = hit.get('_source', {}) or {}
                es_id = hit.get('_id')
                documents.append(self._process_document(src, es_id, index_fields))
            
            df = pd.DataFrame([doc.__dict__ for doc in documents])
            
            self.logger.info(f"✅ Loaded {len(df)} unprocessed documents from Elasticsearch")
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load unprocessed documents: {e}")
            raise
