import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# データベース設定
database_url = os.environ.get("DATABASE_URL", "sqlite:///bbs_data.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- データベースモデル ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
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

# --- 画面の処理 ---

# 1. ログイン/会員登録画面
@app.route('/')
@app.route('/login')
def login_page():
    return render_template('login.html')

# 2. 会員登録 & ログインAPI (JSから呼ばれる)
@app.route('/api/auth', methods=['POST'])
def api_auth():
    data = request.json
    u = data.get('username')
    p = data.get('password')
    g = data.get('group_id', 'default') # 未指定ならdefaultグループ
    
    user = User.query.filter_by(username=u).first()
    
    # ユーザーがいない場合は新規登録
    if not user:
        hashed_pw = generate_password_hash(p)
        user = User(username=u, password=hashed_pw, group_id=g)
        db.session.add(user)
        db.session.commit()
    
    # ログイン判定
    if check_password_hash(user.password, p):
        session['user_id'] = user.id
        session['username'] = user.username
        session['group_id'] = user.group_id
        return jsonify({"success": True, "group_id": user.group_id})
    
    return jsonify({"success": False}), 401

# 3. スレッド一覧
@app.route('/group/<group_id>')
def group_threads(group_id):
    if 'user_id' not in session: return redirect('/login')
    threads = Thread.query.filter_by(group_id=group_id, is_locked=False).all()
    return render_template('index.html', threads=threads, group_id=group_id)

# 4. スレッド表示
@app.route('/view/<thread_id>')
def view_thread(thread_id):
    if 'user_id' not in session: return redirect('/login')
    thread = Thread.query.get_or_404(thread_id)
    return render_template('view.html', thread=thread)

# 5. スレ立て
@app.route('/create_thread', methods=['POST'])
def create_thread():
    group_id = session.get('group_id')
    title = request.form.get('title')
    if group_id and title:
        new_id = str(uuid.uuid4())[:8]
        thread = Thread(id=new_id, group_id=group_id, title=title)
        db.session.add(thread)
        db.session.commit()
    return redirect(url_for('group_threads', group_id=group_id))

# 6. 投稿 (300件制限)
@app.route('/post/<thread_id>', methods=['POST'])
def add_post(thread_id):
    thread = Thread.query.get(thread_id)
    if thread and not thread.is_locked:
        if len(thread.posts) < 300:
            p = Post(thread_id=thread_id, name=session.get('username'), body=request.form.get('body'))
            db.session.add(p)
            db.session.commit()
            if len(thread.posts) >= 300:
                thread.is_locked = True
                db.session.commit()
    return redirect(url_for('view_thread', thread_id=thread_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
