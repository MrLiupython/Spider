#! /usr/bin/env python
# -*- coding: utf-8 -*-
# SC

from pyspider.libs.base_handler import *
from pyspider.libs.utils import md5string
from pymongo import MongoClient
from datetime import timedelta
import requests
import datetime
import re
import json
import sys
import time
import hashlib
import math

# client = MongoClient('mongodb://ip')  # 本地测试
client = MongoClient('mongodb://ip/')
db = client.mongoair
db.authenticate('passwd')

ip = 'proxy'
port = 'port'
ip_port = ip + ":" + port


class Handler(BaseHandler):
    crawl_config = {
        "proxy": ip_port,
        "itag": "v2"
    }

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
                self.crawl('data:,step%d' % i, callback=self.post_page, age=40 * 60, auto_recrawl=False,
                           save={'num': i})
        elif current.hour >= 8 + fetch_time:
            for i in range(int(math.ceil(len(query_list) / 150.0))):
                self.crawl('data:,step%d' % i, age=40 * 60, auto_recrawl=False, cancel=True,
                           force_update=True, save={'num': i})
        else:
            pass

    @config(priority=1)
    def post_page(self, response):
        query_list = self.get_query_list(num=30, start=3)
        num = response.save['num']
        auth = self.get_proxy()
        for query in query_list[num * 150: (num + 1) * 150]:
            url1 = 'http://sc.travelsky.com/scet/queryAv.do'
            Headers1 = {
                'Connection': 'keep-alive',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache',
                'Origin': 'http://sc.travelsky.com',
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Referer': 'http://sc.travelsky.com/scet/airAvail.do',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Proxy-Authorization': auth
            }
            data1 = {
                'countrytype': '0',
                'travelType': '0',
                'cityNameOrg': '',
                'cityCodeOrg': query[0],
                'cityNameDes': '',
                'cityCodeDes': query[1],
                'takeoffDate': query[2],
                'returnDate': '',
                'cabinStage': '0',
                'adultNum': '1',
                'childNum': '0'
            }
            self.crawl(url1, headers=Headers1, data=data1, callback=self.post_page2, method='POST',
                       save={'query': query}, age=5 * 60)

    @config(priority=2)
    def post_page2(self, response):
        query = response.save['query']
        auth = self.get_proxy()
        cookies = response.cookies
        aid = re.search('<input type="hidden" name ="airAvailId" value="(.*?)"', response.text, re.DOTALL).group(1)
        url2 = 'http://sc.travelsky.com/scet/airAvail.do'
        Headers2 = {
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Origin': 'http://sc.travelsky.com',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'http://sc.travelsky.com/scet/queryAv.do',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Proxy-Authorization': auth
        }
        data2 = {
            'airAvailId': aid,
            'cityCodeOrg': query[0],
            'cityCodeDes': query[1],
            'cityNameOrg': '',  # '济南',
            'cityNameDes': '',  # '深圳',
            'takeoffDate': query[2],
            'travelType': '0',
            'countrytype': '0',
            'needRT': '0',
            'cabinStage': '0',
            'adultNum': '1',
            'childNum': '0'
        }
        self.crawl(url2, headers=Headers2, cookies=cookies, callback=self.detail_page, data=data2, method='POST',
                   save={'query': query}, age=5 * 60)

    @config(priority=3)
    def detail_page(self, response):
        # print(response.text)
        query = response.save['query']
        result = {
            "airline_country_type": "1",
            "carrier": "SC",
            "dep": query[0],
            "arr": query[1],
            "date": query[2],
            "data": [],
            "data2": [],
            "code": "1000",
            "message": "航线不存在",
            "update": datetime.datetime.utcnow() + timedelta(hours=8)
        }
        if u'请查询山航航班' in response.text:
            result.update({
                "code": "1000",
                "message": "航线不存在"
            })
        elif u'对不起，由于查询过于频繁，请稍后重试' in response.text:
            result.update({
                'code': '1032',
                'message': '查询过于频繁'
            })
        elif u'很抱歉，未查询到您所需的航班，请更换查询条件或联系客服95369' in response.text:
            result.update({
                "code": "9999",
                "message": "当天没有航班"
            })
        elif u'访问受限，需要帮助请拨打山航客服热线95369' in response.text or not response.text:
            response.status = 400
            response.raise_for_status()
            # result.update({
            #     "code": "1003",
            #     "message": "ip被封，请联系管理员"
            # })
        else:
            html = response.etree
            data1, data2 = self.fetch_data(html, query)
            result.update({
                "data": data1,
                "data2": data2,
                "code": "1111" if data1 or data2 else "1002",
                "message": "ok" if data1 or data2 else "抓取异常",
            })
        return result

    def on_result(self, result):
        if not result:
            return
        print(result)
        db.scair.insert(result)

    @staticmethod
    def get_proxy():
        _version = sys.version_info
        is_python3 = (_version[0] == 3)
        orderno = '****'
        secret = '****'
        timestamp = str(int(time.time()))
        string = "orderno=" + orderno + "," + "secret=" + secret + "," + "timestamp=" + timestamp
        if is_python3:
            string = string.encode()
        md5_string = hashlib.md5(string).hexdigest()
        sign = md5_string.upper()
        auth = "sign=" + sign + "&" + "orderno=" + orderno + "&" + "timestamp=" + timestamp
        return auth

    def get_query_list(self, num, start=None):  # 航线列表
        r = requests.get('http://data_api', timeout=15)  # 大陆
        r.encoding = 'utf-8'
        airlines = r.json()['data']
        # airlines = ['TNA-SZX', 'TNA-PEK', 'TNA-CTU']
        # airlines = ['TNA-SHA']
        # print('airlines: ', airlines)
        query_list = []
        str_date_range = self.get_date_range(num=num, start=start)
        for line in airlines:
            for d in str_date_range:
                dep, arr = line.split('-')
                query_list.append((dep, arr, d))
        return query_list

    def get_date_range(self, num, start=None):  # 日期列表
        date_range = []
        start_day = datetime.datetime.utcnow() + timedelta(hours=8) + timedelta(days=start)
        for i in range(0, num):
            date_range.append(start_day + timedelta(days=i))
        str_date_range = [day.strftime('%Y-%m-%d') for day in date_range]
        return str_date_range

    @staticmethod
    def fetch_data(html, query):
        data1, data2 = [], []
        flight_list = html.xpath('//div[@class="record record-prise"]/table')  # 航线列表
        for flight in flight_list:
            flight_info = {}
            plane_style = flight.xpath('.//div[@class="popup flight-content-info hidden-content"]/p[2]/text()')[0][3:]
            cabin_list = flight.xpath('.//td[@class="choose-cabintable"]')  # 舱位列表
            # print(len(cabin_list))
            for cabin_ in cabin_list:
                cabin_info = cabin_.xpath('.//div[@class="rdo-trigger"]')
                # print(len(cabin_info))
                if not cabin_info:
                    continue
                price = cabin_info[0].get('data-price')
                # print(price)
                dep_date = cabin_info[0].get('data-departuredatetime')
                depdate, deptime = dep_date.split()
                arr_date = cabin_info[0].get('data-arrivaldatetime')
                arrdate, arrtime = arr_date.split()
                carrier = cabin_info[0].get('data-airline')
                flight_no = carrier + cabin_info[0].get('data-flightnumber')
                cabin = cabin_info[0].get('data-classcode')
                tax = cabin_info[0].get('data-tax')
                ticket_remain = cabin_info[0].get('data-quantity').strip()
                ticket_remain = ticket_remain[0] if ticket_remain != u'充足' else '99'
                currency = cabin_.xpath('.//span[@class="choose-cabintable-pirce"]/sup/text()')[0]
                if flight_info.get(flight_no):
                    flight_info[flight_no]['cabin_infolist'].append({
                        'cabin': cabin,
                        'cabin_type': '',
                        'price': '',  # 总售价 float string
                        'base_price': price,  # 不含税价
                        'surcharges_adt': '',  # 附加费
                        'tax_adt': tax,  # 税
                        'ticket_remain': ticket_remain,  # 余票数
                        'tax_fees': '',  # 税费总额
                        'currency': currency,  # 币种
                    })
                else:
                    flight_info[flight_no] = {
                        'carrier': carrier,  # 承运航司
                        'flight_no': flight_no,  # 航班号
                        'dep': query[0],  # 出发机场
                        'deptime': deptime,
                        'depdate': depdate,  # 出发时间
                        'arr': query[1],  # 到达机场
                        'arrdate': arrdate,  # 抵达时间
                        'arrtime': arrtime,
                        'plane_style': plane_style,  # 机型
                        'main_flight_no': '',
                        'cabin_infolist': [{
                            'cabin': cabin,
                            'cabin_type': '',
                            'price': '',  # 总售价 float string
                            'base_price': price,  # 不含税价
                            'surcharges_adt': '',  # 附加费
                            'tax_adt': tax,  # 税
                            'ticket_remain': ticket_remain,  # 余票数
                            'tax_fees': '',  # 税费总额
                            'currency': currency,  # 币种
                        }]
                    }
            for _, v in flight_info.items():
                data1.append(v)
        return data1, data2
