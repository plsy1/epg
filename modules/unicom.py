import re, random, requests,json
import xml.etree.ElementTree as ET
from tqdm import tqdm
from xml.dom import minidom
from merge import convert_to_epg_time
from utils import *
from config import (
    eas_ip,
    eas_port,
    epgIP,
    epgPort,
    userID,
    stbID,
    ip,
    MAC,
    CustomStr,
    encryptKey,
    name_map_by_name
)



class IPTVClient:
    def __init__(self):
        self.session = requests.Session()
        self.encrypt_token = None
        self.jsessionid = None
        self.user_token = None
        self.channels = None

    def login(self):
        url = f"http://{eas_ip}:{eas_port}/iptvepg/platform/getencrypttoken.jsp"
        params = {
            "UserID": userID,
            "Action": "Login",
            "TerminalFlag": "1",
            "TerminalOsType": "0",
            "STBID": "",
            "stbtype": "",
        }
        r = self.session.get(url, params=params, timeout=5)
        r.raise_for_status()
        m = re.search(r"GetAuthInfo\('(.*?)'\)", r.text)
        if not m:
            raise RuntimeError("登录失败: encryptToken 未获取")
        self.encrypt_token = m.group(1)

    def auth(self):
        rand = random.randint(10_000_000, 99_999_999)
        src = f"{rand}${self.encrypt_token}"
        src2 = f"{src}${userID}${stbID}${ip}${MAC}${CustomStr}"
        authenticator = UnionDesEncrypt(src2, encryptKey)
        url = f"http://{epgIP}:{epgPort}/iptvepg/platform/auth.jsp"
        data = {
            "easip": eas_ip,
            "ipVersion": "4",
            "networkid": "1",
            "serterminalno": "311",
            "UserID": userID,
            "Authenticator": authenticator,
            "StbIP": ip,
        }
        r = self.session.post(url, data=data, timeout=5)
        r.raise_for_status()
        self.jsessionid = r.cookies.get("JSESSIONID")

        m = re.search(r"window\.location\s*=\s*'(http[^']+)'", r.content.decode("gbk"))
        if not m:
            raise RuntimeError("鉴权失败: 跳转地址未找到")

        redirect_url = m.group(1)
        r2 = self.session.post(
            redirect_url, headers={"Cookie": f"JSESSIONID={self.jsessionid}"}, timeout=5
        )
        r2.raise_for_status()
        m2 = re.search(r"UserToken=([A-Za-z0-9_\-\.]+)", redirect_url)
        if not m2:
            raise RuntimeError("鉴权失败: user_token 未获取")
        self.user_token = m2.group(1)

    def portal_auth(self):
        url = f"http://{epgIP}:{epgPort}/iptvepg/function/funcportalauth.jsp"
        headers = {"Cookie": f"JSESSIONID={self.jsessionid}"}
        data = {
            "UserToken": self.user_token,
            "UserID": userID,
            "STBID": stbID,
            "stbinfo": "",
            "prmid": "",
            "easip": eas_ip,
            "networkid": 1,
            "stbtype": "",
            "drmsupplier": "",
            "stbversion": "",
        }
        r = self.session.post(url, headers=headers, data=data, timeout=5)
        r.raise_for_status()

    def get_channels(self):
        url = f"http://{epgIP}:{epgPort}/iptvepg/function/frameset_builder.jsp"
        headers = {"Cookie": f"JSESSIONID={self.jsessionid}"}
        data = {
            "MAIN_WIN_SRC": "/iptvepg/frame205/channel_start.jsp?tempno=-1",
            "NEED_UPDATE_STB": "1",
            "BUILD_ACTION": "FRAMESET_BUILDER",
            "hdmistatus": "undefined",
        }
        r = self.session.post(url, headers=headers, data=data, timeout=5)
        r.raise_for_status()
        text = r.content.decode("gbk")
        channels = []
        for line in text.splitlines():
            m = re.search(r"jsSetConfig\('Channel',\s*'([^']+)'\)", line)
            if m:
                cfg = dict(re.findall(r"(\w+)=\"([^\"]+)\"", m.group(1)))
                channels.append(cfg)
        self.channels = channels
    
    def getEPGList(self,channelcode, date):
        url = f"http://{epgIP}:{epgPort}/iptvepg/frame205/action/getchannelprogram.jsp?channelcode={channelcode}&currdate={date}"
        headers = {
            "Host": f"{epgIP}:{epgPort}",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; SkyworthBrowser) AppleWebKit/534.24 (KHTML, like Gecko) Safari/534.24 SkWebKit-SD-CU",
            "Cookie": f"JSESSIONID={self.jsessionid};",
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            raw_data = response.text.strip()
            pattern = r"prevuelist:(.*)"
            match = re.search(pattern, raw_data)
            if match:
                raw_data = match.group(1)
                raw_data = raw_data[:-1]
                data = json.loads(raw_data)
                return data

        else:
            print(f"Error: {response.status_code}")
    
    def generateEPGbyDate(self,date, output_filename):
        root = ET.Element("tv", generator_info_name="https://github.com/plsy1/iptv")

        for channel in tqdm(self.channels, desc=f"生成 EPG - {date}"):
            ChannelName = channel["ChannelName"]
            UserChannelID = channel["UserChannelID"]
            channelcode = channel["ChannelID"]

            ChannelName = ChannelName.replace("超高清", "").replace("高清", "").replace("标清", "").replace(" ", "")
            ChannelName = name_map_by_name.get(ChannelName, ChannelName)

            max_retries = 3
            retries = 0
            epgData = None
            while retries < max_retries:
                epgData = self.getEPGList(channelcode, date)
                if epgData:
                    break
                retries += 1
            if not epgData:
                continue

            channel_element = ET.SubElement(root, "channel", id=UserChannelID)
            ET.SubElement(channel_element, "display-name", lang="zh").text = ChannelName

            for item in epgData:
                start_time = convert_to_epg_time(item["begintime"])
                end_time = convert_to_epg_time(item["endtime"])

                programme = ET.SubElement(
                    root,
                    "programme",
                    start=start_time,
                    stop=end_time,
                    channel=UserChannelID,
                )
                ET.SubElement(programme, "title", lang="zh").text = item["prevuename"]

        xml_str = ET.tostring(root, encoding="utf-8")
        parsed_str = minidom.parseString(xml_str)
        pretty_xml_str = parsed_str.toprettyxml(indent="  ")

        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(pretty_xml_str)


def get_epg_from_unicom():
    print("从 联通IPTV 获取节目单...")
    client = IPTVClient()
    client.login()
    client.auth()
    client.portal_auth()
    client.get_channels()

    today = f"data/unicom/unicom-{get_date_str()}.xml"
    tomorrow = f"data/unicom/unicom-{get_date_str(1)}.xml"
    client.generateEPGbyDate(get_date_str_unicom(),today)
    client.generateEPGbyDate(get_date_str_unicom(1),tomorrow)

