-- Phase 4: 添加身体参数字段到user表
-- 执行时间: 2026-02-04
-- 描述: 为用户偏好添加体重、身高、年龄、性别字段，支持METs精准热量计算

-- 添加体重字段
ALTER TABLE `user` ADD COLUMN `weight` FLOAT DEFAULT NULL COMMENT '体重（kg）' AFTER `daily_budget`;

-- 添加身高字段
ALTER TABLE `user` ADD COLUMN `height` FLOAT DEFAULT NULL COMMENT '身高（cm）' AFTER `weight`;

-- 添加年龄字段
ALTER TABLE `user` ADD COLUMN `age` INT DEFAULT NULL COMMENT '年龄' AFTER `height`;

-- 添加性别字段
ALTER TABLE `user` ADD COLUMN `gender` VARCHAR(10) DEFAULT NULL COMMENT '性别: male/female/other' AFTER `age`;

-- 验证字段添加成功
-- SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_COMMENT 
-- FROM INFORMATION_SCHEMA.COLUMNS 
-- WHERE TABLE_NAME = 'user' AND COLUMN_NAME IN ('weight', 'height', 'age', 'gender');
