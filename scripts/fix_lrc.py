#!/usr/bin/env python3
"""
修复播客LRC字幕文件：
1. 移除英文文本，只保留中文
2. 调整时间戳以匹配音频时长
"""

import wave
import os
import re
import shutil
from pathlib import Path

def extract_chinese(text):
    """从文本中提取中文部分，移除英文"""
    # 如果包含 | 分隔符，取后面的部分（中文部分）
    if '|' in text:
        parts = text.split('|')
        # 取最后一个包含中文的部分
        for part in reversed(parts):
            if re.search(r'[\u4e00-\u9fff]', part):
                return part.strip()
        return parts[-1].strip()
    
    # 如果没有分隔符，检查是否主要是英文
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text.strip())
    
    if total_chars == 0:
        return text
    
    # 如果中文字符少于30%，可能是纯英文或混合文本
    if chinese_chars / total_chars < 0.3:
        return None  # 标记为需要删除
    
    return text

def fix_lrc_file(lrc_path, audio_duration):
    """修复单个LRC文件"""
    with open(lrc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    fixed_lines = []
    
    # 提取所有时间戳和内容
    entries = []
    for line in lines:
        match = re.match(r'\[(\d{2}):(\d{2})\.(\d{2})\](.*)', line)
        if match:
            min_val, sec_val, ms_val, text = match.groups()
            timestamp = int(min_val) * 60 + int(sec_val) + int(ms_val) / 100
            entries.append((timestamp, text.strip()))
        elif line.startswith('[') and ']' in line:
            # 保留元数据行
            fixed_lines.append(line)
    
    if not entries:
        return False
    
    # 获取最后一个时间戳
    last_timestamp = entries[-1][0]
    
    if last_timestamp == 0:
        return False
    
    # 计算缩放因子
    scale_factor = audio_duration / last_timestamp
    
    # 处理每个条目
    for timestamp, text in entries:
        # 提取中文
        chinese_text = extract_chinese(text)
        
        # 如果是纯英文或无意义内容，跳过
        if chinese_text is None or chinese_text == '':
            continue
        
        # 调整时间戳
        new_timestamp = timestamp * scale_factor
        minutes = int(new_timestamp // 60)
        seconds = int(new_timestamp % 60)
        ms = int((new_timestamp % 1) * 100)
        
        # 格式化为 LRC 格式
        formatted = f"[{minutes:02d}:{seconds:02d}.{ms:02d}] {chinese_text}"
        fixed_lines.append(formatted)
    
    # 写回文件
    with open(lrc_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))
    
    return True

def get_audio_duration(audio_path):
    """获取音频时长"""
    with wave.open(audio_path, 'r') as w:
        return w.getnframes() / w.getframerate()

def main():
    base_dir = '/Users/duren/Projects/输出/AI神仙打架'
    
    print("开始修复LRC字幕文件...\n")
    
    for ep_dir in sorted(os.listdir(base_dir)):
        if not ep_dir.startswith('EP'):
            continue
        
        ep_path = os.path.join(base_dir, ep_dir)
        if not os.path.isdir(ep_path):
            continue
        
        # 查找LRC文件
        lrc_files = [f for f in os.listdir(ep_path) if f.endswith('.lrc')]
        if not lrc_files:
            print(f"{ep_dir}: 未找到LRC文件，跳过")
            continue
        
        lrc_path = os.path.join(ep_path, lrc_files[0])
        audio_path = os.path.join(ep_path, 'audio.wav')
        
        if not os.path.exists(audio_path):
            print(f"{ep_dir}: 未找到音频文件，跳过")
            continue
        
        # 获取音频时长
        audio_duration = get_audio_duration(audio_path)
        
        # 备份原文件
        backup_path = lrc_path + '.bak'
        if not os.path.exists(backup_path):
            shutil.copy2(lrc_path, backup_path)
        
        # 修复LRC文件
        success = fix_lrc_file(lrc_path, audio_duration)
        
        if success:
            print(f"{ep_dir}: ✓ 已修复 (音频时长: {audio_duration:.2f}秒)")
        else:
            print(f"{ep_dir}: ✗ 修复失败")
    
    print("\n修复完成！")

if __name__ == '__main__':
    main()
