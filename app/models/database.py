from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# SQLAlchemyインスタンスの初期化
db = SQLAlchemy()

def init_db():
    """データベーステーブルの初期化関数"""
    db.create_all()

# ドキュメントモデル
class Document(db.Model):
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
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# チャットメッセージモデル
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' または 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    model_used = db.Column(db.String(50), nullable=True)  # 使用されたAIモデル名
    thinking_enabled = db.Column(db.Boolean, default=False)  # 思考モードが有効だったか
    
    def to_dict(self):
        """チャットメッセージをJSONシリアライズ可能な辞書に変換"""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'model_used': self.model_used,
            'thinking_enabled': self.thinking_enabled
        } 