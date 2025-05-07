#!/usr/bin/env python
"""
SQLite (wallbounce.db) -> Supabase へデータ移行
既存データは保持し、SQLite 側の id は捨てて新しい id を採番。
chat_messages.document_id だけ、旧→新 id 対応表で書き換える。
"""

import os, sqlite3, json
from datetime import datetime
from supabase import create_client
from postgrest.exceptions import APIError

# --- 環境変数 ---
SUPA_URL = os.getenv("SUPABASE_URL")
SUPA_KEY = os.getenv("SUPABASE_KEY")
SQLITE_PATH = "instance/wallbounce.db"

supabase = create_client(SUPA_URL, SUPA_KEY)

def iso(dt):
    """datetime -> ISO 文字列 (None 安全)"""
    if isinstance(dt, (datetime, )):
        return dt.isoformat()
    return dt

def migrate_documents(cur):
    """SQLite documents -> Supabase documents へ。旧→新 id マップを返す"""
    rows = cur.execute("SELECT * FROM documents").fetchall()
    cols = [d[0] for d in cur.description]
    id_map = {}

    for row in rows:
        data = dict(zip(cols, row))
        old_id = data.pop("id")           # 旧 id は捨てる
        data["created_at"] = iso(data["created_at"])
        data["updated_at"] = iso(data["updated_at"])

        try:
            res = supabase.table("documents").insert(data).execute()
            new_id = res.data[0]["id"]
            id_map[old_id] = new_id
        except APIError as e:
            print("documents insert error:", e)

    print(f"[documents] 移行完了: {len(id_map)} 行")
    return id_map

def migrate_chat_messages(cur, id_map):
    rows = cur.execute("SELECT * FROM chat_messages").fetchall()
    cols = [d[0] for d in cur.description]
    n_ok, n_skip = 0, 0

    for row in rows:
        data = dict(zip(cols, row))
        data.pop("id")                       # id は自動採番
        old_doc_id = data.pop("document_id")
        new_doc_id = id_map.get(old_doc_id)

        if not new_doc_id:
            n_skip += 1
            continue            # 対応するドキュメントが無ければスキップ

        data["document_id"] = new_doc_id
        data["timestamp"]    = iso(data["timestamp"])

        try:
            supabase.table("chat_messages").insert(data).execute()
            n_ok += 1
        except APIError as e:
            print("chat_messages insert error:", e)

    print(f"[chat_messages] 移行完了: OK={n_ok} / SKIP(docなし)={n_skip}")

def main():
    con = sqlite3.connect(SQLITE_PATH)
    cur = con.cursor()

    mapping = migrate_documents(cur)
    migrate_chat_messages(cur, mapping)

    cur.close()
    con.close()
    print("=== 移行処理が完了しました ===")

if __name__ == "__main__":
    main()
