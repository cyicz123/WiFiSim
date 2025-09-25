#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import time
import random
import csv
from typing import Optional
import numpy as np
import capture_parsing
from user_space import Device, DeviceRates
from kernel_driver import create_probe, create_80211
import user_config  # 确保配置文件已生成
from scapy.utils import wrpcap
from phy_layer import PhysicalLayer  # 物理层模块

# 允许被 import 而不触发交互
dataset_count = 1

print("欢迎使用probe request传输仿真系统")

# ------------------- 小工具：按品牌/型号挑设备 -------------------
def _pick_model_by_vendor(device_rates: DeviceRates, vendor_input: str, model_input: Optional[str]):
    """
    从内部数据库中按品牌（vendor）筛选型号（model）。
    - vendor_input 支持大小写/前缀匹配
    - 若提供 model_input，优先精确匹配；否则在该品牌下随机挑选
    - 若找不到，回退到随机设备
    """
    try:
        db = device_rates._database
        candidates = {k: v for k, v in db.items() if v.get("vendor", "").lower().startswith(vendor_input.lower())}
        if not candidates:
            return device_rates.get_random_device()
        if model_input:
            key = model_input.replace(" ", "").lower()
            if key in candidates:
                v = candidates[key]
                return v["vendor"], v["model"], int(v["randomization"])
            for k, v in candidates.items():
                if k.startswith(key):
                    return v["vendor"], v["model"], int(v["randomization"])
        k = random.choice(list(candidates.keys()))
        v = candidates[k]
        return v["vendor"], v["model"], int(v["randomization"])
    except Exception:
        return device_rates.get_random_device()


# ------------------- 交互式配置 -------------------
def generate_dataset_config(run):
    print(f"\n----- 配置数据集 {run} -----")

    dataset_type_input = input(
        "请选择数据集类型：\n"
        "1. 多设备（设备状态切换）\n"
        "2. 单设备（可状态切换）\n"
        "3. 单设备（不可状态切换）\n"
        "请输入编号（1-3）："
    ).strip()

    if dataset_type_input == "1":
        dataset_type = "multi"
    elif dataset_type_input == "2":
        dataset_type = "single_switch"
    elif dataset_type_input == "3":
        dataset_type = "single_static"
    else:
        print("输入有误，默认选择 多设备")
        dataset_type = "multi"

    sim_duration_input = input("请输入仿真时长（分钟）：").strip()
    try:
        sim_duration_minutes = int(sim_duration_input)
    except Exception:
        print("输入有误，默认仿真时长设为10分钟")
        sim_duration_minutes = 10

    # ★ 单设备：完全不涉及“场景/密度/流动性”，只关注设备与状态
    if dataset_type != "multi":
        device_count = 1
        scene_params = {
            # 仅保留仿真所需最小旋钮；不含 density/mobility 等
            "creation_interval_multiplier": 1.0,
            "burst_interval_multiplier": 1.0,
            "dwell_multiplier": 1.0,
            "env_factor": 1.0,
            "interference_prob": 0.0,
            "qa_sample_rate": 0.0,
            # 单设备默认“按时间间隔换 MAC”
            "mac_rotation_mode": "interval",
        }

        # 单设备输入：品牌/型号 + 状态
        single_vendor = input("请输入单设备品牌（如 Apple / Samsung / Xiaomi 等，留空则随机）：").strip()
        single_model = input("可选：请输入具体型号（留空在该品牌下随机）：").strip()

        if dataset_type == "single_switch":
            # 可状态切换：只给开始状态，后续自动切换
            default_phase = 2
            phase_input = input(f"请输入单设备开始状态/相位（0=锁屏，1=亮屏，2=活动，留空默认 {default_phase}）：").strip()
            single_phase = int(phase_input) if phase_input in {"0", "1", "2"} else default_phase
        else:
            # 不可状态切换：必须给固定状态
            while True:
                phase_input = input("请输入单设备固定状态/相位（0=锁屏，1=亮屏，2=活动，必须输入）：").strip()
                if phase_input in {"0", "1", "2"}:
                    single_phase = int(phase_input)
                    break
                print("输入无效，请输入 0/1/2。")

        scene_params["single_vendor"] = single_vendor
        scene_params["single_model"] = single_model
        scene_params["single_phase"] = single_phase

        print(f"仿真参数设置：数据集数量 = {dataset_count}, 仿真时长 = {sim_duration_minutes} 分钟, 数据集类型 = {dataset_type}, 设备数 = {device_count}（单设备：不使用场景/密度/流动性）")
        print(f"单设备设置：品牌='{scene_params.get('single_vendor','(随机)')}', 型号='{scene_params.get('single_model','(随机)')}', 初始状态/相位={scene_params.get('single_phase')}")
        return dataset_type, sim_duration_minutes, device_count, scene_params

    # ★ 多设备：仍保留场景并通过流动性倍率体现差异
    print("请选择场景：")
    print("1. 高流动（设备密度自动生成）")
    print("2. 低流动高密度")
    print("3. 低流动低密度")
    scene_choice = input("请输入场景编号（1-3）：").strip()

    if scene_choice == "1":
        device_count_input = input("请输入初始设备数（正整数，或留空系统随机生成）：").strip()
        try:
            device_count = int(device_count_input) if device_count_input != "" else random.randint(10, 30)
        except Exception:
            print("输入有误，自动生成设备数")
            device_count = random.randint(10, 30)
        scene_params = {
            "density": "auto",
            "mobility": "高流动",
            "creation_interval_multiplier": 0.7,
            "burst_interval_multiplier": 0.8,
            "dwell_multiplier": 0.8,
            "env_factor": 1.2,
            "interference_prob": 0.05,
            "qa_sample_rate": 0.01,
            "mac_rotation_mode": "per_burst",
            "mobility_speed_multiplier": 1.5,
        }
    elif scene_choice == "2":
        device_count = int(input("请输入初始设备数（正整数）：") or "50")
        scene_params = {
            "density": "高密度",
            "mobility": "低流动",
            "creation_interval_multiplier": 0.7,
            "burst_interval_multiplier": 0.8,
            "dwell_multiplier": 1.2,
            "env_factor": 0.9,
            "interference_prob": 0.02,
            "qa_sample_rate": 0.005,
            "mac_rotation_mode": "per_burst",
            "mobility_speed_multiplier": 0.8,
        }
    elif scene_choice == "3":
        device_count = int(input("请输入初始设备数（正整数）：") or "15")
        scene_params = {
            "density": "低密度",
            "mobility": "低流动",
            "creation_interval_multiplier": 1.3,
            "burst_interval_multiplier": 1.2,
            "dwell_multiplier": 1.2,
            "env_factor": 0.9,
            "interference_prob": 0.00,
            "qa_sample_rate": 0.005,
            "mac_rotation_mode": "per_burst",
            "mobility_speed_multiplier": 0.7,
        }
    else:
        print("输入有误，默认选择 高流动（设备密度自动生成）")
        device_count = random.randint(10, 30)
        scene_params = {
            "density": "auto",
            "mobility": "高流动",
            "creation_interval_multiplier": 0.7,
            "burst_interval_multiplier": 0.8,
            "dwell_multiplier": 0.8,
            "env_factor": 1.2,
            "interference_prob": 0.05,
            "qa_sample_rate": 0.01,
            "mac_rotation_mode": "per_burst",
            "mobility_speed_multiplier": 1.5,
        }

    print(f"仿真参数设置：数据集数量 = {dataset_count}, 仿真时长 = {sim_duration_minutes} 分钟, 数据集类型 = {dataset_type}, 设备数 = {device_count}, 场景 = {scene_params['density']} {scene_params['mobility']}")
    return dataset_type, sim_duration_minutes, device_count, scene_params


# ------------------- 物理层与队列延迟 -------------------
phy = PhysicalLayer(tx_power=20, frequency=2400, env="auto")

def simulate_queue_delay(queue_length, service_rate=100):
    """
    简化版 M/M/1 等待时间期望（秒）：1/(μ-λ)，若不稳定则给个小常数。
    queue_length 近似到达率 λ，service_rate=μ 来自 device.processing_delay 的倒数。
    """
    arrival_rate = queue_length
    if service_rate > arrival_rate:
        return 1.0 / (service_rate - arrival_rate)
    else:
        return 0.1


# ------------------- 模拟器本体 -------------------
class Simulator:
    def __init__(self, out_file, avg_permanence_time, scene_params, dataset_type):
        self.device_rates = DeviceRates()
        self.out_file = out_file
        self.next_id_device = 0
        self.number_of_devices_available = 0
        self.events_list = []
        self.devices_list = []
        self.avg_permanence_time = avg_permanence_time  # 单位秒
        self.channel = 6
        self.scene_params = scene_params
        self.dataset_type = dataset_type  # "multi" | "single_switch" | "single_static"

    def add_device(self, device: Device) -> None:
        # 仅多设备时体现“流动性”；单设备忽略移动性倍率
        if self.dataset_type == "multi":
            try:
                mul = float(self.scene_params.get("mobility_speed_multiplier", 1.0))
                device.speed *= mul
            except Exception:
                pass
        self.devices_list.append(device)
        self.next_id_device += 1
        self.number_of_devices_available += 1
        print(f"[{datetime.now()}] 设备 {device.id}（{device.vendor} {device.model}，speed≈{device.speed:.2f} m/s）已创建。")

    def new_burst(self, time_stamp, device):
        int_pkt_time = self.device_rates.get_prob_int_burst(device.model, device.phase)
        int_pkt_time = {k: v * self.scene_params.get("burst_interval_multiplier", 1.0) for k, v in int_pkt_time.items()} if int_pkt_time else {}
        between = self.device_rates.get_prob_between_bursts(device.model, device.phase)
        burst_lens = self.device_rates.get_burst_lengths(device.model)

        int_pkt_time_chosen = random.choices(list(int_pkt_time.keys()), weights=list(int_pkt_time.values()), k=1)[0] if int_pkt_time else 0.02
        burst_rate_chosen = random.choices(list(between.keys()), weights=list(between.values()), k=1)[0] if between else 2.0
        burst_length_chosen = int(random.choices(list(burst_lens.keys()), weights=list(burst_lens.values()), k=1)[0]) if burst_lens else 2

        # === 按 mac_rotation_mode 决定本次 burst 是否换 MAC ===
        mode = getattr(device, "mac_rotation_mode", "per_burst")
        if mode == "per_burst":
            device.force_mac_change = True
        elif mode == "fixed":
            device.force_mac_change = False
        else:  # "interval"
            # 初始化倒计时
            if not hasattr(device, "_mac_change_left") or device._mac_change_left is None:
                dist = self.device_rates.get_prob_between_bursts(device.model, device.phase)
                if dist:
                    ks, ws = list(dist.keys()), list(dist.values())
                    device._mac_change_left = random.choices(ks, weights=ws, k=1)[0]
                else:
                    device._mac_change_left = 30.0
            # 是否到更换点
            if device._mac_change_left <= 0:
                device.force_mac_change = True
                # 抽下一个间隔
                dist = self.device_rates.get_prob_between_bursts(device.model, device.phase)
                if dist:
                    ks, ws = list(dist.keys()), list(dist.values())
                    device._mac_change_left = random.choices(ks, weights=ws, k=1)[0]
                else:
                    device._mac_change_left = 30.0
            else:
                device.force_mac_change = False

        supported_rates = self.device_rates.get_supported_rates(device.model)
        ext_supported_rates = self.device_rates.get_ext_supported_rates(device.model)

        packets = device.send_probe(
            int_pkt_time_chosen,
            self.device_rates.get_VHT_capabilities(device.model),
            self.device_rates.get_extended_capabilities(device.model),
            self.device_rates.get_HT_capabilities(device.model),
            burst_length_chosen,
            time_stamp,
            self.channel,
            supported_rates,
            ext_supported_rates,
        )

        # === 扣减“剩余更换时间”= 本次 burst 持续 + 到下一次 burst 的间隔 ===
        if mode == "interval" and hasattr(device, "_mac_change_left") and device._mac_change_left is not None:
            burst_duration = max(0.0, (burst_length_chosen - 1) * float(int_pkt_time_chosen))
            device._mac_change_left -= (burst_duration + float(burst_rate_chosen))

        return int_pkt_time_chosen, burst_rate_chosen, burst_length_chosen, packets


TIME_OFFSET = timedelta(seconds=0.001)

def generate_phase(device, device_rates, scene_params) -> (int, float):
    current_phase = device.phase
    dwell = device_rates.get_state_dwell(device.model, current_phase)
    if dwell:
        dwell_times = list(dwell.keys())
        weights = list(dwell.values())
        delay = random.choices(dwell_times, weights=weights, k=1)[0]
    else:
        if current_phase == 0:
            delay = random.expovariate(1 / (60 * 5))
        elif current_phase == 1:
            delay = random.expovariate(1 / 30)
        elif current_phase == 2:
            delay = random.expovariate(1 / (60 * 3))
        else:
            delay = 60
    delay *= scene_params.get("dwell_multiplier", 1.0)

    if current_phase == 0:
        new_phase = np.random.choice([1, 2], p=[0.2, 0.8])
    elif current_phase == 1:
        new_phase = np.random.choice([0, 2], p=[0.9, 0.1])
    elif current_phase == 2:
        new_phase = 0
    else:
        new_phase = 0
    return new_phase, delay


class Event:
    def __init__(self, start_time: datetime, job_type: str, device=None, phase: int = None, vendor: str = None, model: str = None, packet=None, burst_end: bool = None):
        self.start_time = start_time
        self.job_type = job_type
        self.device = device
        self.phase = phase
        self.vendor = vendor
        self.model = model
        self.packet = packet
        self.burst_end = burst_end


def add_event(sim, event: Event) -> timedelta:
    # 既有 OS 抖动
    os_delay = timedelta(milliseconds=random.uniform(5, 20))
    event.start_time += os_delay

    # 队列延迟（仅对发送帧）
    q_delay = timedelta(0)
    if event.job_type == "send_packet" and getattr(event, "device", None) is not None:
        service_rate = 1.0 / max(event.device.processing_delay, 1e-4)
        q_sec = simulate_queue_delay(event.device.queue_length, service_rate=service_rate)
        q_delay = timedelta(seconds=q_sec)
        event.start_time += q_delay

    sim.events_list.append(event)
    sim.events_list.sort(key=lambda e: (e.start_time, 1 if e.job_type == "send_packet" else 0))
    return os_delay + q_delay


def clean_events_after_change_phase(sim, device):
    sim.events_list = [
        e for e in sim.events_list
        if e.job_type == "create_device" or (e.device.id != device.id or (e.device.id == device.id and e.job_type not in ["create_burst", "send_packet"]))
    ]


def clean_events_after_delete_device(sim, device_id):
    sim.events_list = [e for e in sim.events_list if e.device is not None and e.device.id != device_id]


def change_phase(simulator, device, phase, time_stamp):
    device.change_phase(phase, time_stamp)
    with open(simulator.out_file + '.txt', 'a') as f:
        f.write(f"Device {device.id} ({device.vendor} {device.model}) changed phase to {phase} at {time_stamp}\n")
    print(f"[{time_stamp}] 设备 {device.id} 状态切换为 {phase}。")


def delete_device(simulator, device, time_stamp):
    device.time_phase_changed = time_stamp
    simulator.number_of_devices_available -= 1
    with open(simulator.out_file + '.txt', 'a') as f:
        f.write(f"Device {device.id} ({device.vendor} {device.model}) deleted at {time_stamp}\n")
    print(f"[{time_stamp}] 设备 {device.id} 已删除。")


def create_device(simulator, time_stamp, phase, vendor, model):
    randomization = simulator.device_rates.get_randomization(model)
    device = Device(simulator.next_id_device, time_stamp, phase, vendor, model, randomization)
    # 覆盖 MAC 轮换策略（默认 per_burst；单设备已设 interval）
    try:
        device.mac_rotation_mode = simulator.scene_params.get("mac_rotation_mode", getattr(device, "mac_rotation_mode", "per_burst"))
    except Exception:
        device.mac_rotation_mode = "per_burst"

    # === 初始化“按间隔换 MAC”的倒计时（秒） ===
    if getattr(device, "mac_rotation_mode", "per_burst") == "interval":
        dist = simulator.device_rates.get_prob_between_bursts(device.model, device.phase)
        if dist:
            ks, ws = list(dist.keys()), list(dist.values())
            device._mac_change_left = random.choices(ks, weights=ws, k=1)[0]
        else:
            device._mac_change_left = 30.0
    else:
        device._mac_change_left = None

    simulator.add_device(device)
    with open(simulator.out_file + '.txt', 'a') as f:
        f.write(f"Device {device.id} ({device.vendor} {device.model}) created at {time_stamp}\n")
    return device


def handle_event(event: Event, simulator):
    if event.job_type == "change_phase":
        # 多设备 & 单设备（可切换）都允许自动状态切换
        if simulator.dataset_type in ("multi", "single_switch"):
            change_phase(simulator, event.device, event.phase, event.start_time)
            new_phase, delay = generate_phase(event.device, simulator.device_rates, simulator.scene_params)
            add_event(simulator, Event(event.start_time + timedelta(seconds=delay), "change_phase", device=event.device, phase=new_phase))
            clean_events_after_change_phase(simulator, event.device)
            if simulator.device_rates.is_sending_probe(event.device.model, event.device.phase):
                add_event(simulator, Event(event.start_time, "create_burst", device=event.device))
        else:
            # 单设备（不可切换）：不改变状态，仅按固定状态发包
            if simulator.device_rates.is_sending_probe(event.device.model, event.device.phase):
                add_event(simulator, Event(event.start_time, "create_burst", device=event.device))

    elif event.job_type == "create_burst":
        if simulator.device_rates.is_sending_probe(event.device.model, event.device.phase):
            int_pkt_time, burst_rate, burst_len, packets = simulator.new_burst(event.start_time, event.device)
            counter_sum = timedelta(seconds=0.0)
            for i in range(int(burst_len)):
                jitter_dist = simulator.device_rates.get_jitter(event.device.model, event.device.phase)
                jitter_sample = random.choices(list(jitter_dist.keys()), weights=list(jitter_dist.values()), k=1)[0] if jitter_dist else 0
                event_time = event.start_time + i * timedelta(seconds=int_pkt_time) + counter_sum + timedelta(seconds=jitter_sample)
                counter = add_event(simulator, Event(event_time, "send_packet", device=event.device, packet=packets[i], burst_end=(i == burst_len - 1)))
                counter_sum += counter
                # 回写帧时间戳（叠加调度延迟与抖动）
                packets[i].time = (datetime.fromtimestamp(packets[i].time) + counter_sum + timedelta(seconds=jitter_sample)).timestamp()
            add_event(simulator, Event(
                event.start_time + (burst_len - 1) * timedelta(seconds=int_pkt_time) + counter_sum + timedelta(seconds=burst_rate),
                "create_burst",
                device=event.device
            ))

    elif event.job_type == "send_packet":
        # 与 AP 的距离（AP 位于 (50,50)）
        distance = np.linalg.norm(np.array(event.device.position) - np.array((50, 50)))

        # 设备功率与场景干扰对物理层的影响
        base_env = simulator.scene_params.get("env_factor", 1.0)
        env = base_env * (event.device.power_level / 20.0)

        if random.random() < simulator.scene_params.get("interference_prob", 0.0):
            channel_success = False
        else:
            channel_success = phy.simulate_channel(distance, env_factor=env)

        if channel_success:
            wrpcap(simulator.out_file + ".pcap", event.packet, append=True)
            # 抽样质检
            if random.random() < simulator.scene_params.get("qa_sample_rate", 0.0):
                c = capture_parsing.capture_frame(event.packet)
                capture_parsing.parse_captured_frame(c)
            with open(simulator.out_file + '_probe_ids.txt', 'a') as f:
                f.write(f"{event.device.id}\n")
            event.device.number_packets_sent += 1
            print(f"[{event.start_time}] 设备 {event.device.id} 发送数据包（成功）。")
        else:
            print(f"[{event.start_time}] 设备 {event.device.id} 数据包因信道条件不佳而丢失。")

        if event.burst_end:
            event.device.number_bursts_sent += 1

    elif event.job_type == "create_device":
        if simulator.dataset_type == "multi":
            phase = np.random.choice([0, 1, 2], p=[0.35, 0.15, 0.50])
            device = create_device(simulator, event.start_time, phase, event.vendor, event.model)
            permanence_time = simulator.avg_permanence_time * simulator.scene_params["creation_interval_multiplier"]
            add_event(simulator, Event(event.start_time + timedelta(seconds=permanence_time), "delete_device", device=device))
            new_phase, delay = generate_phase(device, simulator.device_rates, simulator.scene_params)
            add_event(simulator, Event(event.start_time + timedelta(seconds=delay), "change_phase", device=device, phase=new_phase))
            if simulator.device_rates.is_sending_probe(device.model, device.phase):
                add_event(simulator, Event(event.start_time, "create_burst", device=device))
            next_creation = simulator.avg_permanence_time / 2 * simulator.scene_params["creation_interval_multiplier"]
            vendor, model, _ = simulator.device_rates.get_random_device()
            add_event(simulator, Event(event.start_time + timedelta(seconds=next_creation), "create_device", vendor=vendor, model=model))

        elif simulator.dataset_type == "single_switch":
            # 单设备（可切换）：只输入开始状态，后续自动切换
            start_phase = simulator.scene_params.get("single_phase", 2)
            device = create_device(simulator, event.start_time, start_phase, event.vendor, event.model)
            print(f"单设备（可切换）已选择：{device.vendor} / {device.model}")
            new_phase, delay = generate_phase(device, simulator.device_rates, simulator.scene_params)
            add_event(simulator, Event(event.start_time + timedelta(seconds=delay), "change_phase", device=device, phase=new_phase))
            if simulator.device_rates.is_sending_probe(device.model, device.phase):
                add_event(simulator, Event(event.start_time, "create_burst", device=device))

        else:
            # 单设备（不可切换）：固定相位
            fixed_phase = simulator.scene_params.get("single_phase", 0)
            device = create_device(simulator, event.start_time, fixed_phase, event.vendor, event.model)
            print(f"单设备（不可切换）已选择：{device.vendor} / {device.model}，固定相位={fixed_phase}")
            if simulator.device_rates.is_sending_probe(device.model, device.phase):
                add_event(simulator, Event(event.start_time, "create_burst", device=device))

    elif event.job_type == "delete_device":
        delete_device(simulator, event.device, event.start_time)
        clean_events_after_delete_device(simulator, event.device.id)


def run_simulation(sim_out_file, dataset_type, sim_duration_minutes, device_count, scene_params):
    SIM_DURATION_MINUTES = sim_duration_minutes
    sim_duration = timedelta(minutes=SIM_DURATION_MINUTES)
    sim = Simulator(sim_out_file, avg_permanence_time=15 * 60, scene_params=scene_params, dataset_type=dataset_type)

    # 清空旧文件
    for ext in ['.txt', '.pcap', '_probe_ids.txt']:
        open(sim.out_file + ext, 'w').close()

    start_time = datetime.now()
    print(f"Simulation start time: {start_time}")

    # 添加初始设备创建事件
    if dataset_type == "multi":
        for _ in range(device_count):
            vendor, model, _ = sim.device_rates.get_random_device()
            add_event(sim, Event(start_time, "create_device", vendor=vendor, model=model))
    else:
        vendor_inp = scene_params.get("single_vendor", "").strip()
        model_inp = scene_params.get("single_model", "").strip()
        if vendor_inp:
            vendor, model, _ = _pick_model_by_vendor(sim.device_rates, vendor_inp, model_inp if model_inp else None)
        else:
            vendor, model, _ = sim.device_rates.get_random_device()
        print(f"单设备已选择（可能为随机）：{vendor} / {model}")
        add_event(sim, Event(start_time, "create_device", vendor=vendor, model=model))

    with open(sim.out_file + '.txt', 'a') as f:
        f.write('+++++++++++ Simulation start +++++++++++\n')
        f.write(f'Initial time (real and simulated): {start_time}\n')

    # 主事件循环
    while sim.events_list:
        now = datetime.now()
        next_event = sim.events_list[0]
        if next_event.start_time > now:
            sleep_time = (next_event.start_time - now).total_seconds()
            time.sleep(sleep_time)

        evt = sim.events_list.pop(0)
        time.sleep(random.uniform(0.005, 0.02))

        # 多设备：体现移动；单设备：移动性开关已在 add_device 中忽略倍率
        for dev in sim.devices_list:
            dev.update_position(0.1)

        handle_event(evt, sim)
        if evt.start_time >= start_time + sim_duration:
            break

    print("Simulation finished.")
    for dev in sim.devices_list:
        dev.print_information(sim.out_file)
        dev.print_statistics(sim.out_file)

    end_time = datetime.now()
    with open(sim.out_file + '.txt', 'a') as f:
        f.write('\n+++++++++++ Simulation end +++++++++++\n')
        f.write(f'End time (real): {end_time}\n')
        f.write(f'End time (simulated): {evt.start_time}\n')
        f.write(f'Time ratio (simulated/real): {round((evt.start_time - start_time) / (end_time - start_time), 2)}\n')
        total_MACs = sum(len(d.mac_address) for d in sim.devices_list)
        total_packets = sum(d.number_packets_sent for d in sim.devices_list)
        f.write(f'\nTotal number of different MAC addresses: {total_MACs}\n')
        f.write(f'Total number of packets sent: {total_packets}\n')
    print("Simulation logs and data saved to file.")

    # 输出设备标注 CSV
    csv_file = sim.out_file + '_devices.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['mac_address', 'device_name', 'device_id'])
        for dev in sim.devices_list:
            macs = dev.mac_address if isinstance(dev.mac_address, (list, tuple)) else [dev.mac_address]
            for mac in macs:
                writer.writerow([mac, f"{dev.vendor} {dev.model}", dev.id])
    print(f"设备信息已保存至：{csv_file}")


def main():
    for run in range(1, dataset_count + 1):
        dataset_type, sim_duration_minutes, device_count, scene_params = generate_dataset_config(run)
        out_file = f"out_file_run_{run}"
        print(f"\n----- Starting simulation run {run} -----")
        run_simulation(out_file, dataset_type, sim_duration_minutes, device_count, scene_params)
        time.sleep(5)
    print("All simulation runs completed.")


if __name__ == "__main__":
    # 放到 __main__，避免 import 触发交互
    dataset_count_input = input("请输入生成数据集数量（正整数）：")
    try:
        dataset_count = int(dataset_count_input)
    except Exception:
        print("输入有误，默认生成1个数据集")
        dataset_count = 1
    main()
