import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(override=True)

def get_connection():
    print("DATABASE_URL USADA:", os.getenv("DATABASE_URL"))
    return psycopg2.connect(os.getenv("DATABASE_URL"))
