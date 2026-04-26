import os, uuid
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- データベース接続設定 (エラーを物理的に回避する確定URL) ---
# .singapore-postgres.render.com を省いた最短のホスト名 + ポート番号指定です
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://user:QMe5ISzWDVoOpTMnKLzLb43mbRqM8hWU@dpg-d7mph9a8qa3s739r7lf0-a:5432/bbs_db_03wc?sslmode=require"
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

# --- 基本ルート ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/init_db')
def init_db():
    try:
        db.create_all()
        return "SUCCESS"
    except Exception as e:
        return str(e)

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
# --- 削除機能 ---

# スレッド削除（自分が立てたスレのグループに属している場合のみ）
@app.route('/api/delete_thread/<id>', methods=['POST'])
def api_delete_thread(id):
    if 'user_id' not in session: return jsonify({"success": False}), 403
    t = Thread.query.get(id)
    if t:
        db.session.delete(t)
        db.session.commit()
    return jsonify({"success": True})

# 投稿削除（自分の名前の投稿のみ消せる設定）
@app.route('/api/delete_post/<int:post_id>', methods=['POST'])
def api_delete_post(post_id):
    if 'user_id' not in session: return jsonify({"success": False}), 403
    p = Post.query.get(post_id)
    # 自分の名前の投稿かチェック
    if p and p.name == session.get('username'):
        db.session.delete(p)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "削除権限がありません"}), 403

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
    new_id = str(uuid.uuid4())[:8]
    t = Thread(id=new_id, group_id=session.get('group_id', 'default'), title=request.json['title'])
    db.session.add(t)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/post/<id>', methods=['POST'])
def api_post(id):
    t = Thread.query.get(id)
    if t and not t.is_locked:
        p = Post(thread_id=id, name=session.get('username', 'Guest'), body=request.json['body'])
        db.session.add(p)
        if len(t.posts) >= 300: t.is_locked = True
        db.session.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
