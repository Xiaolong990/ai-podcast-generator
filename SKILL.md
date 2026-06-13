---
name: ai-podcast-generator
description: "Use when creating AI-generated debate podcast episodes. Generates multi-character debate scripts, reviews compliance/quality, produces TTS audio with distinct voices, and assembles synchronized video with subtitles."
version: 1.0.0
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

### 6步自动化流程

```
📝 生成脚本 → 🔍 合规审查 → ⭐ 质量审查 → 🎨 生成图像 → 🎙️ 生成音频 → 🎬 合成视频
```

| 步骤 | 工具 | 说明 |
|------|------|------|
| 1. 生成脚本 | MiMo-V2.5-Pro | LLM 生成辩论对话 JSON |
| 2. 合规审查 | MiMo-V2.5-Pro | 检查政治敏感、法律风险 |
| 3. 质量审查 | MiMo-V2.5-Pro | 评估创新性、深度性等 |
| 4. 生成图像 | Pillow | 角色头像占位图 |
| 5. 生成音频 | MiMo-V2.5-TTS | 多角色语音合成 |
| 6. 合成视频 | ffmpeg | 图像+字幕+音频 |

### 输出文件

```
~/Projects/输出/AI神仙打架/EP{XX}_{人物A}vs{人物B}/
├── script.json           ← 辩论脚本
├── audio.wav             ← 完整音频
├── video_v6.mp4          ← 带字幕视频
├── images/               ← 角色图像
└── segments/             ← 分段音频
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

## 常见问题

### Q: 音频生成超时

A: MiMo TTS API 响应较慢，每段约 5-10 秒。完整一期（20段）约需 3-5 分钟。

### Q: 字幕不同步

A: 使用 v6 版本（`video_v6.py`），它基于每段音频真实时长生成 SRT，精确同步。

### Q: 如何添加新角色

A: 在 `voice_profiles.json` 中添加角色描述，脚本会自动使用。

### Q: 视频太长有空白

A: 确保使用 `-shortest` 和 `-t` 参数限制视频时长为音频时长。

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

- **v1.0.0** (2026-06-14): 初始版本，支持完整工作流
