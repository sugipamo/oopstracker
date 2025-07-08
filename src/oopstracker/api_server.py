"""
FastAPI server for high-performance similarity search using SimHash and BK-tree.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from .core import CodeMemory, DatabaseManager, DatabaseConfig
from .models import CodeRecord, SimilarityResult
from .simhash_detector import SimHashSimilarityDetector
from .exceptions import OOPSTrackerError


# Pydantic models for API requests/responses
class InsertRequest(BaseModel):
    """Request model for inserting code."""
    text: str = Field(..., min_length=1, description="Code content to insert")
    function_name: Optional[str] = Field(None, description="Function name")
    file_path: Optional[str] = Field(None, description="File path")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class InsertResponse(BaseModel):
    """Response model for insert operation."""
    id: int = Field(..., description="Unique ID of the inserted record")
    status: str = Field(..., description="Operation status")
    simhash: int = Field(..., description="SimHash value of the code")


class SearchResponse(BaseModel):
    """Response model for search operation."""
    results: List[Dict[str, Any]] = Field(..., description="List of similar code records")
    query_simhash: int = Field(..., description="SimHash of the query")
    search_time_ms: float = Field(..., description="Search time in milliseconds")


class ListResponse(BaseModel):
    """Response model for list operation."""
    items: List[Dict[str, Any]] = Field(..., description="List of all code records")
    total: int = Field(..., description="Total number of records")


class DeleteRequest(BaseModel):
    """Request model for deleting code."""
    id: int = Field(..., description="ID of the record to delete")


class DeleteResponse(BaseModel):
    """Response model for delete operation."""
    status: str = Field(..., description="Operation status")


class StatsResponse(BaseModel):
    """Response model for statistics."""
    total_records: int = Field(..., description="Total number of records")
    bk_tree_stats: Dict[str, Any] = Field(..., description="BK-tree statistics")
    performance_metrics: Dict[str, Any] = Field(..., description="Performance metrics")


# Global variables for the API server
similarity_detector: Optional[SimHashSimilarityDetector] = None
database_manager: Optional[DatabaseManager] = None
performance_metrics = {
    "total_searches": 0,
    "total_inserts": 0,
    "avg_search_time_ms": 0.0,
    "avg_insert_time_ms": 0.0,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global similarity_detector, database_manager
    
    # Startup
    try:
        # Initialize database
        config = DatabaseConfig(
            db_path="oopstracker_api.db",
            create_tables=True
        )
        database_manager = DatabaseManager(config)
        
        # Initialize similarity detector
        similarity_detector = SimHashSimilarityDetector(threshold=5)
        
        # Load existing records into BK-tree
        await rebuild_index()
        
        logger = logging.getLogger(__name__)
        logger.info("FastAPI server started successfully")
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to start server: {e}")
        raise
    
    yield
    
    # Shutdown
    logger = logging.getLogger(__name__)
    logger.info("FastAPI server shutting down")


# Create FastAPI app
app = FastAPI(
    title="OOPStracker API",
    description="High-performance code similarity search using SimHash and BK-tree",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def rebuild_index():
    """Rebuild the BK-tree index from database records."""
    global similarity_detector, database_manager
    
    if not similarity_detector or not database_manager:
        return
    
    try:
        # Get all records from database
        records = database_manager.get_all_records()
        
        # Rebuild the similarity detector index
        similarity_detector.rebuild_index(records)
        
        logger.info(f"Rebuilt BK-tree index with {len(records)} records")
        
    except Exception as e:
        logger.error(f"Failed to rebuild index: {e}")
        raise


@app.post("/insert", response_model=InsertResponse)
async def insert_code(request: InsertRequest, background_tasks: BackgroundTasks):
    """Insert a new code snippet into the database."""
    global similarity_detector, database_manager, performance_metrics
    
    if not similarity_detector or not database_manager:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    try:
        import time
        start_time = time.time()
        
        # Create code record
        record = CodeRecord(
            code_content=request.text,
            function_name=request.function_name,
            file_path=request.file_path,
            metadata=request.metadata or {}
        )
        
        # Calculate SimHash
        record.simhash = similarity_detector.calculate_simhash(request.text)
        
        # Generate SHA-256 hash for uniqueness
        record.generate_hash()
        
        # Insert into database
        record_id = database_manager.insert_record(record)
        record.id = record_id
        
        # Add to similarity detector
        similarity_detector.add_record(record)
        
        # Update performance metrics
        end_time = time.time()
        insert_time_ms = (end_time - start_time) * 1000
        performance_metrics["total_inserts"] += 1
        performance_metrics["avg_insert_time_ms"] = (
            (performance_metrics["avg_insert_time_ms"] * (performance_metrics["total_inserts"] - 1) + insert_time_ms) /
            performance_metrics["total_inserts"]
        )
        
        logger.info(f"Inserted code record {record_id} with SimHash {record.simhash}")
        
        return InsertResponse(
            id=record_id,
            status="ok",
            simhash=record.simhash
        )
        
    except Exception as e:
        logger.error(f"Failed to insert code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search", response_model=SearchResponse)
async def search_similar_code(
    q: str = Query(..., description="Query code to search for"),
    threshold: int = Query(5, ge=0, le=64, description="Maximum Hamming distance threshold")
):
    """Search for similar code snippets."""
    global similarity_detector, performance_metrics
    
    if not similarity_detector:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    try:
        import time
        start_time = time.time()
        
        # Find similar records
        result = similarity_detector.find_similar(q, max_distance=threshold)
        
        # Convert to response format
        search_results = []
        for record in result.matched_records:
            search_results.append({
                "id": record.id,
                "text": record.code_content,
                "function_name": record.function_name,
                "file_path": record.file_path,
                "similarity_score": record.similarity_score,
                "simhash": record.simhash,
                "timestamp": record.timestamp.isoformat() if record.timestamp else None
            })
        
        # Calculate query SimHash
        query_simhash = similarity_detector.calculate_simhash(q)
        
        # Update performance metrics
        end_time = time.time()
        search_time_ms = (end_time - start_time) * 1000
        performance_metrics["total_searches"] += 1
        performance_metrics["avg_search_time_ms"] = (
            (performance_metrics["avg_search_time_ms"] * (performance_metrics["total_searches"] - 1) + search_time_ms) /
            performance_metrics["total_searches"]
        )
        
        logger.info(f"Search completed in {search_time_ms:.2f}ms, found {len(search_results)} results")
        
        return SearchResponse(
            results=search_results,
            query_simhash=query_simhash,
            search_time_ms=search_time_ms
        )
        
    except Exception as e:
        logger.error(f"Failed to search code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list", response_model=ListResponse)
async def list_all_code(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip")
):
    """List all stored code records."""
    global database_manager
    
    if not database_manager:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    try:
        # Get all records (TODO: implement pagination in database layer)
        all_records = database_manager.get_all_records()
        
        # Apply pagination
        paginated_records = all_records[offset:offset + limit]
        
        # Convert to response format
        items = []
        for record in paginated_records:
            items.append({
                "id": record.id,
                "text": record.code_content,
                "function_name": record.function_name,
                "file_path": record.file_path,
                "simhash": record.simhash,
                "code_hash": record.code_hash,
                "timestamp": record.timestamp.isoformat() if record.timestamp else None
            })
        
        return ListResponse(
            items=items,
            total=len(all_records)
        )
        
    except Exception as e:
        logger.error(f"Failed to list code records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete", response_model=DeleteResponse)
async def delete_code(request: DeleteRequest):
    """Delete a code record by ID."""
    global similarity_detector, database_manager
    
    if not similarity_detector or not database_manager:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    try:
        # Find the record first
        all_records = database_manager.get_all_records()
        target_record = None
        
        for record in all_records:
            if record.id == request.id:
                target_record = record
                break
        
        if not target_record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Remove from similarity detector
        if target_record.simhash:
            similarity_detector.remove_record(request.id, target_record.simhash)
        
        # TODO: Implement delete in database manager
        # For now, we'll just log the deletion
        logger.warning(f"Delete operation not fully implemented for record {request.id}")
        
        return DeleteResponse(status="ok")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete code record: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get server statistics."""
    global similarity_detector, database_manager, performance_metrics
    
    if not similarity_detector or not database_manager:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    try:
        # Get total records
        all_records = database_manager.get_all_records()
        total_records = len(all_records)
        
        # Get BK-tree statistics
        bk_tree_stats = similarity_detector.get_stats()
        
        return StatsResponse(
            total_records=total_records,
            bk_tree_stats=bk_tree_stats,
            performance_metrics=performance_metrics.copy()
        )
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "OOPStracker API is running"}


@app.post("/rebuild-index")
async def rebuild_index_endpoint(background_tasks: BackgroundTasks):
    """Rebuild the BK-tree index from database records."""
    try:
        background_tasks.add_task(rebuild_index)
        return {"status": "ok", "message": "Index rebuild started"}
    except Exception as e:
        logger.error(f"Failed to start index rebuild: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """Run the FastAPI server."""
    uvicorn.run(
        "oopstracker.api_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()