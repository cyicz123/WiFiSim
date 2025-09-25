# kernel_driver.py - Kernel Driver Layer 802.11 Frame Generation

[简体中文](./zh-CN/kernel_driver.py.md) | English

## Overview

`kernel_driver.py` simulates WiFi device kernel driver layer functionality, responsible for generating IEEE 802.11 standard compliant Probe Request frames, including RadioTap headers, 802.11 management frame headers, and various Information Elements (IEs).

## Core Functionality

### 1. Probe Request Frame Construction

#### Main Function: create_probe()
```python
def create_probe(vendor, randomization, ssid, burst_length, mac_address, 
                inter_pkt_time, VHT_capabilities, extended_capabilities, 
                HT_capabilities, wps, uuide, time, channel, 
                supported_rates, ext_supported_rates):
    """Create complete Probe Request burst"""
    # Returns: (mac_address, packets_list)
```

**Parameter Description**:
- `vendor`: Device vendor name
- `randomization`: MAC randomization strategy
- `ssid`: Target SSID list
- `burst_length`: Number of frames in burst
- `mac_address`: Source MAC address
- `inter_pkt_time`: Inter-frame interval time
- Various capability fields: VHT, HT, extended capabilities, etc.
- `wps/uuide`: WPS-related information
- `time`: Timestamp
- `channel`: Operating channel
- `supported_rates`: Supported transmission rates

#### Frame Structure Assembly
```python
# Basic frame structure
frame = radio / dot11 / probeReq / elements...

# Frame with VHT capabilities
if VHT_capabilities is not None:
    frame = radio / dot11 / probeReq / dot11elt / dot11eltrates / 
            dot11eltratesext / dot11eltdssset / dot11elthtcap / 
            dot11eltVHTcap / dot11eltEXTcap / dot11eltven / [wps/uuide]
```

### 2. RadioTap Header Generation

```python
def create_radio(channel):
    """Create RadioTap header"""
    return RadioTap(
        present='TSFT+Flags+Rate+Channel+dBm_AntSignal+Antenna',
        Flags='',
        Rate=1.0,                                    # Transmission rate
        ChannelFrequency=get_frequency(channel),     # Channel frequency
        ChannelFlags='CCK+2GHz',                     # Channel flags
        dBm_AntSignal=-random.randint(30,70),        # Signal strength
        Antenna=0                                    # Antenna number
    )
```

**RadioTap Fields**:
- `TSFT`: Timestamp
- `Flags`: Frame flags
- `Rate`: Transmission rate (Mbps)
- `Channel`: Channel information (frequency + flags)
- `dBm_AntSignal`: Received Signal Strength Indicator (RSSI)
- `Antenna`: Antenna number

### 3. 802.11 Management Frame Header

```python
def create_80211(vendor, randomization, seq_number, mac_address, burst_length):
    """Create 802.11 management frame header"""
    return Dot11(
        addr1='ff:ff:ff:ff:ff:ff',    # Destination address (broadcast)
        addr2=mac_address,            # Source address
        addr3='ff:ff:ff:ff:ff:ff',    # BSSID (broadcast)
        SC=produce_sequenceNumber(0, seq_number)  # Sequence control
    )
```

**Address Fields**:
- `addr1`: Destination address, Probe Request uses broadcast address
- `addr2`: Source address, sending device's MAC address
- `addr3`: BSSID, usually broadcast address in Probe Request

**Sequence Control**:
- Sequence number: Uniquely identifies frame sequence
- Fragment number: Usually 0 (no fragmentation)

## Information Elements (IEs)

### 1. SSID Element
```python
def create_informationElement(ssid):
    """Create SSID information element"""
    return Dot11Elt(ID=0, info=ssid) if ssid else Dot11Elt(ID=0)
```

- **ID=0**: SSID element identifier
- **info**: SSID string, empty string indicates wildcard

### 2. Supported Rates Elements
```python
def create_supportedRates(rates_str):
    """Create supported rates element"""
    rates = parse_rates(rates_str)
    return Dot11EltRates(ID=1, rates=rates)

def create_extendedSupportedRates(rates_str):
    """Create extended supported rates element"""
    rates = parse_rates(rates_str)
    return Dot11EltRates(ID=50, rates=rates)
```

**Rate Parsing**:
```python
def parse_rates(rates_str):
    """Parse rate string "6:0.25/9:0.25/12:0.25/18:0.25" """
    pairs = rates_str.split("/")
    rates = []
    for pair in pairs:
        rate, _ = pair.split(":")  # Ignore probability, only take rate value
        rates.append(int(rate))
    return rates
```

### 3. Channel Parameter Element
```python
def create_DSSSparameterSet(channel):
    """Create DSSS parameter set element"""
    return Dot11EltDSSSet(channel=channel)
```

- **Function**: Indicates current operating channel
- **Applicable**: 2.4GHz DSSS/CCK modulation

### 4. Wireless Capability Elements

#### HT Capabilities
```python
def create_HTcapabilities(HT_info):
    """Create HT capabilities element"""
    return Dot11Elt(ID=45, info=HT_info)
```

#### VHT Capabilities
```python
def create_VHTcapabilities(VHT_capabilities):
    """Create VHT capabilities element"""
    return Dot11Elt(ID=191, info=VHT_capabilities)
```

#### Extended Capabilities
```python
def create_Extendendcapabilities(extended_capabilities):
    """Create extended capabilities element"""
    return Dot11Elt(ID=127, info=extended_capabilities)
```

### 5. Vendor Specific Elements

#### Basic Vendor Element
```python
def create_vendorSpecific(vendor):
    """Create vendor specific element"""
    mac, name = get_oui(vendor)
    return Dot11EltVendorSpecific(
        ID=221, 
        oui=int(mac.replace(":", ""), 16),
        info='\x00\x00\x00\x00'
    )
```

#### WPS Related Elements
```python
def create_wps_uuide(wps, uuide):
    """Create WPS and UUID-E elements"""
    wps_element = Dot11EltVendorSpecific(ID=221, info=wps)
    uuide_element = Dot11EltVendorSpecific(ID=221, info=uuide)
    return wps_element, uuide_element
```

## Burst Generation Mechanism

### Sequence Number Management
```python
# Initial sequence number generation
if seq_number == 0:
    seq_number = random.randint(0, 4095 - int(burst_length))

# Sequence number increment within burst
for i in range(1, int(burst_length)):
    dot11burst, seq_number, mac_address = create_80211(
        vendor, randomization, 
        seq_number + 1,  # Increment sequence number
        mac_address, burst_length
    )
```

### Timestamp Assignment
```python
# First frame timestamp
t_ref = time.timestamp()
frame.time = t_ref

# Subsequent frame timestamps (add interval)
for i in range(1, int(burst_length)):
    t_ref += inter_pkt_time
    frame.time = t_ref
```

### MAC Address Processing
```python
# Process MAC address based on randomization strategy
if mac_address == "":
    mac_address = random_MAC().lower()
    if randomization == 0:  # Use vendor OUI
        vendor_oui = get_oui(vendor)[0].lower()
        if vendor_oui:
            mac_address = vendor_oui + ":%02x:%02x:%02x" % (
                random.randint(0,255), 
                random.randint(0,255), 
                random.randint(0,255)
            )
```

## Usage Examples

### Basic Usage
```python
from kernel_driver import create_probe
from datetime import datetime

# Create Probe Request burst
mac_addr, packets = create_probe(
    vendor="Apple",
    randomization=1,
    ssid=["WiFi-Network"],
    burst_length=3,
    mac_address="",  # Auto-generate
    inter_pkt_time=0.02,
    VHT_capabilities=None,
    extended_capabilities=b'\x2d\x01\x02',
    HT_capabilities=b'\x00\x6f',
    wps=None,
    uuide=None,
    time=datetime.now(),
    channel=6,
    supported_rates="6:1.0/12:1.0",
    ext_supported_rates="24:1.0"
)

print(f"Generated MAC Address: {mac_addr}")
print(f"Generated Frames: {len(packets)}")
```

### Advanced Configuration
```python
# Device with VHT capabilities
vht_cap = bytes.fromhex('b0b1b2b3b4b5b6b7b8b9babbbcbdbebf')
ht_cap = bytes.fromhex('2d1a6f0a2040ffff0000000000000000')
ext_cap = bytes.fromhex('0102040800000040')

mac_addr, packets = create_probe(
    vendor="Samsung",
    randomization=2,  # OUI-preserved randomization
    ssid=["Office-WiFi", "Guest-Network"],
    burst_length=2,
    mac_address="",
    inter_pkt_time=0.025,
    VHT_capabilities=vht_cap,
    extended_capabilities=ext_cap,
    HT_capabilities=ht_cap,
    wps=bytes.fromhex('deadbeefcafebabe'),
    uuide=bytes.fromhex('0123456789abcdef'),
    time=datetime.now(),
    channel=11,
    supported_rates="6:0.5/9:0.3/12:0.2",
    ext_supported_rates="18:0.4/24:0.6"
)
```

### Batch Generation
```python
def generate_device_burst(device_config):
    """Generate burst based on device configuration"""
    bursts = []
    
    for i in range(device_config['num_bursts']):
        mac_addr, packets = create_probe(**device_config['params'])
        bursts.extend(packets)
        
        # Update timestamp and sequence number
        device_config['params']['time'] += timedelta(
            seconds=device_config['burst_interval']
        )
    
    return bursts
```

## Frame Validation and Debugging

### Frame Structure Validation
```python
def validate_frame(packet):
    """Validate generated frame structure"""
    if not packet.haslayer(Dot11):
        return False, "Missing 802.11 layer"
    
    dot11 = packet[Dot11]
    if dot11.type != 0 or dot11.subtype != 4:
        return False, "Not a Probe Request frame"
    
    if not packet.haslayer(Dot11ProbeReq):
        return False, "Missing Probe Request layer"
    
    return True, "Frame structure correct"
```

### Information Element Enumeration
```python
def enumerate_elements(packet):
    """Enumerate all information elements in frame"""
    elements = []
    elt = packet.getlayer(Dot11Elt)
    
    while elt:
        elements.append({
            'id': elt.ID,
            'length': len(elt.info) if elt.info else 0,
            'info': elt.info.hex() if elt.info else ''
        })
        elt = elt.payload.getlayer(Dot11Elt)
    
    return elements
```

### Performance Analysis
```python
import time

def benchmark_frame_generation(num_frames=1000):
    """Benchmark frame generation performance"""
    start_time = time.time()
    
    for i in range(num_frames):
        create_probe(
            vendor="Apple", randomization=1, ssid=["test"],
            burst_length=1, mac_address="", inter_pkt_time=0.02,
            VHT_capabilities=None, extended_capabilities=b'\x00',
            HT_capabilities=b'\x00', wps=None, uuide=None,
            time=datetime.now(), channel=6,
            supported_rates="6:1.0", ext_supported_rates=""
        )
    
    elapsed = time.time() - start_time
    print(f"Generated {num_frames} frames in: {elapsed:.3f} seconds")
    print(f"Average per frame: {elapsed/num_frames*1000:.3f} milliseconds")
```

## Extension and Customization

### New Information Element Support
```python
def create_custom_element(element_id, data):
    """Create custom information element"""
    return Dot11Elt(ID=element_id, info=data)

# Example: Create Power Capability element
def create_power_capability(min_power, max_power):
    """Create power capability element"""
    data = bytes([min_power, max_power])
    return create_custom_element(33, data)  # ID=33
```

### Multi-band Support
```python
def create_radio_5ghz(channel):
    """Create 5GHz RadioTap header"""
    frequency = 5000 + channel * 5  # 5GHz frequency calculation
    return RadioTap(
        present='TSFT+Flags+Rate+Channel+dBm_AntSignal+Antenna',
        Flags='',
        Rate=6.0,  # 5GHz minimum rate usually 6Mbps
        ChannelFrequency=frequency,
        ChannelFlags='OFDM+5GHz',  # 5GHz uses OFDM
        dBm_AntSignal=-random.randint(20,60),
        Antenna=0
    )
```

### Frame Encryption Simulation
```python
def add_privacy_flag(dot11_frame):
    """Add privacy protection flag"""
    dot11_frame.FCfield |= 0x40  # Set Privacy bit
    return dot11_frame

def create_encrypted_probe(base_params):
    """Create encrypted Probe Request (simulation)"""
    # Note: Real encryption requires complete key management
    # This only sets the Privacy flag bit
    pass
```

This module is one of the core components of the WiFi simulation system, responsible for generating highly realistic 802.11 Probe Request frames, providing accurate packet foundation for upper-layer simulation.
