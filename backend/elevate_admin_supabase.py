import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv()

def elevate_admin():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
        return

    supabase: Client = create_client(url, key)
    
    admin_email = "admin@tuadministrativo.com"
    
    # Query user
    response = supabase.table("users").select("*").eq("email", admin_email).execute()
    
    if response.data:
        user = response.data[0]
        print(f"Found user: {user['email']} (is_superuser: {user.get('is_superuser')})")
        
        # Update user
        update_response = supabase.table("users").update({
            "is_superuser": True,
            "is_active": True
        }).eq("email", admin_email).execute()
        
        if update_response.data:
            print(f"Successfully elevated {admin_email} to Superuser via Supabase Client.")
        else:
            print("Error updating user.")
    else:
        print(f"Error: User {admin_email} not found in 'users' table.")
        
        # List some users
        all_users = supabase.table("users").select("email").limit(5).execute()
        print("Existing emails in database (first 5):")
        for u in all_users.data:
            print(f" - {u['email']}")

if __name__ == "__main__":
    elevate_admin()
