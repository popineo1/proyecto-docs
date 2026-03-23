import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Database Connection String
DATABASE_URL = os.getenv("DATABASE_URL")

print(f"Testing connection to: {DATABASE_URL.split('@')[1] if DATABASE_URL else 'None'}")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env")
    exit(1)

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("✅ Successfully connected to the database!")
        
        # Check for tables
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result]
        print(f"Tables found: {tables}")
        
        if 'users' in tables:
            count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            print(f"✅ 'users' table exists. Current count: {count}")
        else:
            print("❌ 'users' table NOT found!")

        if 'tenants' in tables:
            print("✅ 'tenants' table exists.")
        else:
            print("❌ 'tenants' table NOT found!")

except Exception as e:
    print(f"❌ Connection failed: {str(e)}")
