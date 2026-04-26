import os, uuid, logging
from flask import Flask, render_template, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- データベース接続設定 ---
# SSLモードを確実に適用するURL構成
raw_url = "postgresql://user:QMe5ISzWDVoOpTMnKLzLb43mbRqM8hWU@dpg-d7mph9a8qa3s739r7lf0-a/bbs_db_03wc"
app.config['SQLALCHEMY_DATABASE_URI'] = raw_url + "?sslmode=require"
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

# --- APIルート ---
@app.route('/')
def home():
    return render_template('index.html')

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
        return jsonify({"success": False, "error": "パスワードが違います"}), 401
    except Exception as e:
        # ここでエラーの正体をHTML側に送る
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/threads')
def api_threads():
    try:
        ts = Thread.query.filter_by(group_id=session.get('group_id'), is_locked=False).all()
        return jsonify([{"id": t.id, "title": t.title, "count": len(t.posts)} for t in ts])
    except:
        return jsonify([])

# (以下略: 他のAPIルートは前回のままでOK)
@app.route('/api/create_thread', methods=['POST'])
def api_create():
    new_id = str(uuid.uuid4())[:8]
    t = Thread(id=new_id, group_id=session['group_id'], title=request.json['title'])
    db.session.add(t)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/post/<id>', methods=['POST'])
def api_post(id):
    t = Thread.query.get(id)
    if t and not t.is_locked:
        p = Post(thread_id=id, name=session['username'], body=request.json['body'])
        db.session.add(p)
        db.session.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
