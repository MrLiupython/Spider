#c -*- oding:utf-8 -*-
#--------------------------------------------------------
#    程序: yld_v4.py
#    版本: 0.4
#    日期：2018/5/13
#    Python：3.6.3
#    操作: python yld_v4.py
#    功能：从翼龙贷网站采集借款人信息并保存在yld.xls
#--------------------------------------------------------

import requests
import threading
import time
import xlwt
import sys
from queue import Queue

Post_queue = Queue()   #存储POST任务参数的队列
Rep_queue = Queue()    #存储返回Reponse的队列
Data_queue = Queue()   #存储最终数据的队列
Temp_book = None       #保存book对象，防止写入数据时出错，数据丢失
Start_flag = False     #信息保存线程开启/关闭的控制标志
Init_flag = False      #xls文件是否初始化的标志
URL = "https://licai.eloancn.com/pcgway/gateway/v1/01"
Headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 6.1; Win64;x64;rv:58.0) Gecko/20100101 Firefox/58.0",
    "Host":"licai.eloancn.com",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf8"
    }
#线程池管理类，用于网络IO线程
class Thread_pool:
    def __init__(self,thread_name,thread_num=10):
        self.num = thread_num
        self.thread_name = thread_name
        self._pool = [self.thread_name(i+1) for i in range(self.num)]
    def on(self):
        for i in self._pool:
            i.start()
    def is_alive(self):#判断线程池所有线程是否存活
        for i in self._pool:
            if i.is_alive():
                return True
        return False
#网络IO线程
class IO_Thread(threading.Thread):
    def __init__(self,name=1,timeout=20):
        super().__init__()
        self.name = name
        self.daemon = True
        self.stop_flag = False     #线程关闭控制标志
        self.time_out = timeout    #time_out是线程空闲的超时时间，超过超时时间，线程结束
    def run(self):
        start_time = time.time()   #线程开始时间
        while not self.stop_flag:
            while not Post_queue.empty():
                data,step,kind = Post_queue.get()
                if step == 0:
                    reponse = requests.post(URL,headers=Headers,data=data).json()
                    step += 1
                    Rep_queue.put((reponse,step,kind))
                elif step == 1 or step == 2:
#                    sys.exit()
                    reponse = requests.post(URL,headers=Headers,data=data[0]).json()
                    step += 1
                    Rep_queue.put(([reponse,data[1],data[2],data[3]],step,kind))
                else:
                    assert "step error!"
                time.sleep(1)
                start_time = time.time()                  #每发送一次POST就刷新线程开始时间
            if time.time()-start_time > self.time_out:    #判断线程空闲时间
                self.stop_flag = True
        print("网络IO线程-{}关闭.".format(self.name),end="")
        
#处理返回的response对象（json格式)线程
class Handle_Thread(threading.Thread):
    def __init__(self,timeout=20):
        super().__init__()
        self.daemon = True
        self.stop_flag = False    #线程关闭控制标志
        self.time_out = timeout   #time_out是线程空闲的超时时间，超过超时时间，线程结束
    def run(self):
        start_time = time.time()
        while not self.stop_flag:
            while not Rep_queue.empty():
                data,step,kind = Rep_queue.get()
                Add_to_queue(data,step,kind)    #将IO任务添加Post_queue/Data0(1)_queue队列
                start_time = time.time()        #处理一次任务就刷新线程开始时间
            if time.time()-start_time > self.time_out:
                self.stop_flag = True
        print("处理线程关闭",end="")
        
#保存信息的线程，若想信息保存方式为其他方式，可修改此类
class Save_Thread(threading.Thread):
    def __init__(self,timeout=20):
        super().__init__()
        self.daemon = True
        self.stop_flag = False
        self.time_out = timeout
        self.row = 1     #信息要导入的表格位置（行）
        self._queue = Data_queue
    def run(self):
        global Temp_book,Start_flag,Init_flag
        book = xlwt.Workbook(encoding="utf-8")    #创建xls文件对象，
        sheet = book.add_sheet("翼龙贷")          
        if not Init_flag:    #初始化xls文件
            Init_sheet(sheet)
            Load_index(sheet)
        start_time = time.time()
        while not self.stop_flag:
            try:
                while not self._queue.empty():
                    data = self._queue.get()
                    self.row = Save_xls(data,self.row,sheet,book)#写入数据，并更新信息要导入的表格位置
                    Temp_book = book
                    start_time = time.time()
                Temp_book = book
                if time.time()-start_time > self.time_out:
                    self.stop_flag = True
            except:#出错时，及时保存已写信息
                if Temp_book:
                    Temp_book.save("yld.xls")
        book.save("yld.xls")
        Start_flag = False
        print("信息保存于：yls.xls,信息保存线程关闭.",end="")
        
#将IO任务添加Post_queue/Data_queue队列                
def Add_to_queue(data,step,kind):
    if kind:#翼农计划
        if step == 1:    #获取pid
            data2 = {
                'pageNo': 1,
                'requesturl': 'IjE9HTj42YWoZVeH5M3LwlnldpmC7Qbc'
                }
            try:#当要爬取的产品列表页数小于你想爬取的页数时，for循环会出错（data["data"]["data"]:None），吞掉该异常使程序正常运行下去
                for i in data["data"]["data"]:
                    days = i["strPhases"]
                    lv = i["strInterestrate"]
                    title = i["title"]
                    data2["pid"] = i["id"]
                    Post_queue.put(([dict(data2),days,lv,title],step,kind))#此处必须用dict创建data2的副本，因为data2引用为可变对象
            except:
                pass
        elif step == 2:   #获取id
            data2 = {
                'mark': 2,
                'platform': 5,
                'requesturl': 'AqeXfFgEApnttSuMj1r7BaBklHUjMROZ',
                'v': 0.29441846044222364
                }
            for i in data[0]["data"]["data"]:
                data2["id"] = i["id"]
                Post_queue.put(([dict(data2),data[1],data[2],data[3]],step,kind))#此处必须用dict创建data2的副本，因为data2引用为可变对象
        elif step == 3:
            Data_queue.put(data)
        else:
            assert "kind:{} step:{} error.".format(kind,step)
    else:#芝麻开门
        if step == 1:    #获取prodDetail
            data2 = {
                "pageNo":1,
                "platform":5,
                "requesturl":"dtAouQWbsDjA1WICWhCBIEUjayw38KOk",
                "v":0.752217507561683
                }
            try:#当要爬取的产品列表页数小于你想爬取的页数时，for循环会出错（data["data"]["data"]:None），吞掉该异常使程序正常运行下去
                for i in data["data"]["list"]:
                    days = i["investPeriod"]
                    lv = i["minRate"]+"-"+i["maxRate"]+"%"
                    title = i["title"]
                    data2["prodDetail"] = i["prodDetail"]
                    Post_queue.put(([dict(data2),days,lv,title],step,kind))#此处必须用dict创建data2的副本，因为data2引用为可变对象
            except:
                pass
        elif step == 2:  #获取enTenderId
            data2 = {
                "mark":2,
                "platform":5,
                "requesturl":"AqeXfFgEApnttSuMj1r7BaBklHUjMROZ",
                "v":0.6164977597280228
                }
            for i in data[0]["data"]["list"]:
                data2["id"] = i["enTenderId"]
                Post_queue.put(([dict(data2),data[1],data[2],data[3]],step,kind))#此处必须用dict创建data2的副本，因为data2引用为可变对象
        elif step == 3:
            Data_queue.put(data)
        else:
            assert "kind:{} step:{} error.".format(kind,step)
#初识化表格宽度
def Init_sheet(sheet):
    sheet.col(2).width = 4000
    sheet.col(3).width = 3000
    sheet.col(4).width = 6000
    sheet.col(7).width = 6000
    sheet.col(8).width = 8000
    print("初始化表格成功！",end="")
#导入索引
def Load_index(sheet):
    sheet.write(0,0,"姓名")
    sheet.write(0,1,"年龄")
    sheet.write(0,2,"学历")
    sheet.write(0,3,"婚姻")
    sheet.write(0,4,"职业状况")
    sheet.write(0,5,"信用等级")
    sheet.write(0,6,"贷款金额")
    sheet.write(0,7,"年收入")
    sheet.write(0,8,"房产状况")
    sheet.write(0,9,"预期年化利率")
    sheet.write(0,10,"贷款期限")
    sheet.write(0,11,"计划期号")
    print("导入索引成功！",end="")

#信息导入xls文件
def Save_xls(data,row,sheet,book):
    name = data[0]["data"]["realName"]
    age = data[0]["data"]["age"]
    jycd = data[0]["data"]["jycd"]
    hyzk = data[0]["data"]["hyzk"]
    industry = data[0]["data"]["industry"]+"("+data[0]["data"]["gznx"]+")" if data[0]["data"]["industry"] and data[0]["data"]["gznx"] else ""
    Level = data[0]["data"]["finalLevel"]
    amount = data[0]["data"]["amount"]
    nsr = data[0]["data"]["nsr"]
    fc = data[0]["data"]["fc"]
    days = data[1]
    lv = data[2]
    title = data[3]
    sheet.write(row,0,name)
    sheet.write(row,1,age)
    sheet.write(row,2,jycd)
    sheet.write(row,3,hyzk)
    sheet.write(row,4,industry)
    sheet.write(row,5,Level)
    sheet.write(row,6,amount)
    sheet.write(row,7,nsr)
    sheet.write(row,8,fc)
    sheet.write(row,9,lv)
    sheet.write(row,10,days)
    sheet.write(row,11,title)
    return row+1

#主进程逻辑
def main():
    Kind = input("输入爬取的产品列表（输入数字）:0 芝麻开门 1 翼农计划 01 全部").replace(" ","")
    while Kind not in ["0","1","01"]:
        print("输入不对,只允许输入:0,1,01.")
        Kind = input("输入爬取的产品列表（输入数字）:0 芝麻开门 1 翼农计划 01 全部").replace(" ","")
    if "0" in Kind:    #芝麻开门
        pages0 = input("[芝麻开门] - 爬取多少页？").replace(" ","")
        while not pages0.isdigit():
            print("输入的不是数字，只允许输入数字.")
            pages0 = input("[芝麻开门] - 爬取多少页？").replace(" ","")
        pages0 = int(pages0)
        step0 = 0
        kind0 = 0
        data0 = {
            "platform":5,
            "requesturl":"dtAouQWbsDjKac4I44if40Ujayw38KOk?v=123",
            "v":0.4243501500123188
            }
        for page in range(pages0):
            data0["pageNo"] = page + 1
            Post_queue.put((dict(data0),step0,kind0))#此处必须用dict创建data0的副本，因为data0引用为可变对象
    if "1" in Kind:    #翼农计划
        pages1 = input("[翼农计划] - 爬取多少页?").replace(" ","")
        while not pages0.isdigit():
            print("输入的不是数字，只允许输入数字.")
            pages1 = input("[翼农计划] - 爬取多少页？").replace(" ","")
        pages1 = int(pages1)
        step1 = 0
        kind1 = 1
        data1 = {
            "platform":5,
            "requesturl":"IjE9HTj42YUib_sYkABPPFnldpmC7Qbc",
            "v":0.4797244526462968
            }
        for page in range(pages1):
            data1["pageNo"] = page + 1
            Post_queue.put((dict(data1),step1,kind1))#此处必须用dict创建data1的副本，因为data1引用为可变对象
#    sys.exit()
    S_time = time.time()    #线程开始的时间，用于计算程序的用时
#    IO = IO_Thread()
    Pool_ = Thread_pool(IO_Thread)
    Handle = Handle_Thread()
    Save = Save_Thread()
#    print("开启网络IO线程.")
#    IO.start()
    print("开启网络IO线程池.")
    Pool_.on()
    print("开启处理线程.")
    Handle.start()
    while True:
        if Data_queue.qsize() > 20 and not Start_flag:#信息保存任务超过20个时，开启信息保存线程池
            print("开启信息保存线程.")
            Save.start()
#        if IO.is_alive() or Handle.is_alive() or Save.is_alive():
#            print("网络IO线程:{}-{}\n处理线程:{}-{}\n信息保存线程:{}-{}".format(IO.is_alive(),Post_queue.qsize(),Handle.is_alive(),Rep_queue.qsize(),Save.is_alive(),Data_queue.qsize()))
        #当所有线程都不存活时，任务完成，跳出循环
        if Pool_.is_alive() or Handle.is_alive() or Save.is_alive():
            print("网络IO线程池：{}-{}\n处理线程：{}-{}\n信息保存线程：{}-{}".format(Pool_.is_alive(),Post_queue.qsize(),\
                                                                   Handle.is_alive(),Rep_queue.qsize(),Save.is_alive(),\
                                                                   Data_queue.qsize()))
            time.sleep(5)
        else:
            break
    print("爬取结束,用时:{}，3s后退出。。。".format(time.time()-S_time))
    time.sleep(3)

def Menmu():
    print("*"*50)
    print("*"+" "*48+"*")
    print("*"+" "*16+"翼龙贷数据爬虫v4"+" "*17+"*")
    print("*"+" "*5+"多线程爬虫，有点暴力哦，大家为服务器默哀"+" "*5+"*")
    print("*"+" "*48+"*")
    print("*"*50)
    print(" "*50)

if __name__ == "__main__":
    Menmu()
    try:
        main()
    except Exception as e:
        print(str(e))
        time.sleep(3)
