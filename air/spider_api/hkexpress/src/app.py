# -*- coding:utf-8 -*-
from gevent import monkey;
monkey.patch_all()
import gevent

from flask import Flask, request, jsonify, current_app, abort, Response
import datetime
from datetime import timedelta
import queue
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import *
import logging
from pymongo import MongoClient
# from iata_to_cityname import get_name_from_iata

logger = logging.getLogger('flask.app')
logger.setLevel('DEBUG')

# mondodb配置
client = MongoClient('mongodb://ip/')
db = client.mongoair
db.authenticate('passwd')

MAX_RUN = 10

options = webdriver.ChromeOptions()

# 这块没用，改用元素是否出现判断ajax内容是否载入
capabilities = DesiredCapabilities.CHROME.copy()
capabilities["pageLoadStrategy"] = "none"
capabilities.update(options.to_capabilities())

# options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')
options.add_argument("--incognito")
options.add_argument("--disable-extensions")
options.add_argument('--disable-logging')
options.add_argument("--log-level=3")
options.add_argument("--silent")
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ssl-protocol=any')
options.add_argument('--allow-running-insecure-content')
options.add_argument('--ignore-autoplay-restrictions')
options.add_argument('blink-settings=imagesEnabled=false')
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36")


class FetcherPool(object):
    def __init__(self):
        logger.debug('初始化selenium池')
        self.options = options
        self.max_run = MAX_RUN
        self.queue = queue.LifoQueue(self.max_run)
    
    def insert_driver(self, driver):
        logger.debug('插入selenium session到selenium池')
        if self.queue.qsize() == self.max_run:
            driver.close()
        else:
            # 清理脏数据
            # driver.delete_all_cookies()
            # driver.get('about:blank')
            self.queue.put(driver)
    
    def get_driver(self):
        logger.debug('从浏览器池获取浏览器')
        try:
            driver = self.queue.get_nowait()
        except queue.Empty:
            driver = webdriver.Chrome(chrome_options=self.options)
            driver.implicitly_wait(30)
        
        driver.delete_all_cookies()
        driver.get('about:blank')
        return driver
    
    def __exit__(self):
        logger.debug("执行退出方法，清理浏览器队列")
        while not self.queue.empty():
            driver = self.queue.get_nowait()
            driver.quit()


dp = FetcherPool()
app = Flask(__name__)


@app.route('/')
def index():
    return "qunar pc站查询api, api route: /qunar/airlineprice?dep={}&arr={}&date={}"


@app.route('/hkexpress/airlineprice')
def air_line_price():
    dep = request.args.get('dep', '')
    arr = request.args.get('arr', '')
    date = request.args.get('date', '')
    print(dep, arr, date)
    print('current_app.logger', current_app.logger)
    app.logger.debug('{}-{}-{}'.format(dep, arr, date))
    
    if not (dep or arr or date):
        abort(Response('参数异常'))
    
    # 同步
    get_html(dep, arr, date)
    
    # 异步
    # gevent.spawn(get_html_list_call, dep, arr, date)
    
    data = {'message': '任务提交成功', 'code': '11111'}
    
    return jsonify(data)


def get_html(dep, arr, date):
    date_ = date.split('-')
    date = date_[2] + '/' + date_[1] + '/' + date_[0]
    url = 'https://booking.hkexpress.com/zh-CN/select/?SearchType=ONEWAY&OriginStation={}&DestinationStation={}&DepartureDate={}&Adults=1&currency=CNY&LowFareFinderSelected=false'.format(
        dep, arr, date)
    current_app.logger.debug(url)
    driver = dp.get_driver()
    driver.get(url)
    logger.debug('第一次请求 字符长度为{}'.format(len(driver.page_source)))

    try:
        # 载入下一页 判断是否拿到结果
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#maincontent > div:nth-child(2) > div > div > flight-schedule-container > schedule-tabs > div > ibe-tab-panel > div.flights.ng-star-inserted')))
        gevent.sleep(0.1)
        html = driver.page_source
        logger.debug('日期:{} 待存入mongodb 字符长度为{}'.format(date, len(html)))
    except TimeoutException:
        logger.debug("selenium获取元素超时，跳过这一天")
        html = driver.page_source
        logger.debug('超时 字符长度为{}'.format(len(html)))
    except Exception as e:
        logger.warning("获取价格异常, 跳过这一天 Exception:{}".format(e))
    else:
        data = {
            'dep': dep,
            'arr': arr,
            'date': date,
            'code': '',
            'update': datetime.datetime.utcnow() + timedelta(hours=8),
            'carrier': 'qunar',
            'message': '',
            'airline_country_type': '',
            'html': html
        }
        db.hkexpress_pc_html.insert(data)
        logger.debug("完成抓取，浏览器重新加入队列")
    finally:
        logger.debug('回收当前使用的浏览器')
        dp.insert_driver(driver)
    return {'message': 'ok'}


if __name__ == '__main__':
    import argparse
    
    parse = argparse.ArgumentParser(epilog="内置一些脚本启动参数方便未来部署和调试")
    parse.add_argument("-p", "--port", default="6608", help="接口绑定的端口")
    parse.add_argument("-d", "--debug", type=bool, default=False, help="debug状态")
    args = parse.parse_args()
    
    port = args.port
    debug = args.debug
    try:
        logger.info('启动flask app！')
        app.run(host='0.0.0.0', port=port, debug=debug)
        logger.info('退出flask app！')
    finally:
        logger.debug('dp.queue: {} '.format(dp.queue.qsize()))
        dp.__exit__()
        logger.debug('dp.queue: {} '.format(dp.queue.qsize()))
        logger.info('flask app退出后，回收浏览器完成。')


