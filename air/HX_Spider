# !/usr/bin/env python
# -*- encoding: utf-8 -*-
# Project: hongkongairlines
# TODO:货币非CNY
from pyspider.libs.base_handler import *
import datetime
from datetime import timedelta
import requests
from pymongo import MongoClient
import math

# client = MongoClient('mongodb://ip/')  # 本地测试
client = MongoClient('mongodb://ip/')
db = client.mongoair
db.authenticate('passwd')

headers = {
    'Host': 'm.hongkongairlines.com',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
    # 'Referer': 'https://m.hongkongairlines.com/html/ticket/list_new.html?startcity=NRT&endcity=HKG&date=2018-06-09&flighttype=OW&cabintype=E&adultnum=1&childnum=0',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'Authority': 'm.hongkongairlines.com'
}


class Handler(BaseHandler):
    crawl_config = {
        "itag": "v0.1",
        "retries": 1,
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
                self.crawl('data:,step%d' % i, callback=self.get_url, age=40 * 60, auto_recrawl=True,
                           save={'num': i})
        elif current.hour >= 8 + fetch_time:
            for i in range(int(math.ceil(len(query_list) / 150.0))):
                self.crawl('data:,step%d' % i, age=40 * 60, auto_recrawl=False, cancel=True,
                           force_update=True, save={'num': i})
        else:
            pass

    def get_url(self, response):
        # url_list = [
        #     "https://m.hongkongairlines.com/ci/index.php/fffticket/search_new?startcity=NRT&endcity=HKG&date=2018-07-09&flighttype=OW&cabintype=E&adultnum=1&childnum=0&brandIndex=null&email=null&ctoke=&currencyType=",
        #     "https://m.hongkongairlines.com/ci/index.php/fffticket/search_new?startcity=NRT&endcity=HKG&date=2018-07-19&flighttype=OW&cabintype=E&adultnum=1&childnum=0&brandIndex=null&email=null&ctoke=&currencyType="
        # ]
        query_list = self.get_query_list(num=30, start=3)
        num = response.save['num']
        for query in query_list[num * 150: (num + 1) * 150]:
            dep, arr, dep_date = query
            print('query: ', query)
            url = "https://m.hongkongairlines.com/ci/index.php/fffticket/search_new \
             ?startcity={}&endcity={}&date={}&flighttype=OW&cabintype=E&adultnum=1& \
             childnum=0&brandIndex=null&email=null&ctoke=&currencyType=".format(dep, arr, dep_date)
            self.crawl(url, callback=self.detail_page, headers=headers, validate_cert=False, save={'query': query},
                       age=5 * 60)

    def detail_page(self, response):
        dep_date = response.save['query'][2]
        dep = response.save['query'][0]
        arr = response.save['query'][1]
        result = {
            "airline_country_type": "1",  # "3" "2",
            "carrier": "HX",
            "dep": dep,
            "arr": arr,
            "date": dep_date,
            "data": [],
            "data2": [],
            "message": "",
            "code": '0000',
            "update": datetime.datetime.utcnow() + timedelta(hours=8)
        }
        print("开始抓取详情页")
        doc = response.json
        print(doc)
        if doc.get('code') == u'9999':
            print('进入9999')
            result.update({
                "message": "此航线当前没有该类型的舱位",
                "code": '9999'
            })
        elif doc.get('code') == u'1000':
            result.update({
                "message": "香港航空查询异常，可能是航线不存在、日期异常或者是香港航空的负载问题，如果确认航线存在，请稍后再试",
                "code": '1000',
            })
        else:
            result.update({
                "data": self.fetch_price(doc),
                "code": '1111',
                "message": "ok",
            })
        return result

    def on_result(self, result):
        print("数据存储")
        if not result:
            return
        print(result)
        # conn.set(result['update'], json.dumps(result), ex=1200)
        super(Handler, self).on_result(result)
        db.hxair.insert(result)

    def fetch_price(self, html):
        print("开始解析价格")
        flight_data_list = []
        for flight in html.get('airItems'):
            flight_data = {'cabin_infolist': []}
            extend_data = {}
            for ele in flight.get('cabins'):
                flight_no = ele['operateCarrier']

                cabin = ele['cabinCode']
                cabin_type = ele['seatClass']
                if cabin_type == 'E':
                    cabin_type = 'Economy'
                elif cabin_type == 'B':
                    cabin_type = 'BUSINESS'
                tktprice_adt = ele['wsFare']['baseAmount']
                surcharges_adt = ''
                tax_adt = ''
                tax_fees = round(float(ele['wsFare']['amount']) - float(ele['wsFare']['baseAmount']), 2)
                ticket_remain = ele['cabinNum']
                if ticket_remain == 'A':
                    ticket_remain = '99'
                currency = ele['wsFare']['currencyType']
                depdate, deptime = ele['takeoffDateTime'].split()
                arrdate, arrtime = ele['arrivalDateTime'].split()
                carrier = ele['airline']
                dep = ele['orgAirp']
                arr = ele['dstAirp']
                plane_style = ele['planeStyle']
                cabin_info = {
                    'cabin': cabin,
                    'cabin_type': cabin_type,
                    'tktprice_adt': tktprice_adt,
                    'surcharges_adt': surcharges_adt,
                    'tax_adt': tax_adt,
                    'price': '',
                    'ticket_remain': ticket_remain,
                    'tax_fees': str(tax_fees),
                    'currency': currency
                }

                extend_data = {
                    'carrier': carrier,
                    'flight_no': flight_no,
                    'dep': dep,
                    'depdate': depdate,
                    'deptime': deptime,
                    'arr': arr,
                    'arrdate': arrdate,
                    'arrtime': arrtime,
                    'plane_style': plane_style,
                    'main_flight_no': ''
                }

                flight_data['cabin_infolist'].append(cabin_info)
            flight_data.update(extend_data)
            flight_data_list.append(flight_data)
        return flight_data_list

    def get_query_list(self, num, start=None):  # 航线列表
        r = requests.get('http://data_api', timeout=15)  # 大陆
        r.encoding = 'utf-8'
        airlines = r.json()['data']
        # airlines = ['TNA-SZX', 'TNA-PEK', 'TNA-CTU']
        # airlines = ['PEK-SIN']
        # print('airlines: ', airlines)
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
