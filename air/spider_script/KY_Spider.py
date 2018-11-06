#! /usr/bin/env python
# -*- coding : utf-8 -*-
# Projext : kmair
from pyspider.libs.base_handler import *
from datetime import timedelta
import datetime
import requests
from pymongo import MongoClient
import json
import math

# client = MongoClient('mongodb://ip/')  # 本地测试
client = MongoClient('mongodb://ip/')
db = client.mongoair
db.authenticate('passwd')

headers = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Host': 'wap.airkunming.com',
    'Origin': 'http://wap.airkunming.com',
    'Pragma': 'no-cache',
 #   'Upgrade-Insecure-Requests': '1',
    "Referer": "http://wap.airkunming.com/reservation",
    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; SAMSUNG SM-G930F Build/MMB29K) AppleWebKit/537.36 (KHTML, like '
                  'Gecko) SamsungBrowser/4.0 Chrome/44.0.2403.133 Mobile Safari/537.36',
}


class Handler(BaseHandler):
    crawl_config = {

    }

    @every(minutes=40)
    def on_start(self):
        current = datetime.datetime.utcnow() + timedelta(hours=8)
        # 一天内抓取的时间
        fetch_time = 12
        # start天后开始抓取，
        query_list = self.get_query_list(num=30, start=3)
        if 8 <= current.hour < 8 + fetch_time:
            for i in range(int(math.ceil(len(query_list) / 150.0))):
                self.crawl('data:,step%d' % i, callback=self.get_json, age=30 * 60, auto_recrawl=False,
                           save={'num': i})
        elif current.hour >= 8 + fetch_time:
            for i in range(int(math.ceil(len(query_list) / 150.0))):
                self.crawl('data:,step%d' % i, age=40 * 60, auto_recrawl=False, cancel=True,
                           force_update=True, save={'num': i})
        else:
            pass

    def get_json(self, response):
        query_list = self.get_query_list(num=30, start=3)
        num = response.save['num']
        url = "http://wap.airkunming.com/search/flight?depAirportCode={0}&arrAirportCode={1}" \
              "&depDate={2}&tripType=OW&returnDate={2}"
        for query in query_list[num * 150: (num + 1) * 150]:
            dep, arr, date = query
            self.crawl(url.format(dep, arr, date), headers=headers, callback=self.detail_page, save={"query": query},
                       age=5 * 60)

    def detail_page(self, response):
        html = response.json
        query = response.save['query']
        result = {
            "carrier": 'KY',
            "dep": query[0],
            "arr": query[1],
            "date": query[2],
            "data": [],
            "data2": [],
            "code": "0000",
            "message": "0000",
            "airline_country_type": "1",  # "2"
            "update": datetime.datetime.utcnow() + timedelta(hours=8)
        }
        errormessage = html.get(u"errorMessage")
        if errormessage:
            print(html)
            if u'\u822a\u73ed\u67e5\u8be2\u5931\u8d25:av\u7ed3\u679c\u4e2d\u672a\u67e5\u5230\u7b26\u5408\u7684\u822a\u73ed\u4fe1\u606f\u3002' in errormessage:
                result.update({
                    "code": "9999",
                    "message": "当天没有航班",
                })
            elif u'\u822a\u73ed\u8fc7\u6ee4\u4e2d\u672a\u67e5\u5230' in errormessage:
                result.update({
                    'code': '1000',
                    'message': '航线不存在'
                })
            elif u'\u7cfb\u7edf\u5f02\u5e38\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5' in errormessage:
                # response.status_code = 501
                # response.raise_for_status()
                result.update({
                    'code': '1234',
                    'message': '官网系统异常，可能该航线有问题'
                })
            else:
                print('未知异常，{}'.format(errormessage))
        else:
            data = self.fetch_data(html, query)
            result.update({
                'data': data,
                'code': '1111' if data else '1002',
                'message': 'ok' if data else '抓取异常'
            })
        return result

    def on_result(self, result):
        if not result:
            return
        print(result)
        super(Handler, self).on_result(result)
        db.kyair.insert(result)

    def get_query_list(self, num, start=None):  # 航线列表 
        r = requests.get('http://data_api', timeout=10)
        r.encoding = 'utf-8'
        airlines = r.json()['data']['first']
        print('airlines: ', airlines)
        query_list = []
        str_date_range = self.get_date_range(num=num, start=start)
        for line in airlines:
            for d in str_date_range:
                dep, arr = line.split('-')
                query_list.append((dep, arr, d))
        return query_list

    @staticmethod
    def get_date_range(num, start=None):  # 日期列表
        date_range = []
        start_day = datetime.datetime.utcnow() + timedelta(hours=8) + timedelta(days=start)
        for i in range(0, num):
            date_range.append(start_day + timedelta(days=i))
        str_date_range = [day.strftime('%Y-%m-%d') for day in date_range]
        return str_date_range

    @staticmethod
    def fetch_data(html, query):
        dep, arr, date = query
        data = []
        segement_list = html.get(u"data")[0].get(u'segmentList')
        print(segement_list)
        for segment in segement_list:
            cabin_list = []
            flight_no = segment.get(u'marketingFlightNo', "")  # 营销航班号
            flight_no_opr = segment.get(u'operatingFlightNo')  # 操作航班号
            style = segment.get(u"airCraftStyle", "")  # 机型
            depdatetime = segment.get(u"depDateTime", "")  # 出发时间
            depdate, deptime = depdatetime.split()
            arrdatetime = segment.get(u"arrDateTime", "")  # 到达时间
            arrdate, arrtime = arrdatetime.split()
            cabin_list_ = segment.get(u'cabinList')
            for cabinitem in cabin_list_:
                cabin = cabinitem.get(u'cabinCode')  # 舱位代号
                cabin_name = cabinitem.get(u'cabinName')  # 舱名
                price = str(cabinitem.get(u'productList')[0].get(u'priceList')[0].get(u'salePrice'))  # 价格
                ticket_remain = cabinitem.get(u'inventory')  # 若为 A 则表示票数充足，若为数字，则是剩余票数
                ticket_remain = ticket_remain if ticket_remain != "A" else "99"
                cabin_list.append({
                    "cabin": cabin,
                    "cabin_type": cabin_name,
                    "price": price,
                    "ticket_remain": ticket_remain,
                    "base_price": "",
                    "surcharges_adt": "",
                    "tax_adt": "",
                    "tax_fees": "",
                    "currency": "CNY"
                })
            if not cabin_list:
                continue
            data.append({
                "carrier": "KY",
                "flight_no": flight_no,
                "dep": dep,
                "depdate": depdate,
                "deptime": deptime,
                "arr": arr,
                "arrdate": arrdate,
                'arrtime': arrtime,
                "cabin_infolist": cabin_list,
                "plane_style": style,
                "main_flight_no": flight_no_opr
            })
        return data
