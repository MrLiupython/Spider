# -*- coding:utf-8 -*-

import requests
import json
import re
import time
import sys
Data_dict = {}
Index = 0
Base_url = "https://www.instagram.com/ahmad_monk/"
Query_url = "https://www.instagram.com/graphql/query/"
Params = {
    "query_hash":"76d9c5f9c2d88aa251ece9ea61fdc570",
    "variables":{
        "id":"22543622",
        "after":""
        }
    }
Params2 = {
    "q":[{"page_id":"pmkx2k","posts":[["qe:expose",{"qe":"stories_lo","mid":"WyEPiQAEAAEsuy3zUVWvFH8_6KpW"},int(time.time()*1000),0]],"trigger":"qe:expose","send_method":"ajax"}],
    "ts":int(time.time()*1000)
    }
Headers = {
        "User-Agent" : "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0",
        "Host":"www.instagram.com",
        "Referer":"https://www.instagram.com/ahmad_monk/",
        "X-Instagram-GIS": "3d7c7db6c011a62b86371cc9205e65db"
        }
Test = 0
s = requests.Session()
def get_first_data(response):
    h = re.compile('"edge_owner_to_timeline_media":.*{"has_next_page":(.*?),"end_cursor":"(.*?)"').findall(response)
    assert h
    has_next,end_cursor = h[0]
    urls = re.compile('"display_url":"(.*?)"').findall(response)#123 678
    edge_liked = re.compile('"edge_liked_by":{"count":(.*?),').findall(response)
    comment_num = re.compile('"edge_media_to_comment":{"count":(.*?),').findall(response)
#    print(edge_liked,comment_num)
    save_first_data(urls,edge_liked,comment_num)
    return has_next,end_cursor
def get_data(response):
    data_ = response["data"]["user"]["edge_owner_to_timeline_media"]
    has_next = data_["page_info"]["has_next_page"]
    end_cursor = data_["page_info"]["end_cursor"]
    for data in data_["edges"]:
        url = data["node"]["display_url"]
        edge_liked = data["node"]["edge_media_preview_like"]["count"]
        comment_num = data["node"]["edge_media_to_comment"]["count"]
        save_data(url,edge_liked,comment_num)
    return has_next,end_cursor
def save_first_data(urls,edge_liked,comment_num):
    global Index,Data_dict
    i,j,k = 0,0,0
    while k < 12:
        if j > 2:
            i += 3
            j = 0
        Data_dict[Index] = {"url":urls[i],"likes":edge_liked[k],"comment_num":comment_num[k]}
        i += 1
        j += 1
        k += 1
        Index += 1
def save_data(url,edge_liked,comment_num):
    global Index,Data_dict
    Data_dict[Index] = {"url":url,"likes":edge_liked,"comment_num":comment_num}

if __name__ == "__main__":
    status = s.post("https://www.instagram.com/ajax/bz",headers=Headers,data=Params2)
    print(status.status_code)
    response = s.get(Base_url,headers=Headers).text
    assert len(response) > 0
    time.sleep(2)
    has_next,end_cursor = get_first_data(response)
    while has_next == "true":
        Params["variables"]["after"] = end_cursor
        try:
            response = s.get(Query_url,headers=Headers,params=Params).json()
        except Exception as e:
            print(str(e))
            sys.exit()
        time.sleep(2)
        has_next,end_cursor = get_data(response.json())
        Text += 1
        if Test > 2:
            break
    with open("data.json","w") as fp:
        fp.write(json.dumps(Data_dict))
        print("OK")
