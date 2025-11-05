#!/usr/bin/env python3
"""
Elasticsearch Upload Script for Legal Judgment Database

This script reads Excel data and uploads it to Elasticsearch with proper indexing
for legal judgment documents including citations, judges, advocates, outcomes, and case durations.

Author: Anish
Date: November 2025
"""

import logging
import sys
import json
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from datetime import datetime

from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('elasticsearch_upload.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ElasticsearchUploader:
    """
    Elasticsearch uploader for legal judgment data.
    """
    
    # Default Excel file path (can be overridden in __init__)
    DEFAULT_EXCEL_PATH = '/home/anish/Desktop/Anish/Dgraph_final/excel_2024_2025/FINAL/5_sample/tests.xlsx'
    
    def __init__(self, excel_file_path: str = None, es_host: str = None, index_name: str = None):
        """
        Initialize the Elasticsearch uploader.
        
        Args:
            excel_file_path: Path to the Excel file (defaults to DEFAULT_EXCEL_PATH)
            es_host: Elasticsearch host URL (defaults to config)
            index_name: Name of the index to create (defaults to config)
        """
        # Use config values for Elasticsearch only
        es_config = config.get_elasticsearch_config()
        
        # Excel path is hardcoded (user-specific)
        self.excel_file_path = Path(excel_file_path or self.DEFAULT_EXCEL_PATH)
        self.es_host = es_host or es_config['host']
        self.index_name = index_name or es_config['index']
        
        # Initialize Elasticsearch client
        try:
            self.es = Elasticsearch([self.es_host])
            if not self.es.ping():
                raise ConnectionError(f"Cannot connect to Elasticsearch at {self.es_host}")
            logger.info(f"✅ Connected to Elasticsearch at {self.es_host}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Elasticsearch: {e}")
            raise
        
        # Validate input file
        if not self.excel_file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_file_path}")
    
    def _sanitize_string(self, value: Any) -> str:
        """Sanitize and validate string values."""
        if pd.isna(value) or value is None:
            return ""
        return str(value).strip()
    
    def _parse_list_data(self, raw_data: str) -> List[str]:
        """
        Parse list data from various formats (citations, judges, advocates).
        
        Args:
            raw_data: Raw string data from Excel
            
        Returns:
            List of parsed strings
        """
        items = []
        
        if not raw_data or raw_data.lower() in ['nan', '[]', '{}', 'null']:
            return items
        
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
                    import re
                    pattern = r'"([^"]*)"'
                    items = re.findall(pattern, cleaned_data)
            
            # Case 3: Comma-separated values
            elif ',' in raw_data:
                items = [item.strip().strip('"\'') for item in raw_data.split(',')]
            
            # Case 4: Single item
            else:
                items = [raw_data.strip().strip('"\'')]
                
        except Exception as e:
            logger.warning(f"Could not parse list data '{raw_data[:100]}...': {e}")
            items = []
        
        # Clean and filter items
        cleaned_items = []
        for item in items:
            if item and item.strip() and item.strip().lower() not in ['nan', 'null', '']:
                cleaned_items.append(item.strip())
        
        return cleaned_items
    
    def _create_index_mapping(self) -> Dict:
        """
        Create Elasticsearch index mapping for legal judgment data.
        
        Returns:
            Mapping configuration dictionary
        """
        mapping = {
            "mappings": {
                "properties": {
                    "title": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        },
                        "analyzer": "standard"
                    },
                    "doc_id": {
                        "type": "keyword"
                    },
                    "year": {
                        "type": "integer"
                    },
                    "citations": {
                        "type": "keyword"
                    },
                    "judges": {
                        "type": "keyword"
                    },
                    "petitioner_advocates": {
                        "type": "keyword"
                    },
                    "respondant_advocates": {
                        "type": "keyword"
                    },
                    "petitioner_advocates": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "outcome": {
                        "type": "keyword"
                    },
                    "case_duration": {
                        "type": "keyword"
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "legal_analyzer": {
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop"]
                        }
                    }
                }
            }
        }
        
        return mapping
    
    def _create_index_if_not_exists(self) -> None:
        """Create the Elasticsearch index with proper mapping only if it doesn't exist."""
        try:
            # Check if index exists
            if self.es.indices.exists(index=self.index_name):
                logger.info(f"✅ Index already exists: {self.index_name}")
                # Get existing document count
                doc_count = self.es.count(index=self.index_name)['count']
                logger.info(f"📊 Existing documents in index: {doc_count}")
                return
            
            # Create new index with mapping
            logger.info(f"🔨 Creating new index: {self.index_name}")
            mapping = self._create_index_mapping()
            self.es.indices.create(index=self.index_name, body=mapping)
            logger.info(f"✅ Created new index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create index: {e}")
            raise
    
    def _get_existing_doc_ids(self) -> set:
        """Get set of existing document IDs in the index."""
        try:
            if not self.es.indices.exists(index=self.index_name):
                return set()
            
            # Get all existing document IDs
            existing_ids = set()
            
            # Use scroll API to get all document IDs efficiently
            query = {
                "_source": False,  # We only need the IDs
                "query": {"match_all": {}},
                "size": 1000
            }
            
            response = self.es.search(index=self.index_name, body=query, scroll='1m')
            scroll_id = response['_scroll_id']
            
            # Get first batch
            for hit in response['hits']['hits']:
                existing_ids.add(hit['_id'])
            
            # Continue scrolling for remaining documents
            while len(response['hits']['hits']):
                response = self.es.scroll(scroll_id=scroll_id, scroll='1m')
                for hit in response['hits']['hits']:
                    existing_ids.add(hit['_id'])
            
            # Clear scroll context
            self.es.clear_scroll(scroll_id=scroll_id)
            
            logger.info(f"📋 Found {len(existing_ids)} existing documents in index")
            return existing_ids
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to get existing document IDs: {e}")
            return set()

    def _filter_new_documents(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter out documents that already exist in Elasticsearch."""
        try:
            # If Excel does not include doc_id column, cannot filter by ES _id — upload all
            if 'doc_id' not in df.columns:
                logger.info("📝 No 'doc_id' column in Excel; will let Elasticsearch assign IDs and upload all rows")
                return df

            # If doc_id column exists but all values are empty, skip filtering
            if df['doc_id'].isnull().all() or (df['doc_id'].astype(str).str.strip() == '').all():
                logger.info("📝 'doc_id' column present but empty; will let Elasticsearch assign IDs and upload all rows")
                return df

            existing_ids = self._get_existing_doc_ids()

            if not existing_ids:
                logger.info("📝 No existing documents found, all documents will be added")
                return df
            
            # Filter out existing documents
            new_docs_mask = ~df['doc_id'].isin(existing_ids)
            new_df = df[new_docs_mask].copy()
            
            total_docs = len(df)
            existing_docs = total_docs - len(new_df)
            
            logger.info(f"📊 Document analysis:")
            logger.info(f"   • Total documents in Excel: {total_docs}")
            logger.info(f"   • Already exist in Elasticsearch: {existing_docs}")
            logger.info(f"   • New documents to add: {len(new_df)}")
            
            return new_df
            
        except Exception as e:
            logger.error(f"❌ Failed to filter documents: {e}")
            # Return original DataFrame as fallback
            return df

    def _load_excel_data(self) -> pd.DataFrame:
        """Load and validate Excel data."""
        try:
            logger.info(f"📖 Loading Excel file: {self.excel_file_path}")
            df = pd.read_excel(self.excel_file_path)
            
            if df.empty:
                raise ValueError("Excel file is empty")
            
            logger.info(f"✅ Loaded {len(df)} rows from Excel file")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to load Excel file: {e}")
            raise

    def _prepare_document(self, row: pd.Series, row_number: int) -> Dict[str, Any]:
        """
        Prepare a document for Elasticsearch indexing.
        
        Args:
            row: Pandas Series representing a row from Excel
            row_number: Row number for tracking
            
        Returns:
            Document dictionary for Elasticsearch
        """
        # Basic fields - only Excel content
        doc = {
            "title": self._sanitize_string(row.get('Title', 'Untitled')),
            "outcome": self._sanitize_string(row.get('Outcome', '')),
            "case_duration": self._sanitize_string(row.get('Case Duration', ''))
        }

        # Add doc_id only if present in Excel (allow ES to auto-generate otherwise)
        raw_doc_id = self._sanitize_string(row.get('doc_id', ''))
        if raw_doc_id:
            doc["doc_id"] = raw_doc_id
        
        # Year field
        year_value = row.get('Year')
        if pd.notna(year_value):
            try:
                doc["year"] = int(year_value)
            except (ValueError, TypeError):
                doc["year"] = None
        else:
            doc["year"] = None
        
        # Parse and add citations - only clean list
        raw_citations = self._sanitize_string(row.get('Citation', '[]'))
        citations_list = self._parse_list_data(raw_citations)
        if citations_list:  # Only add if not empty
            doc["citations"] = citations_list
        
        # Parse and add judges - only clean list
        raw_judges = self._sanitize_string(row.get('Judge_name', ''))
        judges_list = self._parse_list_data(raw_judges)
        if judges_list:  # Only add if not empty
            doc["judges"] = judges_list
        
        # Parse and add petitioner advocates - only clean list
        raw_petitioner_advocates = self._sanitize_string(row.get('Petitioner_advocate', ''))
        petitioner_advocates_list = self._parse_list_data(raw_petitioner_advocates)
        if petitioner_advocates_list:  # Only add if not empty
            doc["petitioner_advocates"] = petitioner_advocates_list
        
        # Parse and add respondant advocates - only clean list
        raw_respondant_advocates = self._sanitize_string(row.get('Respondant_advocate', ''))
        respondant_advocates_list = self._parse_list_data(raw_respondant_advocates)
        if respondant_advocates_list:  # Only add if not empty
            doc["respondant_advocates"] = respondant_advocates_list
        
        return doc
    
    def _generate_documents(self, df: pd.DataFrame):
        """
        Generator function to yield documents for bulk indexing.
        
        Args:
            df: DataFrame containing Excel data
            
        Yields:
            Document dictionaries for Elasticsearch bulk API
        """
        for idx, row in df.iterrows():
            doc = self._prepare_document(row, idx + 1)

            action = {
                "_index": self.index_name,
                "_source": doc
            }

            # Include _id only if doc_id was provided in Excel
            if doc.get("doc_id"):
                action["_id"] = doc["doc_id"]

            yield action
    
    def _upload_documents(self, df: pd.DataFrame) -> int:
        """
        Upload documents to Elasticsearch using bulk API.
        
        Args:
            df: DataFrame containing Excel data
            
        Returns:
            Number of documents successfully uploaded
        """
        try:
            if df.empty:
                logger.info("📝 No new documents to upload")
                return 0
            
            logger.info(f"📤 Starting bulk upload of {len(df)} documents to index: {self.index_name}")
            
            # Use bulk helper for efficient uploading
            success_count, failed_items = bulk(
                self.es,
                self._generate_documents(df),
                chunk_size=100,
                request_timeout=30
            )
            
            logger.info(f"✅ Successfully uploaded {success_count} new documents")
            
            if failed_items:
                logger.warning(f"⚠️ Failed to upload {len(failed_items)} documents")
                for item in failed_items[:5]:  # Show first 5 failures
                    logger.warning(f"Failed item: {item}")
            
            return success_count
            
        except Exception as e:
            logger.error(f"❌ Failed to upload documents: {e}")
            raise
    
    def _print_summary(self, original_df: pd.DataFrame, new_docs_uploaded: int) -> None:
        """Print upload summary and query examples."""
        # Add a small delay to ensure count is updated
        import time
        time.sleep(0.5)
        
        total_doc_count = self.es.count(index=self.index_name)['count']
        
        print("\n" + "=" * 70)
        print(f"✅ Elasticsearch upload completed!")
        print(f"🔗 Elasticsearch URL: {self.es_host}")
        print(f"📁 Index name: {self.index_name}")
        print("=" * 70)
        print(f"📊 Upload Statistics:")
        print(f"   • Documents in Excel file: {len(original_df)}")
        print(f"   • New documents uploaded: {new_docs_uploaded}")
        print(f"   • Total documents in index: {total_doc_count}")
        print("=" * 70)
        print("🔍 Example queries:")
        print(f"   • All documents: GET {self.es_host}/{self.index_name}/_search")
        print(f"   • Search by title: GET {self.es_host}/{self.index_name}/_search?q=title:\"your_search_term\"")
        print(f"   • Search by outcome: GET {self.es_host}/{self.index_name}/_search?q=outcome:\"Petitioner Won\"")
        print(f"   • Search by judge: GET {self.es_host}/{self.index_name}/_search?q=judges_list:\"judge_name\"")
        print("=" * 70)
        print("🚀 Kibana Dashboard (if available):")
        print(f"   {self.es_host.replace('9200', '5601')}")
        print("=" * 70)
    
    def upload_to_elasticsearch(self) -> None:
        """
        Main method to upload Excel data to Elasticsearch (append-only mode).
        """
        try:
            # Load Excel data
            original_df = self._load_excel_data()
            
            # Create index if it doesn't exist (don't delete existing data)
            self._create_index_if_not_exists()
            
            # Decide whether to filter based on presence of doc_id column
            if 'doc_id' in original_df.columns and not (original_df['doc_id'].isnull().all() or (original_df['doc_id'].astype(str).str.strip() == '').all()):
                new_df = self._filter_new_documents(original_df)
            else:
                # No doc_id provided — upload all and let ES assign IDs
                new_df = original_df
                logger.info("📝 Uploading all rows; Elasticsearch will assign document IDs")
            
            # Upload only new documents
            uploaded_count = self._upload_documents(new_df)
            
            # Print summary
            self._print_summary(original_df, uploaded_count)
            
            if uploaded_count > 0:
                logger.info(f"🎉 Successfully uploaded {uploaded_count} new documents!")
            else:
                logger.info("✅ No new documents to upload - all documents already exist!")
            
        except Exception as e:
            logger.error(f"💥 Elasticsearch upload failed: {e}")
            raise


def main():
    """Main function to run the Elasticsearch uploader."""
    try:
        # Use configuration from .env file for Elasticsearch
        # Excel file path is hardcoded (user-specific)
        logger.info("📋 Using configuration:")
        logger.info(f"   • Excel file: {ElasticsearchUploader.DEFAULT_EXCEL_PATH}")
        logger.info(f"   • Elasticsearch: {config.ELASTICSEARCH_HOST}")
        logger.info(f"   • Index: {config.ELASTICSEARCH_INDEX}")
        
        # Upload to Elasticsearch
        uploader = ElasticsearchUploader()
        uploader.upload_to_elasticsearch()
        
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
