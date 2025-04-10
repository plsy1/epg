import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import re
import os
from datetime import datetime, timedelta


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

    with open(f"e/{filename}.xml", "w", encoding="utf-8") as f:
        f.write(merged_xml)

    with gzip.open(f"e/{filename}.gz", "wt", encoding="utf-8") as f:
        f.write(merged_xml)


def merge():
    today = datetime.today()

    epg_files = [
        (today - timedelta(days=i)).strftime("e/epg-%Y.%m.%d.xml") for i in range(7)
    ]
    epg_files.append((today + timedelta(days=1)).strftime("e/epg-%Y.%m.%d.xml"))
    epg_files.sort(key=lambda x: datetime.strptime(x, "e/epg-%Y.%m.%d.xml"))

    filename = "seven-days"

    save_merged_epg(epg_files, filename)



merge()