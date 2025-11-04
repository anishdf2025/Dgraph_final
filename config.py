#!/usr/bin/env python3
"""
Configuration Management for Legal Judgment Database

This module handles all configuration settings using environment variables
and provides a centralized configuration management system.

Author: Anish
Date: November 2025
"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration management class for the application."""
    
    # Elasticsearch Configuration
    ELASTICSEARCH_HOST: str = os.getenv('ELASTICSEARCH_HOST', 'http://localhost:9200')
    ELASTICSEARCH_INDEX: str = os.getenv('ELASTICSEARCH_INDEX', 'graphdb')
    ELASTICSEARCH_TIMEOUT: int = int(os.getenv('ELASTICSEARCH_TIMEOUT', '30'))
    
    # Dgraph Configuration
    DGRAPH_HOST: str = os.getenv('DGRAPH_HOST', 'dgraph-standalone:9080')
    DGRAPH_ZERO: str = os.getenv('DGRAPH_ZERO', 'dgraph-standalone:5080')
    
    # Output Configuration
    RDF_OUTPUT_FILE: str = os.getenv('RDF_OUTPUT_FILE', 'judgments.rdf')
    RDF_SCHEMA_FILE: str = os.getenv('RDF_SCHEMA_FILE', 'rdf.schema')
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'rdf_generator.log')
    
    # Processing Configuration
    MAX_DOCUMENTS: int = int(os.getenv('MAX_DOCUMENTS', '10000'))
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', '100'))
    AUTO_UPLOAD: bool = os.getenv('AUTO_UPLOAD', 'true').lower() == 'true'
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        required_vars = [
            'ELASTICSEARCH_HOST',
            'ELASTICSEARCH_INDEX',
            'RDF_OUTPUT_FILE'
        ]
        
        for var in required_vars:
            if not getattr(cls, var):
                print(f"Error: Required configuration variable {var} is not set")
                return False
        
        return True
    
    @classmethod
    def get_elasticsearch_config(cls) -> dict:
        """Get Elasticsearch configuration as a dictionary."""
        return {
            'host': cls.ELASTICSEARCH_HOST,
            'index': cls.ELASTICSEARCH_INDEX,
            'timeout': cls.ELASTICSEARCH_TIMEOUT
        }
    
    @classmethod
    def get_dgraph_config(cls) -> dict:
        """Get Dgraph configuration as a dictionary."""
        return {
            'host': cls.DGRAPH_HOST,
            'zero': cls.DGRAPH_ZERO
        }
    
    @classmethod
    def get_output_config(cls) -> dict:
        """Get output configuration as a dictionary."""
        return {
            'rdf_file': cls.RDF_OUTPUT_FILE,
            'schema_file': cls.RDF_SCHEMA_FILE
        }
    
    @classmethod
    def get_logging_config(cls) -> dict:
        """Get logging configuration as a dictionary."""
        return {
            'level': cls.LOG_LEVEL,
            'file': cls.LOG_FILE
        }
    
    @classmethod
    def get_processing_config(cls) -> dict:
        """Get processing configuration as a dictionary."""
        return {
            'max_documents': cls.MAX_DOCUMENTS,
            'batch_size': cls.BATCH_SIZE,
            'auto_upload': cls.AUTO_UPLOAD
        }


# Global configuration instance
config = Config()
