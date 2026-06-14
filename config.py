"""Configuration for Tracker Project"""
import os

DATABASE = os.getenv('DATABASE_PATH', 'tracker.db')
DEVICES_FILE = os.getenv('DEVICES_FILE', 'devices.json')
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
