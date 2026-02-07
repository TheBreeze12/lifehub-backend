-- Phase 25: 运动记录数据模型迁移脚本
-- 创建 exercise_record 表

CREATE TABLE IF NOT EXISTS `exercise_record` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '运动记录ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `plan_id` INT DEFAULT NULL COMMENT '关联的运动计划ID（可选，允许无计划的自由运动记录）',

    -- 运动执行数据
    `exercise_type` VARCHAR(30) DEFAULT 'walking' COMMENT '运动类型: walking/running/cycling/jogging/hiking/swimming/gym/indoor/outdoor',
    `actual_calories` FLOAT NOT NULL COMMENT '实际消耗热量（kcal）',
    `actual_duration` INT NOT NULL COMMENT '实际运动时长（分钟）',
    `distance` FLOAT DEFAULT NULL COMMENT '运动距离（米）',

    -- 路线数据（JSON格式存储轨迹点等）
    `route_data` TEXT DEFAULT NULL COMMENT '路线数据（JSON格式：轨迹点列表等）',

    -- 计划对比数据
    `planned_calories` FLOAT DEFAULT NULL COMMENT '计划消耗热量（kcal）',
    `planned_duration` INT DEFAULT NULL COMMENT '计划运动时长（分钟）',

    -- 运动日期
    `exercise_date` DATE NOT NULL COMMENT '运动日期（YYYY-MM-DD）',

    -- 时间记录
    `started_at` TIMESTAMP NULL DEFAULT NULL COMMENT '运动开始时间',
    `ended_at` TIMESTAMP NULL DEFAULT NULL COMMENT '运动结束时间',

    -- 备注
    `notes` TEXT DEFAULT NULL COMMENT '运动备注',

    -- 创建时间
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',

    -- 外键约束
    CONSTRAINT `fk_exercise_record_user` FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_exercise_record_plan` FOREIGN KEY (`plan_id`) REFERENCES `trip_plan`(`id`) ON DELETE SET NULL,

    -- 索引
    INDEX `idx_exercise_record_user_id` (`user_id`),
    INDEX `idx_exercise_record_plan_id` (`plan_id`),
    INDEX `idx_exercise_record_exercise_date` (`exercise_date`),
    INDEX `idx_exercise_record_exercise_type` (`exercise_type`),
    INDEX `idx_exercise_record_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='运动记录表';

-- 验证表创建
-- SELECT * FROM information_schema.tables WHERE table_name = 'exercise_record';
