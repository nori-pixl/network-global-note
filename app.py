import os, uuid
from flask import Flask, render_template, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- データベース接続設定 ---
raw_url = "postgresql://user:QMe5ISzWDVoOpTMnKLzLb43mbRqM8hWU@dpg-d7mph9a8qa3s739r7lf0-a/bbs_db_03wc"

# Render/PostgreSQL向けの修正
if raw_url.startswith("postgres://"):
    db_url = raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
else:
    db_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# SSL設定を末尾に付与
if "?" not in db_url:
    db_url += "?sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}

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

# --- APIルート ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/auth', methods=['POST'])
def api_auth():
    try:
        d = request.json
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
        return jsonify({"success": False, "error": "パスワード不一致"}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"DB Error: {str(e)}"}), 500

@app.route('/api/threads')
def api_threads():
    try:
        ts = Thread.query.filter_by(group_id=session.get('group_id'), is_locked=False).all()
        return jsonify([{"id": t.id, "title": t.title, "count": len(t.posts)} for t in ts])
    except: return jsonify([])

@app.route('/api/thread/<id>')
def api_thread(id):
    t = Thread.query.get(id)
    if not t: return jsonify({"error": "NoThread"}), 404
    posts = [{"name": p.name, "body": p.body} for p in t.posts]
    return jsonify({"title": t.title, "posts": posts, "is_locked": t.is_locked})

@app.route('/api/create_thread', methods=['POST'])
def api_create():
    try:
        new_id = str(uuid.uuid4())[:8]
        t = Thread(id=new_id, group_id=session['group_id'], title=request.json['title'])
        db.session.add(t)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)})

@app.route('/api/post/<id>', methods=['POST'])
def api_post(id):
    try:
        t = Thread.query.get(id)
        if t and not t.is_locked:
            p = Post(thread_id=id, name=session['username'], body=request.json['body'])
            db.session.add(p)
            if len(t.posts) >= 300: t.is_locked = True
            db.session.commit()
        return jsonify({"success": True})
    except: return jsonify({"success": False})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
