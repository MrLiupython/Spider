# -*- coding: utf-8 -*-
import requests
import urllib
import re

class Captch:
    def __init__(self, proxy):
        self.url_ = "https://www.baidu.com/s?wd={}"
        self.headers = {
            "Accept": "text/html, application/xhtml+xml, image/jxr, */*",
            "Accept - Encoding": "gzip, deflate, br",
            "Accept - Language": "zh - CN",
            "Connection": "Keep - Alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299",
            "referer":"baidu.com"
        }
        self.proxy = proxy

    def captch(self, title):
        # 百度搜索api
        url = self.url_.format(urllib.parse.quote(title))

        response = requests.get(
            url,
            headers=self.headers,
            proxies=self.proxy
        )
        # 查找百度结果的飘红
        pattern = re.compile('<h3 class="t">(.*?)</h3>', re.S)
        pattern2 = re.compile('<em>(.*?)</em>', re.S)
        result = pattern.findall(response.text)
        for item in result:
            result2 = pattern2.findall(item)
            for item2 in result2:
                if len(item2) >= 8:
                    # print(item2)
                    return 1
        return 0
            
        

if __name__ == "__main__":
    test_text = "Python 创建"
    one = Captch()
    proxy = {}
    result = one.captch(test_text, proxy)
    if result:
        print("百度搜索到有相似度的结果")
    else:
        print("百度没有搜索到结果")
