# AI 播客生成器

一键生成 AI 多角色辩论播客：脚本 → 审查 → 音频 → 视频 → 字幕修复

## 功能

- 📝 自动生成辩论脚本
- 🔍 合规+质量双审查
- 🎙️ 多角色语音合成
- 🎬 字幕精确同步视频
- 🔧 LRC字幕自动修复（移除英文+时间戳同步）

## 快速开始

```bash
pip install Pillow imageio-ffmpeg

# 生成播客
python3 scripts/podcast_workflow.py \
  --topic "辩题" \
  --char-a "正方人物" \
  --char-b "反方人物"

# 修复LRC字幕
python3 scripts/fix_lrc.py
```

## 配置

在 `~/.hermes/.env` 中设置：

```
XIAOMI_API_KEY=your_key_here
```

## 文档

详细使用说明请查看 [SKILL.md](SKILL.md)

## License

MIT
