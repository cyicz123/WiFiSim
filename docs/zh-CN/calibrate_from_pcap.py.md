# calibrate_from_pcap.py - 基于真实数据的参数标定工具

## 概述

`calibrate_from_pcap.py` 是一个自动参数标定工具，通过分析真实的WiFi Probe Request数据包，提取关键行为特征，并自动生成相应的仿真参数配置，使仿真数据能够更好地匹配真实设备行为。

## 核心功能

### 1. 真实数据分析

#### PCAP文件解析
```python
def read_probe_seq(pcap_path):
    """从PCAP文件中提取Probe Request序列"""
    pkts = rdpcap(str(pcap_path))
    seq = []
    
    for p in pkts:
        if p.haslayer(Dot11):
            d = p[Dot11]
            # 过滤Probe Request帧 (type=0, subtype=4)
            if getattr(d, "type", None) == 0 and getattr(d, "subtype", None) == 4:
                sa = getattr(d, "addr2", None)  # 源MAC地址
                ts = float(getattr(p, "time", 0.0))  # 时间戳
                if sa is not None:
                    seq.append((ts - t0, sa))  # 时间对齐
    
    return sorted(seq, key=lambda x: x[0])  # 按时间排序
```

**支持的数据格式**：
- 标准PCAP格式文件
- 包含802.11 Probe Request帧
- 时间戳精确到微秒级

### 2. 关键指标提取

#### 综合指标计算
```python
def compute_metrics(seq):
    """计算真实数据的关键行为指标"""
    return {
        'MCR': mac_change_rate,        # MAC变化率 (次/分钟)
        'NUMR': unique_mac_ratio,      # 唯一MAC比例
        'MCIV': change_interval_var,   # MAC变化间隔方差
        'avg_intra': avg_intra_burst,  # 平均burst内间隔
        'burst_sizes': burst_lengths,  # Burst长度分布
        'change_intervals': intervals  # MAC变化间隔序列
    }
```

#### Burst检测算法
```python
# Burst分割阈值
INTRA_BURST_TH = 0.25  # 250ms

# Burst检测逻辑
burst_sizes = []
intra_gaps = []
cur_len = 1

for i in range(1, n):
    gap = times[i] - times[i-1]
    if gap <= INTRA_BURST_TH:
        cur_len += 1
        intra_gaps.append(gap)  # 记录burst内间隔
    else:
        burst_sizes.append(cur_len)  # 记录burst长度
        cur_len = 1
```

### 3. 参数反推算法

#### 时间分布离散化
```python
def to_discrete_dist(samples, num_bins=6, clip_min=0.02, clip_max=120.0):
    """将连续分布转换为离散概率分布"""
    # 数据清理和边界处理
    arr = np.array(samples, dtype=float)
    arr = arr[(arr >= clip_min) & (arr <= clip_max)]
    
    # 直方图统计
    hist, edges = np.histogram(arr, bins=num_bins)
    probs = hist / hist.sum()  # 归一化
    mids = 0.5 * (edges[1:] + edges[:-1])  # 区间中点
    
    # 格式化为字典
    return dict(zip(np.round(mids, 3), np.round(probs, 4)))
```

**应用场景**：
- MAC轮换间隔分布 → `prob_between_bursts`
- Burst内包间隔分布 → `prob_int_burst`
- 状态驻留时间分布 → `state_dwell`
- 传输抖动分布 → `jitter`

#### Burst长度分布
```python
def burst_len_dist(burst_sizes):
    """计算burst长度的概率分布"""
    if not burst_sizes:
        return {1.0: 0.2, 2.0: 0.5, 3.0: 0.3}  # 默认分布
    
    c = Counter(burst_sizes)
    total = sum(c.values())
    keys = sorted(c.keys())
    probs = [c[k] / total for k in keys]
    
    return {float(k): float(round(p, 4)) for k, p in zip(keys, probs)}
```

### 4. 配置文件更新

#### 1.txt文件更新
```python
def upsert_1txt(lines, vendor, model, burst_len_map, randomization=1):
    """更新或插入设备硬件参数"""
    key = model.replace(" ", "").lower()
    blist = "/".join([f"{int(k)}:{p:.3f}" for k, p in burst_len_map.items()])
    
    new_line = f"{vendor},{model},{blist},{randomization}," \
               f"{vht_hex},{ext_hex},{ht_hex},{sup_rates},{ext_rates}"
    
    # 查找现有条目或追加新条目
    for i, line in enumerate(lines):
        if is_matching_device(line, key):
            lines[i] = new_line  # 更新现有条目
            return lines
    
    lines.append(new_line)  # 添加新条目
    return lines
```

#### 2.txt文件更新
```python
def upsert_2txt(lines, model, phase, prob_int_burst, prob_between, 
                state_dwell, jitter):
    """更新或插入设备行为参数"""
    def fmt(d): 
        return "/".join([f"{k}:{v}" for k, v in d.items()])
    
    new_line = f"{model},{phase},{fmt(prob_int_burst)}," \
               f"{fmt(prob_between)},{fmt(state_dwell)},{fmt(jitter)}"
    
    # 查找对应的model+phase组合
    target_idx = find_phase_entry(lines, model, phase)
    if target_idx is not None:
        lines[target_idx] = new_line
    else:
        lines.append(new_line)
    
    return lines
```

### 5. 批量数据处理

#### 多文件聚合分析
```python
def aggregate_metrics(pcaps):
    """对多个PCAP文件进行聚合分析"""
    MCRs, NUMRs, MCIVs = [], [], []
    all_burst_sizes, all_change_ints = [], []
    
    for pcap_path in pcaps:
        seq = read_probe_seq(pcap_path)
        metrics = compute_metrics(seq)
        
        # 收集各项指标
        MCRs.append(metrics["MCR"])
        NUMRs.append(metrics["NUMR"])
        MCIVs.append(metrics["MCIV"])
        all_burst_sizes += metrics["burst_sizes"]
        all_change_ints += metrics["change_intervals"]
    
    # 使用中位数作为鲁棒估计
    return {
        "MCR": float(np.median(MCRs)),
        "NUMR": float(np.median(NUMRs)),
        "MCIV": float(np.median(MCIVs)),
        "burst_sizes": all_burst_sizes,
        "change_intervals": all_change_ints
    }
```

## 标定流程

### 1. 主标定函数
```python
def calibrate(vendor="Xiaomi", model="xiaomi_auto", 
              real_pcaps=None, apply_all_phases=True, write_files=True):
    """执行完整的参数标定流程"""
    
    # Step 1: 聚合分析真实数据
    target = aggregate_metrics([Path(p) for p in real_pcaps])
    print("=== 目标(真实)指标 ===")
    print(json.dumps(target, indent=2))
    
    # Step 2: 反推仿真参数
    between_dist = to_discrete_dist(target["change_intervals"], 
                                   clip_min=1.0, clip_max=300.0)
    int_burst_dist = generate_intra_burst_dist(target["avg_intra"])
    burst_len_map = burst_len_dist(target["burst_sizes"])
    jitter_dist = generate_jitter_dist()
    state_dwell_dist = generate_state_dwell_dist()
    
    # Step 3: 更新配置文件
    if write_files:
        update_config_files(vendor, model, burst_len_map, 
                           int_burst_dist, between_dist, 
                           state_dwell_dist, jitter_dist, apply_all_phases)
    
    return target
```

### 2. 参数生成策略

#### 轮换间隔分布
```python
# 基于真实MAC变化间隔生成轮换参数
between_dist = to_discrete_dist(
    target["change_intervals"], 
    num_bins=6,           # 离散化为6个区间
    clip_min=1.0,         # 最小间隔1秒
    clip_max=300.0        # 最大间隔5分钟
)
```

#### Burst内间隔分布
```python
# 基于平均burst内间隔生成分布
intra_samples = np.random.normal(
    loc=max(0.01, target["avg_intra"]),      # 均值
    scale=max(0.005, 0.25 * target["avg_intra"]),  # 标准差
    size=120
)
int_burst_dist = to_discrete_dist(intra_samples, num_bins=4, 
                                 clip_min=0.01, clip_max=0.5)
```

#### 抖动分布生成
```python
# 生成三角分布的抖动参数
jitter_samples = np.random.triangular(
    left=0.0,      # 最小值
    mode=0.01,     # 众数
    right=0.05,    # 最大值
    size=200
)
jitter_dist = to_discrete_dist(jitter_samples, num_bins=4)
```

### 3. 配置备份机制
```python
def save_backup_and_write(path, lines):
    """保存备份并写入新配置"""
    bak_path = path.with_suffix(path.suffix + ".bak")
    if not bak_path.exists():
        shutil.copyfile(path, bak_path)  # 首次备份
    
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

## 使用示例

### 基本使用
```bash
cd src
python calibrate_from_pcap.py
```

### 自定义标定
```python
# 指定真实数据文件
pcap_files = [
    "device_A_capture.pcap",
    "device_B_capture.pcap",
    "device_C_capture.pcap"
]

# 执行标定
target_metrics = calibrate(
    vendor="Xiaomi",
    model="Mi10_calibrated",
    real_pcaps=pcap_files,
    apply_all_phases=True,    # 应用到所有状态
    write_files=True          # 写入配置文件
)

print("标定完成，目标指标:", target_metrics)
```

### 验证标定效果
```python
# 标定后运行仿真验证
from main import run_simulation

# 使用标定后的参数运行仿真
scene_params = {
    "single_vendor": "Xiaomi",
    "single_model": "Mi10_calibrated",
    "single_phase": 2,
    "mac_rotation_mode": "interval"
}

run_simulation(
    sim_out_file="calibration_test",
    dataset_type="single_switch",
    sim_duration_minutes=5,
    device_count=1,
    scene_params=scene_params
)

# 使用shiyan.py分析仿真结果与真实数据的差距
```

## 质量控制

### 数据有效性检查
```python
def validate_pcap_data(pcap_path):
    """验证PCAP数据的有效性"""
    seq = read_probe_seq(pcap_path)
    
    if len(seq) < 10:
        return False, "数据量太少，至少需要10个Probe Request帧"
    
    time_span = seq[-1][0] - seq[0][0]
    if time_span < 30:
        return False, "时间跨度太短，至少需要30秒"
    
    unique_macs = len(set(mac for _, mac in seq))
    if unique_macs < 2:
        return False, "MAC地址变化不足，可能不是随机化设备"
    
    return True, "数据有效"
```

### 参数合理性检查
```python
def validate_parameters(params):
    """验证生成的参数是否合理"""
    checks = []
    
    # 检查burst间隔范围
    between_intervals = list(params["prob_between_bursts"].keys())
    if max(between_intervals) > 600:  # 10分钟
        checks.append("WARNING: burst间隔过长")
    
    # 检查burst内间隔范围
    intra_intervals = list(params["prob_int_burst"].keys())
    if min(intra_intervals) < 0.01:  # 10ms
        checks.append("WARNING: burst内间隔过短")
    
    # 检查概率分布归一化
    prob_sum = sum(params["prob_between_bursts"].values())
    if abs(prob_sum - 1.0) > 0.01:
        checks.append("ERROR: 概率分布未归一化")
    
    return checks
```

### 标定结果评估
```python
def evaluate_calibration_quality(target_metrics, sim_metrics):
    """评估标定质量"""
    quality_scores = {}
    
    for metric in ['MCR', 'NUMR', 'MCIV']:
        if target_metrics[metric] != 0:
            relative_error = abs(sim_metrics[metric] - target_metrics[metric]) / target_metrics[metric]
            quality_scores[metric] = 1.0 - min(relative_error, 1.0)
        else:
            quality_scores[metric] = 1.0 if sim_metrics[metric] == 0 else 0.0
    
    overall_score = np.mean(list(quality_scores.values()))
    
    return {
        'individual_scores': quality_scores,
        'overall_score': overall_score,
        'quality_level': 'Excellent' if overall_score > 0.9 else
                        'Good' if overall_score > 0.8 else
                        'Fair' if overall_score > 0.7 else 'Poor'
    }
```

## 高级特性

### 多设备联合标定
```python
def multi_device_calibration(device_pcaps_map):
    """对多种设备进行联合标定"""
    results = {}
    
    for device_name, pcap_files in device_pcaps_map.items():
        vendor, model = parse_device_name(device_name)
        target = calibrate(
            vendor=vendor,
            model=model,
            real_pcaps=pcap_files,
            write_files=True
        )
        results[device_name] = target
    
    return results
```

### 增量标定
```python
def incremental_calibration(existing_config, new_pcaps):
    """基于新数据进行增量标定"""
    # 加载现有配置
    current_params = load_existing_config(existing_config)
    
    # 分析新数据
    new_metrics = aggregate_metrics(new_pcaps)
    
    # 加权融合旧参数和新参数
    updated_params = weighted_merge(current_params, new_metrics, alpha=0.3)
    
    return updated_params
```

### 自动化标定流水线
```python
def automated_calibration_pipeline(data_directory):
    """自动化标定流水线"""
    # 1. 扫描数据目录
    pcap_files = discover_pcap_files(data_directory)
    
    # 2. 按设备类型分组
    device_groups = group_by_device_type(pcap_files)
    
    # 3. 批量标定
    for device_type, files in device_groups.items():
        calibrate_device_type(device_type, files)
    
    # 4. 生成标定报告
    generate_calibration_report()
```

这个标定工具是WiFi仿真系统实现高保真度的关键组件，通过分析真实数据自动生成准确的仿真参数，大大提升了仿真结果的可信度。
