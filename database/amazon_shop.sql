SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for amazon_shop
-- ----------------------------
DROP TABLE IF EXISTS `amazon_shop`;
CREATE TABLE `amazon_shop`  (
  `NODE` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_zh_0900_as_cs NOT NULL COMMENT '商品ID',
  `NAME` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '商品名',
  `PRICE` decimal(10, 2) NULL DEFAULT NULL COMMENT '价格',
  `FEATURE` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '商品说明',
  PRIMARY KEY (`NODE`) USING BTREE,
  UNIQUE INDEX `NODE`(`NODE`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
