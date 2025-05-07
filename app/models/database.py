from flask_sqlalchemy import SQLAlchemy  
from datetime import datetime  
import json  
from app.models.supabase_client import get_supabase  
  
# SQLAlchemyインスタンスの初期化（互換性のため維持）  
db = SQLAlchemy()  
  
def init_db():  
    """データベーステーブルの初期化関数"""  
    db.create_all()  
  
# Supabaseの機能を使用するヘルパー関数  
def get_documents():  
    supabase = get_supabase()  
    response = supabase.table('documents').select('*').order('updated_at', desc=True).execute()  
    return response.data  
  
def get_document(doc_id):
    """ID で 1 件取得。存在しなければ None を返す。"""
    supabase = get_supabase()
    response = supabase.table('documents').select('*').eq('id', doc_id).execute()
    if getattr(response, 'error', None):
        # エラー内容をログなどで参照したい場合は呼び出し側で response.error を参照
        return None
    data = response.data or []
    return data[0] if data else None
  
def create_document(title, content):  
    supabase = get_supabase()  
    response = supabase.table('documents').insert({  
        'title': title,  
        'content': content  
    }).execute()  
    return response.data[0]  
  
def update_document(doc_id, data):  
    supabase = get_supabase()  
    response = supabase.table('documents').update(data).eq('id', doc_id).execute()  
    return response.data[0]  
  
def delete_document(doc_id):  
    supabase = get_supabase()  
    response = supabase.table('documents').delete().eq('id', doc_id).execute()  
    return response.data  
  
def get_chat_messages(doc_id):
    """指定ドキュメントのチャット履歴（昇順）。存在しなくても空配列を返す。"""
    supabase = get_supabase()
    response = supabase.table('chat_messages').select('*').eq('document_id', doc_id).order('timestamp').execute()
    if getattr(response, 'error', None):
        return []
    return response.data or []
  
def create_chat_message(document_id, role, content, model_used=None, thinking_enabled=False):  
    supabase = get_supabase()  
    response = supabase.table('chat_messages').insert({  
        'document_id': document_id,  
        'role': role,  
        'content': content,  
        'model_used': model_used,  
        'thinking_enabled': thinking_enabled  
    }).execute()  
    return response.data[0]  
  
# 指定ドキュメントIDのチャットメッセージを全削除
def delete_chat_messages(document_id):
    """指定ドキュメントIDに紐づくチャットメッセージを削除して削除件数を返す"""
    supabase = get_supabase()
    response = supabase.table('chat_messages').delete().eq('document_id', document_id).execute()
    # Supabase からは削除した行データが返るので、その件数を返す
    return len(response.data or [])
  
# 以下は互換性のためにSQLAlchemyモデルを維持  
# ドキュメントモデル  
class Document(db.Model):  
    # 既存のモデル定義を維持  
    __tablename__ = 'documents'  
      
    id = db.Column(db.Integer, primary_key=True)  
    title = db.Column(db.String(100), nullable=False, default='無題のドキュメント')  
    content = db.Column(db.Text, nullable=False, default='')  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  
      
    # ドキュメントに関連するチャットメッセージへの関係定義  
    chat_messages = db.relationship('ChatMessage', backref='document', lazy=True, cascade='all, delete-orphan')  
      
    def to_dict(self):  
        """ドキュメントをJSONシリアライズ可能な辞書に変換"""  
        return {  
            'id': self.id,  
            'title': self.title,  
            'content': self.content,  
            'created_at': self.created_at.isoformat() if self.created_at else None,  
            'updated_at': self.updated_at.isoformat() if self.updated_at else None  
        }  
  
# チャットメッセージモデル  
class ChatMessage(db.Model):  
    # 既存のモデル定義を維持  
    __tablename__ = 'chat_messages'  
      
    id = db.Column(db.Integer, primary_key=True)  
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)  
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'assistant'  
    content = db.Column(db.Text, nullable=False)  
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  
    model_used = db.Column(db.String(100))  # 使用されたAIモデル名  
    thinking_enabled = db.Column(db.Boolean, default=False)  # Claudeの思考モードなど  
      
    def to_dict(self):  
        """チャットメッセージをJSONシリアライズ可能な辞書に変換"""  
        return {  
            'id': self.id,  
            'document_id': self.document_id,  
            'role': self.role,  
            'content': self.content,  
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,  
            'model_used': self.model_used,  
            'thinking_enabled': self.thinking_enabled,  
        }