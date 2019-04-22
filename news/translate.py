# -*- coding: utf-8 -*-
# version: 3.6.0
from langconv import Converter

def translate(text):
    line = Converter('zh-hans').convert(text)
    line.encode('utf-8')
    return line

if __name__ == "__main__":
  test_text = '把中文字符串進行繁體和簡體中文的轉換'
  result = translate(test_text)
  print("test: {}\nreesult: {}".format(test_text, result))

