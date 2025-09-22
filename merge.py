import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import re
import os
from datetime import datetime, timedelta

def merge_epg_by_displayname(merge_list, output_file):
    """
    merge_list: 列表 [(xml_file, [display_name1, display_name2, ...]), ...]
                display_name 列表为空表示写入该文件的所有频道和节目
    output_file: 合并后的 XML 文件
    """
    merged_root = ET.Element("tv", generator_info_name="merged")

    for epg_file, display_names in merge_list:
        try:
            tree = ET.parse(epg_file)
            root = tree.getroot()
        except FileNotFoundError:
            print(f"文件不存在: {epg_file}, 已跳过")
            continue

        for ch in root.findall("channel"):
            ch_id = ch.attrib.get("id")
            name_elem = ch.find("display-name")
            if name_elem is None:
                print(f"频道 {ch_id} 缺少 <display-name>")
            write_channel = not display_names or (name_elem is not None and name_elem.text in display_names)

            if write_channel:
                merged_root.append(ch)
                for prog in root.findall("programme"):
                    if prog.attrib.get("channel") == ch_id:
                        merged_root.append(prog)

    merged_tree = ET.ElementTree(merged_root)
    merged_tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"合并完成，输出文件: {output_file}")

def merge_epg_files(file_list):
    channel_dict = {}

    for file in file_list:
        if not os.path.isfile(file):
            continue
        tree = ET.parse(file)
        root = tree.getroot()

        for channel_element in root.findall("channel"):
            channel_id = channel_element.get("id")

            if channel_id not in channel_dict:
                channel_dict[channel_id] = {
                    "channel_element": channel_element,
                    "programmes": [],
                }

            for programme in root.findall("programme"):
                if programme.get("channel") == channel_id:
                    channel_dict[channel_id]["programmes"].append(programme)

    new_root = ET.Element("tv", generator_info_name="https://github.com/plsy1/iptv")

    for channel_id, data in channel_dict.items():
        new_channel = ET.SubElement(new_root, "channel", id=channel_id)
        new_channel.append(data["channel_element"].find("display-name"))

        for programme in data["programmes"]:
            new_root.append(programme)

    xml_str = ET.tostring(new_root, encoding="utf-8")
    parsed_str = minidom.parseString(xml_str)
    pretty_xml_str = parsed_str.toprettyxml(indent="  ")
    pretty_xml_str = re.sub(r"\n\s*\n", "\n", pretty_xml_str)  ##去除空行
    # pretty_xml_str = re.sub(r">\n\s*<", "><", pretty_xml_str)  ##最小化

    return pretty_xml_str


def save_merged_epg(files, filename):
    merged_xml = merge_epg_files(files)

    with open(f"e/{filename}", "w", encoding="utf-8") as f:
        f.write(merged_xml)

    with gzip.open(f"e/{filename}.gz", "wt", encoding="utf-8") as f:
        f.write(merged_xml)


def merge_seven_days():
    today = datetime.today()

    epg_files = [
        (today - timedelta(days=i)).strftime("e/date/epg-%Y.%m.%d.xml") for i in range(7)
    ]
    epg_files.append((today + timedelta(days=1)).strftime("e/date/epg-%Y.%m.%d.xml"))
    epg_files.sort(key=lambda x: datetime.strptime(x, "e/date/epg-%Y.%m.%d.xml"))

    filename = "seven-days.xml"

    save_merged_epg(epg_files, filename)



