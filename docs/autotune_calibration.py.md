# autotune_calibration.py - Automatic Parameter Tuning Tool

[简体中文](./zh-CN/autotune_calibration.py.md) | English

## Overview

`autotune_calibration.py` is an intelligent parameter tuning tool for the WiFi simulation system that automatically adjusts simulation parameters through iterative optimization algorithms to make simulation results' key metrics as close as possible to real data or target values.

## Core Features

### 1. Intelligent Tuning Algorithm
- **Multi-objective Optimization**: Simultaneously optimize MCR, NUMR, MCIV and other metrics
- **Adaptive Search**: Dynamically adjust search strategy based on historical results
- **Early Stopping**: Automatically stop when reaching target thresholds or consecutive non-improvements
- **Time Limits**: Support wall-clock time limits to avoid infinite running

### 2. Fast Simulation Mode
- **Non-real-time Simulation**: Disable sleep operations for significant simulation speed improvement
- **Streamlined Output**: Reduce unnecessary log output
- **Batch Processing**: Support parallel parameter evaluation

### 3. Robust Metric Parsing
- **Multi-source Parsing**: Support both file parsing and stdout parsing
- **Error Tolerance**: Provide fallback estimation when parsing fails
- **Format Compatibility**: Adapt to multiple output formats

## Core Components

### 1. Parameter Configuration Class

#### SceneParams Data Class
```python
@dataclass
class SceneParams:
    # Basic control parameters
    realtime: bool = False              # Key: Non-real-time mode for speed boost
    fixed_phase: int = 2                # Single device fixed phase
    allow_state_switch: bool = False    # Whether to allow state switching
    brand: Optional[str] = None         # Device brand
    model: Optional[str] = None         # Device model
    
    # Tunable parameters
    scale_between: float = 1.0          # Inter-burst interval scaling factor
    spread_between: float = 0.2         # Inter-burst interval distribution spread
    burst_gamma: float = 0.1            # Burst characteristic parameter
    
    # Performance optimization parameters
    avoid_bg_sleep: bool = True         # Avoid background sleep
    seed: Optional[int] = None          # Random seed
```

### 2. Target Metric Definition

#### Default Target Metrics
```python
DEFAULT_TARGET = {
    "MCR": 0.4641,       # MAC change rate (changes/second)
    "NUMR": 0.0326,      # Unique MAC ratio (unique-mac/total)
    "MCIV": 1322905.0,   # MAC change interval variance
}
```

#### Parameter Search Ranges
```python
SCALE_BETWEEN_RANGE = (0.30, 2.50)    # Inter-burst interval scaling range
SPREAD_BETWEEN_RANGE = (0.05, 1.50)   # Distribution spread range
BURST_GAMMA_RANGE = (0.01, 0.60)      # Burst parameter range
```

### 3. Error Assessment System

#### Relative Error Calculation
```python
def _safe_rel_err(sim_v: float, tgt_v: float, eps: float = 1e-12) -> float:
    """Safe relative error calculation, avoiding division by zero"""
    return abs(sim_v - tgt_v) / (abs(tgt_v) + eps)
```

#### Weighted Scoring Function
```python
def score_error(sim: Dict[str, float], target: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    """Calculate weighted total error"""
    e_mcr = _safe_rel_err(sim.get("MCR", 0.0), target.get("MCR", 0.0))
    e_numr = _safe_rel_err(sim.get("NUMR", 0.0), target.get("NUMR", 0.0))
    e_mciv = _safe_rel_err(sim.get("MCIV", 0.0), target.get("MCIV", 0.0))
    
    # Weighted combination
    total = W_MCR * e_mcr + W_NUMR * e_numr + W_MCIV * e_mciv
    return total, {"e_mcr": e_mcr, "e_numr": e_numr, "e_mciv": e_mciv}
```

#### Weight Configuration
```python
W_MCR = 0.5    # MCR weight
W_NUMR = 0.3   # NUMR weight
W_MCIV = 0.2   # MCIV weight
```

### 4. Acceptance Thresholds
```python
THRESH = {
    "MCR": 0.10,    # 10% relative error
    "NUMR": 0.20,   # 20% relative error
    "MCIV": 0.35,   # 35% relative error
}

def is_good_enough(errors: Dict[str, float]) -> bool:
    """Check if acceptable thresholds are reached"""
    return all(errors[f"e_{k.lower()}"] <= v for k, v in THRESH.items())
```

## Simulation Execution and Parsing

### 1. Simulation Execution
```python
def run_one_simulation(sim_out_base: str, dataset_type: str, 
                      duration_min: int, scene: SceneParams, 
                      device_count: int = 1) -> Tuple[Dict[str, float], str]:
    """Run single simulation and parse metrics"""
    
    # Capture stdout output
    stdout_text, _ = _capture_stdout(
        main.run_simulation,
        sim_out_base, dataset_type, duration_min, device_count, 
        asdict(scene)
    )
    
    # Try to parse metrics from files first
    file_metrics = _parse_metrics_from_files(sim_out_base)
    if file_metrics:
        metrics = file_metrics
    else:
        # Fallback to stdout parsing
        metrics = _parse_metrics_from_stdout(stdout_text)
    
    return metrics, stdout_text
```

### 2. Multi-source Metric Parsing

#### File Parsing Priority
```python
def _parse_metrics_from_files(base_out: str) -> Optional[Dict[str, float]]:
    """Parse metrics from output files (higher priority)"""
    # 1. Try JSON format statistics file
    stats_json = _try_read_json(f"{base_out}_stats.json")
    if stats_json and all(k in stats_json for k in ("MCR", "NUMR", "MCIV")):
        return extract_metrics_from_json(stats_json)
    
    # 2. Try text log file
    log_text = _try_read_text(f"{base_out}.txt")
    if log_text:
        parsed = _parse_metrics_from_stdout(log_text)
        if any(parsed.values()):  # At least one non-zero item
            return parsed
    
    return None
```

#### Stdout Fallback Parsing
```python
def _parse_metrics_from_stdout(stdout_str: str) -> Dict[str, float]:
    """Parse metrics from stdout as fallback"""
    m = {"MCR": 0.0, "NUMR": 0.0, "MCIV": 0.0}
    
    # 1. Direct statistics line matching
    direct = re.search(r"MCR\s*=\s*([0-9.]+).+?NUMR\s*=\s*([0-9.]+).+?MCIV\s*=\s*([0-9.]+)", 
                      stdout_str, re.S)
    if direct:
        m["MCR"] = float(direct.group(1))
        m["NUMR"] = float(direct.group(2))
        m["MCIV"] = float(direct.group(3))
        return m
    
    # 2. Estimate NUMR from MAC/packet statistics
    macs = re.search(r"Total number of different MAC.*?:\s*([0-9]+)", stdout_str)
    pkts = re.search(r"Total number of packets.*?:\s*([0-9]+)", stdout_str)
    if macs and pkts:
        unique_mac = float(macs.group(1))
        total_pkt = float(pkts.group(1))
        if total_pkt > 0:
            m["NUMR"] = unique_mac / total_pkt
    
    # 3. Estimate MCIV from timestamps (fallback approximation)
    timestamps = extract_timestamps_from_stdout(stdout_str)
    if len(timestamps) >= 3:
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        if intervals:
            mean = sum(intervals) / len(intervals)
            var = sum((x - mean) ** 2 for x in intervals) / len(intervals)
            m["MCIV"] = var
    
    return m
```

## Automatic Tuning Main Algorithm

### 1. Parameter Perturbation Strategy
```python
def random_params_around(center: SceneParams, step_scale=0.25) -> SceneParams:
    """Random perturbation around current optimal point"""
    def jitter(val, lo, hi):
        span = (hi - lo) * step_scale
        v = val + random.uniform(-span, span)
        return max(lo, min(hi, v))  # Boundary constraints
    
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

### 2. Main Tuning Loop
```python
def autotune(target: Dict[str, float], dataset_type: str, duration_min: int,
             brand: Optional[str], model: Optional[str], max_iters: int,
             patience: int, walltime_sec: int, out_prefix: str) -> Dict[str, Any]:
    """Main automatic tuning function"""
    
    # Initialize
    best_scene = initial_scene_params(brand, model)
    best_metrics, best_errors, best_score = None, None, float("inf")
    no_improve = 0
    history = []
    
    t0 = time.time()
    
    for it in range(1, max_iters + 1):
        # Check time limit
        if time.time() - t0 > walltime_sec:
            print(f"[Stop] Wall-clock timeout ({walltime_sec}s)")
            break
        
        # Generate candidate parameters
        scene = best_scene if best_metrics is None else random_params_around(best_scene)
        sim_tag = _unique_run_tag(f"{out_prefix}_iter{it}")
        
        try:
            # Run simulation
            sim_metrics, stdout_s = run_one_simulation(
                sim_out_base=os.path.join("calib_runs", sim_tag),
                dataset_type=dataset_type,
                duration_min=duration_min,
                scene=scene
            )
            
            # Evaluate results
            score, errs = score_error(sim_metrics, target)
            history.append({
                "iter": it, "scene": asdict(scene),
                "sim": sim_metrics, "errors": errs, "score": score
            })
            
            # Check if improved
            improved = score < best_score - 1e-9
            acceptable = is_good_enough(errs)
            
            if improved:
                print("=> Accept: Better")
                best_scene = scene
                best_metrics = sim_metrics
                best_errors = errs
                best_score = score
                no_improve = 0
            else:
                print("=> Reject: No improvement")
                no_improve += 1
            
            # Check stopping conditions
            if acceptable:
                print("[Stop] Reached acceptable thresholds")
                break
            
            if no_improve >= patience:
                print(f"[Stop] {patience} consecutive rounds without improvement")
                break
                
        except Exception as e:
            print(f"[Iteration {it}] Simulation exception: {repr(e)}")
            no_improve += 1
            if no_improve >= patience:
                break
    
    # Return results
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

## Command Line Interface

### 1. Parameter Configuration
```python
def main_cli():
    """Command line main entry"""
    ap = argparse.ArgumentParser(description="Automatic calibration/tuning")
    
    # Target and data settings
    ap.add_argument("--target-json", help="Target metrics JSON file")
    ap.add_argument("--dataset-type", default="single_locked", 
                   help="Dataset type")
    ap.add_argument("--duration-min", type=int, default=3, 
                   help="Simulation duration per round (minutes)")
    ap.add_argument("--brand", help="Device brand")
    ap.add_argument("--model", help="Device model")
    
    # Tuning control parameters
    ap.add_argument("--max-iters", type=int, default=12, 
                   help="Maximum iterations")
    ap.add_argument("--patience", type=int, default=4, 
                   help="Early stopping patience rounds")
    ap.add_argument("--walltime-sec", type=int, default=900, 
                   help="Total wall-clock timeout (seconds)")
    
    # Initial parameters
    ap.add_argument("--init-scale", type=float, default=1.0)
    ap.add_argument("--init-spread", type=float, default=0.2)
    ap.add_argument("--init-gamma", type=float, default=0.10)
    
    args = ap.parse_args()
    # ... parameter processing and tuning execution
```

### 2. Usage Examples

#### Basic Tuning
```bash
python autotune_calibration.py \
    --max-iters 15 \
    --patience 5 \
    --duration-min 3 \
    --dataset-type single_locked \
    --brand Xiaomi \
    --model xiaomi_auto
```

#### Using Custom Target
```bash
# Create target file target.json
{
  "MCR": 0.35,
  "NUMR": 0.045,
  "MCIV": 980000.0
}

# Run tuning
python autotune_calibration.py \
    --target-json target.json \
    --max-iters 20 \
    --walltime-sec 1800
```

#### Fast Tuning Mode
```bash
python autotune_calibration.py \
    --duration-min 2 \
    --max-iters 8 \
    --patience 3 \
    --walltime-sec 600
```

## Result Analysis

### 1. Output Format
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

### 2. Quality Assessment
```python
def evaluate_tuning_result(result):
    """Evaluate tuning result quality"""
    errors = result["best_errors"]
    
    # Metric compliance status
    mcr_ok = errors["e_mcr"] <= THRESH["MCR"]
    numr_ok = errors["e_numr"] <= THRESH["NUMR"]
    mciv_ok = errors["e_mciv"] <= THRESH["MCIV"]
    
    # Overall rating
    if all([mcr_ok, numr_ok, mciv_ok]):
        grade = "Excellent"
    elif sum([mcr_ok, numr_ok, mciv_ok]) >= 2:
        grade = "Good"
    elif sum([mcr_ok, numr_ok, mciv_ok]) >= 1:
        grade = "Fair"
    else:
        grade = "Needs Improvement"
    
    return {
        "grade": grade,
        "mcr_status": "Compliant" if mcr_ok else "Non-compliant",
        "numr_status": "Compliant" if numr_ok else "Non-compliant",
        "mciv_status": "Compliant" if mciv_ok else "Non-compliant",
        "overall_score": result["best_score"]
    }
```

## Performance Optimization

### 1. Simulation Acceleration
- **realtime=False**: Disable real-time sleep for 3-5x speed improvement
- **avoid_bg_sleep=True**: Avoid background waiting
- **Streamlined logging**: Reduce unnecessary output
- **Short duration simulation**: Use 2-5 minutes for quick validation

### 2. Parallelization Support
```python
def parallel_parameter_search(param_candidates, target, config):
    """Parallel parameter search (future extension)"""
    from concurrent.futures import ProcessPoolExecutor
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(evaluate_single_param, param, target, config)
            for param in param_candidates
        ]
        
        results = [f.result() for f in futures]
    
    return sorted(results, key=lambda x: x['score'])
```

### 3. Caching Mechanism
```python
def cached_simulation(param_hash, sim_func, *args):
    """Cache simulation results to avoid repeated calculations"""
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

## Troubleshooting

### 1. Common Issues
- **Simulation exceptions**: Check if dependency files (1.txt, 2.txt) exist
- **Metric parsing failure**: Enable verbose logging mode to check output format
- **Slow convergence**: Adjust search range and step size parameters
- **Memory shortage**: Reduce simulation duration or device count

### 2. Debug Mode
```bash
# Enable verbose output
python autotune_calibration.py --verbose \
    --max-iters 3 \
    --duration-min 1
```

This automatic tuning tool is an advanced feature of the WiFi simulation system that can significantly improve the accuracy of simulation parameters and the credibility of simulation results.
