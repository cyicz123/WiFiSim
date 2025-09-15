import numpy as np
import math
from collections import Counter
from scapy.all import rdpcap, Dot11


def compute_update_cycle(timestamps):
    """
    计算平均相邻帧时间间隔，作为MAC地址更新周期的近似指标
    """
    if len(timestamps) < 2:
        return None
    ts_sorted = sorted([float(ts) for ts in timestamps])
    diffs = np.diff(ts_sorted)
    return np.mean(diffs)


def compute_mac_de(mac_list):
    """
    计算MAC地址分布归一化熵 (MAE)
    """
    if len(mac_list) == 0:
        return None
    counts = Counter(mac_list)
    total = sum(counts.values())
    probs = np.array(list(counts.values())) / total
    entropy = -np.sum(probs * np.log(probs))
    N = len(counts)
    if N > 1:
        normalized_entropy = entropy / np.log(N)
    else:
        normalized_entropy = 1.0
    return normalized_entropy


def compute_mac_change_rate(macs, total_time):
    """
    计算MAC变化率 (MCR)：单位时间内MAC地址变化次数
    """
    if len(macs) < 2 or total_time == 0:
        return 0
    changes = sum(1 for i in range(1, len(macs)) if macs[i] != macs[i - 1])
    return changes / total_time


def compute_numr(macs):
    """
    计算归一化唯一MAC比例 (NUMR)：唯一MAC数 / 总帧数
    """
    if len(macs) == 0:
        return 0
    unique_count = len(set(macs))
    return unique_count / len(macs)


def compute_mciv(timestamps, macs):
    """
    计算MAC变化间隔方差 (MCIV)
    对于每次MAC切换，计算相邻切换间隔的时间差，返回这些时间差的方差
    """
    intervals = []
    for i in range(1, len(macs)):
        if macs[i] != macs[i - 1]:
            # 记录MAC变化的时间间隔
            intervals.append(timestamps[i] - timestamps[i - 1])
    if len(intervals) < 2:
        return 0
    return np.var(intervals)


def process_pcap(pcap_file, segment_seconds):
    """
    读取 pcap 文件，按指定时间段划分，返回各时间段内的平均更新周期 (T)、MAC地址熵 (DE)、
    MAC变化率 (MCR)、归一化唯一MAC比例 (NUMR) 及MAC变化间隔方差 (MCIV)。
    对时间戳进行对齐处理，即以最早时间为0点。
    :param pcap_file: pcap 文件路径
    :param segment_seconds: 分段时长，单位秒
    :return: 字典 {segment_index: {'T': update_cycle, 'DE': mac_de, 'MCR': mac_change_rate, 'NUMR': numr, 'MCIV': mciv}}
    """
    packets = rdpcap(pcap_file)
    data = []
    for pkt in packets:
        if pkt.haslayer(Dot11):
            if pkt.type == 0 and pkt.subtype == 4:  # Probe Request帧
                ts = pkt.time
                src_mac = pkt.addr2
                data.append((ts, src_mac))
    if not data:
        return {}
    data.sort(key=lambda x: x[0])
    start_time = data[0][0]
    data_aligned = [(float(ts) - float(start_time), mac) for ts, mac in data]

    segments = {}
    for ts, mac in data_aligned:
        seg_idx = int(ts // segment_seconds)
        if seg_idx not in segments:
            segments[seg_idx] = {'timestamps': [], 'macs': []}
        segments[seg_idx]['timestamps'].append(ts)
        segments[seg_idx]['macs'].append(mac)

    results = {}
    for seg, vals in segments.items():
        T = compute_update_cycle(vals['timestamps'])
        DE = compute_mac_de(vals['macs'])
        MCR = compute_mac_change_rate(vals['macs'], segment_seconds)
        NUMR = compute_numr(vals['macs'])
        MCIV = compute_mciv(vals['timestamps'], vals['macs'])
        results[seg] = {'T': T, 'DE': DE, 'MCR': MCR, 'NUMR': NUMR, 'MCIV': MCIV}
    return results


def compute_mac_rca(T_sim, T_real):
    """
    计算MAC随机周期准确率 (MRCA)
    :param T_sim: 仿真数据的平均更新周期
    :param T_real: 真实数据的平均更新周期
    :return: MRCA值
    """
    if T_real is None or T_real == 0:
        return None
    return 1 - abs(T_sim - T_real) / T_real


if __name__ == "__main__":
    # 定义时间段（秒）：10, 20, 30, 60 分钟
    segments = [300, 600, 900, 1200]

    real_pcap = r"D:\lunwen\数据集代码_王敏\代码\probe_request_simulation2\data_devB_dataset_merged.pcap"
    sim_pcap = r"D:\lunwen\数据集代码_王敏\代码\probe_request_simulation2\out_file_run_1.pcap"

    for seg_time in segments:
        print(f"\n=== Time Segment: {seg_time / 60:.0f} minutes ===")
        real_results = process_pcap(real_pcap, seg_time)
        sim_results = process_pcap(sim_pcap, seg_time)

        # 针对每个段，取所有时间窗口的均值作为全局指标
        real_T_values = [v['T'] for v in real_results.values() if v['T'] is not None]
        real_DE_values = [v['DE'] for v in real_results.values() if v['DE'] is not None]
        real_MCR_values = [v['MCR'] for v in real_results.values()]
        real_NUMR_values = [v['NUMR'] for v in real_results.values()]
        real_MCIV_values = [v['MCIV'] for v in real_results.values()]

        sim_T_values = [v['T'] for v in sim_results.values() if v['T'] is not None]
        sim_DE_values = [v['DE'] for v in sim_results.values() if v['DE'] is not None]
        sim_MCR_values = [v['MCR'] for v in sim_results.values()]
        sim_NUMR_values = [v['NUMR'] for v in sim_results.values()]
        sim_MCIV_values = [v['MCIV'] for v in sim_results.values()]

        if real_T_values and sim_T_values:
            real_T_mean = np.mean(real_T_values)
            sim_T_mean = np.mean(sim_T_values)
            mac_rca = compute_mac_rca(sim_T_mean, real_T_mean)
            print(f"Real Update Cycle (T): {real_T_mean:.2f} s")
            print(f"Simulated Update Cycle (T): {sim_T_mean:.2f} s")
            print(f"MAC-RCA (MRCA): {mac_rca:.2f}")
        else:
            print("Insufficient data for update cycle computation.")

        if real_DE_values and sim_DE_values:
            real_DE_mean = np.mean(real_DE_values)
            sim_DE_mean = np.mean(sim_DE_values)
            print(f"Real MAC Entropy (MAE): {real_DE_mean:.2f}")
            print(f"Simulated MAC Entropy (MAE): {sim_DE_mean:.2f}")
        else:
            print("Insufficient data for MAC entropy computation.")

        if real_MCR_values and sim_MCR_values:
            real_MCR_mean = np.mean(real_MCR_values)
            sim_MCR_mean = np.mean(sim_MCR_values)
            print(f"Real MAC Change Rate (MCR): {real_MCR_mean:.2f} changes/s")
            print(f"Simulated MAC Change Rate (MCR): {sim_MCR_mean:.2f} changes/s")
        else:
            print("Insufficient data for MAC change rate computation.")

        if real_NUMR_values and sim_NUMR_values:
            real_NUMR_mean = np.mean(real_NUMR_values)
            sim_NUMR_mean = np.mean(sim_NUMR_values)
            print(f"Real Unique MAC Ratio (NUMR): {real_NUMR_mean:.2f}")
            print(f"Simulated Unique MAC Ratio (NUMR): {sim_NUMR_mean:.2f}")
        else:
            print("Insufficient data for NUMR computation.")

        if real_MCIV_values and sim_MCIV_values:
            real_MCIV_mean = np.mean(real_MCIV_values)
            sim_MCIV_mean = np.mean(sim_MCIV_values)
            print(f"Real MAC Change Interval Variance (MCIV): {real_MCIV_mean:.2f}")
            print(f"Simulated MAC Change Interval Variance (MCIV): {sim_MCIV_mean:.2f}")
        else:
            print("Insufficient data for MCIV computation.")
