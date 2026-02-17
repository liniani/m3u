import requests
import re

# 配置你的两个直播源网址
SOURCE_URLS = [
    "https://raw.githubusercontent.com/mytv-android/BRTV-Live-M3U8/refs/heads/main/iptv.m3u",
    "https://raw.githubusercontent.com/liniani/BRTV-Live-M3U8/refs/heads/main/cctv.m3u"
]
OUTPUT_FILE = "live.m3u" # 最终合并后存入仓库的文件名

def download_and_merge(urls):
    all_lines = []
    # 可以加一个集合来存储频道名，实现简单的去重
    channel_names = set()

    for url in urls:
        try:
            print(f"正在下载: {url}")
            response = requests.get(url, timeout=10)
            response.encoding = 'utf-8'
            content = response.text

            # 简单的去重逻辑：按行处理，通过频道名去重
            lines = content.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]
                # 如果这一行是频道信息（通常以 #EXTINF 开头）
                if line.startswith('#EXTINF:'):
                    # 尝试提取频道名
                    match = re.search(r'tvg-name="([^"]+)"|,([^,]+)$', line)
                    if match:
                        channel_name = match.group(1) or match.group(2)
                        # 如果频道名没出现过，就保留这一行和下一行的URL
                        if channel_name not in channel_names:
                            channel_names.add(channel_name)
                            all_lines.append(line)
                            if i + 1 < len(lines) and not lines[i+1].startswith('#'):
                                all_lines.append(lines[i+1])
                    else:
                        # 如果没有提取到频道名，也保留（或根据你的规则处理）
                        all_lines.append(line)
                        if i + 1 < len(lines) and not lines[i+1].startswith('#'):
                            all_lines.append(lines[i+1])
                    i += 2 # 跳过下一行URL
                else:
                    # 如果不是#EXTINF行（比如文件头 #EXTM3U），直接添加
                    if line and not line in all_lines:
                        all_lines.append(line)
                    i += 1
        except Exception as e:
            print(f"下载失败 {url}: {e}")

    # 确保文件以 #EXTM3U 开头
    if all_lines and not all_lines[0].startswith('#EXTM3U'):
        all_lines.insert(0, '#EXTM3U')
    return '\n'.join(all_lines)

if __name__ == "__main__":
    merged_content = download_and_merge(SOURCE_URLS)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(merged_content)
    print(f"合并完成，已保存至 {OUTPUT_FILE}")

    # 这里可以增加一个判断：如果文件内容与上次提交时相比没有变化，就退出，避免产生无效提交记录
