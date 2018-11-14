import requests
from lxml import etree
import time
def getLines(url):
    html = requests.get(url)
    selector = etree.HTML(html.text)
    lines = selector.xpath(reg)
    lines = 'http://tieba.baidu.com/p/'+lines[0][2:]
    return lines
def getPage(url):
    html2 = requests.get(url)
    selector2 = etree.HTML(html2.text)
    page = selector2.xpath(reg2)
    return page[0]
def getPic(url):
    html2 = requests.get(url)
    selector2 = etree.HTML(html2.text)
    pics = selector2.xpath(reg3)
    return pics
def Dowload(pictures):
    x = 0
    for picture in pictures:
        pic = requests.get(picture)
        with open('pic'+str(x)+'.jpg','wb') as fp:
            fp.write(pic.content)
        print(x)
        x+=1
def handler(url):
    lines = []
    pictures = []
    digit = input("请问要爬取多少页：")
    for i in range(1,int(digit)+1):
        url1 = url+'&pn='+str(i*50)
        lines.append(getLines(url1))
    for line in lines:
        pages = getPage(line)
        for page in range(1,int(pages)+1):
            line2 = line+'?pn='+str(page)
            pictures.extend(getPic(line2))
    Dowload(pictures)
if __name__ == '__main__':
    reg =r'//div[@class="small_list_gallery"]/ul/@id'
    reg2 = r'//*[@id="thread_theme_5"]/div[1]/ul/li[2]/span[2]/text()'
    reg3 = r'//*[@id="j_p_postlist"]/div/div[3]/div[1]/cc/div/img/@src'
    name = input("请输入贴吧名：")
    url = 'http://tieba.baidu.com/f?kw='+name+'&ie=utf-8'
    time1 = time.time()
    handler(url)
    time2 = time.time()
    print("OVER")