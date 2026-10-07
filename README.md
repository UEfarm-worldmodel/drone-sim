# drone-sim：无人机仿真平台学习与测试工作区

面向无人机方向的模拟器调研与实测工作区：对比主流无人机仿真平台，为"农田场景 + 无人机群 + 数据导出"的自研仿真工程选型，并沉淀一套可复用的部署脚本与 (状态, 动作, 下一状态) 数据管线。

> 本仓库只含**自研脚本与调研笔记**；第三方模拟器本体不入库（见下方各平台的克隆/下载说明）。

## 目录结构

```
E:\drone-sim\                        ← 工作区（必须纯英文路径，原因见"已知坑"）
├── README.md                        ← 本文件
├── platforms\                       每个仿真平台一个自包含目录
│   ├── gym-pybullet-drones\         ✅ 已部署（conda env: drones）
│   │   ├── gym-pybullet-drones\       第三方仓库（clone 而来，不入库）
│   │   └── demo_record_trajectory.py  (s,a,s') 轨迹录制脚本
│   ├── cosys-airsim\                ✅ 已部署（conda env: cosys-airsim）
│   │   ├── env\Windows\Blocks.exe     预编译场景（下载而来，不入库）
│   │   └── scripts\                   自检 / WASDQE 键盘飞行 / RPC 诊断
│   ├── isaac-lab\                   ⬜ 待部署（独立环境 + RTX 显卡机器）
│   ├── flightmare\                  ⬜ 选做（Docker 容器化）
│   └── gazebo-px4\                  ⬜ 暂缓（实机为自研飞控，PX4 链不适用）
├── data\                            运行产物（不入库），按平台分目录
└── notes\                           各平台调研笔记（原理/优缺点/部署记录/踩坑/文献）
```

## 全局约定

1. **路径只放英文**，新平台目录用小写连字符。
2. **每个平台独立 conda 环境**（env 名 = 平台名），互不污染。
3. **数据契约统一**：所有平台产出统一的 (状态, 动作, 下一状态) 三元组，落到 `data\<平台名>\`，字段结构见 `platforms/gym-pybullet-drones/demo_record_trajectory.py` 的 CSV 表头（t + 20 维状态 + 4 维动作 + 20 维下态 + 目标位姿）。
4. **pip 走清华镜像**：`-i https://pypi.tuna.tsinghua.edu.cn/simple`（直连 PyPI 可能被代理挂死）。
5. 平台部署完成的标准：能跑通最小 demo 并输出自己的 (s,a,s') 数据。

---

## 平台 1：gym-pybullet-drones ✅

UTIAS 出品（IROS 2021），PyBullet 刚体动力学 + Gymnasium API 的轻量研究环境，MBRL/世界模型无人机论文的事实标准之一（DreamerV3 纯像素飞行 *Dream to Fly*, 2025 出自该生态）。

```bash
conda create -n drones python=3.12 -y
conda activate drones
cd platforms\gym-pybullet-drones
git clone --depth 1 https://github.com/learnsyslab/gym-pybullet-drones.git gym-pybullet-drones
pip install -e ./gym-pybullet-drones -i https://pypi.tuna.tsinghua.edu.cn/simple

# 轨迹录制 demo（无 GUI 秒出；--gui 开 3D 窗口实时播放）
python demo_record_trajectory.py
# 官方示例
python gym-pybullet-drones/gym_pybullet_drones/examples/pid.py
python gym-pybullet-drones/gym_pybullet_drones/examples/learn.py   # PPO 悬停训练
```

Windows 注意：**pybullet 无预编译包**，需 VS2022 的 C++ 工作负载由 pip 源码编译（一次性 10-20 分钟）。

## 平台 2：Cosys-AirSim ✅（AirSim / Colosseum 系现役续作）

血统：AirSim（微软，2022 归档）→ Colosseum（2026-07 归档）→ **Cosys-AirSim**（活跃）。UE 原生 + msgpack-RPC API（多相机/传感器），是"UE 场景 + 无人机 API"的接口范本。

```bash
conda create -n cosys-airsim python=3.12 -y
conda activate cosys-airsim
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple numpy opencv-python msgpack-rpc-python
pip install https://github.com/Cosys-Lab/Cosys-AirSim/releases/download/5.8-v3.5.0/cosysairsim-3.5.0-py3-none-any.whl
```

场景：下载 [Blocks 预编译包](https://github.com/Cosys-Lab/Cosys-AirSim/releases/download/5.8-v3.5.0/Blocks_packaged_Windows_58_350.zip)（0.56GB，免装 UE）解压到 `platforms\cosys-airsim\env\`。

```bash
# 启动模拟器（exe 必须以其所在目录为工作目录启动，见"已知坑"）
cd platforms\cosys-airsim\env\Windows && .\Blocks.exe

# 自检（起飞/移动/取图/降落）与 WASDQE 键盘飞行
cd ..\..\scripts
python smoke_test.py
python keyboard_flight.py
```

> **msgpackrpc 兼容补丁**：Cosys 的 Python 客户端依赖 2018 年的 msgpackrpc，与本机 tornado 6.5 / msgpack 1.x 冲突，需打 5 处补丁（清单见 `notes/cosys-airsim调研笔记.md` §4，或直接对照笔记修改 site-packages）。

## 待部署

- **Isaac Sim / Isaac Lab**：大规模并行训练后端（数千 GPU 并行实例），需 Linux + RTX 机器、独立环境。
- **Flightmare**：渲染/物理解耦架构的研究平台（UZH RPG），仓库 2022 年后停滞，选做、建议 Docker。
- **Gazebo + PX4 SITL**：暂缓——实机（WHEELTEC F570）为自研 STM32 飞控，非 PX4 生态。

## 数据契约（v0）

`trajectory.csv` 每行一步：`t, s_t(20), a_t(4 RPM), s_t+1(20), target(3)`；`trajectory.npz` 为同名数组。20 维状态 = 位置(3) + 四元数(4) + 欧拉角(3) + 线速度(3) + 角速度(3) + 上帧动作(4)。该格式即未来 UE 农场仿真导出接口的草案：**字段明确、频率稳定、动作可标注、种子可复现**。

## 已知坑（每一条都踩过）

1. **中文路径**：pybullet 的 `loadURDF` 读不了含中文/空格的目录（报 URDF not found 但文件在）；UE 工程同理。工作区一律纯英文。
2. **pybullet Windows 编译**：无预编译包，需 VS2022 C++ 工作负载。
3. **代理挂 pip**：进程零 CPU 卡死 = 网络被代理挂住，换清华镜像直连。
4. **UE 打包 exe 的工作目录**：`Start-Process` 不带 `-WorkingDirectory` 从其他目录启动会静默失败。
5. **msgpackrpc × tornado 6.5**：`tornado.platform.auto`、`PeriodicCallback` 三参、`IOStream(io_loop=)`、callback 风格 connect/write、`read_until_close(streaming_callback)` 五处不兼容，补丁清单见笔记。
6. **gym-pybullet-drones v2.2.0**：要求 Python ≥3.12；20 维观测顺序 = 位置/四元数/欧拉角/**线速度/角速度**/上帧动作——把线速度当角速度喂给 PID 会炸机。

## 平台调研笔记

- [`notes/gym-pybullet-drones调研笔记.md`](notes/gym-pybullet-drones调研笔记.md) —— 原理、示例导览、与 WHEELTEC F570 实机的参数对接思路
- [`notes/cosys-airsim调研笔记.md`](notes/cosys-airsim调研笔记.md) —— 血统考证、API 面、部署全记录、键盘飞行脚本说明
