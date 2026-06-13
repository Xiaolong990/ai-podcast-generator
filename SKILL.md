---
name: ai-podcast-generator
description: "Use when creating AI-generated debate podcast episodes. Generates multi-character debate scripts, reviews compliance/quality, produces TTS audio with distinct voices, and assembles synchronized video with pure-black subtitles for DaVinci Resolve editing."
version: 1.1.0
author: Duren
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [podcast, tts, ai-generation, video, chinese]
    related_skills: []
---

# AI 播客生成器

一键生成 AI 多角色辩论播客：脚本 → 审查 → 音频 → 视频

## Overview

本 skill 提供完整的 AI 播客生成工作流，支持：

- **多角色辩论脚本生成**：用 LLM 自动生成辩论对话
- **合规+质量双审查**：自动检查敏感内容和内容质量
- **多角色语音合成**：每个角色有独特的音色和风格
- **视频自动合成**：字幕精确同步，支持角色切换动画

## When to Use

- 制作 AI 生成的辩论类播客
- 批量生产多角色对话音频
- 需要自动审查脚本合规性
- 需要生成带字幕的视频

**不适用于：** 非辩论类内容、需要真人录音的场景

## 前置要求

### API Keys

| Key | 用途 | 必需 |
|-----|------|------|
| `XIAOMI_API_KEY` | MiMo LLM + TTS | ✅ |

在 `~/.hermes/.env` 中配置：
```
XIAOMI_API_KEY=your_key_here
```

### Python 依赖

```bash
pip install Pillow imageio-ffmpeg
```

### ffmpeg

脚本使用 `imageio-ffmpeg` 自带的 ffmpeg，无需单独安装。

## 快速开始

### 生成一期播客

```bash
cd ~/Projects/AI播客
python3 scripts/podcast_workflow.py \
  --topic "辩题" \
  --char-a "正方人物" \
  --char-b "反方人物"
```

### 示例

```bash
# 生成 EP03：诸葛亮 vs 刘伯温
python3 scripts/podcast_workflow.py \
  --topic "AI时代还需要谋士吗？" \
  --char-a "诸葛亮" \
  --char-b "刘伯温" \
  --ep-num 3
```

## 工作流详解

### 10步自动化流程（含飞书审核）

```
📝 生成脚本 → 🔍 合规审查 → ⭐ 质量审查 → 📤 飞书审核 → ⏸️ 等待审核
                                                           ↓
                                           你回复"同意"后继续 ↓
                                                           ↓
                              🎨 图像 → 🎙️ 音频 → 🎬 视频 → 📊 验证 → 📋 Obsidian → 📜 LRC
```

| 步骤 | 工具 | 说明 |
|------|------|------|
| 1. 生成脚本 | MiMo-V2.5-Pro | LLM 生成辩论对话 JSON |
| 2. 合规审查 | MiMo-V2.5-Pro | 检查政治敏感、法律风险 |
| 3. 质量审查 | MiMo-V2.5-Pro | 评估创新性、深度性等 |
| **4. 飞书审核** | send_message | **发送给你审核，等待回复** |
| 5. 生成图像 | Pillow | 角色头像占位图 |
| 6. 生成音频 | MiMo-V2.5-TTS | 多角色语音合成 |
| 7. 合成视频 | ffmpeg | 纯黑背景+字幕 |
| 8. 验证同步 | ffmpeg | 检查段落数+时长 |
| 9. Obsidian | 保存笔记 | 脚本+审查结果 |
| 10. LRC字幕 | 生成 | 双语时间轴字幕 |

### 输出文件

```
~/Projects/输出/AI神仙打架/EP{XX}_{人物A}vs{人物B}/
├── script.json           ← 辩论脚本
├── audio.wav             ← 完整音频
├── video_v6.mp4          ← 带字幕视频
├── images/               ← 角色图像
├── segments/             ← 分段音频
├── image_prompts.md      ← 配图提示词
├── episode_description.md ← 节目简介
└── EP{XX}_*.lrc          ← 双语字幕
```

## 角色语音设计

在 `scripts/voice_profiles.json` 中配置角色语音：

```json
{
  "角色名": {
    "voice_design": "语音描述（用于 voicedesign 模型）",
    "description": "角色简介"
  }
}
```

### 预置角色

| 角色 | 风格 |
|------|------|
| 主播 | 温暖亲切的播音员 |
| 牛顿 | 严谨理性的古典学究 |
| 爱因斯坦 | 充满好奇的温和教授 |
| 孔子 | 古朴威严的老者 |
| 苏格拉底 | 质疑反讽的哲人 |

## 视频生成说明

### v6 版本（推荐）

- **布局**：全屏背景 + 底部字幕
- **同步**：基于每段音频真实时长
- **字幕**：SRT 格式，ffmpeg 渲染
- **效果**：字幕精确同步，无空白内容

### 自定义

修改 `video_v6.py` 中的参数：

```python
# 字幕样式
FONT_SIZE = 32          # 字幕字号
SUB_MARGIN = 40         # 字幕底部边距
MAX_CHARS_PER_LINE = 30 # 每行最大字数

# 视频参数
FPS = 1                 # 帧率
```

## 选题库管理

在 Obsidian 笔记库中维护选题：

```markdown
# 选题库

| 编号 | 辩题 | 正方 | 反方 | 类型 | 状态 |
|------|------|------|------|------|------|
| EP03 | AI时代还需要谋士吗？ | 诸葛亮 | 刘伯温 | 轻松趣味 | 📋 规划中 |
```

## 内容红线

- ❌ 不涉及政治敏感话题
- ❌ 不冒犯真实人物
- ❌ 不传播未经证实的信息
- ✅ 所有观点基于事实和合理推演
- ✅ 标注"AI生成，仅供娱乐"

## 同步验证（重要）

视频生成后自动执行验证：

```
📊 段落检查：脚本=25段 | 音频=25段    ← 必须相等
📊 时长检查：音频=744.6s | 视频=744.6s | 差异=0.00s  ← 差异必须<1秒
```

**常见问题原因：**
- 旧的音频片段混入（segments目录未清理）
- 脚本重新生成但音频未重新生成
- 拼接时静音间隔计算错误

**解决方案：**
- 生成前清理 segments 目录
- 脚本变更后必须重新生成音频
- 使用 v6 版本（读取真实WAV时长）

## 常见问题

### Q: 音频生成超时

A: MiMo TTS API 响应较慢，每段约 5-10 秒。完整一期（20段）约需 3-5 分钟。

### Q: 字幕不同步

A: 使用 v6 版本（`video_v6.py`），它基于每段音频真实时长生成 SRT，精确同步。

### Q: 如何添加新角色

A: 在 `voice_profiles.json` 中添加角色描述，脚本会自动使用。

### Q: 视频太长有空白

A: 确保使用 `-shortest` 和 `-t` 参数限制视频时长为音频时长。

## 常见陷阱

1. **中文字体问题**：macOS 的 `PingFang.ttc` 无法正常渲染中文。必须使用 `/System/Library/Fonts/STHeiti Medium.ttc`（粗体）或 `STHeiti Light.ttc`（细体）。

2. **XIAOMI_API_KEY 引号问题**：`.env` 文件中的 key 值包含特殊字符，直接用 `startswith("XIAOMI_API_KEY=")` 会因引号嵌套导致 SyntaxError。正确写法：`if s.split("=")[0] == "XIAOMI_API_KEY" and not s.startswith("#"):`

3. **旧音频片段导致字幕不同步**：重新生成脚本后，必须先清理 `segments/` 目录中的旧 WAV 文件，否则新旧片段混合会导致字幕时间戳计算错误。

4. **视频时长超出音频**：ffmpeg 默认取最长流。必须同时使用 `-shortest` 和 `-t {audio_duration}` 来精确限制视频时长。

5. **字幕滚动不同步**：不要用字符数估算每段时长。必须用 `ffprobe` 读取每段 WAV 的真实时长来生成 SRT 时间戳。

6. **用户偏好简洁布局**：全屏背景+底部字幕的简单布局效果最好。分屏布局（头像+字幕分区）和 AI 生成图片效果不佳，用户不喜欢。

7. **视频背景必须纯黑**：用户使用达芬奇剪辑，需要从视频中抠出字幕层。背景必须是纯黑 RGB(0,0,0)，不能有渐变或装饰线，否则 Delta Keyer 无法干净抠出字幕。

8. **飞书推送用 send_message**：不要用 webhook URL。Hermes 已集成飞书，直接用 `send_message(action='send', target='feishu:oc_69021b60724dc0467d0bf6172c7abce6', message=...)` 推送脚本审核通知。

9. **工作流步骤缩进错误**：`podcast_workflow.py` 中步骤 7-10 必须在 `main()` 函数内部，不能在 `if audio_path and video_path:` 条件内部。如果缩进错误，这些步骤不会执行。修改后用 `py_compile` 验证语法。

10. **批量生成时逐个执行**：不要在后台脚本中用 `&` 并行执行多个 `podcast_workflow.py`，会导致进程冲突和文件混乱。应该顺序执行，每个完成后开始下一个。

## 封面生成

MiMo 没有图像生成模型。封面需手动制作：

### Stable Diffusion 提示词模板

**孔子 vs 苏格拉底：**
```
Cartoon illustration, two philosophers debating.
Left: Chinese Confucius in red-gold robes, wise expression.
Right: Greek Socrates in white toga, questioning expression.
Center: glowing "VS" text.
Background: dark blue, yin-yang left, Greek columns right.
Style: colorful cartoon, clean lines, flat design.
Bottom text: "东方哲学 vs 西方哲学".
Square 1024x1024.
```

**牛顿 vs 爱因斯坦：**
```
Cartoon illustration, two scientists debating.
Left: Newton in 17th century black coat, holding apple.
Right: Einstein with wild white hair, casual sweater.
Center: glowing "VS" text.
Background: dark blue, gravity waves left, atoms right.
Style: colorful cartoon, clean lines, flat design.
Bottom text: "物理学的终极理论".
Square 1024x1024.
```

封面保存为 `cover.png`（1280x1280 或 1024x1024），上传到播客平台。

## 发布到播客平台

### 小宇宙（推荐首选）

1. 打开 https://creator.xiaoyuzhou.com.cn
2. 创建播客：名称「AI神仙打架」，分类「科技/知识」
3. 上传音频（audio.wav）+ 封面（cover.png）
4. 填写标题和简介

### 喜马拉雅

1. 打开 https://www.ximalaya.com/creator
2. 创建专辑：名称「AI神仙打架」
3. 上传音频 + 封面

### B站（视频版）

1. 打开 https://member.bilibili.com/platform/upload/video/frame
2. 上传视频（video_v6.mp4）
3. 分区：知识 > 科学科普
4. 标签：AI辩论、播客、哲学

### 推荐标题格式

```
【AI神仙打架】正方vs反方：辩题？
```

### 推荐简介模板

```
当[正方]遇上[反方]，两位[领域]巨匠将就"[辩题]"展开激烈辩论。
本节目由AI生成，所有观点仅供娱乐和思考。
```

## 定时任务

已配置 cron job 每天早上 9 点自动生成：

```
Job ID: c26527f650d2
Schedule: 0 9 * * * (每天 9:00)
流程: 生成脚本+审查 → 发飞书审核 → 等待用户批准
```

管理命令：
```bash
hermes cron list           # 查看任务
hermes cron pause ID       # 暂停
hermes cron resume ID      # 恢复
hermes cron run ID         # 手动触发
```

## 文件结构

```
~/.hermes/skills/media/ai-podcast-generator/
├── SKILL.md                  ← 本文件
├── scripts/
│   ├── podcast_workflow.py   ← 主工作流脚本
│   └── voice_profiles.json   ← 角色语音配置
└── references/
    └── video_v6.py           ← 视频生成脚本
```

## 验证清单

- [ ] `XIAOMI_API_KEY` 已配置
- [ ] Python 依赖已安装（Pillow, imageio-ffmpeg）
- [ ] `~/Projects/AI播客/scripts/` 目录存在
- [ ] `~/Projects/输出/AI神仙打架/` 目录存在
- [ ] 测试生成一期播客，检查音频和视频

## 版本历史

- **v1.3.0** (2026-06-14): 添加飞书审核步骤（步骤4）；修复工作流缩进bug；添加定时任务配置
- **v1.2.0** (2026-06-14): 视频背景改为纯黑（达芬奇抠字幕）；飞书推送用 send_message
- **v1.1.0** (2026-06-14): 添加常见陷阱（字体、引号、旧文件、时长限制）；修复 video_v6.py 和 podcast_workflow.py 的 API key 读取
- **v1.0.0** (2026-06-14): 初始版本，支持完整工作流
