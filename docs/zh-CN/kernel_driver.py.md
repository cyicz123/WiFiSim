# kernel_driver.py - 内核驱动层802.11帧生成

## 概述

`kernel_driver.py` 模拟WiFi设备的内核驱动层功能，负责生成符合IEEE 802.11标准的Probe Request帧，包括RadioTap头、802.11管理帧头以及各种信息元素(Information Elements)。

## 核心功能

### 1. Probe Request帧构建

#### 主函数：create_probe()
```python
def create_probe(vendor, randomization, ssid, burst_length, mac_address, 
                inter_pkt_time, VHT_capabilities, extended_capabilities, 
                HT_capabilities, wps, uuide, time, channel, 
                supported_rates, ext_supported_rates):
    """创建完整的Probe Request burst"""
    # 返回: (mac_address, packets_list)
```

**参数说明**：
- `vendor`：设备厂商名称
- `randomization`：MAC随机化策略
- `ssid`：目标SSID列表
- `burst_length`：burst中的帧数量
- `mac_address`：源MAC地址
- `inter_pkt_time`：帧间间隔时间
- 各种能力字段：VHT、HT、扩展能力等
- `wps/uuide`：WPS相关信息
- `time`：时间戳
- `channel`：工作信道
- `supported_rates`：支持的传输速率

#### 帧结构组装
```python
# 基本帧结构
frame = radio / dot11 / probeReq / elements...

# 带VHT能力的帧
if VHT_capabilities is not None:
    frame = radio / dot11 / probeReq / dot11elt / dot11eltrates / 
            dot11eltratesext / dot11eltdssset / dot11elthtcap / 
            dot11eltVHTcap / dot11eltEXTcap / dot11eltven / [wps/uuide]
```

### 2. RadioTap头生成

```python
def create_radio(channel):
    """创建RadioTap头部"""
    return RadioTap(
        present='TSFT+Flags+Rate+Channel+dBm_AntSignal+Antenna',
        Flags='',
        Rate=1.0,                                    # 传输速率
        ChannelFrequency=get_frequency(channel),     # 信道频率
        ChannelFlags='CCK+2GHz',                     # 信道标志
        dBm_AntSignal=-random.randint(30,70),        # 信号强度
        Antenna=0                                    # 天线编号
    )
```

**RadioTap字段**：
- `TSFT`：时间戳
- `Flags`：帧标志
- `Rate`：传输速率（Mbps）
- `Channel`：信道信息（频率+标志）
- `dBm_AntSignal`：接收信号强度指示(RSSI)
- `Antenna`：天线编号

### 3. 802.11管理帧头

```python
def create_80211(vendor, randomization, seq_number, mac_address, burst_length):
    """创建802.11管理帧头"""
    return Dot11(
        addr1='ff:ff:ff:ff:ff:ff',    # 目标地址（广播）
        addr2=mac_address,            # 源地址
        addr3='ff:ff:ff:ff:ff:ff',    # BSSID（广播）
        SC=produce_sequenceNumber(0, seq_number)  # 序列控制
    )
```

**地址字段**：
- `addr1`：目标地址，Probe Request使用广播地址
- `addr2`：源地址，发送设备的MAC地址
- `addr3`：BSSID，Probe Request中通常为广播地址

**序列控制**：
- 序列号：唯一标识帧序列
- 分片号：通常为0（不分片）

## 信息元素(Information Elements)

### 1. SSID元素
```python
def create_informationElement(ssid):
    """创建SSID信息元素"""
    return Dot11Elt(ID=0, info=ssid) if ssid else Dot11Elt(ID=0)
```

- **ID=0**：SSID元素标识符
- **info**：SSID字符串，空字符串表示通配符

### 2. 支持速率元素
```python
def create_supportedRates(rates_str):
    """创建支持速率元素"""
    rates = parse_rates(rates_str)
    return Dot11EltRates(ID=1, rates=rates)

def create_extendedSupportedRates(rates_str):
    """创建扩展支持速率元素"""
    rates = parse_rates(rates_str)
    return Dot11EltRates(ID=50, rates=rates)
```

**速率解析**：
```python
def parse_rates(rates_str):
    """解析速率字符串 "6:0.25/9:0.25/12:0.25/18:0.25" """
    pairs = rates_str.split("/")
    rates = []
    for pair in pairs:
        rate, _ = pair.split(":")  # 忽略概率，只取速率值
        rates.append(int(rate))
    return rates
```

### 3. 信道参数元素
```python
def create_DSSSparameterSet(channel):
    """创建DSSS参数集元素"""
    return Dot11EltDSSSet(channel=channel)
```

- **功能**：指示当前工作信道
- **适用**：2.4GHz DSSS/CCK调制

### 4. 无线能力元素

#### HT能力
```python
def create_HTcapabilities(HT_info):
    """创建HT能力元素"""
    return Dot11Elt(ID=45, info=HT_info)
```

#### VHT能力
```python
def create_VHTcapabilities(VHT_capabilities):
    """创建VHT能力元素"""
    return Dot11Elt(ID=191, info=VHT_capabilities)
```

#### 扩展能力
```python
def create_Extendendcapabilities(extended_capabilities):
    """创建扩展能力元素"""
    return Dot11Elt(ID=127, info=extended_capabilities)
```

### 5. 厂商特定元素

#### 基本厂商元素
```python
def create_vendorSpecific(vendor):
    """创建厂商特定元素"""
    mac, name = get_oui(vendor)
    return Dot11EltVendorSpecific(
        ID=221, 
        oui=int(mac.replace(":", ""), 16),
        info='\x00\x00\x00\x00'
    )
```

#### WPS相关元素
```python
def create_wps_uuide(wps, uuide):
    """创建WPS和UUID-E元素"""
    wps_element = Dot11EltVendorSpecific(ID=221, info=wps)
    uuide_element = Dot11EltVendorSpecific(ID=221, info=uuide)
    return wps_element, uuide_element
```

## Burst生成机制

### 序列号管理
```python
# 初始序列号生成
if seq_number == 0:
    seq_number = random.randint(0, 4095 - int(burst_length))

# Burst内序列号递增
for i in range(1, int(burst_length)):
    dot11burst, seq_number, mac_address = create_80211(
        vendor, randomization, 
        seq_number + 1,  # 递增序列号
        mac_address, burst_length
    )
```

### 时间戳分配
```python
# 第一个帧的时间戳
t_ref = time.timestamp()
frame.time = t_ref

# 后续帧的时间戳（加上间隔）
for i in range(1, int(burst_length)):
    t_ref += inter_pkt_time
    frame.time = t_ref
```

### MAC地址处理
```python
# 根据randomization策略处理MAC地址
if mac_address == "":
    mac_address = random_MAC().lower()
    if randomization == 0:  # 使用厂商OUI
        vendor_oui = get_oui(vendor)[0].lower()
        if vendor_oui:
            mac_address = vendor_oui + ":%02x:%02x:%02x" % (
                random.randint(0,255), 
                random.randint(0,255), 
                random.randint(0,255)
            )
```

## 使用示例

### 基本使用
```python
from kernel_driver import create_probe
from datetime import datetime

# 创建Probe Request burst
mac_addr, packets = create_probe(
    vendor="Apple",
    randomization=1,
    ssid=["WiFi-Network"],
    burst_length=3,
    mac_address="",  # 自动生成
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

print(f"生成MAC地址: {mac_addr}")
print(f"生成帧数: {len(packets)}")
```

### 高级配置
```python
# 带VHT能力的设备
vht_cap = bytes.fromhex('b0b1b2b3b4b5b6b7b8b9babbbcbdbebf')
ht_cap = bytes.fromhex('2d1a6f0a2040ffff0000000000000000')
ext_cap = bytes.fromhex('0102040800000040')

mac_addr, packets = create_probe(
    vendor="Samsung",
    randomization=2,  # 保留OUI的随机化
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

### 批量生成
```python
def generate_device_burst(device_config):
    """根据设备配置生成burst"""
    bursts = []
    
    for i in range(device_config['num_bursts']):
        mac_addr, packets = create_probe(**device_config['params'])
        bursts.extend(packets)
        
        # 更新时间戳和序列号
        device_config['params']['time'] += timedelta(
            seconds=device_config['burst_interval']
        )
    
    return bursts
```

## 帧验证与调试

### 帧结构检查
```python
def validate_frame(packet):
    """验证生成的帧结构"""
    if not packet.haslayer(Dot11):
        return False, "缺少802.11层"
    
    dot11 = packet[Dot11]
    if dot11.type != 0 or dot11.subtype != 4:
        return False, "不是Probe Request帧"
    
    if not packet.haslayer(Dot11ProbeReq):
        return False, "缺少Probe Request层"
    
    return True, "帧结构正确"
```

### 信息元素枚举
```python
def enumerate_elements(packet):
    """枚举帧中的所有信息元素"""
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

### 性能分析
```python
import time

def benchmark_frame_generation(num_frames=1000):
    """基准测试帧生成性能"""
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
    print(f"生成{num_frames}帧耗时: {elapsed:.3f}秒")
    print(f"平均每帧: {elapsed/num_frames*1000:.3f}毫秒")
```

## 扩展与定制

### 新信息元素支持
```python
def create_custom_element(element_id, data):
    """创建自定义信息元素"""
    return Dot11Elt(ID=element_id, info=data)

# 示例：创建Power Capability元素
def create_power_capability(min_power, max_power):
    """创建功率能力元素"""
    data = bytes([min_power, max_power])
    return create_custom_element(33, data)  # ID=33
```

### 多频段支持
```python
def create_radio_5ghz(channel):
    """创建5GHz RadioTap头"""
    frequency = 5000 + channel * 5  # 5GHz频率计算
    return RadioTap(
        present='TSFT+Flags+Rate+Channel+dBm_AntSignal+Antenna',
        Flags='',
        Rate=6.0,  # 5GHz最低速率通常是6Mbps
        ChannelFrequency=frequency,
        ChannelFlags='OFDM+5GHz',  # 5GHz使用OFDM
        dBm_AntSignal=-random.randint(20,60),
        Antenna=0
    )
```

### 帧加密模拟
```python
def add_privacy_flag(dot11_frame):
    """添加隐私保护标志"""
    dot11_frame.FCfield |= 0x40  # 设置Privacy位
    return dot11_frame

def create_encrypted_probe(base_params):
    """创建加密的Probe Request（模拟）"""
    # 注意：真实加密需要完整的密钥管理
    # 这里只是设置Privacy标志位
    pass
```

这个模块是WiFi仿真系统的核心组件之一，负责生成高度真实的802.11 Probe Request帧，为上层仿真提供准确的数据包基础。
