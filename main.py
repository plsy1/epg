from modules.unicom import get_epg_from_unicom
from modules.cctv import get_epg_from_cctv
from modules.oneonetwo import get_epg_from_112114
from merge import merge_epg
from multiday import generate_multiday
from markdown import update_readme

get_epg_from_unicom()
get_epg_from_cctv()
get_epg_from_112114()

merge_epg()
merge_epg(1)

generate_multiday()

update_readme("e/three-days.xml", "README.md")



