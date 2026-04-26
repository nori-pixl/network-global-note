import os, uuid
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- データベース設定 ---
# RenderのEnvironmentで設定した「DATABASE_URL」を読み込みます
db_url = os.environ.get("DATABASE_URL")

# もし設定が postgres:// で始まっていたら自動で修正する（Renderの仕様対策）
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- あとはこれまでの削除機能付きコードと同じ ---
# (User, Thread, Postモデルと各APIルート)
# ...中略...

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
