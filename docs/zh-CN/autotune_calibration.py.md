# autotune_calibration.py - 自动参数调优工具

## 概述

`autotune_calibration.py` 是WiFi仿真系统的智能参数调优工具，通过迭代优化算法自动调整仿真参数，使仿真结果的关键指标尽可能接近真实数据或目标值。

## 核心特性

### 1. 智能调优算法
- **多目标优化**：同时优化MCR、NUMR、MCIV等多个指标
- **自适应搜索**：根据历史结果动态调整搜索策略
- **早停机制**：达到目标阈值或连续无改进时自动停止
- **时间限制**：支持墙钟时间限制，避免无限运行

### 2. 快速仿真模式
- **非实时仿真**：关闭sleep操作，大幅提升仿真速度
- **精简输出**：减少不必要的日志输出
- **批量处理**：支持并行参数评估

### 3. 健壮的指标解析
- **多源解析**：支持文件解析和stdout解析
- **容错机制**：解析失败时提供兜底估算
- **格式兼容**：适配多种输出格式

## 核心组件

### 1. 参数配置类

#### SceneParams 数据类
```python
@dataclass
class SceneParams:
    # 基础控制参数
    realtime: bool = False              # 关键：非实时模式提升速度
    fixed_phase: int = 2                # 单设备固定相位
    allow_state_switch: bool = False    # 是否允许状态切换
    brand: Optional[str] = None         # 设备品牌
    model: Optional[str] = None         # 设备型号
    
    # 可调优参数
    scale_between: float = 1.0          # burst间隔缩放因子
    spread_between: float = 0.2         # burst间隔分布扩散度
    burst_gamma: float = 0.1            # burst特征参数
    
    # 性能优化参数
    avoid_bg_sleep: bool = True         # 避免后台sleep
    seed: Optional[int] = None          # 随机种子
```

### 2. 目标指标定义

#### 默认目标指标
```python
DEFAULT_TARGET = {
    "MCR": 0.4641,       # MAC变化率 (changes/second)
    "NUMR": 0.0326,      # 唯一MAC比例 (unique-mac/total)
    "MCIV": 1322905.0,   # MAC变化间隔方差
}
```

#### 参数搜索范围
```python
SCALE_BETWEEN_RANGE = (0.30, 2.50)    # burst间隔缩放范围
SPREAD_BETWEEN_RANGE = (0.05, 1.50)   # 分布扩散度范围
BURST_GAMMA_RANGE = (0.01, 0.60)      # burst参数范围
```

### 3. 误差评估系统

#### 相对误差计算
```python
def _safe_rel_err(sim_v: float, tgt_v: float, eps: float = 1e-12) -> float:
    """安全的相对误差计算，避免除零"""
    return abs(sim_v - tgt_v) / (abs(tgt_v) + eps)
```

#### 加权评分函数
```python
def score_error(sim: Dict[str, float], target: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    """计算加权总误差"""
    e_mcr = _safe_rel_err(sim.get("MCR", 0.0), target.get("MCR", 0.0))
    e_numr = _safe_rel_err(sim.get("NUMR", 0.0), target.get("NUMR", 0.0))
    e_mciv = _safe_rel_err(sim.get("MCIV", 0.0), target.get("MCIV", 0.0))
    
    # 加权组合
    total = W_MCR * e_mcr + W_NUMR * e_numr + W_MCIV * e_mciv
    return total, {"e_mcr": e_mcr, "e_numr": e_numr, "e_mciv": e_mciv}
```

#### 权重配置
```python
W_MCR = 0.5    # MCR权重
W_NUMR = 0.3   # NUMR权重
W_MCIV = 0.2   # MCIV权重
```

### 4. 接受阈值
```python
THRESH = {
    "MCR": 0.10,    # 10%相对误差
    "NUMR": 0.20,   # 20%相对误差
    "MCIV": 0.35,   # 35%相对误差
}

def is_good_enough(errors: Dict[str, float]) -> bool:
    """判断是否达到可接受阈值"""
    return all(errors[f"e_{k.lower()}"] <= v for k, v in THRESH.items())
```

## 仿真执行与解析

### 1. 仿真运行
```python
def run_one_simulation(sim_out_base: str, dataset_type: str, 
                      duration_min: int, scene: SceneParams, 
                      device_count: int = 1) -> Tuple[Dict[str, float], str]:
    """运行单次仿真并解析指标"""
    
    # 捕获stdout输出
    stdout_text, _ = _capture_stdout(
        main.run_simulation,
        sim_out_base, dataset_type, duration_min, device_count, 
        asdict(scene)
    )
    
    # 尝试从文件解析指标
    file_metrics = _parse_metrics_from_files(sim_out_base)
    if file_metrics:
        metrics = file_metrics
    else:
        # 回退到stdout解析
        metrics = _parse_metrics_from_stdout(stdout_text)
    
    return metrics, stdout_text
```

### 2. 多源指标解析

#### 文件解析优先
```python
def _parse_metrics_from_files(base_out: str) -> Optional[Dict[str, float]]:
    """从输出文件解析指标（优先级高）"""
    # 1. 尝试JSON格式统计文件
    stats_json = _try_read_json(f"{base_out}_stats.json")
    if stats_json and all(k in stats_json for k in ("MCR", "NUMR", "MCIV")):
        return extract_metrics_from_json(stats_json)
    
    # 2. 尝试文本日志文件
    log_text = _try_read_text(f"{base_out}.txt")
    if log_text:
        parsed = _parse_metrics_from_stdout(log_text)
        if any(parsed.values()):  # 至少有一项非零
            return parsed
    
    return None
```

#### stdout兜底解析
```python
def _parse_metrics_from_stdout(stdout_str: str) -> Dict[str, float]:
    """从stdout兜底解析指标"""
    m = {"MCR": 0.0, "NUMR": 0.0, "MCIV": 0.0}
    
    # 1. 直接统计行匹配
    direct = re.search(r"MCR\s*=\s*([0-9.]+).+?NUMR\s*=\s*([0-9.]+).+?MCIV\s*=\s*([0-9.]+)", 
                      stdout_str, re.S)
    if direct:
        m["MCR"] = float(direct.group(1))
        m["NUMR"] = float(direct.group(2))
        m["MCIV"] = float(direct.group(3))
        return m
    
    # 2. 从MAC/包统计估算NUMR
    macs = re.search(r"Total number of different MAC.*?:\s*([0-9]+)", stdout_str)
    pkts = re.search(r"Total number of packets.*?:\s*([0-9]+)", stdout_str)
    if macs and pkts:
        unique_mac = float(macs.group(1))
        total_pkt = float(pkts.group(1))
        if total_pkt > 0:
            m["NUMR"] = unique_mac / total_pkt
    
    # 3. 从时间戳估算MCIV（兜底近似）
    timestamps = extract_timestamps_from_stdout(stdout_str)
    if len(timestamps) >= 3:
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        if intervals:
            mean = sum(intervals) / len(intervals)
            var = sum((x - mean) ** 2 for x in intervals) / len(intervals)
            m["MCIV"] = var
    
    return m
```

## 自动调优主算法

### 1. 参数扰动策略
```python
def random_params_around(center: SceneParams, step_scale=0.25) -> SceneParams:
    """在当前最优点附近随机扰动"""
    def jitter(val, lo, hi):
        span = (hi - lo) * step_scale
        v = val + random.uniform(-span, span)
        return max(lo, min(hi, v))  # 边界约束
    
    return SceneParams(
        realtime=center.realtime,
        fixed_phase=center.fixed_phase,
        allow_state_switch=center.allow_state_switch,
        brand=center.brand,
        model=center.model,
        scale_between=jitter(center.scale_between, *SCALE_BETWEEN_RANGE),
        spread_between=jitter(center.spread_between, *SPREAD_BETWEEN_RANGE),
        burst_gamma=jitter(center.burst_gamma, *BURST_GAMMA_RANGE),
        avoid_bg_sleep=True,
        seed=None
    )
```

### 2. 主调优循环
```python
def autotune(target: Dict[str, float], dataset_type: str, duration_min: int,
             brand: Optional[str], model: Optional[str], max_iters: int,
             patience: int, walltime_sec: int, out_prefix: str) -> Dict[str, Any]:
    """主自动调优函数"""
    
    # 初始化
    best_scene = initial_scene_params(brand, model)
    best_metrics, best_errors, best_score = None, None, float("inf")
    no_improve = 0
    history = []
    
    t0 = time.time()
    
    for it in range(1, max_iters + 1):
        # 检查时间限制
        if time.time() - t0 > walltime_sec:
            print(f"[停止] 触发墙钟超时（{walltime_sec}s）")
            break
        
        # 生成候选参数
        scene = best_scene if best_metrics is None else random_params_around(best_scene)
        sim_tag = _unique_run_tag(f"{out_prefix}_iter{it}")
        
        try:
            # 运行仿真
            sim_metrics, stdout_s = run_one_simulation(
                sim_out_base=os.path.join("calib_runs", sim_tag),
                dataset_type=dataset_type,
                duration_min=duration_min,
                scene=scene
            )
            
            # 评估结果
            score, errs = score_error(sim_metrics, target)
            history.append({
                "iter": it, "scene": asdict(scene),
                "sim": sim_metrics, "errors": errs, "score": score
            })
            
            # 判断是否改进
            improved = score < best_score - 1e-9
            acceptable = is_good_enough(errs)
            
            if improved:
                print("=> 接受：更优")
                best_scene = scene
                best_metrics = sim_metrics
                best_errors = errs
                best_score = score
                no_improve = 0
            else:
                print("=> 拒绝：未改进")
                no_improve += 1
            
            # 检查停止条件
            if acceptable:
                print("[停止] 达到可接受阈值")
                break
            
            if no_improve >= patience:
                print(f"[停止] 连续{patience}轮无改进")
                break
                
        except Exception as e:
            print(f"[迭代{it}] 仿真异常：{repr(e)}")
            no_improve += 1
            if no_improve >= patience:
                break
    
    # 返回结果
    return {
        "best_params": asdict(best_scene),
        "best_metrics": best_metrics,
        "best_errors": best_errors,
        "best_score": best_score,
        "iters_done": len(history),
        "used_seconds": time.time() - t0,
        "history": history
    }
```

## 命令行界面

### 1. 参数配置
```python
def main_cli():
    """命令行主入口"""
    ap = argparse.ArgumentParser(description="自动标定/调参")
    
    # 目标和数据设置
    ap.add_argument("--target-json", help="目标指标JSON文件")
    ap.add_argument("--dataset-type", default="single_locked", 
                   help="数据集类型")
    ap.add_argument("--duration-min", type=int, default=3, 
                   help="每轮仿真时长（分钟）")
    ap.add_argument("--brand", help="设备品牌")
    ap.add_argument("--model", help="设备型号")
    
    # 调优控制参数
    ap.add_argument("--max-iters", type=int, default=12, 
                   help="最大迭代数")
    ap.add_argument("--patience", type=int, default=4, 
                   help="早停耐心轮次")
    ap.add_argument("--walltime-sec", type=int, default=900, 
                   help="总墙钟超时（秒）")
    
    # 初始参数
    ap.add_argument("--init-scale", type=float, default=1.0)
    ap.add_argument("--init-spread", type=float, default=0.2)
    ap.add_argument("--init-gamma", type=float, default=0.10)
    
    args = ap.parse_args()
    # ... 参数处理和调优执行
```

### 2. 使用示例

#### 基本调优
```bash
python autotune_calibration.py \
    --max-iters 15 \
    --patience 5 \
    --duration-min 3 \
    --dataset-type single_locked \
    --brand Xiaomi \
    --model xiaomi_auto
```

#### 使用自定义目标
```bash
# 创建目标文件 target.json
{
  "MCR": 0.35,
  "NUMR": 0.045,
  "MCIV": 980000.0
}

# 运行调优
python autotune_calibration.py \
    --target-json target.json \
    --max-iters 20 \
    --walltime-sec 1800
```

#### 快速调优模式
```bash
python autotune_calibration.py \
    --duration-min 2 \
    --max-iters 8 \
    --patience 3 \
    --walltime-sec 600
```

## 结果分析

### 1. 输出格式
```json
{
  "best_params": {
    "scale_between": 1.23,
    "spread_between": 0.18,
    "burst_gamma": 0.15,
    "realtime": false
  },
  "best_metrics": {
    "MCR": 0.441,
    "NUMR": 0.034,
    "MCIV": 1298765.0
  },
  "best_errors": {
    "e_mcr": 0.051,
    "e_numr": 0.043,
    "e_mciv": 0.018
  },
  "best_score": 0.038,
  "iters_done": 12,
  "used_seconds": 645.2,
  "history": [...]
}
```

### 2. 质量评估
```python
def evaluate_tuning_result(result):
    """评估调优结果质量"""
    errors = result["best_errors"]
    
    # 各指标达标情况
    mcr_ok = errors["e_mcr"] <= THRESH["MCR"]
    numr_ok = errors["e_numr"] <= THRESH["NUMR"]
    mciv_ok = errors["e_mciv"] <= THRESH["MCIV"]
    
    # 综合评级
    if all([mcr_ok, numr_ok, mciv_ok]):
        grade = "优秀"
    elif sum([mcr_ok, numr_ok, mciv_ok]) >= 2:
        grade = "良好"
    elif sum([mcr_ok, numr_ok, mciv_ok]) >= 1:
        grade = "一般"
    else:
        grade = "需改进"
    
    return {
        "grade": grade,
        "mcr_status": "达标" if mcr_ok else "未达标",
        "numr_status": "达标" if numr_ok else "未达标",
        "mciv_status": "达标" if mciv_ok else "未达标",
        "overall_score": result["best_score"]
    }
```

## 性能优化

### 1. 仿真加速
- **realtime=False**：关闭实时sleep，提升3-5倍速度
- **avoid_bg_sleep=True**：避免后台等待
- **精简日志**：减少不必要的输出
- **短时长仿真**：使用2-5分钟快速验证

### 2. 并行化支持
```python
def parallel_parameter_search(param_candidates, target, config):
    """并行参数搜索（未来扩展）"""
    from concurrent.futures import ProcessPoolExecutor
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(evaluate_single_param, param, target, config)
            for param in param_candidates
        ]
        
        results = [f.result() for f in futures]
    
    return sorted(results, key=lambda x: x['score'])
```

### 3. 缓存机制
```python
def cached_simulation(param_hash, sim_func, *args):
    """缓存仿真结果避免重复计算"""
    cache_file = f"cache/{param_hash}.json"
    
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    
    result = sim_func(*args)
    
    os.makedirs("cache", exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(result, f)
    
    return result
```

## 故障排除

### 1. 常见问题
- **仿真异常**：检查依赖文件(1.txt, 2.txt)是否存在
- **指标解析失败**：启用详细日志模式检查输出格式
- **收敛慢**：调整搜索范围和步长参数
- **内存不足**：减少仿真时长或设备数量

### 2. 调试模式
```bash
# 启用详细输出
python autotune_calibration.py --verbose \
    --max-iters 3 \
    --duration-min 1
```

这个自动调优工具是WiFi仿真系统的高级功能，能够显著提升仿真参数的准确性和仿真结果的可信度。
