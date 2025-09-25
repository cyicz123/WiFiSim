# phy_layer.py
import math
import random
import numpy as np

class PhysicalLayer:
    def __init__(self, tx_power=20, frequency=2400, env='urban'):
        self.tx_power = tx_power  # 发射功率，单位 dBm
        self.frequency = frequency  # 频率，单位 MHz
        self.env = env  # 环境类型，可用于后续调整

    def free_space_path_loss(self, distance):
        # 自由空间路径损耗公式（单位 dB）
        # FSPL = 20*log10(d) + 20*log10(f) - 27.55, d单位米，f单位MHz
        if distance <= 0:
            distance = 0.001
        loss = 20 * math.log10(distance) + 20 * math.log10(self.frequency) - 27.55
        return loss

    def rayleigh_fading(self):
        # Rayleigh 衰落模拟，单位 dB（负值表示衰落）
        fading = np.random.rayleigh(scale=2.0)
        return -fading

    def shadowing(self):
        # 阴影衰落模拟，服从正态分布（均值0，标准差3 dB）
        return random.gauss(0, 3)

    def compute_received_power(self, distance):
        # 计算接收功率 = tx_power - path_loss + fading + shadowing
        loss = self.free_space_path_loss(distance)
        fading = self.rayleigh_fading()
        shadow = self.shadowing()
        received_power = self.tx_power - loss + fading + shadow
        return received_power

    def simulate_channel(self, distance, env_factor=1.0):
        # 模拟信道条件：根据距离和环境因子调整接收功率，
        # 若接收功率大于噪声门限（噪声底约 -90 dBm，加上 margin 10 dB），则认为传输成功
        received_power = self.compute_received_power(distance) * env_factor
        noise_floor = -90  # dBm
        if received_power > noise_floor + 10:
            return True
        else:
            return False
