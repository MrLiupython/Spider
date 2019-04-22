# -*- coding: utf-8 -*-
import requests
import time
from queue import Queue


class Title_spider:
    def __init__(self, proxy):
        self.url_ = "https://udn.com/news/get_article/{page}/2/6645/{type_}?_={time_}"
        self.headers = {
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
            "referer": "https://udn.com/news/cate/2/6645",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "authority": "udn.com"
        }
        self.proxy = proxy
    
    def fetch(self, page, type_):
        time_ = int(time.time() * 1000)
        url = self.url_.format(page, type_, time_)
        r = requests.get(url, headers=self.headers, proxies=self.proxy)
        return r.text
     
    def parse(self, text, type_, queue):
        title_p = re.compile('<h2>(.*?)</h2>', re.S)
        time_p = re.compile('<div class="dt">(.*?)</div>', re.S)
        url_p = re.compile('<dt><a href="(.*?)">', re.S)
        
        title_list = title_p.findall(text)
        if not title_list:
            return None
        time_list = time_p.findall(text)
        url_list = url_p.findall(text)
        
        result = []
        for i in range(len(title_list)):
            title = title_list[i]
            time_ = time_list[i]
            url = url_list[i]
            id_ = re.search(
                '/story/.*?/(.*?)\?', url).group(1)
            queue.put({
                'title': title,
                'publish_time': time_,
                'type': type_,
                'url': url,
                'article_id': id_,
                'compliance': 0
            })


if __name__ == "__main__":
    test_page = 2
    type_ = '股市要闻'
    type_2 = 7251
    queue = Queue()
    spider = Title_spider()
    text = spider.fetch(test_page, type_2)
    spider.parse(text, type_, queue)
    result = queue.get()
    assert result['type'] == type_, '标题抓取出错'
    print('标题抓取成功')
