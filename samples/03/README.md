# 项目三 G2 样例数据

本目录提供四表导入与 5 层 BOM 展开的最小闭环样例：

- `orders.csv`：订单表，含中文原始表头；
- `bom.csv`：5 层 BOM，含 2% 损耗与替代组；
- `inventory.csv`：原材料库存；
- `in_transit.csv`：在途批次；
- `sample_error_orders.csv`：包含负数量与非法日期的错误样例；
- `templates/`：四张标准 CSV 模板。

G2 验证订单：`SO-DEMO-001`，成品 `FG-100`，数量 `10`。
预期关键结果：`RM-005=122.400000`、`RM-006=40.800000`、`RM-007=50.000000`。
