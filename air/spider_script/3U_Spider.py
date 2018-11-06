# -*- coding:utf-8 -*-
# Project : sichuangair.com

from pyspider.libs.base_handler import *
from pyspider.libs.utils import md5string
import requests
import json
import datetime
from pymongo import MongoClient
from datetime import timedelta
import math
import time, hashlib, sys
#
# client = MongoClient('mongodb://ip/')  # 本地测试
client = MongoClient('mongodb://ip')
db = client.mongoair
db.authenticate('password')

ip = 'proxy'
port = 'port'
ip_port = ip + ":" + port
headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json;charset=UTF-8',
    'Host': 'm.sichuanair.com',
    'Origin': 'http://m.sichuanair.com',
    'Pragma': 'no-cache',
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
    #         'Referer': 'http://m.sichuanair.com/touch-webapp/flight/flightList?adt=1&chd=0&departDate=2018-09-05&orgCity=CTU&destCity=PEK&promotionCod=&flightType=ONEWAY'
}


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
        for query in query_list[num * 150: (num + 1) * 150]:
            dep, arr, dep_date = query
            params = dep + arr + dep_date,
            print('query: ', query)
            data = json.dumps({"body": {}, "head": {"platformId": 3, "tokenId": None}})
            url = 'http://m.sichuanair.com/tribe-touch-web-h5/tribe/home/clientInitSetings#%s' % params
            headers1 = headers.copy()
            headers1.update({
                'Proxy-Authorization': self.get_proxy()
            })
            self.crawl(url, callback=self.post_form, headers=headers1, data=data, method="POST", save=query, age=5 * 60,
                       proxy=ip_port)

    def post_form(self, response):
        dep, arr, dep_date = response.save
        url = 'http://m.sichuanair.com/tribe-touch-web-h5/tribe/flight/queryFlightList'
        data = json.dumps({"body": {
            "flightSearchRequest": {"adt": "1", "chd": "0", "departDate": dep_date, "orgCity": dep,
                                    "destCity": arr, "promotionCod": "", "flightType": "ONEWAY",
                                    "calendarSearch": "false", "reqId": "", "searchType": "F", "userPrice": "false"},
            "page": {"count": 2147483647, "index": 1}, "sortType": "DATE_ASC"},
            "head": {"platformId": 3, "tokenId": ""}})
        headers2 = headers.copy()
        headers2.update({
            'Proxy-Authorization': self.get_proxy()
        })

        self.crawl(url, callback=self.detail_page, headers=headers2, cookies=response.cookies, data=data, method="POST",
                   save=response.save, age=5 * 60, proxy=ip_port, priority=2)

    def detail_page(self, response):
        doc = response.json
        query = response.save
        result = {
            "carrier": "3U",
            "dep": query[0],
            "arr": query[1],
            "date": query[2],
            "data": [],
            "data2": [],
            "code": "0000",
            "message": "0000",
            "airline_country_type": "2",  # "1", "3"
            "update": datetime.datetime.utcnow() + timedelta(hours=8)
        }
        if not doc.get('body').get('airlines'):
            if doc.get('body').get('message').get('keyCode') == 0:  # 空航班
                result.update({
                    "code": "9999",
                    "message": "当天没有航班"
                })
            # 访问频率过高或者莫名错误
            elif doc.get('body').get('message').get('keyCode') == 119 or doc.get('body').get('message').get('keyCode') == 21:
                response.status_code = 400
                response.raise_for_status()
            elif doc.get('body').get('message').get('keyCode') == 2:  # 参数错误包括航线不存在
                result.update({
                    "code": "1000",
                    "message": "航线不存在或者参数错误"
                })
        else:
            print(doc)
            data = self.fetch_price(doc)
            result.update({
                "data": data,
                "message": "ok" if data else "抓取异常",
                "code": "1111" if data else "1002"
            })
        return result

    def on_result(self, result):
        if not result:
            return
        super(Handler, self).on_result(result)
        db['3uair'].insert(result)

    def get_query_list(self, num, start=None):  # 航线列表
        # r = requests.get("http://data_api", timeout=15)
        r = requests.get('http://data_api', timeout=15)  # 跨境
        r.encoding = 'utf-8'
        airlines = r.json()['data']
        # airlines = ['CTU-KIX']
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

    @staticmethod
    def fetch_price(doc):
        flight_data_list = []
        for fl in doc.get('body').get('airlines')[0].get('airline'):
            info = fl.get('airlineDetailList')[0].get('airlineDetail')
            info2 = fl.get('airlineDetailList')[0].get('flightNoSegment')[0]
            # info_segment = fl.get('airline')[0].get('airlineDetailList')[0].get('flightNoSegment')
            flight_no = info2['marketingAirline'] + info2['flegFlightNo']
            main_flight_no = info2['operatingAirline'] + info2['flegFlightNo']
            dep = info['summary']['orgCity']
            arr = info['summary']['destCity']
            dep_date_time = info['summary']['departTime']
            arr_date_time = info['summary']['arrivalTime']
            depdate, deptime = dep_date_time.split()
            arrdate, arrtime = arr_date_time.split()
            plane_style = info2['planeModel']
            # share_flag = info2['shareFlight']

            # if cabin_type == '经济舱':
            #     cabin_type = 'Economy'
            # elif cabin_type == 'B':
            #     cabin_type = 'BUSINESS'

            flight_data = {'cabin_infolist': []}

            price_info = fl.get('price').get('fareFamilyTotal')

            extend_data = {
                'carrier': main_flight_no[0:2],
                'flight_no': flight_no,
                'dep': dep,
                'depdate': depdate,
                'arr': arr,
                'arrdate': arrdate,
                'plane_style': plane_style,
                'main_flight_no': main_flight_no,
                'deptime': deptime,
                'arrtime': arrtime
            }

            for cabin in price_info:
                # 总价
                price = cabin['fareFamilyTotal']['passengerFares']['ADT']['totalFare']['amount']
                # base价格
                base_price = cabin['fareFamilyTotal']['passengerFares']['ADT']['baseFare']['amount']
                surcharges_adt = ''
                tax_adt = ''
                tax_fees = str(price - base_price)
                ticket_remain = cabin.get('ticketNum', '')
                if ticket_remain == '':
                    ticket_remain = '99'
                currency = cabin['fareFamilyTotal']['passengerFares']['ADT']['baseFare']['currency']
                cabin_code = cabin['cabinCode'][0]
                cabin_type = cabin['fareFamilyTotal']['name']

                cabin_info = {
                    'cabin': cabin_code,
                    'cabin_type': cabin_type,
                    'base_price': str(base_price),
                    'surcharges_adt': surcharges_adt,
                    'tax_adt': tax_adt,
                    'price': str(price),
                    'ticket_remain': ticket_remain,
                    'tax_fees': tax_fees,
                    'currency': currency
                }

                flight_data['cabin_infolist'].append(cabin_info)
            flight_data.update(extend_data)
            flight_data_list.append(flight_data)

        return flight_data_list
