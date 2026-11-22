from app.database import engine
from app.models import Base


def initialize_database():
    Base.metadata.create_all(bind=engine)

    print("TradePulse database tables created successfully!")

    print("\nTables:")
    for table_name in Base.metadata.tables:
        print(f"- {table_name}")


if __name__ == "__main__":
    initialize_database()
