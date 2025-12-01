# TE-CCL 配置更新说明

## 主要变更

所有示例 JSON 配置文件已从 `total_data_MB` 更新为 `total_data`，现在支持带单位的字符串输入。

## 更新的文件列表

✅ **所有示例配置文件已更新：**

1. `mesh.json` - 1GB
2. `dgx1_sample.json` - 1GB
3. `dgx2_sample.json` - 1GB
4. `amd_sample.json` - 256MB
5. `ndv2_sample.json` - 1GB
6. `ndv2_input.json` - 1GB
7. `torus_allgather.json` - 1GB
8. `torus_alltoall.json` - 1GB

## 使用方式

### 新格式（推荐）

```json
{
    "TopologyParams": {
        "total_data": "1GB"  // 支持 KB, MB, GB
    }
}
```

**支持的格式：**
- `"1KB"`, `"4KB"`, `"256KB"` - 千字节
- `"1MB"`, `"256MB"`, `"1GB"` - 兆字节
- `"1GB"`, `"4GB"`, `"16GB"` - 吉字节
- `"1.5GB"`, `"0.5MB"` - 支持小数
- 不区分大小写：`"1gb"`, `"1GB"`, `"1Gb"` 都可以
- 支持简写：`"1K"`, `"1M"`, `"1G"`

### 旧格式（仍然支持）

```json
{
    "TopologyParams": {
        "total_data_MB": 1024  // 必须是数值，单位为 MB
    }
}
```

## 常用数据量示例

| 需求           | 新格式                | 旧格式 (MB)        |
|---------------|----------------------|-------------------|
| 1 KB          | `"total_data": "1KB"` | `"total_data_MB": 0.0009765625` |
| 256 KB        | `"total_data": "256KB"` | `"total_data_MB": 0.25` |
| 1 MB          | `"total_data": "1MB"` | `"total_data_MB": 1` |
| 256 MB        | `"total_data": "256MB"` | `"total_data_MB": 256` |
| 1 GB          | `"total_data": "1GB"` | `"total_data_MB": 1024` |
| 4 GB          | `"total_data": "4GB"` | `"total_data_MB": 4096` |

## 优势

✅ **更直观**：直接看到数据单位，无需换算  
✅ **更安全**：避免单位混淆错误  
✅ **更灵活**：支持 KB/MB/GB 任意单位  
✅ **向后兼容**：旧的 `total_data_MB` 仍然支持

## 输出显示

无论使用哪种输入方式，输出摘要都会**自适应选择合适的单位**：

```
0️⃣  总数据量: 1.0000 KB    (当 < 1MB)
0️⃣  总数据量: 256.0000 MB  (当 1MB ~ 1GB)
0️⃣  总数据量: 4.0000 GB    (当 >= 1GB)
```

## 迁移指南

如果你有自己的配置文件，可以这样快速迁移：

**旧配置：**
```json
"total_data_MB": 1024
```

**新配置：**
```json
"total_data": "1GB"
```

换算方法：
- 如果 `total_data_MB >= 1024`：除以 1024，单位用 `GB`
- 如果 `1 <= total_data_MB < 1024`：保持数值，单位用 `MB`
- 如果 `total_data_MB < 1`：乘以 1024，单位用 `KB`

详见 `DATA_SIZE_CONVERSION.md` 获取完整换算表。
