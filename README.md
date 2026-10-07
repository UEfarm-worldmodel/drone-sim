# drone-sim：无人机仿真平台调研与测试工作区

面向无人机方向的模拟器调研与实测工作区：对比主流无人机仿真平台，为"农田场景 + 无人机群 + 数据导出"的自研仿真工程选型，并沉淀一套可复用的部署脚本与 (状态, 动作, 下一状态) 数据管线。本仓库仅包含自研脚本与本文档；第三方模拟器本体不入库，获取方式见各平台章节。

## 1. 目录结构

```
drone-sim\
├── README.md                        ← 本文件（唯一文档）
├── platforms\                       每个仿真平台一个自包含目录
│   ├── gym-pybullet-drones\         ✅ 已部署（conda env: drones）
│   │   ├── gym-pybullet-drones\       第三方仓库（clone 而来，不入库）
│   │   └── demo_record_trajectory.py  轨迹录制脚本
│   ├── cosys-airsim\                ✅ 已部署（conda env: cosys-airsim）
│   │   ├── env\Windows\Blocks.exe     预编译场景（下载而来，不入库）
│   │   └── scripts\                   自检 / 键盘飞行 / RPC 诊断脚本
│   ├── isaac-lab\                   ⬜ 待部署（独立环境 + RTX 显卡）
│   ├── flightmare\                  ⬜ 选做（Docker 容器化）
│   └── gazebo-px4\                  ⬜ 暂缓（实机为自研飞控，PX4 链不适用）
└── data\                            运行产物（不入库），按平台分目录
```

## 2. 全局约定

1. 工作区及所有子目录**只使用英文路径**（原因见 §6.1）。
2. 每个平台使用**独立 conda 环境**（环境名 = 平台名），互不污染。
3. 所有平台产出统一的 (状态, 动作, 下一状态) 三元组，写入 `data\<平台名>\`，字段结构见 §3.4。
4. pip 统一使用清华镜像：`-i https://pypi.tuna.tsinghua.edu.cn/simple`（直连 PyPI 可能被代理长时间阻塞）。
5. 平台部署完成的判据：最小示例可运行，并能输出本平台的 (s, a, s') 数据。

## 3. 平台一：gym-pybullet-drones（已部署）

### 3.1 概述

UTIAS（多伦多大学航空航天研究所）动态系统实验室开发，Panerati 等发表于 IROS 2021，MIT 许可证。本质是将 PyBullet 物理引擎封装为 Gymnasium 标准接口的无人机研究环境，面向 RL / MBRL 研究场景。

关键文献先例：RPG 实验室 Dream to Fly（arXiv:2501.14377, 2025）以 DreamerV3 纯像素输入在本环境训练竞速策略，经硬件在环部署真机（9 m/s）。仿真器、观测、世界模型、策略控制的完整技术路径均可在本平台复现。

### 3.2 实现原理

- 物理内核：PyBullet 刚体引擎，四旋翼采用简化转子动力学（转子转速一阶滞后，推力/扭矩系数合成机体受力），含气动阻力与碰撞；URDF 与动力学公式公开（论文第 III 节）。
- 机型：默认 Bitcraze Crazyflie 2.x（X/十字构型），新版含 RACE 竞速机型；支持硬件在环（HITL）。
- 动作接口分层：底层 RPM（自行实现控制器，适用于世界模型数据采集）；位置目标（内置级联 PID，适用于快速实验）；速度控制。
- 观测：默认 20 维状态向量（位置 3 + 四元数 4 + 欧拉角 3 + 角速度 3 + 上一帧动作 4）；支持 RGB/深度/分割相机。
- 多机：`Aviary` 原生支持多机同飞；`downwash.py` 演示上机气流对下机的气动干扰。
- RL 生态：Gymnasium 标准 API，兼容 stable-baselines3 2.0。

### 3.3 部署

```bash
conda create -n drones python=3.12 -y
conda activate drones
cd platforms\gym-pybullet-drones
git clone --depth 1 https://github.com/learnsyslab/gym-pybullet-drones.git gym-pybullet-drones
pip install -e ./gym-pybullet-drones -i https://pypi.tuna.tsinghua.edu.cn/simple
```

Windows 注意：pybullet 无预编译包，需 VS2022 C++ 工作负载由 pip 源码编译（一次性，约 10–20 分钟）。

### 3.4 示例与数据管线

```bash
# PID 跟踪圆轨迹（GUI）
python gym-pybullet-drones/gym_pybullet_drones/examples/pid.py
# PPO 悬停训练（GUI，完成后 play.py 回放）
python gym-pybullet-drones/gym_pybullet_drones/examples/learn.py
# 轨迹录制（数据契约 v0；--gui 打开三维窗口实时播放）
python demo_record_trajectory.py
```

数据契约 v0：`trajectory.csv` 每行一步，字段为 `t, s_t(20), a_t(4 RPM), s_t+1(20), target(3)`；`trajectory.npz` 为同名数组。20 维状态 = 位置(3) + 四元数(4) + 欧拉角(3) + 线速度(3) + 角速度(3) + 上帧动作(4)。该格式即 UE 农场仿真导出接口草案，设计原则：字段明确、频率稳定、动作可标注、随机种子可复现。

### 3.5 部署验证结论

轨迹录制、PID 跟踪、PPO 悬停训练均已在本机验证。位置跟踪 RMSE ≈ 16 cm 的残差属于纯位置 PID 无速度前馈条件下的固有跟随误差（目标切向速度越高滞后越大），并非实现缺陷；可作为引入速度前馈（`computeControl` 的 `target_vel` 参数）的改进实验。

### 3.6 与 WHEELTEC F570 实机的参数对接

实机为 WHEELTEC F570 开源无刷四旋翼（随机资料包含使用手册、开发手册、STM32 源码、油门-推力拟合脚本）：

1. 飞控为自研 STM32F405 固件（PID 与 LQR 两套源码），非 PX4 / Betaflight。因此 PX4 SITL / Pegasus / Gazebo-PX4 的 sim-to-real 路径对该机型不适用；如需 HITL，须按其串口协议（CH9102 USB 转串口）自行开发桥接。
2. 资料包含实测油门-推力数据表：油门 48–1148（步长 50）× 电压 10–12.5 V（3S 锂电），12.5 V 满油门推力约 319 g。可据此拟合仿真推力系数，替换默认 Crazyflie（27 g 级）参数，建立 F570 机型条目（URDF 质量 + 推力/扭矩系数）。
3. 资料包另含 MATLAB 动力学参考模型（`Quadcopter.m`、`LQR.slx`）与传感器手册（STP-23L 激光测距、光流模块）。

后续工作：提取整机质量、轴距、电机 KV 值、桨尺寸，结合推力表建立 `DroneModel.F570` 机型配置；先复现 F570 悬停油门工作点，再迁移至 UE 农场仿真。

## 4. 平台二：Cosys-AirSim（已部署）

### 4.1 项目沿革

- **AirSim**（微软，2017–2022）：UE 原生无人机仿真的开创性工作，2022 年 7 月被微软归档。
- **Colosseum**（MSR → CodexLabsLLC）：AirSim 官方后继，附 RL 泛化基准（14 任务 × 20 扰动等级，Sawant et al. 2023, arXiv:2310.09371）；**2026 年 7 月亦已归档**（GitHub API 核实，Releases 无预编译产物）。
- **Cosys-AirSim**（Cosys-Lab，安特卫普大学）：AirSim 系当前持续维护的后继项目（2026-10 仍有提交），面向 UE 5.8，提供预编译环境与 pip 客户端，MIT 许可证。

结论：本系的实际部署对象为 Cosys-AirSim；引用泛化基准时仍称 Colosseum benchmark。

### 4.2 实现原理

- 架构：UE 插件 + msgpack-RPC 服务器（默认端口 41451）。Python 客户端经 RPC 下发控制指令并读取状态、图像与传感器数据。
- 飞控：内置 SimpleFlight 轻量级联控制器（无需外部固件）；亦支持 PX4 / ArduPilot 硬件在环。
- 坐标系：NED（x 北、y 东、z 下，高度为负值）。
- API：多机、多相机（RGB/深度/分割/红外/法线）、IMU/GPS/磁力计/激光雷达/光流。该 API 面是"UE 场景 + 无人机接口"的设计参考。
- 场景：Blocks 官方测试场景提供预编译可执行文件，无需安装 UE；自建场景 = UE 工程内置插件。

### 4.3 部署

```bash
conda create -n cosys-airsim python=3.12 -y
conda activate cosys-airsim
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple numpy opencv-python msgpack-rpc-python
pip install https://github.com/Cosys-Lab/Cosys-AirSim/releases/download/5.8-v3.5.0/cosysairsim-3.5.0-py3-none-any.whl
```

场景：下载 [Blocks 预编译包](https://github.com/Cosys-Lab/Cosys-AirSim/releases/download/5.8-v3.5.0/Blocks_packaged_Windows_58_350.zip)（0.56 GB）解压至 `platforms\cosys-airsim\env\`。

**msgpackrpc 兼容补丁（重新创建环境后需重新应用）**：客户端依赖的 msgpackrpc 停更于 2018 年，与 tornado 6.5 / msgpack 1.x 存在五处不兼容（修改位置 `site-packages\msgpackrpc\`）：

1. `address.py`：`tornado.platform.auto` 导入改为 try/except 兜底；
2. `loop.py`：`PeriodicCallback` 移除第三参数 io_loop；
3. `transport/tcp.py`：`IOStream` 构造移除 io_loop 关键字参数；
4. `transport/tcp.py`：`connect`/`write` 的 callback 风格改为 `Future.add_done_callback`；
5. `transport/tcp.py`：`read_until_close(streaming_callback)` 改为 `read_bytes(partial=True)` 加 Future 回调的循环读取。

### 4.4 使用

```bash
cd platforms\cosys-airsim\env\Windows
.\Blocks.exe          # 启动模拟器（可执行文件须以所在目录为工作目录，见 §6.4）

cd ..\..\scripts
python smoke_test.py        # 自检：连接、起飞、移动、取图、降落
python keyboard_flight.py   # 键盘飞行
```

键盘飞行键位：W/S 前后，A/D 左右，空格/Shift 升降，Q/E 偏航，Esc 降落退出；松开全部按键即原地悬停。按键经 `GetAsyncKeyState` 全局捕获，模拟器窗口保持焦点即可控制；由于按键为系统级捕获，在其他窗口输入文字亦会被视为飞行指令，结束后请按 Esc 退出。Blocks 窗口内按 F10 可切换内置手动模式。

HUD 提示说明：`API call was not received, entering hover mode` 为 SimpleFlight 安全看门狗（1 秒未收到指令即自动悬停，如脚本被 Ctrl+C 终止时）；`materials.csv not found` 仅影响分割图接口，对 RGB/深度与控制无影响。部署验收记录：2026-10-07 自检脚本全链路通过（连接、起飞、移动、状态读取、取图、降落）。

### 4.5 与本项目的集成

1. **UE 农场接口设计参考**：RPC API 面（状态/控制/多相机/传感器 + NED 契约）即为农场仿真 API 的设计蓝本；`smoke_test.py` 的调用序列可直接翻译为 UE 接口清单。
2. **数据集生成**：`simGetImage` 支持多相机多模态，可批量生成带位姿标注的模拟农田图像。
3. **F570 对接**：实机为自研 STM32 飞控，在 Cosys 中以 SimpleFlight 为对照；如需贴合实机动力学，采用 §3.6 的 F570 推力数据重新参数化。
4. **UE 版本**：本机 UE 为 5.7.4，Cosys 最新插件仅提供 UE 5.8 构建。自建农场环境时可选：以 VS2022 从源码编译插件（兼容 5.7），或加装 UE 5.8（引擎版本可共存）。

## 5. 待部署平台

- **Isaac Sim / Isaac Lab**：大规模并行训练后端（GPU 数千并行实例），需 Linux + RTX 机器与独立环境。
- **Flightmare**：渲染/物理解耦架构（UZH RPG），上游 2022 年后停滞，选做，建议 Docker 部署。
- **Gazebo + PX4 SITL**：暂缓，理由见 §3.6（实机非 PX4 生态）。

## 6. 已知问题与工程注意事项

1. **中文路径**：pybullet 的 `loadURDF` 无法读取含中文或空格的目录（报 URDF not found 但文件存在）；UE 工程同理。所有仿真工程使用纯英文路径。
2. **pybullet Windows 编译**：无预编译包，需 VS2022 C++ 工作负载。
3. **代理阻塞 pip**：进程零 CPU 占用的长时间卡滞通常为网络被代理阻塞，应改用清华镜像。
4. **UE 打包可执行文件的工作目录**：以 `Start-Process` 从其他目录启动且不带 `-WorkingDirectory` 时会静默失败；应从其所在目录启动。
5. **gym-pybullet-drones v2.2.0**：要求 Python ≥ 3.12；观测向量中线速度与角速度的顺序不可混淆（见 §3.2）。
6. **msgpackrpc × tornado 6.5**：见 §4.3 补丁清单。

## 7. 参考文献

1. Panerati et al. *Learning to Fly — a Gym Environment with PyBullet Physics for RL of Multi-agent Quadcopter Control*. IROS 2021. arXiv:2103.02142
2. Romero et al. *Dream to Fly: Model-Based RL for Vision-Based Drone Flight*. 2025. arXiv:2501.14377
3. Shah et al. *AirSim: High-Fidelity Visual and Physical Simulation for Autonomous Vehicles*. FSR 2017
4. Sawant et al. *Colosseum: A Benchmark for Evaluating Generalization for Reinforcement Learning*. 2023. arXiv:2310.09371
5. gym-pybullet-drones: https://github.com/learnsyslab/gym-pybullet-drones
6. Cosys-AirSim: https://github.com/Cosys-Lab/Cosys-AirSim

> 信息核查日期：2026-10-07
