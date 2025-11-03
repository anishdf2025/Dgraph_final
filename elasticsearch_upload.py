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
    
    def __init__(self, excel_file_path: str, es_host: str = "http://192.168.1.170:9200", index_name: str = "graphdb"):
        """
        Initialize the Elasticsearch uploader.
        
        Args:
            excel_file_path: Path to the Excel file
            es_host: Elasticsearch host URL
            index_name: Name of the index to create
        """
        self.excel_file_path = Path(excel_file_path)
        self.es_host = es_host
        self.index_name = index_name
        
        # Initialize Elasticsearch client
        try:
            self.es = Elasticsearch([es_host])
            if not self.es.ping():
                raise ConnectionError(f"Cannot connect to Elasticsearch at {es_host}")
            logger.info(f"✅ Connected to Elasticsearch at {es_host}")
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
    
    def _create_index(self) -> None:
        """Create the Elasticsearch index with proper mapping."""
        try:
            # Delete index if it exists
            if self.es.indices.exists(index=self.index_name):
                logger.info(f"🗑️ Deleting existing index: {self.index_name}")
                self.es.indices.delete(index=self.index_name)
            
            # Create new index with mapping
            mapping = self._create_index_mapping()
            self.es.indices.create(index=self.index_name, body=mapping)
            logger.info(f"✅ Created index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create index: {e}")
            raise
    
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
            "doc_id": self._sanitize_string(row.get('doc_id', 'unknown')),
            "outcome": self._sanitize_string(row.get('Outcome', '')),
            "case_duration": self._sanitize_string(row.get('Case Duration', ''))
        }
        
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
            
            yield {
                "_index": self.index_name,
                "_id": doc["doc_id"],
                "_source": doc
            }
    
    def _upload_documents(self, df: pd.DataFrame) -> None:
        """
        Upload documents to Elasticsearch using bulk API.
        
        Args:
            df: DataFrame containing Excel data
        """
        try:
            logger.info(f"📤 Starting bulk upload to index: {self.index_name}")
            
            # Use bulk helper for efficient uploading
            success_count, failed_items = bulk(
                self.es,
                self._generate_documents(df),
                chunk_size=100,
                request_timeout=30
            )
            
            logger.info(f"✅ Successfully uploaded {success_count} documents")
            
            if failed_items:
                logger.warning(f"⚠️ Failed to upload {len(failed_items)} documents")
                for item in failed_items[:5]:  # Show first 5 failures
                    logger.warning(f"Failed item: {item}")
            
        except Exception as e:
            logger.error(f"❌ Failed to upload documents: {e}")
            raise
    
    def _print_summary(self, df: pd.DataFrame) -> None:
        """Print upload summary and query examples."""
        doc_count = self.es.count(index=self.index_name)['count']
        
        print("\n" + "=" * 70)
        print(f"✅ Data uploaded successfully to Elasticsearch!")
        print(f"🔗 Elasticsearch URL: {self.es_host}")
        print(f"📁 Index name: {self.index_name}")
        print(f"📊 Total documents: {doc_count}")
        print(f"📄 Source rows: {len(df)}")
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
        Main method to upload Excel data to Elasticsearch.
        """
        try:
            # Load Excel data
            df = self._load_excel_data()
            
            # Create index with mapping
            self._create_index()
            
            # Upload documents
            self._upload_documents(df)
            
            # Print summary
            self._print_summary(df)
            
            logger.info("🎉 Elasticsearch upload completed successfully!")
            
        except Exception as e:
            logger.error(f"💥 Elasticsearch upload failed: {e}")
            raise


def main():
    """Main function to run the Elasticsearch uploader."""
    try:
        # Configuration
        excel_file = "/home/anish/Desktop/Anish/Dgraph_final/excel_2024_2025/FINAL/5_sample/tests.xlsx"
        es_host = "http://localhost:9200"
        index_name = "graphdb"
        
        # Upload to Elasticsearch
        uploader = ElasticsearchUploader(excel_file, es_host, index_name)
        uploader.upload_to_elasticsearch()
        
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
