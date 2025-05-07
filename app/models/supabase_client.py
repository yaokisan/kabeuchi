from supabase import create_client  
import os  
  
# --- 環境変数の取得 --- #
url = os.getenv("SUPABASE_URL")

# 1) ANON_KEY → 2) SERVICE_ROLE_KEY の順で取得
key = (
    os.getenv("SUPABASE_ANON_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

if not key or not url:
    # デバッグ用に環境変数の状況をログ出力
    print("[SupabaseClient] URL present:", bool(url),
          "ANON present:", bool(os.getenv("SUPABASE_ANON_KEY")),
          "SERVICE_ROLE present:", bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")))

supabase = create_client(url, key)  
  
def get_supabase():  
    return supabase