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
    
    # --------- ファイルへの書き込みを試みる ---------
    try:
        dotenv_path = find_dotenv()
        if not dotenv_path:
            # .env が無ければ作成を試みる
            with open(".env", "w") as f:
                f.write("\n")
            dotenv_path = find_dotenv()

        if openai_key:
            set_key(dotenv_path, 'OPENAI_API_KEY', openai_key)
            current_app.logger.info("OpenAI API Keyを.envに保存しました")
        if google_key:
            set_key(dotenv_path, 'GOOGLE_API_KEY', google_key)
            current_app.logger.info("Google API Keyを.envに保存しました")
        if anthropic_key:
            set_key(dotenv_path, 'ANTHROPIC_API_KEY', anthropic_key)
            current_app.logger.info("Anthropic API Keyを.envに保存しました")

        return jsonify({"message": "APIキーを .env に保存しました（ローカル環境）"})

    # --------- 読み取り専用ファイルシステムなどで失敗した場合 ---------
    except OSError as e:
        if e.errno == 30:  # Read-only file system
            # ランタイム環境変数として設定だけ行う
            if openai_key:
                os.environ['OPENAI_API_KEY'] = openai_key
            if google_key:
                os.environ['GOOGLE_API_KEY'] = google_key
            if anthropic_key:
                os.environ['ANTHROPIC_API_KEY'] = anthropic_key

            current_app.logger.warning("読み取り専用ファイルシステムのため .env には書き込めませんでした。環境変数にのみ設定しました。")
            return jsonify({
                "message": "読み取り専用環境のため .env には保存できませんでしたが、ランタイム環境変数としては設定しました。ホスティング環境のダッシュボードで永久保存してください。"
            }), 200

        # その他の OS エラーはそのままハンドリング
        current_app.logger.error(f"APIキーの保存中に OSError: {str(e)}")
        return jsonify({"error": f"APIキーの保存に失敗しました: {str(e)}"}), 500

    except Exception as e:
        current_app.logger.error(f"APIキーの保存中にエラー: {str(e)}")
        return jsonify({"error": f"APIキーの保存に失敗しました: {str(e)}"}), 500 