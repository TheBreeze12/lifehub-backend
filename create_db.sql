CREATE DATABASE `lifehub` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

CREATE TABLE `diet_record` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `food_name` varchar(100) NOT NULL,
  `calories` decimal(6,1) NOT NULL,
  `protein` decimal(5,1) DEFAULT NULL,
  `fat` decimal(5,1) DEFAULT NULL,
  `carbs` decimal(5,1) DEFAULT NULL,
  `meal_type` varchar(20) DEFAULT NULL,
  `record_date` date NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_date` (`user_id`,`record_date`),
  CONSTRAINT `diet_record_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `menu_recognition` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `user_id` int DEFAULT NULL COMMENT '用户ID（可选）',
  `dishes` json NOT NULL COMMENT '识别出的菜品列表，JSON格式',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `fk_menu_recognition_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='菜单识别结果表';

CREATE TABLE `trip_item` (
  `id` int NOT NULL AUTO_INCREMENT,
  `trip_id` int NOT NULL,
  `day_index` int NOT NULL,
  `start_time` time DEFAULT NULL,
  `place_name` varchar(100) NOT NULL,
  `place_type` varchar(20) DEFAULT NULL COMMENT '类型: walking/running/cycling/park/gym/indoor/outdoor (运动类型) 或 attraction/dining/transport/accommodation (兼容旧数据)',
  `duration` int DEFAULT NULL,
  `cost` decimal(8,2) DEFAULT NULL COMMENT '预计消耗卡路里（kcal），原为费用字段，现语义转换为卡路里',
  `notes` text,
  `sort_order` int DEFAULT '0',
  `latitude` float DEFAULT NULL COMMENT '纬度',
  `longitude` float DEFAULT NULL COMMENT '经度',
  PRIMARY KEY (`id`),
  KEY `idx_trip` (`trip_id`),
  CONSTRAINT `trip_item_ibfk_1` FOREIGN KEY (`trip_id`) REFERENCES `trip_plan` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=252 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

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
) ENGINE=InnoDB AUTO_INCREMENT=65 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nickname` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `health_goal` varchar(20) DEFAULT 'balanced',
  `allergens` json DEFAULT NULL,
  `travel_preference` varchar(20) DEFAULT 'self_driving',
  `daily_budget` int DEFAULT '500',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `password` varchar(100) NOT NULL DEFAULT '123456',
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_unique` (`nickname`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;