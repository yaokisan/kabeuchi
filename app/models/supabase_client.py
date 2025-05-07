from supabase import create_client  
import os  
  
# Supabaseクライアントの初期化  
url = os.getenv('SUPABASE_URL')  
key = os.getenv('SUPABASE_KEY')  
supabase = create_client(url, key)  
  
def get_supabase():  
    return supabase