import unittest
import json
from unittest.mock import patch
from api.app import create_app
from utils.api_key_manager import APIKeyManager
from config.settings import FRONTEND_URL

class BackendHealthTestCase(unittest.TestCase):
    def setUp(self):
        """Set up the Flask test client and application context."""
        # Patch the actual components inside create_app to avoid hitting live APIs during setup.
        # We also need to mock dimension computation in create_app.
        with patch('api.app.GeminiEmbedder.embed_text', return_value=[0.1]*1536), \
             patch('retrieval.reranker.Reranker.__init__', return_value=None):
            self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def test_health_endpoints(self):
        """Verify that health check endpoints return HTTP 200 and healthy status."""
        for endpoint in ['/health', '/api/health']:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertEqual(data.get("status"), "healthy")

    def test_recommend_endpoint_contract(self):
        """
        Verify that POST /api/recommend returns HTTP 200 (or graceful fallback)
        and adheres to the expected structural decoupling.
        """
        payload = {"query": "test query"}

        # We will mock the dependencies to simulate a successful processing
        # and avoid real Gemini API calls during tests.
        with patch('api.app.GeminiEmbedder.embed_text', return_value=[0.1]*1536), \
             patch('retrieval.retriever.Retriever.search_summary', return_value=[
                 {"book_id": "1", "title": "Test Book", "summary_text": "Summary", "score": 0.85, "metadata": {}}
             ]), \
             patch('retrieval.reranker.Reranker.rerank_results', return_value=[
                 {"book_id": "1", "title": "Test Book", "summary_text": "Summary", "score": 0.85, "metadata": {}}
             ]), \
             patch('generation.answer_generator.AnswerGenerator.generate_recommendation', return_value="Here is a book"):

            response = self.client.post('/api/recommend',
                                        data=json.dumps(payload),
                                        content_type='application/json')

            # Should be HTTP 200 with the correct structure
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content_type, 'application/json')
            data = json.loads(response.data)

            # Check structure
            self.assertIn("status", data)
            self.assertIn("recommendations", data)
            self.assertIn("answer", data)
            self.assertIsInstance(data["recommendations"], list)
            self.assertIsInstance(data["answer"], str)

    def test_admin_books_graceful_degradation(self):
        """
        Verify that GET /api/admin/books handles absent raw data gracefully,
        returning a proper structure without crashing.
        """
        response = self.client.get('/api/admin/books?page=1&limit=5')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertIn("books", data)
        self.assertIn("total_books", data)
        self.assertIn("total_pages", data)
        self.assertIn("current_page", data)
        self.assertIsInstance(data["books"], list)
        self.assertTrue(data["current_page"] == 1)

    def test_cors_network_verification(self):
        """
        Verify that a pre-flight OPTIONS request returns the correct CORS headers
        whitelisting the frontend URL and methods.
        """
        # Mock origin hitting an endpoint that allows CORS
        headers = {
            "Origin": FRONTEND_URL,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization"
        }
        response = self.client.options('/api/recommend', headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.headers.get("Access-Control-Allow-Origin"), [FRONTEND_URL, "*"])
        # Flask-CORS behavior: it mirrors the requested Origin or '*' if allowed
        allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")
        self.assertIn("GET", allowed_methods)
        self.assertIn("POST", allowed_methods)
        self.assertIn("PUT", allowed_methods)
        self.assertIn("DELETE", allowed_methods)
        self.assertIn("OPTIONS", allowed_methods)

        allowed_headers = response.headers.get("Access-Control-Allow-Headers", "")
        self.assertIn("Content-Type", allowed_headers)
        self.assertIn("Authorization", allowed_headers)

    def test_api_key_manager_failover(self):
        """
        Verify the rotation logic inside APIKeyManager triggering upon a mocked
        429 Rate Limit error.
        """
        keys = ["key1", "key2", "key3"]
        manager = APIKeyManager(keys, service_name="TestService")

        # Initial check
        first_key = manager.get_current_key()
        self.assertEqual(first_key, "key1")

        # Trigger Rate Limit Failover
        manager.report_error(first_key, error_msg="429 Too Many Requests")

        # Check rotation occurred
        second_key = manager.get_current_key()
        self.assertEqual(second_key, "key2")

        # Trigger Max Attempts (set to 3 by default) Failover
        # We need to report errors against the CURRENT active key (second_key)
        for _ in range(manager.max_attempts_per_key):
            active_key = manager.get_current_key()
            manager.report_error(active_key, error_msg="Some internal failure")

        third_key = manager.get_current_key()
        self.assertEqual(third_key, "key3")


if __name__ == '__main__':
    unittest.main()
