import requests
import re

# ========== 配置区域 ==========
# 你可以在这里添加、删除或修改源 URL，支持任意数量
SOURCE_URLS = [
    "https://raw.githubusercontent.com/mytv-android/BRTV-Live-M3U8/refs/heads/main/iptv.m3u",
    "https://raw.githubusercontent.com/liniani/BRTV-Live-M3U8/refs/heads/main/cctv.m3u",
    # 添加第三个源：
    # "https://example.com/other.m3u",
    # 添加第四个源：
    # "https://example.com/more.m3u",
]

OUTPUT_FILE = "live.m3u"

# 分组显示顺序：北京 → 央视 → 卫视 → 地方 → 其他 → 未分组
GROUP_ORDER = ["北京", "央视", "卫视", "地方", "其他", "未分组"]
# ==============================

def extract_group_title(extinf_line):
    """从 #EXTINF 行提取 group-title 属性值，若无则返回 None"""
    match = re.search(r'group-title="([^"]*)"', extinf_line)
    return match.group(1) if match else None

def infer_group(channel_name):
    """根据频道名推断分组（当 group-title 缺失时使用）"""
    name_upper = channel_name.upper()
    if name_upper.startswith(("BTV", "BRTV", "北京")):
        return "北京"
    if name_upper.startswith("CCTV"):
        return "央视"
    if "卫视" in channel_name:
        return "卫视"
    # 可继续添加更多规则，例如地方台识别
    return "其他"

def sort_key(channel):
    """用于排序的 key 函数：按 GROUP_ORDER 索引排序，不在列表中的组排在最后"""
    group = channel['group']
    try:
        return GROUP_ORDER.index(group)
    except ValueError:
        return len(GROUP_ORDER)  # 未知组统一放最后

def download_and_merge(urls):
    channels = []          # 存储所有频道条目
    channel_names = set()  # 用于去重

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
                        # 获取分组信息
                        group = extract_group_title(line)
                        if not group:
                            group = infer_group(channel_name)
                        
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

    # 生成最终内容
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
