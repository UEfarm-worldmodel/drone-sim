# -*- coding: utf-8 -*-
"""gym-pybullet-drones 最小 demo：悬停+圆轨迹跟踪，同时录制 (s, a, s') 轨迹。

这是无人机仿真数据契约的草案 v0：
  s_t   = 20 维状态向量（位置/四元数/欧拉角/角速度/上一帧 RPM）
  a_t   = 4 维 RPM 动作
  s_t+1 = 下一帧 20 维状态
落盘格式：CSV（一行一步）+ NPZ（数组），将来 UE 农场端照此结构导出。

运行（本机虚拟环境已装好）：
    .venv/Scripts/python demo_录制轨迹.py      # 本脚本（无 GUI，出 CSV + PNG）
    想看画面：.venv/Scripts/python gym-pybullet-drones/gym_pybullet_drones/examples/pid.py
"""
import os
import sys
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")  # 无窗口环境也能出图
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "gym-pybullet-drones"))

from gym_pybullet_drones.envs.CtrlAviary import CtrlAviary
from gym_pybullet_drones.control.DSLPIDControl import DSLPIDControl
import argparse
import time
from gym_pybullet_drones.utils.enums import DroneModel, Physics
from gym_pybullet_drones.utils.utils import sync

OUT_DIR = r"E:\drone-sim\data\gym-pybullet-drones"   # 统一数据目录：所有平台的 (s,a,s') 产物都进这里
os.makedirs(OUT_DIR, exist_ok=True)

PYB_FREQ = 240          # 物理仿真频率
CTRL_FREQ = 48          # 控制频率（每秒 48 个 (s,a,s') 样本）
DURATION = 6            # 仿真时长（秒）：1.5s 爬升悬停 + 4.5s 圆轨迹
N_STEPS = CTRL_FREQ * DURATION
CTRL_TIMESTEP = 1.0 / CTRL_FREQ

# 目标轨迹：先在 (0,0,0.5) 悬停 1.5 秒，再走半径 0.3 的圆
TARGET = np.zeros((N_STEPS, 3))
for i in range(N_STEPS):
    t = i * CTRL_TIMESTEP
    if t < 1.5:
        TARGET[i] = (0.0, 0.0, 0.5)
    else:
        theta = (t - 1.5) * (2 * math.pi / 6.0)   # 6 秒一圈，转 0.75 圈
        TARGET[i] = (0.3 * math.cos(theta), 0.3 * math.sin(theta), 0.5)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gui", action="store_true", help="打开 3D 窗口实时观看（按设定速度实时播放）")
    GUI = ap.parse_args().gui
    env = CtrlAviary(
        drone_model=DroneModel.CF2X,
        num_drones=1,
        initial_xyzs=np.array([[0.0, 0.0, 0.1]]),
        physics=Physics.PYB,
        pyb_freq=PYB_FREQ,
        ctrl_freq=CTRL_FREQ,
        gui=GUI,
        record=False,
        obstacles=False,
        user_debug_gui=False,
    )
    pid = DSLPIDControl(drone_model=DroneModel.CF2X)
    obs, info = env.reset(seed=0)   # 固定种子，轨迹可复现

    rows = []                        # 数据契约：t, s_t(20), a_t(4), s_t+1(20), 目标(3)
    start_time = time.time()
    for i in range(N_STEPS):
        state = np.atleast_2d(obs)[0]
        rpm, pos_err, yaw_err = pid.computeControl(
            control_timestep=CTRL_TIMESTEP,
            cur_pos=state[0:3],
            cur_quat=state[3:7],
            cur_vel=state[10:13],
            cur_ang_vel=state[13:16],
            target_pos=TARGET[i, :],
        )
        next_obs, reward, terminated, truncated, info = env.step(np.asarray(rpm).reshape(1, 4))

        rows.append(np.concatenate(([i * CTRL_TIMESTEP], state, np.asarray(rpm).flatten(),
                                    np.atleast_2d(next_obs)[0], TARGET[i, :])))
        obs = next_obs
        if GUI:
            sync(i, start_time, CTRL_TIMESTEP)   # GUI 模式按实时速度播放
        if terminated or truncated:
            print(f"提前终止于第 {i} 步")
            break

    env.close()
    data = np.array(rows)
    n_state = 20

    # ---- CSV（人类可读）----
    header = (["t"]
              + [f"s_t_{j}" for j in range(n_state)]
              + [f"a_t_rpm{j}" for j in range(4)]
              + [f"s_t1_{j}" for j in range(n_state)]
              + ["target_x", "target_y", "target_z"])
    csv_path = os.path.join(OUT_DIR, "trajectory.csv")
    np.savetxt(csv_path, data, delimiter=",", header=",".join(header), comments="")

    # ---- NPZ（喂模型的干净数组版）----
    npz_path = os.path.join(OUT_DIR, "trajectory.npz")
    np.savez(npz_path,
             t=data[:, 0],
             s_t=data[:, 1:1 + n_state],
             a_t=data[:, 1 + n_state:5 + n_state],
             s_t1=data[:, 5 + n_state:25 + n_state],
             target=data[:, 25 + n_state:28 + n_state])

    # ---- 跟踪图 ----
    pos = data[:, 1:4]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    ax1.plot(TARGET[:, 0], TARGET[:, 1], "g--", lw=1, label="目标轨迹")
    ax1.plot(pos[:, 0], pos[:, 1], "b-", lw=1, label="实际轨迹")
    ax1.set_xlabel("x (m)"); ax1.set_ylabel("y (m)"); ax1.axis("equal")
    ax1.set_title("XY 平面轨迹跟踪"); ax1.legend(); ax1.grid(alpha=0.3)
    t = data[:, 0]
    ax2.plot(t, TARGET[:, 2], "g--", lw=1, label="目标 z")
    ax2.plot(t, pos[:, 2], "b-", lw=1, label="实际 z")
    ax2.set_xlabel("t (s)"); ax2.set_ylabel("z (m)")
    ax2.set_title("高度跟踪"); ax2.legend(); ax2.grid(alpha=0.3)
    fig.suptitle("gym-pybullet-drones demo：Crazyflie 2.x · PID · 48Hz 控制")
    fig.tight_layout()
    png_path = os.path.join(OUT_DIR, "tracking.png")
    fig.savefig(png_path, dpi=150)

    # ---- 统计 ----
    err = np.linalg.norm(pos - TARGET, axis=1)
    print(f"\n完成：{len(data)} 步（{DURATION}s × {CTRL_FREQ}Hz）")
    print(f"位置跟踪 RMSE = {np.sqrt((err**2).mean())*100:.1f} cm（后 3 秒 {np.sqrt((err[-CTRL_FREQ*3:]**2).mean())*100:.1f} cm）")
    print(f"数据契约 v0 输出：\n  {csv_path}\n  {npz_path}\n  {png_path}")

if __name__ == "__main__":
    main()
