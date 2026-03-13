-- 为 trip_item 表新增 POI 相关字段
-- place_address: 真实地址（来自高德POI）
-- poi_id: 高德POI唯一标识
-- 注意: latitude/longitude 字段已存在，无需新增；语义从"用户位置"变更为"地点坐标（GCJ-02）"

ALTER TABLE trip_item
    ADD COLUMN place_address VARCHAR(200) DEFAULT NULL COMMENT '地点详细地址（来自POI）' AFTER longitude,
    ADD COLUMN poi_id VARCHAR(64) DEFAULT NULL COMMENT '高德POI唯一标识' AFTER place_address;
