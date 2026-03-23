from sqlalchemy import create_engine, text
import sys
import os

# Add the current directory to sys.path to allow importing 'app'
sys.path.append(os.getcwd())

from app.core.config import settings

def elevate_admin():
    engine = create_engine(settings.DATABASE_URL)
    
    admin_email = "admin@tuadministrativo.com"
    
    with engine.connect() as connection:
        # Check if user exists
        result = connection.execute(text("SELECT id, email, is_superuser FROM users WHERE email = :email"), {"email": admin_email}).fetchone()
        
        if result:
            print(f"Found user: {result.email} (is_superuser: {result.is_superuser})")
            # Update user
            connection.execute(
                text("UPDATE users SET is_superuser = TRUE, is_active = TRUE WHERE email = :email"),
                {"email": admin_email}
            )
            connection.commit()
            print(f"Successfully elevated {admin_email} to Superuser via direct SQL.")
        else:
            print(f"Error: User {admin_email} not found in the database. (Found no match for email in 'users' table)")
            
            # List some users to verify the table content
            all_users = connection.execute(text("SELECT email FROM users LIMIT 5")).fetchall()
            print("Existing emails in database (first 5):")
            for u in all_users:
                print(f" - {u.email}")

if __name__ == "__main__":
    elevate_admin()
