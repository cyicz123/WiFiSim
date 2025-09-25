# user_config.py - 用户配置生成器

## 概述

`user_config.py` 是WiFi仿真系统的配置文件生成器，负责创建和维护设备参数数据库，包括OUI数据预处理、设备配置文件生成等功能。

## 主要功能

### 1. OUI数据预处理

#### OUI提取与转换
```python
# 从IEEE OUI数据库提取厂商信息
with open('oui.txt', encoding='utf-8', errors='replace') as f:
    # 处理原始OUI文件
    # 提取十六进制OUI和厂商名称
    # 生成oui_hex.txt文件
```

**输入文件**：`oui.txt` - IEEE官方OUI数据库
**输出文件**：`oui_hex.txt` - 处理后的OUI映射表

#### 格式转换
- 从复杂的IEEE格式提取关键信息
- 统一OUI格式为 `XX:XX:XX` 形式
- 建立厂商名称到OUI的快速索引

### 2. 设备配置文件生成

#### 1.txt - 设备硬件参数配置

**文件结构**：
```
# vendor, device_name, burst_lengths, mac_policy, VHT_cap, ext_cap, HT_cap, rates, ext_rates
```

**字段说明**：
- `vendor`：设备厂商名称
- `device_name`：具体设备型号
- `burst_lengths`：Burst长度概率分布（格式：`1:0.2/2:0.5/3:0.3`）
- `mac_policy`：MAC地址策略（0-3）
- `VHT_cap`：VHT能力字段（十六进制，"?"表示不支持）
- `ext_cap`：扩展能力字段（十六进制）
- `HT_cap`：HT能力字段（十六进制）
- `rates`：支持速率（十六进制编码）
- `ext_rates`：扩展支持速率（十六进制编码）

#### 2.txt - 设备行为参数配置

**文件结构**：
```
# device_name, Phase, intra_burst_interval, inter_burst_interval, state_dwell, jitter
```

**字段说明**：
- `device_name`：设备型号
- `Phase`：设备状态（0=锁屏，1=亮屏，2=活动）
- `intra_burst_interval`：Burst内包间隔分布
- `inter_burst_interval`：Burst间间隔分布
- `state_dwell`：状态驻留时间分布
- `jitter`：包间隔抖动分布

## 内置设备数据库

### 支持的厂商和设备

#### 主要厂商
```python
vendor_device_map = {
    'OnePlus': ['nord 5g', 'one plus9pro', 'one plus9rt', ...],
    'Samsung': ['note20ultra', 'galaxys21', 'galaxys20fe', ...],
    'Xiaomi': ['note8t', 'mi9lite', 'mi10lite', ...],
    'Huawei': ['p9lite', 'p40lite', 'p30lite', ...],
    'Lenovo': ['think pad x13gen1', 'think pad x1yoga', ...],
    'OPPO': ['find x3pro', 'find x5pro', ...],
    'vivo': ['x60', 'x60pro', 'x60t', ...],
    'Realme': ['gt neo2', 'gt neo2t', ...],
    'iQOO': ['iQOO 7', 'iQOO Neo5', ...],
    'honor': ['honor9x', 'honor90', ...],
    'MeiZu': ['18', '18s', '18plus', ...],
    'Nubia': ['red magic7', 'red magic7pro', ...]
}
```

### 参数生成算法

#### VHT能力生成
```python
def generate_vht_capabilities():
    """70%概率不支持VHT，否则生成8字节能力字段"""
    if random.random() < 0.7:
        return "?"  # 不支持VHT
    else:
        return ''.join(random.choices('0123456789abcdef', k=16))
```

#### 扩展能力生成
```python
def generate_extended_capabilities():
    """生成6字节扩展能力字段"""
    return ''.join(random.choices('0123456789abcdef', k=12))
```

#### HT能力生成
```python
def generate_ht_capabilities():
    """生成8字节HT能力字段"""
    return ''.join(random.choices('0123456789abcdef', k=16))
```

#### MAC策略生成
```python
def generate_mac_policy():
    """随机选择MAC地址策略"""
    return random.choice([0, 1, 2, 3])
    # 0: 永久MAC
    # 1: 完全随机
    # 2: 随机但保留OUI
    # 3: 专用/预生成MAC
```

### 时间参数生成

#### 支持速率分布
```python
def generate_supported_rates():
    """生成基本支持速率分布"""
    rates = [6, 9, 12, 18]  # Mbps
    probs = [随机概率分布]
    return '/'.join(f"{r}:{p}" for r, p in zip(rates, probs))
```

#### 状态驻留时间
```python
def generate_state_dwell():
    """生成状态驻留时间分布（5-60秒）"""
    dwell_times = [5, 10, 20, 30, 45, 60]
    probs = [随机权重分布]
    return '/'.join(f"{t}:{p}" for t, p in zip(dwell_times, probs))
```

#### 包间隔抖动
```python
def generate_jitter():
    """生成包间隔抖动分布（0.01-0.2秒）"""
    jitters = [0.01, 0.05, 0.1, 0.2]
    probs = [随机权重分布]
    return '/'.join(f"{j}:{p}" for j, p in zip(jitters, probs))
```

## 真实性优化

### Burst参数优化
- **Burst内间隔**：20-100毫秒，符合真实设备行为
- **Burst间间隔**：2-5秒，模拟实际扫描周期
- **Burst长度**：1-3帧，匹配观测到的实际模式

### 时间分布建模
```python
# Burst内部间隔（毫秒级）
burst_time_in = '/'.join(
    f"{round(random.uniform(0.02, 0.1)*100)/100}:{random_prob}"
    for _ in range(random.randint(1, 3))
)

# Burst之间间隔（秒级）  
burst_time_between = '/'.join(
    f"{round(random.uniform(2, 5)*100)/100}:{random_prob}"
    for _ in range(random.randint(1, 3))
)
```

## 配置文件模板

### 1.txt模板
```python
TEMPLATE_1 = (
    "# vendor name, device_name, burst length (value:probability/...), "
    "mac_policy, VHT capabilities, extended capabilities, HT capabilities, "
    "supported_rates (Mbps), ext_supported_rates (Mbps)\n"
)
```

### 2.txt模板
```python
TEMPLATE_2 = (
    "# device_name, Phase (0 Locked 1 Awake 2 Active), "
    "intra-burst interval (value:probability/...), "
    "inter-burst interval (value:probability/...), "
    "state dwell time (value:probability/...), "
    "jitter (value:probability/...)\n"
)
```

## 批量生成流程

### 主生成循环
```python
for i in range(100):  # 生成100种设备配置
    vendor_name = random.choice(list(vendor_device_map.keys()))
    device_name = get_device_name(vendor_name)
    
    # 为每个设备生成3个状态的参数
    for phase in range(3):
        # 生成时间参数分布
        # 写入2.txt
        
    # 生成硬件能力参数
    # 写入1.txt
```

## 使用方法

### 基本使用
```bash
cd src
python user_config.py
```

### 输出文件
运行后将生成/更新以下文件：
- `oui_hex.txt`：处理后的OUI数据库
- `1.txt`：设备硬件参数配置
- `2.txt`：设备行为参数配置

### 自定义配置

#### 添加新厂商
```python
vendor_device_map['NewVendor'] = [
    'device1', 'device2', 'device3'
]
```

#### 调整参数范围
```python
# 修改时间参数范围
burst_time_in_range = (0.01, 0.15)    # Burst内间隔范围
burst_time_between_range = (1.0, 8.0)  # Burst间间隔范围
state_dwell_range = (3, 120)           # 状态驻留范围
```

#### 自定义能力字段
```python
def custom_vht_capabilities():
    """自定义VHT能力生成逻辑"""
    # 实现特定的VHT能力模式
    pass
```

## 数据质量保证

### 概率分布归一化
```python
# 确保概率分布总和为1
total = sum(probs)
probs = [round(p/total, 2) for p in probs]
```

### 参数合理性检查
- 时间参数在合理范围内
- 概率值非负且归一化
- 十六进制字段格式正确
- 设备型号命名一致性

### 兼容性维护
- 向后兼容旧版本配置格式
- 处理缺失或损坏的数据条目
- 提供默认值机制

## 扩展接口

### 自定义设备添加
```python
def add_custom_device(vendor, model, capabilities):
    """添加自定义设备配置"""
    # 验证参数格式
    # 写入配置文件
    # 更新内部数据库
```

### 配置导入导出
```python
def export_config(filename):
    """导出当前配置为JSON格式"""
    
def import_config(filename):
    """从JSON导入配置并更新文件"""
```

### 批量更新工具
```python
def batch_update_devices(update_rules):
    """根据规则批量更新设备参数"""
    # 支持正则表达式匹配
    # 支持条件更新
    # 提供回滚机制
```
