# 现有演奏工具与音频转谱调研

> 后续补充：这是用户提供具体工具前的初轮检索记录。用户之后提供 DIEtype/Guitarplayer-For-NTE 及寻枫椛的视频；前者已有四页 24 和弦及混合演奏的作者说明，但当前 main 只见 README 和旧源码 ZIP，没有确认最新源码及许可证。详见 `user-specified-tools.md`。下文“未找到”仅指本次初轮搜索覆盖，不代表现有工具均不支持和弦翻页。用户也已明确普通歌曲为主要输入，现有工具的 MIDI 门槛就是不满意原因。

检索日期：2026-10-21。范围：4 个直接支持 NTE 的开源演奏项目、Spotify Basic Pitch；另附一个明确提到吉他的闭源作者页面。不安装、不运行软件、不操作游戏，全部为公开资料核查。

## 结论先行

1. **MIDI → 游戏按键已有可核查实现，不必从零证明技术路径。** Windows 优先评估 AutoMidiPlayer，参考其音轨选择、试听、移调和失焦停播；PlayFlowMIDI 可参考较小的通用配置结构。两者不能仅凭“支持 NTE”就认定支持明音凛吉他。[A][B]
2. **21 键/36 键钢琴不等于吉他/钢琴两种乐器。** AutoMidiPlayer、macOS 项目明确宣称 21 自然音/36 半音钢琴；本轮没有找到明确以明音凛吉他为目标并公开映射源码的项目。作者网站“爱光遇弹琴”明确宣称另有吉他 36 键、每排从 E 起，但它不是游戏官方机制说明，仍需实际校验。[A][C][F]
3. **当前项目映射存在时间与音高差异，不能照抄一个表。** Noki 使用 MIDI 36–71；AutoMidiPlayer 最新 v7.14.6 将 36 键钢琴配置上移到 60–95，发布说明明确是 NTE 钢琴音高修正。它们是工具配置，不是已经测量确认的当前游戏实际音域。[A2][A3][D2][D3]
4. **MP3/WAV → MIDI 与 MIDI → 按键应分开评价。** Basic Pitch 能转多音音符及弯音，官方同时明确“单一乐器效果最好”；不能据此承诺整首流行歌曲可一键还原主旋律、伴奏、鼓组及音色。[E]

证据标记：**源码核查**指读到了实现或配置；**作者说明**指 README/发布页自述；**分析建议**不是实测结论。所有项目的本地兼容性、听感、输入准确率、延迟和游戏内成功率均未实测。

## 1. AutoMidiPlayer — Windows 首选评估对象

- 仓库：[Jed556/AutoMidiPlayer][A]；发布：[v7.14.6][A3]，API 回读发布日期 2026-10-19。
- **输入／选择：作者说明**支持 `.mid`、实时 MIDI 输入设备、并行多轨、运行时开关音轨；未见直接把 MP3/WAV 转谱的功能说明。[A]
- **模式：源码核查** `Piano21k` 为 21 个自然音，MIDI 36–71 中的白键；`Piano36k` 为连续 60–95，均命名 Piano。没有在所核查 NTE 配置中看到 Guitar；不能把其 36 键宣传改写成吉他支持。[A2]
- **适配：作者说明**每曲保存 key offset、transpose、speed、BPM；可试听、保持和合并临近音、切换键盘布局；开始时切游戏，离开目标窗口停止。[A]
- **依赖差异：源码核查**README 仍写 .NET 8 SDK 以上，但当前 `csproj` 已是 `net10.0-windows10.0.22621.0`，主要依赖包括 DryWetMidi 8.0.3、WPF-UI、Stylet、SkiaSharp。评估当前源码应按 .NET 10，而不是机械照搬 README 的 .NET 8；发布包是否自带运行时未核查。[A4]
- **复用：**GPL-3.0；源自 sabihoshi/GenshinLyreMidiPlayer 后独立发展。适合作为已有多游戏演奏交互和实现参照，复制/派生代码需满足 GPL，不能当作任意闭源代码素材。[A]
- **边界：**v7.14.6 修音高说明映射会随版本改变；作者也提示不具音乐理论背景及封禁风险不确定。未核查所有调度分支，不承诺完整 MIDI 表情或原音符无损输出。[A][A3]

## 2. PlayFlowMIDI — 较小的通用 Windows 参照

- 仓库：[tigurand/PlayFlowMIDI][B]；发布：[v1.1.1.0][B4]，API 回读日期 2026-06-21，说明为 15 键转调提示更新，不是新增吉他支持证据。
- **输入／适配：作者说明**MIDI 文件/文件夹播放列表、实时速度/移调、分轨开关、越界 Wrap/Clamp、全局快捷键、自定义游戏配置。后台输入仅作者声称且注明并非所有游戏可用。[B]
- **NTE 模式：源码核查**默认 profile 为 `Neverness to Everness`、目标 `HTGame.exe`、36 键。界面对 NTE 隐藏 15/37 键，只显示 36 键；没有看到 NTE 21 键或吉他专属配置。默认行键为 QWERTYU、ASDFGHJ、ZXCVBNM 加 Shift/Ctrl。[B2，约 91–95、1481–1490、2273–2277 行]
- **重要限制：源码核查**NTE 的 note-on 走单次点击队列；note-off 对 NTE 直接返回。因此通用 `HoldNotes` 选项不能作为“NTE 延音正确”的证明。Wrap/Clamp 在实现中都涉及按八度移动，并非根据名字假定 Clamp 会夹到最近边界音。[B2，约 864–886、920–923、995–996 行]
- **依赖／复用：源码核查**WPF，`net10.0-windows`，DryWetMidi 8.0.3；README 要求 Windows 10/11、.NET 10 Runtime。MIT，复用约束相对宽松。[B][B3]
- **未核查：**变速曲线及复杂 tempo map 实际播放准确性、跨修饰键和弦冲突、长时间调度误差。不能以 README 的“高精度”当测量数据。[B]

## 3. NTE Piano MIDI Player — macOS 编曲/安全释放参考

- 仓库：[Kusanalee/NTE-Piano-MIDI-Player][C]；发布：[v1.1.0][C2]，API 回读日期 2026-08-22。
- **输入：作者说明**Standard MIDI `.mid`/`.midi`，音轨启用、静音、独奏、扬声器试听、无输入 Preview Mode；无 MP3/WAV 转谱宣称。[C]
- **模式：作者说明**21 键自然音、36 键半音钢琴，均为三排七个物理位置与修饰键；并未声明明音凛吉他专属布局。[C]
- **编曲：作者说明**Automatic 处理 tempo/sustain、略去 GM 第 10 通道打击乐、邻近 onset 和弦分组、有限范围转调/八度折叠、减音。跨层慢和弦可滚奏，太快则略掉不兼容音而非替换成错半音。其“每个 onset 最多 6 音”是本项目输入预算，不能升级为游戏官方复音上限。[C]
- **运行：作者说明**macOS 26+，Swift/SwiftUI；21 键需辅助功能权限；36 键需 Karabiner VirtualHID package 8.2.0/driver 1.8.0 或兼容安装及本地提权桥接。Windows 用户不能直接使用。GPL-3.0。[C]
- **安全释放：作者说明**暂停/失焦/取消/结束/断连/异常释放按键。未运行确认。[C]
- **验证证据须区分：**v1.0 发布说明称 62 项自动化测试通过、1 项可选测试跳过；v1.1 声明 UI 更新没有重新进行游戏实测。以上是作者报告，不是本轮测试结果。[C2]

## 4. Noki-NTE-Auto — 直接相关但非专用播放器

- 仓库：[nokiruy/Noki-NTE-Auto][D]；最新发布列表回读为 v1.8.68（2026-09-30）。综合脚本还包含战斗/钓鱼/宏等功能，不建议为单纯演奏需求引入整个自动化功能集。[D][D4]
- **输入／音轨：源码核查** `异环钢琴main.py` 使用 `mido.MidiFile(..., clip=True)`；逐轨收集 note-on/off，从所有轨收集 `set_tempo`；有音轨选择、速度倍率、JSON 中间演奏数据路径。[D2]
- **适配：说明与源码均可见**加减 key、水平/垂直反转、整体移调/八度折叠、最大覆盖窗口等多种压缩；映射范围 36–71，字母键配合左 Shift/Ctrl。并非 MP3 音频识别。[D2][D3]
- **两种乐器：未证实**文件和界面围绕钢琴 36 音映射，没有核实到 21 自然音模式或明音凛吉他独立映射。不能把“映射反转”当作切换乐器。[D2][D3]
- **运行依赖：源码可见但非完整清单**Python、mido、pydirectinput、win32gui、tkinter 及仓库内部的按键/窗口模块，明显依赖 Windows；无干净环境构建验证。[D2]
- **文档瑕疵：**说明 4.3 的示例把 72 写成“≤71”，且部分结果仍超出自称范围；因此该文档对效果的解释不能原样作为正确性依据。这里只确认算法意图，不评价听感优劣。[D3]
- **许可：**本轮没确认明确许可证；公开源码不自动等于允许复制、改编和分发，先作阅读参考。[D]

## 5. Spotify Basic Pitch — 音频转 MIDI，不是全曲自动编配器

- 官方仓库：[spotify/basic-pitch][E]；发布：[v0.4.0][E2]（2024-08-16，新增训练代码）；Apache-2.0。
- **官方能力：**音频自动转谱（AMT），跨乐器、多音符识别、pitch bend；输出 MIDI，也可保存音符 CSV、原始 NPZ 和 MIDI 合成试听 WAV。支持 librosa 可解码的 MP3/WAV/OGG/FLAC/M4A 等，不等于承诺任意机器均具相同音频解码后端。[E]
- **输入处理：**立体声先混为单声道，重采样到 22050 Hz。它不是利用左右声道保留不同乐器的多轨提取器。[E]
- **明确限制：**官方写明“works best on one instrument at a time”。多音能力是同时多个音高，不是自动区分主唱/钢琴/鼓/吉他并输出各自可用分轨的保证。[E；后半句为根据接口与定位作出的分析]
- **运行条件：**README 列 Python 3.7–3.11，Windows/macOS/Ubuntu；模型含 TensorFlow/CoreML/TFLite/ONNX。默认依赖按平台和 Python 版本选择，Windows 通常 ONNX；Python ≥3.11 的 TensorFlow 依赖例外需注意。不能直接承诺用户当前 Python 版本可装。[E]
- **可调项：**最小/最大频率等需针对素材选择；官方 README 未提供本任务游戏场景质量数据。不得声称“准确率 X%”“某分钟歌曲 Y 秒处理”或 GPU 必需，本轮没有这些测量。[E]
- **完整歌曲的建议流程（分析建议，未验证）：**优先获得用户认可的 MIDI；否则先取得授权的音频，必要时单独做源分离/主旋律提取，再转谱、试听清理音符、选择声部、限制音域/密度、适配目标乐器。Basic Pitch 不替代后面的编配和游戏输入校验。
- **成本边界：**可作为本地开源组件，不要求按次购买云转谱 API；仍有机器计算、打包、依赖维护和人工修谱成本。这里不提供未经实测的硬件门槛或货币报价。[E；成本为分析]

## 附：唯一明确检索到吉他布局的作者页面（非开源证据）

[爱光遇弹琴《异环》页面][F]自述 Android 无 Root，通过无障碍和悬浮窗匹配触摸位置；支持普通 21 键/吉他 36 键、MIDI 与 Sky Studio TXT 导入、自动转调。它称吉他每排从 E 起，比常规 36 键低 8 半音。**这些均为工具作者宣称，未得到游戏官方文档或源码佐证，也未实测。**其“不是外挂”“防检测”等措辞不构成官方许可或安全保证，本轮不采用也不研究规避检测方式。该页面不能证明 Windows 版能力、现有开源项目的吉他支持或所有用户均可免费使用。

## 搜索覆盖与仍未知

- TinyFish CLI 可用，本轮使用轻量 `search query`、批量 `fetch content get`；GitHub API/Raw 用标准库 HTTP 补充读发布记录、树与指定源码；没有安装、下载软件包或使用浏览器重型代理。
- 关键词覆盖“异环 自动演奏 github”“异环 吉他 自动演奏 github 明音凛 早雾”“Neverness to Everness guitar piano midi github auto player”“github NTE Sakiri guitar MIDI autoplay 明音”。Sakiri/早雾/明音凛没有因关键词同时出现就被认定为同一角色。
- 没找到明确以明音凛吉他为目标、公开 MIDI 映射并说明当前兼容版本的开源项目；这不等于证明互联网上绝对不存在。
- 游戏版本/平台、吉他与钢琴实际音高、修饰键切层、同时发音数、延音和游戏输入间隔仍需独立确认。工具 README 只能作为候选线索。
- **推荐下一步：**Windows 优先拿 AutoMidiPlayer 作“已有方案是否足够”的参照，不立即开始新产品；乐器映射先逐音确认，输入链先用少轨 MIDI 校验。若主要输入是成品歌曲，另设转谱试听与修谱验收，不能沿用“导入 MIDI 即可播放”的完成标准。
- **最影响方向的问题：**主要想导入 MIDI 乐谱，还是 MP3/WAV 完整歌曲？这决定播放器适配与音频转谱哪一个才是核心工作。

## 来源与源码快照

以下为直接读取的一手页面；main 分支可能继续变动，源码结论对应本次 API 返回的 SHA。

[A]: https://github.com/Jed556/AutoMidiPlayer （README）
[A2]: https://github.com/Jed556/AutoMidiPlayer/blob/7e1a43f3f00c165697b9e0d70b0a85c78a09761d/AutoMidiPlayer.WPF/Core/Games/NTE/Instruments/Piano.cs
[A3]: https://github.com/Jed556/AutoMidiPlayer/releases/tag/v7.14.6
[A4]: https://github.com/Jed556/AutoMidiPlayer/blob/7e1a43f3f00c165697b9e0d70b0a85c78a09761d/AutoMidiPlayer.WPF/AutoMidiPlayer.WPF.csproj
[B]: https://github.com/tigurand/PlayFlowMIDI （README）
[B2]: https://github.com/tigurand/PlayFlowMIDI/blob/85eb4f7066589f2347f2f283690def405ef96387/PlayFlowMIDI/MainWindow.xaml.cs
[B3]: https://github.com/tigurand/PlayFlowMIDI/blob/85eb4f7066589f2347f2f283690def405ef96387/PlayFlowMIDI/PlayFlowMIDI.csproj
[B4]: https://github.com/tigurand/PlayFlowMIDI/releases/tag/v1.1.1.0
[C]: https://github.com/Kusanalee/NTE-Piano-MIDI-Player （README；快照 c0f5578a4fb630b85bec097218c7a93ef4981651）
[C2]: https://github.com/Kusanalee/NTE-Piano-MIDI-Player/releases （v1.0.0、v1.1.0）
[D]: https://github.com/nokiruy/Noki-NTE-Auto （README）
[D2]: https://github.com/nokiruy/Noki-NTE-Auto/blob/f19dc38b4a224cf1d4634020d03ac75df6d20c8f/异环钢琴main.py
[D3]: https://github.com/nokiruy/Noki-NTE-Auto/blob/main/异环钢琴自动演奏工具使用说明书.txt
[D4]: https://github.com/nokiruy/Noki-NTE-Auto/releases
[E]: https://github.com/spotify/basic-pitch （README；快照 fa5997af0a8210982619003269994a1be25eddf3）
[E2]: https://github.com/spotify/basic-pitch/releases/tag/v0.4.0
[F]: https://igytq.cn/games/yihuan/ （第三方工具作者页面，非游戏官方）
