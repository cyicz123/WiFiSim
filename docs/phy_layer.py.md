# phy_layer.py - Physical Layer Simulation Module

[简体中文](./zh-CN/phy_layer.py.md) | English

## Overview

`phy_layer.py` implements WiFi physical layer simulation functionality, modeling wireless signal propagation characteristics in real environments, including path loss, fading, shadowing effects and other physical phenomena.

## Core Classes

### PhysicalLayer Class

#### Initialization Parameters
```python
class PhysicalLayer:
    def __init__(self, tx_power=20, frequency=2400, env='urban'):
        self.tx_power = tx_power      # Transmission power (dBm)
        self.frequency = frequency    # Frequency (MHz)
        self.env = env               # Environment type
```

**Parameter Description**:
- `tx_power`: Transmission power, default 20dBm, range typically 10-30dBm
- `frequency`: Operating frequency, default 2400MHz (2.4GHz WiFi)
- `env`: Environment type, can be used for subsequent environment-related parameter adjustments

## Physical Phenomena Modeling

### 1. Free Space Path Loss (FSPL)

```python
def free_space_path_loss(self, distance):
    """Calculate free space path loss"""
    # FSPL = 20*log10(d) + 20*log10(f) - 27.55
    # d: distance (meters), f: frequency (MHz)
    loss = 20 * math.log10(distance) + 20 * math.log10(self.frequency) - 27.55
    return loss  # Unit: dB
```

**Physical Meaning**:
- Signal power attenuation with distance in ideal free space
- Follows inverse square law: power ∝ 1/d²
- Higher frequency results in greater loss

**Application Scenarios**:
- Signal propagation in open areas
- Basic loss calculation for line-of-sight (LOS) communication
- Reference baseline for other loss models

### 2. Rayleigh Fading

```python
def rayleigh_fading(self):
    """Simulate Rayleigh fading"""
    fading = np.random.rayleigh(scale=2.0)
    return -fading  # Negative value indicates fading loss
```

**Physical Meaning**:
- Simulate fast fading caused by multipath propagation
- Applicable to non-line-of-sight (NLOS) environments
- Signal amplitude follows Rayleigh distribution

**Characteristics**:
- High randomness, reflecting rapid signal changes
- Scale parameter controls fading depth
- Usually results in signal power reduction

### 3. Shadowing/Log-normal Fading

```python
def shadowing(self):
    """Simulate shadowing fading"""
    return random.gauss(0, 3)  # Normal distribution with mean 0, std 3dB
```

**Physical Meaning**:
- Simulate large-scale slow fading effects
- Caused by terrain, buildings and other obstacles
- Power variation follows log-normal distribution

**Parameter Settings**:
- Mean: 0dB (unbiased estimate)
- Standard deviation: 3dB (typical urban environment value)
- Can adjust standard deviation based on environment type

## Channel Simulation

### Received Power Calculation

```python
def compute_received_power(self, distance):
    """Calculate received power"""
    loss = self.free_space_path_loss(distance)
    fading = self.rayleigh_fading()
    shadow = self.shadowing()
    
    # Received power = Tx power - Path loss + Fading + Shadowing
    received_power = self.tx_power - loss + fading + shadow
    return received_power
```

**Calculation Formula**:
```
P_rx = P_tx - FSPL + Rayleigh + Shadowing
```

**Component Contributions**:
- `P_tx`: Transmission power (positive value)
- `FSPL`: Path loss (positive value, indicating loss)
- `Rayleigh`: Rayleigh fading (negative value, indicating additional loss)
- `Shadowing`: Shadow fading (can be positive or negative, mean is 0)

### Channel Success Decision

```python
def simulate_channel(self, distance, env_factor=1.0):
    """Simulate channel transmission success"""
    received_power = self.compute_received_power(distance) * env_factor
    noise_floor = -90  # Noise floor (dBm)
    
    if received_power > noise_floor + 10:  # 10dB margin
        return True   # Transmission success
    else:
        return False  # Transmission failure
```

**Decision Criteria**:
- **Noise Floor**: -90dBm (typical WiFi receiver noise level)
- **Reception Threshold**: Noise floor + 10dB = -80dBm
- **Environment Factor**: Allows external adjustment of environmental impact

## Usage Examples

### Basic Usage
```python
# Create physical layer instance
phy = PhysicalLayer(tx_power=20, frequency=2400, env='urban')

# Calculate received power at specific distance
distance = 10.0  # 10 meters
rx_power = phy.compute_received_power(distance)
print(f"Received Power: {rx_power:.2f} dBm")

# Determine transmission success
success = phy.simulate_channel(distance, env_factor=1.2)
print(f"Transmission Status: {'Success' if success else 'Failure'}")
```

### Distance-Power Relationship Analysis
```python
distances = np.linspace(1, 100, 100)  # 1-100 meters
powers = []

for d in distances:
    power = phy.compute_received_power(d)
    powers.append(power)

# Plot power-distance curve
import matplotlib.pyplot as plt
plt.plot(distances, powers)
plt.xlabel('Distance (m)')
plt.ylabel('Received Power (dBm)')
plt.title('Power-Distance Relationship')
plt.grid(True)
plt.show()
```

### Success Rate Statistics
```python
def calculate_success_rate(distance, num_trials=1000):
    """Calculate transmission success rate at specific distance"""
    successes = 0
    for _ in range(num_trials):
        if phy.simulate_channel(distance):
            successes += 1
    return successes / num_trials

# Analyze success rates at different distances
distances = [5, 10, 20, 50, 100]
for d in distances:
    rate = calculate_success_rate(d)
    print(f"Distance {d}m: Success Rate {rate:.1%}")
```

## Parameter Configuration

### Environment-Related Parameters

#### Typical Parameters for Different Environments
```python
ENV_PARAMS = {
    'indoor': {
        'shadowing_std': 4.0,    # Indoor shadow standard deviation
        'rayleigh_scale': 1.5,   # Indoor multipath weaker
        'noise_floor': -85       # Indoor noise lower
    },
    'urban': {
        'shadowing_std': 6.0,    # Urban shadow standard deviation
        'rayleigh_scale': 2.0,   # Urban multipath moderate
        'noise_floor': -90       # Standard noise level
    },
    'rural': {
        'shadowing_std': 2.0,    # Rural shadow standard deviation
        'rayleigh_scale': 1.0,   # Rural multipath less
        'noise_floor': -95       # Rural noise very low
    }
}
```

### Frequency Band Related Parameters

#### 2.4GHz vs 5GHz
```python
# 2.4GHz configuration
phy_2g = PhysicalLayer(tx_power=20, frequency=2400)

# 5GHz configuration
phy_5g = PhysicalLayer(tx_power=23, frequency=5200)
```

**Difference Description**:
- 5GHz band has greater path loss
- 5GHz has weaker penetration capability
- 5GHz typically allows higher transmission power

## Advanced Features

### Dynamic Environment Factor
```python
def dynamic_env_factor(device_position, ap_position):
    """Calculate dynamic environment factor based on device and AP positions"""
    # Consider obstacles, terrain and other factors
    distance = np.linalg.norm(np.array(device_position) - np.array(ap_position))
    
    # Simple distance-related environment factor
    if distance < 10:
        return 1.2  # Short distance, small environmental impact
    elif distance < 50:
        return 1.0  # Medium distance, standard environment
    else:
        return 0.8  # Long distance, large environmental impact
```

### Multipath Delay Spread
```python
def multipath_delay_spread(self):
    """Simulate multipath delay spread"""
    # Typical indoor RMS delay spread: 10-50ns
    # Typical outdoor RMS delay spread: 100-1000ns
    if self.env == 'indoor':
        return random.uniform(10e-9, 50e-9)  # nanoseconds
    else:
        return random.uniform(100e-9, 1000e-9)
```

### Doppler Frequency Shift
```python
def doppler_shift(self, velocity):
    """Calculate Doppler frequency shift"""
    # f_d = (v/c) * f_c
    c = 3e8  # Speed of light m/s
    doppler = (velocity / c) * self.frequency * 1e6  # Hz
    return doppler
```

## Extension and Customization

### Custom Fading Models
```python
class CustomPhysicalLayer(PhysicalLayer):
    def rician_fading(self, k_factor=3):
        """Rician fading model"""
        # K factor represents power ratio of direct to scattered components
        los = np.sqrt(k_factor / (k_factor + 1))
        nlos = np.sqrt(1 / (k_factor + 1)) * (np.random.randn() + 1j * np.random.randn())
        amplitude = abs(los + nlos)
        return 20 * np.log10(amplitude)  # Convert to dB
```

### Frequency-Dependent Modeling
```python
def frequency_dependent_loss(self, distance, frequency):
    """Frequency-dependent additional loss"""
    # Additional attenuation for high-frequency signals
    extra_loss = 0
    if frequency > 3000:  # Above 3GHz
        extra_loss = (frequency - 3000) / 1000 * 2  # 2dB loss per GHz
    return extra_loss
```

### Antenna Model Integration
```python
def antenna_gain(self, angle):
    """Simple directional antenna gain model"""
    # Assume main lobe direction is 0 degrees
    if abs(angle) < 30:  # Main lobe range ±30 degrees
        return 10  # 10dB gain
    elif abs(angle) < 90:  # Side lobe range
        return -3  # -3dB
    else:  # Back lobe
        return -20  # -20dB
```

## Performance Optimization

### Batch Calculation
```python
def batch_channel_simulation(self, distances, env_factors=None):
    """Batch channel simulation"""
    if env_factors is None:
        env_factors = [1.0] * len(distances)
    
    results = []
    for dist, env_f in zip(distances, env_factors):
        success = self.simulate_channel(dist, env_f)
        results.append(success)
    
    return results
```

### Pre-computed Lookup Tables
```python
def build_loss_table(self, max_distance=200, step=1):
    """Build path loss lookup table"""
    self.loss_table = {}
    for d in range(1, max_distance + 1, step):
        self.loss_table[d] = self.free_space_path_loss(d)
```

This physical layer module provides realistic channel condition simulation for the WiFi simulation system, enabling generated packets to reflect transmission characteristics in actual wireless environments.
