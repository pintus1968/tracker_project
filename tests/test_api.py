"""API Tests"""
import unittest
import json
from server import app

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    def test_health(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
