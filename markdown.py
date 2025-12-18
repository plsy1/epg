import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
def update_readme(epg_file, md_file, template_md="data/README-TEMPLATE.md"):
    """
    将 EPG XML 文件的 display-name 写入 Markdown 表格，
    开头包含模板内容，再写更新时间和总频道数
    """
    try:
        with open(template_md, "r", encoding="utf-8") as f:
            template_lines = f.read().splitlines()
    except Exception as e:
        print(f"读取模板 {template_md} 失败: {e}")
        template_lines = []

    try:
        tree = ET.parse(epg_file)
        root = tree.getroot()
    except Exception as e:
        print(f"解析 {epg_file} 失败: {e}")
        return

    channels = []
    for ch in root.findall("channel"):
        dn_elem = ch.find("display-name")
        if dn_elem is not None and dn_elem.text:
            ch_id = ch.attrib.get("id", "")
            channels.append((dn_elem.text, ch_id))

    total_channels = len(channels)


    tz_utc8 = timezone(timedelta(hours=8))
    now_str = datetime.now(tz=tz_utc8).strftime("%Y-%m-%d %H:%M:%S")
    
    lines = []
    lines.extend(template_lines)
    lines.append("\n")
    lines.append(f"## 节目单信息\n")
    lines.append(f"**更新时间**: {now_str} UTC+8\n")
    lines.append(f"**频道总数**: {total_channels}\n")
    lines.append("| 频道名称 | 频道号 |")
    lines.append("|--------------|------------|")

    for name, ch_id in channels:
        lines.append(f"| {name} | {ch_id} |")

    with open(md_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

