/**
 * auth.js - アカウント情報の暗号化保存と自動ログイン
 */

// 1. ログイン情報を暗号化(Base64)してローカルストレージに保存
function saveAuthSession(username, password) {
    const authData = {
        u: username,
        p: password,
        t: Date.now() // 保存日時
    };
    // JSONを文字列にしてからBase64で難読化
    const encrypted = btoa(unescape(encodeURIComponent(JSON.stringify(authData))));
    localStorage.setItem('bbs_session_key', encrypted);
}

// 2. ログアウト時にストレージを消去
function clearAuthSession() {
    localStorage.removeItem('bbs_session_key');
    window.location.href = '/login';
}

// 3. 自動ログイン実行（ページ読み込み時に呼ばれる）
async function attemptAutoLogin() {
    const savedData = localStorage.getItem('bbs_session_key');
    
    if (!savedData) return; // データがなければ何もしない

    try {
        // Base64をデコードしてパース
        const decoded = JSON.parse(decodeURIComponent(escape(atob(savedData))));
        
        // サーバーのログインAPIへ送信
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: decoded.u,
                password: decoded.p
            })
        });

        if (response.ok) {
            const result = await response.json();
            // ログイン成功ならそのグループのスレ一覧へ
            window.location.href = `/group/${result.group_id}`;
        } else {
            // 失敗（パスワード変更後など）ならストレージをクリア
            localStorage.removeItem('bbs_session_key');
        }
    } catch (e) {
        console.error("Auto login failed:", e);
        localStorage.removeItem('bbs_session_key');
    }
}

// フォーム送信時のイベント（ログイン画面で使用）
function handleLoginForm(event) {
    event.preventDefault();
    const u = document.getElementById('username').value;
    const p = document.getElementById('password').value;
    const remember = document.getElementById('remember_me').checked;

    if (remember) {
        saveAuthSession(u, p);
    }
    
    // 通常のログイン処理へ（fetch等）
    // ...
}

// ページロード時に自動ログインをチェック
document.addEventListener('DOMContentLoaded', () => {
    // ログインページにいる場合のみ自動ログインを試行
    if (window.location.pathname === '/login' || window.location.pathname === '/') {
        attemptAutoLogin();
    }
});
