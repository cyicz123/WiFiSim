#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从真实小米 pcap 标定仿真参数，使得 MCR / NUMR / MCIV 拟合到目标值
- 读取一组真实 pcap（Probe Request）
- 计算目标指标：MCR(每分钟), NUMR(唯一MAC/总帧), MCIV(相邻换MAC间隔方差, s^2)
- 反推仿真参数（1.txt, 2.txt）
  * 2.txt：prob_between_bursts（burst 间隔, 受轮换间隔约束）、prob_int_burst（包内间隔）、state_dwell（相位停留）、jitter（抖动）
  * 1.txt：burst_lengths（每个 burst 的包数分布）、randomization=1（本地随机MAC）
- 覆盖指定小米型号条目（若无该型号则添加新条目）
- 备份 1.txt/2.txt 到 .bak
- 可选：立即运行一次仿真并用 shiyan.py 验证三指标差距

依赖：scapy (解析 802.11), numpy, pandas
"""
import os, sys, json, math, shutil, random
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import numpy as np

try:
    from scapy.all import rdpcap, Dot11
except Exception as e:
    print("请先安装 scapy：pip install scapy")
    sys.exit(1)

# --------- 可调参数 ---------
# 判定 burst 内包间隔阈值（秒），小于该阈值视为同一 burst
INTRA_BURST_TH = 0.25
# “相邻换 MAC”间隔 -> 近似 “轮换间隔”
# 我们将其拟合为对数正态分布(离散化后写入 2.txt)
NUM_BINS = 6
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# --------- 指标计算 ---------
def read_probe_seq(pcap_path: Path):
    pkts = rdpcap(str(pcap_path))
    seq = []
    t0 = None
    for p in pkts:
        if not p.haslayer(Dot11):
            continue
        d = p[Dot11]
        # type=0 管理帧, subtype=4 Probe Request
        if getattr(d, "type", None) == 0 and getattr(d, "subtype", None) == 4:
            sa = getattr(d, "addr2", None)
            ts = float(getattr(p, "time", 0.0))
            if sa is None:
                continue
            if t0 is None:
                t0 = ts
            seq.append((ts - t0, sa))
    # 按时间排序
    seq.sort(key=lambda x: x[0])
    return seq  # [(t, mac), ...]

def compute_metrics(seq):
    if not seq:
        return dict(MCR=0.0, NUMR=0.0, MCIV=0.0, avg_intra=0.0, burst_sizes=[], change_intervals=[])
    times = [t for t,_ in seq]
    macs  = [m for _,m in seq]
    n = len(seq)
    # MCR：每分钟的 MAC 变化次数
    changes = 0
    change_times = []
    for i in range(1, n):
        if macs[i] != macs[i-1]:
            changes += 1
            change_times.append(times[i])
    duration = max(1e-6, times[-1] - times[0])
    mcr = changes / max(1.0, duration/60.0)  # 次/分钟

    # NUMR：唯一MAC数 / 总Probe帧数
    numr = len(set(macs)) / float(n) if n>0 else 0.0

    # MCIV：相邻换MAC的时间间隔方差
    change_intervals = np.diff(change_times) if len(change_times) >= 2 else np.array([])
    mciv = float(np.var(change_intervals)) if change_intervals.size>=1 else 0.0

    # 估计 burst 规模与包内间隔
    burst_sizes = []
    intra_gaps = []
    cur_len = 1
    for i in range(1, n):
        gap = times[i] - times[i-1]
        if gap <= INTRA_BURST_TH:
            cur_len += 1
            intra_gaps.append(gap)
        else:
            burst_sizes.append(cur_len)
            cur_len = 1
    burst_sizes.append(cur_len)
    avg_intra = float(np.mean(intra_gaps)) if intra_gaps else 0.05

    return dict(MCR=mcr, NUMR=numr, MCIV=mciv, avg_intra=avg_intra,
                burst_sizes=burst_sizes, change_intervals=change_intervals.tolist())

def aggregate_metrics(pcaps):
    # 对多份 pcap 取中位数/众数等鲁棒统计
    MCRs, NUMRs, MCIVs = [], [], []
    intra_list, all_burst_sizes, all_change_ints = [], [], []
    for p in pcaps:
        seq = read_probe_seq(p)
        m = compute_metrics(seq)
        MCRs.append(m["MCR"]); NUMRs.append(m["NUMR"]); MCIVs.append(m["MCIV"])
        intra_list.append(m["avg_intra"])
        all_burst_sizes += m["burst_sizes"]
        all_change_ints += m["change_intervals"]
    target = {
        "MCR": float(np.median(MCRs)) if MCRs else 0.0,
        "NUMR": float(np.median(NUMRs)) if NUMRs else 0.0,
        "MCIV": float(np.median(MCIVs)) if MCIVs else 0.0,
        "avg_intra": float(np.median(intra_list)) if intra_list else 0.05,
        "burst_sizes": all_burst_sizes,
        "change_intervals": all_change_ints
    }
    return target

# --------- 反推 -> 离散分布（写入 1.txt / 2.txt）---------
def to_discrete_dist(samples, num_bins=NUM_BINS, clip_min=0.02, clip_max=120.0):
    if not samples:
        # 合理兜底：均匀 6 桶
        edges = np.linspace(clip_min, clip_max, num_bins+1)
        probs = np.ones(num_bins) / num_bins
        mids  = 0.5*(edges[1:]+edges[:-1])
        return dict(zip(np.round(mids,3).tolist(), np.round(probs,4).tolist()))
    arr = np.array(samples, dtype=float)
    arr = arr[(arr>=clip_min) & (arr<=clip_max)]
    if arr.size==0:
        arr = np.array([clip_min, clip_max, (clip_min+clip_max)/2])
    hist, edges = np.histogram(arr, bins=num_bins)
    hist = hist.astype(float);
    if hist.sum()==0: hist += 1.0
    probs = hist / hist.sum()
    mids  = 0.5*(edges[1:]+edges[:-1])
    # 规范化到 3 位
    mids = np.round(mids, 3).tolist()
    probs = np.round(probs, 4).tolist()
    return dict(zip(mids, probs))

def burst_len_dist(burst_sizes):
    if not burst_sizes:
        return {1.0:0.2, 2.0:0.5, 3.0:0.3}
    c = Counter(burst_sizes)
    total = sum(c.values())
    keys = sorted(c.keys())
    probs = [c[k]/total for k in keys]
    return {float(k): float(round(p,4)) for k,p in zip(keys, probs)}

# --------- 文本条目读写（1.txt / 2.txt）---------
def load_txt_lines(path: Path):
    return [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines()]

def save_backup_and_write(path: Path, lines):
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        shutil.copyfile(path, bak)
    path.write_text("\n".join(lines)+"\n", encoding="utf-8")

def upsert_1txt(lines, vendor, model, burst_len_map, randomization=1,
                vht_hex="?", ext_hex="2d0102", ht_hex="006f", sup_rates="0c121824", ext_rates=""):
    """
    1.txt 行格式（示例）：
    vendor, model, "1:0.2/2:0.5/3:0.3", randomization, VHT, EXT, HT, supported_rates, ext_supported_rates
    """
    key = model.replace(" ", "").lower()
    blist = "/".join([f"{int(k)}:{p:.3f}" for k,p in burst_len_map.items()])
    new_line = f"{vendor},{model},{blist},{randomization},{vht_hex},{ext_hex},{ht_hex},{sup_rates},{ext_rates}"

    idx = None
    for i,l in enumerate(lines):
        if l.strip().startswith("#") or not l.strip():
            continue
        parts = [x.strip() for x in l.split(",")]
        if len(parts)>=2 and parts[1].replace(" ","").lower()==key:
            idx = i; break
    if idx is None:
        # 追加
        lines.append(new_line)
    else:
        lines[idx] = new_line
    return lines

def upsert_2txt(lines, model, phase, prob_int_burst, prob_between, state_dwell, jitter):
    """
    2.txt 行格式（示例）：
    model, phase, "0.02:0.7/0.04:0.3", "2.0:0.5/3.0:0.5", "30:0.5/60:0.5", "0.0:0.5/0.02:0.5"
    """
    def fmt(d): return "/".join([f"{k}:{v}" for k,v in d.items()])
    key = model.replace(" ", "").lower()
    new_line = f"{model},{phase},{fmt(prob_int_burst)},{fmt(prob_between)},{fmt(state_dwell)},{fmt(jitter)}"

    # 找该 model+phase 的行
    target_idx = None
    for i,l in enumerate(lines):
        if l.strip().startswith("#") or not l.strip():
            continue
        parts = [x.strip() for x in l.split(",")]
        if len(parts)>=2 and parts[0].replace(" ","").lower()==key and parts[1]==str(phase):
            target_idx = i; break
    if target_idx is None:
        lines.append(new_line)
    else:
        lines[target_idx] = new_line
    return lines

# --------- 标定主流程 ---------
def calibrate(vendor="Xiaomi", model="xiaomi_auto",
              real_pcaps=None, apply_all_phases=True, write_files=True):
    if real_pcaps is None or len(real_pcaps)==0:
        print("未提供 pcap，退出")
        return
    target = aggregate_metrics([Path(p) for p in real_pcaps])
    print("=== 目标(真实)指标 ===")
    print(json.dumps({k: (round(v,3) if isinstance(v,float) else v) for k,v in target.items() if k in ("MCR","NUMR","MCIV","avg_intra")}, ensure_ascii=False, indent=2))

    # 1) 轮换间隔分布（由 change_intervals 离散化，用作 2.txt 的 prob_between）
    between_dist = to_discrete_dist(target["change_intervals"], num_bins=NUM_BINS, clip_min=1.0, clip_max=300.0)
    # 2) 包内间隔分布（由 avg_intra 附近构造一个窄分布）
    intra_samples = np.random.normal(loc=max(0.01, target["avg_intra"]), scale=max(0.005, 0.25*target["avg_intra"]), size=120)
    int_burst_dist = to_discrete_dist(intra_samples.tolist(), num_bins=4, clip_min=0.01, clip_max=0.5)
    # 3) burst 长度分布（1.txt）
    bl_map = burst_len_dist(target["burst_sizes"])
    # 4) jitter：给 0~0.05s 的均匀/三角分布离散化（更贴近真实抖动）
    jitter_samples = np.random.triangular(left=0.0, mode=0.01, right=0.05, size=200)
    jitter_dist = to_discrete_dist(jitter_samples.tolist(), num_bins=4, clip_min=0.0, clip_max=0.08)
    # 5) state_dwell：若你只做“单设备可切换/不可切换”两类，可给个温和的停留时间分布
    dwell_samples = np.random.lognormal(mean=np.log(45), sigma=0.6, size=200)
    state_dwell = to_discrete_dist(dwell_samples.tolist(), num_bins=4, clip_min=10.0, clip_max=240.0)

    # ---- 写回 1.txt / 2.txt ----
    p1 = Path("1.txt"); p2 = Path("2.txt")
    lines1 = load_txt_lines(p1); lines2 = load_txt_lines(p2)

    # 1.txt：写入/更新条目
    lines1 = upsert_1txt(lines1, vendor, model, bl_map, randomization=1)

    # 2.txt：三个相位都用同一组分布（也可按需要细分）
    phases = [0,1,2] if apply_all_phases else [2]
    for ph in phases:
        lines2 = upsert_2txt(lines2, model, ph,
                             prob_int_burst=int_burst_dist,
                             prob_between=between_dist,
                             state_dwell=state_dwell,
                             jitter=jitter_dist)

    if write_files:
        save_backup_and_write(p1, lines1)
        save_backup_and_write(p2, lines2)
        print("已写回 1.txt / 2.txt（并保存 .bak 备份）。")
        print(f"写入型号：{vendor} / {model}")
        print("建议在 main.py 里选择该型号进行单设备仿真验证。")

    # 导出一个覆盖参数的 JSON（可选给 main.py 读取）
    override = {
        "vendor": vendor, "model": model,
        "mac_rotation_mode": "interval",   # 与真实轮换间隔一致
        "notes": "由真实 pcap 标定生成"
    }
    Path("xiaomi_calibrated_override.json").write_text(json.dumps(override, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已写出 xiaomi_calibrated_override.json")
    return target

if __name__ == "__main__":
    # 你上传的 pcap 文件（可自行增减）
    pcaps = [
        "data_devB_dataset_merged.pcap",
        "data_devE_dataset_merged.pcap",
        "data_devJ_dataset_merged.pcap",
        "data_devS_dataset_merged.pcap",
        "data_devT_dataset_merged.pcap",
    ]
    pcaps = [p for p in pcaps if Path(p).exists()]
    if not pcaps:
        print("未找到 pcap 文件，请把小米真实 pcap 放到当前目录。")
        sys.exit(0)
    calibrate(vendor="Xiaomi", model="xiaomi_auto", real_pcaps=pcaps, apply_all_phases=True, write_files=True)
