# WiFiSim Documentation Overview

[简体中文](./zh-CN/README.md) | English

This directory contains detailed functional documentation for each Python file in the WiFi Probe Request simulation system.

## Documentation List

### Core Simulation Modules

1. **[main.py](./main.py.md)** - Main Simulation Program
   - Core system entry point with interactive configuration interface
   - Complete event-driven simulation engine implementation
   - Support for multiple dataset types and scenario configurations
   - Generate standard format output files

2. **[user_space.py](./user_space.py.md)** - User Space Device Simulation
   - Device class: Core of device behavior simulation
   - DeviceRates class: Device parameter database management
   - MAC address generation and rotation strategies
   - Device mobility and state switching simulation

3. **[kernel_driver.py](./kernel_driver.py.md)** - Kernel Driver Layer 802.11 Frame Generation
   - Generate IEEE 802.11 standard compliant Probe Request frames
   - RadioTap header and 802.11 management frame construction
   - Information Elements (IEs) processing
   - Burst generation and sequence number management

4. **[phy_layer.py](./phy_layer.py.md)** - Physical Layer Simulation Module
   - Wireless channel characteristics simulation
   - Path loss, fading, and shadowing effects modeling
   - Channel success determination and RSSI calculation
   - Multi-band and environment configuration support

### Configuration and Calibration Tools

5. **[user_config.py](./user_config.py.md)** - User Configuration Generator
   - OUI data preprocessing and conversion
   - Device parameter database generation (1.txt, 2.txt)
   - Built-in multi-vendor device model support
   - Realistic parameter optimization

6. **[calibrate_from_pcap.py](./calibrate_from_pcap.py.md)** - Real Data-based Parameter Calibration Tool
   - Real PCAP file analysis and metric extraction
   - Automatic parameter inference and configuration file updates
   - Support for batch data processing and aggregated analysis
   - Quality control and validation mechanisms

7. **[autotune_calibration.py](./autotune_calibration.py.md)** - Automatic Parameter Tuning Tool
   - Intelligent multi-objective optimization algorithms
   - Fast simulation mode and early stopping mechanisms
   - Robust metric parsing and error handling
   - Command-line interface and batch processing support

### Analysis and Utility Modules

8. **[shiyan.py](./shiyan.py.md)** - Simulation Data Quality Analysis Tool
   - Key performance indicator calculations (MCR, NUMR, MCIV, MAE, etc.)
   - PCAP file processing and time segment analysis
   - Simulation quality assessment and comparative analysis
   - Support for multiple time windows and statistical methods

9. **[capture_parsing.py](./capture_parsing.py.md)** - Packet Capture and Parsing Tool
   - Simulated frame capture and RSSI assignment
   - Detailed 802.11 frame parsing
   - Information element by element analysis
   - Device fingerprinting and anomaly detection

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   main.py       │    │  user_space.py   │    │ kernel_driver.py│
│ (Sim Engine)    │◄──►│ (Device Sim)     │◄──►│ (Frame Gen)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   phy_layer.py  │    │ user_config.py   │    │capture_parsing.py│
│ (Physical Layer)│    │ (Config Gen)     │    │ (Quality Check) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌──────────────────┐
                    │    shiyan.py     │
                    │ (Quality Analysis)│
                    └──────────────────┘
                                │
                                ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │calibrate_from_   │    │autotune_        │
                    │pcap.py (Calib)   │◄──►│calibration.py   │
                    └──────────────────┘    │ (Auto Tuning)   │
                                           └─────────────────┘
```

## Data Flow

### 1. Configuration Phase
```
OUI Data → user_config.py → 1.txt, 2.txt
Real PCAP → calibrate_from_pcap.py → Update Config Files
```

### 2. Simulation Phase
```
Config Files → user_space.py → Device Instances
Device → kernel_driver.py → 802.11 Frames
802.11 Frames → phy_layer.py → Channel Simulation
Final Frames → main.py → PCAP Output
```

### 3. Analysis Phase
```
PCAP Output → shiyan.py → Quality Metrics
Quality Metrics → autotune_calibration.py → Parameter Optimization
Optimized Parameters → Re-simulation → Iterative Improvement
```

## Key Concepts

### Device States (Phase)
- **0 - Locked State**: Device screen off, low-frequency scanning
- **1 - Awake State**: Device screen on, medium-frequency scanning
- **2 - Active State**: Device in use, high-frequency scanning

### MAC Rotation Strategies
- **per_burst**: Change MAC address for each burst
- **per_phase**: Change MAC when state transitions
- **interval**: Change MAC at regular time intervals

### Key Metrics
- **MCR (MAC Change Rate)**: MAC change rate, changes/second
- **NUMR (Normalized Unique MAC Ratio)**: Unique MAC ratio
- **MCIV (MAC Change Interval Variance)**: MAC change interval variance
- **MAE (MAC Address Entropy)**: MAC address entropy

### Dataset Types
- **Multi-device Mode**: Simulate multi-device network environment
- **Single Device Switchable Mode**: Single device with state transitions
- **Single Device Static Mode**: Single device with fixed state

## Quick Navigation

- **New User Getting Started**: Read [main.py documentation](./main.py.md) first for system overview
- **Device Modeling**: Refer to [user_space.py documentation](./user_space.py.md)
- **Frame Format Customization**: See [kernel_driver.py documentation](./kernel_driver.py.md)
- **Parameter Tuning**: Use [autotune_calibration.py documentation](./autotune_calibration.py.md)
- **Quality Assessment**: Refer to [shiyan.py documentation](./shiyan.py.md)

## Development Guide

### Adding New Device Types
1. Add device parameters in `user_config.py`
2. Update `1.txt` and `2.txt` configuration files
3. Test device behavior in `user_space.py`

### Custom Physical Layer Models
1. Extend PhysicalLayer class in `phy_layer.py`
2. Implement new fading or propagation models
3. Integrate new models in `main.py`

### Extending Analysis Metrics
1. Add new metric calculation functions in `shiyan.py`
2. Update optimization targets in `autotune_calibration.py`
3. Modify evaluation and reporting logic

## Troubleshooting

### Common Issues
- **Missing Config Files**: Run `user_config.py` to generate initial configuration
- **Slow Simulation**: Use `realtime=False` parameter
- **Metric Parsing Failure**: Check output file format and permissions
- **Parameter Non-convergence**: Adjust search range and optimization strategy

### Debug Tips
- Use `capture_parsing.py` to check generated frame format
- Compare simulation and real data through `shiyan.py`
- Enable verbose logging mode to view execution process
- Use short-duration simulation for quick testing

## Contributing Guide

Welcome to contribute code and documentation to this project. Please ensure:
1. New features have corresponding documentation
2. Code style is consistent with the project
3. Add necessary test cases
4. Update related README documentation

For more detailed information, please refer to the README.md file in the project root directory.
