-- ============================================================
-- 咕噜咖喱饭 数据库初始化
-- ============================================================

CREATE DATABASE IF NOT EXISTS gulu_curry
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE gulu_curry;

-- ---------------------------------------------------
-- 用户表
-- ---------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nickname    VARCHAR(50)     NOT NULL,
    phone       VARCHAR(20)     NOT NULL UNIQUE,
    email       VARCHAR(100)    DEFAULT NULL,
    password    VARCHAR(255)    NOT NULL COMMENT 'bcrypt hash',
    avatar      VARCHAR(500)    DEFAULT NULL COMMENT '头像URL',
    gender      ENUM('male','female','other') DEFAULT NULL,
    birthday    DATE            DEFAULT NULL,
    role        ENUM('user','admin') NOT NULL DEFAULT 'user',
    status      TINYINT         NOT NULL DEFAULT 1 COMMENT '1=正常 0=禁用',
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_phone  (phone),
    INDEX idx_email  (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------
-- 订单表（预留）
-- ---------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT UNSIGNED NOT NULL,
    order_no    VARCHAR(32)     NOT NULL UNIQUE COMMENT '订单号',
    total_price DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    status      ENUM('pending','paid','preparing','delivering','completed','cancelled')
                                NOT NULL DEFAULT 'pending',
    remark      VARCHAR(500)    DEFAULT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user   (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
