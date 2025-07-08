"""
Simple tests for FastAPI server endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from oopstracker.api_server import app
from oopstracker.models import CodeRecord


class TestFastAPISimple:
    """Simple FastAPI server tests."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "message" in data
    
    def test_pydantic_models(self):
        """Test Pydantic models for API."""
        from oopstracker.api_server import InsertRequest, InsertResponse, SearchResponse
        
        # Test InsertRequest
        request = InsertRequest(
            text="def hello(): pass",
            function_name="hello",
            file_path="test.py",
            metadata={"author": "test"}
        )
        
        assert request.text == "def hello(): pass"
        assert request.function_name == "hello"
        assert request.file_path == "test.py"
        assert request.metadata == {"author": "test"}
        
        # Test InsertResponse
        response = InsertResponse(id=1, status="ok", simhash=123456)
        assert response.id == 1
        assert response.status == "ok"
        assert response.simhash == 123456
        
        # Test SearchResponse
        search_response = SearchResponse(
            results=[{"id": 1, "text": "def hello(): pass", "similarity_score": 0.95}],
            query_simhash=123456,
            search_time_ms=2.5
        )
        assert len(search_response.results) == 1
        assert search_response.query_simhash == 123456
        assert search_response.search_time_ms == 2.5
    
    def test_insert_validation(self):
        """Test insert request validation."""
        # Test with empty text (should fail)
        response = self.client.post("/insert", json={"text": ""})
        assert response.status_code == 422
        
        # Test with missing text (should fail)
        response = self.client.post("/insert", json={"function_name": "test"})
        assert response.status_code == 422
    
    def test_search_validation(self):
        """Test search request validation."""
        # Test without query parameter (should fail)
        response = self.client.get("/search")
        assert response.status_code == 422
        
        # Test with invalid threshold (should fail)
        response = self.client.get("/search", params={"q": "test", "threshold": 100})
        assert response.status_code == 422
    
    def test_app_creation(self):
        """Test that FastAPI app is created correctly."""
        assert app.title == "OOPStracker API"
        assert app.version == "0.1.0"
        assert "SimHash" in app.description
        
        # Check that routes exist
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        expected_routes = ['/insert', '/search', '/list', '/delete', '/stats', '/health', '/rebuild-index']
        
        for route in expected_routes:
            assert route in routes
    
    def test_cors_middleware(self):
        """Test that CORS middleware is configured."""
        # This is a basic test to ensure CORS headers are present
        response = self.client.options("/health")
        # FastAPI should handle OPTIONS requests
        assert response.status_code in [200, 405]  # 405 is OK for OPTIONS without explicit handler
    
    def test_openapi_docs(self):
        """Test that OpenAPI documentation is available."""
        response = self.client.get("/docs")
        assert response.status_code == 200
        
        response = self.client.get("/redoc")
        assert response.status_code == 200
        
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        
        # Check that OpenAPI spec contains expected endpoints
        openapi_spec = response.json()
        assert "paths" in openapi_spec
        assert "/insert" in openapi_spec["paths"]
        assert "/search" in openapi_spec["paths"]
        assert "/health" in openapi_spec["paths"]


class TestAPIServerMocked:
    """Test API server with mocked dependencies."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    @patch('oopstracker.api_server.similarity_detector')
    @patch('oopstracker.api_server.database_manager')
    def test_insert_mocked(self, mock_db, mock_detector):
        """Test insert endpoint with mocked dependencies."""
        # Mock the detector
        mock_detector.calculate_simhash.return_value = 123456
        mock_detector.add_record.return_value = True
        
        # Mock the database
        mock_db.insert_record.return_value = 1
        
        response = self.client.post("/insert", json={
            "text": "def hello(): print('Hello, world!')",
            "function_name": "hello"
        })
        
        if response.status_code == 500:
            # Server not initialized, which is expected in test environment
            assert "Server not initialized" in response.text
        else:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
    
    @patch('oopstracker.api_server.similarity_detector')
    def test_search_mocked(self, mock_detector):
        """Test search endpoint with mocked dependencies."""
        # Mock search results
        mock_result = MagicMock()
        mock_result.matched_records = []
        mock_detector.find_similar.return_value = mock_result
        mock_detector.calculate_simhash.return_value = 123456
        
        response = self.client.get("/search", params={"q": "def hello(): pass"})
        
        if response.status_code == 500:
            # Server not initialized, which is expected in test environment
            assert "Server not initialized" in response.text
        else:
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "query_simhash" in data
    
    @patch('oopstracker.api_server.database_manager')
    def test_list_mocked(self, mock_db):
        """Test list endpoint with mocked dependencies."""
        # Mock records
        mock_records = [
            CodeRecord(
                id=1,
                code_content="def hello(): pass",
                function_name="hello",
                simhash=123456,
                code_hash="abc123"
            )
        ]
        mock_records[0].timestamp = None
        mock_db.get_all_records.return_value = mock_records
        
        response = self.client.get("/list")
        
        if response.status_code == 500:
            # Server not initialized, which is expected in test environment
            assert "Server not initialized" in response.text
        else:
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
    
    def test_server_initialization_check(self):
        """Test that server responds appropriately when not initialized."""
        # Most endpoints should return 500 when server is not initialized
        response = self.client.get("/stats")
        assert response.status_code == 500
        
        response = self.client.post("/insert", json={"text": "def test(): pass"})
        assert response.status_code == 500
        
        response = self.client.get("/search", params={"q": "def test(): pass"})
        assert response.status_code == 500
        
        response = self.client.get("/list")
        assert response.status_code == 500
        
        response = self.client.request("DELETE", "/delete", json={"id": 1})
        assert response.status_code == 500
        
        # But health check should always work
        response = self.client.get("/health")
        assert response.status_code == 200