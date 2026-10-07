# -*- coding: utf-8 -*-
"""FPV 链路自检：取一帧机载前视相机图像并存盘。"""
import cosysairsim as airsim
import cv2
import numpy as np

client = airsim.MultirotorClient()
client.confirmConnection()
raw = client.simGetImage("0", airsim.ImageType.Scene)
assert raw, "未取到图像数据"
img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
out = r"E:\drone-sim\platforms\cosys-airsim\scripts\fpv_test.png"
cv2.imwrite(out, img)
print("FPV 帧尺寸:", img.shape, "->", out)
