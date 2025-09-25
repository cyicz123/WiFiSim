# WiFi Probe Request Simulation System

[简体中文](./docs/zh-CN/README.md) | English

A comprehensive WiFi Probe Request simulation platform for generating and analyzing WiFi probe requests with support for various device types and network scenarios.

## Features

- 🚀 Support for multi-device and single-device simulation modes
- 📱 Built-in realistic device models (Apple, Samsung, Xiaomi, etc.)
- 🔄 Flexible MAC address rotation strategies
- 📊 Complete physical layer channel simulation
- 📈 Rich performance metrics analysis
- 🎯 Automatic parameter calibration and optimization

## Requirements

- Python 3.8+
- Supports Linux, macOS, Windows

## Installation

### Using uv (Recommended)

1. Install uv if not already installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or using pip
pip install uv
```

2. Install project dependencies using uv:
```bash
# Navigate to project directory
cd WiFiSim

# Install all dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
source .venv/Scripts/activate  # Windows
```

## Quick Start

### 1. Generate Synthetic Dataset

Run the main program to start interactive dataset generation:

```bash
cd src
python main.py
```

The program will guide you through the following configuration:

1. **Choose Dataset Type**:
   - Multi-device (with device state switching)
   - Single device (with state switching)
   - Single device (without state switching)

2. **Set Simulation Parameters**:
   - Simulation duration (minutes)
   - Number of devices
   - Network scenarios (high mobility, low mobility high density, low mobility low density)

3. **Device Configuration** (Single device mode):
   - Select device brand (Apple, Samsung, Xiaomi, etc.)
   - Specify device model (optional)
   - Set device state (locked/awake/active)

### 2. Output Files

After simulation completion, the following files will be generated:

- `out_file_run_N.pcap` - Network packet capture file
- `out_file_run_N.txt` - Detailed simulation logs
- `out_file_run_N_probe_ids.txt` - Probe request device ID mapping
- `out_file_run_N_devices.csv` - Device information table (MAC addresses, device names, device IDs)

### 3. Data Analysis

Use analysis tools to validate simulation quality:

```bash
# Analyze simulation data quality metrics
python shiyan.py

# Calibrate parameters from real data
python calibrate_from_pcap.py

# Automatic parameter optimization
python autotune_calibration.py --max-iters 10 --duration-min 3
```

## Advanced Usage

### Custom Device Configuration

1. Edit `1.txt` file to add new device models
2. Edit `2.txt` file to configure device behavior parameters
3. Run `user_config.py` to regenerate configuration

### Physical Layer Parameter Adjustment

Modify physical layer parameters in `phy_layer.py`:
- Transmission power
- Frequency settings
- Channel fading models

### Batch Simulation

```bash
# Modify dataset_count variable in main.py
dataset_count = 5  # Generate 5 datasets

# Or via command line arguments (if supported)
python main.py --count 5
```

## Project Structure

```
WiFiSim/
├── src/                    # Source code directory
├── docs/                   # Documentation directory
│   ├── zh-CN/             # Chinese documentation
│   └── ...                # English documentation (default)
├── requirements.txt        # Python dependencies
├── README.md              # Project documentation
└── pyproject.toml         # Project configuration
```

## Configuration Files

- `1.txt` - Device hardware parameter configuration
- `2.txt` - Device behavior parameter configuration
- `oui.txt` - IEEE OUI database
- `oui_hex.txt` - Processed OUI data

## Performance Metrics

The system supports analysis of the following key performance indicators:

- **MCR (MAC Change Rate)** - MAC address change rate
- **NUMR (Normalized Unique MAC Ratio)** - Normalized unique MAC ratio
- **MCIV (MAC Change Interval Variance)** - MAC change interval variance
- **MAE (MAC Address Entropy)** - MAC address entropy

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure all dependencies are properly installed
2. **File permissions**: Ensure write permissions to current directory
3. **Memory shortage**: Consider increasing available memory for large-scale simulations

### Debug Mode

Enable verbose logging output:
```bash
python main.py --verbose
```

## Documentation

- [English Documentation](./docs/) (Default)
- [简体中文文档](./docs/zh-CN/) 

For detailed module documentation, please refer to the docs directory.

## Citation

If you use this project in your research, please cite it as follows:

```
@misc{hao2025wifisimsimulatingwifiprobe,
      title={WiFiSim: Simulating WiFi Probe Requests via AOSP Analysis and Device Behavior Modeling}, 
      author={Lifei Hao and Yue Cheng and Min Wang and Bing Jia and Baoqi Huang},
      year={2025},
      eprint={2509.15501},
      archivePrefix={arXiv},
      primaryClass={cs.NI},
      url={https://arxiv.org/abs/2509.15501}, 
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions or suggestions, please contact us through GitHub Issues.