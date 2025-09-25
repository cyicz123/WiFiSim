# shiyan.py - Simulation Data Quality Analysis Tool

[简体中文](./zh-CN/shiyan.py.md) | English

## Overview

`shiyan.py` is the data quality analysis module of the WiFi simulation system, used to evaluate the similarity between simulated data and real data, providing calculation and analysis functions for multiple key performance indicators.

## Core Metrics

### 1. MAC Address Related Metrics

#### MAC Address Distribution Normalized Entropy (MAE - MAC Address Entropy)
```python
def compute_mac_de(mac_list):
    """Calculate normalized entropy of MAC address distribution"""
    counts = Counter(mac_list)
    total = sum(counts.values())
    probs = np.array(list(counts.values())) / total
    entropy = -np.sum(probs * np.log(probs))
    normalized_entropy = entropy / np.log(len(counts))
    return normalized_entropy
```

**Meaning**: Measures randomness and diversity of MAC address distribution
- Range: [0, 1]
- 1 indicates completely random distribution
- 0 indicates all frames use the same MAC

#### MAC Change Rate (MCR - MAC Change Rate)
```python
def compute_mac_change_rate(macs, total_time):
    """Calculate MAC change rate: number of MAC address changes per unit time"""
    changes = sum(1 for i in range(1, len(macs)) if macs[i] != macs[i-1])
    return changes / total_time
```

**Meaning**: Reflects frequency of MAC address rotation
- Unit: changes/second
- High values indicate frequent MAC rotation
- Low values indicate relatively stable MAC addresses

#### Normalized Unique MAC Ratio (NUMR - Normalized Unique MAC Ratio)
```python
def compute_numr(macs):
    """Calculate normalized unique MAC ratio: unique MAC count / total frame count"""
    unique_count = len(set(macs))
    return unique_count / len(macs)
```

**Meaning**: Measures degree of MAC address uniqueness
- Range: (0, 1]
- 1 indicates each frame uses different MAC
- Close to 0 indicates many frames reuse same MAC

#### MAC Change Interval Variance (MCIV - MAC Change Interval Variance)
```python
def compute_mciv(timestamps, macs):
    """Calculate time interval variance of adjacent MAC changes"""
    intervals = []
    for i in range(1, len(macs)):
        if macs[i] != macs[i-1]:
            intervals.append(timestamps[i] - timestamps[i-1])
    return np.var(intervals) if len(intervals) >= 2 else 0
```

**Meaning**: Reflects stability of MAC rotation time intervals
- High variance indicates irregular rotation intervals
- Low variance indicates relatively fixed rotation intervals

### 2. Time Related Metrics

#### Average Update Cycle (T - Update Cycle)
```python
def compute_update_cycle(timestamps):
    """Calculate average adjacent frame time interval"""
    ts_sorted = sorted([float(ts) for ts in timestamps])
    diffs = np.diff(ts_sorted)
    return np.mean(diffs)
```

**Meaning**: Reflects Probe Request transmission frequency
- Unit: seconds
- Smaller values indicate high-frequency transmission
- Larger values indicate low-frequency transmission

## PCAP File Processing

### Data Extraction
```python
def process_pcap(pcap_file, segment_seconds):
    """Read PCAP file and analyze by time segments"""
    packets = rdpcap(pcap_file)
    data = []
    
    for pkt in packets:
        if pkt.haslayer(Dot11):
            if pkt.type == 0 and pkt.subtype == 4:  # Probe Request frames
                ts = pkt.time
                src_mac = pkt.addr2
                data.append((ts, src_mac))
```

**Functions**:
- Filter Probe Request frames (type=0, subtype=4)
- Extract timestamps and source MAC addresses
- Support time alignment processing

### Time Segment Analysis
```python
# Segment analysis by specified time length
segments = {}
for ts, mac in data_aligned:
    seg_idx = int(ts // segment_seconds)
    if seg_idx not in segments:
        segments[seg_idx] = {'timestamps': [], 'macs': []}
    segments[seg_idx]['timestamps'].append(ts)
    segments[seg_idx]['macs'].append(mac)
```

**Supported Time Segments**:
- 5 minutes (300 seconds)
- 10 minutes (600 seconds)
- 15 minutes (900 seconds)
- 20 minutes (1200 seconds)

## Quality Assessment

### MAC Random Cycle Accuracy (MRCA)
```python
def compute_mac_rca(T_sim, T_real):
    """Calculate MAC random cycle accuracy"""
    return 1 - abs(T_sim - T_real) / T_real
```

**Meaning**: Evaluate temporal characteristic accuracy of simulated data
- Range: (-∞, 1]
- 1 indicates perfect match
- Negative values indicate large deviation

### Comprehensive Quality Scoring
System evaluates simulation quality through comprehensive assessment of multiple metrics:

```python
# Example evaluation criteria
quality_thresholds = {
    "MCR_diff": 0.10,    # MCR relative error < 10%
    "NUMR_diff": 0.15,   # NUMR relative error < 15%
    "MCIV_diff": 0.20,   # MCIV relative error < 20%
    "MAE_diff": 0.12     # MAE relative error < 12%
}
```

## Usage Examples

### Basic Analysis Process
```python
# Define analysis time segments
segments = [300, 600, 900, 1200]  # 5, 10, 15, 20 minutes

# Real data and simulation data paths
real_pcap = "real_data.pcap"
sim_pcap = "simulation_output.pcap"

for seg_time in segments:
    print(f"=== Time Segment: {seg_time/60:.0f} minutes ===")
    
    # Analyze real data
    real_results = process_pcap(real_pcap, seg_time)
    
    # Analyze simulation data
    sim_results = process_pcap(sim_pcap, seg_time)
    
    # Calculate average values for each metric
    real_mcr_mean = np.mean([v['MCR'] for v in real_results.values()])
    sim_mcr_mean = np.mean([v['MCR'] for v in sim_results.values()])
    
    # Calculate accuracy
    mrca = compute_mac_rca(sim_mcr_mean, real_mcr_mean)
    
    print(f"Real MCR: {real_mcr_mean:.3f}")
    print(f"Sim MCR: {sim_mcr_mean:.3f}")
    print(f"MRCA: {mrca:.3f}")
```

### Batch Comparison Analysis
```python
# Compare multiple simulation results
sim_files = [
    "sim_run_1.pcap",
    "sim_run_2.pcap", 
    "sim_run_3.pcap"
]

results_summary = {}
for sim_file in sim_files:
    results = process_pcap(sim_file, 600)  # 10-minute segments
    # Calculate average metrics
    avg_metrics = calculate_average_metrics(results)
    results_summary[sim_file] = avg_metrics

# Generate comparison report
generate_comparison_report(results_summary)
```

## Output Format

### Console Output Example
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

### Result Interpretation

#### Excellent Simulation Metrics
- **MRCA > 0.90**: Highly similar temporal characteristics
- **MCR relative error < 10%**: Good MAC rotation frequency match
- **NUMR relative error < 15%**: Similar MAC uniqueness degree
- **MCIV relative error < 20%**: Similar rotation interval patterns

#### Metrics Needing Improvement
- **MRCA < 0.80**: Large temporal characteristic deviation
- **MCR relative error > 25%**: Obvious MAC rotation frequency difference
- **MAE relative error > 20%**: Large MAC distribution randomness difference

## Extension Functions

### Custom Metrics
```python
def compute_custom_metric(timestamps, macs, **kwargs):
    """Implement custom quality metrics"""
    # User-defined analysis logic
    pass

# Register to analysis process
register_metric("custom", compute_custom_metric)
```

### Visualization Support
```python
import matplotlib.pyplot as plt

def plot_metric_comparison(real_data, sim_data, metric_name):
    """Plot metric comparison chart"""
    plt.figure(figsize=(10, 6))
    plt.plot(real_data, label='Real Data', marker='o')
    plt.plot(sim_data, label='Simulated Data', marker='s')
    plt.xlabel('Time Segment')
    plt.ylabel(metric_name)
    plt.legend()
    plt.title(f'{metric_name} Comparison')
    plt.show()
```

### Report Generation
```python
def generate_quality_report(real_pcap, sim_pcap, output_file):
    """Generate detailed quality assessment report"""
    report = {
        'timestamp': datetime.now(),
        'files': {'real': real_pcap, 'simulated': sim_pcap},
        'metrics': {},
        'recommendations': []
    }
    
    # Analyze various metrics
    # Generate improvement suggestions
    # Output HTML/PDF report
```

## Performance Optimization

### Large File Processing
- Support streaming reading of large PCAP files
- Memory-efficient time segment processing
- Parallel computation of multiple metrics

### Caching Mechanism
- Cache PCAP parsing results
- Avoid repeated calculations on same data
- Support incremental analysis updates

### Configuration Options
```python
analysis_config = {
    'segment_sizes': [300, 600, 900, 1200],
    'metrics_enabled': ['MCR', 'NUMR', 'MCIV', 'MAE'],
    'output_format': 'detailed',  # 'summary' | 'detailed'
    'cache_results': True,
    'parallel_processing': True
}
```
