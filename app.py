import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv

# 載入本地環境變數 (.env)
load_dotenv()

app = Flask(__name__)

# 允許跨域請求 (確保前後端串接順暢)
CORS(app) 

# 環境變數安全檢查
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("🚨 系統錯誤: 未設定 DATABASE_URL 環境變數")

# 修正 Neon 連線字串開頭相容性問題 (將 postgres:// 修正為 postgresql://)
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------------------------------------------------------------
# 1. 資料庫模型設計 (Task Model)
# -------------------------------------------------------------------------
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'completed': self.completed,
            'created_at': self.created_at.isoformat()
        }

# -------------------------------------------------------------------------
# 2. Vercel Serverless 環境優化
# -------------------------------------------------------------------------
@app.before_request
def create_tables():
    """
    避免在全域執行 db.create_all() 導致 Vercel 編譯階段因缺少環境變數而失敗。
    改在第一個 HTTP 請求進來時才動態建立資料表，建立完後自動移除此檢查。
    """
    db.create_all()
    if None in app.before_request_funcs and create_tables in app.before_request_funcs[None]:
        app.before_request_funcs[None].remove(create_tables)

# -------------------------------------------------------------------------
# 3. 網頁與 API 路由設定 (CRUD)
# -------------------------------------------------------------------------

# 首頁：渲染前端網頁畫面
@app.route('/')
def index():
    return render_template('index.html')

# 取得所有任務 (GET)
@app.route('/tasks', methods=['GET'])
def get_tasks():
    try:
        tasks = Task.query.order_by(Task.created_at.desc()).all()
        return jsonify([task.to_dict() for task in tasks])
    except Exception as e:
        return jsonify({'error': '無法取得任務列表', 'details': str(e)}), 500

# 建立新任務 (POST)
@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data or not data.get('title'):
        return jsonify({'error': '任務標題 (title) 是必填欄位'}), 400
    
    try:
        new_task = Task(title=data['title'])
        db.session.add(new_task)
        db.session.commit()
        return jsonify(new_task.to_dict()), 201
    except Exception as e:
        db.session.rollback()  # 發生錯誤時復原狀態，避免連線卡死
        return jsonify({'error': '建立任務失敗', 'details': str(e)}), 500

# 更新任務狀態或內容 (PUT)
@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': '找不到該任務'}), 404

    data = request.get_json()
    try:
        if 'title' in data:
            task.title = data['title']
        if 'completed' in data:
            task.completed = data['completed']
            
        db.session.commit()
        return jsonify(task.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '更新任務失敗', 'details': str(e)}), 500

# 刪除任務 (DELETE)
@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': '找不到該任務'}), 404

    try:
        db.session.delete(task)
        db.session.commit()
        return jsonify({'message': '任務已成功刪除', 'id': task_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '刪除任務失敗', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)