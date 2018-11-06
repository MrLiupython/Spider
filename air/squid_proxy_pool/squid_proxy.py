'''
quid+第三方代理搭建代理IP池

参考Github: github.com/xNathan

注意squid缓存配置，如果缓存了图片，可能会对验证码造成影响
'''
from gevent import monkey

monkey.patch_all()

import os
import time
import logging
import requests
from gevent.pool import Pool
import re
import codecs
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s: - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

# 使用StreamHandler输出到屏幕
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)

logger.addHandler(ch)

# Squid的配置文件语法
# 将请求转发到父代理
# cache_peer *** parent 25824 0 no-query weighted-round-robin weight=1 login=name:passwd connect-fail-limit=2 allow-miss max-conn=5

PEER_CONF = "cache_peer %s parent %s 0 no-query weighted-round-robin weight=1 connect-fail-limit=2 allow-miss max-conn=5\n"

# 可用代理
GOOD_PROXIES = []

pool = Pool(50)


def check_proxy(proxy, timeout=5):
    """验证代理是否可用
    :param proxy list:[ip, port]"""
    global GOOD_PROXIES
    ip, port = proxy
    _proxies = {
        'http': '{}:{}'.format(ip, port)
    }
    try:
        res = requests.get('http://www.httpbin.org/ip', proxies=_proxies, timeout=timeout)
        assert ip in res.text
        logger.info('[GOOD] - {}:{}'.format(ip, port))
        GOOD_PROXIES.append(proxy)
    except Exception as e:
        logger.error('[BAD] - {}:{}, {}'.format(ip, port, e))


def update_conf():
    with codecs.open('./squid.conf.default', 'r', 'utf-8') as f:
        squid_conf = f.readlines()
    squid_conf.append('\n# Cache peer config\n')
    for proxy in GOOD_PROXIES:
        squid_conf.append(PEER_CONF % (proxy[0], proxy[1]))
    with codecs.open('/etc/squid/squid.conf', 'w', 'utf-8') as f:
        f.writelines(squid_conf)


# 从配置文件读取现有的ip，因为全局队列GOOD_PROXIES的存在用不上了，方法留着备用
def ip_from_conf():
    with open('/etc/squid/squid.conf', 'r', encoding='UTF-8') as f:
        file = f.read()
        p_list = re.findall('cache_peer\s(\d+\.\d+\.\d+\.\d+)\sparent\s(\d+)\s', file)
        return p_list


def get_proxy(num):
    logger.debug('获取新代理')
    """
        {
    "ERRORCODE":"0",
    "RESULT":[
    {"port":"43617","ip":"***"},
    {"port":"43569","ip":"***"},
    {"port":"20443","ip":"***"}
    ]}
    :return:
    """
    if num <= 0:
        return
    # 每次最多取5个
    if num > 5:
        num = 5
    global GOOD_PROXIES
    proxies = GOOD_PROXIES[:]
    GOOD_PROXIES = []
    
    # 1. 获取代理IP资源
    api_url = 'http://proxy_address'.format(num)
    res = requests.get(api_url).json()
    
    logger.debug('res: {}'.format(res))
    if len(res.get('RESULT')) == 0:
        logger.error('no data')
    else:
        for proxy in res.get('RESULT'):
            logger.debug('proxy: ', proxy, type(proxy))
            proxies.append((proxy['ip'], proxy['port']))
        pool.map(check_proxy, proxies)
        pool.join()
        # 2. 写入Squid配置文件
        logger.info('所有待加入squid的代理 {}， 共 {} 个'.format(GOOD_PROXIES, len(GOOD_PROXIES)))
        update_conf()
        # 3. 重新加载配置文件
        os.system('squid -k reconfigure')
        # os.system('echo %s|sudo -S %s' % ('18443333', 'squid -k reconfigure'))
        
        logger.info('>>>> DONE! <<<<')

def check_alive():
    logger.debug('检查存活')
    global GOOD_PROXIES
    proxies = GOOD_PROXIES[:]
    GOOD_PROXIES = []
    pool.map(check_proxy, proxies)
    pool.join()
    logger.info('当前squid共有代理数量：{} ，存活代理数量：{}'.format(len(proxies), len(GOOD_PROXIES)))
    return len(GOOD_PROXIES)
    

def main(num):
    start = time.time()
    logger.info('开始运行')
    get_proxy(5)
    # while True:
    #     if time.time() - start >= 60:
    #         check_alive()
    #         # 每10秒获取一批新IP
    #     logger.debug('等待超过10秒')
    #     get_proxy(5)
    #     # logger.debug('从接口取回{}个代理'.format(5))
    #     time.sleep(10)
    while True:
        # 每30秒获取一批新IP
        logger.debug('进入循环')
        alive = 5
        if time.time() - start >= 60:
            alive = check_alive()
        
        # 按需维持代理的数量来取
        get_proxy(num + 3 - alive)
        # get_proxy(1)
        logger.debug('从接口取回{}个代理'.format(num + 3 - alive))
        start = time.time()
        time.sleep(60)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--num", type=int, default=5,
                        help=" 希望保持的代理ip数量, 后台每次向接口请求（num + 2 - 当前活跃数量）  default:--num 5")
    args = parser.parse_args()
    main(args.num)

