from flask import Blueprint, request, jsonify, current_app
import os
from dotenv import set_key, find_dotenv

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

@settings_bp.route('/keys', methods=['GET'])
def get_api_keys_status():
    """APIキーの設定状況（キー名のみ）を取得"""
    keys_status = {
        'openai_key_set': bool(os.getenv('OPENAI_API_KEY')),
        'google_key_set': bool(os.getenv('GOOGLE_API_KEY')),
        'anthropic_key_set': bool(os.getenv('ANTHROPIC_API_KEY')),
    }
    return jsonify(keys_status)

@settings_bp.route('/keys', methods=['POST'])
def save_api_keys():
    """APIキーを.envファイルに保存"""
    data = request.get_json()
    openai_key = data.get('openai_key')
    google_key = data.get('google_key')
    anthropic_key = data.get('anthropic_key')
    
    dotenv_path = find_dotenv()
    if not dotenv_path:
        # .envファイルが存在しない場合、新規作成を試みる
        try:
            with open(".env", "w") as f:
                f.write("\n") # 空ファイルを作成
            dotenv_path = find_dotenv()
            if not dotenv_path:
                raise FileNotFoundError(".envファイルが見つからず、作成もできませんでした。")
        except Exception as e:
             return jsonify({"error": f".envファイルの処理中にエラー: {str(e)}"}), 500

    try:
        if openai_key:
            set_key(dotenv_path, 'OPENAI_API_KEY', openai_key)
            current_app.logger.info("OpenAI API Keyを.envに保存しました")
        if google_key:
            set_key(dotenv_path, 'GOOGLE_API_KEY', google_key)
            current_app.logger.info("Google API Keyを.envに保存しました")
        if anthropic_key:
            set_key(dotenv_path, 'ANTHROPIC_API_KEY', anthropic_key)
            current_app.logger.info("Anthropic API Keyを.envに保存しました")
        
        return jsonify({"message": "APIキーが正常に保存されました。"})
    except Exception as e:
        current_app.logger.error(f"APIキーの保存中にエラー: {str(e)}")
        return jsonify({"error": f"APIキーの保存に失敗しました: {str(e)}"}), 500 