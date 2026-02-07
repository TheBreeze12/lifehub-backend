-- Phase 10: 餐前餐后对比数据模型迁移脚本
-- 创建 meal_comparison 表

CREATE TABLE IF NOT EXISTS `meal_comparison` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '对比记录ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    
    -- 餐前图片信息
    `before_image_url` VARCHAR(500) COMMENT '餐前图片URL/路径',
    `before_features` TEXT COMMENT '餐前图片特征（JSON格式）',
    
    -- 餐后图片信息
    `after_image_url` VARCHAR(500) COMMENT '餐后图片URL/路径',
    `after_features` TEXT COMMENT '餐后图片特征（JSON格式）',
    
    -- 对比计算结果
    `consumption_ratio` FLOAT COMMENT '消耗比例（0-1，1表示全部吃完）',
    `original_calories` FLOAT COMMENT '原始估算热量（kcal）',
    `net_calories` FLOAT COMMENT '净摄入热量（kcal）',
    
    -- 营养素信息
    `original_protein` FLOAT COMMENT '原始蛋白质（g）',
    `original_fat` FLOAT COMMENT '原始脂肪（g）',
    `original_carbs` FLOAT COMMENT '原始碳水化合物（g）',
    `net_protein` FLOAT COMMENT '净摄入蛋白质（g）',
    `net_fat` FLOAT COMMENT '净摄入脂肪（g）',
    `net_carbs` FLOAT COMMENT '净摄入碳水化合物（g）',
    
    -- 状态字段
    `status` VARCHAR(20) DEFAULT 'pending_before' COMMENT '状态: pending_before/pending_after/completed',
    
    -- AI分析说明
    `comparison_analysis` TEXT COMMENT 'AI对比分析说明',
    
    -- 时间戳
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 外键约束
    CONSTRAINT `fk_meal_comparison_user` FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
    
    -- 索引
    INDEX `idx_meal_comparison_user_id` (`user_id`),
    INDEX `idx_meal_comparison_status` (`status`),
    INDEX `idx_meal_comparison_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='餐前餐后对比表';

-- 验证表创建
-- SELECT * FROM information_schema.tables WHERE table_name = 'meal_comparison';
