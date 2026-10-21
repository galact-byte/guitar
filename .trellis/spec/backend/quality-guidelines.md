# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

<!--
Document your project's quality standards here.

Questions to answer:
- What patterns are forbidden?
- What linting rules do you enforce?
- What are your testing requirements?
- What code review standards apply?
-->

(To be filled by the team)

---

## Forbidden Patterns

<!-- Patterns that should never be used and why -->

(To be filled by the team)

---

## Required Patterns

<!-- Patterns that must always be used -->

(To be filled by the team)

---

## Testing Requirements

<!-- What level of testing is expected -->

(To be filled by the team)

---

## Code Review Checklist

<!-- What reviewers should check -->

(To be filled by the team)

## Local Audio Research: Musical Continuity Regression

Allowing accompaniment simplification does not authorize strict monophony or shortened source-note tails. The rejected 94-note experiment passed its initial mechanical tests yet introduced discontinuities.

- Compare the complete candidate against the accepted reference: retain original note ends and inspect where voice removal creates new gaps. Keep genuine source rests; do not solve discontinuity by arbitrary note stretching or filling every gap.
- If supporting voices are retained, verify they are original MIDI events with unchanged attack, pitch, end, and velocity. Do not assume polyphony one is a correctness invariant for the final arrangement.
- Independently check note coverage, attack retention, and rendered low-level audio segments. A single held note can cover the entire timeline while multiple source attacks have been deleted; sample decay then creates audible discontinuity. Coverage equality is not proof of audible continuity or correct melody.
- Source spectral onset detection can reveal lost transients but does not label the true melody. Do not automatically insert notes at every detected transient. The rejected 122-note experiment is the concrete counterexample; see the task's `research/attack-loss-diagnosis.md`.
- Required regression fixtures include overlapping source tails, bass bridging a melody gap at its original attack, an unfilled genuine rest, and no invented source events. Decoding and legal MIDI alone are insufficient.

Evidence: `.trellis/tasks/10-21-guitar-player-research/research/melody-continuity-correction.md`.

## 本地音频研究：显式踏板控制

- 试听导出不得静默忽略模型预测的控制事件。当前研究渲染器只支持二值CC64踏板（`value >= 64`）；其他控制或非法时间须明确拒绝，不能悄悄近似处理。
- 当前TinySoundFont调用路径仅发送CC64并未在松键后保持发声。已验证的处理是：踏板按下时延迟松键，分别跟踪实际按住的键与待释放的键；抬踏板只释放后者，不能截断再次按下的同音键。
- 同一采样时刻先处理踏板，再处理松键与新起音。不凭空添加踏板来掩盖识别缺失。保留原MIDI，片段边界裁齐须单独记录。
- 回归覆盖保持/释放、同刻顺序、同音重击、不支持的控制、非法时间，以及旧无踏板基线逐采样一致。这不代表游戏延音兼容或音乐质量通过。

证据：`.trellis/tasks/10-21-guitar-player-research/research/independent-neural-model-probe.md`。

## Local Audio Research: Numeric JSON Boundary

This verified research rule does not fill the pending product-backend guidelines above.

- `pretty_midi` timestamps and derived counts may be NumPy scalar types. Standard `json.dumps` can reject them even after audio export succeeded.
- Normalize note fields to native `float` / `int` immediately after reading MIDI, before arithmetic, comparisons, or report construction. Do not use `default=str`, which silently changes numeric contracts into strings.
- Run `json.dumps(metadata, allow_nan=False)` on normalized input metadata before exporting listening files. Verify final report JSON as part of the complete experiment, not only the WAV decode.

```python
# Wrong: NumPy scalars can propagate into derived counts and metadata.
notes = [{"start": n.start, "pitch": n.pitch} for n in instrument.notes]

# Correct: keep the serialized numeric contract explicit.
notes = [{"start": float(n.start), "pitch": int(n.pitch)} for n in instrument.notes]
json.dumps(notes, allow_nan=False)
```

Evidence: `.trellis/tasks/10-21-guitar-player-research/research/melody-priority-experiment.md`.
Local-only reproduction: `research/audio-sample/run_melody_focus_experiment.py` under that task; its inputs and scripts are intentionally not distributed. The complete check covers WAV decode, numeric report serialization, MIDI reparse, and unchanged source/baseline hashes. A passing decode alone is not an experiment pass.
