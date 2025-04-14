# app/supabase_client.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY") # Anon key

if not supabase_url or not supabase_key:
    # アプリケーション起動時にエラーを明確にする
    raise ValueError("Supabase URL and Key must be set in environment variables.")

# Supabaseクライアントインスタンスを作成
supabase: Client = create_client(supabase_url, supabase_key)
print(f"Supabase client initialized for URL: {supabase_url[:20]}...") # URLの一部だけログ出力 