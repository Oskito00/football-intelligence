# config.py
import os
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv()


class Config:
    DB_HOST = os.getenv('DB_HOST')
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    API_FOOTBALL_KEY = os.getenv('API_FOOTBALL_KEY')

class ProductionConfig(Config):
    def __init__(self):
        # Parse DATABASE_URL if a deployment platform provides one.
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            parsed = urlparse(database_url)
            self.DB_HOST = parsed.hostname
            self.DB_NAME = parsed.path[1:]  # Remove leading slash
            self.DB_USER = parsed.username
            self.DB_PASSWORD = parsed.password
            self.DB_PORT = parsed.port or 5432
        else:
            # Fallback to individual environment variables
            self.DB_HOST = os.getenv('DB_HOST')
            self.DB_NAME = os.getenv('DB_NAME')
            self.DB_USER = os.getenv('DB_USER')
            self.DB_PASSWORD = os.getenv('DB_PASSWORD')
            self.DB_PORT = os.getenv('DB_PORT', 5432)

def get_config():
    env = os.getenv("ENV", "dev")
    return ProductionConfig() if env == "prod" else Config()
