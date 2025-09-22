import requests

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
