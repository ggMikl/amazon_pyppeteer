import asyncio
import aiomysql
import aiohttp
from parsel import Selector
import re
from pyppeteer import launch


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

#使用pyppeteer来获取cookies
async def cookies_get(url):
    cookies = ''
    browser = await launch(headless=True, args=['--disable-infobars'])
    page = await browser.newPage()
    try:
        await asyncio.wait_for(page.goto(url),timeout=30)
        cookies_list = await page.cookies()
        for cookie in cookies_list:
            coo = "{}={}".format(cookie.get('name'),cookie.get('value'))
            cookies += coo
    except Exception as e:
        raise e
    await browser.close()
    return cookies

#使用aiohttp来爬取网页
async def craw(url,headers,payload):
    try :
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url,data=payload) as response:
                html = await response.text()
    except Exception as e :
        raise e
        html = ''
    return html

#提取数据
async def parse(html):
    index_sele_parsel = Selector(html)
    ShopBox = index_sele_parsel.xpath(
        "//div[@class='sg-col-4-of-12 s-result-item s-asin sg-col-4-of-16 sg-col sg-col-4-of-20']")
    if ShopBox == []:
        return ['RootCheck']
    else:
        return [re.compile("\/dp\/(.*?)\/").findall(
            i.xpath("./descendant::*//a[@class='a-link-normal s-no-outline']/@href").get())[0] for i in
                ShopBox]  # 顺便清洗一下


#连接数据库并保存数据
async def save(results,host,password,loop):
    # print('连接数据库')
    conn = await aiomysql.connect(host=host, port=port, user=user, password=password, db=db, loop=loop)
    async with conn.cursor() as cur:
        for i in results:
            sql = "INSERT INTO amazon_index(NODE) VALUES (\'%s\')" % (str(i))
            # print('入库操作')
            try:
                # print('执行sql语句')
                await cur.execute(sql)
                # print('提交到数据库执行')
                await conn.commit()
            except Exception as e:
                # print('如果发生错误则回滚')
                print(e)
                await conn.rollback()
        await cur.close()
    conn.close()
    # print('入库完成')

#协程的主要运行函数
async def run(url_queue:asyncio.Queue,headers, payload,conn,cur,loop):
    while True:
        url = await url_queue.get()
        if url == None:
            break
        html = await craw(url, headers, payload)
        rs = await parse(html)
        print(rs)
        await asyncio.sleep(0.1)  # 防阻塞
        await save(rs, conn, cur,loop)
        url_queue.task_done()

#主协程，添加一些必要的参数
async def main(loop):
    payload = {}
    headers = {
        'Host': 'www.amazon.cn',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'rtt': '50',
        'downlink': '10',
        'ect': '4g',
        'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cookie': ''

    }

    url_queue = asyncio.Queue()
    urls = [f"https://www.amazon.cn/s?__mk_zh_CN=亚马逊网站&k={KEY}&page={page}" for page in range(1, PAGE + 1)]
    for url in urls:
        url_queue.put_nowait(url)

    rs = await cookies_get('https://www.amazon.cn/')
    print('获取cookies:',rs)
    headers['Cookie'] = rs
    # print(headers)

    tasks = []
    for i in range(2) :
        task = asyncio.create_task(run(url_queue,headers, payload,host,password,loop))
        tasks.append(task)

    await url_queue.join()
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


#启动这个协程
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))




