# 《潮鸣》45 秒音频转谱实验

> 历史研究报告：下文关于规划期、尚未验收或 planning 边界的描述反映实验当时状态，现已由 `handoff.md` 顶部当前状态覆盖；转谱实验数据与当时验收结论仍作为历史记录保留。

日期：2026-10-21。本轮属于规划期的可行性研究，不是产品实现或游戏兼容性验收。

最新反馈及整体复查见 `whole-chain-review.md`：用户已确认原02和A/B全段都有滴声，前8秒均难辨旋律；不再重复比较阈值候选。本轮已用采样钢琴替代纯正弦试听，并隔离默认残余能量补音机制，仍待听感确认。

## 已得到的产物

- 输入是用户已提供 MP3 的 00:30–01:15 安全衰减片段，45 秒、22050 Hz、单声道；没有使用预制 MIDI。
- 实际运行 Basic Pitch 0.4.0 的 ICASSP 2022 ONNX 模型，输出 450 个音符及 MIDI。
- 本机试听目录：项目根目录下 `试听结果/潮鸣45秒/`，包含原曲、原音域转谱合成、键盘音域示意、左右声道对照和说明。私人派生文件已被 Git 忽略。
- 文件检查通过：4 个 WAV 均可解码，时长均为 45 秒、无非有限样本、无满幅削顶，峰值约 -1 dBFS；2 个 MIDI 均可重新解析且各含 450 个音符。
- 原 MP3 的 SHA-256 和纳秒修改时间在实验前后均一致。
- 尚未作用户听感验收，也没有游戏演奏结果。不将技术输出成功等同于音乐识别准确。

## 环境与复用

- RTX 4060 Laptop，8188 MiB 显存；定向检查既有 conda/uv 环境，发现 `Pycode` 已有 GPU PyTorch 2.7.1+cu128。
- 在该既有环境实测 CUDA 张量求和成功，CUDA 12.8、cuDNN 9.7.1 可用。
- 新建项目 `.venv-transcription`，使用已安装 Python 3.11.15。没有修改全局环境或原有 conda 环境。
- ONNX Runtime GPU 1.24.4，通过 `preload_dlls(directory=...)` 只读复用既有 PyTorch 的 CUDA/cuDNN DLL，不重新安装 CUDA、驱动或 GPU PyTorch。
- 安装依赖 38 包，另加 Basic Pitch；resampy 0.4.2 依赖 `pkg_resources`，从现有全局环境只读复制 setuptools 76.1.0 到隔离环境后运行成功。复制来源与文件清单见私有 `audio-sample/reused-setuptools.json`。
- 没有安装 TensorFlow、CoreML、TFLite 或 Demucs。Basic Pitch 对未安装的可选后端会打印警告，不代表当前 ONNX 运行失败。为避免默认依赖引入 TensorFlow，Basic Pitch wheel 使用 `--no-deps` 安装，其余运行依赖单独解析；`uv pip check` 因 0.4.0 在 Python 3.11 的元数据强制声明 TensorFlow 而报告 **1 项缺失**。这是当前研究环境的已知元数据不满足，不能声称依赖检查全绿；ONNX 运行与产物验证已独立通过。
- 大小边界：Basic Pitch wheel 为 758279 字节，内含 ONNX 模型 230444 字节；依赖下载明显大于模型。安装日志列出的 9 个大包合计约 312.3 MiB，不能当作精确网络流量。逐包 PyPI 元数据核算遇到 TLS EOF，未得到完整下载字节账单；不编造精确总量。其余小包及缓存复用见安装日志，未自动拉取 TensorFlow/CUDA 整套依赖。

## 发布包与主分支差异

之前阅读的上游主分支会优先选择可用 CUDA provider，但 **PyPI 0.4.0 的 `Model.__init__` 写死 `CPUExecutionProvider`**。

本地研究脚本的 `ResearchOnnxModel` 继承官方 `Model`，仅显式创建 ONNX 会话，继续复用其 `predict`、切窗和后处理；没有改动第三方包文件。要求 GPU 时同时检查会话 provider 与实际 profiling 事件，避免将 CPU 回退报为 GPU 成功。

模型 SHA-256：`2c3c1d144bfa61ad236e92e169c13535c880469a12a047d4e73451f2c059a0ec`。

## 参数与时间测量

固定参数：onset 0.5、frame 0.3、最短音长 127.7 ms（11 帧）、melodia_trick=true、无音域限制、不允许重叠音符独立弯音、MIDI tempo 120。tempo 是输出时间表示参数，不代表测得原曲 BPM。

首次 GPU 实验：

| 阶段 | 秒 |
| --- | ---: |
| ONNX 会话初始化 | 0.269 |
| 完整 `run_inference` | 24.659 |
| 其中模型 `session.run` 累计 | 1.056 |
| 音符后处理 | 0.115 |

首次总耗时含音频处理库冷启动/JIT，不应将其与后续 CPU 热缓存结果直接比较；未逐项计时冷启动内部成本，不把差额全部归因于 JIT。

同进程预热音频加载与两个会话后，交替顺序各跑三次，CPU intra-op=4、inter-op=1，两端均启用 profiling：

| 45 秒音频推理 | 第 1 次 | 第 2 次 | 第 3 次 | 中位数 |
| --- | ---: | ---: | ---: | ---: |
| GPU `run_inference` | 0.506 | 0.460 | 0.543 | **0.506 秒** |
| CPU `run_inference` | 0.860 | 0.862 | 0.901 | **0.862 秒** |

该样本热推理 GPU 约快 1.70 倍；这是小模型、单样本的推理测量，不含启动、后处理、合成导出，也不能推广至其他歌曲、源分离模型或全曲处理。

首次 GPU profile 中 6748 个 CUDA 节点事件、140 个 CPU 节点事件，证明确实有 GPU 执行；不宣称所有节点均在 GPU。

### CPU/GPU 数值差异

- 输出张量最大绝对差：note 0.01693、onset 0.03400、contour 0.02550。没有达到绝对差 0.001 的严格等价条件，不声称逐元素一致。
- 首次 CPU/GPU 均得到 450 音、相同逐音高数量分布；434 个音符的音高及起止时间（取 6 位小数）完全一致，16 个事件的时间不同。
- 按音高与时间排序比较，最大起始差约 11.61 ms、结束差约 69.66 ms。不据此声称两者音乐质量等同，也没有人工标注真值来计算准确率。

## 音域与试听边界

- 原始识别音域 MIDI 29–100（F1–E7），最多同时 8 音。
- 对照截图键盘标签推算的 MIDI 52–87，136/450 音（30.2%）超出范围；截图标签尚未经过实际发声校准。
- `03` 试听只把这 136 音按整八度移入 52–87，保留音级。未做主旋律筛选、声部简化、同音合并、吉他和弦识别或分页编排，不能当成最终游戏适配。
- `02` 是全部识别音的合成参考；`04` 左原曲、右 `02`。合成音不是游戏音色。
- 没有默认替用户决定只留旋律或保留伴奏；下一步先听样本，判断主要问题是错音、漏音、声部混杂还是音域折叠，再收敛需求。

## 首次试听反馈与单变量降杂对照

用户反馈：能听出原曲，但中间有“滴滴的乱音”。这不是听感通过，具体错误事件尚未定位。

- 原始450音中，60音短于200ms，35音高于MIDI87，两者交集仅5音；这些仅是统计，不能直接判为误音或据此一刀切删高音。
- 排查假设依次为弱起音误识别、短促误音、合成音色/正确声部的高音突出，均未确认。缺少具体滴声时间及人工音符真值，无法建立自动判定“滴声消失”的测试；因此本轮只生成探索性对照，不宣称找到根因或修复。
- 复用相同GPU模型输出，不重新下载或推理模型；保留原音域与所有声部，不擅自改为仅主旋律。
- 新目录 `试听结果/潮鸣45秒-降杂对照/`：`00_原参数对照.wav`、`A_提高起音门槛.wav`、`B_减少短促音.wav` 和说明。

| 版本 | 唯一改变 | 音符数 | 短于200ms |
| --- | --- | ---: | ---: |
| 00 | 无；重建事件与上一轮完全匹配 | 450 | 60 |
| A | onset 0.5 → 0.6 | 392 | 47 |
| B | 最短音长11 → 17帧（约197ms） | 396 | 1 |

所有候选采用相同正弦合成音色、相同增益、相同时间起点；显式关闭 `pretty_midi.synthesize` 默认的逐文件峰值归一化，再统一缩放，避免音量拉满干扰比较。A可能漏弱音，B可能漏快音，音符变少不等于更准确。

`compare_postprocessing.py` 验证基线事件重建一致、每个候选只改一个参数、3个WAV均完整FFmpeg解码、45秒、无削顶，原MP3和上一轮02文件哈希未变。结果在私有 `audio-sample/postprocessing-comparison.json`，`musical_quality_verified=false`。后续用户反馈：A/B在第8秒才辨认出旋律、前8秒听不懂，不能将这两版作为已改善结果。停止继续调阈值或追加候选。

只读复查文件0–8秒（对应原曲30–38秒）：原参数101音、A83音、B92音，三版首音均约0.023秒。A有56个、B有89个事件的音高与起止时间同原参数完全匹配；数量变化不能证明删掉了主旋律，也不能证明没删。证据为 `audio-sample/first-eight-seconds-analysis.json`，根因仍未确认。下一步只需确认最初02版同一前8秒是否也不清楚，区分原识别不足和过滤退化；本次未修改任何试听音频。

## 复现与证据

以下文件全部位于任务 `research/audio-sample/`，含私有素材或本机路径，不入 Git：

- `run_transcription_experiment.py`、`benchmark_warm.py`、`build_listening_exports.py`：研究脚本。
- `result-gpu/summary.json`、`result-cpu/summary.json`、对应 notes/MIDI/模型输出/profiling。
- `warm-benchmark.json`、`cpu-gpu-note-comparison.json`、`listening-validation.json`、`final-verification.json`。
- 独立复查命令：`.venv-transcription/Scripts/python.exe .trellis/tasks/10-21-guitar-player-research/research/audio-sample/verify_experiment.py`；4个WAV完整FFmpeg解码、声道对照、2个MIDI、原件不变、隐私忽略和planning边界均通过。
- `install.log`、`install-dry-run.log`、`environment-freeze.txt`、`gpu-reuse-inspection.json`。

从项目目录执行：

```bash
.venv-transcription/Scripts/python.exe .trellis/tasks/10-21-guitar-player-research/research/audio-sample/run_transcription_experiment.py --backend gpu
.venv-transcription/Scripts/python.exe .trellis/tasks/10-21-guitar-player-research/research/audio-sample/run_transcription_experiment.py --backend cpu
.venv-transcription/Scripts/python.exe .trellis/tasks/10-21-guitar-player-research/research/audio-sample/benchmark_warm.py
```

试听导出脚本拒绝覆盖已有 WAV，避免重跑覆盖用户可能修改的文件。重新导出应选择新目录，不删除或覆盖既有文件。

一手参考：
- https://github.com/spotify/basic-pitch/tree/v0.4.0
- https://pypi.org/pypi/basic-pitch/0.4.0/json
- https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html （本轮已抓取，支持指定目录预加载 DLL）
