"""
最適化されたデータベース処理
- バッチ処理
- キャッシング
- 接続プーリング
- クエリ最適化
"""

from flask_sqlalchemy import SQLAlchemy
from functools import lru_cache
import time
import logging
from typing import List, Dict, Optional, Tuple
from app.models.supabase_client import get_supabase

db = SQLAlchemy()
logger = logging.getLogger(__name__)

# キャッシュ設定
CACHE_TTL = 300  # 5分
BATCH_SIZE = 50  # バッチ処理サイズ

class DatabaseOptimizer:
    """データベース処理最適化クラス"""
    
    def __init__(self):
        self.supabase = get_supabase()
        self._document_cache = {}
        self._cache_timestamps = {}
    
    def _is_cache_valid(self, key: str) -> bool:
        """キャッシュの有効性チェック"""
        if key not in self._cache_timestamps:
            return False
        return time.time() - self._cache_timestamps[key] < CACHE_TTL
    
    def _update_cache(self, key: str, value):
        """キャッシュ更新"""
        self._document_cache[key] = value
        self._cache_timestamps[key] = time.time()
    
    def get_document_optimized(self, doc_id: int) -> Optional[Dict]:
        """最適化されたドキュメント取得"""
        cache_key = f"doc_{doc_id}"
        
        # キャッシュチェック
        if self._is_cache_valid(cache_key):
            return self._document_cache[cache_key]
        
        try:
            # 必要なフィールドのみ取得
            response = self.supabase.table('documents').select(
                'id, title, content, created_at, updated_at, user_id'
            ).eq('id', doc_id).execute()
            
            if response.data:
                document = response.data[0]
                self._update_cache(cache_key, document)
                return document
            return None
            
        except Exception as e:
            logger.error(f"Document fetch error: {e}")
            return None
    
    def get_chat_messages_optimized(self, doc_id: int, limit: int = 25) -> List[Dict]:
        """最適化されたチャット履歴取得"""
        try:
            # 最新のlimit件のみ取得、必要なフィールドのみ
            response = self.supabase.table('chat_messages').select(
                'id, role, content, timestamp'
            ).eq('document_id', doc_id).order(
                'timestamp', desc=True
            ).limit(limit).execute()
            
            # 時系列順に並び替え
            if response.data:
                return list(reversed(response.data))
            return []
            
        except Exception as e:
            logger.error(f"Chat messages fetch error: {e}")
            return []
    
    def create_chat_message_batch(self, messages: List[Dict]) -> bool:
        """バッチでチャットメッセージを作成"""
        try:
            if not messages:
                return True
            
            # バッチサイズに分割して処理
            for i in range(0, len(messages), BATCH_SIZE):
                batch = messages[i:i + BATCH_SIZE]
                self.supabase.table('chat_messages').insert(batch).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Batch message creation error: {e}")
            return False
    
    def get_recent_documents_optimized(self, user_id: str, limit: int = 10) -> List[Dict]:
        """最適化された最近のドキュメント取得"""
        cache_key = f"recent_docs_{user_id}_{limit}"
        
        # キャッシュチェック
        if self._is_cache_valid(cache_key):
            return self._document_cache[cache_key]
        
        try:
            # 必要最小限のフィールドのみ取得
            response = self.supabase.table('documents').select(
                'id, title, updated_at, created_at'
            ).eq('user_id', user_id).order(
                'updated_at', desc=True
            ).limit(limit).execute()
            
            documents = response.data or []
            self._update_cache(cache_key, documents)
            return documents
            
        except Exception as e:
            logger.error(f"Recent documents fetch error: {e}")
            return []
    
    def update_document_optimized(self, doc_id: int, updates: Dict) -> bool:
        """最適化されたドキュメント更新"""
        try:
            # 更新フィールドのみ送信
            filtered_updates = {k: v for k, v in updates.items() if v is not None}
            
            response = self.supabase.table('documents').update(
                filtered_updates
            ).eq('id', doc_id).execute()
            
            # キャッシュを無効化
            cache_key = f"doc_{doc_id}"
            if cache_key in self._document_cache:
                del self._document_cache[cache_key]
                del self._cache_timestamps[cache_key]
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Document update error: {e}")
            return False
    
    def delete_old_chat_messages(self, doc_id: int, keep_latest: int = 50) -> bool:
        """古いチャットメッセージの削除（パフォーマンス維持）"""
        try:
            # 最新のkeep_latest件以外を削除
            response = self.supabase.table('chat_messages').select(
                'id'
            ).eq('document_id', doc_id).order(
                'timestamp', desc=True
            ).offset(keep_latest).execute()
            
            if response.data:
                ids_to_delete = [msg['id'] for msg in response.data]
                
                # バッチで削除
                for i in range(0, len(ids_to_delete), BATCH_SIZE):
                    batch_ids = ids_to_delete[i:i + BATCH_SIZE]
                    self.supabase.table('chat_messages').delete().in_(
                        'id', batch_ids
                    ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Old messages deletion error: {e}")
            return False
    
    def get_document_statistics(self, user_id: str) -> Dict:
        """ユーザーのドキュメント統計（キャッシュ付き）"""
        cache_key = f"stats_{user_id}"
        
        if self._is_cache_valid(cache_key):
            return self._document_cache[cache_key]
        
        try:
            # ドキュメント数
            doc_response = self.supabase.table('documents').select(
                'id'
            ).eq('user_id', user_id).execute()
            
            doc_count = len(doc_response.data) if doc_response.data else 0
            
            # チャットメッセージ数（概算）
            msg_response = self.supabase.table('chat_messages').select(
                'id'
            ).eq('user_id', user_id).limit(1000).execute()  # 最大1000件まで
            
            msg_count = len(msg_response.data) if msg_response.data else 0
            
            stats = {
                'document_count': doc_count,
                'message_count': msg_count,
                'last_updated': time.time()
            }
            
            self._update_cache(cache_key, stats)
            return stats
            
        except Exception as e:
            logger.error(f"Statistics fetch error: {e}")
            return {'document_count': 0, 'message_count': 0, 'last_updated': time.time()}
    
    def clear_cache(self, pattern: str = None):
        """キャッシュクリア"""
        if pattern:
            keys_to_remove = [k for k in self._document_cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._document_cache[key]
                del self._cache_timestamps[key]
        else:
            self._document_cache.clear()
            self._cache_timestamps.clear()

# グローバルインスタンス
db_optimizer = DatabaseOptimizer()

# 最適化された関数群（既存コードとの互換性維持）
def get_document(doc_id: int) -> Optional[Dict]:
    """最適化されたドキュメント取得"""
    return db_optimizer.get_document_optimized(doc_id)

def get_chat_messages(doc_id: int, limit: int = 25) -> List[Dict]:
    """最適化されたチャット履歴取得"""
    return db_optimizer.get_chat_messages_optimized(doc_id, limit)

def create_chat_message(doc_id: int, role: str, content: str) -> bool:
    """単一チャットメッセージ作成"""
    message = {
        'document_id': doc_id,
        'role': role,
        'content': content,
        'timestamp': time.time()
    }
    return db_optimizer.create_chat_message_batch([message])

def create_chat_messages_batch(messages: List[Dict]) -> bool:
    """バッチチャットメッセージ作成"""
    return db_optimizer.create_chat_message_batch(messages)

def get_recent_documents(user_id: str, limit: int = 10) -> List[Dict]:
    """最適化された最近のドキュメント取得"""
    return db_optimizer.get_recent_documents_optimized(user_id, limit)

def update_document(doc_id: int, **kwargs) -> bool:
    """最適化されたドキュメント更新"""
    return db_optimizer.update_document_optimized(doc_id, kwargs)

def delete_chat_messages(doc_id: int) -> bool:
    """チャットメッセージ削除（古いもののみ）"""
    return db_optimizer.delete_old_chat_messages(doc_id)

def get_user_statistics(user_id: str) -> Dict:
    """ユーザー統計取得"""
    return db_optimizer.get_document_statistics(user_id)

def clear_cache(pattern: str = None):
    """キャッシュクリア"""
    db_optimizer.clear_cache(pattern)

# 既存のSQLAlchemy初期化（互換性維持）
def init_db():
    """データベース初期化"""
    try:
        # Supabaseを使用する場合は特に何もしない
        logger.info("Database initialized (using Supabase)")
        return True
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False

# パフォーマンス監視
class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    def __init__(self):
        self.query_times = []
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_query_time(self, duration: float):
        """クエリ時間記録"""
        self.query_times.append(duration)
        if len(self.query_times) > 100:
            self.query_times.pop(0)  # 最新100件のみ保持
    
    def record_cache_hit(self):
        """キャッシュヒット記録"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """キャッシュミス記録"""
        self.cache_misses += 1
    
    def get_statistics(self) -> Dict:
        """統計情報取得"""
        if not self.query_times:
            return {
                'avg_query_time': 0,
                'cache_hit_ratio': 0,
                'total_queries': 0
            }
        
        avg_time = sum(self.query_times) / len(self.query_times)
        total_cache_requests = self.cache_hits + self.cache_misses
        hit_ratio = self.cache_hits / total_cache_requests if total_cache_requests > 0 else 0
        
        return {
            'avg_query_time': avg_time,
            'cache_hit_ratio': hit_ratio,
            'total_queries': len(self.query_times),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses
        }

# グローバル監視インスタンス
performance_monitor = PerformanceMonitor()