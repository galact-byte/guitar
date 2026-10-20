# 续接说明：普通歌曲导入与异环吉他自动演奏

更新日期：2026-10-21。用户要求今天暂停，保存状态，并将可公开内容提交推送至 https://github.com/galact-byte/guitar 。

## 当前阶段

- Trellis 任务：`.trellis/tasks/10-21-guitar-player-research`，状态 **planning**。未完成产品方案评审，没有运行 task.py start。
- **未写产品代码，未创建转谱虚拟环境，未安装/下载转谱软件和模型，未运行转谱，未安装或使用 TensorFlow。**
- 用户已明确授权为本次研究下载、安装必要开源依赖及模型，但仅限项目隔离环境；不修改全局环境、不上传歌曲、不操作游戏、不安装驱动或绕过反作弊。该授权不等于批准产品实现。
- 不要将用户询问 GPU/PyTorch 误记为已安装 GPU 环境或已确定框架。不要再次未经测量就宣布 CPU 足够快。
- 用户已确认提交推送范围，并要求先归档无关 bootstrap；现已归档至 `.trellis/tasks/archive/2026-10/00-bootstrap-guidelines/`。归档元数据明确需求未完成，不表示规范已填充。当前仅此调研任务活跃。
- 本地已初始化 Git 的 main 分支，origin 为 https://github.com/galact-byte/guitar.git 。不要再次 git init 或重建远端；提交及推送记录以实际 Git 历史和远端为准。
- 用户要求尽量少用子代理；本次早期已有一次独立资料调研，后续均由主代理完成。继续时默认主代理直接处理。

## 用户真正的需求

用户没有音乐基础，希望直接导入 MP3/WAV 后在明音凛演奏玩法中自动弹奏。现有工具不满意的唯一已确认原因是 **必须自行提供 MIDI**，不是已经报告它们音质差或翻页有问题。

MIDI 可作内部格式，但不得要求用户找谱、读谱、手工改谱，或手工串联两个软件作为最终体验。先验证音频转谱效果，再判断复用现有演奏端还是独立实现；不默认全部重写。

## 游戏界面证据

- 用户的吉他截图为和弦圆盘，当前页 G/Am/Bm/C/D/Em，六弦，有 R/T 上下页。用户特别提醒下一页功能，不能只处理当前六个和弦。
- 钢琴键模式为三排各 12 个连续半音，标签 E3–D♯6；按 C4=MIDI60 换算是 52–87，但实际发声频率未测。
- 复音、按住/松开、最短触发间隔、翻页状态、页切换时间等尚未实测。
- 用户的两张临时截图已复制到本机 `research/local-evidence/`，不上传仓库。完整按键观察在本机 `research/user-screenshot-evidence.md`。

## 用户指定的现有工具

1. https://github.com/DIEtype/Guitarplayer-For-NTE/releases
   - 核查时 latest v0.11.7，作者说明支持四页 24 和弦、翻页、指弹、品格/和弦混合与 Z 切换；未找到 MP3/WAV 输入转谱说明，WAV 试听输出不等于音频导入。
   - 当前 main 仅 README、旧 v0.8.0 源码 ZIP 及哈希；未下载 ZIP，未确认最新源码和许可证，不能当作可直接复制的完整开源项目。
2. https://www.bilibili.com/video/BV1Ptng64Erf/
   - 寻枫椛的 V2.5。沿作者评论跟进 V3：https://www.bilibili.com/video/BV1TLJR6nEnq/ 。
   - 核查元数据、作者评论、V2.5 00:45 和 V3 01:30/05:00 抽样画面，见 MIDI 导入；没有找到成品音频转谱证据，不声称看完所有视频或实测程序。

早期搜索漏掉第一个项目，已明确修正，不要重回“没有支持吉他翻页的现有工具”的错误概括。详细来源在 `research/user-specified-tools.md`。

## 《潮鸣》素材与已做检查

- 用户已提供本地 JiJiDown 下载的 Av829205387/P1 MP3。**无需再次向用户索要路径**；完整原路径保存在本机忽略文件 `research/audio-sample/source.json` 和 `research/audio-sample-inspection.md`。
- 时长 154.410667 秒，48 kHz、双声道、约 128 kbps、2,471,446 字节；全曲 FFmpeg 解码返回 0，无错误日志。
- SHA-256：`6006c9572380f19526d1bcb5bcb38fe6f5a959408e5c8678b5e244815e6a47dc`。复核原文件哈希和修改时间均未变化。
- 候选片段 00:30–01:15，45 秒，是非静音的技术测试候选，尚未确认音乐代表性或主旋律听感。
- 有效派生输入：本机 `research/audio-sample/candidate-30s-75s-normalized.wav`，单声道 22050Hz、PCM16。原解码样本超 0dBFS，已对派生片段作约 -4.19dB 衰减；验证输出峰值 -1.00015dBFS、无满幅样本。
- **不要使用**同目录早期 `candidate-30s-75s-mono22050.wav`：它未衰减，可能削顶。安全版本使用 FFmpeg 解码浮点数据、浮点衰减后由 SoundFile 量化，避免自动滤镜格式转换导致的量化偏差。
- 尚无转换 MIDI、音符识别结果、合成试听和任何游戏演奏结果；不得把现成 MIDI 冒充这份音频的转谱结果。

音频、截图及带临时播放地址的抓取数据只留本机，不推送；换机器需用户自行迁移素材，但同机无需重复索取。

## GPU 与框架：最后停在这里

已验证：
- GPU：**NVIDIA GeForce RTX 4060 Laptop GPU，8188 MiB 显存**，驱动 616.92；检查当时空闲约 6883 MiB，空闲量会变。
- 当前解释器：本机已安装 Python 3.12，具体路径见本机 `research/audio-sample/local-environment.json`。
- 当前环境 PyTorch **2.11.0+cpu**，CUDA build None，`torch.cuda.is_available()` false。
- 当前 ONNX Runtime **1.24.4**，providers 为 AzureExecutionProvider、CPUExecutionProvider，没有 CUDA。
- 存在可复用 Python 3.11（uv 管理）、其他 conda 环境；Basic Pitch/Demucs 包未在已定向检查的环境中发现，**其他环境是否有 GPU PyTorch 尚未核查**。不能说用户机器无 GPU 软件。
- Spotify Basic Pitch 上游 inference.py 模型后端列 TensorFlow/CoreML/TFLite/ONNX，没有原生 PyTorch 接口；ONNX 分支在存在 CUDAExecutionProvider 时会优先 GPU。
- Basic Pitch 0.4.0 PyPI 主 wheel 758,279 字节；这是主包而非总下载量。Py>=3.11 非macOS 的默认依赖会引入 TensorFlow，轻量 ONNX 安装须单独规划依赖。
- 目前 **没有安装任何转谱环境**，用户质疑 CPU 后只检查了 GPU 与源码，没有继续安装。

## 下次按此顺序继续

1. 先读本文件和 prd.md；如新会话没有 active task，按 Trellis 恢复此 planning 任务，不创建重复任务、不切 in_progress。
2. 定向核查已知环境中可复用 GPU PyTorch/CUDA/cuDNN，不全盘扫描，不先大规模下载。用户偏好复用现有安装。
3. 推荐评估 GPU ONNX 路线，说明它是模型后端而不是训练框架；若已有 GPU PyTorch 可供依赖复用则利用它。不为框架偏好无依据地移植模型，也不排除经证据比较后更合适的 PyTorch 转谱模型。
4. 在用户已授权范围内核算隔离环境依赖与下载量，避免自动安装整套 TensorFlow/CUDA。普通实现细节无需再次逐项确认；超出授权范围或风险改变才询问。
5. 实际运行45秒音频转谱，记录后端、模型版本、完整参数、初始化/推理耗时、识别音符数与音域；如对比 CPU/GPU，必须实际执行并报告。
6. 输出原音/转谱合成试听及可解释的音域适配结果。不要将合成参考音色说成游戏原音，主观听感需用户试听，不能虚构自己听过。
7. 有样本证据后收敛用户效果目标、平台和风险接受范围，再写完整设计与实现计划，进行最终规划评审；后续明确批准后才 task.py start/产品实现。

## 规则与资料

官方通用协议与公平运营声明均对第三方自动化有限制，没有找到音乐自动演奏的明确豁免；模拟键鼠不等于零风险。游戏实测由用户操作，代理不驱动游戏。

推荐阅读顺序：本文件 → `prd.md` → `research/user-specified-tools.md` → `research/feasibility-and-recommendation.md` → 按需读取本机 `research/audio-sample/` JSON。长原文、截图、视频证据按需读取后释放，不重新灌入整个上下文。
