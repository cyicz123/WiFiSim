# capture_parsing.py - 数据包捕获与解析工具

## 概述

`capture_parsing.py` 是WiFi仿真系统的数据包解析模块，提供对生成的Probe Request帧进行捕获、解析和质量检查的功能，模拟真实网络监控设备的行为。

## 核心功能

### 1. 帧捕获模拟

#### CapturedFrame 类
```python
class CapturedFrame:
    def __init__(self, frame, rssi):
        self.frame = frame    # 原始帧数据
        self.rssi = rssi      # 接收信号强度指示
```

**属性说明**：
- `frame`：Scapy数据包对象，包含完整的帧结构
- `rssi`：接收信号强度，单位dBm，范围通常为-40到-90dBm

#### 帧捕获函数
```python
def capture_frame(frame):
    """模拟帧捕获过程"""
    # 为帧分配随机RSSI值
    rssi = -(40 + random.randint(0, 50))  # -40到-90 dBm
    return CapturedFrame(frame, rssi)
```

**RSSI模拟特点**：
- 范围：-40dBm（强信号）到-90dBm（弱信号）
- 随机分布：模拟真实环境中的信号强度变化
- 用途：后续可用于信号质量分析和过滤

### 2. 帧解析与分析

#### 主解析函数
```python
def parse_captured_frame(captured):
    """解析捕获的Probe Request帧"""
    print("捕获到 Probe Request 帧：")
    
    # 显示帧的十六进制转储
    hexdump(captured.frame)
    
    # 解析各层协议信息
    parse_dot11_header(captured.frame)
    parse_information_elements(captured.frame)
    
    print(f"捕获时 RSSI: {captured.rssi} dBm")
```

### 3. 802.11头部解析

#### 基本头部信息
```python
if captured.frame.haslayer(Dot11):
    dot11 = captured.frame.getlayer(Dot11)
    print(f"源 MAC地址: {dot11.addr2}")      # 发送设备MAC
    print(f"目标 MAC地址: {dot11.addr1}")    # 通常为广播地址
    print(f"BSSID: {dot11.addr3}")          # 基站标识
    print(f"序列号: {dot11.SC}")             # 序列控制字段
```

**地址字段含义**：
- `addr1`：目标地址，Probe Request中为广播地址(ff:ff:ff:ff:ff:ff)
- `addr2`：源地址，即发送设备的MAC地址
- `addr3`：BSSID，Probe Request中通常为广播地址

### 4. 信息元素解析

#### 元素遍历机制
```python
elt = captured.frame.getlayer(Dot11Elt)
while elt:
    parse_single_element(elt)
    elt = elt.payload.getlayer(Dot11Elt)  # 获取下一个元素
```

#### 具体元素解析

##### SSID元素 (ID=0)
```python
if elt.ID == 0:
    try:
        ssid = elt.info.decode(errors="ignore")
    except Exception:
        ssid = elt.info
    print(f"SSID: {ssid}")
```

**特殊情况**：
- 空SSID：表示通配符扫描
- 非UTF-8编码：使用错误忽略模式解码
- 隐藏SSID：长度为0的SSID字段

##### 支持速率元素 (ID=1)
```python
elif elt.ID == 1:
    # 速率以0.5 Mbps为单位编码
    rates = [f"{r / 2:.1f}" for r in elt.rates]
    print("支持速率:", " ".join(rates), "Mbps")
```

**速率编码**：
- 原始值以0.5Mbps为单位
- 显示时转换为实际Mbps值
- 例：0x0c → 6Mbps, 0x12 → 9Mbps

##### 扩展支持速率元素 (ID=50)
```python
elif elt.ID == 50:
    ext_rates = [f"{r / 2:.1f}" for r in elt.rates]
    print("扩展支持速率:", " ".join(ext_rates), "Mbps")
```

##### 无线能力元素
```python
elif elt.ID == 45:
    print("HT 能力:", elt.info.hex())       # HT能力

elif elt.ID == 191:
    print("VHT 能力:", elt.info.hex())      # VHT能力

elif elt.ID == 127:
    print("扩展能力:", elt.info.hex())      # 扩展能力
```

##### 厂商特定元素 (ID=221)
```python
elif elt.ID == 221:
    print("Vendor Specific:", elt.info.hex())
    # 可能包含WPS、P2P等厂商特定信息
```

## 使用示例

### 基本解析流程
```python
from capture_parsing import capture_frame, parse_captured_frame
from scapy.all import rdpcap

# 读取PCAP文件
packets = rdpcap("simulation_output.pcap")

for packet in packets:
    if packet.haslayer(Dot11) and packet.type == 0 and packet.subtype == 4:
        # 模拟捕获过程
        captured = capture_frame(packet)
        
        # 解析帧内容
        parse_captured_frame(captured)
        print("-" * 50)
```

### 批量质量检查
```python
def quality_check_batch(pcap_file, sample_rate=0.1):
    """对PCAP文件进行批量质量检查"""
    packets = rdpcap(pcap_file)
    probe_requests = [p for p in packets if is_probe_request(p)]
    
    # 按采样率选择帧进行检查
    sample_size = int(len(probe_requests) * sample_rate)
    sampled_packets = random.sample(probe_requests, sample_size)
    
    for packet in sampled_packets:
        captured = capture_frame(packet)
        try:
            parse_captured_frame(captured)
        except Exception as e:
            print(f"解析错误: {e}")
```

### 信号质量分析
```python
def analyze_signal_quality(captured_frames):
    """分析捕获帧的信号质量分布"""
    rssi_values = [cf.rssi for cf in captured_frames]
    
    print(f"RSSI统计:")
    print(f"  平均值: {np.mean(rssi_values):.1f} dBm")
    print(f"  标准差: {np.std(rssi_values):.1f} dB")
    print(f"  最强信号: {max(rssi_values):.1f} dBm")
    print(f"  最弱信号: {min(rssi_values):.1f} dBm")
    
    # 信号强度分级
    strong = sum(1 for rssi in rssi_values if rssi > -50)
    medium = sum(1 for rssi in rssi_values if -70 <= rssi <= -50)
    weak = sum(1 for rssi in rssi_values if rssi < -70)
    
    total = len(rssi_values)
    print(f"信号分布:")
    print(f"  强信号 (>-50dBm): {strong} ({strong/total:.1%})")
    print(f"  中等信号 (-70~-50dBm): {medium} ({medium/total:.1%})")
    print(f"  弱信号 (<-70dBm): {weak} ({weak/total:.1%})")
```

## 高级解析功能

### 设备指纹识别
```python
def extract_device_fingerprint(captured_frame):
    """提取设备指纹特征"""
    fingerprint = {
        'mac_oui': captured_frame.frame[Dot11].addr2[:8],  # OUI前缀
        'supported_rates': [],
        'capabilities': {},
        'vendor_elements': []
    }
    
    # 遍历信息元素提取特征
    elt = captured_frame.frame.getlayer(Dot11Elt)
    while elt:
        if elt.ID == 1:  # 支持速率
            fingerprint['supported_rates'] = list(elt.rates)
        elif elt.ID == 45:  # HT能力
            fingerprint['capabilities']['ht'] = elt.info.hex()
        elif elt.ID == 191:  # VHT能力
            fingerprint['capabilities']['vht'] = elt.info.hex()
        elif elt.ID == 221:  # 厂商特定
            fingerprint['vendor_elements'].append(elt.info.hex())
        
        elt = elt.payload.getlayer(Dot11Elt)
    
    return fingerprint
```

### 异常帧检测
```python
def detect_anomalies(captured_frame):
    """检测异常帧"""
    anomalies = []
    frame = captured_frame.frame
    
    # 检查基本结构
    if not frame.haslayer(Dot11):
        anomalies.append("缺少802.11头部")
        return anomalies
    
    dot11 = frame[Dot11]
    
    # 检查帧类型
    if dot11.type != 0 or dot11.subtype != 4:
        anomalies.append("不是Probe Request帧")
    
    # 检查地址字段
    if dot11.addr1 != "ff:ff:ff:ff:ff:ff":
        anomalies.append("目标地址不是广播地址")
    
    if not is_valid_mac(dot11.addr2):
        anomalies.append("源MAC地址格式异常")
    
    # 检查信息元素
    if not frame.haslayer(Dot11Elt):
        anomalies.append("缺少信息元素")
    
    return anomalies

def is_valid_mac(mac_str):
    """验证MAC地址格式"""
    import re
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(pattern, mac_str))
```

### 时序分析
```python
def analyze_timing_patterns(captured_frames):
    """分析帧的时序模式"""
    timestamps = [cf.frame.time for cf in captured_frames]
    intervals = np.diff(sorted(timestamps))
    
    # Burst检测
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
    
    print(f"检测到 {len(bursts)} 个burst")
    print(f"平均burst长度: {np.mean([len(b) for b in bursts]):.1f}")
    print(f"平均帧间隔: {np.mean(intervals):.3f}s")
    print(f"间隔标准差: {np.std(intervals):.3f}s")
```

## 调试和诊断

### 详细帧转储
```python
def detailed_frame_dump(captured_frame):
    """详细的帧信息转储"""
    frame = captured_frame.frame
    
    print("=== 帧详细信息 ===")
    print(f"捕获时间: {datetime.fromtimestamp(frame.time)}")
    print(f"帧长度: {len(frame)} 字节")
    print(f"RSSI: {captured_frame.rssi} dBm")
    
    # RadioTap头部
    if frame.haslayer(RadioTap):
        rt = frame[RadioTap]
        print(f"RadioTap长度: {rt.len} 字节")
        print(f"信道频率: {rt.ChannelFrequency} MHz")
        print(f"传输速率: {rt.Rate} Mbps")
    
    # 802.11头部
    if frame.haslayer(Dot11):
        dot11 = frame[Dot11]
        print(f"帧控制: 0x{dot11.FCfield:04x}")
        print(f"序列控制: 0x{dot11.SC:04x}")
        print(f"源地址: {dot11.addr2}")
        print(f"目标地址: {dot11.addr1}")
        print(f"BSSID: {dot11.addr3}")
    
    # 信息元素统计
    element_count = count_information_elements(frame)
    print(f"信息元素数量: {element_count}")
```

### 性能监控
```python
def monitor_parsing_performance():
    """监控解析性能"""
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
            print(f"解析错误: {e}")
    
    # 处理完成后计算统计信息
    elapsed_time = time.time() - start_time
    fps = frame_count / elapsed_time if elapsed_time > 0 else 0
    error_rate = error_count / (frame_count + error_count) if (frame_count + error_count) > 0 else 0
    
    print(f"解析性能统计:")
    print(f"  处理帧数: {frame_count}")
    print(f"  错误帧数: {error_count}")
    print(f"  处理速度: {fps:.1f} 帧/秒")
    print(f"  错误率: {error_rate:.2%}")
```

## 集成与扩展

### 与仿真系统集成
```python
# 在main.py中的使用示例
if random.random() < simulator.scene_params.get("qa_sample_rate", 0.0):
    c = capture_parsing.capture_frame(event.packet)
    capture_parsing.parse_captured_frame(c)
```

### 自定义解析器
```python
def register_custom_parser(element_id, parser_func):
    """注册自定义信息元素解析器"""
    custom_parsers[element_id] = parser_func

def parse_custom_element(elt):
    """解析自定义信息元素"""
    if elt.ID in custom_parsers:
        return custom_parsers[elt.ID](elt)
    else:
        return f"未知元素 ID={elt.ID}: {elt.info.hex()}"
```

这个模块为WiFi仿真系统提供了重要的质量保证功能，通过实时解析和检查生成的数据包，确保仿真结果的准确性和可靠性。
