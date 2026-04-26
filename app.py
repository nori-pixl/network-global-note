import os, uuid
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- データベース接続設定 (エラーを物理的に回避する書き方) ---
raw_url = "postgresql://user:QMe5ISzWDVoOpTMnKLzLb43mbRqM8hWU@://render.com"

# ポート番号が抜けている場合に備え、明示的に :5432 を挿入し、SSL設定を付加
if ".render.com" in raw_url and ":5432" not in raw_url:
    database_url = raw_url.replace(".render.com", ".render.com:5432", 1) + "?sslmode=require"
else:
    database_url = raw_url + "?sslmode=require"

# postgres:// を postgresql:// に統一
app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- モデル定義 ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(255))
    group_id = db.Column(db.String(50))

class Thread(db.Model):
    id = db.Column(db.String(8), primary_key=True)
    group_id = db.Column(db.String(50))
    title = db.Column(db.String(100))
    is_locked = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='thread', cascade="all, delete")

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.String(8), db.ForeignKey('thread.id'))
    name = db.Column(db.String(50))
    body = db.Column(db.Text)

# --- ルート設定 ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/init_db')
def init_db():
    try:
        db.create_all()
        return "<h1>成功</h1><p>DB準備完了。ログイン画面へ戻ってください。</p>"
    except Exception as e:
        return f"失敗: {str(e)}"

@app.route('/api/auth', methods=['POST'])
def api_auth():
    d = request.json
    try:
        user = User.query.filter_by(username=d['u']).first()
        if not user:
            user = User(username=d['u'], password=generate_password_hash(d['p']), group_id="default")
            db.session.add(user)
            db.session.commit()
        if check_password_hash(user.password, d['p']):
            session['user_id'] = user.id
            session['username'] = user.username
            session['group_id'] = user.group_id
            return jsonify({"success": True, "group_id": user.group_id})
    except:
        db.session.rollback()
    return jsonify({"success": False}), 401

@app.route('/api/threads')
def api_threads():
    try:
        gid = session.get('group_id', 'default')
        ts = Thread.query.filter_by(group_id=gid, is_locked=False).all()
        return jsonify([{"id": t.id, "title": t.title, "count": len(t.posts)} for t in ts])
    except: return jsonify([])

@app.route('/api/thread/<id>')
def api_thread(id):
    t = Thread.query.get(id)
    if not t: return jsonify({"error": "None"}), 404
    posts = [{"name": p.name, "body": p.body} for p in t.posts]
    return jsonify({"title": t.title, "posts": posts, "is_locked": t.is_locked})

@app.route('/api/create_thread', methods=['POST'])
def api_create():
    if 'group_id' not in session: return jsonify({"success": False}), 403
    new_id = str(uuid.uuid4())[:8]
    t = Thread(id=new_id, group_id=session['group_id'], title=request.json['title'])
    db.session.add(t)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/post/<id>', methods=['POST'])
def api_post(id):
    t = Thread.query.get(id)
    if t and not t.is_locked and len(t.posts) < 300:
        p = Post(thread_id=id, name=session.get('username', 'Guest'), body=request.json['body'])
        db.session.add(p)
        if len(t.posts) + 1 >= 300: t.is_locked = True
        db.session.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
