#!/usr/bin/env python3
"""
FastAPI Application for Legal Judgment Database RDF Generator

This module provides REST API endpoints for processing legal judgments from Elasticsearch,
generating RDF files, and uploading to Dgraph with automatic document tracking.

Features:
- Process only new/unprocessed documents
- Mark documents as processed in Elasticsearch
- Real-time status updates
- Incremental processing support
- Health check endpoints

Author: Anish
Date: November 2025
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import logging
import os
import asyncio

from config import config
from incremental_processor import IncrementalRDFProcessor
from elasticsearch_handler import ElasticsearchHandler
from utils import setup_logging
from auto_processor import start_auto_processor, stop_auto_processor, get_auto_processor_status

# Initialize FastAPI app
app = FastAPI(
    title="Legal Judgment RDF Generator API",
    description="API for processing legal judgments and generating RDF files for Dgraph",
    version="1.0.0"
)

# Initialize logger
logger = setup_logging()

# Global processing status
processing_status = {
    "is_processing": False,
    "last_run": None,
    "last_run_status": None,
    "last_run_stats": None,
    "current_progress": None
}


# Pydantic Models
class ProcessRequest(BaseModel):
    """Request model for processing documents."""
    doc_ids: Optional[List[str]] = Field(None, description="Specific document IDs to process. If not provided, all unprocessed documents will be processed.")
    force_reprocess: bool = Field(False, description="Force reprocessing of already processed documents")
    auto_upload: bool = Field(True, description="Automatically upload to Dgraph after processing")


class ProcessResponse(BaseModel):
    """Response model for processing requests."""
    status: str
    message: str
    job_id: Optional[str] = None
    timestamp: str


class StatusResponse(BaseModel):
    """Response model for status check."""
    is_processing: bool
    last_run: Optional[str]
    last_run_status: Optional[str]
    last_run_stats: Optional[Dict[str, Any]]
    current_progress: Optional[str]


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    elasticsearch_connected: bool
    dgraph_configured: bool
    timestamp: str


# Background task for processing
def process_documents_task(doc_ids: Optional[List[str]], force_reprocess: bool, auto_upload: bool):
    """
    Background task to process documents and update status.
    
    Args:
        doc_ids: Optional list of specific document IDs to process
        force_reprocess: Whether to reprocess already processed documents
        auto_upload: Whether to automatically upload to Dgraph
    """
    global processing_status
    
    try:
        processing_status["is_processing"] = True
        processing_status["current_progress"] = "Initializing processor..."
        
        logger.info(f"🚀 Starting background processing task...")
        logger.info(f"   • Document IDs: {doc_ids if doc_ids else 'All unprocessed'}")
        logger.info(f"   • Force reprocess: {force_reprocess}")
        logger.info(f"   • Auto upload: {auto_upload}")
        
        # Initialize incremental processor
        processor = IncrementalRDFProcessor()
        
        # Process documents
        processing_status["current_progress"] = "Loading documents from Elasticsearch..."
        stats = processor.process_incremental(
            doc_ids=doc_ids,
            force_reprocess=force_reprocess,
            auto_upload=auto_upload
        )
        
        # Update status
        processing_status["is_processing"] = False
        processing_status["last_run"] = datetime.now().isoformat()
        processing_status["last_run_status"] = "success"
        processing_status["last_run_stats"] = stats
        processing_status["current_progress"] = None
        
        logger.info("✅ Background processing completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Background processing failed: {e}")
        processing_status["is_processing"] = False
        processing_status["last_run"] = datetime.now().isoformat()
        processing_status["last_run_status"] = "error"
        processing_status["last_run_stats"] = {"error": str(e)}
        processing_status["current_progress"] = None


# API Endpoints

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Legal Judgment RDF Generator API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify system status.
    
    Returns:
        HealthResponse: System health status
    """
    es_connected = False
    dgraph_configured = False
    
    try:
        # Check Elasticsearch connection directly without ElasticsearchHandler
        from elasticsearch import Elasticsearch
        es_config = config.get_elasticsearch_config()
        es = Elasticsearch([es_config['host']])
        es_connected = es.ping()
        
        # Check Dgraph configuration
        dgraph_config = config.get_dgraph_config()
        dgraph_configured = bool(dgraph_config.get('host') and dgraph_config.get('zero'))
        
        status = "healthy" if (es_connected and dgraph_configured) else "degraded"
        
        return HealthResponse(
            status=status,
            elasticsearch_connected=es_connected,
            dgraph_configured=dgraph_configured,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            elasticsearch_connected=es_connected,
            dgraph_configured=dgraph_configured,
            timestamp=datetime.now().isoformat()
        )


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Get current processing status.
    
    Returns:
        StatusResponse: Current processing status and last run information
    """
    return StatusResponse(
        is_processing=processing_status["is_processing"],
        last_run=processing_status["last_run"],
        last_run_status=processing_status["last_run_status"],
        last_run_stats=processing_status["last_run_stats"],
        current_progress=processing_status["current_progress"]
    )


@app.post("/process", response_model=ProcessResponse)
async def process_judgments(
    request: ProcessRequest,
    background_tasks: BackgroundTasks
):
    """
    Process legal judgments from Elasticsearch and generate RDF.
    
    This endpoint:
    1. Identifies unprocessed documents in Elasticsearch
    2. Generates RDF triples using modular handlers
    3. Uploads to Dgraph (if auto_upload=True)
    4. Marks documents as processed in Elasticsearch
    
    Args:
        request: ProcessRequest with processing options
        background_tasks: FastAPI background tasks
        
    Returns:
        ProcessResponse: Processing status and job information
        
    Raises:
        HTTPException: If processing is already in progress
    """
    # Check if already processing
    if processing_status["is_processing"]:
        raise HTTPException(
            status_code=409,
            detail="Processing is already in progress. Please wait for completion."
        )
    
    # Start background processing
    background_tasks.add_task(
        process_documents_task,
        request.doc_ids,
        request.force_reprocess,
        request.auto_upload
    )
    
    return ProcessResponse(
        status="accepted",
        message="Processing started in background",
        job_id=datetime.now().strftime("%Y%m%d%H%M%S"),
        timestamp=datetime.now().isoformat()
    )


@app.get("/documents/unprocessed")
async def get_unprocessed_documents(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of documents to return")
):
    """
    Get list of unprocessed documents from Elasticsearch.
    
    Args:
        limit: Maximum number of documents to return
        
    Returns:
        List of unprocessed document IDs and titles
    """
    try:
        es_handler = ElasticsearchHandler()
        unprocessed = es_handler.get_unprocessed_documents(limit=limit)
        
        return {
            "total": len(unprocessed),
            "documents": unprocessed
        }
    except Exception as e:
        logger.error(f"Failed to get unprocessed documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/count")
async def get_document_counts():
    """
    Get counts of processed and unprocessed documents.
    
    Returns:
        Document counts by processing status
    """
    try:
        es_handler = ElasticsearchHandler()
        counts = es_handler.get_processing_counts()
        
        return counts
    except Exception as e:
        logger.error(f"Failed to get document counts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/mark-processed")
async def mark_documents_processed(doc_ids: List[str]):
    """
    Manually mark specific documents as processed.
    
    Args:
        doc_ids: List of document IDs to mark as processed
        
    Returns:
        Success message and count of updated documents
    """
    try:
        es_handler = ElasticsearchHandler()
        updated_count = es_handler.mark_documents_as_processed(doc_ids)
        
        return {
            "status": "success",
            "message": f"Marked {updated_count} documents as processed",
            "updated_count": updated_count,
            "doc_ids": doc_ids
        }
    except Exception as e:
        logger.error(f"Failed to mark documents as processed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/reset-processed")
async def reset_processed_status(doc_ids: Optional[List[str]] = None):
    """
    Reset processed status for documents (for reprocessing).
    
    Args:
        doc_ids: Optional list of document IDs. If not provided, resets all documents.
        
    Returns:
        Success message and count of reset documents
    """
    try:
        es_handler = ElasticsearchHandler()
        reset_count = es_handler.reset_processed_status(doc_ids)
        
        return {
            "status": "success",
            "message": f"Reset processed status for {reset_count} documents",
            "reset_count": reset_count,
            "doc_ids": doc_ids if doc_ids else "all"
        }
    except Exception as e:
        logger.error(f"Failed to reset processed status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_statistics():
    """
    Get overall system statistics.
    
    Returns:
        System statistics including document counts and processing history
    """
    try:
        es_handler = ElasticsearchHandler()
        
        # Get document counts
        counts = es_handler.get_processing_counts()
        
        # Get RDF file info if exists
        rdf_file = Path(config.get_output_config()['rdf_file'])
        rdf_stats = None
        if rdf_file.exists():
            rdf_stats = {
                "exists": True,
                "size_bytes": rdf_file.stat().st_size,
                "last_modified": datetime.fromtimestamp(rdf_file.stat().st_mtime).isoformat()
            }
        
        return {
            "elasticsearch": counts,
            "rdf_file": rdf_stats,
            "last_processing": {
                "timestamp": processing_status["last_run"],
                "status": processing_status["last_run_status"],
                "stats": processing_status["last_run_stats"]
            },
            "auto_processor": get_auto_processor_status()
        }
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auto-processor/status")
async def get_auto_processor_info():
    """
    Get automatic processor status.
    
    Returns:
        Auto processor status and statistics
    """
    return get_auto_processor_status()


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize system on startup."""
    logger.info("🚀 FastAPI application starting...")
    logger.info("📡 Checking system connections...")
    
    # Validate configuration
    if not config.validate():
        logger.error("❌ Configuration validation failed!")
    else:
        logger.info("✅ Configuration validated successfully")
    
    # Start automatic background processor
    check_interval = int(os.getenv('AUTO_PROCESS_INTERVAL', '60'))
    logger.info(f"🤖 Starting automatic document processor (interval: {check_interval}s)...")
    asyncio.create_task(start_auto_processor(check_interval=check_interval))
    logger.info("✅ Automatic document processor started!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("🛑 FastAPI application shutting down...")
    
    # Stop automatic processor
    await stop_auto_processor()
    logger.info("🛑 Automatic document processor stopped")


if __name__ == "__main__":
    import uvicorn
    
    # Get host and port from environment or use defaults
    host = "0.0.0.0"
    port = 8003
    
    logger.info(f"🚀 Starting FastAPI server on {host}:{port}")
    logger.info(f"📚 API documentation available at http://{host}:{port}/docs")
    
    uvicorn.run(
        "fastapi_app:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
