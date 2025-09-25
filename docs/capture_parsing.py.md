# capture_parsing.py - Packet Capture and Parsing Tool

[简体中文](./zh-CN/capture_parsing.py.md) | English

## Overview

`capture_parsing.py` is the packet parsing module of the WiFi simulation system, providing functions for capturing, parsing, and quality checking generated Probe Request frames, simulating the behavior of real network monitoring devices.

## Core Functions

### 1. Frame Capture Simulation

#### CapturedFrame Class
```python
class CapturedFrame:
    def __init__(self, frame, rssi):
        self.frame = frame    # Raw frame data
        self.rssi = rssi      # Received Signal Strength Indicator
```

**Attribute Description**:
- `frame`: Scapy packet object containing complete frame structure
- `rssi`: Received signal strength in dBm, typically ranging from -40 to -90dBm

#### Frame Capture Function
```python
def capture_frame(frame):
    """Simulate frame capture process"""
    # Assign random RSSI value to frame
    rssi = -(40 + random.randint(0, 50))  # -40 to -90 dBm
    return CapturedFrame(frame, rssi)
```

**RSSI Simulation Characteristics**:
- Range: -40dBm (strong signal) to -90dBm (weak signal)
- Random distribution: Simulates signal strength variations in real environments
- Usage: Can be used for subsequent signal quality analysis and filtering

### 2. Frame Parsing and Analysis

#### Main Parsing Function
```python
def parse_captured_frame(captured):
    """Parse captured Probe Request frame"""
    print("Captured Probe Request frame:")
    
    # Display frame hexadecimal dump
    hexdump(captured.frame)
    
    # Parse protocol information at each layer
    parse_dot11_header(captured.frame)
    parse_information_elements(captured.frame)
    
    print(f"RSSI at capture: {captured.rssi} dBm")
```

### 3. 802.11 Header Parsing

#### Basic Header Information
```python
if captured.frame.haslayer(Dot11):
    dot11 = captured.frame.getlayer(Dot11)
    print(f"Source MAC Address: {dot11.addr2}")      # Sending device MAC
    print(f"Destination MAC Address: {dot11.addr1}")  # Usually broadcast address
    print(f"BSSID: {dot11.addr3}")                   # Base station identifier
    print(f"Sequence Number: {dot11.SC}")            # Sequence control field
```

**Address Field Meanings**:
- `addr1`: Destination address, broadcast address (ff:ff:ff:ff:ff:ff) in Probe Request
- `addr2`: Source address, i.e., sending device's MAC address
- `addr3`: BSSID, usually broadcast address in Probe Request

### 4. Information Element Parsing

#### Element Traversal Mechanism
```python
elt = captured.frame.getlayer(Dot11Elt)
while elt:
    parse_single_element(elt)
    elt = elt.payload.getlayer(Dot11Elt)  # Get next element
```

#### Specific Element Parsing

##### SSID Element (ID=0)
```python
if elt.ID == 0:
    try:
        ssid = elt.info.decode(errors="ignore")
    except Exception:
        ssid = elt.info
    print(f"SSID: {ssid}")
```

**Special Cases**:
- Empty SSID: Indicates wildcard scanning
- Non-UTF-8 encoding: Use error-ignore mode for decoding
- Hidden SSID: SSID field with length 0

##### Supported Rates Element (ID=1)
```python
elif elt.ID == 1:
    # Rates encoded in 0.5 Mbps units
    rates = [f"{r / 2:.1f}" for r in elt.rates]
    print("Supported Rates:", " ".join(rates), "Mbps")
```

**Rate Encoding**:
- Raw values in 0.5Mbps units
- Convert to actual Mbps for display
- Example: 0x0c → 6Mbps, 0x12 → 9Mbps

##### Extended Supported Rates Element (ID=50)
```python
elif elt.ID == 50:
    ext_rates = [f"{r / 2:.1f}" for r in elt.rates]
    print("Extended Supported Rates:", " ".join(ext_rates), "Mbps")
```

##### Wireless Capability Elements
```python
elif elt.ID == 45:
    print("HT Capabilities:", elt.info.hex())       # HT capabilities

elif elt.ID == 191:
    print("VHT Capabilities:", elt.info.hex())      # VHT capabilities

elif elt.ID == 127:
    print("Extended Capabilities:", elt.info.hex()) # Extended capabilities
```

##### Vendor Specific Element (ID=221)
```python
elif elt.ID == 221:
    print("Vendor Specific:", elt.info.hex())
    # May contain vendor-specific information like WPS, P2P, etc.
```

## Usage Examples

### Basic Parsing Process
```python
from capture_parsing import capture_frame, parse_captured_frame
from scapy.all import rdpcap

# Read PCAP file
packets = rdpcap("simulation_output.pcap")

for packet in packets:
    if packet.haslayer(Dot11) and packet.type == 0 and packet.subtype == 4:
        # Simulate capture process
        captured = capture_frame(packet)
        
        # Parse frame content
        parse_captured_frame(captured)
        print("-" * 50)
```

### Batch Quality Check
```python
def quality_check_batch(pcap_file, sample_rate=0.1):
    """Perform batch quality check on PCAP file"""
    packets = rdpcap(pcap_file)
    probe_requests = [p for p in packets if is_probe_request(p)]
    
    # Select frames for checking based on sampling rate
    sample_size = int(len(probe_requests) * sample_rate)
    sampled_packets = random.sample(probe_requests, sample_size)
    
    for packet in sampled_packets:
        captured = capture_frame(packet)
        try:
            parse_captured_frame(captured)
        except Exception as e:
            print(f"Parsing error: {e}")
```

### Signal Quality Analysis
```python
def analyze_signal_quality(captured_frames):
    """Analyze signal quality distribution of captured frames"""
    rssi_values = [cf.rssi for cf in captured_frames]
    
    print(f"RSSI Statistics:")
    print(f"  Mean: {np.mean(rssi_values):.1f} dBm")
    print(f"  Std Dev: {np.std(rssi_values):.1f} dB")
    print(f"  Strongest Signal: {max(rssi_values):.1f} dBm")
    print(f"  Weakest Signal: {min(rssi_values):.1f} dBm")
    
    # Signal strength classification
    strong = sum(1 for rssi in rssi_values if rssi > -50)
    medium = sum(1 for rssi in rssi_values if -70 <= rssi <= -50)
    weak = sum(1 for rssi in rssi_values if rssi < -70)
    
    total = len(rssi_values)
    print(f"Signal Distribution:")
    print(f"  Strong Signal (>-50dBm): {strong} ({strong/total:.1%})")
    print(f"  Medium Signal (-70~-50dBm): {medium} ({medium/total:.1%})")
    print(f"  Weak Signal (<-70dBm): {weak} ({weak/total:.1%})")
```

## Advanced Parsing Functions

### Device Fingerprinting
```python
def extract_device_fingerprint(captured_frame):
    """Extract device fingerprint features"""
    fingerprint = {
        'mac_oui': captured_frame.frame[Dot11].addr2[:8],  # OUI prefix
        'supported_rates': [],
        'capabilities': {},
        'vendor_elements': []
    }
    
    # Traverse information elements to extract features
    elt = captured_frame.frame.getlayer(Dot11Elt)
    while elt:
        if elt.ID == 1:  # Supported rates
            fingerprint['supported_rates'] = list(elt.rates)
        elif elt.ID == 45:  # HT capabilities
            fingerprint['capabilities']['ht'] = elt.info.hex()
        elif elt.ID == 191:  # VHT capabilities
            fingerprint['capabilities']['vht'] = elt.info.hex()
        elif elt.ID == 221:  # Vendor specific
            fingerprint['vendor_elements'].append(elt.info.hex())
        
        elt = elt.payload.getlayer(Dot11Elt)
    
    return fingerprint
```

### Anomaly Frame Detection
```python
def detect_anomalies(captured_frame):
    """Detect anomalous frames"""
    anomalies = []
    frame = captured_frame.frame
    
    # Check basic structure
    if not frame.haslayer(Dot11):
        anomalies.append("Missing 802.11 header")
        return anomalies
    
    dot11 = frame[Dot11]
    
    # Check frame type
    if dot11.type != 0 or dot11.subtype != 4:
        anomalies.append("Not a Probe Request frame")
    
    # Check address fields
    if dot11.addr1 != "ff:ff:ff:ff:ff:ff":
        anomalies.append("Destination address is not broadcast")
    
    if not is_valid_mac(dot11.addr2):
        anomalies.append("Source MAC address format anomaly")
    
    # Check information elements
    if not frame.haslayer(Dot11Elt):
        anomalies.append("Missing information elements")
    
    return anomalies

def is_valid_mac(mac_str):
    """Validate MAC address format"""
    import re
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(pattern, mac_str))
```

### Timing Analysis
```python
def analyze_timing_patterns(captured_frames):
    """Analyze timing patterns of frames"""
    timestamps = [cf.frame.time for cf in captured_frames]
    intervals = np.diff(sorted(timestamps))
    
    # Burst detection
    burst_threshold = 0.25  # 250ms
    bursts = []
    current_burst = [timestamps[0]]
    
    for i, interval in enumerate(intervals):
        if interval <= burst_threshold:
            current_burst.append(timestamps[i + 1])
        else:
            if len(current_burst) > 1:
                bursts.append(current_burst)
            current_burst = [timestamps[i + 1]]
    
    if len(current_burst) > 1:
        bursts.append(current_burst)
    
    print(f"Detected {len(bursts)} bursts")
    print(f"Average burst length: {np.mean([len(b) for b in bursts]):.1f}")
    print(f"Average frame interval: {np.mean(intervals):.3f}s")
    print(f"Interval standard deviation: {np.std(intervals):.3f}s")
```

## Debugging and Diagnostics

### Detailed Frame Dump
```python
def detailed_frame_dump(captured_frame):
    """Detailed frame information dump"""
    frame = captured_frame.frame
    
    print("=== Detailed Frame Information ===")
    print(f"Capture Time: {datetime.fromtimestamp(frame.time)}")
    print(f"Frame Length: {len(frame)} bytes")
    print(f"RSSI: {captured_frame.rssi} dBm")
    
    # RadioTap header
    if frame.haslayer(RadioTap):
        rt = frame[RadioTap]
        print(f"RadioTap Length: {rt.len} bytes")
        print(f"Channel Frequency: {rt.ChannelFrequency} MHz")
        print(f"Transmission Rate: {rt.Rate} Mbps")
    
    # 802.11 header
    if frame.haslayer(Dot11):
        dot11 = frame[Dot11]
        print(f"Frame Control: 0x{dot11.FCfield:04x}")
        print(f"Sequence Control: 0x{dot11.SC:04x}")
        print(f"Source Address: {dot11.addr2}")
        print(f"Destination Address: {dot11.addr1}")
        print(f"BSSID: {dot11.addr3}")
    
    # Information element statistics
    element_count = count_information_elements(frame)
    print(f"Number of Information Elements: {element_count}")
```

### Performance Monitoring
```python
def monitor_parsing_performance():
    """Monitor parsing performance"""
    import time
    
    start_time = time.time()
    frame_count = 0
    error_count = 0
    
    def process_frame(frame):
        nonlocal frame_count, error_count
        try:
            captured = capture_frame(frame)
            parse_captured_frame(captured)
            frame_count += 1
        except Exception as e:
            error_count += 1
            print(f"Parsing error: {e}")
    
    # Calculate statistics after processing completion
    elapsed_time = time.time() - start_time
    fps = frame_count / elapsed_time if elapsed_time > 0 else 0
    error_rate = error_count / (frame_count + error_count) if (frame_count + error_count) > 0 else 0
    
    print(f"Parsing Performance Statistics:")
    print(f"  Processed Frames: {frame_count}")
    print(f"  Error Frames: {error_count}")
    print(f"  Processing Speed: {fps:.1f} frames/second")
    print(f"  Error Rate: {error_rate:.2%}")
```

## Integration and Extension

### Integration with Simulation System
```python
# Usage example in main.py
if random.random() < simulator.scene_params.get("qa_sample_rate", 0.0):
    c = capture_parsing.capture_frame(event.packet)
    capture_parsing.parse_captured_frame(c)
```

### Custom Parsers
```python
def register_custom_parser(element_id, parser_func):
    """Register custom information element parser"""
    custom_parsers[element_id] = parser_func

def parse_custom_element(elt):
    """Parse custom information element"""
    if elt.ID in custom_parsers:
        return custom_parsers[elt.ID](elt)
    else:
        return f"Unknown element ID={elt.ID}: {elt.info.hex()}"
```

This module provides important quality assurance functionality for the WiFi simulation system, ensuring the accuracy and reliability of simulation results through real-time parsing and checking of generated packets.
