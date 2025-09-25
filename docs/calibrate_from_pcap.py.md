# calibrate_from_pcap.py - Real Data-based Parameter Calibration Tool

[简体中文](./zh-CN/calibrate_from_pcap.py.md) | English

## Overview

`calibrate_from_pcap.py` is an automatic parameter calibration tool that analyzes real WiFi Probe Request packets, extracts key behavioral characteristics, and automatically generates corresponding simulation parameter configurations to make simulated data better match real device behavior.

## Core Functions

### 1. Real Data Analysis

#### PCAP File Parsing
```python
def read_probe_seq(pcap_path):
    """Extract Probe Request sequence from PCAP file"""
    pkts = rdpcap(str(pcap_path))
    seq = []
    
    for p in pkts:
        if p.haslayer(Dot11):
            d = p[Dot11]
            # Filter Probe Request frames (type=0, subtype=4)
            if getattr(d, "type", None) == 0 and getattr(d, "subtype", None) == 4:
                sa = getattr(d, "addr2", None)  # Source MAC address
                ts = float(getattr(p, "time", 0.0))  # Timestamp
                if sa is not None:
                    seq.append((ts - t0, sa))  # Time alignment
    
    return sorted(seq, key=lambda x: x[0])  # Sort by time
```

**Supported Data Formats**:
- Standard PCAP format files
- Contains 802.11 Probe Request frames
- Microsecond-precision timestamps

### 2. Key Metric Extraction

#### Comprehensive Metric Calculation
```python
def compute_metrics(seq):
    """Calculate key behavioral metrics from real data"""
    return {
        'MCR': mac_change_rate,        # MAC change rate (changes/minute)
        'NUMR': unique_mac_ratio,      # Unique MAC ratio
        'MCIV': change_interval_var,   # MAC change interval variance
        'avg_intra': avg_intra_burst,  # Average intra-burst interval
        'burst_sizes': burst_lengths,  # Burst length distribution
        'change_intervals': intervals  # MAC change interval sequence
    }
```

#### Burst Detection Algorithm
```python
# Burst segmentation threshold
INTRA_BURST_TH = 0.25  # 250ms

# Burst detection logic
burst_sizes = []
intra_gaps = []
cur_len = 1

for i in range(1, n):
    gap = times[i] - times[i-1]
    if gap <= INTRA_BURST_TH:
        cur_len += 1
        intra_gaps.append(gap)  # Record intra-burst interval
    else:
        burst_sizes.append(cur_len)  # Record burst length
        cur_len = 1
```

### 3. Parameter Inference Algorithms

#### Time Distribution Discretization
```python
def to_discrete_dist(samples, num_bins=6, clip_min=0.02, clip_max=120.0):
    """Convert continuous distribution to discrete probability distribution"""
    # Data cleaning and boundary processing
    arr = np.array(samples, dtype=float)
    arr = arr[(arr >= clip_min) & (arr <= clip_max)]
    
    # Histogram statistics
    hist, edges = np.histogram(arr, bins=num_bins)
    probs = hist / hist.sum()  # Normalization
    mids = 0.5 * (edges[1:] + edges[:-1])  # Interval midpoints
    
    # Format as dictionary
    return dict(zip(np.round(mids, 3), np.round(probs, 4)))
```

**Application Scenarios**:
- MAC rotation interval distribution → `prob_between_bursts`
- Intra-burst packet interval distribution → `prob_int_burst`
- State dwell time distribution → `state_dwell`
- Transmission jitter distribution → `jitter`

#### Burst Length Distribution
```python
def burst_len_dist(burst_sizes):
    """Calculate probability distribution of burst lengths"""
    if not burst_sizes:
        return {1.0: 0.2, 2.0: 0.5, 3.0: 0.3}  # Default distribution
    
    c = Counter(burst_sizes)
    total = sum(c.values())
    keys = sorted(c.keys())
    probs = [c[k] / total for k in keys]
    
    return {float(k): float(round(p, 4)) for k, p in zip(keys, probs)}
```

### 4. Configuration File Updates

#### 1.txt File Updates
```python
def upsert_1txt(lines, vendor, model, burst_len_map, randomization=1):
    """Update or insert device hardware parameters"""
    key = model.replace(" ", "").lower()
    blist = "/".join([f"{int(k)}:{p:.3f}" for k, p in burst_len_map.items()])
    
    new_line = f"{vendor},{model},{blist},{randomization}," \
               f"{vht_hex},{ext_hex},{ht_hex},{sup_rates},{ext_rates}"
    
    # Find existing entry or append new entry
    for i, line in enumerate(lines):
        if is_matching_device(line, key):
            lines[i] = new_line  # Update existing entry
            return lines
    
    lines.append(new_line)  # Add new entry
    return lines
```

#### 2.txt File Updates
```python
def upsert_2txt(lines, model, phase, prob_int_burst, prob_between, 
                state_dwell, jitter):
    """Update or insert device behavior parameters"""
    def fmt(d): 
        return "/".join([f"{k}:{v}" for k, v in d.items()])
    
    new_line = f"{model},{phase},{fmt(prob_int_burst)}," \
               f"{fmt(prob_between)},{fmt(state_dwell)},{fmt(jitter)}"
    
    # Find corresponding model+phase combination
    target_idx = find_phase_entry(lines, model, phase)
    if target_idx is not None:
        lines[target_idx] = new_line
    else:
        lines.append(new_line)
    
    return lines
```

### 5. Batch Data Processing

#### Multi-file Aggregated Analysis
```python
def aggregate_metrics(pcaps):
    """Perform aggregated analysis on multiple PCAP files"""
    MCRs, NUMRs, MCIVs = [], [], []
    all_burst_sizes, all_change_ints = [], []
    
    for pcap_path in pcaps:
        seq = read_probe_seq(pcap_path)
        metrics = compute_metrics(seq)
        
        # Collect various metrics
        MCRs.append(metrics["MCR"])
        NUMRs.append(metrics["NUMR"])
        MCIVs.append(metrics["MCIV"])
        all_burst_sizes += metrics["burst_sizes"]
        all_change_ints += metrics["change_intervals"]
    
    # Use median as robust estimate
    return {
        "MCR": float(np.median(MCRs)),
        "NUMR": float(np.median(NUMRs)),
        "MCIV": float(np.median(MCIVs)),
        "burst_sizes": all_burst_sizes,
        "change_intervals": all_change_ints
    }
```

## Calibration Process

### 1. Main Calibration Function
```python
def calibrate(vendor="Xiaomi", model="xiaomi_auto", 
              real_pcaps=None, apply_all_phases=True, write_files=True):
    """Execute complete parameter calibration process"""
    
    # Step 1: Aggregated analysis of real data
    target = aggregate_metrics([Path(p) for p in real_pcaps])
    print("=== Target (Real) Metrics ===")
    print(json.dumps(target, indent=2))
    
    # Step 2: Infer simulation parameters
    between_dist = to_discrete_dist(target["change_intervals"], 
                                   clip_min=1.0, clip_max=300.0)
    int_burst_dist = generate_intra_burst_dist(target["avg_intra"])
    burst_len_map = burst_len_dist(target["burst_sizes"])
    jitter_dist = generate_jitter_dist()
    state_dwell_dist = generate_state_dwell_dist()
    
    # Step 3: Update configuration files
    if write_files:
        update_config_files(vendor, model, burst_len_map, 
                           int_burst_dist, between_dist, 
                           state_dwell_dist, jitter_dist, apply_all_phases)
    
    return target
```

### 2. Parameter Generation Strategies

#### Rotation Interval Distribution
```python
# Generate rotation parameters based on real MAC change intervals
between_dist = to_discrete_dist(
    target["change_intervals"], 
    num_bins=6,           # Discretize into 6 intervals
    clip_min=1.0,         # Minimum interval 1 second
    clip_max=300.0        # Maximum interval 5 minutes
)
```

#### Intra-burst Interval Distribution
```python
# Generate distribution based on average intra-burst interval
intra_samples = np.random.normal(
    loc=max(0.01, target["avg_intra"]),      # Mean
    scale=max(0.005, 0.25 * target["avg_intra"]),  # Standard deviation
    size=120
)
int_burst_dist = to_discrete_dist(intra_samples, num_bins=4, 
                                 clip_min=0.01, clip_max=0.5)
```

#### Jitter Distribution Generation
```python
# Generate triangular distribution jitter parameters
jitter_samples = np.random.triangular(
    left=0.0,      # Minimum value
    mode=0.01,     # Mode
    right=0.05,    # Maximum value
    size=200
)
jitter_dist = to_discrete_dist(jitter_samples, num_bins=4)
```

### 3. Configuration Backup Mechanism
```python
def save_backup_and_write(path, lines):
    """Save backup and write new configuration"""
    bak_path = path.with_suffix(path.suffix + ".bak")
    if not bak_path.exists():
        shutil.copyfile(path, bak_path)  # First backup
    
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

## Usage Examples

### Basic Usage
```bash
cd src
python calibrate_from_pcap.py
```

### Custom Calibration
```python
# Specify real data files
pcap_files = [
    "device_A_capture.pcap",
    "device_B_capture.pcap",
    "device_C_capture.pcap"
]

# Execute calibration
target_metrics = calibrate(
    vendor="Xiaomi",
    model="Mi10_calibrated",
    real_pcaps=pcap_files,
    apply_all_phases=True,    # Apply to all states
    write_files=True          # Write to configuration files
)

print("Calibration completed, target metrics:", target_metrics)
```

### Verify Calibration Results
```python
# Run simulation validation after calibration
from main import run_simulation

# Run simulation using calibrated parameters
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

# Use shiyan.py to analyze gap between simulation results and real data
```

## Quality Control

### Data Validity Check
```python
def validate_pcap_data(pcap_path):
    """Validate PCAP data validity"""
    seq = read_probe_seq(pcap_path)
    
    if len(seq) < 10:
        return False, "Too little data, need at least 10 Probe Request frames"
    
    time_span = seq[-1][0] - seq[0][0]
    if time_span < 30:
        return False, "Time span too short, need at least 30 seconds"
    
    unique_macs = len(set(mac for _, mac in seq))
    if unique_macs < 2:
        return False, "Insufficient MAC address changes, may not be randomized device"
    
    return True, "Data valid"
```

### Parameter Reasonableness Check
```python
def validate_parameters(params):
    """Validate generated parameters are reasonable"""
    checks = []
    
    # Check inter-burst interval range
    between_intervals = list(params["prob_between_bursts"].keys())
    if max(between_intervals) > 600:  # 10 minutes
        checks.append("WARNING: Inter-burst interval too long")
    
    # Check intra-burst interval range
    intra_intervals = list(params["prob_int_burst"].keys())
    if min(intra_intervals) < 0.01:  # 10ms
        checks.append("WARNING: Intra-burst interval too short")
    
    # Check probability distribution normalization
    prob_sum = sum(params["prob_between_bursts"].values())
    if abs(prob_sum - 1.0) > 0.01:
        checks.append("ERROR: Probability distribution not normalized")
    
    return checks
```

### Calibration Result Evaluation
```python
def evaluate_calibration_quality(target_metrics, sim_metrics):
    """Evaluate calibration quality"""
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

## Advanced Features

### Multi-device Joint Calibration
```python
def multi_device_calibration(device_pcaps_map):
    """Perform joint calibration for multiple devices"""
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

### Incremental Calibration
```python
def incremental_calibration(existing_config, new_pcaps):
    """Perform incremental calibration based on new data"""
    # Load existing configuration
    current_params = load_existing_config(existing_config)
    
    # Analyze new data
    new_metrics = aggregate_metrics(new_pcaps)
    
    # Weighted fusion of old and new parameters
    updated_params = weighted_merge(current_params, new_metrics, alpha=0.3)
    
    return updated_params
```

### Automated Calibration Pipeline
```python
def automated_calibration_pipeline(data_directory):
    """Automated calibration pipeline"""
    # 1. Scan data directory
    pcap_files = discover_pcap_files(data_directory)
    
    # 2. Group by device type
    device_groups = group_by_device_type(pcap_files)
    
    # 3. Batch calibration
    for device_type, files in device_groups.items():
        calibrate_device_type(device_type, files)
    
    # 4. Generate calibration report
    generate_calibration_report()
```

This calibration tool is a key component for achieving high fidelity in the WiFi simulation system. By analyzing real data to automatically generate accurate simulation parameters, it greatly improves the credibility of simulation results.
