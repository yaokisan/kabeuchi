from flask import Blueprint, request, jsonify, g
# Supabase 用ヘルパー関数をインポート
from app.models.database import (
    get_documents as supa_get_documents,
    get_document as supa_get_document,
    create_document as supa_create_document,
    update_document as supa_update_document,
    delete_document as supa_delete_document,
)
from app.controllers.auth_controller import require_auth

document_bp = Blueprint('document', __name__, url_prefix='/api/document')

@document_bp.route('/list', methods=['GET'])
@require_auth
def list_documents():
    """全てのドキュメントをJSON形式で返す (Supabase)"""
    try:
        print(f"[DEBUG] Starting list_documents")
        print(f"[DEBUG] User ID: {g.current_user}")
        print(f"[DEBUG] JWT Token prefix: {g.jwt_token[:20]}...")
        
        # 直接Supabaseクライアントでクエリ
        from supabase import create_client
        import os
        
        url = os.getenv('SUPABASE_URL')
        anon_key = os.getenv('SUPABASE_ANON_KEY')
        supabase = create_client(url, anon_key)
        supabase.postgrest.session.headers.update({
            'Authorization': f'Bearer {g.jwt_token}'
        })
        
        print(f"[DEBUG] Executing query...")
        response = supabase.table('documents').select('*').order('updated_at', desc=True).execute()
        print(f"[DEBUG] Query completed, found {len(response.data) if response.data else 0} documents")
        
        return jsonify(response.data or [])
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@document_bp.route('/recent', methods=['GET'])
@require_auth
def get_recent_documents():
    """最近更新された10件のドキュメントをJSON形式で返す (Supabase)"""
    recent_docs = (supa_get_documents() or [])[:10]
    return jsonify(recent_docs)

@document_bp.route('/<int:doc_id>', methods=['GET'])
@require_auth
def get_document(doc_id):
    """指定されたIDのドキュメントを取得 (Supabase)"""
    document = supa_get_document(doc_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(document)

@document_bp.route('/create', methods=['POST'])
@require_auth
def create_document():
    """新規ドキュメントを作成 (Supabase)"""
    data = request.get_json()
    title = data.get('title', '無題のドキュメント')
    content = data.get('content', '')
    
    new_doc = supa_create_document(title, content, user_id=g.current_user)
    if not new_doc:
        return jsonify({"error": "Failed to create document"}), 500
    return jsonify(new_doc), 201

@document_bp.route('/<int:doc_id>', methods=['PUT'])
@require_auth
def update_document(doc_id):
    """指定されたIDのドキュメントを更新 (Supabase)"""
    data = request.get_json()
    updated_doc = supa_update_document(doc_id, data)
    if not updated_doc:
        return jsonify({"error": "Failed to update document"}), 500
    return jsonify(updated_doc)

@document_bp.route('/<int:doc_id>/duplicate', methods=['POST'])
@require_auth
def duplicate_document(doc_id):
    """指定されたIDのドキュメントを複製 (Supabase)"""
    document = supa_get_document(doc_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404

    new_doc = supa_create_document(f"{document['title']} (コピー)", document.get('content', ''))
    if not new_doc:
        return jsonify({"error": "Failed to duplicate document"}), 500
    return jsonify(new_doc), 201

@document_bp.route('/<int:doc_id>', methods=['DELETE'])
@require_auth
def delete_document(doc_id):
    """指定されたIDのドキュメントを削除 (Supabase)"""
    # 削除結果は Supabase のレスポンスに含まれる (deleted rows)
    result = supa_delete_document(doc_id)
    if result is None:
        return jsonify({"error": "Failed to delete document"}), 500
    return jsonify({"message": "ドキュメントが削除されました", "id": doc_id})

@document_bp.route('/latest_id', methods=['GET'])
@require_auth
def get_latest_document_id():
    """最新のドキュメントIDを返す (Supabase)"""
    docs = supa_get_documents() or []
    if docs:
        return jsonify({"latest_id": docs[0]['id']})
    return jsonify({"error": "No documents found"}), 404 