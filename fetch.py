import shutil
from config import *
from merge import append_channel_from_other_epg,gennerate_multi_day,get_date_str
from markdown import update_readme
from STB import IPTVClient

client = IPTVClient()
client.login()
client.auth()
client.portal_auth()
client.get_channels()

# # 按天从联通 IPTV 获取 EPG

day0 = f"e/date/epg-{get_date_str()}.xml"
day1 = f"e/date/epg-{get_date_str(1)}.xml"
client.generateEPGbyDate(get_date_str(),day0)
client.generateEPGbyDate(get_date_str(1),day1)

# ## 从其他 EPG 数据源添加频道

tmpFileForMerge = "data/iptv.xml"
shutil.copy(day0, tmpFileForMerge)
append_channel_from_other_epg(merge_list, day0)

# 生成多天 EPG 列表

today = "e/e.xml"
gennerate_multi_day(0,1,today)

sevendays = "e/seven-days.xml"
gennerate_multi_day(7,1,sevendays)

threedays = "e/three-days.xml"
gennerate_multi_day(3,1,threedays)

## 更新 README

update_readme("e/e.xml", "README.md")