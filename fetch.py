import requests
import re
import gzip
import json
from Crypto.Cipher import DES
from Crypto.Util.Padding import pad
import random
import binascii
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
from config import *
from merge import merge_epg_by_displayname,merge_seven_days


def Entrance():
    url = f"http://{eas_ip}:{eas_port}/iptvepg/platform/index.jsp?UserID={userID}&Action=Login&Mode=MENU"
    response = requests.get(url)
    if response.status_code == 200:
        return
    else:
        print(f"Entrance: 请求失败，状态码：{response.status_code}")


def getEncryptToken():
    url = f"http://{eas_ip}:{eas_port}/iptvepg/platform/getencrypttoken.jsp"

    queries = {
        "UserID": userID,
        "Action": "Login",
        "TerminalFlag": "1",
        "TerminalOsType": "0",
        "STBID": "",
        "stbtype": "",
    }

    query_string = "&".join([f"{key}={value}" for key, value in queries.items()])

    full_url = f"{url}?{query_string}"

    response = requests.get(full_url)

    if response.status_code == 200:
        match = re.search(r"GetAuthInfo\('(.*?)'\)", response.text)
        if match:
            encryptToken = match.group(1)
            return encryptToken
        else:
            print("getEncryptToken: 未找到 GetAuthInfo 函数中的值, 请检查网络连接")
    else:
        print(f"getEncryptToken: 请求失败，状态码：{response.status_code}")


def generateAuthenticator():
    try:
        random_number = random.randint(10000000, 99999999)
        strEncry = str(random_number) + "$" + encryptToken
        strEncry2 = (
            strEncry
            + "$"
            + userID
            + "$"
            + stbID
            + "$"
            + ip
            + "$"
            + MAC
            + "$"
            + CustomStr
        )
        res = UnionDesEncrypt(strEncry2, encryptKey)
        return res

    except Exception as e:
        print(f"generateAuthenticator: {e}")


def auth(Authenticator):
    user_token = ""
    url = f"http://{epgIP}:{epgPort}/iptvepg/platform/auth.jsp?easip={eas_ip}&ipVersion=4&networkid=1&serterminalno=311"

    data = {"UserID": userID, "Authenticator": Authenticator, "StbIP": ip}

    response = requests.post(url, data=data)

    cookies = response.cookies
    jsessionid = cookies.get("JSESSIONID")

    url_pattern = r"window\.location\s*=\s*'(http[^']+)'"
    match = re.search(url_pattern, response.content.decode("gbk"))

    if match:
        extracted_url = match.group(1)

        response = requests.post(
            extracted_url, headers={"Cookie": f"JSESSIONID={jsessionid}"}
        )
        if response.status_code == 200:
            pattern = r"UserToken=([A-Za-z0-9_\-\.]+)"
            match = re.search(pattern, extracted_url)

            if match:
                user_token = match.group(1)
    else:
        print("auth: 鉴权链接获取失败.")

    return jsessionid, user_token


def authEPG(jsessionid):
    url = f"http://{epgIP}:{epgPort}/iptvepg/function/funcportalauth.jsp"

    headers = {"Cookie": f"JSESSIONID={jsessionid}"}

    data = {
        "UserToken": user_token,
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

    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        return


def getRawInformation(jsessionid):
    url = f"http://{epgIP}:{epgPort}/iptvepg/function/frameset_builder.jsp"

    headers = {"Cookie": f"JSESSIONID={jsessionid}"}

    data = {
        "MAIN_WIN_SRC": "/iptvepg/frame205/channel_start.jsp?tempno=-1",
        "NEED_UPDATE_STB": "1",
        "BUILD_ACTION": "FRAMESET_BUILDER",
        "hdmistatus": "undefined",
    }

    response = requests.post(url, headers=headers, data=data)

    with open("raw.txt", "w", encoding="utf-8") as file:
        file.write(response.content.decode("gbk"))


def processRawInformation():
    channels = []

    with open("raw.txt", "r", encoding="utf-8") as file:
        for line in file:
            match = re.search(r"jsSetConfig\('Channel',\s*'([^']+)'\)", line)

            if match:
                config_str = match.group(1)
                pattern = r"(\w+)=\"([^\"]+)\""
                config_dict = dict(re.findall(pattern, config_str))
                channels.append(config_dict)

    with open("iptv.json", "w", encoding="utf-8") as json_file:
        json.dump(channels, json_file, ensure_ascii=False, indent=4)
    return channels


def UnionDesEncrypt(strMsg, strKey):
    try:
        keyappend = 8 - len(strKey)
        if keyappend > 0:
            strKey = strKey + "0" * keyappend

        key_bytes = strKey.encode("utf-8")
        msg_bytes = strMsg.encode("utf-8")

        padded_msg = pad(msg_bytes, DES.block_size)

        cipher = DES.new(key_bytes, DES.MODE_ECB)
        encrypted = cipher.encrypt(padded_msg)

        return binascii.hexlify(encrypted).decode("utf-8").upper()

    except Exception as e:
        print(f"UnionDesEncrypt: {e}")


def getEPGList(jsessionid, channelcode, date):
    url = f"http://{epgIP}:{epgPort}/iptvepg/frame205/action/getchannelprogram.jsp?channelcode={channelcode}&currdate={date}"
    headers = {
        "Host": f"{epgIP}:{epgPort}",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; SkyworthBrowser) AppleWebKit/534.24 (KHTML, like Gecko) Safari/534.24 SkWebKit-SD-CU",
        "Cookie": f"JSESSIONID={jsessionid};",
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


def convert_to_epg_time(date_str):
    dt = datetime.strptime(date_str, "%Y.%m.%d %H:%M:%S")
    return dt.strftime("%Y%m%d%H%M%S") + " +0800"


def generateEPG(channelData, jsessionid, date, output_filename):
    root = ET.Element("tv", generator_info_name="https://github.com/plsy1/iptv")

    for channel in channelData:

        ChannelName = channel["ChannelName"]
        UserChannelID = channel["UserChannelID"]
        channelcode = channel["ChannelID"]

        ChannelName = ChannelName.replace("超高清", "").replace("高清", "").replace("标清", "").replace(" ", "")
        ChannelName = name_map_by_name.get(ChannelName, ChannelName)

        print(f"正在处理：{ChannelName}")

        epgData = getEPGList(jsessionid, channelcode, date)

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

        
def get_date_str(offset=0):
    date = datetime.now() + timedelta(days=offset)
    return date.strftime("%Y.%m.%d")


encryptToken = getEncryptToken()

Authenticator = generateAuthenticator()

jsessionid, user_token = auth(Authenticator)

authEPG(jsessionid)

getRawInformation(jsessionid)

channelData = processRawInformation()

generateEPG(channelData, jsessionid, get_date_str(),f"e/date/epg-{get_date_str()}.xml")
generateEPG(channelData, jsessionid, get_date_str(1),f"e/date/epg-{get_date_str(1)}.xml")
generateEPG(channelData, jsessionid, get_date_str(),"iptv.xml")

merge_epg_by_displayname(merge_list, "e/e.xml")
merge_epg_by_displayname(merge_list, f"e/date/epg-{get_date_str()}.xml")

merge_seven_days()