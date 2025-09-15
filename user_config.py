#!/usr/bin/env python3
import random

# —— 预处理 OUI 数据 ——
# 从 'oui.txt' 中提取 OUI 信息，生成 'oui_hex.txt'
with open('oui.txt', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()
    count = 0
    # 初始化输出文件（覆盖旧数据）
    with open('oui_hex.txt', 'w', encoding='utf-8') as f_out:
        for line in lines:
            l = line.strip().split("\t")
            if "(hex)" in line:
                count += 1
                f_out.write(l[0][0:8] + "\t" + l[2] + "\n")
print("Processed OUI count:", count)

# —— 以下是用户配置阶段生成设备配置文件 1.txt 和 2.txt 的代码 ——
# 修改后的模板：
# 1.txt 包含：厂商, 设备名称, burst 长度分布, mac_policy, VHT 能力, 扩展能力, HT 能力, 支持速率, 扩展支持速率
TEMPLATE_1 = ("# vendor name, device_name, burst length (value:probability/value:probability/...), "
              "mac_policy, VHT capabilities, extended capabilities, HT capabilities, "
              "supported_rates (Mbps), ext_supported_rates (Mbps)\n")
# 2.txt 包含：设备名称, Phase, burst 内包间隔分布, burst 间包间隔分布, 状态持续时间分布, 包间隔抖动分布
TEMPLATE_2 = ("# device_name, Phase (0 Locked 1 Awake 2 Active), "
              "intra-burst interval (value:probability/value:probability/... ), "
              "inter-burst interval (value:probability/value:probability/... ), "
              "state dwell time (value:probability/... ), "
              "jitter (value:probability/... )\n")

# 初始化文件（覆盖旧数据）
with open('1.txt', 'w') as f:
    f.write(TEMPLATE_1)
with open('2.txt', 'w') as f:
    f.write(TEMPLATE_2)

# 厂商与设备型号映射
vendor_device_map = {
    'OnePlus': ['nord 5g', 'one plus9pro', 'one plus9rt', 'one plus8t', 'one plus8pro', 'one plus8', 'one plus7t',
                'one plus7pro', 'one plus ace', 'one plus Nord'],
    'Samsung': ['note20ultra', 'galaxys21', 'galaxys20fe', 'galaxys20', 'galaxys10', 'galaxys9', 'galaxys8',
                'galaxys7edge', 'galaxys7', 'galaxys6edge'],
    'Xiaomi': ['note8t', 'mi9lite', 'mi10lite', 'mi9pro', 'mi9se', 'mi8lite', 'mi8pro', 'mi8ud', 'redmi note10pro',
               'redmi note9pro'],
    'Huawei': ['p9lite', 'p40lite', 'p30lite', 'p20pro', 'p10plus', 'p10lite', 'nova8pro', 'nova7pro', 'mate30pro',
               'mate20x'],
    'Lenovo': ['think pad x13gen1', 'think pad x1yoga', 'think pad x1carbon', 'think pad t14gen1', 'think pad t14sgen1',
               'think pad p15gen1', 'think pad p53', 'think pad x28 gen1', 'think pad new x1 carbon gen 9',
               'lenovo think book 14p', 'lenovo think book 13s'],
    'OPPO': ['find x3pro', 'find x5pro', 'oppo find x4pro', 'oppo encofree', 'oppo ace2', 'oppo ace2neo', 'oppo a93',
             'oppo a95', 'oppo a16', 'oppo a1pro'],
    'vivo': ['x60', 'x60pro', 'x60t', 'x60u', 'x60pro+', 'x70', 'x70pro', 'x70pro+', 'x80', 'x80pro'],
    'Realme': ['gt neo2', 'gt neo2t', 'gt neo3', 'gt neo3neos', 'gt neo3pro', 'gt neo4', 'gt neo4pro', 'Realme q3i',
               'Realme q3pro', 'Realme q5'],
    'iQOO': ['iQOO 7', 'iQOO Neo5', 'iQOO Neo5s', 'iQOO Neo6', 'iQOO Neo6se', 'iQOO Neo7', 'iQOO Neo7se', 'iQOO 10',
             'iQOO 10pro', 'iQOO U5'],
    'honor': ['honor9x', 'honor90', 'honor91', 'honor92', 'honor93', 'honor94', 'honor95', 'honor96', 'honor97',
              'honor98'],
    'MeiZu': ['18', '18s', '18plus', '18v', '18lite'],
    'Nubia': ['red magic7', 'red magic7pro', 'red magic7s', 'red magic7mini'],
}

def get_device_name(vendor):
    return random.choice(vendor_device_map.get(vendor, ["default_device"]))

# 修改后的能力字段生成函数（符合真实设备要求）：
# VHT 能力：70% 概率不支持（返回 "?"），否则生成 8 字节（16 个十六进制字符）
def generate_vht_capabilities():
    if random.random() < 0.7:
        return "?"
    else:
        return ''.join(random.choices('0123456789abcdef', k=16))

# 扩展能力：生成 6 字节（12 个十六进制字符）
def generate_extended_capabilities():
    return ''.join(random.choices('0123456789abcdef', k=12))

# HT 能力：生成 8 字节（16 个十六进制字符）
def generate_ht_capabilities():
    return ''.join(random.choices('0123456789abcdef', k=16))

# 生成 MAC 策略：0 - 永久 MAC, 1 - 完全随机, 2 - 随机但保留 OUI, 3 - 专用/预生成 MAC
def generate_mac_policy():
    return random.choice([0, 1, 2, 3])

# 固定的 MAC 地址配置（可由用户修改）
PERMANENT_MAC = "00:11:22:33:44:55"
DEDICATED_MAC = "02:12:34:56:78:9a"
MAC_MASK = "ff:ff:ff:00:00:00"

# 生成支持速率配置：支持速率和扩展支持速率，均采用“速率:概率”格式
def generate_supported_rates():
    # 例如，设备可能支持 6,9,12,18 Mbps，以随机概率分布给出
    rates = [6, 9, 12, 18]
    probs = [round(random.uniform(0.1, 1), 2) for _ in rates]
    total = sum(probs)
    probs = [round(p/total, 2) for p in probs]
    return '/'.join(f"{r}:{p}" for r, p in zip(rates, probs))

def generate_ext_supported_rates():
    rates = [24, 36]
    probs = [round(random.uniform(0.1, 1), 2) for _ in rates]
    total = sum(probs)
    probs = [round(p/total, 2) for p in probs]
    return '/'.join(f"{r}:{p}" for r, p in zip(rates, probs))

# 生成状态持续时间分布：单位秒
def generate_state_dwell():
    # 例如，每个状态可能持续 5 到 60 秒之间
    dwell_times = [5, 10, 20, 30, 45, 60]
    probs = [round(random.uniform(0.1, 1), 2) for _ in dwell_times]
    total = sum(probs)
    probs = [round(p/total, 2) for p in probs]
    return '/'.join(f"{t}:{p}" for t, p in zip(dwell_times, probs))

# 生成包间隔抖动分布（单位秒）
def generate_jitter():
    jitters = [0.01, 0.05, 0.1, 0.2]
    probs = [round(random.uniform(0.1, 1), 2) for _ in jitters]
    total = sum(probs)
    probs = [round(p/total, 2) for p in probs]
    return '/'.join(f"{j}:{p}" for j, p in zip(jitters, probs))

# 修改 burst 参数以符合真实设备 Probe burst 特性：
# － burst 内部间隔设为 20～100 毫秒之间
# － burst 之间间隔设为 2～5 秒之间
# － burst 长度限定为 1～3 帧
for i in range(100):
    vendor_name = random.choice(list(vendor_device_map.keys()))
    device_name = get_device_name(vendor_name)

    for phase in range(3):
        burst_time_in = '/'.join(
            f"{round(random.uniform(0.02, 0.1)*100)/100}" + ":" + f"{round(random.uniform(0.1, 1)*100)/100}"
            for _ in range(random.randint(1, 3))
        )
        burst_time_between = '/'.join(
            f"{round(random.uniform(2, 5)*100)/100}" + ":" + f"{round(random.uniform(0.1, 1)*100)/100}"
            for _ in range(random.randint(1, 3))
        )
        state_dwell = generate_state_dwell()
        jitter = generate_jitter()
        with open('2.txt', 'a') as f2:
            f2.write(f"{device_name},{phase},{burst_time_in},{burst_time_between},{state_dwell},{jitter}\n")

    burst_length = '/'.join(
        f"{b}:{round(random.uniform(0.1, 0.9)*100)/100}" for b in range(1, random.randint(2, 4))
    )
    mac_policy = generate_mac_policy()
    vht_cap = generate_vht_capabilities()
    ext_cap = generate_extended_capabilities()
    ht_cap = generate_ht_capabilities()
    supported_rates = generate_supported_rates()
    ext_supported_rates = generate_ext_supported_rates()

    with open('1.txt', 'a') as f1:
        f1.write(f"{vendor_name},{device_name},{burst_length},{mac_policy},{vht_cap},{ext_cap},{ht_cap},"
                 f"{supported_rates},{ext_supported_rates}\n")