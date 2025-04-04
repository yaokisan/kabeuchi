from flask import Blueprint, request, jsonify
from app.models.database import db, Document, ChatMessage
import os
import json
import sys

# APIクライアントのインポート
import openai
import google.generativeai as genai
from anthropic import Anthropic

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# APIキーの取得と設定
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# APIキーが設定されているか確認
print(f"OpenAI API Key設定状況: {'設定済み' if OPENAI_API_KEY else '未設定'}")
print(f"Google API Key設定状況: {'設定済み' if GOOGLE_API_KEY else '未設定'}")
print(f"Anthropic API Key設定状況: {'設定済み' if ANTHROPIC_API_KEY else '未設定'}")

# APIクライアントの設定
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
if ANTHROPIC_API_KEY:
    anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    anthropic_client = None

@chat_bp.route('/reset/<int:doc_id>', methods=['POST'])
def reset_chat_history(doc_id):
    """指定されたドキュメントIDに関連するチャット履歴を削除"""
    try:
        # ドキュメントが存在するか確認（任意）
        document = Document.query.get_or_404(doc_id)
        
        # 該当ドキュメントIDのチャットメッセージを全て削除
        num_deleted = ChatMessage.query.filter_by(document_id=doc_id).delete()
        db.session.commit()
        
        print(f"ドキュメントID {doc_id} のチャット履歴を {num_deleted} 件削除しました。")
        return jsonify({'success': True, 'message': 'チャット履歴がリセットされました。'}), 200
    except Exception as e:
        db.session.rollback() # エラー発生時はロールバック
        print(f"チャット履歴のリセット中にエラーが発生しました: {str(e)}", file=sys.stderr)
        return jsonify({'success': False, 'message': 'チャット履歴のリセットに失敗しました。'}), 500

@chat_bp.route('/history/<int:doc_id>', methods=['GET'])
def get_chat_history(doc_id):
    """指定されたドキュメントIDに関連するチャット履歴を取得"""
    document = Document.query.get_or_404(doc_id)
    chat_messages = ChatMessage.query.filter_by(document_id=doc_id).order_by(ChatMessage.timestamp).all()
    return jsonify([msg.to_dict() for msg in chat_messages])

@chat_bp.route('/send/<int:doc_id>', methods=['POST'])
def send_message(doc_id):
    """ユーザーメッセージを保存し、AIからの応答を取得して保存"""
    document = Document.query.get_or_404(doc_id)
    data = request.get_json()
    
    user_message = data.get('message', '')
    model_name = data.get('model', 'gemini-2.0-flash')
    thinking_enabled = data.get('thinking_enabled', False)
    chat_context = data.get('chat_context')
    
    # ユーザーメッセージをデータベースに保存
    user_chat = ChatMessage(
        document_id=doc_id,
        role='user',
        content=user_message,
        model_used=model_name,
        thinking_enabled=thinking_enabled
    )
    db.session.add(user_chat)
    db.session.commit()
    
    # ドキュメント内容とチャット履歴を取得してコンテキストを作成
    chat_history = ChatMessage.query.filter_by(document_id=doc_id).order_by(ChatMessage.timestamp).all()
    context = document.content
    
    # モデルに応じてAI応答を取得
    ai_response = ""
    
    try:
        if model_name.startswith('gemini'):
            # Googleのキーが設定されていない場合はエラー
            if not GOOGLE_API_KEY:
                raise ValueError("Google API Keyが設定されていません。.envファイルを確認してください。")
            ai_response = get_gemini_response(model_name, context, chat_history, user_message, chat_context)
        elif model_name.startswith('claude'):
            # Anthropicのキーが設定されていない場合はエラー
            if not ANTHROPIC_API_KEY:
                raise ValueError("Anthropic API Keyが設定されていません。.envファイルを確認してください。")
            ai_response = get_claude_response(model_name, context, chat_history, user_message, thinking_enabled, chat_context)
        elif model_name.startswith('gpt'):
            # OpenAIのキーが設定されていない場合はエラー
            if not OPENAI_API_KEY:
                raise ValueError("OpenAI API Keyが設定されていません。.envファイルを確認してください。")
            ai_response = get_openai_response(model_name, context, chat_history, user_message, chat_context)
        else:
            ai_response = "エラー: サポートされていないモデルが指定されました。"
    except Exception as e:
        ai_response = f"エラー: AIモデルからの応答取得に失敗しました。{str(e)}"
        print(f"AI応答エラー: {str(e)}", file=sys.stderr)
    
    # AI応答をデータベースに保存
    ai_chat = ChatMessage(
        document_id=doc_id,
        role='assistant',
        content=ai_response,
        model_used=model_name,
        thinking_enabled=thinking_enabled
    )
    db.session.add(ai_chat)
    db.session.commit()
    
    return jsonify({
        'message': ai_response,
        'model': model_name,
        'thinking_enabled': thinking_enabled
    })

def get_gemini_response(model_name, context, chat_history, user_message, chat_context):
    """Google Geminiモデルを使用して応答を生成"""
    # チャット履歴の作成
    chat_history_formatted = []
    for msg in chat_history:  # すべてのメッセージを使用（制限なし）
        if msg.role == 'user':
            chat_history_formatted.append({"role": "user", "parts": [msg.content]})
        else:
            chat_history_formatted.append({"role": "model", "parts": [msg.content]})
    
    model = genai.GenerativeModel(model_name)
    
    # システムプロンプトの組み立て
    system_prompt_base = f"""あなたはユーザーのアシスタントとして、ユーザーがチャットで入力した内容に応じて適切な内容を出力します。

このチャットでは、あなたとユーザーの過去の会話履歴が自動的に提供されます。過去の会話のコンテキストを考慮して返答してください。ユーザーが過去の会話内容に言及した場合は、その履歴を参照して適切に応答してください。

また、以下のドキュメントはユーザーが現在作成している内容で、この内容についての会話がこのチャットでは実施されます。
--- ドキュメントここから ---
{context}
--- ドキュメントここまで ---
"""
    
    # 選択テキスト -> チャットコンテキスト がある場合の追加指示
    if chat_context:
        system_prompt = system_prompt_base + f"""\n\n重要: ユーザーは以下のテキストを現在の会話の最重要コンテキストとして指定しました。ユーザーの指示が曖昧な場合（例：「これについて教えて」）、直前の会話履歴よりもまず、この追加コンテキストについて言及・回答することを最優先してください。
--- 追加コンテキストここから ---
{chat_context}
--- 追加コンテキストここまで ---
"""
    else:
        system_prompt = system_prompt_base

    # チャットセッションの作成とレスポンスの取得
    # Geminiではシステムプロンプトを最初のユーザーメッセージに含めることが多い
    # 履歴が空の場合、または最初のメッセージがシステムプロンプトでない場合に挿入
    if not chat_history_formatted or chat_history_formatted[0].get('role') != 'user' or not chat_history_formatted[0].get('parts',[''])[0].startswith('あなたは'):
         # 既存の履歴の前にシステムプロンプトをユーザーメッセージとして追加
         # 厳密には履歴の扱い方によりますが、ここでは会話の最初にシステム指示を置く想定
         chat_history_formatted.insert(0, {"role": "user", "parts": [system_prompt]})
         # 応答を期待しないため、空のモデル応答を追加
         chat_history_formatted.insert(1, {"role": "model", "parts": ["承知しました。"]})

    chat = model.start_chat(history=chat_history_formatted)
    response = chat.send_message(user_message)
    
    return response.text

def get_claude_response(model_name, context, chat_history, user_message, thinking_enabled, chat_context):
    """Anthropic Claudeモデルを使用して応答を生成"""
    messages = []
    
    # システムプロンプトの組み立て
    system_prompt_base = f"""あなたはユーザーのアシスタントとして、ユーザーがチャットで入力した内容に応じて適切な内容を出力します。

このチャットでは、あなたとユーザーの過去の会話履歴が自動的に提供されます。過去の会話のコンテキストを考慮して返答してください。ユーザーが過去の会話内容に言及した場合は、その履歴を参照して適切に応答してください。

また、以下のドキュメントはユーザーが現在作成している内容で、この内容についての会話がこのチャットでは実施されます。
--- ドキュメントここから ---
{context}
--- ドキュメントここまで ---
"""
    
    # 選択テキスト -> チャットコンテキスト がある場合の追加指示
    if chat_context:
        system_prompt = system_prompt_base + f"""\n\n重要: ユーザーは以下のテキストを現在の会話の最重要コンテキストとして指定しました。ユーザーの指示が曖昧な場合（例：「これについて教えて」）、直前の会話履歴よりもまず、この追加コンテキストについて言及・回答することを最優先してください。
--- 追加コンテキストここから ---
{chat_context}
--- 追加コンテキストここまで ---
"""
    else:
        system_prompt = system_prompt_base
    
    # Claude API v2 (messages) では system パラメータを使用
    # messagesリストにはシステムプロンプトを含めない

    # すべての会話履歴を追加
    for msg in chat_history:  # すべてのメッセージを使用（制限なし）
        messages.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # 新しいユーザーメッセージを追加
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    # Claudeモデルでレスポンスを生成
    response = anthropic_client.messages.create(
        model=model_name,
        messages=messages,
        system=system_prompt, # systemパラメータにプロンプトを渡す
        # thinking_enabled はClaudeのAPIには直接対応するパラメータがないため、
        # プロンプト内で指示するか、フロントエンド側で制御する
    )
    
    return response.content[0].text

def get_openai_response(model_name, context, chat_history, user_message, chat_context):
    """OpenAI GPTモデルを使用して応答を生成"""
    messages = []
    
    # システムプロンプトの組み立て
    system_prompt_base = f"""あなたはユーザーのアシスタントとして、ユーザーがチャットで入力した内容に応じて適切な内容を出力します。

このチャットでは、あなたとユーザーの過去の会話履歴が自動的に提供されます。過去の会話のコンテキストを考慮して返答してください。ユーザーが過去の会話内容に言及した場合は、その履歴を参照して適切に応答してください。

また、以下のドキュメントはユーザーが現在作成している内容で、この内容についての会話がこのチャットでは実施されます。
--- ドキュメントここから ---
{context}
--- ドキュメントここまで ---
"""
    
    # 選択テキスト -> チャットコンテキスト がある場合の追加指示
    if chat_context:
        system_prompt = system_prompt_base + f"""\n\n重要: ユーザーは以下のテキストを現在の会話の最重要コンテキストとして指定しました。ユーザーの指示が曖昧な場合（例：「これについて教えて」）、直前の会話履歴よりもまず、この追加コンテキストについて言及・回答することを最優先してください。
--- 追加コンテキストここから ---
{chat_context}
--- 追加コンテキストここまで ---
"""
    else:
        system_prompt = system_prompt_base
    
    messages.append({
        "role": "system",
        "content": system_prompt
    })
    
    # すべての会話履歴を追加
    for msg in chat_history:  # すべてのメッセージを使用（制限なし）
        messages.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # 新しいユーザーメッセージを追加
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    # GPTモデルでレスポンスを生成
    response = openai.ChatCompletion.create(
        model=model_name,
        messages=messages
    )
    
    return response.choices[0].message.content 