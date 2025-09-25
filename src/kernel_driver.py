from datetime import datetime
from scapy.layers.dot11 import Dot11, RadioTap, Dot11ProbeReq, Dot11Elt, Dot11EltRates, Dot11EltDSSSet, Dot11EltVendorSpecific
from numpy import random
import random as pyrandom
from user_space import random_MAC, get_oui, get_frequency, produce_sequenceNumber

def parse_rates(rates_str: str) -> list:
    """
    将支持速率字符串（格式："6:0.25/9:0.25/12:0.25/18:0.25"）解析为速率列表 [6,9,12,18]
    概率部分忽略，仅返回速率值。
    """
    if not rates_str:
        return []
    pairs = rates_str.split("/")
    rates = []
    for pair in pairs:
        try:
            rate, _ = pair.split(":")
            rates.append(int(rate))
        except Exception:
            continue
    return rates

def create_probe(vendor: str,
                 randomization: int,
                 ssid: list,
                 burst_length: int,
                 mac_address: str,
                 inter_pkt_time: float,
                 VHT_capabilities: bytes,
                 extended_capabilities: bytes,
                 HT_capabilities: bytes,
                 wps: bytes,
                 uuide: bytes,
                 time: datetime,
                 channel: int,
                 supported_rates: str,
                 ext_supported_rates: str) -> tuple[str, list]:
    packets = []
    radio = create_radio(channel)
    dot11, seq_number, mac_address = create_80211(vendor, randomization, seq_number=0, mac_address=mac_address, burst_lenght=burst_length)

    dot11Array = []
    for i in range(1, int(burst_length)):
        dot11burst, seq_number, mac_address = create_80211(vendor, randomization, seq_number=seq_number+1, mac_address=mac_address, burst_lenght=burst_length)
        dot11Array.append(dot11burst)

    probeReq = Dot11ProbeReq()
    if ssid:
        dot11elt = create_informationElement(ssid=random.choice(ssid))
    else:
        dot11elt = create_informationElement(ssid="")
    dot11eltrates = create_supportedRates(supported_rates)
    dot11eltratesext = create_extendedSupportedRates(ext_supported_rates)
    dot11eltdssset = create_DSSSparameterSet(channel)
    dot11elthtcap = create_HTcapabilities(HT_capabilities)
    dot11eltven = create_vendorSpecific(vendor)
    if wps and uuide:
        dot11wps, dot11uuide = create_wps_uuide(wps, uuide)
    if VHT_capabilities is not None:
        dot11eltVHTcap = create_VHTcapabilities(VHT_capabilities)
    dot11eltEXTcap = create_Extendendcapabilities(extended_capabilities)

    if VHT_capabilities is not None:
        if wps and uuide:
            frame = radio / dot11 / probeReq / dot11elt / dot11eltrates / dot11eltratesext / dot11eltdssset / dot11elthtcap / dot11eltVHTcap / dot11eltEXTcap / dot11eltven / dot11wps / dot11uuide
        else:
            frame = radio / dot11 / probeReq / dot11elt / dot11eltrates / dot11eltratesext / dot11eltdssset / dot11elthtcap / dot11eltVHTcap / dot11eltEXTcap / dot11eltven
    else:
        if wps and uuide:
            frame = radio / dot11 / probeReq / dot11elt / dot11eltrates / dot11eltratesext / dot11eltdssset / dot11elthtcap / dot11eltEXTcap / dot11eltven / dot11wps / dot11uuide
        else:
            frame = radio / dot11 / probeReq / dot11elt / dot11eltrates / dot11eltratesext / dot11eltdssset / dot11elthtcap / dot11eltEXTcap / dot11eltven

    packets.append(frame)
    t_ref = time.timestamp()
    frame.time = t_ref

    for i in range(1, int(burst_length)):
        if VHT_capabilities is not None:
            if wps and uuide:
                frame = radio / dot11Array.pop(0) / probeReq / dot11elt / dot11eltrates / dot11eltratesext / dot11eltdssset / dot11elthtcap / dot11eltVHTcap / dot11eltEXTcap / dot11eltven / dot11wps / dot11uuide
            else:
                frame = radio / dot11Array.pop(0) / probeReq / dot11elt / dot11eltrates / dot11eltratesext / dot11eltdssset / dot11elthtcap / dot11eltVHTcap / dot11eltEXTcap / dot11eltven
        else:
            if wps and uuide:
                frame = radio / dot11Array.pop(0) / probeReq / dot11elt / dot11eltrates / dot11eltratesext / dot11eltdssset / dot11elthtcap / dot11eltEXTcap / dot11eltven / dot11wps / dot11uuide
            else:
                frame = radio / dot11Array.pop(0) / probeReq / dot11elt / dot11eltrates / dot11eltratesext / dot11eltdssset / dot11elthtcap / dot11eltEXTcap / dot11eltven
        t_ref += inter_pkt_time
        frame.time = t_ref
        packets.append(frame)

    return mac_address, packets

def create_radio(channel: int):
    return RadioTap(present='TSFT+Flags+Rate+Channel+dBm_AntSignal+Antenna',
                    Flags='',
                    Rate=1.0,
                    ChannelFrequency=get_frequency(channel),
                    ChannelFlags='CCK+2GHz',
                    dBm_AntSignal=-pyrandom.randint(30,70),
                    Antenna=0)

def create_80211(vendor, randomization, seq_number, mac_address, burst_lenght):
    if mac_address == "":
        mac_address = random_MAC().lower()
        if randomization == 0:
            vendor_oui = get_oui(vendor)[0].lower()
            if vendor_oui:
                mac_address = vendor_oui + (":%02x:%02x:%02x" % (pyrandom.randint(0,255), pyrandom.randint(0,255), pyrandom.randint(0,255))).lower()
    if seq_number == 0:
        # 将 burst_lenght 转换为整数，确保 randint 参数正确
        seq_number = pyrandom.randint(0, 4095 - int(burst_lenght))
    return [Dot11(addr1='ff:ff:ff:ff:ff:ff',
                  addr2=mac_address,
                  addr3='ff:ff:ff:ff:ff:ff',
                  SC=produce_sequenceNumber(0, seq_number)),
            seq_number,
            mac_address]

def create_informationElement(ssid):
    return Dot11Elt(ID=0, info=ssid) if ssid else Dot11Elt(ID=0)

def create_supportedRates(rates_str):
    rates = parse_rates(rates_str)
    return Dot11EltRates(ID=1, rates=rates)

def create_extendedSupportedRates(rates_str):
    rates = parse_rates(rates_str)
    return Dot11EltRates(ID=50, rates=rates)

def create_DSSSparameterSet(channel: int):
    return Dot11EltDSSSet(channel=channel)

def create_HTcapabilities(HT_info):
    return Dot11Elt(ID=45, info=HT_info)

def create_vendorSpecific(vendor):
    mac, name = get_oui(vendor)
    return Dot11EltVendorSpecific(ID=221, oui=int(mac.replace(":", ""), 16), info='\x00\x00\x00\x00')

def create_VHTcapabilities(VHT_capabilities: bytes):
    return Dot11Elt(ID=191, info=VHT_capabilities)

def create_Extendendcapabilities(extended_capabilities: bytes):
    return Dot11Elt(ID=127, info=extended_capabilities)

def create_wps_uuide(wps: bytes, uuide: bytes):
    return Dot11EltVendorSpecific(ID=221, info=wps), Dot11EltVendorSpecific(ID=221, info=uuide)
