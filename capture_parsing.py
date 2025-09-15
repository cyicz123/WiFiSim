import random


class CapturedFrame:
    def __init__(self, frame, rssi):
        self.frame = frame
        self.rssi = rssi


def capture_frame(frame):
    # 为帧分配随机 RSSI（-40 到 -90 dBm）
    rssi = -(40 + random.randint(0, 50))
    return CapturedFrame(frame, rssi)


def parse_captured_frame(captured):
    print("捕获到 Probe Request 帧：")
    try:
        from scapy.all import hexdump, Dot11, Dot11Elt
        # 使用 hexdump 显示整个帧
        hexdump(captured.frame)

        # 解析 Dot11 头部信息
        if captured.frame.haslayer(Dot11):
            dot11 = captured.frame.getlayer(Dot11)
            print(f"源 MAC地址: {dot11.addr2}")
            print(f"目标 MAC地址: {dot11.addr1}")
            print(f"BSSID: {dot11.addr3}")
            print(f"序列号: {dot11.SC}")

        # 遍历所有 Dot11Elt 信息元素
        elt = captured.frame.getlayer(Dot11Elt)
        while elt:
            if elt.ID == 0:
                # SSID
                try:
                    ssid = elt.info.decode(errors="ignore")
                except Exception:
                    ssid = elt.info
                print(f"SSID: {ssid}")
            elif elt.ID == 1:
                # 支持速率（注意速率单位通常为 0.5 Mbps 单位）
                rates = [f"{r / 2:.1f}" for r in elt.rates]
                print("支持速率:", " ".join(rates), "Mbps")
            elif elt.ID == 50:
                # 扩展支持速率
                ext_rates = [f"{r / 2:.1f}" for r in elt.rates]
                print("扩展支持速率:", " ".join(ext_rates), "Mbps")
            elif elt.ID == 45:
                print("HT 能力:", elt.info.hex())
            elif elt.ID == 191:
                print("VHT 能力:", elt.info.hex())
            elif elt.ID == 127:
                print("扩展能力:", elt.info.hex())
            elif elt.ID == 221:
                # Vendor Specific 信息，例如可能包含 WPS 数据
                print("Vendor Specific:", elt.info.hex())
            elt = elt.payload.getlayer(Dot11Elt)
    except Exception as e:
        print("解析错误：", e)
    print(f"捕获时 RSSI: {captured.rssi} dBm")
