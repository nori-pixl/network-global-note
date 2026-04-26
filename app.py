import os, uuid
from flask import Flask, render_template, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# 余計な変数を使わず、直接URLを1行で書く
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://user:QMe5ISzWDVoOpTMnKLzLb43mbRqM8hWU@://render.com"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# モデル・ルートは「削除機能・自動更新付き」の以前のものを使用
# (※中身はこれまでの完成版と同じものを貼り付けてください)
