# -*- coding:utf-8 -*-
import threading
from queue import Queue
from news_spider import Title_spider
from captch import Captch
from translate import translate
from db import Database

# 新闻标题队列
news_queue = Queue()

# 代理
proxy = {}

# 新闻类型
type_dict = {
    "股市要闻": 7251,
    "上市电子": 7253,
    "店头未上市": 7254,
    "权证期货": 7255
}

# 线程池
class Thread_pool:
    def __init__(self, thread_name, thread_num=10):
        self.num = thread_num
        self.thread_name = thread_name
        self._pool = [self.thread_name(i+1) for i range(self.num)]

    def on(self):
        for i in self._pool:
          i.start()
    
    def is_alive(self):
        for i in self._pool:
           if i.is_alive():
               return True
        return False

# 新闻标题抓取线程
class News_Thread(threading.Thread):
    def __init__(self, name=1):
        super().__init__()
        self.name = name
        self.daemon = True

    def run(self):
        start_time = time.time()
        spider = Title_spider(proxy)

        for i in type_dict:
           page = 2
           while 1:
               text = spider.fetch(page, type_dict[i])
               if spider.parse(text, i, news_queue):
                   page += 1
               else:
                   break


# 百度验证线程
class Captch_Thread(threading.Thread):
    def __init__(self, name=1, timeout=60):
        super().__init__()
        self.name = name
        self.daemon = True
        self.stop_flag = False
        self.timeout = timeout
        
    def run(self):
        start_time = time.time()
        spider2 = Captch(proxy)
        mysqldb = Database()

        while not self.stop_flag:
            while not news_queue.empty():
                news_data = news_queue.get()
                
                title = translate(news_data['title'])
                flag = spider2.captch(title)
                news_data.update({
                    'title': title,
                    'compliance': flag
                    })
                
                mysqldb.insert(news_data)
            
            if time.time() - start_time > self.timeout:
                self.stop_flag = True
        
        mysqldb.close()
        print("百度验证线程-{}关闭.".format(self.name), end="")


def main():
    Pool_ = Thread_pool(Captch_Thread)
    News = News_Thread()
    print("开启新闻抓取线程")
    News.start()
    S_time = time.time()
    
    while True:
        if news_queue.qsize() > 20:
            print("开启百度验证线程池")
            Pool_.start()
        if News.is_alive() or Pool_.is_alive():
            time.sleep(5)
        else:
            break
    
    print("抓取结束，用时：{}, 3s后退出...".format(time.time() - S_time)
   time.sleep(3)

def Menmu():
    print("*"*50)
    print("*"+" "*48+"*")
    print("*"+" "*16+"联合新闻爬虫"+" "*17+"*")
    print("*"+" "*48+"*")
    print("*"*50)
    print(" "*50)

if __name__ == "__main__":
    Menmu()
    main()

