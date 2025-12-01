# TE-CCL 数据量输入指南

TE-CCL 现在支持**两种方式**指定数据量：

## 方式 1：带单位的字符串输入（推荐）✨

使用 `total_data` 字段，直接写带单位的字符串：

```json
"TopologyParams": {
    "total_data": "1KB"    // 支持 KB、MB、GB
}
```

**支持的单位**：
- `KB` 或 `K`：千字节
- `MB` 或 `M`：兆字节  
- `GB` 或 `G`：吉字节
- 大小写不敏感，支持空格：`"1 gb"`, `"4KB"`, `"2 GB"` 都可以

## 方式 2：数值输入（向后兼容）

使用 `total_data_MB` 字段，单位固定为 **MB**：

```json
"TopologyParams": {
    "total_data_MB": 1024   // 必须是 MB
}
```

## 常用数据量快速参考

| 数据量        | 换算为 MB                | total_data_MB 值    |
|--------------|-------------------------|---------------------|
| **1 KB**     | 1 / 1024 MB             | `0.0009765625`      |
| **4 KB**     | 4 / 1024 MB             | `0.00390625`        |
| **16 KB**    | 16 / 1024 MB            | `0.015625`          |
| **64 KB**    | 64 / 1024 MB            | `0.0625`            |
| **256 KB**   | 256 / 1024 MB           | `0.25`              |
| **1 MB**     | 1 MB                    | `1`                 |
| **4 MB**     | 4 MB                    | `4`                 |
| **16 MB**    | 16 MB                   | `16`                |
| **64 MB**    | 64 MB                   | `64`                |
| **256 MB**   | 256 MB                  | `256`               |
| **1 GB**     | 1024 MB                 | `1024`              |
| **4 GB**     | 4096 MB                 | `4096`              |

## 换算公式

- **KB → MB**:  `MB = KB / 1024`
- **GB → MB**:  `MB = GB × 1024`

## 示例配置

### 使用带单位字符串（推荐）

#### 1KB 数据量
```json
"TopologyParams": {
    "total_data": "1KB"
}
```

#### 256KB 数据量
```json
"TopologyParams": {
    "total_data": "256KB"
}
```

#### 4GB 数据量
```json
"TopologyParams": {
    "total_data": "4GB"
}
```

### 使用数值（传统方式）

#### 1KB 数据量
```json
"TopologyParams": {
    "total_data_MB": 0.0009765625
}
```

#### 256KB 数据量
```json
"TopologyParams": {
    "total_data_MB": 0.25
}
```

#### 4GB 数据量
```json
"TopologyParams": {
    "total_data_MB": 4096
}
```

## 注意事项

1. **优先级**：如果同时指定 `total_data` 和 `total_data_MB`，`total_data` 优先生效
2. **自适应单位显示**：输出摘要会自动选择合适单位（KB/MB/GB）显示
3. **小数支持**：可以使用小数，如 `"1.5GB"`, `"0.5MB"`
4. **AllToAll 语义**：对 AllToAll 集合通信，数据量表示**每个节点的接收缓冲区大小**
5. **AllGather 语义**：对 AllGather，总数据量 = `数据量 × 节点数`

## Python 快速换算脚本

```python
# KB 转 MB
kb = 1
mb = kb / 1024
print(f"{kb} KB = {mb} MB")

# GB 转 MB
gb = 1
mb = gb * 1024
print(f"{gb} GB = {mb} MB")
```
