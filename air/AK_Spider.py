#! /usr/bin/env python
# -*- coding: utf-8 -*-
from pyspider.libs.base_handler import *
from datetime import timedelta
import datetime
from pymongo import MongoClient
import sys
import time
import hashlib
import re
import requests
from lxml import etree
import math

ip = 'proxy_ip
port = 'port'
ip_port = ip + ":" + port


# client = MongoClient('mongodb://mongodb_ip:port/')  # 本地测试
client = MongoClient('mongodb://mongodb_ip:port/')
db = client.mongoair
db.authenticate('password')


# 优先航线的机场梯度字典，包含中国的航线为一梯度，东南亚之内的航线为另一梯度
def airport_dict():
    code_dict = {'China': {}, 'DNY': {}}
    dongnanya = [u'越南', u'老挝', u'柬埔寨', u'泰国', u'缅甸', u'马来西亚', u'新加坡', u'印度尼西亚', u'文莱', u'菲律宾', u'东帝汶']
    r = requests.get('http://112.74.47.255:8080/api/sp/airport?all=1', timeout=12)
    for airport_item in r.json()['data']:
        country = airport_item.get('country')
        iata = airport_item.get('iata')
        if country == u'中国':
            code_dict['China'].update({iata: 1})
        elif country in dongnanya:
            code_dict['DNY'].update({iata: 1})
    return code_dict


code_dict = airport_dict()


class Handler(BaseHandler):
    crawl_config = {
        "proxy": ip_port,
        "retries": 0,
        "itag": "v1"
    }

    @every(minutes=30)
    def on_start(self):
        current = datetime.datetime.utcnow() + timedelta(hours=8)
        # 一天内抓取的时间
        fetch_time = 12
        # start天后开始抓取，
        query_list = self.get_query_list(num=30, start=3)
        # 机场梯度字典
        print(code_dict['China'])
        if 8 <= current.hour < 8 + fetch_time:
            for i in range(int(math.ceil(len(query_list) / 150.0))):
                self.crawl('data:,step%d' % i, callback=self.get_url, age=30 * 60, auto_recrawl=True,
                           save={'num': i}, priority=1)
        elif current.hour >= 8 + fetch_time:
            for i in range(int(math.ceil(len(query_list) / 150.0))):
                self.crawl('data:,step%d' % i, age=30 * 60, auto_recrawl=False, cancel=True,
                           force_update=True, save={'num': i}, priority=1)
        else:
            pass

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

    def get_url(self, response):
        auth = self.get_proxy()
        num = response.save.get('num')
        headers = {
            'Host': 'booking.airasia.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.75 Safari/537.36',
            'Referer': 'https://www.airasia.com/cn/zh/home.page',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Proxy-Authorization': auth
        }

        cookies = {
            "acw_tc": "790c6dcc15367210705655944e9b1d24a16b679a6cb5d1a72800b41cbd"
        }

        query_list = self.get_query_list(num=30, start=3)
        for query in query_list[num * 150: (num + 1) * 150]:
            url = 'https://booking.airasia.com/Flight/Select?o1={}&d1={}&culture=zh-CN&dd1={}&ADT=1&s=true&mon=true&cc=CNY&c=false'.format(
                query[0], query[1], query[2])
            p_num = 0
            # 根据机场梯度字典判断抓取任务的优先级
            if code_dict['China'].get(query[0]) or code_dict['China'].get(query[1]):
                p_num = 2
            elif code_dict['DNY'].get(query[0]) and code_dict['DNY'].get(query[1]):
                if 'DMK' in query[:2] or 'KUL' in query[:2]:
                    p_num = 1
            self.crawl(url, headers=headers, cookies=cookies, validate_cert=False, allow_redirects=False,
                       callback=self.detail_page, save={'query': query, 'p_num': p_num}, age=5 * 60, priority=p_num)

    def on_message(self, project, msg):
        auth = self.get_proxy()
        query = msg.get('query')
        p_num = msg.get('p_num')
        headers = {
            'Host': 'booking.airasia.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.75 Safari/537.36',
            'Referer': 'https://www.airasia.com/cn/zh/home.page',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Proxy-Authorization': auth
        }

        cookies = {
            "acw_tc": "790c6dcc15367210705655944e9b1d24a16b679a6cb5d1a72800b41cbd"
        }
        url = 'https://booking.airasia.com/Flight/Select?o1={}&d1={}&culture=zh-CN&dd1={}&ADT=1&s=true&mon=true&cc=CNY&c=false'.format(
            query[0], query[1], query[2])
        self.crawl(url, headers=headers, cookies=cookies, validate_cert=False, allow_redirects=False,
                   callback=self.detail_page, save={'query': query, 'p_num': p_num}, age=5 * 60, priority=p_num)

    def detail_page(self, response):
        print(response.text)
        query = response.save['query']
        result = {
            # 根据该任务抓取优先级判断航线类型
            "airline_country_type": "2" if response.save['p_num'] == 2 else '3',
            "carrier": "AK",
            "dep": query[0],
            "arr": query[1],
            "date": query[2],
            "data": [],
            "data2": [],
            "code": "0000",
            "message": "0000",
            "update": datetime.datetime.utcnow() + timedelta(hours=8)
        }
        data = re.search('<table class="table avail-table">(.*?)<div class="message"', response.text, re.DOTALL)
        # print(data)
        if not data:
            # 没有需要数据的情况判断
            if u'很抱歉，这个日期没有航班或所选航班的机位已售完 请选择其他日期或查看' in response.text:
                result.update({
                    "code": "9999",
                    "message": "当天没有航班"
                })
            elif u'/Flight/Select' in response.text:
                result.update({
                    'code': '1000',
                    'message': '航线不存在'
                })
            else:
                result.update({
                    "code": "1002",
                    "message": "抓取异常"
                })
        else:
            data1, data2 = self.fetch_data(data.group(1).strip(), query)
            # if data1 or data2:
            #     self.send_message('AK_Spider_follow_qunar', query, url=response.url + '#{}{}{}'.format(*query))
            # 单程中转包含的子航线抓取
            if data2:
                re_query_list = []
                for re_airline in data2:
                    for re_flight in re_airline['trip_list']:
                        re_dep = re_flight['dep']
                        re_arr = re_flight['arr']
                        re_date = re_flight['depdate']
                        re_query_list.append([re_dep, re_arr, re_date])
                for re_query in re_query_list:
                    # 根据机场梯度字典判断抓取任务的优先级
                    p_num = 0
                    if code_dict['China'].get(query[0]) or code_dict['China'].get(query[1]):
                        p_num = 2
                    elif code_dict['DNY'].get(query[0]) and code_dict['DNY'].get(query[1]):
                        if 'DMK' in query[:2] or 'KUL' in query[:2]:
                            p_num = 1
                    self.send_message('AK_Spider', {'query': re_query, 'p_num': p_num}, url=response.url + '#{}{}{}'.format(*re_query))

            result.update({
                "data": data1,
                "data2": data2,
                "code": "1111" if data1 or data2 else "1001",
                "message": "ok" if data1 or data2 else "当天没有有效航班",
            })
        return result

    def on_result(self, result):
        if not result:
            return
        super(Handler, self).on_result(result)
        db.akair.insert(result)

    def get_query_list(self, num, start=None):  # 航线列表
        # # r = requests.get("http://data_ip", timeout=15)
        airlines = ['DMK-BKI', 'CTU-KUL', 'BKI-SDK', 'KUL-DEL', 'BKI-DMK', 'KUL-PER', 'KUL-DVO', 'KUL-DAC', 'BKI-HGH', 'CAN-JHB', 'SWA-KUL', 'DMK-SZX', 'SWA-DMK', 'DMK-CCU', 'KUL-PKU', 'DEL-KUL', 'KUL-WUH', 'BKI-SZX', 'KMG-KUL', 'KUL-AOR', 'HKT-DMK', 'SGN-KUL', 'KUL-HKT', 'PKU-KUL', 'OOL-KUL', 'HGH-BKI', 'PVG-DMK', 'COK-DMK', 'DMK-CNX', 'KUL-KWL', 'KBV-KUL', 'KUL-PNH', 'TGG-KUL', 'DMK-MLE', 'KUL-SYD', 'KUL-BDO', 'KUL-TRZ', 'CKG-KUL', 'KUL-LOP', 'KUL-MYY', 'LBU-KUL', 'KUL-SUB', 'TWU-KUL', 'DMK-CAN', 'KUL-LBU', 'KCH-BKI', 'KUL-CTU', 'CNX-KUL', 'PER-KUL', 'DMK-XIY', 'KUL-DPS', 'KUL-CEB', 'MLE-DMK', 'DPS-DMK', 'KUL-HYD', 'KUL-CMB', 'CKG-DMK', 'CCU-DMK', 'KNO-KUL', 'TRZ-KUL', 'DMK-HKT', 'MNL-DVO', 'KUL-PEK', 'KUL-SDK', 'KMG-HKT', 'DMK-PNH', 'DMK-CSX', 'DPS-KUL', 'DMK-PEN', 'SYD-KUL', 'PEN-KUL', 'SZX-DMK', 'KUL-KBR', 'HHQ-KUL', 'SZX-BKI', 'AOR-KUL', 'DVO-CEB', 'DMK-KMG', 'SDK-KUL', 'KUL-CAN', 'KCH-BTU', 'SBW-KCH', 'SIN-BKI', 'CSX-DMK', 'BKI-MYY', 'HGH-KUL', 'KUL-CKG', 'KUL-DAD', 'DMK-CKG', 'KUL-MEL', 'KUL-KCH', 'KUL-XIY', 'KUL-CNX', 'DVO-KUL', 'CEB-DVO', 'KUL-RGN', 'SIN-KCH', 'MNL-KUL', 'MYY-KCH', 'SZX-KCH', 'KUL-SZX', 'HDY-DMK', 'HDY-KUL', 'MYY-KUL', 'KCH-PNK', 'CAN-KUL', 'KCH-MYY', 'PLM-KUL', 'JHB-KCH', 'JAI-KUL', 'HKT-WUH', 'KUL-JOG', 'JHB-CAN', 'DVO-MNL', 'CNX-CSX', 'DMK-VTE', 'KUL-CCU', 'KUL-BLR', 'CCU-KUL', 'DMK-RGN', 'CAN-LGK', 'JOG-KUL', 'KUL-BTJ', 'LGK-CAN', 'CMB-KUL', 'MEL-KUL', 'DMK-HGH', 'DMK-KNO', 'PVG-MNL', 'KWL-KUL', 'KUL-MLE', 'DMK-DAD', 'KUL-KMG', 'DMK-HAN', 'DMK-REP', 'KUL-PNK', 'HAN-DMK', 'BKI-JHB', 'KOS-KUL', 'SUB-KUL', 'KUL-SGN', 'BTJ-KUL', 'RGN-DMK', 'KUL-VTZ', 'KUL-NNG', 'KUL-KBV', 'KCH-SIN', 'HGH-DMK', 'KUL-CXR', 'SZX-KUL', 'BKI-WUH', 'MYY-BKI', 'REP-KUL', 'MNL-CAN', 'KUL-BKI', 'TWU-BKI', 'KCH-SZX', 'KCH-KUL', 'DAD-KUL', 'UPG-KUL', 'ATQ-KUL', 'XIY-DMK', 'SRG-KUL', 'DMK-WUH', 'HKT-KUL', 'DMK-CGK', 'BDO-KUL', 'KUL-PDG', 'WUH-KUL', 'DMK-KUL', 'KUL-HHQ', 'KUL-KOS', 'SDK-BKI', 'CXR-KUL', 'VTE-DMK', 'KMG-DMK', 'KNO-DMK', 'BTU-KUL', 'KUL-DMK', 'PNK-KCH', 'VTE-KUL', 'KUL-JHB', 'JHB-BKI', 'DMK-HDY', 'HGH-CNX', 'COK-KUL', 'DMK-SWA', 'CSX-CNX', 'CEB-SZX', 'KUL-HGH', 'PEN-DMK', 'DMK-CTU', 'BWN-KUL', 'BKI-SIN', 'BLR-KUL', 'KUL-HDY', 'KUL-CSX', 'KUL-SBW', 'KUL-CGK', 'KUL-PLM', 'DMK-JHB', 'DMK-ICN', 'JHB-DMK', 'ICN-DMK', 'KBV-DMK', 'BKI-KCH', 'KUL-JAI', 'KUL-SIN', 'KUL-TWU', 'NNG-KUL', 'CNX-HGH', 'SGN-DMK', 'PVG-KUL', 'DMK-DPS', 'PEK-KUL', 'KUL-MAA', 'WUH-BKI', 'KBR-KUL', 'DMK-KBV', 'RGN-KUL', 'SIN-DMK', 'LOP-KUL', 'KUL-MNL', 'KUL-COK', 'REP-DMK', 'DMK-COK', 'DMK-PVG', 'CAN-BKI', 'DAD-DMK', 'PNH-KUL', 'KUL-OOL', 'MLE-KUL', 'LGK-KUL', 'CGK-KUL', 'SZX-CEB', 'VTZ-KUL', 'UTP-NNG', 'MNL-PVG', 'KUL-PEN', 'KUL-LGK', 'CSX-KUL', 'WUH-HKT', 'PDG-KUL', 'CAN-MNL', 'MAA-KUL', 'BKI-TWU', 'SBW-KUL', 'CEB-KUL', 'HKT-KMG', 'SIN-KUL', 'DAC-KUL', 'DMK-SGN', 'CAN-DMK', 'CGK-DMK', 'PNK-KUL', 'KCH-SBW', 'XIY-KUL', 'KUL-TGG', 'CNX-DMK', 'BTU-KCH', 'KUL-UPG', 'BKI-KUL', 'PNH-DMK', 'KUL-BTU', 'KUL-REP', 'KUL-VTE', 'KUL-BWN', 'KCH-JHB', 'BKI-CAN', 'KUL-PVG', 'KUL-SWA', 'JHB-KUL', 'KUL-ATQ', 'KUL-KNO', 'CTU-DMK', 'HYD-KUL', 'DMK-SIN', 'NNG-UTP', 'KUL-SRG', 'WUH-DMK']
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
    def revers(strings):
        t = strings.split('/')
        result = [t[2], t[0], t[1]]
        return '-'.join(result)

    def fetch_data(self, data, query):
        html = etree.HTML(data)
        f_list = html.xpath('./body/tbody/tr[starts-with(@class, "fare")]')  # 航线列表
        data1 = []
        data2 = []
        for flight in f_list:
            airline_info = [0, 0]
            dep_arr_time = flight.xpath('.//table[@class="avail-table-detail-table"]/tr')
            # print(len(dep_arr_time))
            dep_dict = {}
            cabin_list = []
            # 航班的日期
            for n in dep_arr_time:
                times = n.xpath('.//div[@class="avail-table-bold"]/text()')
                di = n.xpath('.//div[@class="text-center"]/div[2]/text()')
                dep_dict.update(
                    {times[0]: {'dep': di[0][1:-1], 'arr': di[1][1:-1], 'deptime': times[0], 'arrtime': times[1]}})
            # print(dep_dict)
            # data_sets = flight.xpath('.//input') # 舱位列表
            # data_sets = flight.xpath('./td/div/div[@class="text-center"]')
            data_sets = flight.xpath('./td[2]/div/div[@class="text-center"]')
            ticket_remain = flight.xpath('./td[2]/div/div[2]/div/text()')
            if ticket_remain:
                ticket_remain = ticket_remain[0].strip()[-4]
            else:
                ticket_remain = '99'
            # print(len(data_sets))
            length = len(flight.xpath('.//tr[starts-with(@class, "fare")]'))
            # print(length)
            flight_info = {}
            if length not in [1, 2]:
                continue
            for item in data_sets:  # 舱位列表
                data_set = item.xpath('.//input')[0]
                # 数据源的币种，非页面展示的币种
                currency_2 = data_set.get('data-cur')
                cur_pr = item.xpath('.//div[@class="avail-fare-price"]/text()')[0].strip()
                # print('cur-pr:',cur_pr)
                price, currency = cur_pr.split()
                # 提取航线总价的舱位，非子航班的舱位
                cabin_list.append({
                    'cabin': '',
                    'cabin_type': '',
                    'price': price.replace(',', '').replace(u'≈', ''),  # 总售价 float string
                    'base_price': '',  # 不含税价
                    'surcharges_adt': '',  # 附加费
                    'tax_adt': '',  # 税
                    'ticket_remain': ticket_remain,  # 余票数
                    'tax_fees': '',  # 税费总额
                    'currency': currency,  # 币种
                })
                # print(currency,price)
                value = data_set.get('value').split('~')
                d_jsons = eval(data_set.get('data-json'))  # 航班列表
                # print([value[-8].strip()])
                date = {}
                if length == 1:
                    # print(1)
                    date = {value[-8].strip(): (value[-4], value[-2])}
                elif length == 2:
                    date = {
                        value[-8].strip(): (value[-4], value[-2]),
                        value[-16].strip(): (value[-12], value[-10])}
                    # print(date)

                for d_json in d_jsons:  # 航班列表
                    # 子航班的舱位价
                    price_2 = d_json.get('price')
                    # dep, _, arr = d_json.get('dimension13').split('-')
                    flight_no = d_json.get('dimension16')
                    cabin = d_json.get('dimension4')
                    sort_n = d_json.get('dimension6').split()[1]
                    num = flight_no[2:]
                    dep_, arr_ = date[num]
                    depdate, deptime = dep_.split()
                    # print(deptime)
                    arrdate, arrtime = arr_.split()
                    carrier = d_json.get('brand')
                    flight_k = flight_no + '-' + sort_n
                    if flight_info.get(flight_k):
                        # continue
                        # 具体提取子航班的舱位，目前不需要
                        flight_info[flight_k]['cabin_infolist'].append({
                            'cabin': cabin,
                            'cabin_type': '',
                            'price': price_2.replace(',', ''),  # 总售价 float string
                            'base_price': '',  # 不含税价
                            'surcharges_adt': '',  # 附加费
                            'tax_adt': '',  # 税
                            'ticket_remain': '',  # 余票数
                            'tax_fees': '',  # 税费总额
                            'currency': currency_2,  # 币种
                        })
                    else:
                        flight_info[flight_k] = {
                            'carrier': carrier,
                            'flight_no': flight_no,
                            'dep': dep_dict.get(deptime).get('dep'),
                            'arr': dep_dict.get(deptime).get('arr'),
                            'plane_style': '',
                            'depdate': self.revers(depdate),
                            'deptime': deptime,
                            'arrdate': self.revers(arrdate),
                            'arrtime': arrtime,
                            'main_flight_no': '',
                            # 'cabin_infolist': []
                            # 具体提取子航班的舱位，目前不需要
                            'cabin_infolist': [{
                                'cabin': cabin,
                                'cabin_type': '',
                                'price': price_2.replace(',', ''),  # 总售价 float string
                                'base_price': '',  # 不含税价
                                'surcharges_adt': '',  # 附加费
                                'tax_adt': '',  # 税
                                'ticket_remain': '',  # 余票数
                                'tax_fees': '',  # 税费总额
                                'currency': currency_2,  # 币种
                            }]
                        }
            for k, v in flight_info.items():
                _, n = k.split('-')
                airline_info[int(n)-1] = v
            if airline_info[0] and length == 1:
                airline_info[0]['cabin_infolist'][0].update({'price': cabin_list[0]['price'],
                                                             'currency': cabin_list[0]['currency'],
                                                             'ticket_remain': ticket_remain})
                data1.append(airline_info[0])
            elif airline_info[0] and length == 2:
                flight_no2 = airline_info[0]['flight_no'] + '/' + airline_info[1]['flight_no']
                data2.append({
                    'dep': query[0],
                    'arr': query[1],
                    'carrier': '',
                    'flight_no': flight_no2,
                    'price_list': cabin_list,
                    'trip_list': airline_info})
        return data1, data2
