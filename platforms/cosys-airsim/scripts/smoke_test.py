# -*- coding: utf-8 -*-
"""Cosys-AirSim 连接自检：先启动 Blocks 环境，再跑这个脚本。

    conda activate cosys-airsim
    python smoke_test.py
"""
import sys

import cosysairsim as airsim

print("[1/3] cosysairsim 客户端导入 OK")

client = airsim.MultirotorClient()
print("[2/3] RPC 客户端构造 OK，正在连接模拟器（需要 Blocks 窗口已打开）……")
try:
    client.confirmConnection()
except Exception as e:
    print("连接失败：", e)
    print("请先双击 env\\Blocks\\Blocks.exe（或 Blocks.bat），等它加载完再重跑本脚本")
    sys.exit(1)

print("[3/3] 已连上模拟器！起飞测试……")
client.enableApiControl(True)
client.armDisarm(True)
client.takeoffAsync(3).join()                 # 3 秒起飞到 1 米
client.moveToPositionAsync(0, -5, -3, 2).join()  # NED 坐标：z=-3 即 3 米高，y=-5 向前 5 米
state = client.getMultirotorState()
pos = state.kinematics_estimated.position
print(f"当前位置: x={pos.x_val:.2f}, y={pos.y_val:.2f}, z={pos.z_val:.2f}")

img = client.simGetImage("0", airsim.ImageType.Scene)
print("相机图像字节数:", len(img) if img else 0)

client.landAsync().join()
client.armDisarm(False)
client.enableApiControl(False)
print("自检完成：连接、起飞、移动、取图、降落全部通过 ✔")
