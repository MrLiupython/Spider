# -*- coding: utf-8 -*-
import MySQLdb

class Database:
    def __init__(self):
        self.db = MySQLdb.connect(
            host='localhost',
            port=3306,
            user='name',
            passwd='passwd',
            db='db_name',
            charset='utf8'
        )
        self.cursor = self.db.cursor()

    def init_db(self):
        with open('news.sql', 'r') as fp:
            content = fp.read()
        self.cursor.execute(content)
        print("初始化数据库成功")
    
    def insert(self, data):
        sql_ = "INSERT INTO news_t (title, type, " \
            "publish_time, url, article_id, compliance)" \
            "VALUES ({}, {}, {}, {}, {}, {})"
        
        title = data['title']
        type_ = data['type']
        time_ = data['publish_time']
        url = data['url']
        id_ = data['article_id']
        flag = data['compliance']

        sql = sql_.format(title, type_, time_, url, id_, flag)
        
        self.cursor.execute(sql)
    
    def close(self):
        self.cursor.close()

