import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import re
import os
from datetime import datetime, timedelta
import requests

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


def merge():
    today = datetime.today()

    epg_files = [
        (today - timedelta(days=i)).strftime("e/date/epg-%Y.%m.%d.xml") for i in range(7)
    ]
    epg_files.append((today + timedelta(days=1)).strftime("e/date/epg-%Y.%m.%d.xml"))
    epg_files.sort(key=lambda x: datetime.strptime(x, "e/date/epg-%Y.%m.%d.xml"))

    filename = "seven-days.xml"

    save_merged_epg(epg_files, filename)


def download_xml(url, save_path):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status() 
        res.encoding = 'utf-8'
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(res.text)
        print(f"下载成功: {save_path}")
    except requests.RequestException as e:
        print(f"下载失败: {e}")


def merge_epg_by_displayname(epg_files_with_displayname, output_file):
    """
    epg_files_with_displayname: 列表 [(xml_file, display_name), ...]
    output_file: 合并后的 XML 文件
    """
    merged_root = ET.Element('tv', generator_info_name="merged")

    for epg_file, display_name in epg_files_with_displayname:
        try:
            tree = ET.parse(epg_file)
            root = tree.getroot()
        except FileNotFoundError:
            print(f"文件不存在: {epg_file}, 已跳过")
            continue

        channel_map = {}
        for ch in root.findall('channel'):
            ch_id = ch.attrib.get('id')
            name_elem = ch.find('display-name')
            if name_elem is not None and name_elem.text == display_name:
                channel_map[ch_id] = display_name
                merged_root.append(ch)

        for prog in root.findall('programme'):
            ch_id = prog.attrib.get('channel')
            if ch_id in channel_map:
                merged_root.append(prog)
                
    merged_tree = ET.ElementTree(merged_root)
    merged_tree.write(output_file, encoding='utf-8', xml_declaration=True)
    print(f"合并完成，输出文件: {output_file}")

def merge_others():
    import json

    with open('config.json', 'r', encoding='utf-8') as f:
        epg_config = json.load(f)

    epg_list = []
    for item in epg_config:
        for name in item['display_name']:
            epg_list.append((item['file'], name))

    download_xml('https://raw.githubusercontent.com/sparkssssssssss/epg/main/pp.xml', '112114-today.xml')

    merge_epg_by_displayname(epg_list, 'e-merged.xml')

merge()
# merge_others()
