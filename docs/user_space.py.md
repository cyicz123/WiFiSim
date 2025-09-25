# user_space.py - User Space Device Simulation

[简体中文](./zh-CN/user_space.py.md) | English

## Overview

`user_space.py` implements user space behavior simulation for WiFi devices, including device class definitions, MAC address management, device parameter databases, and other core functionalities.

## Main Components

### 1. Device Class - Device Simulator

#### Core Properties
```python
class Device:
    def __init__(self, id, time, phase, vendor, model, randomization):
        self.id = id                    # Device unique identifier
        self.phase = phase              # Device state (0:locked, 1:awake, 2:active)
        self.vendor = vendor            # Device vendor
        self.model = model              # Device model
        self.randomization = randomization  # MAC randomization strategy
        self.mac_address = []           # MAC address list
        self.position = (x, y)          # Device position coordinates
        self.speed = float              # Movement speed (m/s)
        self.direction = float          # Movement direction (degrees)
```

#### MAC Address Strategies
- **Strategy 0 (Permanent MAC)**: Use fixed MAC address
- **Strategy 1 (Fully Random)**: Generate locally administered random MAC
- **Strategy 2 (OUI Preserved)**: Preserve vendor OUI, randomize last three bytes
- **Strategy 3 (Dedicated MAC)**: Use predefined dedicated MAC address

#### Rotation Modes
```python
self.mac_rotation_mode = 'per_burst'    # Change per burst
self.mac_rotation_mode = 'per_phase'    # Change per state transition
self.mac_rotation_mode = 'interval'     # Change at time intervals
```

### 2. DeviceRates Class - Device Parameter Database

#### Data Sources
- **1.txt**: Device hardware parameters
  - Vendor and model information
  - Burst length distribution
  - Wireless capability parameters (VHT, HT, extended capabilities)
  - Supported transmission rates

- **2.txt**: Device behavior parameters
  - Packet interval distribution for different states
  - Burst interval distribution
  - State dwell time distribution
  - Packet transmission jitter distribution

#### Key Methods
```python
def get_prob_int_burst(self, model, phase)      # Get intra-burst packet interval probability distribution
def get_prob_between_bursts(self, model, phase) # Get inter-burst interval probability distribution
def get_state_dwell(self, model, phase)         # Get state dwell time distribution
def get_burst_lengths(self, model)              # Get burst length distribution
def is_sending_probe(self, model, phase)        # Check if sending probe request
```

## Core Functionality Details

### MAC Address Generation and Management

#### Random MAC Generation
```python
def random_MAC() -> str:
    """Generate locally administered random MAC address"""
    first_byte = int('%d%d%d%d%d%d10' % (bits), 2)  # Set locally administered bit
    return formatted_mac_address
```

#### OUI Processing
```python
def get_oui(vendor_name: str) -> [str, str]:
    """Get corresponding OUI based on vendor name"""
    # Read IEEE OUI database from oui_hex.txt
    # Support prefix matching and case insensitive
```

#### Masked Randomization
```python
def random_mac_addr_with_mask(base: str, mask: str) -> str:
    """MAC address randomization using mask"""
    # Bits where mask=1 preserve base value
    # Bits where mask=0 use random values
```

### Device Behavior Simulation

#### Probe Request Transmission
```python
def send_probe(self, inter_pkt_time, VHT_capabilities, ...):
    """Send Probe Request burst"""
    # 1. Decide whether to change MAC based on rotation strategy
    # 2. Call kernel_driver to create 802.11 frames
    # 3. Simulate processing delay
    # 4. Return generated packet list
```

#### State Switching
```python
def change_phase(self, phase, time):
    """Device state switching"""
    self.phase = phase
    self.time_phase_changed = time
    # Trigger MAC change for per_phase mode
    if self.mac_rotation_mode == 'per_phase':
        self.force_mac_change = True
```

#### Position Updates
```python
def update_position(self, delta_t):
    """Update device position (simple linear motion model)"""
    # Calculate new position coordinates
    # Add random direction changes
    # Boundary checking and constraints
```

### SSID Management

#### SSID Generation
```python
def create_ssid(self):
    """Create random SSID list"""
    # Generate 1-10 random SSIDs
    # Each SSID is 32 characters long
    # Use alphanumeric character set
```

## Configuration File Formats

### 1.txt Format
```
# vendor, device_name, burst_lengths, mac_policy, VHT_cap, ext_cap, HT_cap, rates, ext_rates
Apple,iPhone12,1:0.2/2:0.5/3:0.3,1,?,2d0102,006f,0c121824,
```

### 2.txt Format
```
# device_name, Phase, intra_burst_interval, inter_burst_interval, state_dwell, jitter
iPhone12,0,0.02:0.7/0.04:0.3,2.0:0.5/3.0:0.5,30:0.5/60:0.5,0.0:0.5/0.02:0.5
iPhone12,1,0.03:0.6/0.05:0.4,1.5:0.6/2.5:0.4,15:0.7/25:0.3,0.01:0.6/0.03:0.4
iPhone12,2,0.02:0.8/0.03:0.2,1.0:0.8/1.5:0.2,45:0.4/90:0.6,0.0:0.7/0.01:0.3
```

## Physical Parameter Simulation

### Hardware Characteristics
```python
self.queue_length = np.random.randint(1, 10)        # Queue length
self.processing_delay = random.uniform(0.001, 0.005) # Processing delay
self.power_level = random.uniform(10, 20)           # Transmission power (dBm)
```

### Mobility Simulation
```python
self.position = (random.uniform(0, 100), random.uniform(0, 100))  # Initial position
self.speed = random.uniform(0.5, 2.0)                             # Movement speed
self.direction = random.uniform(0, 360)                           # Movement direction
```

## Utility Functions

### Frequency Calculation
```python
def get_frequency(channel: int) -> int:
    """Calculate frequency based on channel number"""
    if channel == 14:
        return 2484  # Special channel
    else:
        return 2407 + (channel * 5)  # Standard 2.4GHz channels
```

### Sequence Number Generation
```python
def produce_sequenceNumber(frag: int, seq: int) -> int:
    """Generate 802.11 sequence control field"""
    return (seq << 4) + frag
```

### MAC Address Conversion
```python
def mac_str_to_bytes(mac_str: str) -> bytes:    # String to bytes
def bytes_to_mac_str(mac_bytes: bytes) -> str:  # Bytes to string
```

## Usage Examples

### Creating Device Instance
```python
device_rates = DeviceRates()
device = Device(
    id=0,
    time=datetime.now(),
    phase=2,  # Active state
    vendor="Apple",
    model="iPhone12",
    randomization=1  # Fully random MAC
)
```

### Configuring MAC Rotation
```python
device.mac_rotation_mode = 'interval'  # Rotate at time intervals
device.force_mac_change = True         # Force change next time
```

### Sending Probe Request
```python
packets = device.send_probe(
    inter_pkt_time=0.02,
    VHT_capabilities=vht_cap,
    extended_capabilities=ext_cap,
    HT_capabilities=ht_cap,
    num_pkt_burst=3,
    timestamp=datetime.now(),
    channel=6,
    supported_rates="0c121824",
    ext_supported_rates=""
)
```

## Extension and Customization

### Adding New Device Types
1. Add device parameter lines in 1.txt
2. Add behavior parameters for each state in 2.txt
3. Update OUI database (if needed)

### Custom MAC Rotation Strategies
1. Extend mac_rotation_mode options
2. Add processing logic in send_probe()
3. Implement corresponding time management mechanisms

### Enhanced Mobility Models
1. Replace simple linear model in update_position()
2. Add more complex path planning algorithms
3. Integrate real mobility trajectory data
