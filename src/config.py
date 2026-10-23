import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
NEON_DB_URL = os.getenv("NEON_DB_URL")
DB_MONGO = "SmartCity"
