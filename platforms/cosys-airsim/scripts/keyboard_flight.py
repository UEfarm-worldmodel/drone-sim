# -*- coding: utf-8 -*-
"""WASDQE 键盘飞行 demo（Cosys-AirSim · Blocks）· 全局按键版

先启动模拟器（env\\Windows\\Blocks.exe 或 一键键盘飞行.bat），再运行本脚本：

    conda activate cosys-airsim
    python keyboard_flight.py [--fpv]

--fpv：额外打开机载前视相机窗口（第一视角，约 20 FPS）。

键位（**全局生效**：焦点在 Blocks 窗口上也能飞）：
    W / S        前进 / 后退      A / D   左移 / 右移
    空格 / Shift  上升 / 下降     Q / E   偏航（左转 / 右转）
    Esc          降落退出（松开全部按键 = 原地悬停，即急停）
方向为机头系：W 永远朝当前机头方向飞。

注意：按键是系统级的——切到微信打字也会被当成飞行输入，飞完记得 Esc 退出。
"""
import argparse
import math
import sys
import time
import ctypes

import cosysairsim as airsim

user32 = ctypes.windll.user32
VK = {"w": 0x57, "a": 0x41, "s": 0x53, "d": 0x44,
      "q": 0x51, "e": 0x45, "space": 0x20, "shift": 0x10,
      "esc": 0x1B}

V_HORZ = 3.0     # 水平速度 m/s
V_VERT = 2.0     # 垂直速度 m/s
YAW_RATE = 90.0  # 偏航角速度 deg/s


def key_down(name):
    return bool(user32.GetAsyncKeyState(VK[name]) & 0x8000)


def heading_deg(state):
    """从四元数取偏航角（度）"""
    q = state.kinematics_estimated.orientation
    w, x, y, z = q.w_val, q.x_val, q.y_val, q.z_val
    return math.degrees(math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fpv", action="store_true", help="打开机载前视相机 FPV 窗口（第一视角）")
    args = ap.parse_args()
    FPV = args.fpv
    if FPV:
        import cv2
        import numpy as np

    client = airsim.MultirotorClient()
    try:
        client.confirmConnection()
    except Exception:
        print("连不上模拟器（127.0.0.1:41451）。请先启动：")
        print("    E:\\drone-sim\\platforms\\cosys-airsim\\env\\Windows\\Blocks.exe")
        print("等窗口完全加载后再重跑本脚本。")
        sys.exit(1)

    client.enableApiControl(True)
    client.armDisarm(True)
    print("起飞到 1.5 m……")
    client.takeoffAsync(2).join()
    client.moveToZAsync(-1.5, 2).join()   # 先爬到 1.5 m 再交给键盘控制
    print("键位：W/S 前后  A/D 左右  空格/Shift 升降  Q/E 偏航  Esc 降落退出（松开=悬停）")
    print("（按键全局生效：保持 Blocks 窗口在前台看画面即可）")

    yaw_cmd = heading_deg(client.getMultirotorState())
    t_prev = time.time()
    try:
        while True:
            time.sleep(max(0.0, 0.05 - (time.time() - t_prev)))
            dt = time.time() - t_prev
            t_prev = time.time()

            if key_down("esc"):
                print("\n降落退出……")
                break

            fwd = (V_HORZ if key_down("w") else 0) - (V_HORZ if key_down("s") else 0)
            right = (V_HORZ if key_down("d") else 0) - (V_HORZ if key_down("a") else 0)
            down = (V_VERT if key_down("shift") else 0) - (V_VERT if key_down("space") else 0)
            yaw_rate = (YAW_RATE if key_down("e") else 0) - (YAW_RATE if key_down("q") else 0)

            yaw_cmd += yaw_rate * dt
            # 机头系速度 → 世界 NED 系
            rad = math.radians(yaw_cmd)
            vx = fwd * math.cos(rad) - right * math.sin(rad)
            vy = fwd * math.sin(rad) + right * math.cos(rad)
            client.moveByVelocityAsync(vx, vy, down, 0.3,
                                       drivetrain=airsim.DrivetrainType.MaxDegreeOfFreedom,
                                       yaw_mode=airsim.YawMode(True, yaw_rate))

            if FPV:
                raw = client.simGetImage("0", airsim.ImageType.Scene)
                if raw:
                    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
                    if img is not None:
                        cv2.imshow("FPV - onboard camera 0", cv2.resize(img, (512, 288)))
                if cv2.waitKey(1) & 0xFF == 27:   # FPV 窗口内按 Esc 同样退出
                    break

            s = client.getMultirotorState()
            p = s.kinematics_estimated.position
            print(f"\r位置 x={p.x_val:+6.1f} y={p.y_val:+6.1f} z={-p.z_val:5.1f} m | "
                  f"机头 {yaw_cmd % 360:5.1f}° | 输入 f={fwd:+.0f} r={right:+.0f} d={down:+.0f} yaw={yaw_rate:+.0f}   ",
                  end="", flush=True)
    finally:
        print("\n降落并交还控制权……")
        try:
            client.landAsync().join()
            client.armDisarm(False)
            client.enableApiControl(False)
        except Exception:
            pass
        if FPV:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n中断退出")
        sys.exit(0)
