# 修改记录 — 异环吉他演奏工具研究

## 2026-10-21 — 普通歌曲转谱调研与暂停交接

### 背景与目标
- 用户希望直接导入普通歌曲自动演奏，不需要寻找 MIDI 或理解乐理。
- 完成公开资料、用户指定两个工具和本地《潮鸣》音频前置检查；保存后暂停，尚未进入产品实现。
- 按用户要求归档初始化 bootstrap 任务，明确记录规范填充未执行、未验收，保留原始待办，不伪装为已完成开发。

### 影响与兼容性
- 无产品代码、接口或数据迁移；未修改原始音频、全局 Python 环境或游戏。
- 已授权在项目隔离环境下载/安装研究组件，但目前尚未执行；GPU 路线待核查与实测。
- 私人截图、音乐、原始抓取数据和本地路径记录不进入 Git。研究文档中的本地证据引用在其他设备上可能不可用。

### 文件与实现
| 操作 | 路径 | 说明 |
|---|---|---|
| 新增 | `.gitignore` | 排除本地 AI 配置、私有素材、抓取数据、依赖与运行环境 |
| 归档 | `.trellis/tasks/archive/2026-10/00-bootstrap-guidelines/` | 用户要求关闭无关初始化任务，元数据明确 requirements_completed=false |
| 新增 | `.trellis/tasks/10-21-guitar-player-research/prd.md` | 需求、授权范围、已知证据与待确认事项 |
| 新增 | `.trellis/tasks/10-21-guitar-player-research/handoff.md` | 暂停状态、GPU 环境事实、资料位置与恢复步骤 |
| 新增 | `.trellis/tasks/10-21-guitar-player-research/research/` 内可公开 Markdown | 现有工具、音频转谱能力、用户指定工具与方案建议；不含私有观察记录和素材目录 |

### 验证
- `ffprobe -show_format -show_streams -of json <本地原音频>`：154.410667 秒、48 kHz、双声道 MP3。
- `ffmpeg -v error -i <本地原音频> -map 0:a:0 -f null -`：退出码 0，错误日志为空。
- 本地 SHA-256 与修改时间复核：原文件未变化；安全候选片段45秒、22050Hz、单声道，峰值约 -1dBFS，无满幅样本。
- `nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv,noheader`：RTX 4060 Laptop，8188MiB 显存。
- 当前解释器检查：PyTorch 2.11.0+cpu；ONNX Runtime 1.24.4 未提供 CUDA 后端。不代表其他环境没有 GPU 支持。
- 未运行转谱、试听质量验收或游戏测试，没有对应成功结论。
- `python ./.trellis/scripts/task.py list`：仅剩 guitar-player-research，状态 planning；bootstrap 已归档，当前任务指针保持不变。

### 已知限制与后续
- 先核查现有 GPU 环境，核算轻量 ONNX 或有证据支持的其他模型依赖，再进行授权范围内的45秒转谱实验。
- GitHub 上的工具和视频说明不等于本地运行验证；最新完整源码、许可、对接接口及普通音频识别效果仍未确认。
- Trellis 任务保持 planning；未经方案评审和后续批准不启动产品实现。
