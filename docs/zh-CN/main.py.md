# main.py - 主仿真程序

## 概述

`main.py` 是WiFi Probe Request仿真系统的核心入口文件，提供了完整的交互式仿真环境和数据集生成功能。

## 主要功能

### 1. 交互式配置界面
- 支持三种数据集类型选择：
  - **多设备模式**：模拟多个设备在网络中的行为，支持设备状态切换
  - **单设备可切换模式**：模拟单个设备的状态变化（锁屏→亮屏→活动）
  - **单设备不可切换模式**：模拟单个设备的固定状态行为

### 2. 场景配置系统
- **高流动场景**：设备密度自动生成，移动性强
- **低流动高密度场景**：设备数量多但移动性弱
- **低流动低密度场景**：设备数量少且移动性弱

### 3. 设备管理
- 支持多种品牌设备（Apple、Samsung、Xiaomi、Huawei等）
- 灵活的MAC地址轮换策略：
  - `per_burst`：每次burst更换MAC
  - `per_phase`：每次状态切换时更换MAC
  - `interval`：按时间间隔更换MAC

### 4. 物理层仿真
- 集成物理层模块，模拟真实的无线信道条件
- 支持路径损耗、衰落、阴影效应等物理现象
- 可配置的发射功率和环境因子

### 5. 事件驱动仿真引擎
- 基于事件队列的离散事件仿真
- 支持设备创建、删除、状态切换、数据包发送等事件
- 精确的时间戳管理和调度延迟模拟

## 核心类和函数

### Simulator 类
```python
class Simulator:
    def __init__(self, out_file, avg_permanence_time, scene_params, dataset_type)
```
- **功能**：仿真引擎核心类
- **参数**：
  - `out_file`：输出文件前缀
  - `avg_permanence_time`：平均驻留时间
  - `scene_params`：场景参数字典
  - `dataset_type`：数据集类型

### 关键函数

#### generate_dataset_config(run)
- **功能**：交互式生成数据集配置
- **返回**：数据集类型、仿真时长、设备数量、场景参数

#### run_simulation(sim_out_file, dataset_type, sim_duration_minutes, device_count, scene_params)
- **功能**：执行完整的仿真流程
- **输出**：
  - `.pcap` 文件：网络数据包
  - `.txt` 文件：仿真日志
  - `_probe_ids.txt`：设备ID映射
  - `_devices.csv`：设备信息表

#### handle_event(event, simulator)
- **功能**：处理仿真事件
- **支持事件类型**：
  - `create_device`：创建设备
  - `delete_device`：删除设备  
  - `change_phase`：状态切换
  - `create_burst`：创建burst
  - `send_packet`：发送数据包

## 配置参数

### 场景参数 (scene_params)
```python
scene_params = {
    "creation_interval_multiplier": 1.0,    # 创建间隔倍率
    "burst_interval_multiplier": 1.0,       # burst间隔倍率
    "dwell_multiplier": 1.0,                # 驻留时间倍率
    "env_factor": 1.0,                      # 环境因子
    "interference_prob": 0.0,               # 干扰概率
    "qa_sample_rate": 0.0,                  # 质检采样率
    "mac_rotation_mode": "per_burst",       # MAC轮换模式
    "mobility_speed_multiplier": 1.0        # 移动性倍率
}
```

### 单设备配置
```python
scene_params.update({
    "single_vendor": "Apple",               # 设备品牌
    "single_model": "iPhone12",             # 设备型号
    "single_phase": 2                       # 初始状态
})
```

## 输出格式

### PCAP文件
- 标准的网络数据包捕获格式
- 包含完整的802.11 Probe Request帧
- 可用Wireshark等工具分析

### 设备信息CSV
```csv
mac_address,device_name,device_id
aa:bb:cc:dd:ee:ff,Apple iPhone12,0
11:22:33:44:55:66,Samsung GalaxyS21,1
```

### 仿真日志
包含详细的仿真事件记录：
- 设备创建/删除时间
- 状态切换记录
- 数据包发送统计
- 性能指标汇总

## 使用示例

### 基本使用
```bash
cd src
python main.py
```

### 批量生成
```python
# 修改main.py中的dataset_count变量
dataset_count = 5  # 生成5个数据集
```

### 程序化调用
```python
from main import run_simulation

# 配置参数
scene_params = {
    "single_vendor": "Xiaomi",
    "single_model": "Mi10",
    "single_phase": 2,
    "mac_rotation_mode": "interval"
}

# 运行仿真
run_simulation(
    sim_out_file="test_output",
    dataset_type="single_static", 
    sim_duration_minutes=5,
    device_count=1,
    scene_params=scene_params
)
```

## 性能考虑

### 仿真速度优化
- 使用 `realtime=False` 避免实时sleep
- 调整 `qa_sample_rate` 减少质检开销
- 合理设置仿真时长和设备数量

### 内存管理
- 大规模仿真时注意内存使用
- 定期清理事件队列
- 使用流式写入减少内存占用

## 扩展点

### 添加新设备类型
1. 在 `1.txt` 中添加设备参数
2. 在 `2.txt` 中添加行为配置
3. 更新设备选择逻辑

### 自定义场景
1. 扩展 `scene_params` 参数
2. 在 `handle_event` 中添加处理逻辑
3. 调整物理层参数

### 新的输出格式
1. 扩展 `run_simulation` 函数
2. 添加数据处理和导出逻辑
3. 集成外部分析工具
