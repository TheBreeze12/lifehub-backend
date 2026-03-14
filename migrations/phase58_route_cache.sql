-- Phase 58: 为 trip_plan 增加路线缓存字段

ALTER TABLE `trip_plan`
    ADD COLUMN `route_cache` JSON NULL COMMENT '已生成路线缓存（JSON）' AFTER `offline_size`,
    ADD COLUMN `route_cache_updated_at` TIMESTAMP NULL DEFAULT NULL COMMENT '路线缓存更新时间' AFTER `route_cache`;