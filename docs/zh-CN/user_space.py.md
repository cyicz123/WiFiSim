# user_space.py - 用户空间设备模拟

## 概述

`user_space.py` 实现了WiFi设备的用户空间行为模拟，包括设备类定义、MAC地址管理、设备参数数据库等核心功能。

## 主要组件

### 1. Device 类 - 设备模拟器

#### 核心属性
```python
class Device:
    def __init__(self, id, time, phase, vendor, model, randomization):
        self.id = id                    # 设备唯一标识
        self.phase = phase              # 设备状态 (0:锁屏, 1:亮屏, 2:活动)
        self.vendor = vendor            # 设备厂商
        self.model = model              # 设备型号
        self.randomization = randomization  # MAC随机化策略
        self.mac_address = []           # MAC地址列表
        self.position = (x, y)          # 设备位置坐标
        self.speed = float              # 移动速度 (m/s)
        self.direction = float          # 移动方向 (度)
```

#### MAC地址策略
- **策略0 (永久MAC)**：使用固定的MAC地址
- **策略1 (完全随机)**：生成本地管理的随机MAC
- **策略2 (保留OUI)**：保留厂商OUI，随机化后三字节
- **策略3 (专用MAC)**：使用预定义的专用MAC地址

#### 轮换模式
```python
self.mac_rotation_mode = 'per_burst'    # 每次burst更换
self.mac_rotation_mode = 'per_phase'    # 每次状态切换更换
self.mac_rotation_mode = 'interval'     # 按时间间隔更换
```

### 2. DeviceRates 类 - 设备参数数据库

#### 数据源
- **1.txt**：设备硬件参数
  - 厂商和型号信息
  - Burst长度分布
  - 无线能力参数（VHT、HT、扩展能力）
  - 支持的传输速率

- **2.txt**：设备行为参数
  - 不同状态下的包间隔分布
  - Burst间隔分布  
  - 状态驻留时间分布
  - 包传输抖动分布

#### 关键方法
```python
def get_prob_int_burst(self, model, phase)      # 获取burst内包间隔概率分布
def get_prob_between_bursts(self, model, phase) # 获取burst间间隔概率分布
def get_state_dwell(self, model, phase)         # 获取状态驻留时间分布
def get_burst_lengths(self, model)              # 获取burst长度分布
def is_sending_probe(self, model, phase)        # 判断是否发送probe request
```

## 核心功能详解

### MAC地址生成与管理

#### 随机MAC生成
```python
def random_MAC() -> str:
    """生成本地管理的随机MAC地址"""
    first_byte = int('%d%d%d%d%d%d10' % (bits), 2)  # 设置本地管理位
    return formatted_mac_address
```

#### OUI处理
```python
def get_oui(vendor_name: str) -> [str, str]:
    """根据厂商名称获取对应的OUI"""
    # 从oui_hex.txt读取IEEE OUI数据库
    # 支持前缀匹配和大小写不敏感
```

#### 掩码随机化
```python
def random_mac_addr_with_mask(base: str, mask: str) -> str:
    """使用掩码进行MAC地址随机化"""
    # mask=1的位保留base值
    # mask=0的位使用随机值
```

### 设备行为模拟

#### Probe Request发送
```python
def send_probe(self, inter_pkt_time, VHT_capabilities, ...):
    """发送Probe Request burst"""
    # 1. 根据轮换策略决定是否更换MAC
    # 2. 调用kernel_driver创建802.11帧
    # 3. 模拟处理延迟
    # 4. 返回生成的数据包列表
```

#### 状态切换
```python
def change_phase(self, phase, time):
    """设备状态切换"""
    self.phase = phase
    self.time_phase_changed = time
    # 触发per_phase模式的MAC更换
    if self.mac_rotation_mode == 'per_phase':
        self.force_mac_change = True
```

#### 位置更新
```python
def update_position(self, delta_t):
    """更新设备位置（简单直线运动模型）"""
    # 计算新位置坐标
    # 添加随机方向变化
    # 边界检查和约束
```

### SSID管理

#### SSID生成
```python
def create_ssid(self):
    """创建随机SSID列表"""
    # 生成1-10个随机SSID
    # 每个SSID长度为32字符
    # 使用字母数字字符集
```

## 配置文件格式

### 1.txt 格式
```
# vendor, device_name, burst_lengths, mac_policy, VHT_cap, ext_cap, HT_cap, rates, ext_rates
Apple,iPhone12,1:0.2/2:0.5/3:0.3,1,?,2d0102,006f,0c121824,
```

### 2.txt 格式  
```
# device_name, Phase, intra_burst_interval, inter_burst_interval, state_dwell, jitter
iPhone12,0,0.02:0.7/0.04:0.3,2.0:0.5/3.0:0.5,30:0.5/60:0.5,0.0:0.5/0.02:0.5
iPhone12,1,0.03:0.6/0.05:0.4,1.5:0.6/2.5:0.4,15:0.7/25:0.3,0.01:0.6/0.03:0.4
iPhone12,2,0.02:0.8/0.03:0.2,1.0:0.8/1.5:0.2,45:0.4/90:0.6,0.0:0.7/0.01:0.3
```

## 物理参数模拟

### 硬件特性
```python
self.queue_length = np.random.randint(1, 10)        # 队列长度
self.processing_delay = random.uniform(0.001, 0.005) # 处理延迟
self.power_level = random.uniform(10, 20)           # 发射功率(dBm)
```

### 移动性模拟
```python
self.position = (random.uniform(0, 100), random.uniform(0, 100))  # 初始位置
self.speed = random.uniform(0.5, 2.0)                             # 移动速度
self.direction = random.uniform(0, 360)                           # 移动方向
```

## 工具函数

### 频率计算
```python
def get_frequency(channel: int) -> int:
    """根据信道号计算频率"""
    if channel == 14:
        return 2484  # 特殊信道
    else:
        return 2407 + (channel * 5)  # 标准2.4GHz信道
```

### 序列号生成
```python
def produce_sequenceNumber(frag: int, seq: int) -> int:
    """生成802.11序列控制字段"""
    return (seq << 4) + frag
```

### MAC地址转换
```python
def mac_str_to_bytes(mac_str: str) -> bytes:    # 字符串转字节
def bytes_to_mac_str(mac_bytes: bytes) -> str:  # 字节转字符串
```

## 使用示例

### 创建设备实例
```python
device_rates = DeviceRates()
device = Device(
    id=0,
    time=datetime.now(),
    phase=2,  # 活动状态
    vendor="Apple",
    model="iPhone12",
    randomization=1  # 完全随机MAC
)
```

### 配置MAC轮换
```python
device.mac_rotation_mode = 'interval'  # 按时间间隔轮换
device.force_mac_change = True         # 强制下次更换
```

### 发送Probe Request
```python
packets = device.send_probe(
    inter_pkt_time=0.02,
    VHT_capabilities=vht_cap,
    extended_capabilities=ext_cap,
    HT_capabilities=ht_cap,
    num_pkt_burst=3,
    timestamp=datetime.now(),
    channel=6,
    supported_rates="0c121824",
    ext_supported_rates=""
)
```

## 扩展和定制

### 添加新设备类型
1. 在1.txt中添加设备参数行
2. 在2.txt中为每个状态添加行为参数
3. 更新OUI数据库（如需要）

### 自定义MAC轮换策略
1. 扩展mac_rotation_mode选项
2. 在send_probe()中添加处理逻辑
3. 实现相应的时间管理机制

### 增强移动性模型
1. 替换update_position()中的简单直线模型
2. 添加更复杂的路径规划算法
3. 集成真实的移动轨迹数据
