import uuid, socket, os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bbs_data.db'
db = SQLAlchemy(app)

# --- モデル ---
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

# --- 投稿 & 300件制限ロジック ---
@app.route('/post/<thread_id>', methods=['POST'])
def add_post(thread_id):
    thread = Thread.query.get(thread_id)
    if thread and not thread.is_locked:
        if len(thread.posts) < 300:
            p = Post(thread_id=thread_id, name=request.form['name'], body=request.form['body'])
            db.session.add(p)
            db.session.commit()
            if len(thread.posts) >= 300:
                thread.is_locked = True
                db.session.commit()
    return redirect(url_for('view_thread', thread_id=thread_id))

# --- ポート探索機能 ---
def find_free_port(start):
    with socket.socket(socket.socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('localhost', start)) != 0: return start
        return find_free_port(start + 1)

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    port = find_free_port(10000)
    print(f"🚀 Server Start: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port)
