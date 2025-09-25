# WiFiSim 文档总览

本目录包含WiFi Probe Request仿真系统各个Python文件的详细功能文档。

## 文档列表

### 核心仿真模块

1. **[main.py](./main.py.md)** - 主仿真程序
   - 系统的核心入口，提供交互式配置界面
   - 实现完整的事件驱动仿真引擎
   - 支持多种数据集类型和场景配置
   - 生成标准格式的输出文件

2. **[user_space.py](./user_space.py.md)** - 用户空间设备模拟
   - Device类：设备行为模拟的核心
   - DeviceRates类：设备参数数据库管理
   - MAC地址生成与轮换策略
   - 设备移动性和状态切换模拟

3. **[kernel_driver.py](./kernel_driver.py.md)** - 内核驱动层802.11帧生成
   - 生成符合IEEE 802.11标准的Probe Request帧
   - RadioTap头部和802.11管理帧构建
   - 信息元素(Information Elements)处理
   - Burst生成和序列号管理

4. **[phy_layer.py](./phy_layer.py.md)** - 物理层仿真模块
   - 无线信道特性模拟
   - 路径损耗、衰落、阴影效应建模
   - 信道成功判决和RSSI计算
   - 支持多频段和环境配置

### 配置与标定工具

5. **[user_config.py](./user_config.py.md)** - 用户配置生成器
   - OUI数据预处理和转换
   - 设备参数数据库生成(1.txt, 2.txt)
   - 内置多厂商设备型号支持
   - 真实性参数优化

6. **[calibrate_from_pcap.py](./calibrate_from_pcap.py.md)** - 基于真实数据的参数标定工具
   - 真实PCAP文件分析和指标提取
   - 自动参数反推和配置文件更新
   - 支持批量数据处理和聚合分析
   - 质量控制和验证机制

7. **[autotune_calibration.py](./autotune_calibration.py.md)** - 自动参数调优工具
   - 智能多目标优化算法
   - 快速仿真模式和早停机制
   - 健壮的指标解析和容错处理
   - 命令行界面和批量处理支持

### 分析与工具模块

8. **[shiyan.py](./shiyan.py.md)** - 仿真数据质量分析工具
   - 关键性能指标计算(MCR, NUMR, MCIV, MAE等)
   - PCAP文件处理和时间段分析
   - 仿真质量评估和对比分析
   - 支持多种时间窗口和统计方法

9. **[capture_parsing.py](./capture_parsing.py.md)** - 数据包捕获与解析工具
   - 模拟帧捕获和RSSI分配
   - 详细的802.11帧解析
   - 信息元素逐一分析
   - 设备指纹识别和异常检测

## 系统架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   main.py       │    │  user_space.py   │    │ kernel_driver.py│
│  (仿真引擎)      │◄──►│   (设备模拟)      │◄──►│  (帧生成)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   phy_layer.py  │    │ user_config.py   │    │capture_parsing.py│
│   (物理层)       │    │  (配置生成)       │    │  (质量检查)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌──────────────────┐
                    │    shiyan.py     │
                    │   (质量分析)      │
                    └──────────────────┘
                                │
                                ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │calibrate_from_   │    │autotune_        │
                    │pcap.py (标定)    │◄──►│calibration.py   │
                    └──────────────────┘    │ (自动调优)       │
                                           └─────────────────┘
```

## 数据流程

### 1. 配置阶段
```
OUI数据 → user_config.py → 1.txt, 2.txt
真实PCAP → calibrate_from_pcap.py → 更新配置文件
```

### 2. 仿真阶段
```
配置文件 → user_space.py → Device实例
Device → kernel_driver.py → 802.11帧
802.11帧 → phy_layer.py → 信道模拟
最终帧 → main.py → PCAP输出
```

### 3. 分析阶段
```
PCAP输出 → shiyan.py → 质量指标
质量指标 → autotune_calibration.py → 参数优化
优化参数 → 重新仿真 → 迭代改进
```

## 关键概念

### 设备状态 (Phase)
- **0 - 锁屏状态**：设备屏幕关闭，低频扫描
- **1 - 亮屏状态**：设备屏幕开启，中频扫描  
- **2 - 活动状态**：设备正在使用，高频扫描

### MAC轮换策略
- **per_burst**：每次burst更换MAC地址
- **per_phase**：每次状态切换时更换MAC
- **interval**：按时间间隔定期更换MAC

### 关键指标
- **MCR (MAC Change Rate)**：MAC变化率，次/秒
- **NUMR (Normalized Unique MAC Ratio)**：唯一MAC比例
- **MCIV (MAC Change Interval Variance)**：MAC变化间隔方差
- **MAE (MAC Address Entropy)**：MAC地址熵

### 数据集类型
- **多设备模式**：模拟多个设备的网络环境
- **单设备可切换模式**：单设备支持状态转换
- **单设备不可切换模式**：单设备固定状态

## 快速导航

- **新用户入门**：先阅读[main.py文档](./main.py.md)了解系统概览
- **设备建模**：参考[user_space.py文档](./user_space.py.md)
- **帧格式定制**：查看[kernel_driver.py文档](./kernel_driver.py.md)
- **参数调优**：使用[autotune_calibration.py文档](./autotune_calibration.py.md)
- **质量评估**：参考[shiyan.py文档](./shiyan.py.md)

## 开发指南

### 添加新设备类型
1. 在`user_config.py`中添加设备参数
2. 更新`1.txt`和`2.txt`配置文件
3. 在`user_space.py`中测试设备行为

### 自定义物理层模型
1. 扩展`phy_layer.py`中的PhysicalLayer类
2. 实现新的衰落或传播模型
3. 在`main.py`中集成新模型

### 扩展分析指标
1. 在`shiyan.py`中添加新的指标计算函数
2. 更新`autotune_calibration.py`的优化目标
3. 修改评估和报告生成逻辑

## 故障排除

### 常见问题
- **配置文件缺失**：运行`user_config.py`生成初始配置
- **仿真速度慢**：使用`realtime=False`参数
- **指标解析失败**：检查输出文件格式和权限
- **参数不收敛**：调整搜索范围和优化策略

### 调试技巧
- 使用`capture_parsing.py`检查生成的帧格式
- 通过`shiyan.py`对比仿真和真实数据
- 启用详细日志模式查看执行过程
- 使用短时长仿真进行快速测试

## 贡献指南

欢迎为本项目贡献代码和文档。请确保：
1. 新功能有对应的文档说明
2. 代码风格与项目保持一致
3. 添加必要的测试用例
4. 更新相关的README文档

更多详细信息请参考项目根目录的README.md文件。
