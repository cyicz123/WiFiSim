# user_config.py - User Configuration Generator

[简体中文](./zh-CN/user_config.py.md) | English

## Overview

`user_config.py` is the configuration file generator for the WiFi simulation system, responsible for creating and maintaining device parameter databases, including OUI data preprocessing, device configuration file generation, and other functions.

## Main Features

### 1. OUI Data Preprocessing

#### OUI Extraction and Conversion
```python
# Extract vendor information from IEEE OUI database
with open('oui.txt', encoding='utf-8', errors='replace') as f:
    # Process raw OUI file
    # Extract hexadecimal OUI and vendor names
    # Generate oui_hex.txt file
```

**Input File**: `oui.txt` - IEEE official OUI database
**Output File**: `oui_hex.txt` - Processed OUI mapping table

#### Format Conversion
- Extract key information from complex IEEE format
- Standardize OUI format to `XX:XX:XX` form
- Build fast index from vendor names to OUIs

### 2. Device Configuration File Generation

#### 1.txt - Device Hardware Parameter Configuration

**File Structure**:
```
# vendor, device_name, burst_lengths, mac_policy, VHT_cap, ext_cap, HT_cap, rates, ext_rates
```

**Field Descriptions**:
- `vendor`: Device vendor name
- `device_name`: Specific device model
- `burst_lengths`: Burst length probability distribution (format: `1:0.2/2:0.5/3:0.3`)
- `mac_policy`: MAC address policy (0-3)
- `VHT_cap`: VHT capability field (hexadecimal, "?" means not supported)
- `ext_cap`: Extended capability field (hexadecimal)
- `HT_cap`: HT capability field (hexadecimal)
- `rates`: Supported rates (hexadecimal encoded)
- `ext_rates`: Extended supported rates (hexadecimal encoded)

#### 2.txt - Device Behavior Parameter Configuration

**File Structure**:
```
# device_name, Phase, intra_burst_interval, inter_burst_interval, state_dwell, jitter
```

**Field Descriptions**:
- `device_name`: Device model
- `Phase`: Device state (0=locked, 1=awake, 2=active)
- `intra_burst_interval`: Intra-burst packet interval distribution
- `inter_burst_interval`: Inter-burst interval distribution
- `state_dwell`: State dwell time distribution
- `jitter`: Packet interval jitter distribution

## Built-in Device Database

### Supported Vendors and Devices

#### Major Vendors
```python
vendor_device_map = {
    'OnePlus': ['nord 5g', 'one plus9pro', 'one plus9rt', ...],
    'Samsung': ['note20ultra', 'galaxys21', 'galaxys20fe', ...],
    'Xiaomi': ['note8t', 'mi9lite', 'mi10lite', ...],
    'Huawei': ['p9lite', 'p40lite', 'p30lite', ...],
    'Lenovo': ['think pad x13gen1', 'think pad x1yoga', ...],
    'OPPO': ['find x3pro', 'find x5pro', ...],
    'vivo': ['x60', 'x60pro', 'x60t', ...],
    'Realme': ['gt neo2', 'gt neo2t', ...],
    'iQOO': ['iQOO 7', 'iQOO Neo5', ...],
    'honor': ['honor9x', 'honor90', ...],
    'MeiZu': ['18', '18s', '18plus', ...],
    'Nubia': ['red magic7', 'red magic7pro', ...]
}
```

### Parameter Generation Algorithms

#### VHT Capability Generation
```python
def generate_vht_capabilities():
    """70% probability not supporting VHT, otherwise generate 8-byte capability field"""
    if random.random() < 0.7:
        return "?"  # VHT not supported
    else:
        return ''.join(random.choices('0123456789abcdef', k=16))
```

#### Extended Capability Generation
```python
def generate_extended_capabilities():
    """Generate 6-byte extended capability field"""
    return ''.join(random.choices('0123456789abcdef', k=12))
```

#### HT Capability Generation
```python
def generate_ht_capabilities():
    """Generate 8-byte HT capability field"""
    return ''.join(random.choices('0123456789abcdef', k=16))
```

#### MAC Policy Generation
```python
def generate_mac_policy():
    """Randomly select MAC address policy"""
    return random.choice([0, 1, 2, 3])
    # 0: Permanent MAC
    # 1: Fully random
    # 2: Random but preserve OUI
    # 3: Dedicated/pre-generated MAC
```

### Time Parameter Generation

#### Supported Rate Distribution
```python
def generate_supported_rates():
    """Generate basic supported rate distribution"""
    rates = [6, 9, 12, 18]  # Mbps
    probs = [random probability distribution]
    return '/'.join(f"{r}:{p}" for r, p in zip(rates, probs))
```

#### State Dwell Time
```python
def generate_state_dwell():
    """Generate state dwell time distribution (5-60 seconds)"""
    dwell_times = [5, 10, 20, 30, 45, 60]
    probs = [random weight distribution]
    return '/'.join(f"{t}:{p}" for t, p in zip(dwell_times, probs))
```

#### Packet Interval Jitter
```python
def generate_jitter():
    """Generate packet interval jitter distribution (0.01-0.2 seconds)"""
    jitters = [0.01, 0.05, 0.1, 0.2]
    probs = [random weight distribution]
    return '/'.join(f"{j}:{p}" for j, p in zip(jitters, probs))
```

## Realism Optimization

### Burst Parameter Optimization
- **Intra-burst interval**: 20-100ms, conforming to real device behavior
- **Inter-burst interval**: 2-5 seconds, simulating actual scanning cycles
- **Burst length**: 1-3 frames, matching observed real patterns

### Time Distribution Modeling
```python
# Intra-burst interval (millisecond level)
burst_time_in = '/'.join(
    f"{round(random.uniform(0.02, 0.1)*100)/100}:{random_prob}"
    for _ in range(random.randint(1, 3))
)

# Inter-burst interval (second level)
burst_time_between = '/'.join(
    f"{round(random.uniform(2, 5)*100)/100}:{random_prob}"
    for _ in range(random.randint(1, 3))
)
```

## Usage Methods

### Basic Usage
```bash
cd src
python user_config.py
```

### Output Files
After running, the following files will be generated/updated:
- `oui_hex.txt`: Processed OUI database
- `1.txt`: Device hardware parameter configuration
- `2.txt`: Device behavior parameter configuration

### Custom Configuration

#### Adding New Vendors
```python
vendor_device_map['NewVendor'] = [
    'device1', 'device2', 'device3'
]
```

#### Adjusting Parameter Ranges
```python
# Modify time parameter ranges
burst_time_in_range = (0.01, 0.15)    # Intra-burst interval range
burst_time_between_range = (1.0, 8.0)  # Inter-burst interval range
state_dwell_range = (3, 120)           # State dwell range
```

## Extension Interfaces

### Custom Device Addition
```python
def add_custom_device(vendor, model, capabilities):
    """Add custom device configuration"""
    # Validate parameter format
    # Write to configuration file
    # Update internal database
```

### Configuration Import/Export
```python
def export_config(filename):
    """Export current configuration as JSON format"""
    
def import_config(filename):
    """Import configuration from JSON and update files"""
```

### Batch Update Tools
```python
def batch_update_devices(update_rules):
    """Batch update device parameters according to rules"""
    # Support regular expression matching
    # Support conditional updates
    # Provide rollback mechanism
```
