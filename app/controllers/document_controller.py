from flask import Blueprint, request, jsonify
# Supabase 用ヘルパー関数をインポート
from app.models.database import (
    get_documents as supa_get_documents,
    get_document as supa_get_document,
    create_document as supa_create_document,
    update_document as supa_update_document,
    delete_document as supa_delete_document,
)

document_bp = Blueprint('document', __name__, url_prefix='/api/document')

@document_bp.route('/list', methods=['GET'])
def list_documents():
    """全てのドキュメントをJSON形式で返す (Supabase)"""
    documents = supa_get_documents() or []
    return jsonify(documents)

@document_bp.route('/recent', methods=['GET'])
def get_recent_documents():
    """最近更新された10件のドキュメントをJSON形式で返す (Supabase)"""
    recent_docs = (supa_get_documents() or [])[:10]
    return jsonify(recent_docs)

@document_bp.route('/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    """指定されたIDのドキュメントを取得 (Supabase)"""
    document = supa_get_document(doc_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(document)

@document_bp.route('/create', methods=['POST'])
def create_document():
    """新規ドキュメントを作成 (Supabase)"""
    data = request.get_json()
    title = data.get('title', '無題のドキュメント')
    content = data.get('content', '')
    
    new_doc = supa_create_document(title, content)
    if not new_doc:
        return jsonify({"error": "Failed to create document"}), 500
    return jsonify(new_doc), 201

@document_bp.route('/<int:doc_id>', methods=['PUT'])
def update_document(doc_id):
    """指定されたIDのドキュメントを更新 (Supabase)"""
    data = request.get_json()
    updated_doc = supa_update_document(doc_id, data)
    if not updated_doc:
        return jsonify({"error": "Failed to update document"}), 500
    return jsonify(updated_doc)

@document_bp.route('/<int:doc_id>/duplicate', methods=['POST'])
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
def delete_document(doc_id):
    """指定されたIDのドキュメントを削除 (Supabase)"""
    # 削除結果は Supabase のレスポンスに含まれる (deleted rows)
    result = supa_delete_document(doc_id)
    if result is None:
        return jsonify({"error": "Failed to delete document"}), 500
    return jsonify({"message": "ドキュメントが削除されました", "id": doc_id})

@document_bp.route('/latest_id', methods=['GET'])
def get_latest_document_id():
    """最新のドキュメントIDを返す (Supabase)"""
    docs = supa_get_documents() or []
    if docs:
        return jsonify({"latest_id": docs[0]['id']})
    return jsonify({"error": "No documents found"}), 404 