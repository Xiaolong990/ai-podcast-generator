#!/usr/bin/env python3
"""
AI神仙打架 - 播客生成工作流 v3（完整10步）
"""
import json, os, sys, base64, struct, urllib.request, urllib.error, time, argparse, subprocess
from pathlib import Path
from datetime import datetime

# ============================================================
# 配置
# ============================================================
SCRIPTS_DIR = Path(os.path.expanduser("~/Projects/AI播客/scripts"))
OUTPUT_BASE = Path(os.path.expanduser("~/Projects/输出/AI神仙打架"))
OBSIDIAN_BASE = Path(os.path.expanduser("~/Projects/AI探索库/01-AI播客"))
VOICE_PROFILES_PATH = SCRIPTS_DIR / "voice_profiles.json"
MIMO_API = "https://api.xiaomimimo.com/v1/chat/completions"
TTS_MODEL = "mimo-v2.5-tts-voicedesign"
LLM_MODEL = "mimo-v2.5-pro"
FFMPEG = "ffmpeg"

def get_api_key():
    with open(os.path.expanduser("~/.hermes/.env")) as f:
        for line in f:
            s = line.strip()
            if s.split("=")[0] == "XIAOMI_API_KEY" and not s.startswith("#"):
                return s.split("=", 1)[1].strip()
    raise RuntimeError("XIAOMI_API_KEY not found")

def call_llm(prompt, system="", timeout=240):
    api_key = get_api_key()
    messages = []
    if system: messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": LLM_MODEL, "messages": messages, "stream": False}
    req = urllib.request.Request(MIMO_API, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "api-key": api_key}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode())
    if "error" in result: raise RuntimeError(result["error"].get("message", "LLM error"))
    return result["choices"][0]["message"]["content"]

def parse_json(text):
    clean = text.strip()
    if clean.startswith("```"): clean = clean.split("\n", 1)[1]
    if clean.endswith("```"): clean = clean.rsplit("```", 1)[0]
    return json.loads(clean.strip())

# ============================================================
# Step 1: 生成脚本
# ============================================================
def generate_script(topic, char_a, char_b, style="混合"):
    print(f"\n📝 [1/10] 生成脚本：{char_a} vs {char_b}")
    system = """你是专业播客脚本编剧。输出JSON数组，每个元素含speaker和text。
角色：主播、正方人物、反方人物。
结构：开场→立论(各3分钟)→攻辩(各2分钟)→自由辩论(6-8分钟)→总结(各3分钟)→主播点评。
台词用[停顿 X秒]标记停顿。不涉及政治敏感。15-25分钟。直接输出JSON。"""
    prompt = f"辩题：{topic}\n正方：{char_a}\n反方：{char_b}\n风格：{style}\n\n输出完整JSON脚本。"
    result = call_llm(prompt, system, timeout=240)
    script = parse_json(result)
    print(f"   ✅ {len(script)} 段对话")
    return script

# ============================================================
# Step 2 & 3: 审查
# ============================================================
def compliance_review(script, topic):
    print(f"\n🔍 [2/10] 合规审查")
    system = """合规审查专家。检查政治敏感、法律风险、平台规则、虚假信息、伦理问题。
输出JSON：{"passed":bool, "risk_level":"low/medium/high", "issues":[], "summary":""}"""
    prompt = f"辩题：{topic}\n脚本：{json.dumps(script, ensure_ascii=False)}"
    result = call_llm(prompt, system, timeout=120)
    review = parse_json(result)
    print(f"   {'✅ 通过' if review.get('passed') else '⚠️ 有问题'} | {review.get('risk_level','?')}")
    return review

def quality_review(script, topic):
    print(f"\n⭐ [3/10] 质量审查")
    system = """质量评审。评估创新性、深度性、吸引力、可信度、节奏感(每项1-10分)。
输出JSON：{"scores":{"innovation":N,"depth":N,"appeal":N,"credibility":N,"rhythm":N}, "total_score":N}"""
    prompt = f"辩题：{topic}\n脚本：{json.dumps(script, ensure_ascii=False)}"
    result = call_llm(prompt, system, timeout=120)
    review = parse_json(result)
    print(f"   总分：{review.get('total_score',0)}/10")
    return review

# ============================================================
# Step 4: 飞书审核通知
# ============================================================
def send_to_feishu_for_review(script, ep_num, topic, char_a, char_b, compliance, quality, ep_dir):
    print(f"\n📤 [4/10] 飞书审核通知")
    scores = quality.get("scores", {})
    compliance_status = "✅ 通过" if compliance.get("passed") else "⚠️ 有问题"
    quality_score = quality.get("total_score", 0)
    
    # 构建预览
    preview_lines = []
    for seg in script[:5]:
        text = seg["text"][:50] + "..." if len(seg["text"]) > 50 else seg["text"]
        preview_lines.append(f"**{seg['speaker']}**：{text}")
    preview = "\n".join(preview_lines)
    
    # 保存审核请求到文件
    review_request = {
        "ep_num": ep_num,
        "topic": topic,
        "char_a": char_a,
        "char_b": char_b,
        "segments": len(script),
        "compliance": compliance_status,
        "compliance_risk": compliance.get("risk_level", "?"),
        "quality_score": quality_score,
        "scores": scores,
        "preview": preview,
        "ep_dir": str(ep_dir),
    }
    
    review_path = ep_dir / "review_request.json"
    with open(review_path, "w", encoding="utf-8") as f:
        json.dump(review_request, f, ensure_ascii=False, indent=2)
    
    print(f"   ✅ 审核请求已保存：{review_path}")
    print(f"   📋 内容：EP{ep_num:02d} | {char_a} vs {char_b}")
    print(f"   🔍 合规：{compliance_status} | ⭐ 质量：{quality_score}/10")
    
    # 返回消息内容（供外部调用飞书发送）
    msg = f"""🎙️ **AI神仙打架 EP{ep_num:02d} - 待审核**

**辩题**：{topic}
**正方**：{char_a}
**反方**：{char_b}
**段落数**：{len(script)} 段

**合规审查**：{compliance_status}（{compliance.get("risk_level", "?")}风险）
**质量评分**：{quality_score}/10
- 创新性：{scores.get("innovation", "?")} | 深度性：{scores.get("depth", "?")}
- 吸引力：{scores.get("appeal", "?")} | 可信度：{scores.get("credibility", "?")}

---
**脚本预览**：
{preview}

... 共 {len(script)} 段

---
请回复：**同意** 生成音频视频 / **修改意见**"""
    
    return msg

# ============================================================
# Step 5: 生成图像
# ============================================================
def generate_images(script, ep_dir, char_a, char_b):
    print(f"\n🎨 [4/10] 生成图像")
    from PIL import Image, ImageDraw, ImageFont
    images_dir = ep_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    FONT = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 64)
    FONT_S = ImageFont.truetype("/System/Library/Fonts/STHeiti Light.ttc", 28)
    SW, SH = 1280, 720
    
    chars = {char_a: (100,180,100), char_b: (200,150,80), "主播": (80,140,255)}
    for name, color in chars.items():
        p = images_dir / f"{name}.png"
        if p.exists() and p.stat().st_size > 1000: continue
        img = Image.new("RGB", (SW, SH), (20, 25, 35))
        draw = ImageDraw.Draw(img)
        for i in range(SH):
            draw.line([(0,i),(SW,i)], fill=(int(20+i/SH*25), int(25+i/SH*15), int(35+i/SH*35)))
        draw.rectangle([(0,0),(SW,8)], fill=color)
        draw.rectangle([(0,SH-8),(SW,SH)], fill=color)
        bbox = draw.textbbox((0,0), name, font=FONT)
        tw = bbox[2]-bbox[0]
        draw.text(((SW-tw)//2+2, 302), name, fill=(0,0,0), font=FONT)
        draw.text(((SW-tw)//2, 300), name, fill=(255,255,255), font=FONT)
        img.save(p)
        print(f"   {name}: ✅")
    
    scene_images = []
    for i in range(len(script)):
        sp = script[i]["speaker"]
        fp = images_dir / f"scene_{i+1:03d}.png"
        src = images_dir / f"{sp}.png"
        if src.exists():
            Image.open(src).save(fp)
        scene_images.append(str(fp))
    print(f"   共 {len(scene_images)} 张场景图")
    return scene_images

# ============================================================
# Step 5: 生成音频
# ============================================================
def generate_audio(script, ep_dir):
    print(f"\n🎙️ [5/10] 生成音频")
    with open(VOICE_PROFILES_PATH) as f: profiles = json.load(f)
    seg_dir = ep_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    api_key = get_api_key()
    wavs = []
    for i, seg in enumerate(script):
        sp, txt = seg["speaker"], seg["text"]
        fp = seg_dir / f"{i+1:03d}_{sp}.wav"
        print(f"   [{i+1}/{len(script)}] {sp}")
        if fp.exists() and fp.stat().st_size > 1000:
            print(f"      ⏭️"); wavs.append(str(fp)); continue
        vd = profiles.get(sp, {}).get("voice_design", "一位播音员，声音温和专业")
        payload = {"model": TTS_MODEL, "messages": [{"role": "user", "content": vd}, {"role": "assistant", "content": txt}], "audio": {"format": "wav"}, "stream": False}
        req = urllib.request.Request(MIMO_API, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "api-key": api_key}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode())
            audio = base64.b64decode(result["choices"][0]["message"]["audio"]["data"])
            with open(fp, "wb") as f: f.write(audio)
            wavs.append(str(fp))
            print(f"      ✅ {len(audio)/1024:.0f}KB")
        except Exception as e:
            print(f"      ❌ {e}")
        time.sleep(0.3)
    
    final = ep_dir / "audio.wav"
    if wavs:
        print(f"\n   🔗 合并 {len(wavs)} 段...")
        _merge_wavs(wavs, str(final))
    return str(final) if wavs else None

def _merge_wavs(wavs, out):
    def read_wav(fp):
        with open(fp, "rb") as f:
            f.read(12)
            while True:
                c, n = f.read(4), struct.unpack("<I", f.read(4))[0]
                if c == b"fmt ": fmt = f.read(n); _, nch, sr, br, ba, bps = struct.unpack("<HHIIHH", fmt[:16]); break
                else: f.read(n)
            while True:
                c, n = f.read(4), struct.unpack("<I", f.read(4))[0]
                if c == b"data": return {"sr": sr, "nch": nch, "bps": bps, "ba": ba}, f.read(n)
                else: f.read(n)
    p, first = read_wav(wavs[0])
    bps_bytes = p["bps"] // 8
    sil = b"\x00" * int(p["sr"] * 0.4 * p["nch"] * bps_bytes)
    pcm = bytearray(first)
    for w in wavs[1:]:
        try:
            _, d = read_wav(w); pcm.extend(sil); pcm.extend(d)
        except: pass
    ds = len(pcm); br = p["sr"] * p["nch"] * bps_bytes
    h = struct.pack("<4sI4s", b"RIFF", 36+ds, b"WAVE")
    h += struct.pack("<4sIHHIIHH", b"fmt ", 16, 1, p["nch"], p["sr"], br, p["ba"], p["bps"])
    h += struct.pack("<4sI", b"data", ds)
    with open(out, "wb") as f: f.write(h); f.write(pcm)
    print(f"   ✅ {ds/br:.1f}秒 ({ds/br/60:.1f}分钟)")

# ============================================================
# Step 6: 合成视频（纯黑背景 + SRT字幕）
# ============================================================
def generate_video(script, scene_images, audio_path, ep_dir):
    print(f"\n🎬 [6/10] 合成视频")
    if not audio_path: print("   ❌ 无音频"); return None
    temp = ep_dir / "_temp"
    temp.mkdir(exist_ok=True)
    out = ep_dir / "video_v6.mp4"
    
    def ffprobe_dur(fp):
        r = subprocess.run([FFMPEG, "-i", fp, "-f", "null", "-"], capture_output=True, text=True)
        for l in r.stderr.split("\n"):
            if "Duration" in l:
                p = l.split("Duration:")[1].split(",")[0].strip()
                h, m, s = p.split(":")
                return float(h)*3600 + float(m)*60 + float(s)
        return 0
    def fmt_srt(s):
        return f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d},{int((s%1)*1000):03d}"
    
    # 拼接音频
    wavs = sorted((ep_dir/"segments").glob("*.wav"))
    with open(temp/"list.txt", "w") as f:
        for w in wavs: f.write(f"file '{w}'\n")
    concat = temp/"full.wav"
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(temp/"list.txt"), "-c", "copy", str(concat)], capture_output=True)
    audio_dur = ffprobe_dur(str(concat))
    print(f"   音频：{audio_dur:.1f}秒")
    
    # 每段时长
    seg_durs = [ffprobe_dur(str(w)) for w in wavs]
    
    # 生成SRT
    srt = temp/"sub.srt"
    lines, idx, cur = [], 1, 0.0
    for seg, dur in zip(script, seg_durs):
        text = f"【{seg['speaker']}】{seg['text']}"
        chunks, rem = [], text
        while rem:
            if len(rem) <= 30: chunks.append(rem); break
            cut = 30
            while cut > 0 and rem[cut-1] not in "。，！？、；：": cut -= 1
            if cut == 0: cut = 30
            chunks.append(rem[:cut]); rem = rem[cut:]
        cd = dur / len(chunks)
        for c in chunks:
            lines.append(f"{idx}\n{fmt_srt(cur)} --> {fmt_srt(cur+cd)}\n{c}\n")
            idx += 1; cur += cd
    with open(srt, "w") as f: f.write("\n".join(lines))
    
    # 纯黑背景
    from PIL import Image
    bg = Image.new("RGB", (1280, 720), (0, 0, 0))
    bg.save(temp/"bg.png")
    
    # 合成
    srt_esc = str(srt).replace("\\", "/").replace(":", "\\:")
    cmd = [FFMPEG, "-y", "-loop", "1", "-i", str(temp/"bg.png"), "-i", str(concat),
           "-vf", f"subtitles='{srt_esc}':force_style='FontName=STHeiti Medium,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,MarginV=50'",
           "-c:v", "libx264", "-preset", "medium", "-c:a", "aac", "-b:a", "192k",
           "-pix_fmt", "yuv420p", "-t", f"{audio_dur:.3f}", "-shortest", str(out)]
    subprocess.run(cmd, capture_output=True)
    
    shutil.rmtree(temp, ignore_errors=True)
    if out.exists() and out.stat().st_size > 1000:
        final_dur = ffprobe_dur(str(out))
        print(f"   ✅ {final_dur:.1f}秒 | {out.stat().st_size/1024/1024:.1f}MB")
        return str(out)
    return None

# ============================================================
# Step 6.5: 验证同步
# ============================================================
def verify_sync(script, audio_path, video_path):
    print(f"\n📊 [6.5/10] 验证同步")
    script_count = len(script)
    wav_count = len(list(Path(audio_path).parent.glob("*.wav")))
    print(f"   段落：脚本={script_count}段 | 音频={wav_count}段")
    if script_count != wav_count: print(f"   ⚠️ 不匹配！")
    else: print(f"   ✅ 匹配")
    
    def dur(fp):
        r = subprocess.run([FFMPEG, "-i", fp, "-f", "null", "-"], capture_output=True, text=True)
        for l in r.stderr.split("\n"):
            if "Duration" in l:
                p = l.split("Duration:")[1].split(",")[0].strip()
                h, m, s = p.split(":")
                return float(h)*3600 + float(m)*60 + float(s)
        return 0
    a_dur = dur(audio_path)
    v_dur = dur(video_path)
    diff = abs(a_dur - v_dur)
    print(f"   时长：音频={a_dur:.1f}s | 视频={v_dur:.1f}s | 差异={diff:.2f}s")
    if diff > 1.0: print(f"   ⚠️ 差异>1秒")
    else: print(f"   ✅ 同步正常")

# ============================================================
# Step 7: 保存到 Obsidian
# ============================================================
def save_to_obsidian(script, ep_num, topic, char_a, char_b, compliance, quality):
    print(f"\n📋 [7/10] 保存到 Obsidian")
    scores = quality.get("scores", {})
    script_text = "\n".join(f"**{s['speaker']}**：{s['text']}\n" for s in script)
    md = f"""# EP{ep_num:02d} - {char_a} vs {char_b}

> {topic}

---

## 基本信息

| 项目 | 内容 |
|------|------|
| 正方 | {char_a} |
| 反方 | {char_b} |
| 段落数 | {len(script)} 段 |

---

## 审查结果

| 审查 | 结果 |
|------|------|
| 合规 | {"✅" if compliance.get("passed") else "⚠️"} {compliance.get("risk_level","?")} |
| 质量 | {quality.get("total_score",0)}/10 |

---

## 脚本全文

{script_text}

---

## 标签

#播客 #EP{ep_num:02d} #{char_a} #{char_b}
"""
    filepath = OBSIDIAN_BASE / f"EP{ep_num:02d}-{char_a}vs{char_b}.md"
    with open(filepath, "w", encoding="utf-8") as f: f.write(md)
    print(f"   ✅ {filepath}")

# ============================================================
# Step 8: 配图提示词（给豆包/SD用）
# ============================================================
def generate_image_prompts(script, char_a, char_b, topic):
    print(f"\n🎨 [8/10] 生成配图提示词")
    
    prompts = f"""# {char_a} vs {char_b} 配图提示词

适用于：豆包AI绘画 / Stable Diffusion / Midjourney

## 1. 播客封面图（必须）

卡通插画风格的播客封面，正方形构图。
画面中央是一个巨大的发光VS字母，金色描边，带有光效。
左侧：{char_a}的卡通形象，穿着传统服饰，面带智慧的表情。
右侧：{char_b}的卡通形象，穿着对应时代服饰，面带思索的表情。
背景：深蓝色星空渐变，融合东西方文化元素。
底部有一条金色横幅，上面写：{topic}
顶部标签：AI神仙打架
整体风格：扁平化设计，色彩鲜艳，线条清晰，1024x1024。

## 2. 立论环节配图

卡通插画风格，画面分为左右两部分。
左边：{char_a}的场景，暖色调，角色站在讲台前陈述观点。
右边：{char_b}的场景，冷色调，角色站在书桌旁反驳。
中间用一道光束分隔两个场景。
顶部标题：立论环节
整体风格：扁平化卡通，色彩对比鲜明，16:9构图。

## 3. 自由辩论高潮配图

卡通插画风格，两位辩手站在圆形辩论台上激烈交锋。
{char_a}在左边，手势激昂，身后浮现相关符号。
{char_b}在右边，手指向上辩论，身后浮现相关图案。
辩论台下方有光效散发，背景是深蓝色星空。
顶部标题：自由辩论
整体风格：扁平化卡通，充满张力和动感，16:9构图。

## 4. 总结配图

卡通插画风格，两位辩手站在一起，握手言和。
背景融合了双方的文化元素，形成和谐的画面。
中间有一个发光的符号，代表辩论的主题。
底部标题：思想的碰撞
整体风格：扁平化卡通，温暖和谐的色调，16:9构图。

## 5. 社交媒体分享图（横版）

宽幅海报风格，16:9构图。
左侧：{char_a}的卡通形象，半身像。
右侧：{char_b}的卡通形象，半身像。
中间大字：{topic}
底部标签：AI神仙打架 跨时空辩论
背景：渐变深蓝色，带有科技感光效。
整体风格：现代海报设计，色彩鲜明，适合社交媒体分享。

## 使用建议

小宇宙封面：3000x3000，用封面图
喜马拉雅封面：3000x3000，用封面图
B站封面：1146x717，用社交媒体分享图
小红书：1080x1440，用封面图
"""
    return prompts

# ============================================================
# Step 9: 节目简介
# ============================================================
def generate_episode_desc(ep_num, topic, char_a, char_b, script):
    print(f"\n📝 [9/10] 生成节目简介")
    key_points = []
    for s in script:
        if s["speaker"] != "主播" and len(s["text"]) > 80:
            key_points.append(f"- {s['speaker']}：{s['text'][:60]}...")
            if len(key_points) >= 5:
                break
    
    desc = f"""# EP{ep_num:02d} 节目简介

## 标题

【AI神仙打架】{topic}：{char_a}vs{char_b}

## 完整版

AI神仙打架 第{ep_num}期

辩题：{topic}

当{char_a}遇上{char_b}，两位跨越时空的巨匠将就"{topic}"展开激烈辩论。

{chr(10).join(key_points)}

收听平台：小宇宙 | 喜马拉雅 | B站

本节目由AI生成，所有观点仅供娱乐和思考。

## 一句话简介

{char_a} vs {char_b}：{topic}。AI让两位穿越时空的巨匠正面交锋
"""
    return desc

# ============================================================
# Step 10: LRC 字幕
# ============================================================
def generate_lrc(script, ep_dir, ep_name):
    print(f"\n📜 [10/10] 生成 LRC 字幕")
    seg_dir = ep_dir / "segments"
    def get_dur(fp):
        with open(fp, "rb") as f:
            f.read(12)
            while True:
                c, n = f.read(4), struct.unpack("<I", f.read(4))[0]
                if c == b"fmt ": fmt = f.read(n); _, _, sr, br = struct.unpack("<HHII", fmt[:12]); break
                else: f.read(n)
            while True:
                c, n = f.read(4), struct.unpack("<I", f.read(4))[0]
                if c == b"data": return n / br if br > 0 else 0
                else: f.read(n)
        return 0
    def fmt(s):
        return f"{int(s//60):02d}:{s%60:05.2f}"
    
    lrc = [f"[ti:{ep_name}]", "[ar:AI神仙打架]", "[al:AI神仙打架]", ""]
    cur = 0.0
    for i, seg in enumerate(script):
        sp, text = seg["speaker"], seg["text"]
        for m in ["[停顿", "停顿", "秒]", "秒。"]: text = text.replace(m, "")
        wav = seg_dir / f"{i+1:03d}_{sp}.wav"
        dur = get_dur(str(wav)) if wav.exists() else 3.0
        sents, rem = [], text.strip()
        for sep in ["。", "！", "？"]:
            if sep in rem:
                parts = rem.split(sep)
                sents = [p.strip()+sep for j, p in enumerate(parts) if p.strip()]
                break
        if not sents: sents = [rem]
        cd = dur / len(sents)
        for j, s in enumerate(sents):
            lrc.append(f"[{fmt(cur+j*cd)}] {s}")
        cur += dur
    lrc_path = ep_dir / f"{ep_name}.lrc"
    with open(lrc_path, "w", encoding="utf-8") as f: f.write("\n".join(lrc))
    print(f"   ✅ {lrc_path}")
    return str(lrc_path)

# ============================================================
# 主函数
# ============================================================
import shutil

def main():
    parser = argparse.ArgumentParser(description="AI神仙打架 v3")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--char-a", required=True)
    parser.add_argument("--char-b", required=True)
    parser.add_argument("--style", default="混合")
    parser.add_argument("--ep-num", type=int, default=None)
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--skip-video", action="store_true")
    args = parser.parse_args()
    
    if args.ep_num is None:
        existing = list(OUTPUT_BASE.glob("EP*_*/"))
        nums = []
        for d in existing:
            try: nums.append(int(d.name.split("_")[0].replace("EP", "")))
            except: pass
        args.ep_num = max(nums, default=0) + 1
    
    safe_a = args.char_a.replace(" ", "")
    safe_b = args.char_b.replace(" ", "")
    ep_name = f"EP{args.ep_num:02d}_{safe_a}vs{safe_b}"
    ep_dir = OUTPUT_BASE / ep_name
    ep_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 50)
    print(f"🎙️ AI神仙打架 v3")
    print(f"   EP{args.ep_num:02d} | {args.char_a} vs {args.char_b}")
    print(f"   {args.topic}")
    print("=" * 50)
    
    # 1. 生成脚本
    script = generate_script(args.topic, args.char_a, args.char_b, args.style)
    
    # 2. 合规审查
    compliance = compliance_review(script, args.topic)
    
    # 3. 质量审查
    quality = quality_review(script, args.topic)
    
    # 保存脚本
    with open(ep_dir / "script.json", "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    
    # 4. 飞书审核通知
    feishu_msg = send_to_feishu_for_review(script, args.ep_num, args.topic, args.char_a, args.char_b, compliance, quality, ep_dir)
    
    # 保存飞书消息供外部发送
    with open(ep_dir / "feishu_message.txt", "w", encoding="utf-8") as f:
        f.write(feishu_msg)
    print(f"   📤 飞书消息已保存：{ep_dir / 'feishu_message.txt'}")
    
    # 5. 生成图像
    scene_images = generate_images(script, ep_dir, args.char_a, args.char_b)
    
    # 5. 生成音频
    audio_path = None
    if not args.skip_audio:
        audio_path = generate_audio(script, ep_dir)
    
    # 6. 合成视频
    video_path = None
    if not args.skip_video and audio_path:
        video_path = generate_video(script, scene_images, audio_path, ep_dir)
    
    # 6.5 验证同步
    if audio_path and video_path:
        verify_sync(script, audio_path, video_path)
    
    # 7. 保存到 Obsidian
    save_to_obsidian(script, args.ep_num, args.topic, args.char_a, args.char_b, compliance, quality)
    
    # 8. 配图提示词
    prompts = generate_image_prompts(script, args.char_a, args.char_b, args.topic)
    with open(ep_dir / "image_prompts.md", "w", encoding="utf-8") as f: f.write(prompts)
    
    # 9. 节目简介
    desc = generate_episode_desc(args.ep_num, args.topic, args.char_a, args.char_b, script)
    with open(ep_dir / "episode_description.md", "w", encoding="utf-8") as f: f.write(desc)
    
    # 10. LRC 字幕
    generate_lrc(script, ep_dir, ep_name)
    
    # 输出摘要
    print("\n" + "=" * 50)
    print("✅ 完成")
    print(f"   脚本：{ep_dir / 'script.json'}")
    if audio_path: print(f"   音频：{audio_path}")
    if video_path: print(f"   视频：{video_path}")
    print("=" * 50)

if __name__ == "__main__":
    main()
