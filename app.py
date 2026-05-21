import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app) 

database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("🚨 系統錯誤: 未設定 DATABASE_URL 環境變數")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------------------------------------------------------------
# 【升級版】資料庫模型設計 (豪華版 Task Model)
# -------------------------------------------------------------------------
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    category = db.Column(db.String(50), default='一般')     # 工作、生活、學習等
    due_date = db.Column(db.String(50), nullable=True)     # 截止日期
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'completed': self.completed,
            'priority': self.priority,
            'category': self.category,
            'due_date': self.due_date,
            'created_at': self.created_at.isoformat()
        }

@app.before_request
def create_tables():
    db.create_all()
    if None in app.before_request_funcs and create_tables in app.before_request_funcs[None]:
        app.before_request_funcs[None].remove(create_tables)

# -------------------------------------------------------------------------
# 路由設定
# -------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

# 取得所有任務
@app.route('/tasks', methods=['GET'])
def get_tasks():
    try:
        tasks = Task.query.order_by(Task.completed.asc(), Task.created_at.desc()).all()
        return jsonify([task.to_dict() for task in tasks])
    except Exception as e:
        return jsonify({'error': '無法取得任務列表', 'details': str(e)}), 500

# 建立新任務 (支援新欄位)
@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data or not data.get('title'):
        return jsonify({'error': '任務標題是必填欄位'}), 400
    
    try:
        new_task = Task(
            title=data['title'],
            priority=data.get('priority', 'medium'),
            category=data.get('category', '一般'),
            due_date=data.get('due_date', None)
        )
        db.session.add(new_task)
        db.session.commit()
        return jsonify(new_task.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '建立任務失敗', 'details': str(e)}), 500

# 更新任務
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
        if 'priority' in data:
            task.priority = data['priority']
        if 'category' in data:
            task.category = data['category']
        if 'due_date' in data:
            task.due_date = data['due_date']
            
        db.session.commit()
        return jsonify(task.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '更新任務失敗', 'details': str(e)}), 500

# 刪除任務
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