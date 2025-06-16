"""
非同期AIチャット処理
Server-Sent EventsとWeb Workersによるストリーミング対応
"""

from flask import Blueprint, request, Response, stream_with_context, jsonify, g
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import logging
from app.models.database import (
    get_document as supa_get_document,
    get_chat_messages as supa_get_chat_messages,
    create_chat_message as supa_create_chat_message,
    delete_chat_messages as supa_delete_chat_messages,
)

# 非同期処理用のAPIクライアント
import openai
import google.generativeai as genai
from anthropic import Anthropic
from duckduckgo_search import DDGS
from google.generativeai.types import GenerationConfig, FunctionDeclaration, Tool
import os
import base64
from urllib.parse import urlparse
from io import BytesIO

# 設定
chat_async_bp = Blueprint('chat_async', __name__, url_prefix='/api/chat/async')

# パフォーマンス最適化設定
MAX_DOCUMENT_CHARS = 8000  # ドキュメント最大文字数を削減
MAX_CHAT_HISTORY = 15      # チャット履歴を削減
STREAM_CHUNK_SIZE = 50     # ストリーミングチャンクサイズ
REQUEST_TIMEOUT = 45       # API リクエストタイムアウト（秒）

# APIキーの取得
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') 
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# APIクライアントの設定
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
if ANTHROPIC_API_KEY:
    anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    anthropic_client = None

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# スレッドプール
executor = ThreadPoolExecutor(max_workers=4)

class ChatContextOptimizer:
    """チャットコンテキストの最適化"""
    
    @staticmethod
    def optimize_document_content(content, max_chars=MAX_DOCUMENT_CHARS):
        """ドキュメント内容を最適化"""
        if len(content) <= max_chars:
            return content
        
        # 段落単位で切り詰め
        paragraphs = content.split('\n\n')
        optimized = ""
        for paragraph in paragraphs:
            if len(optimized + paragraph) <= max_chars:
                optimized += paragraph + '\n\n'
            else:
                break
        
        return optimized.strip() + "... [内容が省略されました]"
    
    @staticmethod
    def optimize_chat_history(messages, max_messages=MAX_CHAT_HISTORY):
        """チャット履歴を最適化"""
        if len(messages) <= max_messages:
            return messages
        
        # 最新のmax_messages件を保持
        return messages[-max_messages:]
    
    @staticmethod
    def calculate_token_estimate(text):
        """トークン数の概算"""
        # 日本語: 約1文字 = 1.5トークン、英語: 約4文字 = 1トークン
        japanese_chars = sum(1 for char in text if ord(char) > 127)
        english_chars = len(text) - japanese_chars
        return int(japanese_chars * 1.5 + english_chars * 0.25)

class AsyncAIClient:
    """非同期AI API クライアント"""
    
    def __init__(self):
        self.optimizer = ChatContextOptimizer()
    
    def generate_stream_openai_sync(self, messages, model="gpt-4o-mini"):
        """OpenAI ストリーミング生成"""
        def _call_openai():
            try:
                client = openai.OpenAI(api_key=OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    max_tokens=2000,
                    temperature=0.7
                )
                
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                yield f"[エラー: {str(e)}]"
        
        return _call_openai()
    
    def generate_stream_gemini_sync(self, prompt, search_enabled=False):
        """Gemini ストリーミング生成"""
        def _call_gemini():
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Web検索機能は必要時のみ有効化
                if search_enabled:
                    # 簡略化されたWeb検索実装
                    search_tool = Tool([
                        FunctionDeclaration(
                            name="web_search",
                            description="現在の情報を検索",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"}
                                }
                            }
                        )
                    ])
                    model = genai.GenerativeModel('gemini-1.5-flash', tools=[search_tool])
                
                generation_config = GenerationConfig(
                    max_output_tokens=2000,
                    temperature=0.7,
                    candidate_count=1,
                )
                
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    stream=True
                )
                
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                        
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                yield f"[エラー: {str(e)}]"
        
        return _call_gemini()
    
    def generate_stream_claude_sync(self, messages):
        """Claude ストリーミング生成"""
        def _call_claude():
            try:
                if not anthropic_client:
                    yield "[Claude APIキーが設定されていません]"
                    return
                
                response = anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",  # 高速モデルを使用
                    max_tokens=2000,
                    messages=messages,
                    stream=True,
                    timeout=REQUEST_TIMEOUT
                )
                
                for chunk in response:
                    if chunk.type == 'content_block_delta':
                        yield chunk.delta.text
                        
            except Exception as e:
                logger.error(f"Claude API error: {e}")
                yield f"[エラー: {str(e)}]"
        
        return _call_claude()

# グローバルクライアント
ai_client = AsyncAIClient()

@chat_async_bp.route('/stream/<int:doc_id>', methods=['GET', 'POST'])
def stream_chat_response(doc_id):
    """ストリーミングチャット応答"""
    
    def generate_response():
        try:
            # リクエストデータ取得
            if request.method == 'POST':
                data = request.get_json() or {}
            else:
                data = request.args.to_dict()
                
            user_message = data.get('message', '').strip()
            ai_model = data.get('aiModel', 'openai')
            image_data = data.get('image')
            search_enabled = data.get('searchEnabled', False)
            
            # 初期状態を送信
            yield f"data: {json.dumps({'type': 'status', 'message': '処理を開始しています...'})}\n\n"
            
            # ドキュメント取得（最適化済み）
            document = supa_get_document(doc_id)
            if not document:
                yield f"data: {json.dumps({'type': 'error', 'message': 'ドキュメントが見つかりません'})}\n\n"
                return
            
            # ドキュメント内容を最適化
            optimized_content = ai_client.optimizer.optimize_document_content(
                document.get('content', '')
            )
            
            # チャット履歴取得（最適化済み）
            chat_history = supa_get_chat_messages(doc_id)
            optimized_history = ai_client.optimizer.optimize_chat_history(chat_history)
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'AI応答を生成中...'})}\n\n"
            
            # ユーザーメッセージを保存
            supa_create_chat_message(doc_id, 'user', user_message)
            yield f"data: {json.dumps({'type': 'user_message', 'content': user_message})}\n\n"
            
            # AI応答生成
            if ai_model == 'openai':
                messages = build_openai_messages(optimized_content, optimized_history, user_message)
                chunks = ai_client.generate_stream_openai_sync(messages)
            elif ai_model == 'gemini':
                prompt = build_gemini_prompt(optimized_content, optimized_history, user_message)
                chunks = ai_client.generate_stream_gemini_sync(prompt, search_enabled)
            elif ai_model == 'claude':
                messages = build_claude_messages(optimized_content, optimized_history, user_message)
                chunks = ai_client.generate_stream_claude_sync(messages)
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': 'サポートされていないAIモデルです'})}\n\n"
                return
            
            # ストリーミング送信
            full_response = ""
            for chunk in chunks:
                if chunk:
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    time.sleep(0.01)  # 少し遅延を入れて安定化
            
            # 応答を保存
            if full_response:
                supa_create_chat_message(doc_id, 'assistant', full_response)
            
            # 完了通知
            yield f"data: {json.dumps({'type': 'complete', 'message': '応答完了'})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'エラーが発生しました: {str(e)}'})}\n\n"
    
    return Response(
        stream_with_context(generate_response()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    )

def build_openai_messages(document_content, chat_history, user_message):
    """OpenAI用メッセージ構築"""
    messages = [
        {
            "role": "system",
            "content": f"""あなたは壁打ちチャットAIです。以下のドキュメントの内容について質問に答えてください。

ドキュメント内容:
{document_content}

回答時の注意:
- 簡潔で分かりやすく答える
- ドキュメント内容に基づいて回答する  
- 不明な場合は素直に「分からない」と答える"""
        }
    ]
    
    # チャット履歴を追加
    for msg in chat_history:
        messages.append({
            "role": msg['role'],
            "content": msg['content']
        })
    
    # 現在のメッセージを追加
    messages.append({
        "role": "user", 
        "content": user_message
    })
    
    return messages

def build_gemini_prompt(document_content, chat_history, user_message):
    """Gemini用プロンプト構築"""
    prompt = f"""あなたは壁打ちチャットAIです。以下のドキュメントについて質問に答えてください。

ドキュメント:
{document_content}

チャット履歴:
"""
    
    for msg in chat_history:
        role_label = "ユーザー" if msg['role'] == 'user' else "AI"
        prompt += f"{role_label}: {msg['content']}\n"
    
    prompt += f"\nユーザー: {user_message}\nAI: "
    
    return prompt

def build_claude_messages(document_content, chat_history, user_message):
    """Claude用メッセージ構築"""
    messages = []
    
    # システムメッセージはseparateパラメータで指定
    system_message = f"""あなたは壁打ちチャットAIです。以下のドキュメントについて質問に答えてください。

ドキュメント:
{document_content}

簡潔で分かりやすく答えてください。"""
    
    # チャット履歴を追加
    for msg in chat_history:
        messages.append({
            "role": msg['role'],
            "content": msg['content']
        })
    
    # 現在のメッセージを追加
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    return messages

@chat_async_bp.route('/status', methods=['GET'])
def get_status():
    """サービス状態確認"""
    return jsonify({
        'status': 'active',
        'models': {
            'openai': bool(OPENAI_API_KEY),
            'gemini': bool(GOOGLE_API_KEY),
            'claude': bool(ANTHROPIC_API_KEY)
        },
        'config': {
            'max_document_chars': MAX_DOCUMENT_CHARS,
            'max_chat_history': MAX_CHAT_HISTORY,
            'stream_chunk_size': STREAM_CHUNK_SIZE
        }
    })