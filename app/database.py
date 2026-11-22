import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "").strip()
DB_PORT = os.getenv("DB_PORT", "5432").strip()
DB_NAME = os.getenv("DB_NAME", "").strip()
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
DB_SSLMODE = os.getenv("DB_SSLMODE", "prefer").strip()

required_values = {
    "DB_HOST": DB_HOST,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
}

missing = [key for key, value in required_values.items() if not value]

if missing:
    raise RuntimeError(f"Missing database configuration: {', '.join(missing)}")

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
    query={"sslmode": DB_SSLMODE},
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)


def test_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT current_database(), current_user"))
            database, user = result.fetchone()

            print("TradePulse database connection successful!")
            print(f"Database: {database}")
            print(f"User: {user}")

    except SQLAlchemyError as error:
        print("Database connection failed.")
        print(f"Error: {error}")


if __name__ == "__main__":
    test_connection()
