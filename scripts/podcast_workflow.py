#!/usr/bin/env python3
"""
AI神仙打架 - 完整工作流 v3
脚本生成 → 审查 → 图像生成 → 音频生成 → 视频合成
"""
import json, os, sys, base64, struct, urllib.request, urllib.error, time, argparse, subprocess, textwrap
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

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

# ffmpeg from imageio
import imageio_ffmpeg
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# ============================================================
# API Key
# ============================================================
def get_api_key():
    with open(os.path.expanduser("~/.hermes/.env")) as f:
        for line in f:
            s = line.strip()
            if s.split("=")[0] == "XIAOMI_API_KEY" and not s.startswith("#"):
                return s.split("=", 1)[1].strip()
    raise RuntimeError("XIAOMI_API_KEY not found")

# ============================================================
# LLM / TTS 调用
# ============================================================
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

def call_tts(text, voice_design, api_key):
    payload = {"model": TTS_MODEL,
        "messages": [{"role": "user", "content": voice_design}, {"role": "assistant", "content": text}],
        "audio": {"format": "wav"}, "stream": False}
    req = urllib.request.Request(MIMO_API, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "api-key": api_key}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read().decode())
    if "error" in result: raise RuntimeError(result["error"].get("message", "TTS error"))
    return base64.b64decode(result["choices"][0]["message"]["audio"]["data"])

# ============================================================
# Step 1: 生成脚本
# ============================================================
def generate_script(topic, char_a, char_b, style="混合"):
    print(f"\n📝 [1/6] 生成脚本：{char_a} vs {char_b}")
    system = """你是专业播客脚本编剧。输出JSON数组，每个元素含speaker和text。
角色：主播、正方人物、反方人物。
结构：开场→立论(各3分钟)→攻辩(各2分钟)→自由辩论(6-8分钟)→总结(各3分钟)→主播点评。
台词用[停顿 X秒]标记停顿。不涉及政治敏感。15-25分钟(3000-4000字)。
直接输出JSON。"""
    prompt = f"辩题：{topic}\n正方：{char_a}\n反方：{char_b}\n风格：{style}\n\n输出完整JSON脚本。"
    result = call_llm(prompt, system)
    script = parse_json(result)
    print(f"   ✅ {len(script)} 段对话")
    return script

# ============================================================
# Step 2 & 3: 审查
# ============================================================
def compliance_review(script, topic):
    print(f"\n🔍 [2/6] 合规审查")
    system = """合规审查专家。检查政治敏感、法律风险、平台规则、虚假信息、伦理问题。
输出JSON：{"passed":bool, "risk_level":"low/medium/high", "issues":[], "summary":""}"""
    prompt = f"辩题：{topic}\n脚本：{json.dumps(script, ensure_ascii=False)}"
    result = call_llm(prompt, system, timeout=120)
    review = parse_json(result)
    print(f"   {'✅ 通过' if review.get('passed') else '⚠️ 有问题'} | {review.get('risk_level','?')}")
    return review

def quality_review(script, topic):
    print(f"\n⭐ [3/6] 质量审查")
    system = """质量评审。评估创新性、深度性、吸引力、可信度、节奏感(每项1-10分)。
输出JSON：{"scores":{"innovation":N,"depth":N,"appeal":N,"credibility":N,"rhythm":N}, "total_score":N, "summary":""}"""
    prompt = f"辩题：{topic}\n脚本：{json.dumps(script, ensure_ascii=False)}"
    result = call_llm(prompt, system, timeout=120)
    review = parse_json(result)
    print(f"   总分：{review.get('total_score',0)}/10")
    return review

# ============================================================
# Step 4: 生成图像
# ============================================================
def generate_images(script, ep_dir, char_a, char_b):
    print(f"\n🎨 [4/6] 生成图像")
    images_dir = ep_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    with open(VOICE_PROFILES_PATH) as f:
        profiles = json.load(f)
    
    # 角色描述映射
    char_descriptions = {
        char_a: profiles.get(char_a, {}).get("voice_design", f"一位{char_a}的肖像，古典风格"),
        char_b: profiles.get(char_b, {}).get("voice_design", f"一位{char_b}的肖像，古典风格"),
        "主播": "一位现代播音员的肖像，专业着装，温暖微笑",
    }
    
    # 为每个角色生成头像
    generated = {}
    for char, desc in char_descriptions.items():
        img_path = images_dir / f"{char}.png"
        if img_path.exists() and img_path.stat().st_size > 1000:
            print(f"   {char}: ⏭️ 已存在")
            generated[char] = str(img_path)
            continue
        
        # 使用 Python 生成占位图（带角色名和描述）
        try:
            create_placeholder_image(img_path, char, desc)
            generated[char] = str(img_path)
            print(f"   {char}: ✅ 占位图")
        except Exception as e:
            print(f"   {char}: ❌ {e}")
    
    # 为每段对话生成场景图（简化版：使用对应角色的头像）
    scene_images = []
    for i, seg in enumerate(script):
        sp = seg["speaker"]
        scene_path = images_dir / f"scene_{i+1:03d}.png"
        if scene_path.exists() and scene_path.stat().st_size > 1000:
            scene_images.append(str(scene_path))
            continue
        
        src = generated.get(sp, generated.get("主播"))
        if src:
            # 复制角色头像作为场景图
            img = Image.open(src)
            img.save(scene_path)
            scene_images.append(str(scene_path))
        else:
            scene_images.append(None)
    
    print(f"   共生成 {len(scene_images)} 张场景图")
    return scene_images

def create_placeholder_image(path, name, desc):
    """创建带文字的占位图"""
    img = Image.new("RGB", (1280, 720), color=(30, 30, 40))
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 64)
        font_small = ImageFont.truetype("/System/Library/Fonts/STHeiti Light.ttc", 28)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 绘制装饰
    draw.rectangle([(0, 0), (1280, 8)], fill=(100, 150, 255))
    draw.rectangle([(0, 712), (1280, 720)], fill=(100, 150, 255))
    
    # 角色名
    bbox = draw.textbbox((0, 0), name, font=font_large)
    tw = bbox[2] - bbox[0]
    draw.text(((1280-tw)//2, 280), name, fill=(255, 255, 255), font=font_large)
    
    # 描述（截断）
    short_desc = desc[:60] + "..." if len(desc) > 60 else desc
    bbox2 = draw.textbbox((0, 0), short_desc, font=font_small)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((1280-tw2)//2, 380), short_desc, fill=(180, 180, 200), font=font_small)
    
    img.save(path)

# ============================================================
# Step 5: 生成音频
# ============================================================
def generate_audio(script, ep_dir):
    print(f"\n🎙️ [5/6] 生成音频")
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
        try:
            audio = call_tts(txt, vd, api_key)
            with open(fp, "wb") as f: f.write(audio)
            wavs.append(str(fp))
            print(f"      ✅ {len(audio)/1024:.0f}KB")
        except Exception as e:
            print(f"      ❌ {e}")
        time.sleep(0.3)
    
    # 合并
    final = ep_dir / "audio.wav"
    if wavs:
        print(f"\n   🔗 合并 {len(wavs)} 段...")
        merge_wavs(wavs, str(final))
    return str(final) if wavs else None

def merge_wavs(wavs, out):
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
    bps = p["bps"] // 8
    sil = b"\x00" * int(p["sr"] * 0.4 * p["nch"] * bps)
    pcm = bytearray(first)
    for w in wavs[1:]:
        try:
            _, d = read_wav(w); pcm.extend(sil); pcm.extend(d)
        except: pass
    ds = len(pcm); br = p["sr"] * p["nch"] * bps
    h = struct.pack("<4sI4s", b"RIFF", 36+ds, b"WAVE")
    h += struct.pack("<4sIHHIIHH", b"fmt ", 16, 1, p["nch"], p["sr"], br, p["ba"], p["bps"])
    h += struct.pack("<4sI", b"data", ds)
    with open(out, "wb") as f: f.write(h); f.write(pcm)
    print(f"   ✅ {ds/br:.1f}秒 ({ds/br/60:.1f}分钟)")

# ============================================================
# Step 6: 合成视频
# ============================================================
def generate_video(script, scene_images, audio_path, ep_dir):
    print(f"\n🎬 [6/6] 合成视频")
    
    if not audio_path:
        print("   ❌ 无音频，跳过"); return None
    
    # 获取音频时长
    probe_cmd = [FFMPEG, "-i", audio_path, "-f", "null", "-"]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    # 从 stderr 解析时长
    duration = 0
    for line in result.stderr.split("\n"):
        if "Duration" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = parts.split(":")
            duration = float(h)*3600 + float(m)*60 + float(s)
            break
    
    if duration == 0:
        print("   ❌ 无法获取音频时长"); return None
    
    print(f"   音频时长：{duration:.1f}秒")
    
    # 计算每段的时长
    total_chars = sum(len(seg["text"]) for seg in script)
    segment_durations = []
    for seg in script:
        seg_dur = (len(seg["text"]) / total_chars) * duration
        segment_durations.append(seg_dur)
    
    # 创建临时图片序列
    temp_dir = ep_dir / "temp_frames"
    temp_dir.mkdir(exist_ok=True)
    
    # 为每段生成视频帧
    frame_idx = 0
    for i, (seg, dur) in enumerate(zip(script, segment_durations)):
        sp = seg["speaker"]
        img_path = scene_images[i] if i < len(scene_images) else None
        
        if img_path and Path(img_path).exists():
            # 复制图片作为帧
            img = Image.open(img_path)
            # 添加字幕
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 36)
            except:
                font = ImageFont.load_default()
            
            # 字幕背景
            text = seg["text"][:50] + "..." if len(seg["text"]) > 50 else seg["text"]
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.rectangle([(640-tw//2-20, 600), (640+tw//2+20, 600+th+20)], fill=(0, 0, 0, 180))
            draw.text((640-tw//2, 610), text, fill=(255, 255, 255), font=font)
            
            # 角色名
            draw.rectangle([(50, 50), (200, 90)], fill=(0, 100, 200))
            draw.text((60, 55), sp, fill=(255, 255, 255), font=font)
            
            # 保存帧
            frame_path = temp_dir / f"frame_{frame_idx:05d}.png"
            img.save(frame_path)
            frame_idx += 1
    
    print(f"   生成 {frame_idx} 帧")
    
    # 用 ffmpeg 合成视频
    output_video = ep_dir / "video.mp4"
    
    # 创建 ffmpeg 输入文件列表
    concat_file = temp_dir / "concat.txt"
    # 计算每帧持续时间（简化：均匀分配）
    frames_per_seg = max(1, frame_idx // len(script))
    
    with open(concat_file, "w") as f:
        for i in range(frame_idx):
            f.write(f"file 'frame_{i:05d}.png'\n")
            f.write(f"duration {duration/frame_idx:.3f}\n")
        # 最后一帧需要重复
        f.write(f"file 'frame_{frame_idx-1:05d}.png'\n")
    
    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", audio_path,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(output_video)
    ]
    
    print(f"   合成视频中...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if output_video.exists() and output_video.stat().st_size > 1000:
        print(f"   ✅ {output_video}")
        print(f"      大小：{output_video.stat().st_size/1024/1024:.1f}MB")
        
        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return str(output_video)
    else:
        print(f"   ❌ 视频合成失败")
        print(f"      {result.stderr[:200]}")
        return None

# ============================================================
# Step 7: 保存到 Obsidian
# ============================================================
def save_to_obsidian(script, ep_num, topic, char_a, char_b, compliance, quality):
    print(f"\n📋 保存到 Obsidian")
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
| 模型 | {LLM_MODEL} + {TTS_MODEL} |

---

## 审查结果

| 审查 | 结果 |
|------|------|
| 合规 | {"✅" if compliance.get("passed") else "⚠️"} {compliance.get("risk_level","?")} |
| 质量 | {quality.get("total_score",0)}/10 |
| 创新 | {scores.get("innovation","?")} | 深度 | {scores.get("depth","?")} | 吸引 | {scores.get("appeal","?")} |

---

## 脚本全文

{script_text}

---

## 标签

#播客 #EP{ep_num:02d} #{char_a} #{char_b}
"""
    safe_a = char_a.replace(" ", "")
    safe_b = char_b.replace(" ", "")
    filepath = OBSIDIAN_BASE / f"EP{ep_num:02d}-{safe_a}vs{safe_b}.md"
    with open(filepath, "w", encoding="utf-8") as f: f.write(md)
    print(f"   ✅ {filepath}")

# ============================================================
# 主流程
# ============================================================
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
    
    # 4. 生成图像
    scene_images = generate_images(script, ep_dir, args.char_a, args.char_b)
    
    # 5. 生成音频
    audio_path = None
    if not args.skip_audio:
        audio_path = generate_audio(script, ep_dir)
    
    # 6. 合成视频
    video_path = None
    if not args.skip_video and audio_path:
        video_path = generate_video(script, scene_images, audio_path, ep_dir)
    
    # 7. 保存到 Obsidian
    save_to_obsidian(script, args.ep_num, args.topic, args.char_a, args.char_b, compliance, quality)
    
    # 输出摘要
    print("\n" + "=" * 50)
    print("✅ 完成")
    print(f"   脚本：{ep_dir / 'script.json'}")
    if audio_path: print(f"   音频：{audio_path}")
    if video_path: print(f"   视频：{video_path}")
    print("=" * 50)
    
    return {"script": script, "audio": audio_path, "video": video_path}

if __name__ == "__main__":
    main()
