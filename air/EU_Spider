#! /usr/bin/env python
# -*- coding: utf-8 -*-
# http://eub2c.travelsky.com/euair

from pyspider.libs.base_handler import *
from pyspider.libs.utils import md5string
from pymongo import MongoClient
from datetime import timedelta
import datetime
import json
import time
import requests
import math

# client = MongoClient('mongodb://ip/')
client = MongoClient('mongodb://ip/')
db = client.mongoair
db.authenticate('passwd')


class Handler(BaseHandler):
    config_crawl = {}

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
                self.crawl('data:,step%d' % i, callback=self.get_url, age=40 * 60, auto_recrawl=False,
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
        Headers = {
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Origin': 'http://eub2c.travelsky.com',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'http://eub2c.travelsky.com/euair/index.jsp',
            'Accept-Encoding': 'gzip, deflate'
        }
        data = {
            'orgCity': 'CTU',
            'takeoffDate': '2018-09-23',
            'tripType': '0',
            'destCity': 'FOC',
            'returnDate': '2018-09-23',
            'adultNum': '1',
            'childNum': '0',
            'babyNum': '0',
            'x': '50',
            'y': '10'
        }
        url = 'http://eub2c.travelsky.com/euair/reservation/flightQuery.do'
        for query in query_list[num * 150: (num + 1) * 150]:
                dep, arr, date = query
                data.update({
                    'orgCity': dep,
                    'takeoffDate': date,
                    'destCity': arr,
                    'returnDate': date
                })
                self.crawl(url, headers=Headers, callback=self.detail_page, data=data, validate_cert=False,
                           method='POST', auto_recrawl=False, save={'query': query}, age=5 * 60)

    def detail_page(self, response):
        query = response.save['query']
        result = {
            "airline_country_type": "1",
            "carrier": "EU",
            "dep": query[0],
            "arr": query[1],
            "date": query[2],
            "data": [],
            "data2": [],
            "code": "1111",
            "message": "ok",
            "update": datetime.datetime.utcnow() + timedelta(hours=8)
        }
        if u'航班已销售完毕' in response.text:
            result.update({
                'code': '9999',
                'message': '当天没有航班'
            })
        elif u'<div class="right_item1">' in response.text:
            result.update({
                'code': '1000',
                'message': '航线不存在'
            })
        else:
            data, data2 = self.fetch_data(response.etree, query)
            result.update({
                'data': data,
                'data2': data2,
                'code': '1111' if data or data2 else '1002',
                'message': 'ok' if data or data2 else '抓取异常'
            })
        return result

    def on_result(self, result):
        if not result:
            return
        print(result)
        db.euair.insert(result)

    def get_query_list(self, num, start=None):  # 航线列表
        r = requests.get('http://data_api', timeout=15)  # 大陆
        r.encoding = 'utf-8'
        airlines = r.json()['data']
        # airlines = ['CTU-CAN', 'CTU-PVG']
        # print('airlines: ', airlines)
        query_list = []
        str_date_range = self.get_date_range(num=num, start=start)
        for line in airlines:
            for d in str_date_range:
                dep, arr = line.split('-')
                query_list.append((dep, arr, d))
        return query_list

    def get_date_range(self, num, start=0):  # 日期列表
        date_range = []
        start_day = datetime.datetime.utcnow() + timedelta(hours=8) + timedelta(days=start)
        for i in range(0, num):
            date_range.append(start_day + timedelta(days=i))
        str_date_range = [day.strftime('%Y-%m-%d') for day in date_range]
        return str_date_range

    @staticmethod
    def fetch_data(html, query):
        tbody = html.xpath('//table[@class="tab_result"]')
        flights = tbody[0].xpath('.//tr[@class="air_line"]')  # 航班列表
        data = []
        data2 = []
        for flight_info in flights:
            td = flight_info.xpath('./td')
            flag = td[4].text.strip()
            flight_no = td[1].text.strip()
            deptime, arrtime = td[2].text.split('-')
            depdate = query[2]
            # 处理时间，若到达时间为第二天，则将日期加一天
            if datetime.datetime.strptime(deptime, '%H:%M') > datetime.datetime.strptime(arrtime, '%H:%M'):
                tm = datetime.datetime.strptime(depdate, '%Y-%m-%d') + timedelta(days=1)
                arrdate = datetime.datetime.strftime(tm, '%Y-%m-%d')
            else:
                arrdate = depdate
            plane_style = td[3].text.strip()
            # 所有舱位信息
            cabin_list = td[5:-1]
            cabin_info_list = []
            for cabin_info in cabin_list:
                p = cabin_info.xpath('./text()')
                if not p or not ''.join(p).strip():
                    continue
                price = ''.join(p).strip()
                c_s = cabin_info.xpath('./span/text()')
                if not c_s or len(c_s) < 2:
                    continue
                cabin, seat = c_s
                cabin = cabin[0]
                seat = seat.replace('>', '')
                cabin_info_list.append({
                    'cabin': cabin,
                    'cabin_type': '',
                    'price': price,  # 总售价 float string
                    'base_price': '',  # 不含税价
                    'surcharges_adt': '',  # 附加费
                    'tax_adt': '',  # 税
                    'ticket_remain': seat,  # 余票数
                    'tax_fees': '',  # 税费总额
                    'currency': 'CNY',  # 币种
                })
            # price = td[-2].xpath('./text()')[3].strip()
            # cabin, seat = td[-2].xpath('./span/text()')
            data.append({
                'carrier': flight_no[:2],
                'flight_no': flight_no,
                'dep': query[0],
                'arr': query[1],
                'plane_style': plane_style,
                'depdate': depdate,
                'deptime': deptime,
                'arrdate': arrdate,
                'arrtime': arrtime,
                'flag': flag,
                'main_flight_no': '',
                'cabin_infolist': cabin_info_list
                # 'cabin_infolist': [{
                #     'cabin': cabin[0],
                #     'cabin_type': '',
                #     'price': str(price),  # 总售价 float string
                #     'base_price': '',  # 不含税价
                #     'surcharges_adt': '',  # 附加费
                #     'tax_adt': '',  # 税
                #     'ticket_remain': seat.replace('>', ''),  # 余票数
                #     'tax_fees': '',  # 税费总额
                #     'currency': 'CNY',  # 币种
                # }]
            })
        return data, data2
