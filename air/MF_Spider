#! /usr/bin/env python
# -*- coding: utf-8 -*-
# https://m.xiamenair.com 国内

from pyspider.libs.base_handler import *
from pyspider.libs.utils import md5string
from datetime import timedelta
import datetime
from pymongo import MongoClient
import json
import requests
import math

# client = MongoClient('mongodb://ip/')  # 本地测试
client = MongoClient('mongodb://ip/')
db = client.mongoair
db.authenticate('passwd')


class Handler(BaseHandler):
    crawl_config = {}

    def get_taskid(self, task):
        return md5string(
            task['url'] + json.dumps(task['fetch'].get('data', '')) + json.dumps(task['fetch'].get('params', '')))

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
        query_list = self.get_query_list(num=30, start=3)
        num = response.save['num']
        headers = {
            'Origin': 'https://m.xiamenair.com',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Referer': 'https://m.xiamenair.com/wxjweb/ticketBooking',
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive'
        }
        url = 'https://m.xiamenair.com/wxjweb/flightSearch/getFlightList'
        for query in query_list[num * 150: (num + 1) * 150]:
            data = {"tripType": "OW",
                    "segments": [{"org": query[0], "dst": query[1], "beginDepartDate": query[2], "endDepartDate": query[2]}],
                    "isDeirect": True,
                    "carriers": ["MF"]}
            self.crawl(url, headers=headers, validate_cert=False, data=json.dumps(data), callback=self.detail_page,
                       age=5 * 60, method='POST', save={'query': query})

    def detail_page(self, response):
        doc = json.loads(response.json)
        query = response.save['query']
        result = {
            "carrier": "MF",
            "dep": query[0],
            "arr": query[1],
            "date": query[2],
            "data": [],
            "data2": [],
            "code": "0000",
            "message": "0000",
            "airline_country_type": "1",
            "update": datetime.datetime.utcnow() + timedelta(hours=8)
        }
        if not doc.get('result').get('flightSearchItemList'):
            result.update({
                'code': '1000',
                'message': '该航线不存在'
            })
        else:
            _, airline_list = doc.get('result').get('flightSearchItemList').popitem()
            if not airline_list:
                result.update({
                    'code': '9999',
                    'message': '当天没有航班'
                })
            else:
                data = self.fetch_data(airline_list)
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
        db.mfair.insert(result)

    def get_query_list(self, num, start=None):  # 航线列表
        r = requests.get('http://data_api', timeout=15)  # 大陆
        r.encoding = 'utf-8'
        airlines = r.json()['data']
        # airlines = ['XMN-HGH']
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
    def fetch_data(airline_list):
        data = []
        for airline in airline_list:
            arr = airline['dst']
            dep = airline['org']
            depdate = airline['takeoffDate']
            arrdate = airline['arrivalDate']
            dep_time = airline['takeoffTime']
            arr_time = airline['arrivalTime']
            carrier = airline['carrier']
            flight_no = airline['flightNumber']
            main_flight_no = airline['operatingFlightNumber']
            plane_style = airline['aircraftType']
            cabin_list = airline['cabinInfos']
            flight_dict = {
                'carrier': carrier,
                'flight_no': flight_no,
                'main_flight_no': main_flight_no,
                'dep': dep,
                'arr': arr,
                'depdate': depdate,
                'arrdate': arrdate,
                'deptime': dep_time,
                'arrtime': arr_time,
                'plane_style': plane_style,
                'cabin_infolist': []
            }
            for cabin_info in cabin_list:
                price = str(int(cabin_info['amount']))
                currency = cabin_info['currency']
                cabin = cabin_info['cabin']
                cabin_name = cabin_info['description']
                ticket_remain = cabin_info['cabinNum']
                if ticket_remain == 'A':
                    ticket_remain = '99'
                flight_dict['cabin_infolist'].append({
                    'cabin': cabin,
                    'cabin_type': cabin_name,
                    'base_price': '',
                    'surcharges_adt': '',
                    'tax_adt': '',
                    'price': price,
                    'ticket_remain': ticket_remain,
                    'tax_fees': '',
                    'currency': currency
                })
            data.append(flight_dict)
        return data
