#!/usr/bin/env python3
"""
Automatic Background Processor for Legal Judgment Database

This module runs a background task that automatically checks for new documents
in Elasticsearch and processes them to Dgraph at regular intervals.

Features:
- Automatic polling for new documents
- Configurable check interval
- Non-blocking background execution
- Error recovery and retry logic

Author: Anish
Date: November 2025
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from config import config
from incremental_processor import IncrementalRDFProcessor
from elasticsearch_handler import ElasticsearchHandler
from utils import setup_logging


class AutoProcessor:
    """
    Automatic background processor that polls Elasticsearch for new documents
    and processes them to Dgraph automatically.
    """
    
    def __init__(self, check_interval: int = 60):
        """
        Initialize the auto processor.
        
        Args:
            check_interval: Seconds between checks for new documents (default: 60)
        """
        self.logger = setup_logging()
        self.check_interval = check_interval
        self.is_running = False
        self.is_processing = False
        self.last_check: Optional[datetime] = None
        self.last_process: Optional[datetime] = None
        self.total_processed = 0
        
        self.logger.info(f"🤖 AutoProcessor initialized (check interval: {check_interval}s)")
    
    async def start(self):
        """Start the automatic processing loop."""
        self.is_running = True
        self.logger.info("🚀 Starting automatic document processor...")
        
        while self.is_running:
            try:
                await self._check_and_process()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"❌ Error in auto-processing loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Stop the automatic processing loop."""
        self.logger.info("🛑 Stopping automatic document processor...")
        self.is_running = False
    
    async def _check_and_process(self):
        """Check for new documents and process them if found."""
        self.last_check = datetime.now()
        
        try:
            # Check if already processing
            if self.is_processing:
                self.logger.info("⏳ Previous processing still in progress, skipping check...")
                return
            
            # Check for unprocessed documents
            es_handler = ElasticsearchHandler()
            counts = es_handler.get_processing_counts()
            
            unprocessed_count = counts.get('unprocessed', 0)
            
            if unprocessed_count == 0:
                self.logger.info(f"✅ No new documents to process (checked at {self.last_check.strftime('%H:%M:%S')})")
                return
            
            # Process new documents
            self.logger.info(f"📦 Found {unprocessed_count} new document(s) - Starting automatic processing...")
            self.is_processing = True
            
            # Run processing in thread pool to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self._process_documents
            )
            
            self.is_processing = False
            self.last_process = datetime.now()
            
        except Exception as e:
            self.logger.error(f"❌ Error during auto-check: {e}")
            self.is_processing = False
    
    def _process_documents(self):
        """Process unprocessed documents (runs in thread pool)."""
        try:
            processor = IncrementalRDFProcessor()
            result = processor.process_incremental(
                doc_ids=None,
                force_reprocess=False,
                auto_upload=True
            )
            
            if result['status'] == 'success':
                docs_processed = result.get('documents_processed', 0)
                self.total_processed += docs_processed
                self.logger.info(f"✅ Auto-processed {docs_processed} document(s) successfully!")
                self.logger.info(f"📊 Total documents auto-processed: {self.total_processed}")
            else:
                self.logger.error(f"❌ Auto-processing failed: {result.get('message')}")
                
        except Exception as e:
            self.logger.error(f"❌ Error in document processing: {e}")
    
    def get_status(self) -> dict:
        """Get current status of the auto processor."""
        return {
            "is_running": self.is_running,
            "is_processing": self.is_processing,
            "check_interval": self.check_interval,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_process": self.last_process.isoformat() if self.last_process else None,
            "total_processed": self.total_processed
        }


# Global auto processor instance
auto_processor: Optional[AutoProcessor] = None


async def start_auto_processor(check_interval: int = 60):
    """
    Start the automatic background processor.
    
    Args:
        check_interval: Seconds between checks for new documents
    """
    global auto_processor
    
    if auto_processor and auto_processor.is_running:
        logging.info("⚠️ Auto processor already running")
        return
    
    auto_processor = AutoProcessor(check_interval=check_interval)
    await auto_processor.start()


async def stop_auto_processor():
    """Stop the automatic background processor."""
    global auto_processor
    
    if auto_processor:
        await auto_processor.stop()


def get_auto_processor_status() -> dict:
    """Get status of the auto processor."""
    if auto_processor:
        return auto_processor.get_status()
    return {
        "is_running": False,
        "is_processing": False,
        "message": "Auto processor not initialized"
    }
