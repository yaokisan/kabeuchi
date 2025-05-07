import importlib.util
import pathlib

# プロジェクトルートの app.py へのパスを取得
module_path = pathlib.Path(__file__).resolve().parent.parent / "app.py"

spec = importlib.util.spec_from_file_location("flask_app_module", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Vercel が検出する WSGI アプリとして公開
app = module.app

# Vercel Python Runtime は `api/` 配下の .py で `app` 変数を探し、WSGI アプリとして実行する。
# そのため import だけで十分。特別なハンドラ関数は不要。
# ここでの `app` は root の app.py で定義済み。 