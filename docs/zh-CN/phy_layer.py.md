# phy_layer.py - 物理层仿真模块

## 概述

`phy_layer.py` 实现了WiFi物理层的仿真功能，模拟无线信号在真实环境中的传播特性，包括路径损耗、衰落、阴影效应等物理现象。

## 核心类

### PhysicalLayer 类

#### 初始化参数
```python
class PhysicalLayer:
    def __init__(self, tx_power=20, frequency=2400, env='urban'):
        self.tx_power = tx_power      # 发射功率 (dBm)
        self.frequency = frequency    # 频率 (MHz)
        self.env = env               # 环境类型
```

**参数说明**：
- `tx_power`：发射功率，默认20dBm，范围通常为10-30dBm
- `frequency`：工作频率，默认2400MHz（2.4GHz WiFi）
- `env`：环境类型，可用于后续环境相关的参数调整

## 物理现象建模

### 1. 自由空间路径损耗 (Free Space Path Loss)

```python
def free_space_path_loss(self, distance):
    """计算自由空间路径损耗"""
    # FSPL = 20*log10(d) + 20*log10(f) - 27.55
    # d: 距离(米), f: 频率(MHz)
    loss = 20 * math.log10(distance) + 20 * math.log10(self.frequency) - 27.55
    return loss  # 单位: dB
```

**物理意义**：
- 理想自由空间中信号功率随距离的衰减
- 遵循平方反比定律：功率 ∝ 1/d²
- 频率越高，损耗越大

**应用场景**：
- 开阔地带的信号传播
- 视距(LOS)通信的基础损耗计算
- 其他损耗模型的参考基准

### 2. 瑞利衰落 (Rayleigh Fading)

```python
def rayleigh_fading(self):
    """模拟瑞利衰落"""
    fading = np.random.rayleigh(scale=2.0)
    return -fading  # 负值表示衰落损耗
```

**物理意义**：
- 模拟多径传播引起的快衰落
- 适用于非视距(NLOS)环境
- 信号幅度服从瑞利分布

**特点**：
- 随机性强，反映信号的快速变化
- scale参数控制衰落深度
- 通常导致信号功率降低

### 3. 阴影衰落 (Shadowing/Log-normal Fading)

```python
def shadowing(self):
    """模拟阴影衰落"""
    return random.gauss(0, 3)  # 均值0，标准差3dB的正态分布
```

**物理意义**：
- 模拟大尺度的慢衰落效应
- 由地形、建筑物等障碍物引起
- 功率变化服从对数正态分布

**参数设置**：
- 均值：0dB（无偏估计）
- 标准差：3dB（典型城市环境值）
- 可根据环境类型调整标准差

## 信道仿真

### 接收功率计算

```python
def compute_received_power(self, distance):
    """计算接收功率"""
    loss = self.free_space_path_loss(distance)
    fading = self.rayleigh_fading()
    shadow = self.shadowing()
    
    # 接收功率 = 发射功率 - 路径损耗 + 衰落 + 阴影
    received_power = self.tx_power - loss + fading + shadow
    return received_power
```

**计算公式**：
```
P_rx = P_tx - FSPL + Rayleigh + Shadowing
```

**各项贡献**：
- `P_tx`：发射功率（正值）
- `FSPL`：路径损耗（正值，表示损耗）
- `Rayleigh`：瑞利衰落（负值，表示额外损耗）
- `Shadowing`：阴影衰落（可正可负，均值为0）

### 信道成功判决

```python
def simulate_channel(self, distance, env_factor=1.0):
    """模拟信道传输成功与否"""
    received_power = self.compute_received_power(distance) * env_factor
    noise_floor = -90  # 噪声底 (dBm)
    
    if received_power > noise_floor + 10:  # 10dB余量
        return True   # 传输成功
    else:
        return False  # 传输失败
```

**判决准则**：
- **噪声底**：-90dBm（典型WiFi接收机噪声水平）
- **接收门限**：噪声底 + 10dB = -80dBm
- **环境因子**：允许外部调整环境影响

## 使用示例

### 基本使用
```python
# 创建物理层实例
phy = PhysicalLayer(tx_power=20, frequency=2400, env='urban')

# 计算特定距离的接收功率
distance = 10.0  # 10米
rx_power = phy.compute_received_power(distance)
print(f"接收功率: {rx_power:.2f} dBm")

# 判断传输是否成功
success = phy.simulate_channel(distance, env_factor=1.2)
print(f"传输状态: {'成功' if success else '失败'}")
```

### 距离-功率关系分析
```python
distances = np.linspace(1, 100, 100)  # 1-100米
powers = []

for d in distances:
    power = phy.compute_received_power(d)
    powers.append(power)

# 绘制功率-距离曲线
import matplotlib.pyplot as plt
plt.plot(distances, powers)
plt.xlabel('距离 (m)')
plt.ylabel('接收功率 (dBm)')
plt.title('功率-距离关系')
plt.grid(True)
plt.show()
```

### 成功率统计
```python
def calculate_success_rate(distance, num_trials=1000):
    """计算特定距离的传输成功率"""
    successes = 0
    for _ in range(num_trials):
        if phy.simulate_channel(distance):
            successes += 1
    return successes / num_trials

# 分析不同距离的成功率
distances = [5, 10, 20, 50, 100]
for d in distances:
    rate = calculate_success_rate(d)
    print(f"距离 {d}m: 成功率 {rate:.1%}")
```

## 参数配置

### 环境相关参数

#### 不同环境的典型参数
```python
ENV_PARAMS = {
    'indoor': {
        'shadowing_std': 4.0,    # 室内阴影标准差
        'rayleigh_scale': 1.5,   # 室内多径较弱
        'noise_floor': -85       # 室内噪声较低
    },
    'urban': {
        'shadowing_std': 6.0,    # 城市阴影标准差
        'rayleigh_scale': 2.0,   # 城市多径适中
        'noise_floor': -90       # 标准噪声水平
    },
    'rural': {
        'shadowing_std': 2.0,    # 乡村阴影标准差
        'rayleigh_scale': 1.0,   # 乡村多径较少
        'noise_floor': -95       # 乡村噪声很低
    }
}
```

### 频段相关参数

#### 2.4GHz vs 5GHz
```python
# 2.4GHz配置
phy_2g = PhysicalLayer(tx_power=20, frequency=2400)

# 5GHz配置  
phy_5g = PhysicalLayer(tx_power=23, frequency=5200)
```

**差异说明**：
- 5GHz频段路径损耗更大
- 5GHz穿透能力较弱
- 5GHz通常允许更高发射功率

## 高级功能

### 动态环境因子
```python
def dynamic_env_factor(device_position, ap_position):
    """根据设备和AP位置计算动态环境因子"""
    # 考虑障碍物、地形等因素
    distance = np.linalg.norm(np.array(device_position) - np.array(ap_position))
    
    # 简单的距离相关环境因子
    if distance < 10:
        return 1.2  # 近距离，环境影响小
    elif distance < 50:
        return 1.0  # 中距离，标准环境
    else:
        return 0.8  # 远距离，环境影响大
```

### 多径延迟扩展
```python
def multipath_delay_spread(self):
    """模拟多径延迟扩展"""
    # 典型室内RMS延迟扩展: 10-50ns
    # 典型室外RMS延迟扩展: 100-1000ns
    if self.env == 'indoor':
        return random.uniform(10e-9, 50e-9)  # 纳秒
    else:
        return random.uniform(100e-9, 1000e-9)
```

### 多普勒频移
```python
def doppler_shift(self, velocity):
    """计算多普勒频移"""
    # f_d = (v/c) * f_c
    c = 3e8  # 光速 m/s
    doppler = (velocity / c) * self.frequency * 1e6  # Hz
    return doppler
```

## 扩展与定制

### 自定义衰落模型
```python
class CustomPhysicalLayer(PhysicalLayer):
    def rician_fading(self, k_factor=3):
        """莱斯衰落模型"""
        # K因子表示直射分量与散射分量功率比
        los = np.sqrt(k_factor / (k_factor + 1))
        nlos = np.sqrt(1 / (k_factor + 1)) * (np.random.randn() + 1j * np.random.randn())
        amplitude = abs(los + nlos)
        return 20 * np.log10(amplitude)  # 转换为dB
```

### 频率相关建模
```python
def frequency_dependent_loss(self, distance, frequency):
    """频率相关的额外损耗"""
    # 高频信号的额外衰减
    extra_loss = 0
    if frequency > 3000:  # 3GHz以上
        extra_loss = (frequency - 3000) / 1000 * 2  # 每GHz增加2dB损耗
    return extra_loss
```

### 天线模型集成
```python
def antenna_gain(self, angle):
    """简单的定向天线增益模型"""
    # 假设主瓣方向为0度
    if abs(angle) < 30:  # 主瓣范围±30度
        return 10  # 10dB增益
    elif abs(angle) < 90:  # 副瓣范围
        return -3  # -3dB
    else:  # 后瓣
        return -20  # -20dB
```

## 性能优化

### 批量计算
```python
def batch_channel_simulation(self, distances, env_factors=None):
    """批量进行信道仿真"""
    if env_factors is None:
        env_factors = [1.0] * len(distances)
    
    results = []
    for dist, env_f in zip(distances, env_factors):
        success = self.simulate_channel(dist, env_f)
        results.append(success)
    
    return results
```

### 预计算查找表
```python
def build_loss_table(self, max_distance=200, step=1):
    """构建路径损耗查找表"""
    self.loss_table = {}
    for d in range(1, max_distance + 1, step):
        self.loss_table[d] = self.free_space_path_loss(d)
```

这个物理层模块为WiFi仿真系统提供了真实的信道条件模拟，使得生成的数据包能够反映实际无线环境中的传输特性。
