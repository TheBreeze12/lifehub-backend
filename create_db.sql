-- ============================================================
-- LifeHub 数据库完整DDL（最新版本）
-- 更新时间: 2026-02-04
-- 版本说明: 包含 Phase 1-11 所有表结构
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS `lifehub` 
  DEFAULT CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

USE `lifehub`;

-- ============================================================
-- 1. 用户表 (user)
-- 包含 Phase 4 新增的身体参数字段: weight, height, age, gender
-- ============================================================
CREATE TABLE `user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nickname` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `password` varchar(128) NOT NULL DEFAULT '123456' COMMENT '用户密码',
  `health_goal` varchar(20) DEFAULT 'balanced' COMMENT '健康目标: reduce_fat/gain_muscle/control_sugar/balanced',
  `allergens` json DEFAULT NULL COMMENT '过敏原列表，JSON格式: ["海鲜", "花生"]',
  `travel_preference` varchar(20) DEFAULT 'self_driving' COMMENT '出行偏好: self_driving/public_transport/walking',
  `daily_budget` int DEFAULT '500' COMMENT '出行日预算（元）',
  -- Phase 4 新增: 身体参数字段
  `weight` float DEFAULT NULL COMMENT '体重（kg）',
  `height` float DEFAULT NULL COMMENT '身高（cm）',
  `age` int DEFAULT NULL COMMENT '年龄',
  `gender` varchar(10) DEFAULT NULL COMMENT '性别: male/female/other',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_unique` (`nickname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户表';

-- ============================================================
-- 2. 饮食记录表 (diet_record)
-- ============================================================
CREATE TABLE `diet_record` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `food_name` varchar(100) NOT NULL,
  `calories` decimal(6,1) NOT NULL,
  `protein` decimal(5,1) DEFAULT NULL,
  `fat` decimal(5,1) DEFAULT NULL,
  `carbs` decimal(5,1) DEFAULT NULL,
  `meal_type` varchar(20) DEFAULT NULL COMMENT '餐次: breakfast/lunch/dinner/snack',
  `record_date` date NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_date` (`user_id`,`record_date`),
  CONSTRAINT `diet_record_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='饮食记录表';

-- ============================================================
-- 3. 菜单识别表 (menu_recognition)
-- ============================================================
CREATE TABLE `menu_recognition` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `user_id` int DEFAULT NULL COMMENT '用户ID（可选）',
  `dishes` json NOT NULL COMMENT '识别出的菜品列表，JSON格式',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `fk_menu_recognition_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='菜单识别结果表';

-- ============================================================
-- 4. 运动计划表 (trip_plan)
-- ============================================================
CREATE TABLE `trip_plan` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `title` varchar(100) NOT NULL,
  `destination` varchar(50) DEFAULT NULL,
  `latitude` float DEFAULT NULL COMMENT '用户生成计划时的位置纬度（可选）',
  `longitude` float DEFAULT NULL COMMENT '用户生成计划时的位置经度（可选）',
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `status` varchar(20) DEFAULT 'planning',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `travelers` json DEFAULT NULL COMMENT '同行人员，JSON格式: ["本人", "父母"]',
  `is_offline` int DEFAULT '0' COMMENT '是否已下载离线包（0/1）',
  `offline_size` int DEFAULT NULL COMMENT '离线包大小（字节）',
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  CONSTRAINT `trip_plan_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='运动计划表';

-- ============================================================
-- 5. 运动项目表 (trip_item)
-- ============================================================
CREATE TABLE `trip_item` (
  `id` int NOT NULL AUTO_INCREMENT,
  `trip_id` int NOT NULL,
  `day_index` int NOT NULL,
  `start_time` time DEFAULT NULL,
  `place_name` varchar(100) NOT NULL,
  `place_type` varchar(20) DEFAULT NULL COMMENT '类型: walking/running/cycling/park/gym/indoor/outdoor',
  `duration` int DEFAULT NULL COMMENT '时长（分钟）',
  `cost` decimal(8,2) DEFAULT NULL COMMENT '预计消耗卡路里（kcal）',
  `notes` text,
  `sort_order` int DEFAULT '0',
  `latitude` float DEFAULT NULL COMMENT '纬度',
  `longitude` float DEFAULT NULL COMMENT '经度',
  PRIMARY KEY (`id`),
  KEY `idx_trip` (`trip_id`),
  CONSTRAINT `trip_item_ibfk_1` FOREIGN KEY (`trip_id`) REFERENCES `trip_plan` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='运动项目表';

-- ============================================================
-- 6. 餐前餐后对比表 (meal_comparison) - Phase 10 新增
-- ============================================================
CREATE TABLE `meal_comparison` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '对比记录ID',
  `user_id` int NOT NULL COMMENT '用户ID',
  -- 餐前图片信息
  `before_image_url` varchar(500) DEFAULT NULL COMMENT '餐前图片URL/路径',
  `before_features` text COMMENT '餐前图片特征（JSON格式）',
  -- 餐后图片信息
  `after_image_url` varchar(500) DEFAULT NULL COMMENT '餐后图片URL/路径',
  `after_features` text COMMENT '餐后图片特征（JSON格式）',
  -- 对比计算结果
  `consumption_ratio` float DEFAULT NULL COMMENT '消耗比例（0-1，1表示全部吃完）',
  `original_calories` float DEFAULT NULL COMMENT '原始估算热量（kcal）',
  `net_calories` float DEFAULT NULL COMMENT '净摄入热量（kcal）',
  -- 营养素信息
  `original_protein` float DEFAULT NULL COMMENT '原始蛋白质（g）',
  `original_fat` float DEFAULT NULL COMMENT '原始脂肪（g）',
  `original_carbs` float DEFAULT NULL COMMENT '原始碳水化合物（g）',
  `net_protein` float DEFAULT NULL COMMENT '净摄入蛋白质（g）',
  `net_fat` float DEFAULT NULL COMMENT '净摄入脂肪（g）',
  `net_carbs` float DEFAULT NULL COMMENT '净摄入碳水化合物（g）',
  -- 状态字段
  `status` varchar(20) DEFAULT 'pending_before' COMMENT '状态: pending_before/pending_after/completed',
  -- AI分析说明
  `comparison_analysis` text COMMENT 'AI对比分析说明',
  -- 时间戳
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_meal_comparison_user_id` (`user_id`),
  KEY `idx_meal_comparison_status` (`status`),
  KEY `idx_meal_comparison_created_at` (`created_at`),
  CONSTRAINT `fk_meal_comparison_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='餐前餐后对比表（Phase 10新增）';

-- ============================================================
-- 版本说明
-- ============================================================
-- 如果是从旧版本升级，请按顺序执行以下迁移脚本:
-- 1. migrations/phase4_add_body_params.sql (添加身体参数字段)
-- 2. migrations/phase10_meal_comparison.sql (创建餐前餐后对比表)
-- ============================================================