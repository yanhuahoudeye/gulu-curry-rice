# ============================================================
# 咕噜咖喱饭 后端配置
# ============================================================
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# MariaDB 配置（服务器上改，兼容 MySQL 变量名）
DB_HOST     = os.getenv('MYSQL_HOST', '127.0.0.1') or os.getenv('DB_HOST', '127.0.0.1')
DB_PORT     = int(os.getenv('MYSQL_PORT', 3306) or os.getenv('DB_PORT', 3306))
DB_USER     = os.getenv('MYSQL_USER', 'root') or os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('MYSQL_PASSWORD', 'your_password_here') or os.getenv('DB_PASSWORD', 'your_password_here')
DB_NAME     = os.getenv('MYSQL_DB', 'gulu_curry') or os.getenv('DB_NAME', 'gulu_curry')

# JWT 密钥（生产环境请改掉）
JWT_SECRET = os.getenv('JWT_SECRET', 'gulu-curry-secret-key-change-in-production-2026')

# 上传目录
UPLOAD_DIR  = os.path.join(BASE_DIR, 'uploads')
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB

# 服务端口
SERVER_PORT = int(os.getenv('SERVER_PORT', 25036))
