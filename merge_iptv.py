import requests
import re

# ========== 配置区域 ==========
SOURCE_URLS = [
    "https://raw.githubusercontent.com/mytv-android/BRTV-Live-M3U8/refs/heads/main/iptv.m3u",
    "https://raw.githubusercontent.com/liniani/BRTV-Live-M3U8/refs/heads/main/cctv.m3u",
    # 在这里添加更多源，例如：
    # "https://example.com/other.m3u",
]

OUTPUT_FILE = "live.m3u"

# 分组顺序（北京置顶）
GROUP_ORDER = ["北京", "央视", "卫视", "地方", "其他", "未分组"]

# 组名映射：将源中的原始组名统一到标准组
GROUP_MAPPING = {
    "北京": "北京",
    "BRTV": "北京",
    "BTV": "北京",
    "央视": "央视",
    "CCTV": "央视",
    "卫视": "卫视",
    "地方": "地方",
    # 可根据需要继续添加
}
# ==============================

def extract_group_title(extinf_line):
    """提取 group-title 属性值"""
    match = re.search(r'group-title="([^"]*)"', extinf_line)
    return match.group(1) if match else None

def normalize_group(group_name):
    """将原始组名映射为标准组名，若无映射则返回原值"""
    return GROUP_MAPPING.get(group_name, group_name)

def infer_group(channel_name):
    """根据频道名推断分组（当无 group-title 时使用）"""
    name_upper = channel_name.upper()
    if any(key in name_upper for key in ["北京", "BRTV", "BTV"]):
        return "北京"
    if name_upper.startswith("CCTV"):
        return "央视"
    if "卫视" in channel_name:
        return "卫视"
    return "其他"

def sort_key(channel):
    """排序：按 GROUP_ORDER 顺序，未知组放最后"""
    group = channel['group']
    try:
        return GROUP_ORDER.index(group)
    except ValueError:
        return len(GROUP_ORDER)

def download_and_merge(urls):
    channels = []
    channel_names = set()

    for url in urls:
        try:
            print(f"正在下载: {url}")
            response = requests.get(url, timeout=10)
            response.encoding = 'utf-8'
            lines = response.text.splitlines()

            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue

                if line.startswith('#EXTINF:'):
                    # 提取频道名
                    name_match = re.search(r'tvg-name="([^"]+)"|,([^,]+)$', line)
                    channel_name = None
                    if name_match:
                        channel_name = name_match.group(1) or name_match.group(2)

                    if channel_name and channel_name not in channel_names:
                        # 1. 尝试从源中提取 group-title
                        group = extract_group_title(line)
                        if group:
                            group = normalize_group(group)  # 映射
                        else:
                            group = infer_group(channel_name)  # 推断

                        # 强制后处理：若频道名明显属于北京但组不对，强制设为北京
                        if "北京" in channel_name and group != "北京":
                            group = "北京"

                        print(f"发现频道: {channel_name} -> 组: {group}")  # 调试输出

                        channel_names.add(channel_name)
                        if i + 1 < len(lines):
                            url_line = lines[i+1].strip()
                            if url_line and not url_line.startswith('#'):
                                channels.append({
                                    'name': channel_name,
                                    'group': group,
                                    'extinf': line,
                                    'url': url_line
                                })
                                i += 2
                                continue
                    i += 1
                else:
                    i += 1
        except Exception as e:
            print(f"下载失败 {url}: {e}")

    # 按组排序
    channels.sort(key=sort_key)

    # 生成输出
    output_lines = ['#EXTM3U']
    for ch in channels:
        output_lines.append(ch['extinf'])
        output_lines.append(ch['url'])

    return '\n'.join(output_lines)

if __name__ == "__main__":
    merged_content = download_and_merge(SOURCE_URLS)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(merged_content)
    print(f"合并完成，已保存至 {OUTPUT_FILE}")
