# shiyan.py - 仿真数据质量分析工具

## 概述

`shiyan.py` 是WiFi仿真系统的数据质量分析模块，用于评估仿真数据与真实数据的相似度，提供多种关键性能指标的计算和分析功能。

## 核心指标

### 1. MAC地址相关指标

#### MAC地址分布归一化熵 (MAE - MAC Address Entropy)
```python
def compute_mac_de(mac_list):
    """计算MAC地址分布的归一化熵"""
    counts = Counter(mac_list)
    total = sum(counts.values())
    probs = np.array(list(counts.values())) / total
    entropy = -np.sum(probs * np.log(probs))
    normalized_entropy = entropy / np.log(len(counts))
    return normalized_entropy
```

**意义**：衡量MAC地址分布的随机性和多样性
- 值域：[0, 1]
- 1表示完全随机分布
- 0表示所有帧使用相同MAC

#### MAC变化率 (MCR - MAC Change Rate)
```python
def compute_mac_change_rate(macs, total_time):
    """计算MAC变化率：单位时间内MAC地址变化次数"""
    changes = sum(1 for i in range(1, len(macs)) if macs[i] != macs[i-1])
    return changes / total_time
```

**意义**：反映MAC地址轮换的频率
- 单位：次/秒
- 高值表示频繁的MAC轮换
- 低值表示MAC地址相对稳定

#### 归一化唯一MAC比例 (NUMR - Normalized Unique MAC Ratio)
```python
def compute_numr(macs):
    """计算归一化唯一MAC比例：唯一MAC数 / 总帧数"""
    unique_count = len(set(macs))
    return unique_count / len(macs)
```

**意义**：衡量MAC地址的唯一性程度
- 值域：(0, 1]
- 1表示每个帧都使用不同MAC
- 接近0表示大量帧重复使用相同MAC

#### MAC变化间隔方差 (MCIV - MAC Change Interval Variance)
```python
def compute_mciv(timestamps, macs):
    """计算MAC变化间隔的时间方差"""
    intervals = []
    for i in range(1, len(macs)):
        if macs[i] != macs[i-1]:
            intervals.append(timestamps[i] - timestamps[i-1])
    return np.var(intervals) if len(intervals) >= 2 else 0
```

**意义**：反映MAC轮换时间间隔的稳定性
- 高方差表示轮换间隔不规律
- 低方差表示轮换间隔相对固定

### 2. 时间相关指标

#### 平均更新周期 (T - Update Cycle)
```python
def compute_update_cycle(timestamps):
    """计算平均相邻帧时间间隔"""
    ts_sorted = sorted([float(ts) for ts in timestamps])
    diffs = np.diff(ts_sorted)
    return np.mean(diffs)
```

**意义**：反映Probe Request的发送频率
- 单位：秒
- 较小值表示高频发送
- 较大值表示低频发送

## PCAP文件处理

### 数据提取
```python
def process_pcap(pcap_file, segment_seconds):
    """读取PCAP文件并按时间段分析"""
    packets = rdpcap(pcap_file)
    data = []
    
    for pkt in packets:
        if pkt.haslayer(Dot11):
            if pkt.type == 0 and pkt.subtype == 4:  # Probe Request帧
                ts = pkt.time
                src_mac = pkt.addr2
                data.append((ts, src_mac))
```

**功能**：
- 过滤Probe Request帧（type=0, subtype=4）
- 提取时间戳和源MAC地址
- 支持时间对齐处理

### 时间段分析
```python
# 按指定时间长度分段分析
segments = {}
for ts, mac in data_aligned:
    seg_idx = int(ts // segment_seconds)
    if seg_idx not in segments:
        segments[seg_idx] = {'timestamps': [], 'macs': []}
    segments[seg_idx]['timestamps'].append(ts)
    segments[seg_idx]['macs'].append(mac)
```

**支持的时间段**：
- 5分钟 (300秒)
- 10分钟 (600秒)
- 15分钟 (900秒)
- 20分钟 (1200秒)

## 质量评估

### MAC随机周期准确率 (MRCA)
```python
def compute_mac_rca(T_sim, T_real):
    """计算MAC随机周期准确率"""
    return 1 - abs(T_sim - T_real) / T_real
```

**意义**：评估仿真数据的时间特征准确性
- 值域：(-∞, 1]
- 1表示完美匹配
- 负值表示偏差较大

### 综合质量评分
系统通过多个指标的综合评估来判断仿真质量：

```python
# 示例评估标准
quality_thresholds = {
    "MCR_diff": 0.10,    # MCR相对误差 < 10%
    "NUMR_diff": 0.15,   # NUMR相对误差 < 15%
    "MCIV_diff": 0.20,   # MCIV相对误差 < 20%
    "MAE_diff": 0.12     # MAE相对误差 < 12%
}
```

## 使用示例

### 基本分析流程
```python
# 定义分析时间段
segments = [300, 600, 900, 1200]  # 5, 10, 15, 20分钟

# 真实数据和仿真数据路径
real_pcap = "real_data.pcap"
sim_pcap = "simulation_output.pcap"

for seg_time in segments:
    print(f"=== Time Segment: {seg_time/60:.0f} minutes ===")
    
    # 分析真实数据
    real_results = process_pcap(real_pcap, seg_time)
    
    # 分析仿真数据
    sim_results = process_pcap(sim_pcap, seg_time)
    
    # 计算各项指标的平均值
    real_mcr_mean = np.mean([v['MCR'] for v in real_results.values()])
    sim_mcr_mean = np.mean([v['MCR'] for v in sim_results.values()])
    
    # 计算准确率
    mrca = compute_mac_rca(sim_mcr_mean, real_mcr_mean)
    
    print(f"Real MCR: {real_mcr_mean:.3f}")
    print(f"Sim MCR: {sim_mcr_mean:.3f}")
    print(f"MRCA: {mrca:.3f}")
```

### 批量比较分析
```python
# 比较多个仿真结果
sim_files = [
    "sim_run_1.pcap",
    "sim_run_2.pcap", 
    "sim_run_3.pcap"
]

results_summary = {}
for sim_file in sim_files:
    results = process_pcap(sim_file, 600)  # 10分钟段
    # 计算平均指标
    avg_metrics = calculate_average_metrics(results)
    results_summary[sim_file] = avg_metrics

# 生成比较报告
generate_comparison_report(results_summary)
```

## 输出格式

### 控制台输出示例
```
=== Time Segment: 10 minutes ===
Real Update Cycle (T): 2.45 s
Simulated Update Cycle (T): 2.38 s
MAC-RCA (MRCA): 0.97

Real MAC Entropy (MAE): 0.87
Simulated MAC Entropy (MAE): 0.84

Real MAC Change Rate (MCR): 0.42 changes/s
Simulated MAC Change Rate (MCR): 0.39 changes/s

Real Unique MAC Ratio (NUMR): 0.73
Simulated Unique MAC Ratio (NUMR): 0.71

Real MAC Change Interval Variance (MCIV): 1245.67
Simulated MAC Change Interval Variance (MCIV): 1198.34
```

### 结果解读

#### 优秀仿真指标
- **MRCA > 0.90**：时间特征高度相似
- **MCR相对误差 < 10%**：MAC轮换频率匹配良好
- **NUMR相对误差 < 15%**：MAC唯一性程度相近
- **MCIV相对误差 < 20%**：轮换间隔模式相似

#### 需要改进的指标
- **MRCA < 0.80**：时间特征偏差较大
- **MCR相对误差 > 25%**：MAC轮换频率差异明显
- **MAE相对误差 > 20%**：MAC分布随机性差异较大

## 扩展功能

### 自定义指标
```python
def compute_custom_metric(timestamps, macs, **kwargs):
    """实现自定义质量指标"""
    # 用户自定义的分析逻辑
    pass

# 注册到分析流程
register_metric("custom", compute_custom_metric)
```

### 可视化支持
```python
import matplotlib.pyplot as plt

def plot_metric_comparison(real_data, sim_data, metric_name):
    """绘制指标对比图"""
    plt.figure(figsize=(10, 6))
    plt.plot(real_data, label='Real Data', marker='o')
    plt.plot(sim_data, label='Simulated Data', marker='s')
    plt.xlabel('Time Segment')
    plt.ylabel(metric_name)
    plt.legend()
    plt.title(f'{metric_name} Comparison')
    plt.show()
```

### 报告生成
```python
def generate_quality_report(real_pcap, sim_pcap, output_file):
    """生成详细的质量评估报告"""
    report = {
        'timestamp': datetime.now(),
        'files': {'real': real_pcap, 'simulated': sim_pcap},
        'metrics': {},
        'recommendations': []
    }
    
    # 分析各项指标
    # 生成改进建议
    # 输出HTML/PDF报告
```

## 性能优化

### 大文件处理
- 支持流式读取大型PCAP文件
- 内存高效的时间段处理
- 并行计算多个指标

### 缓存机制
- 缓存PCAP解析结果
- 避免重复计算相同数据
- 支持增量分析更新

### 配置选项
```python
analysis_config = {
    'segment_sizes': [300, 600, 900, 1200],
    'metrics_enabled': ['MCR', 'NUMR', 'MCIV', 'MAE'],
    'output_format': 'detailed',  # 'summary' | 'detailed'
    'cache_results': True,
    'parallel_processing': True
}
```
