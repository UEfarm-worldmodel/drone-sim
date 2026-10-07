# Cosys-AirSim（AirSim / Colosseum 系）调研笔记

> 2026-10-07 整理
> 六平台调研中"UE 接口范本"一档（适配 ★★★★）。**已部署跑通**：连接、起飞、移动、取图、降落全链路 ✔，键盘飞行脚本可用。

## 1. 血统与现状（调研结论更新）

- **AirSim**（微软，2017-2022）：UE 原生无人机仿真的开山之作，2022-07 被微软归档。
- **Colosseum**（MSR → CodexLabsLLC）：AirSim 的官方后继 + RL 泛化基准（14 任务 × 20 扰动，Sawant et al. 2023, arXiv:2310.09371）。**注意：2026-07 也已归档**（GitHub API 核实，Releases 无预编译包）。
- **Cosys-AirSim**（Cosys-Lab / 安特卫普大学）：AirSim 系当前**真正活跃**的续作（2026-10-05 仍有提交），UE 5.8 构建，预编译环境 + pip 客户端齐全，MIT 协议。
- 结论：调研幻灯片里"Colosseum（AirSim 系）"这条线，实际部署对象就是 Cosys-AirSim；引用基准论文时仍称 Colosseum benchmark。

## 2. 原理

- **架构**：UE 插件（C++/Python API 注入 UE 场景）+ **msgpack-RPC 服务器**（默认端口 41451）。Python 客户端发 RPC 指令（起飞/移动/取图/读传感器），仿真端返回状态。
- **飞控**：内置 **SimpleFlight**（轻量级联控制器，无需外部固件即可飞）；也支持 PX4/ArduPilot HIL 接入。
- **坐标系**：NED（x 北、y 东、z 下，高度为负值）。
- **API 面**：多机、多相机（RGB/深度/分割/红外/法线）、IMU/GPS/磁力计/激光雷达/光流，`simGetImage` 直接拿图——**这就是"UE 场景 + 无人机 API"的接口范本**。
- **环境**：Blocks（官方测试场景，预编译 exe 免装 UE）可直接跑；自建环境 = UE 里放插件（农场工程的路径）。

## 3. 优缺点

**优点**：UE 画面与场景自由度；API 面（多相机/传感器）是六平台最全的 UE 方案；预编译环境免装 UE 秒开；客户端 pip 即装；多机支持好。
**缺点**：单实例无并行（训练侧硬伤）；上游六年三次换手（AirSim→Colosseum→Cosys），生态碎片化；Python 客户端依赖的 msgpackrpc 年久失修（本机已打 tornado 6.5 兼容补丁，见 §5）；插件二进制严格绑定 UE 版本。

## 4. 本机部署记录

- 预编译环境：`platforms\cosys-airsim\env\Windows\Blocks.exe`（0.56GB 下载解压，**独立运行不需要装 UE**）
- conda 环境：`cosys-airsim`（py3.12），客户端 `cosysairsim-3.5.0` wheel + numpy/opencv/msgpack-rpc-python
- 自检脚本：`scripts\smoke_test.py`（连接→起飞→移动→状态→取图→降落 全通过，2026-10-07）
- 诊断脚本：`scripts\diag_rpc.py`（RPC 不通时用它定位）

### tornado 6.5 兼容补丁（重要，重装环境后要重打）

客户端依赖的 `msgpackrpc` 停更于 2018 年，与本机 tornado 6.5 / msgpack 1.x 冲突，共打 5 处补丁（位置 `miniconda3\envs\cosys-airsim\Lib\site-packages\msgpackrpc\`）：
1. `address.py`：`tornado.platform.auto` 导入 → try/except 兜底
2. `loop.py`：`PeriodicCallback` 去掉第三参 io_loop
3. `transport/tcp.py`：`IOStream` 构造去掉 io_loop kwarg
4. `transport/tcp.py`：`connect/write` 的 callback 风格 → Future.add_done_callback
5. `transport/tcp.py`：`read_until_close(streaming_callback)` → `read_bytes(partial=True)` + Future 回调读泵

## 5. 使用

```bash
conda activate cosys-airsim
cd E:\drone-sim\platforms\cosys-airsim\scripts

# ① 启动模拟器（或直接双击 env\Windows\Blocks.exe）
start ..\env\Windows\Blocks.exe
# ② 自检（起飞/移动/取图/降落）
python smoke_test.py
# ③ WASDQE 键盘飞行（W/S 前后 A/D 左右 空格/Shift 升降 Q/E 偏航 Esc 降落退出；松开全部键 = 原地悬停）
python keyboard_flight.py
```

**一键版**：双击 `platforms\cosys-airsim\一键键盘飞行.bat`——自动开 Blocks（没开才开）→ 等端口就绪 → 直接进入键盘飞行，全程免命令。

> 键盘说明：按键用 `GetAsyncKeyState` **全局捕获**——焦点在 Blocks 窗口上也能飞，看着画面开；代价是切到别的窗口打字也会被当成飞行输入，**飞完记得 Esc 退出**。已实测：全局按 W 2.5 s，无人机前进 1.3 m。
> HUD 提示解读：`API call was not received, entering hover mode` = SimpleFlight 安全看门狗（1 秒没收到指令自动悬停，比如脚本被 Ctrl+C 后）；`materials.csv not found` 只影响分割图 API，RGB/深度/控制不受影响，无害。

另：Blocks 窗口内按 **F10** 可切换内置键盘手动模式（方向键控机，键位随版本略有差异）。

> 坑：UE 打包 exe 必须以其所在目录为**工作目录**启动。从别的目录用 `Start-Process` 不带 `-WorkingDirectory` 会**静默失败**（进程都没有）；资源管理器双击天然没问题。

## 6. 与本项目对接

1. **UE 农场接口范本**：RPC API 面（状态/控制/多相机/传感器 + NED 契约）就是本组 UE 农场 API 设计的参考蓝本；`smoke_test.py` 的调用序列可直接翻译成 UE C++/蓝图接口清单。
2. **数据集**：`simGetImage` 多相机多模态，可批量生成带位姿标注的模拟农田图像。
3. **F570 对接**：实机为自研 STM32 飞控（非 PX4），Cosys 里用 **SimpleFlight** 对照飞；以后要贴实机动力学，改用 §8（gpb 笔记）里的 F570 推力表重新参数化。
4. **UE 5.7 版本问题**：本机 UE 为 5.7.4（D 盘），Cosys 最新插件只发到 UE 5.8。自建农场环境时二选一：用 VS2022 从源码编译插件（支持 5.7），或 D 盘加装 UE 5.8（引擎可共存）。

## 7. 文献锚点

1. Shah et al., *AirSim: High-Fidelity Visual and Physical Simulation for Autonomous Vehicles* (FSR 2017)
2. Sawant et al., *Colosseum: A Benchmark for Evaluating Generalization for RL* (2023, arXiv:2310.09371)
3. Cosys-AirSim: https://github.com/Cosys-Lab/Cosys-AirSim （MIT；docs: cosysairsim.readthedocs.io）

> 信息核查日期：2026-10-07
