# -*- coding: utf-8 -*-
"""
autotune_calibration.py  ——  可替换版本（含停止条件 + 快速仿真 + 健壮解析）

用法（示例）：
    python autotune_calibration.py \
        --max-iters 12 \
        --patience 4 \
        --walltime-sec 900 \
        --duration-min 3 \
        --dataset-type single_locked \
        --brand Xiaomi \
        --model xiaomi_auto

可选：如果你有一份真实目标（REAL TARGET）指标的 JSON：
    {
      "MCR": 0.4641,
      "NUMR": 0.0326,
      "MCIV": 1322905.0
    }
可通过 --target-json 指定；否则使用下面 DEFAULT_TARGET 作为兜底。
"""

from __future__ import annotations
import argparse
import contextlib
import io
import json
import math
import os
import random
import re
import signal
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# ==== 你工程里的主仿真入口 ====
# 需要 main.py 里提供：run_simulation(sim_out_file, dataset_type, sim_duration_minutes, device_count, scene_params)
try:
    import main  # noqa: F401
except Exception as e:
    print("导入 main.py 失败，请确认该文件与本脚本在同一工程内。错误：", repr(e))
    raise

# ------------ 配置与默认值 ------------
# 若未提供目标 JSON，这组会作为默认“真实指标”
DEFAULT_TARGET = {
    "MCR": 0.4641,       # changes / second
    "NUMR": 0.0326,      # unique-mac / total
    "MCIV": 1322905.0,   # 真实数据中经常是微秒或其派生量；我们做相对误差归一
}

# 参数采样边界（可按需要微调）
SCALE_BETWEEN_RANGE = (0.30, 2.50)
SPREAD_BETWEEN_RANGE = (0.05, 1.50)
BURST_GAMMA_RANGE   = (0.01, 0.60)

# 权重（可按需要微调）
W_MCR  = 0.5
W_NUMR = 0.3
W_MCIV = 0.2

# 接受阈值（相对误差）
THRESH = {
    "MCR":  0.10,   # 10%
    "NUMR": 0.20,   # 20%
    "MCIV": 0.35,   # 35%
}

@dataclass
class SceneParams:
    # 与 main.run_simulation 的 scene_params 对齐（不要求完全匹配，冗余键不会出错）
    realtime: bool = False     # 关键：避免实时 sleep，提升速度
    fixed_phase: int = 2       # 单设备锁相位时使用
    allow_state_switch: bool = False
    brand: Optional[str] = None
    model: Optional[str] = None
    # 可扩展的调参量
    scale_between: float = 1.0
    spread_between: float = 0.2
    burst_gamma: float = 0.1
    # 其它可能被 main 消费的提示性开关（可有可无）
    avoid_bg_sleep: bool = True
    seed: Optional[int] = None


# ------------------ 指标与误差 ------------------
def _safe_rel_err(sim_v: float, tgt_v: float, eps: float = 1e-12) -> float:
    """相对误差：|sim - tgt| / (|tgt| + eps)，统一为无量纲，避免单位主导。"""
    return abs(sim_v - tgt_v) / (abs(tgt_v) + eps)

def score_error(sim: Dict[str, float], target: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    """
    计算三指标的相对误差并加权。
    这里对 MCIV 不再做绝对单位换算，而是直接用相对误差，天然规避单位量纲问题。
    """
    e_mcr  = _safe_rel_err(sim.get("MCR", 0.0),  target.get("MCR", 0.0))
    e_numr = _safe_rel_err(sim.get("NUMR", 0.0), target.get("NUMR", 0.0))
    # MCIV：直接相对误差，即使单位不同也不至于“量纲碾压”
    e_mciv = _safe_rel_err(sim.get("MCIV", 0.0), target.get("MCIV", 0.0))

    total = W_MCR * e_mcr + W_NUMR * e_numr + W_MCIV * e_mciv
    return total, {"e_mcr": e_mcr, "e_numr": e_numr, "e_mciv": e_mciv}

def is_good_enough(errors: Dict[str, float]) -> bool:
    return (
        errors["e_mcr"]  <= THRESH["MCR"] and
        errors["e_numr"] <= THRESH["NUMR"] and
        errors["e_mciv"] <= THRESH["MCIV"]
    )


# ------------------ 仿真与解析 ------------------
def _unique_run_tag(prefix: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{prefix}_{ts}"

def _capture_stdout(func, *args, **kwargs) -> Tuple[str, Any]:
    """捕获函数执行期间的 stdout，返回(文本, 函数返回值)。"""
    buf = io.StringIO()
    rv = None
    try:
        with contextlib.redirect_stdout(buf):
            rv = func(*args, **kwargs)
    finally:
        out = buf.getvalue()
    return out, rv

def _try_read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None

def _try_read_text(path: str) -> Optional[str]:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception:
        pass
    return None

def _parse_metrics_from_stdout(stdout_str: str) -> Dict[str, float]:
    """
    兜底：从仿真 stdout 中尽力提取/估算 MCR、NUMR、MCIV。
    - 优先找带关键字的统计行；
    - 否则用时间戳行估算（近似，保证调参过程可进行且有可比性）。
    """
    m = {"MCR": 0.0, "NUMR": 0.0, "MCIV": 0.0}

    # 1) 直接统计行（如果 main 打印了）
    # 例如：MCR=..., NUMR=..., MCIV=...
    direct = re.search(r"MCR\s*=\s*([0-9.]+).+?NUMR\s*=\s*([0-9.]+).+?MCIV\s*=\s*([0-9.]+)", stdout_str, re.S)
    if direct:
        try:
            m["MCR"]  = float(direct.group(1))
            m["NUMR"] = float(direct.group(2))
            m["MCIV"] = float(direct.group(3))
            return m
        except Exception:
            pass

    # 2) NUMR 估算：若日志里包含 “Total number of different MAC:” 与 “Total number of packets:”
    # 有些实现会把这两行打到 stdout（更多时候写文件，文件解析在下面）
    macs = re.search(r"Total number of different MAC.*?:\s*([0-9]+)", stdout_str)
    pkts = re.search(r"Total number of packets.*?:\s*([0-9]+)", stdout_str)
    if macs and pkts:
        try:
            unique_mac = float(macs.group(1))
            total_pkt  = float(pkts.group(1))
            if total_pkt > 0:
                m["NUMR"] = unique_mac / total_pkt
        except Exception:
            pass

    # 3) 利用“发送成功”行的时间戳估算 MCIV（仅作为近似兜底）
    # 形如：[2025-09-15 07:52:50.737935] 设备 0 发送数据包（成功）。
    ts = []
    for line in stdout_str.splitlines():
        # 提取 [YYYY-mm-dd HH:MM:SS.micro] 这样的时间戳
        mo = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\].*发送数据包（成功", line)
        if mo:
            try:
                dt = datetime.strptime(mo.group(1), "%Y-%m-%d %H:%M:%S.%f").timestamp()
                ts.append(dt)
            except Exception:
                pass
    if len(ts) >= 3:
        intervals = [ts[i+1] - ts[i] for i in range(len(ts)-1)]
        if intervals:
            mean = sum(intervals) / len(intervals)
            var  = sum((x - mean) ** 2 for x in intervals) / len(intervals)
            # 这里把“发送间隔方差”当作 MCIV 的兜底近似
            m["MCIV"] = var

    # 4) MCR 兜底估算：若日志中能识别到 “MAC 变更/更换/随机化”等事件，则据此统计；否则按 0 处理
    mac_change = 0
    for line in stdout_str.splitlines():
        if re.search(r"MAC.*(变更|更换|随机|rotation|changed)", line, re.I):
            mac_change += 1
    if mac_change and ts:
        # 每秒变化次数 ≈ 变化次数 / 总时长（用首次与末次发送时间估算）
        dur = max(ts) - min(ts)
        if dur > 0:
            m["MCR"] = mac_change / dur

    return m

def _parse_metrics_from_files(base_out: str) -> Optional[Dict[str, float]]:
    """
    从文件解析指标。支持多种可能的导出：
      - {base}_stats.json（若你的 main 写过这类文件，这是首选）
      - {base}.txt（若包含统计行）
      - {base}_packets.csv / {base}_devices.csv（可扩展：此处演示对 .txt 的解析，csv 如需更精确可按列解析）
    """
    # 1) stats.json
    j = _try_read_json(f"{base_out}_stats.json")
    if j and all(k in j for k in ("MCR", "NUMR", "MCIV")):
        # 允许键名大小写不敏感
        return {
            "MCR":  float(j.get("MCR", 0.0)),
            "NUMR": float(j.get("NUMR", 0.0)),
            "MCIV": float(j.get("MCIV", 0.0)),
        }

    # 2) 主文本日志
    txt = _try_read_text(f"{base_out}.txt") or _try_read_text(base_out)
    if txt:
        out = _parse_metrics_from_stdout(txt)
        # 只要至少有一项非零，就认为取到了有效估计
        if any(out.values()):
            return out

    # 3) 设备/分包 CSV —— 这里按需扩展；先返回 None 表示没取到
    return None

def run_one_simulation(sim_out_base: str,
                       dataset_type: str,
                       duration_min: int,
                       scene: SceneParams,
                       device_count: int = 1) -> Tuple[Dict[str, float], str]:
    """
    运行一次仿真并解析三指标。返回 (metrics, raw_stdout)。

    说明：
      - 默认捕获 stdout，以便我们兜底解析；
      - 同时尝试从 {sim_out_base}_stats.json / {sim_out_base}.txt 读取更“官方”的统计；
      - 若两者都没有，就用 stdout 近似（保证调参流程可继续进行）。
    """
    # 确保输出目录存在
    out_dir = os.path.dirname(sim_out_base)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # 统一打包 scene_params
    scene_params: Dict[str, Any] = asdict(scene)
    # 过滤 None
    scene_params = {k: v for k, v in scene_params.items() if v is not None}

    # 真正调用主仿真
    stdout_text, _ = _capture_stdout(
        main.run_simulation,
        sim_out_base,                 # 注意：你的 main 里可能会自己加扩展名
        dataset_type,
        duration_min,
        device_count,
        scene_params
    )

    # 先尝试文件解析（更精确）
    file_metrics = _parse_metrics_from_files(sim_out_base)
    if file_metrics:
        metrics = file_metrics
    else:
        # 回退到 stdout 提取（近似）
        metrics = _parse_metrics_from_stdout(stdout_text)

    # 最终仍保证返回三项键
    metrics.setdefault("MCR",  0.0)
    metrics.setdefault("NUMR", 0.0)
    metrics.setdefault("MCIV", 0.0)

    return metrics, stdout_text


# ------------------ 自动调参主循环 ------------------
def random_params_around(center: SceneParams, step_scale=0.25) -> SceneParams:
    """
    在当前最优附近做随机扰动；边界会被夹紧到 RANGE 内。
    step_scale 控制扰动幅度。
    """
    def jitter(val, lo, hi):
        span = (hi - lo) * step_scale
        v = val + random.uniform(-span, span)
        return max(lo, min(hi, v))

    return SceneParams(
        realtime=center.realtime,
        fixed_phase=center.fixed_phase,
        allow_state_switch=center.allow_state_switch,
        brand=center.brand,
        model=center.model,
        scale_between=jitter(center.scale_between, *SCALE_BETWEEN_RANGE),
        spread_between=jitter(center.spread_between, *SPREAD_BETWEEN_RANGE),
        burst_gamma=jitter(center.burst_gamma, *BURST_GAMMA_RANGE),
        avoid_bg_sleep=True,
        seed=None
    )


def autotune(target: Dict[str, float],
             dataset_type: str,
             duration_min: int,
             brand: Optional[str],
             model: Optional[str],
             max_iters: int,
             patience: int,
             walltime_sec: int,
             out_prefix: str,
             initial: Optional[SceneParams] = None,
             seed: Optional[int] = None) -> Dict[str, Any]:

    if seed is not None:
        random.seed(seed)

    # 初始点（相对稳妥的一组）
    best_scene = initial or SceneParams(
        realtime=False,
        fixed_phase=2,
        allow_state_switch=False,
        brand=brand,
        model=model,
        scale_between=1.0,
        spread_between=0.2,
        burst_gamma=0.10,
        avoid_bg_sleep=True,
        seed=seed
    )

    print("欢迎使用 probe request 传输仿真系统（自动调参模式）")
    print(f"[REAL TARGET] {target}")
    print(f"仿真参数设置：数据集类型 = {dataset_type}，仿真时长 = {duration_min} 分钟，设备数 = 1，"
          f"固定品牌/机型 = {brand}/{model}，realtime={best_scene.realtime}\n")

    t0 = time.time()
    best_metrics, best_errors, best_score = None, None, float("inf")
    no_improve = 0

    history = []  # 记录每轮结果

    for it in range(1, max_iters + 1):
        now = time.time()
        if now - t0 > walltime_sec:
            print(f"\n[停止] 触发墙钟超时（{walltime_sec}s），结束调参。")
            break

        # 迭代 1 用最佳点；之后围绕最佳点扰动
        scene = best_scene if best_metrics is None else random_params_around(best_scene, step_scale=0.25)
        sim_tag = _unique_run_tag(f"{out_prefix}_iter{it}")
        sim_out_base = os.path.join("calib_runs", sim_tag)

        print(f"\n===== 迭代 {it} / {max_iters} =====")
        print("[PARAMS]", {k: v for k, v in asdict(scene).items() if k in ("scale_between","spread_between","burst_gamma","realtime")})

        try:
            sim_metrics, stdout_s = run_one_simulation(
                sim_out_base=sim_out_base,
                dataset_type=dataset_type,
                duration_min=duration_min,
                scene=scene,
                device_count=1
            )
        except Exception as e:
            print(f"[迭代 {it}] 仿真异常：{repr(e)}，跳过该轮。")
            history.append({"iter": it, "scene": asdict(scene), "error": "simulation_exception"})
            no_improve += 1
            if no_improve >= patience:
                print(f"[停止] 连续 {patience} 轮无有效结果（异常/无改进），早停。")
                break
            continue

        # 打分
        score, errs = score_error(sim_metrics, target)
        history.append({
            "iter": it,
            "scene": asdict(scene),
            "sim": sim_metrics,
            "errors": errs,
            "score": score
        })

        print(f"[SIM]   {sim_metrics}")
        print(f"[ERROR] {errs}  ->  [SCORE] {score:.6f}")

        improved = score < best_score - 1e-9
        acceptable = is_good_enough(errs)

        if improved:
            print("=> 接受：更优")
            best_scene = scene
            best_metrics = sim_metrics
            best_errors = errs
            best_score = score
            no_improve = 0
        else:
            print("=> 拒绝：未改进")
            no_improve += 1

        if acceptable:
            print("[停止] 达到可接受阈值，提前结束。")
            break

        if no_improve >= patience:
            print(f"[停止] 连续 {patience} 轮无改进，早停。")
            break

    used_sec = time.time() - t0
    result = {
        "best_params": asdict(best_scene),
        "best_metrics": best_metrics,
        "best_errors": best_errors,
        "best_score": best_score,
        "iters_done": len(history),
        "used_seconds": used_sec,
        "history": history,
    }

    # 保存结果
    os.makedirs("calib_runs", exist_ok=True)
    out_path = os.path.join("calib_runs", f"{out_prefix}_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n===== 调参结束 =====")
    print("最优参数：", result["best_params"])
    print("最优指标：", result["best_metrics"])
    print("误差：", result["best_errors"], "  分数：", f"{result['best_score']:.6f}")
    print(f"历史记录与最优结果已保存：{out_path}")
    print(f"总耗时：{used_sec:.1f}s")
    return result


# ------------------ CLI ------------------
def main_cli():
    ap = argparse.ArgumentParser(description="自动标定/调参（带停止条件与快速仿真）")
    ap.add_argument("--target-json", type=str, default=None, help="目标指标 JSON 文件路径（含 MCR/NUMR/MCIV）")
    ap.add_argument("--dataset-type", type=str, default="single_locked", help="single_locked / single_active / multi 等")
    ap.add_argument("--duration-min", type=int, default=3, help="每轮仿真时长（分钟）")
    ap.add_argument("--brand", type=str, default=None, help="单设备品牌（可选）")
    ap.add_argument("--model", type=str, default=None, help="单设备型号（可选）")

    ap.add_argument("--max-iters", type=int, default=12, help="最大迭代数")
    ap.add_argument("--patience", type=int, default=4, help="早停耐心轮次")
    ap.add_argument("--walltime-sec", type=int, default=900, help="总墙钟超时（秒）")

    ap.add_argument("--seed", type=int, default=42, help="随机种子（影响采样）")
    ap.add_argument("--prefix", type=str, default="calib", help="输出前缀（用于结果/中间文件命名）")

    # 初始参数（可选，不给则用默认初值）
    ap.add_argument("--init-scale", type=float, default=1.0)
    ap.add_argument("--init-spread", type=float, default=0.2)
    ap.add_argument("--init-gamma", type=float, default=0.10)

    args = ap.parse_args()

    # 目标指标
    target = DEFAULT_TARGET.copy()
    if args.target_json and os.path.exists(args.target_json):
        try:
            with open(args.target_json, "r", encoding="utf-8") as f:
                j = json.load(f)
            # 允许大小写/别名，做一层稳健映射
            def pick(*keys, default=0.0):
                for k in keys:
                    if k in j:
                        return float(j[k])
                return default
            target = {
                "MCR":  pick("MCR", "mcr", "mac_change_rate", default=target["MCR"]),
                "NUMR": pick("NUMR", "numr", "unique_mac_ratio", default=target["NUMR"]),
                "MCIV": pick("MCIV", "mciv", "mac_change_interval_var", default=target["MCIV"]),
            }
        except Exception as e:
            print("读取 target-json 失败，改用默认目标。错误：", repr(e))

    # 初始场景参数
    init = SceneParams(
        realtime=False,
        fixed_phase=2,
        allow_state_switch=False,
        brand=args.brand,
        model=args.model,
        scale_between=max(SCALE_BETWEEN_RANGE[0], min(SCALE_BETWEEN_RANGE[1], args.init_scale)),
        spread_between=max(SPREAD_BETWEEN_RANGE[0], min(SPREAD_BETWEEN_RANGE[1], args.init_spread)),
        burst_gamma=max(BURST_GAMMA_RANGE[0], min(BURST_GAMMA_RANGE[1], args.init_gamma)),
        avoid_bg_sleep=True,
        seed=args.seed
    )

    autotune(
        target=target,
        dataset_type=args.dataset_type,
        duration_min=args.duration_min,
        brand=args.brand,
        model=args.model,
        max_iters=args.max_iters,
        patience=args.patience,
        walltime_sec=args.walltime_sec,
        out_prefix=args.prefix,
        initial=init,
        seed=args.seed
    )


if __name__ == "__main__":
    main_cli()
