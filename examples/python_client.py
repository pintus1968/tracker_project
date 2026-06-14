"""Python API Client"""
import requests

class TrackerClient:
    def __init__(self, base_url="http://localhost:5000/api"):
        self.base_url = base_url
    
    def get_devices(self):
        return requests.get(f"{self.base_url}/devices").json()

if __name__ == "__main__":
    client = TrackerClient()
    print(client.get_devices())
