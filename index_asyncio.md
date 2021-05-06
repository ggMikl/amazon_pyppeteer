# 需要输入的参数

```python
#查询参数
KEY = '运动休闲鞋'#查询关键字
PAGE = 2 #查询页数 亚马逊来说最多是10

#设置UserAgent
UA = ''

#数据库
host = ''
password = ''
port = ''
user = ''
db = ''
```

# 运行逻辑

商品页主要是静态页面，所以使用`aiohttp`来爬取，`cookies`用`pyppeteer`来获取
