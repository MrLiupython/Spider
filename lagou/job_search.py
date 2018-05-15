import requests
import json
from queue import Queue
import csv
import time
import sys
import random
class Jobs:
    headers = {
            "User-Agent":"Mozilla/5.0 (Windows NT 6.1; Win64;x64;rv:58.0) Gecko/20100101 Firefox/58.0",
            "Host": "www.lagou.com",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded;charset=utf8",
            "Content-Length": "25"
            }
    def __init__(self,search_data=None):
        self.url = "https://www.lagou.com/jobs/positionAjax.json"
        self.headers["Referer"] = "https://lagou.com/jobs/list_{}".format(search_data)
        self.data_queue = Queue()
        self.forms = {"first":False,"kd":search_data,"pn":1}
        self.params = {"needAddtionResult":False}
        self._data = []
        self.search_data = search_data
    def test(self):
        print("This test...")
        r = requests.post(self.url,headers=self.headers,data=self.forms,params=self.params)
        if r.json()['success']:
            print(r.json()['content']['positionResult']['result'][0]['companyShortName'])
        else:
            print(r.json())
    def get_data(self):
        for i in range(31):
            self.forms["pn"] = i
            response = requests.post(self.url,headers=self.headers,data=self.forms,params=self.params)
            if not response.json()["success"]:
                print("{} page stop!".format(i))
                print(response.json())
                break
            self.data_queue.put(response.json())
            if i%5 == 0:
                sleep_time = random.randrange(60,65)
                print("Get 5 page,then sleep {}s...".format(sleep_time))
                time.sleep(sleep_time)
        print("get {}s".format(self.data_queue.qsize()))
    def get_dict(self):
        if not len(self._data):
            while not self.data_queue.empty():
                data = self.data_queue.get()
                try:
                    results = data["content"]["positionResult"]["result"]
                    for i in results:
                        name = i["positionName"]
                        money = i["salary"]
                        city = i["city"]
                        company = i["companyShortName"]
                        education = i["education"]
                        workyear = i["workYear"]
                        self._data.append({"name":name,"city":city,"money":money,"company":company,"education":education,"workyear":workyear})
                except Exception as e:
                    print("data error:",e)
                    break
            print("data_queue is empty!")
        else:
            print("Had get data")
    def save_csv(self):
        self.get_dict()
        with open("jobs_{}.csv".format(self.search_data),"a",encoding="utf-8",newline='') as fp:
            field = ["name","city","money","education","workyear","company"]
            writer = csv.DictWriter(fp,fieldnames=field)
            writer.writeheader()
            for i in self._data:
                writer.writerow(i)
        print("save to jobs_{}.csv.".format(self.search_data))
    def save_json(self):
        self.get_dict()
        with open("jos_{}.json".format(self.search_data),"a",encoding="utf-8") as fp:
            fp.write(json.dumps(self._data))
        print("save to jobs_{}.json".format(self.search_data))
if __name__ == "__main__":
    print("*"*30)
    search = input("What job do you want to know?(quit to stop)\n")
    while(search.strip() != "quit"):
        jobs = Jobs(search.strip())
        jobs.get_data()
        jobs.save_csv()
#        jobs.test()
        search = input("What job do you want to know?(quit to stop)\n")
    print("quit...")
    time.sleep(3)
