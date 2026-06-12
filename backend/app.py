# ============================================================
# 咕噜咖喱饭 后端 API 服务
# Flask + MariaDB + JWT 认证
# ============================================================
import os
import re
import json
import uuid
import bcrypt
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import pymysql

from config import *

# ---------------------------------------------------
# 初始化 Flask
# ---------------------------------------------------
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
CORS(app, supports_credentials=True)

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------
# 数据库连接池（简易版）
# ---------------------------------------------------
def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME, charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db:
        db.close()

# ---------------------------------------------------
# 工具函数
# ---------------------------------------------------
def hash_password(plain):
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(plain, hashed):
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

# ---------------------------------------------------
# 认证装饰器
# ---------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'code': 401, 'msg': '请先登录'}), 401
        try:
            payload = decode_token(auth[7:])
            g.user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'code': 401, 'msg': '登录已过期，请重新登录'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'code': 401, 'msg': 'Token 无效'}), 401
        return f(*args, **kwargs)
    return wrapper

# ---------------------------------------------------
# 校验
# ---------------------------------------------------
PHONE_REGEX = re.compile(r'^1[3-9]\d{9}$')
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def validate_register(data):
    errors = []
    if not data.get('nickname') or len(data['nickname'].strip()) < 2:
        errors.append('昵称至少2个字符')
    if not data.get('phone') or not PHONE_REGEX.match(data['phone'].strip()):
        errors.append('手机号格式不正确')
    if not data.get('password') or len(data['password']) < 6:
        errors.append('密码至少6位')
    return errors

# ============================================================
# API 路由
# ============================================================

# ── 健康检查 ──
@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'code': 0, 'msg': 'pong', 'data': {}})

# ── 用户注册 ──
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    errors = validate_register(data)
    if errors:
        return jsonify({'code': 400, 'msg': '; '.join(errors)}), 400

    nickname = data['nickname'].strip()
    phone    = data['phone'].strip()
    password = data['password']

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE phone = %s", (phone,))
            if cur.fetchone():
                return jsonify({'code': 409, 'msg': '该手机号已注册'}), 409

        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO users (nickname, phone, password) VALUES (%s, %s, %s)",
                (nickname, phone, hash_password(password))
            )
            user_id = cur.lastrowid

        db.commit()

        token = create_token(user_id)
        return jsonify({
            'code': 0, 'msg': '注册成功',
            'data': {
                'token': token,
                'user': {'id': user_id, 'nickname': nickname, 'phone': phone}
            }
        })
    except Exception as e:
        db.rollback()
        return jsonify({'code': 500, 'msg': f'注册失败: {str(e)}'}), 500

# ── 用户登录 ──
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    account = data.get('account', '').strip()
    password = data.get('password', '')

    if not account or not password:
        return jsonify({'code': 400, 'msg': '账号和密码不能为空'}), 400

    db = get_db()
    with db.cursor() as cur:
        # 用手机号或邮箱登录
        if PHONE_REGEX.match(account):
            cur.execute("SELECT * FROM users WHERE phone = %s AND status = 1", (account,))
        elif EMAIL_REGEX.match(account):
            cur.execute("SELECT * FROM users WHERE email = %s AND status = 1", (account,))
        else:
            return jsonify({'code': 400, 'msg': '请输入正确的手机号或邮箱'}), 400

        user = cur.fetchone()

    if not user:
        return jsonify({'code': 401, 'msg': '账号未注册或已被禁用'}), 401

    if not check_password(password, user['password']):
        return jsonify({'code': 401, 'msg': '密码错误'}), 401

    token = create_token(user['id'])
    return jsonify({
        'code': 0, 'msg': '登录成功',
        'data': {
            'token': token,
            'user': {
                'id': user['id'],
                'nickname': user['nickname'],
                'phone': user['phone'],
                'email': user['email'],
                'avatar': user['avatar'],
                'gender': user['gender'],
                'role': user['role']
            }
        }
    })

# ── 获取个人信息 ──
@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_profile():
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, nickname, phone, email, avatar, gender, birthday, role, created_at "
            "FROM users WHERE id = %s", (g.user_id,)
        )
        user = cur.fetchone()

    if not user:
        return jsonify({'code': 404, 'msg': '用户不存在'}), 404

    # 日期转字符串
    if user.get('birthday'):
        user['birthday'] = user['birthday'].strftime('%Y-%m-%d')
    user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({'code': 0, 'msg': 'ok', 'data': user})

# ── 更新个人信息 ──
@app.route('/api/user/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    db = get_db()

    allowed_fields = ['nickname', 'email', 'gender', 'birthday']
    updates = []
    params = []

    for field in allowed_fields:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            if field == 'email' and val and not EMAIL_REGEX.match(val):
                return jsonify({'code': 400, 'msg': '邮箱格式不正确'}), 400
            if field == 'gender' and val not in ('male', 'female', 'other', None):
                return jsonify({'code': 400, 'msg': '性别值无效'}), 400
            updates.append(f"{field} = %s")
            params.append(val)

    if not updates:
        return jsonify({'code': 400, 'msg': '没有需要更新的字段'}), 400

    params.append(g.user_id)
    sql = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"

    try:
        with db.cursor() as cur:
            cur.execute(sql, tuple(params))
        db.commit()
        return jsonify({'code': 0, 'msg': '更新成功'})
    except Exception as e:
        db.rollback()
        return jsonify({'code': 500, 'msg': f'更新失败: {str(e)}'}), 500

# ── 上传头像 ──
@app.route('/api/user/avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'file' not in request.files:
        return jsonify({'code': 400, 'msg': '请选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 400, 'msg': '文件名为空'}), 400

    # 校验文件类型
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return jsonify({'code': 400, 'msg': '仅支持 jpg/png/gif/webp 格式'}), 400

    # 保存文件
    filename = f"avatar_{g.user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    # 更新数据库
    avatar_url = f"/gulu/api/uploads/{filename}"
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE users SET avatar = %s WHERE id = %s", (avatar_url, g.user_id))
        db.commit()
        return jsonify({'code': 0, 'msg': '头像更新成功', 'data': {'avatar': avatar_url}})
    except Exception as e:
        db.rollback()
        return jsonify({'code': 500, 'msg': f'保存失败: {str(e)}'}), 500

# ── 静态文件: 头像访问 ──
@app.route('/api/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(UPLOAD_DIR, filename)

# ── 修改密码 ──
@app.route('/api/user/password', methods=['PUT'])
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')

    if not old_pw or not new_pw:
        return jsonify({'code': 400, 'msg': '新旧密码不能为空'}), 400
    if len(new_pw) < 6:
        return jsonify({'code': 400, 'msg': '新密码至少6位'}), 400

    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT password FROM users WHERE id = %s", (g.user_id,))
        user = cur.fetchone()

    if not check_password(old_pw, user['password']):
        return jsonify({'code': 401, 'msg': '原密码错误'}), 401

    try:
        with db.cursor() as cur:
            cur.execute("UPDATE users SET password = %s WHERE id = %s",
                        (hash_password(new_pw), g.user_id))
        db.commit()
        return jsonify({'code': 0, 'msg': '密码修改成功'})
    except Exception as e:
        db.rollback()
        return jsonify({'code': 500, 'msg': f'修改失败: {str(e)}'}), 500

# ============================================================
# 启动
# ============================================================
if __name__ == '__main__':
    print(f'🍛 咕噜咖喱饭 API 启动在 0.0.0.0:{SERVER_PORT}')
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=False)
