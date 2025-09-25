# main.py - Main Simulation Program

[简体中文](./zh-CN/main.py.md) | English

## Overview

`main.py` is the core entry file of the WiFi Probe Request simulation system, providing a complete interactive simulation environment and dataset generation functionality.

## Main Features

### 1. Interactive Configuration Interface
- Support for three dataset type selections:
  - **Multi-device Mode**: Simulate multiple device behaviors in network with device state switching
  - **Single Device Switchable Mode**: Simulate single device state changes (locked→awake→active)
  - **Single Device Static Mode**: Simulate single device fixed state behavior

### 2. Scenario Configuration System
- **High Mobility Scenario**: Auto-generated device density with strong mobility
- **Low Mobility High Density Scenario**: Many devices but weak mobility
- **Low Mobility Low Density Scenario**: Few devices and weak mobility

### 3. Device Management
- Support for multiple brand devices (Apple, Samsung, Xiaomi, Huawei, etc.)
- Flexible MAC address rotation strategies:
  - `per_burst`: Change MAC for each burst
  - `per_phase`: Change MAC on state transitions
  - `interval`: Change MAC at time intervals

### 4. Physical Layer Simulation
- Integrated physical layer module simulating realistic wireless channel conditions
- Support for path loss, fading, shadowing effects and other physical phenomena
- Configurable transmission power and environment factors

### 5. Event-Driven Simulation Engine
- Discrete event simulation based on event queues
- Support for device creation, deletion, state switching, packet transmission events
- Precise timestamp management and scheduling delay simulation

## Core Classes and Functions

### Simulator Class
```python
class Simulator:
    def __init__(self, out_file, avg_permanence_time, scene_params, dataset_type)
```
- **Function**: Core simulation engine class
- **Parameters**:
  - `out_file`: Output file prefix
  - `avg_permanence_time`: Average dwell time
  - `scene_params`: Scenario parameter dictionary
  - `dataset_type`: Dataset type

### Key Functions

#### generate_dataset_config(run)
- **Function**: Interactively generate dataset configuration
- **Returns**: Dataset type, simulation duration, device count, scenario parameters

#### run_simulation(sim_out_file, dataset_type, sim_duration_minutes, device_count, scene_params)
- **Function**: Execute complete simulation process
- **Output**:
  - `.pcap` file: Network packets
  - `.txt` file: Simulation logs
  - `_probe_ids.txt`: Device ID mapping
  - `_devices.csv`: Device information table

#### handle_event(event, simulator)
- **Function**: Handle simulation events
- **Supported Event Types**:
  - `create_device`: Create device
  - `delete_device`: Delete device
  - `change_phase`: State switching
  - `create_burst`: Create burst
  - `send_packet`: Send packet

## Configuration Parameters

### Scenario Parameters (scene_params)
```python
scene_params = {
    "creation_interval_multiplier": 1.0,    # Creation interval multiplier
    "burst_interval_multiplier": 1.0,       # Burst interval multiplier
    "dwell_multiplier": 1.0,                # Dwell time multiplier
    "env_factor": 1.0,                      # Environment factor
    "interference_prob": 0.0,               # Interference probability
    "qa_sample_rate": 0.0,                  # QA sampling rate
    "mac_rotation_mode": "per_burst",       # MAC rotation mode
    "mobility_speed_multiplier": 1.0        # Mobility multiplier
}
```

### Single Device Configuration
```python
scene_params.update({
    "single_vendor": "Apple",               # Device brand
    "single_model": "iPhone12",             # Device model
    "single_phase": 2                       # Initial state
})
```

## Output Formats

### PCAP File
- Standard network packet capture format
- Contains complete 802.11 Probe Request frames
- Analyzable with tools like Wireshark

### Device Information CSV
```csv
mac_address,device_name,device_id
aa:bb:cc:dd:ee:ff,Apple iPhone12,0
11:22:33:44:55:66,Samsung GalaxyS21,1
```

### Simulation Logs
Contains detailed simulation event records:
- Device creation/deletion times
- State switching records
- Packet transmission statistics
- Performance metrics summary

## Usage Examples

### Basic Usage
```bash
cd src
python main.py
```

### Batch Generation
```python
# Modify dataset_count variable in main.py
dataset_count = 5  # Generate 5 datasets
```

### Programmatic Invocation
```python
from main import run_simulation

# Configure parameters
scene_params = {
    "single_vendor": "Xiaomi",
    "single_model": "Mi10",
    "single_phase": 2,
    "mac_rotation_mode": "interval"
}

# Run simulation
run_simulation(
    sim_out_file="test_output",
    dataset_type="single_static", 
    sim_duration_minutes=5,
    device_count=1,
    scene_params=scene_params
)
```

## Performance Considerations

### Simulation Speed Optimization
- Use `realtime=False` to avoid real-time sleep
- Adjust `qa_sample_rate` to reduce QA overhead
- Set reasonable simulation duration and device count

### Memory Management
- Pay attention to memory usage for large-scale simulations
- Periodically clean event queues
- Use streaming writes to reduce memory footprint

## Extension Points

### Adding New Device Types
1. Add device parameters in `1.txt`
2. Add behavior configuration in `2.txt`
3. Update device selection logic

### Custom Scenarios
1. Extend `scene_params` parameters
2. Add processing logic in `handle_event`
3. Adjust physical layer parameters

### New Output Formats
1. Extend `run_simulation` function
2. Add data processing and export logic
3. Integrate external analysis tools
