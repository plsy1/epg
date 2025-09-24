from datetime import datetime, timedelta
from Crypto.Cipher import DES
from Crypto.Util.Padding import pad
import binascii,re

def natural_key(s):
    """自然排序 key，例如 'ch10a' -> ['ch', 10, 'a']"""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

def get_date_str(offset: int = 0) -> str:
    """
    获取指定偏移天数的日期字符串

    :param offset: 偏移天数，0=今天, 1=明天, -1=昨天
    :return: 日期字符串，格式 YYYYMMDD
    """
    target_date = datetime.now() + timedelta(days=offset)
    return target_date.strftime("%Y%m%d")

def get_date_str_unicom(offset=0):
    date = datetime.now() + timedelta(days=offset)
    return date.strftime("%Y.%m.%d")

def convert_to_epg_time(date_str):
    dt = datetime.strptime(date_str, "%Y.%m.%d %H:%M:%S")
    return dt.strftime("%Y%m%d%H%M%S") + " +0800"

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