from config import *
from utils import *
import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import re
import os

def merge_epg_files(file_list):
    channel_dict = {}

    for file in file_list:
        if not os.path.isfile(file):
            print(f"文件 {file} 不存在，跳过")
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

    sorted_keys = sorted(channel_dict.keys(), key=natural_key)

    new_root = ET.Element("tv", generator_info_name="https://github.com/plsy1/iptv")

    for channel_id in sorted_keys:
        data = channel_dict[channel_id]
        new_channel = ET.SubElement(new_root, "channel", id=channel_id)
        display_name = data["channel_element"].find("display-name")
        if display_name is not None:
            new_channel.append(display_name)
        for programme in data["programmes"]:
            new_root.append(programme)

    xml_str = ET.tostring(new_root, encoding="utf-8")
    parsed_str = minidom.parseString(xml_str)
    pretty_xml_str = parsed_str.toprettyxml(indent="  ")
    pretty_xml_str = re.sub(r"\n\s*\n", "\n", pretty_xml_str)

    return pretty_xml_str



def gennerate_multi_day(forward,backward,filename):
    today = datetime.today()

    epg_files = [
        (today - timedelta(days=i)).strftime("data/final/final-%Y%m%d.xml") for i in range(forward+1)
    ]
    epg_files.append((today + timedelta(days=backward)).strftime("data/final/final-%Y%m%d.xml"))
    epg_files.sort(key=lambda x: datetime.strptime(x, "data/final/final-%Y%m%d.xml"))

    merged_xml = merge_epg_files(epg_files)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(merged_xml)

    with gzip.open(f'{filename}.gz', "wt", encoding="utf-8") as f:
        f.write(merged_xml)


def generate_multiday():
    today = "e/e.xml"
    threedays = "e/three-days.xml"
    sevendays = "e/seven-days.xml"
    gennerate_multi_day(0,1,today)
    gennerate_multi_day(3,1,threedays)
    gennerate_multi_day(7,1,sevendays)

