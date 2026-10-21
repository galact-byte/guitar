# combine_ark 输入经验与本工具的复用边界

## 来源与证据等级

用户提供 https://github.com/galact-byte/combine_ark ，并表示此前使用未被封禁。这是用户的历史经验，不证明《异环》允许自动演奏或零账号风险。用户已接受普通前台模拟输入仍有风险；正式工具方案中的鼠标需求须在整体终审中明确披露。

本轮仅从公开仓库读取指定文件，没有运行其注入、点击或提权逻辑。固定仓库树：`22014ba389177b47749a515f2f658d188d9afc95`。

## 已读取的实现

- `ark_pixel_helper/win_input.py:1-201`：标准库ctypes封装Win32 SendInput，实际为**鼠标**而非音乐键盘调度器。含虚拟桌面坐标归一化、F8急停、客户区坐标转换、管理员重启和相对/绝对鼠标双路处理。
- 其中 `SendInputMouse.PAUSE=0.03`，`click()` 内还按固定时长等待。不能将逐格填图的等待直接用作音乐节拍。
- `tests/test_win_input.py:1-42`：覆盖坐标归一化、相对增量与提权防循环，不触发真实输入。
- `tests/test_window_identity.py:17-30`：明确同时匹配窗口句柄和进程ID，并重新读取当前PID防止句柄复用误判。
- `LICENSE:1-31`：当前为 `LicenseRef-Galact-Internal-Use-1.0` 自定义源码可用许可，不是MIT；允许合规个人/内部使用与免费分发，但含通知保留、第三方例外和商业化限制。

仓库README正文和NOTICE未成功取回，未据此推断其内容。没有下载整个仓库或执行项目。

## 推荐复用与不复用

复用的是窄而可验证的经验：原生Win32接口、指针宽度正确的ctypes结构、F8停止习惯、窗口句柄/PID身份校验、纯逻辑与真实输入分离的测试方式。

不直接照搬：

- 另一游戏的相对移动扰动/Raw Input双路逻辑；没有在《异环》验证，不能当作通用兼容技巧。
- 自动管理员提权；本工具默认普通权限，被系统拒绝就停止并提示，不改系统安全设置。
- 固定点击间隔及填图扫描循环；音乐需单调时钟绝对时间调度。
- 只有鼠标的INPUT联合体；新增键盘事件时必须按Win32结构完整定义，验证32/64位布局，不能按字段名称猜结构尺寸。

优先基于官方Win32接口独立实现最小输入模块，参考上述经验而非拷贝整个项目。若实际摘用源码，必须先核对NOTICE/第三方例外并保留适用通知，不将自定义许可证误标为MIT。当前未复制任何参考代码进产品。

## 与现有演奏工具的比较

`research/user-specified-tools.md` 已核查DIEtype工具支持四页和弦，但没有文档化自动导入CLI/API，当前许可和最新源码未确认。直接外接不能保证无缝流程，也不能要求用户手动导出/导入MIDI来充当最终体验。

因此拟在已有音频模型上做一个窄的本地界面、游戏适配与安全调度器，不重建通用MIDI编辑器、复杂曲库、Guitar Pro编辑或多游戏框架。若后续确有可用授权接口，可以替换输入适配器，不影响音频和UI契约。

## 不能遗漏的鼠标边界

用户截图证据表明键盘模式有独立36键；吉他和弦圆盘不同。现有工具文档明确默认使用键盘和鼠标，六弦数字键拨弦，鼠标选择圆盘和上下扫弦（作者说明，非本机验证）。

完整方案不能继续只承诺键盘模拟：键盘模式发送按键；吉他模式拟增加普通前台鼠标选区/扫弦及R/T翻页，全部受窗口身份、失焦、F8停止和释放保护。此增量在最终方案中明确列出，整体批准前不得实现或触发真实输入。无需虚拟手柄、额外驱动、后台消息或内存操作。

## 环境与后续验证

既有 `.venv-piano-probe` 实测Tk8.6.14可启动，探测窗口已关闭。原生字体中“等线”、Microsoft YaHei UI和Cascadia Mono可用，无需为界面下载字体/浏览器框架。

后续仍需用户实际操作游戏确认36键发声、复音/重复触发、四页全部标签、分页方向、选和弦和扫弦动作。单元测试只用假输入设备；不能把其他项目未封禁、作者说明或离线测试当作真实游戏兼容证据。

## 固定文件证据链接

Git tree的SHA不是commit SHA；提交查询遇到403，不猜测提交。以下使用已成功读取并与树对应的文件blob作为固定证据：

- `ark_pixel_helper/win_input.py`：https://api.github.com/repos/galact-byte/combine_ark/git/blobs/1884589993a6006d4814ae1ca0a87a05fdf3aeba
- `tests/test_win_input.py`：https://api.github.com/repos/galact-byte/combine_ark/git/blobs/a7afe87f3ef955257ed7a696f566063419690406
- `tests/test_window_identity.py`：https://api.github.com/repos/galact-byte/combine_ark/git/blobs/aacb9a5675279a6ba1ac65da7f3adc19dfe0a001
- `LICENSE`：https://api.github.com/repos/galact-byte/combine_ark/git/blobs/ec40f27094751841f7cf4a00e97970f3e46f80ff

私有取证文件在任务 `research/audio-sample/combine-ark-source/`，仓库树在 `combine-ark-tree.json`；不将抓取原文或下载中间文件提交。
