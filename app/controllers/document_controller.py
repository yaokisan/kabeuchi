from flask import Blueprint, request, jsonify, render_template
from app.models.database import db, Document
from datetime import datetime

document_bp = Blueprint('document', __name__, url_prefix='/api/document')

@document_bp.route('/list', methods=['GET'])
def list_documents():
    """全てのドキュメントをJSON形式で返す"""
    documents = Document.query.order_by(Document.updated_at.desc()).all()
    return jsonify([doc.to_dict() for doc in documents])

@document_bp.route('/recent', methods=['GET'])
def get_recent_documents():
    """最近更新された10件のドキュメントをJSON形式で返す"""
    recent_docs = Document.query.order_by(Document.updated_at.desc()).limit(10).all()
    return jsonify([doc.to_dict() for doc in recent_docs])

@document_bp.route('/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    """指定されたIDのドキュメントを取得"""
    document = Document.query.get_or_404(doc_id)
    return jsonify(document.to_dict())

@document_bp.route('/create', methods=['POST'])
def create_document():
    """新規ドキュメントを作成"""
    data = request.get_json()
    title = data.get('title', '無題のドキュメント')
    content = data.get('content', '')
    
    new_doc = Document(title=title, content=content)
    db.session.add(new_doc)
    db.session.commit()
    
    return jsonify(new_doc.to_dict()), 201

@document_bp.route('/<int:doc_id>', methods=['PUT'])
def update_document(doc_id):
    """指定されたIDのドキュメントを更新"""
    document = Document.query.get_or_404(doc_id)
    data = request.get_json()
    
    if 'title' in data:
        document.title = data['title']
    if 'content' in data:
        document.content = data['content']
    
    document.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(document.to_dict())

@document_bp.route('/<int:doc_id>/duplicate', methods=['POST'])
def duplicate_document(doc_id):
    """指定されたIDのドキュメントを複製"""
    document = Document.query.get_or_404(doc_id)
    
    new_doc = Document(
        title=f"{document.title} (コピー)",
        content=document.content
    )
    
    db.session.add(new_doc)
    db.session.commit()
    
    return jsonify(new_doc.to_dict()), 201

@document_bp.route('/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """指定されたIDのドキュメントを削除"""
    document = Document.query.get_or_404(doc_id)
    db.session.delete(document)
    db.session.commit()
    
    return jsonify({"message": "ドキュメントが削除されました", "id": doc_id})

@document_bp.route('/latest_id', methods=['GET'])
def get_latest_document_id():
    """最新のドキュメントIDを返す"""
    latest_doc = Document.query.order_by(Document.updated_at.desc()).first()
    if latest_doc:
        return jsonify({"latest_id": latest_doc.id})
    else:
        # ドキュメントが存在しない場合は 404 Not Found を返す
        return jsonify({"error": "No documents found"}), 404 