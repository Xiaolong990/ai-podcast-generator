#!/usr/bin/env python3
#!/usr/bin/env python3
"""
视频生成 v6 - 最终稳定版
基于每段音频真实时长，SRT字幕精确同步
已修复：中文字体、视频时长精确限制
"""
import subprocess, imageio_ffmpeg, os, json, shutil
from pathlib import Path
from PIL import Image, ImageDraw

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SW, SH = 1280, 720

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

def generate_video(ep_dir):
    ep_dir = Path(ep_dir)
    script = json.load(open(ep_dir/"script.json"))
    seg_dir = ep_dir/"segments"
    temp = ep_dir/"_temp"
    temp.mkdir(exist_ok=True)
    out = ep_dir/"video_v6.mp4"
    
    print(f"🎬 视频生成 v6（精确同步）")
    
    # 收集WAV
    wavs = []
    for i in range(len(script)):
        wav = seg_dir/f"{i+1:03d}_{script[i]['speaker']}.wav"
        if wav.exists(): wavs.append(str(wav))
    
    # 1. 拼接音频
    print(f"   🔗 拼接音频...")
    with open(temp/"list.txt", "w") as f:
        for w in wavs: f.write(f"file '{w}'\n")
    concat = temp/"full.wav"
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(temp/"list.txt"),
                    "-c", "copy", str(concat)], capture_output=True)
    audio_dur = ffprobe_dur(str(concat))
    print(f"      {audio_dur:.1f}秒 ({audio_dur/60:.1f}分钟)")
    
    # 2. 每段时长
    seg_durs = [ffprobe_dur(w) for w in wavs]
    
    # 3. 生成SRT
    print(f"   📝 生成字幕...")
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
    
    # 4. 背景图（使用 STHeiti 中文字体）
    bg = Image.new("RGB", (SW, SH), (20, 25, 35))
    d = ImageDraw.Draw(bg)
    for i in range(0, SH, 2):
        d.line([(0,i),(SW,i)], fill=(int(20+i/SH*30), int(25+i/SH*20), int(35+i/SH*40)))
    d.rectangle([(0,0),(SW,4)], fill=(80,140,255))
    d.rectangle([(0,SH-4),(SW,SH)], fill=(80,140,255))
    bg.save(temp/"bg.png")
    
    # 5. 合成（使用 -t 精确限制时长 + STHeiti 字体）
    print(f"   🎬 合成视频...")
    srt_esc = str(srt).replace("\\", "/").replace(":", "\\:")
    cmd = [FFMPEG, "-y", "-loop", "1", "-i", str(temp/"bg.png"), "-i", str(concat),
           "-vf", f"subtitles='{srt_esc}':force_style='FontName=STHeiti Medium,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,MarginV=50'",
           "-c:v", "libx264", "-preset", "medium", "-c:a", "aac", "-b:a", "192k",
           "-pix_fmt", "yuv420p", "-t", f"{audio_dur:.3f}", "-shortest", str(out)]
    subprocess.run(cmd, capture_output=True)
    shutil.rmtree(temp, ignore_errors=True)
    
    if out.exists() and out.stat().st_size > 1000:
        final_dur = ffprobe_dur(str(out))
        print(f"   ✅ {out}")
        print(f"      时长：{final_dur:.1f}秒 | 大小：{out.stat().st_size/1024/1024:.1f}MB")
        return str(out)
    return None

if __name__ == "__main__":
    import sys
    generate_video(sys.argv[1])
        return str(out)
    return None

if __name__ == "__main__":
    import sys
    generate_video(sys.argv[1])
