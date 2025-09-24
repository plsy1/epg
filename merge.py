import xml.etree.ElementTree as ET
import copy
from config import special_map,raw_channel_id_map,build_merge_list
from utils import *

def parse_epg_file(epg_file):
    """解析 XML 文件，返回 root 对象"""
    try:
        tree = ET.parse(epg_file)
        return tree.getroot()
    except FileNotFoundError:
        print(f"文件不存在: {epg_file}, 已跳过")
        return None

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

def merge_epg(offset: int=0):
    date = get_date_str(offset)
    merge_list = build_merge_list(offset)
    print(f"合并节目单 {date}...")
    output_file=f"data/final/final-{date}.xml"
    channels_dict = {}   
    programmes_dict = {}
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



