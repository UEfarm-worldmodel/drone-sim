# gym-pybullet-drones 调研笔记

> 2026-10-07 整理
> 定位：六平台调研中**本项目适配度第一**的模拟器（★★★★★），本周本地部署 + 世界模型数据管线验证的主战场。

## 1. 一句话定位

UTIAS（多伦多大学航空航天研究所）动态系统实验室出品，Panerati 等人发表于 IROS 2021（《Learning to Fly》），MIT 协议开源。**把 PyBullet 物理引擎包装成 Gymnasium 标准接口的无人机研究环境**——给"用 RL / MBRL 研究无人机控制"的论文当实验台。

关键先例：RPG 组 2025 年的 **Dream to Fly**（arXiv:2501.14377）用 DreamerV3 纯像素输入在该环境上训练竞速策略、经硬件在环部署真机（9 m/s）——世界模型探索的完整参考路径（仿真器 → 像素/状态 → 世界模型 → 策略）这一个库里全都有。

## 2. 工作原理

- **物理内核**：PyBullet 刚体引擎。四旋翼用简化转子动力学：每个转子 RPM 带一阶惯性滞后，由推力/扭矩系数算出合力与合力矩；含气阻与碰撞。保真度中等，但机制透明（`assets/` 内有 URDF，公式见论文 III 节）。
- **机型**：默认 Bitcraze Crazyflie 2.x（X / 十字构型），新版有 RACE 竞速机型；支持 HITL 真机在环。
- **动作分层**：
  - 底层 **RPM**（自己写控制，做世界模型用这个）
  - **位置目标**（内置级联 PID 自动换算 RPM，快速实验用）
  - 速度控制模式
- **观测**：默认 20 维状态向量（位置 3 + 四元数 4 + 欧拉角 3 + 角速度 3 + 上一帧 RPM 4）；可开 RGB / 深度 / 分割摄像头，做像素输入。
- **多机**：`Aviary` 类原生支持 N 架同飞；`downwash.py` 演示上机气流压制下机的气动效应。
- **RL 生态**：Gymnasium 标准 API + stable-baselines3 2.0 兼容，`learn.py` 一条命令训 PPO 悬停。

## 3. 自带示例（按上手顺序）

| 示例 | 看什么 |
|---|---|
| `pid.py` | 经典控制：位置目标 → 内置 PID → RPM |
| `learn.py` | RL 主线：PPO 训悬停（单机/双机），`play.py` 回放 |
| `downwash.py` | 多机气动耦合（与"无人机群"场景相关） |
| `mrac.py` / `pid_velocity.py` | 进阶控制参考 |
| `beta.py` | Betaflight SITL 真固件在环（**仅 Ubuntu**，Windows 跳过） |

## 4. 优缺点

**优点**：pip 即装、笔记本能跑；核心代码极小（`Aviary` + 几个控制类），读得动改得动；Gymnasium/SB3 标准 API，新算法即插即用；多机 + 下洗 + HITL 齐全；世界模型研究文献先例（Dream to Fly）就在本环境。

**缺点**：渲染朴素（做不了比赛演示）；物理保真中等（无复杂风场/柔性效应，可自行扩展）；官方主要测试 Ubuntu 24.04 / macOS，Windows 可跑但 Betaflight SITL 仅 Ubuntu。

## 5. 与世界模型探索的对接

- 本环境是**数据契约的最小验证场**：`Aviary.step()` 返回 `(obs, reward, terminated, truncated, info)`。UE 农场要设计的 (状态, 动作, 下一状态) 三元组落盘格式，先在这里定义、验证，UE 端将来照抄。
- 探索两级：
  1. 在 20 维状态上训**下一帧状态预测器**；
  2. 上像素观测跑 **DreamerV3**（社区 PyTorch 复现 dreamerv3-torch），复现 Dream to Fly 最小版本。
- 这条线跑通后，UE 农场数据接入 = 换数据源。

## 6. 本地环境（本机已装好）

- conda 环境：`drones`（Python 3.12；conda 在 `C:\Users\rui\miniconda3`，**未加入 PATH**，用 Anaconda Prompt 或全路径 `C:\Users\rui\miniconda3\Scripts\conda.exe` 调用）
- 仿真工作区：**`E:\drone-sim\`**（纯英文路径，原因见下；多平台整体布局见 `E:\drone-sim\README.md`）
  - 本平台目录：`E:\drone-sim\platforms\gym-pybullet-drones\`（仓库 + demo 脚本）
  - 数据产物统一：`E:\drone-sim\data\gym-pybullet-drones\`；本笔记：`E:\drone-sim\notes\`
  - **这个文件夹不能再挪动**：pybullet 的 C++ 层读不了中文路径，挪回中文目录 URDF 立刻加载失败（已踩过一次）。
  - 项目文件夹里的 `drone-sim.lnk` 是指向它的快捷方式（E 盘不是 NTFS，建不了目录联接，只能用 .lnk）。
  - `gym-pybullet-drones/` —— learnsyslab 主仓库 v2.2.0（要求 Python ≥3.12），editable 安装进 `drones` 环境
  - `demo_record_trajectory.py` —— (s,a,s') 录制脚本
  - `demo输出/trajectory.csv、trajectory.npz、tracking.png` —— demo 产物
- 依赖已装：pybullet 3.2.7（源码编译，本机 VS2022 Community 提供的 MSVC）、gymnasium 1.4.0、stable-baselines3 2.9.0

### 跑 demo

```bash
conda activate drones
cd E:\drone-sim\platforms\gym-pybullet-drones

# ① GUI 经典控制（3 架无人机 PID 跟踪圆轨迹）
python gym-pybullet-drones/gym_pybullet_drones/examples/pid.py

# ② GUI PPO 训练（RL 主线，训练完用 play.py 回放）
python gym-pybullet-drones/gym_pybullet_drones/examples/learn.py

# ③ (s,a,s') 轨迹录制（世界模型数据契约草案 v0）
python demo_record_trajectory.py            # 无 GUI，秒出结果
python demo_record_trajectory.py --gui      # 打开 3D 窗口实时观看（6 秒后自动关闭并落盘）

# 产物统一落在 E:\drone-sim\data\gym-pybullet-drones\
```

> GUI 说明：`pid.py`、`learn.py` 默认就是 GUI（3 架机 / PPO 训练过程）；`demo_record_trajectory.py` 加 `--gui` 按 48Hz 实时播放。想看久一点改脚本里的 `DURATION`。

### 踩坑记录（团队都该知道）

1. **pybullet 不认中文路径**：`loadURDF` 的 C++ 层读不了含中文/空格的目录，报 "URDF not found" 但文件明明在——仿真工程一律放纯英文路径（UE 工程同理）。
2. **Windows 上 pybullet 无预编译包**：必须装 VS2022 的 C++ 工作负载后由 pip 源码编译（一次性 10--20 分钟）。
3. **Clash 代理会挂死 pip**：进程 CPU 为零地卡住 = 网络被代理挂住，pip 加 `-i https://pypi.tuna.tsinghua.edu.cn/simple` 走直连镜像。
4. **v2.2.0 的 API 与旧版不同**：`computeControl()` 返回三元组 `(rpm, pos_err, yaw_err)`；20 维观测顺序为 `[位置0:3, 四元数3:7, 欧拉角7:10, 线速度10:13, 角速度13:16, 上帧动作16:20]`——把线速度当角速度喂给 PID 会直接炸机。
5. 位置跟踪 RMSE ≈ 16 cm 的残差是**纯位置 PID 无速度前馈的固有跟随误差**（目标切向速度越快滞后越多），不是 bug；改进实验素材：给 `computeControl` 传 `target_vel`。

验收标准：录出自己的 `(s,a,s')` 轨迹 CSV + 一张位置跟踪图 + 一张 PPO 回放截图。

## 7. 文献锚点

1. Panerati et al., *Learning to Fly — a Gym Environment with PyBullet Physics for RL of Multi-agent Quadcopter Control*, IROS 2021. arXiv:2103.02142
2. Romero et al., *Dream to Fly: Model-Based RL for Vision-Based Drone Flight*, 2025. arXiv:2501.14377
3. 仓库：https://github.com/learnsyslab/gym-pybullet-drones （MIT）

> 信息核查日期：2026-10-07

## 8. WHEELTEC F570 实机 → 仿真参数对接（重要）

实机资料：WHEELTEC F570 随机资料包 V1.1（本地路径从略，含使用手册/开发手册/STM32 源码/油门-推力拟合脚本）。

对仿真选型与参数化的直接影响：

1. **飞控是自研 STM32F405 固件（PID 版 + LQR 版两套源码），不是 PX4 / Betaflight**
   ⇒ PX4 SITL / Pegasus / Gazebo-PX4 那条 sim-to-real 链对**这台机不适用**；要 HITL 得按它的串口协议自写桥（CH9102 USB 转串口）。
2. **附实测油门-推力数据表**（`2.开发手册/飞行器油门拟合文件.../F570_throttle_fitting.py`）：
   油门 48--1148（步长 50）× 电压 10/10.5/11/11.5/12/12.5V（3S 锂电），推力以克计，12.5V 满油门约 319g。
   ⇒ 可拟合出仿真用的**推力系数**，替换 gym-pybullet-drones 默认 Crazyflie（27g 级）的参数，做 F570 机型条目（URDF 质量 + thrust/torque 系数）。
3. MATLAB 参考模型：`3.WHEELTEC F570 四轴飞行器程序源码/2.MATLAB程序/Quadcopter.m` + `LQR.slx`（动力学公式对照）。
4. 传感器：STP-23L 激光测距 + WHEELTEC 光流模块（观测模型要考虑）。
5. 遥控为 PS2 手柄，默认定高 + 有头模式，低电量自动降落。

下一步（单独任务）：从源码与手册提取整机质量 / 轴距 / 电机 KV / 桨尺寸，结合推力表做一个 `DroneModel.F570` 机型配置，先在 gym-pybullet-drones 里复现 F570 的悬停油门点，再迁移到 UE 农场。
