import requests, re, json
from bs4 import BeautifulSoup as bs
import time
import xml.etree.ElementTree as ET
from utils import *


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    " AppleWebKit/537.36 (KHTML, like Gecko)"
    " Chrome/99.0.4844.82 Safari/537.36"
}

display_map_by_name = {
    "CCTV-1 综合": "CCTV1",
    "CCTV-2 财经": "CCTV2",
    "CCTV-3 综艺": "CCTV3",
    "CCTV-4 (亚洲)": "CCTV4",
    "CCTV-5 体育": "CCTV5",
    "CCTV-6 电影": "CCTV6",
    "CCTV-7 国防军事": "CCTV7",
    "CCTV-8 电视剧": "CCTV8",
    "CCTV-9 纪录": "CCTV9",
    "CCTV-10 科教": "CCTV10",
    "CCTV-11 戏曲": "CCTV11",
    "CCTV-12 社会与法": "CCTV12",
    "CCTV-13 新闻": "CCTV13",
    "CCTV-14 少儿": "CCTV14",
    "CCTV-15 音乐": "CCTV15",
    "CCTV-5+ 体育赛事": "CCTV5+",
    "CCTV-16奥林匹克": "CCTV16",
    "CCTV-17农业农村": "CCTV17",
    "CCTV-4 (欧洲)": "CCTV4欧洲",
    "CCTV-4 (美洲)": "CCTV4美洲"
}

def data_to_epg(data: dict, output_file: str):
    tv = ET.Element("tv")

    for channel_id, channel_info in data.items():
        channel = ET.SubElement(tv, "channel", id=channel_id)
        display_name = ET.SubElement(channel, "display-name", lang="zh")

        name = channel_info.get("channelName", channel_id)
        name = display_map_by_name.get(name,name)
        display_name.text = name

        for prog in channel_info.get("list", []):
            start = time.strftime(
                "%Y%m%d%H%M%S +0800", time.localtime(prog["startTime"])
            )
            stop = time.strftime("%Y%m%d%H%M%S +0800", time.localtime(prog["endTime"]))
            programme = ET.SubElement(
                tv, "programme", start=start, stop=stop, channel=channel_id
            )

            title = ET.SubElement(programme, "title", lang="zh")
            title.text = prog.get("title", "未知节目")

    tree = ET.ElementTree(tv)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)



def get_epgs_cctv(channel_id: str, date_str: str, retries: int = 3, delay: float = 1.0):
    url = (
        "http://api.cntv.cn/epg/getEpgInfoByChannelNew"
        "?c=%s&serviceId=tvcctv&d=%s&t=jsonp&cb=set" % (channel_id, date_str)
    )

    for attempt in range(retries):
        try:
            res = requests.get(url, headers=headers, timeout=5)
            raw = res.text.strip()
            m = re.search(r"set\((.*)\)\s*;?", raw, re.S)
            if m:
                json_str = m.group(1)
                return json.loads(json_str)
            else:
                print(f"{channel_id} 未匹配到 JSON 数据，重试 {attempt + 1}/{retries} ...")
                time.sleep(delay)
        except Exception as e:
            print(f"{channel_id} 请求异常，重试 {attempt + 1}/{retries} ... {e}")
            time.sleep(delay)
    print(f"{channel_id} 获取失败，跳过")
    return None


def get_channel_id_list():
    channels = []
    host = "https://tv.cctv.com"
    url = "%s/epg/index.shtml" % host
    res = requests.get(url, headers=headers)
    res.encoding = "utf-8"
    soup = bs(res.text, "html.parser")
    lis = soup.select("div.channel_con > div > ul > li")
    for li in lis:
        id = li.select("img")[0].attrs["title"].strip()
        channels.append(id)
    return channels


def fetch_all_epg_by_date(date_str: str, output_file: str = "cctv.xml"):
    """
    获取指定日期的所有 CCTV 频道 EPG 并生成 XML

    :param date_str: 日期字符串，例如 "20250924"
    :param output_file: 输出的 XML 文件名
    """
    ch_list = get_channel_id_list()
    all_data = {}
    from tqdm import tqdm
    for channel_id in tqdm(ch_list, desc=f"生成 EPG - {date_str}"):
        try:
            data = get_epgs_cctv(channel_id, date_str)
            all_data.update(data["data"])
        except Exception as e:
            pass

    data_to_epg(all_data, output_file)



def get_epg_from_cctv():
    print("从 CCTV 获取节目单...")
    today = f"data/cctv/cctv-{get_date_str()}.xml"
    tomorrow = f"data/cctv/cctv-{get_date_str(1)}.xml"
    fetch_all_epg_by_date(get_date_str(), today)
    fetch_all_epg_by_date(get_date_str(1), tomorrow)
