import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import re
import os
import copy
from datetime import datetime, timedelta
from config import special_map,raw_channel_id_map

def parse_epg_file(epg_file):
    """解析 XML 文件，返回 root 对象"""
    try:
        tree = ET.parse(epg_file)
        return tree.getroot()
    except FileNotFoundError:
        print(f"文件不存在: {epg_file}, 已跳过")
        return None

def natural_key(s):
    """自然排序 key，例如 'ch10a' -> ['ch', 10, 'a']"""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

def get_channel_infos(name, ch_id):
    """
    返回两个结果：
    1. 原始频道的最终 ID（raw_channel_id_map 处理）
    2. special_map 映射信息，如果有，返回 (new_id, new_name)，否则 None
    """
    original_id = raw_channel_id_map.get(name, ch_id)
    special_info = None
    if name in special_map:
        special_info = (special_map[name]["new_id"], special_map[name]["new_name"])
    return original_id, special_info

def merge_epg_by_displayname(merge_list, output_file):
    channels_dict = {}     # {channel_id: channel_element}
    programmes_dict = {}   # {channel_id: [programme_elements]}
    written_channels = set()

    for epg_file, display_names in merge_list:
        root = parse_epg_file(epg_file)
        if root is None:
            continue

        programmes_by_channel = {}
        for prog in root.findall("programme"):
            orig_ch_id = prog.attrib.get("channel")
            programmes_by_channel.setdefault(orig_ch_id, []).append(prog)

        for ch in root.findall("channel"):
            name_elem = ch.find("display-name")
            if name_elem is None:
                continue
            if display_names and name_elem.text not in display_names:
                continue

            ch_id = ch.attrib.get("id")
            original_id, special_info = get_channel_infos(name_elem.text, ch_id)

            if original_id not in written_channels:
                written_channels.add(original_id)
                ch_copy = copy.deepcopy(ch)
                ch_copy.set("id", original_id)
                dn_copy = ch_copy.find("display-name")
                if dn_copy is not None:
                    dn_copy.text = name_elem.text 
                channels_dict[original_id] = ch_copy

                programmes_dict[original_id] = []
                for prog in programmes_by_channel.get(ch_id, []):
                    prog_copy = copy.deepcopy(prog)
                    prog_copy.set("channel", original_id)
                    programmes_dict[original_id].append(prog_copy)

            if special_info:
                special_id, special_name = special_info
                if special_id not in written_channels:
                    written_channels.add(special_id)
                    ch_copy = copy.deepcopy(ch)
                    ch_copy.set("id", special_id)
                    dn_copy = ch_copy.find("display-name")
                    if dn_copy is not None:
                        dn_copy.text = special_name
                    channels_dict[special_id] = ch_copy

                    programmes_dict[special_id] = []
                    for prog in programmes_by_channel.get(ch_id, []):
                        prog_copy = copy.deepcopy(prog)
                        prog_copy.set("channel", special_id)
                        programmes_dict[special_id].append(prog_copy)

    sorted_channel_ids = sorted(channels_dict.keys(), key=natural_key)

    merged_root = ET.Element("tv", generator_info_name="merged")
    for ch_id in sorted_channel_ids:
        merged_root.append(channels_dict[ch_id])
        for prog_elem in programmes_dict.get(ch_id, []):
            merged_root.append(prog_elem)

    ET.ElementTree(merged_root).write(output_file, encoding="utf-8", xml_declaration=True)


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



