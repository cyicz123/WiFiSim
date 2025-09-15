# =========================
# user_space.py （合并后的完整版本）
# =========================
# user_space.py
from datetime import timedelta
import numpy as np
from numpy import random
import os
import math
import time

PERMANENT_MAC = "00:11:22:33:44:55"
DEDICATED_MAC = "02:12:34:56:78:9a"
MAC_MASK = "ff:ff:ff:00:00:00"


def get_oui(vendor_name: str) -> [str, str]:
    oui = {}
    with open('oui_hex.txt', encoding='utf-8') as f:
        for line in f.readlines():
            parts = line.strip().split("\t")
            if len(parts) < 2:
                continue
            mac = parts[0]
            vendor = parts[1]
            if vendor in oui:
                oui[vendor].append(mac)
            else:
                oui[vendor] = [mac]
    res = ""
    res_name = ""
    for key in oui:
        if key.lower().startswith(vendor_name.lower()):
            res = oui[key][0]
            res_name = key
            break
    if not res:
        res = "00:00:00"
        res_name = "default"
    return [res.replace("-", ":"), res_name]


def get_frequency(channel: int) -> int:
    if channel == 14:
        return 2484
    else:
        return 2407 + (channel * 5)


def produce_sequenceNumber(frag: int, seq: int) -> int:
    return (seq << 4) + frag


def random_MAC() -> str:
    first_byte = int('%d%d%d%d%d%d10' % (random.randint(0, 1), random.randint(0, 1), random.randint(0, 1),
                                          random.randint(0, 1), random.randint(0, 1), random.randint(0, 1)), 2)
    mac_address = ("%02x:%02x:%02x:%02x:%02x:%02x" % (
        first_byte,
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )).lower()
    return mac_address


def random_hex(number_of_elements: int):
    hex_chars = list("abcdef0123456789")
    return "".join(random.choices(hex_chars, k=number_of_elements))


def mac_str_to_bytes(mac_str: str) -> bytes:
    return bytes(int(b, 16) for b in mac_str.split(":"))


def bytes_to_mac_str(mac_bytes: bytes) -> str:
    return ":".join('{:02x}'.format(b) for b in mac_bytes)


def random_mac_addr_with_mask(base: str, mask: str) -> str:
    base_bytes = bytearray(mac_str_to_bytes(base))
    if len(base_bytes) < 6:
        base_bytes.extend([0] * (6 - len(base_bytes)))
    mask_bytes = bytearray(mac_str_to_bytes(mask))
    if len(mask_bytes) < 6:
        mask_bytes.extend([0] * (6 - len(mask_bytes)))
    result = bytearray(6)
    for i in range(6):
        rand_byte = os.urandom(1)[0]
        # 由 mask=1 的位取 base，对应位为 0 的用随机
        result[i] = (base_bytes[i] & mask_bytes[i]) | (rand_byte & (~mask_bytes[i] & 0xFF))
    return bytes_to_mac_str(result)


class Device:
    def __init__(self, id, time, phase, vendor, model, randomization):
        self.id = id
        self.time_phase_changed = time
        self.phase = phase  # 0: 锁屏, 1: 亮屏, 2: 活动
        self.vendor = vendor
        self.model = model.replace(" ", "").lower()
        self.randomization = randomization
        self.SSID = []
        self.mac_address = []
        self.number_packets_sent = 0
        self.number_bursts_sent = 0
        self.wps = None
        self.uuide = None

        # ★新增：MAC 轮换策略（'per_burst' | 'per_phase' | 'interval'）
        self.mac_rotation_mode = 'per_burst'
        self._next_mac_change_ts = None

        # 硬件及调度参数
        self.queue_length = np.random.randint(1, 10)
        self.processing_delay = random.uniform(0.001, 0.005)
        self.power_level = random.uniform(10, 20)  # dBm
        self.position = (random.uniform(0, 100), random.uniform(0, 100))  # 初始位置
        self.speed = random.uniform(0.5, 2.0)  # 米/秒
        self.direction = random.uniform(0, 360)

        self.force_mac_change = True

        if self.randomization in [0, 3] and not self.force_mac_change:
            self.mac_address.append(self.create_mac_address())
        if np.random.choice([True, False], p=[0.11, 0.89]):
            self.wps = bytes.fromhex(''.join(np.random.choice(list("0123456789abcdef"), 8)))
            self.uuide = bytes.fromhex(''.join(np.random.choice(list("0123456789abcdef"), 8)))
        if np.random.choice([True, False], p=[0.2, 0.8]):
            self.SSID = self.create_ssid()

    def create_mac_address(self):
        if self.randomization == 0:
            return PERMANENT_MAC.lower()
        elif self.randomization == 1:
            # 随机本地 MAC：置 U/L 位
            mac = bytearray(os.urandom(6))
            mac[0] &= 0xFE
            mac[0] |= 0x02
            return ":".join(f"{b:02x}" for b in mac)
        elif self.randomization == 2:
            vendor_oui = get_oui(self.vendor)[0].lower()
            return random_mac_addr_with_mask(vendor_oui, MAC_MASK)
        elif self.randomization == 3:
            return DEDICATED_MAC.lower()
        else:
            return PERMANENT_MAC.lower()

    def send_probe(self, inter_pkt_time, VHT_capabilities, extended_capabilities, HT_capabilities,
                   num_pkt_burst, timestamp, channel, supported_rates, ext_supported_rates):
        time.sleep(self.processing_delay)
        from kernel_driver import create_probe

        # ★新增：按策略决定是否更换 MAC
        need_change = self.force_mac_change
        if getattr(self, 'mac_rotation_mode', 'per_burst') == 'interval':
            now = timestamp
            if self._next_mac_change_ts is None or now >= self._next_mac_change_ts:
                need_change = True
                # 间隔 20–60 秒一次
                self._next_mac_change_ts = now + timedelta(seconds=float(random.uniform(20, 60)))

        new_mac = self.create_mac_address() if need_change else (
            self.mac_address[0] if self.mac_address else self.create_mac_address())

        # per_burst：每次发送前都置回 True；per_phase：由 change_phase 置 True
        self.force_mac_change = (self.mac_rotation_mode == 'per_burst')

        if self.randomization in [0, 3]:
            self.mac_address = [new_mac]
        else:
            self.mac_address.append(new_mac)

        vendor_for_probe = "Broadcom" if self.randomization == 1 else self.vendor
        mac, packets = create_probe(vendor_for_probe, self.randomization, self.SSID, num_pkt_burst,
                                    new_mac, inter_pkt_time, VHT_capabilities, extended_capabilities,
                                    HT_capabilities, self.wps, self.uuide, timestamp, channel,
                                    supported_rates, ext_supported_rates)
        return packets

    def create_ssid(self):
        ssid_chars = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        num = np.random.randint(1, 11)
        ssids = []
        for _ in range(num):
            ssid = "".join(np.random.choice(ssid_chars, size=32))
            ssids.append(ssid)
        return ssids

    def change_phase(self, phase, time):
        self.phase = phase
        self.time_phase_changed = time
        # ★新增：每“相位”换 MAC 的策略触发
        if getattr(self, 'mac_rotation_mode', 'per_burst') == 'per_phase':
            self.force_mac_change = True

    def update_position(self, delta_t):
        # 简单直线运动更新位置，delta_t 为时间间隔（秒）
        dx = self.speed * delta_t * math.cos(math.radians(self.direction))
        dy = self.speed * delta_t * math.sin(math.radians(self.direction))
        x, y = self.position
        new_x = max(0, min(100, x + dx))
        new_y = max(0, min(100, y + dy))
        self.position = (new_x, new_y)
        self.direction = (self.direction + random.uniform(-10, 10)) % 360

    def print_information(self, file_name):
        with open(file_name + '.txt', 'a') as f:
            f.write(f"\nDevice {self.id} information:\nVendor: {self.vendor}\nModel: {self.model}\n"
                    f"MAC Policy: {self.randomization}\nMAC address(es): {self.mac_address}\nSSID: {self.SSID}\n")

    def print_statistics(self, file_name):
        with open(file_name + '.txt', 'a') as f:
            f.write(f"Number of different MAC addresses: {len(self.mac_address)}\n"
                    f"Number of packets sent: {self.number_packets_sent}\n"
                    f"Number of bursts sent: {self.number_bursts_sent}\n")


class DeviceRates:
    def __init__(self):
        self._database = {}
        # 设备参数库（1.txt）
        with open("1.txt", "r") as f:
            line = f.readline().replace("\\n", "")
            while line:
                if line.startswith("#"):
                    line = f.readline().replace("\\n", "")
                    continue
                parts = line.strip().split(",")
                vendor = parts[0].strip()
                model = parts[1].strip()
                burst_probs = parts[2].strip()
                burst_length = {float(x.split(":")[0]): float(x.split(":")[1]) for x in burst_probs.split("/")}
                randomization = int(parts[3].strip())
                VHT_cap = parts[4].strip()
                if VHT_cap == "?":
                    VHT_cap = None
                else:
                    VHT_cap = bytes.fromhex(VHT_cap.replace("x", ""))
                ext_cap = bytes.fromhex(parts[5].strip().replace("x", ""))
                HT_cap = bytes.fromhex(parts[6].strip().replace("x", ""))
                supported_rates = parts[7].strip()
                ext_supported_rates = parts[8].strip()
                key = model.replace(" ", "").lower()
                self._database[key] = {
                    "vendor": vendor,
                    "model": model,
                    "burst_lengths": burst_length,
                    "randomization": randomization,
                    "VHT_capabilities": VHT_cap,
                    "extended_capabilities": ext_cap,
                    "HT_capabilities": HT_cap,
                    "supported_rates": supported_rates,
                    "ext_supported_rates": ext_supported_rates
                }
                line = f.readline().replace("\\n", "")

        # 相位参数库（2.txt）
        with open("2.txt", "r") as f2:
            line = f2.readline().replace("\\n", "")
            while line:
                if line.startswith("#"):
                    line = f2.readline().replace("\\n", "")
                    continue
                parts = line.strip().split(",")
                model = parts[0].strip()
                key = model.replace(" ", "").lower()
                phase = int(parts[1].strip())
                prob_int = {float(x.split(":")[0]): float(x.split(":")[1]) for x in parts[2].strip().split("/")}
                prob_between = {float(x.split(":")[0]): float(x.split(":")[1]) for x in parts[3].strip().split("/")}
                state_dwell = {float(x.split(":")[0]): float(x.split(":")[1]) for x in parts[4].strip().split("/")}
                jitter = {float(x.split(":")[0]): float(x.split(":")[1]) for x in parts[5].strip().split("/")}

                if "prob_int_burst" not in self._database[key]:
                    self._database[key]["prob_int_burst"] = []
                if "prob_between_bursts" not in self._database[key]:
                    self._database[key]["prob_between_bursts"] = []
                if "state_dwell" not in self._database[key]:
                    self._database[key]["state_dwell"] = []
                if "jitter" not in self._database[key]:
                    self._database[key]["jitter"] = []

                self._database[key]["prob_int_burst"].append((phase, prob_int))
                self._database[key]["prob_between_bursts"].append((phase, prob_between))
                self._database[key]["state_dwell"].append((phase, state_dwell))
                self._database[key]["jitter"].append((phase, jitter))
                line = f2.readline().replace("\\n", "")

    def get_element(self, model):
        return self._database[model.replace(" ", "").lower()]

    def get_randomization(self, model):
        return self.get_element(model)["randomization"]

    def get_burst_lengths(self, model):
        return self.get_element(model)["burst_lengths"]

    def get_supported_rates(self, model):
        return self.get_element(model)["supported_rates"]

    def get_ext_supported_rates(self, model):
        return self.get_element(model)["ext_supported_rates"]

    def get_prob_int_burst(self, model, phase):
        for ph, probs in self.get_element(model).get("prob_int_burst", []):
            if ph == phase:
                return probs
        return {}

    def get_prob_between_bursts(self, model, phase):
        for ph, probs in self.get_element(model).get("prob_between_bursts", []):
            if ph == phase:
                return probs
        return {}

    def get_state_dwell(self, model, phase):
        for ph, dist in self.get_element(model).get("state_dwell", []):
            if ph == phase:
                return dist
        return {}

    def get_jitter(self, model, phase):
        for ph, dist in self.get_element(model).get("jitter", []):
            if ph == phase:
                return dist
        return {}

    def get_VHT_capabilities(self, model):
        return self.get_element(model)["VHT_capabilities"]

    def get_extended_capabilities(self, model):
        return self.get_element(model)["extended_capabilities"]

    def get_HT_capabilities(self, model):
        return self.get_element(model)["HT_capabilities"]

    def is_sending_probe(self, model, phase):
        el = self.get_element(model)
        if "prob_between_bursts" not in el:
            return False
        for ph, probs in el["prob_between_bursts"]:
            if ph == phase:
                return True
        return False

    def get_random_device(self):
        key = random.choice(list(self._database.keys()))
        device = self._database[key]
        return device["vendor"], device["model"], int(device["randomization"])
