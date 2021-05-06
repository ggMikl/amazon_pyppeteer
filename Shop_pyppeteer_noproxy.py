import asyncio
from pyppeteer import launch
import time
import json
from fake_useragent import UserAgent
import aiomysql
from pymysql import escape_string
from pymysql.err import IntegrityError
from Shop_parse import parse



# 抓取模式
# MODE = 'Normal' #在数据库中取指定最大数量（默认30）的商品抓取
MODE = 'Retry'  # 在数据库中取抓取失败的商品，也就是重试
NUM = 30 #抓取数量
TYPE_MODE = True #是否抓取商品页的型号
COROUTINE_NUM = 5 #协程数

#数据库参数
db_host =''
db_prot = 3306
db_user = ''
db_password = ''
db_db = ''

#代理池
proxy_host = ''
proxy_port = ''



#全局变量用来控制协程保持数据同步
READY = set() #待爬集合
SUCCESS = set() #爬取成功集合
FAILURE = set() #爬取失败集合
ALL = set() #数据库所有数据集合

#pyppeteer参数
width,height = 2560,1440


#爬取访问主机
host = 'https://www.amazon.cn'

#入库处理
async def execute(sql, pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql)
            await conn.commit()
async def select(sql, pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql)
            r = await cur.fetchall()
    return r




#pyppeteer动作
async def thum_hover(page):
    thum_id = await page.xpath("//div[@id='altImages']/descendant::*//span[@class='a-button-text']")
    # #动作触摸：每个缩略图
    for i in thum_id[2:]:
        await i.hover()

#pyppeteer主函数
async def craw_consume(task_name,shop_queue:asyncio.Queue,pool,lock,type_mode):
    global READY
    global SUCCESS
    global FAILURE
    global ALL
    while True:
        start = time.time()
        print(f'****************************Task {task_name} is staring****************************************************')
        shop_code = await shop_queue.get()
        url = host + '/dp/'+shop_code
        browser = await launch(headless=True,
                               args=['--disable-infobars',
                                     # f'--window-size={width},{height}',
                                     "--start-maximized",
                                     ]
                               )
        page = await browser.newPage()
        # await page.evaluateOnNewDocument('() =>{ Object.defineProperties(navigator,'
        #                                  '{ webdriver:{ get: () => false } }) }')  # 本页刷新后值不变
        ua = UserAgent().chrome
        # print('设置：',ua)
        await page.setUserAgent(ua)#设置随机UA
        await page.setViewport({
            "width": width,
            "height": height
        })
        try:
            await asyncio.wait_for(page.goto(url),timeout=30)
            print(f'Task {task_name}: {shop_code}'+'发送请求：', url)
            # 等待元素加载
            if await page.xpath("//*[@id='productTitle']"):
                print(f'Task {task_name}: {shop_code}'+'正常请求，没有被检测')
                # 进行动作
                if await page.xpath("//div[@id='altImages']"):
                # if await page.waitForXPath("//div[@id='altImages']"):
                    print(f'Task {task_name}: {shop_code}'+ '：进行动作')
                    await asyncio.sleep(0.1)
                    await thum_hover(page)
                content = await page.content()
                rs = parse(content)
                print(f'Task {task_name} {shop_code}:' ,rs)
                #入库
                name = rs["SHOP_NAME"]
                price = rs["PRICE"]
                feature = rs["FEATURE"]
                imgs = rs["IMG"]
                TYPE_SET = rs['TYPE_SET']
                await asyncio.sleep(0.1)#防阻塞
                await execute(f'INSERT INTO amazon_shop(NODE,NAME,PRICE,FEATURE) VALUES(\'{shop_code}\',\'{name}\',{price},\'{feature}\')',pool)
                for img in imgs:
                    await execute(f'INSERT INTO amazon_img(NODE,IMG_URL) VALUES(\'{shop_code}\',\'{img}\')',pool)

                await execute(f"UPDATE amazon_index SET STATUS='SUCESS' where NODE=\'{shop_code}\'",pool)
                SUCCESS.add(shop_code)
                print(f'Task {task_name}: {shop_code}'+'###############入库成功###############')
                if type_mode == True:#开启型号循环
                    # 判断其他型号
                    if TYPE_SET != set():  # 如果这次遍历得到了型号集合，那么将这个型号加入到请求队列中
                        print(f'Task {task_name}: {shop_code}'+'有其他型号')
                        STR_TYPE_SET = r'' + json.dumps(list(TYPE_SET), ensure_ascii=False)
                        await execute(f"UPDATE amazon_index SET SHOP_TYPE =\'{STR_TYPE_SET}\' where NODE=\'{shop_code}\'",pool)
                        async with lock:#使用协程锁，防止数据同步出现问题
                            # print(f'Task {task_name}: {shop_code}:',READY)
                            for type in rs['TYPE_SET']:  # 遍历型号集合
                                if type not in READY and type not in ALL and type != shop_code:
                                    await asyncio.sleep(0.1)  # 防阻塞
                                    await shop_queue.put(type)  # 入队
                                    await execute(f"INSERT INTO amazon_index(NODE) VALUES (\'{type}\')",pool)
                            READY = READY|TYPE_SET #入队完毕后将这个TYPE_SET并起来
            else:
                await asyncio.sleep(0.1)
                FAILURE.add(shop_code)
                await execute(f"UPDATE amazon_index SET STATUS='FAILURE',INFO ='Robot Check' where NODE=\'{shop_code}\'",pool)
        except IntegrityError:
            print(f'Task {task_name}: {shop_code}:数据重复，需要修改数据库数据')
            await asyncio.sleep(0.1)
            try:
                await asyncio.sleep(0.1)  # 防阻塞
                sql = f"UPDATE amazon_index SET STATUS='SUCCESS' where NODE=\'{shop_code}\'"
                await execute(sql,pool)
            except Exception as be:
                print(f'Task {task_name}: {shop_code}:数据重复，需要修改数据库数据',repr(be))
        except Exception as e:
            try:
                error = escape_string(repr(e))
                print(f'Task {task_name}: {shop_code}:',error)
                await asyncio.sleep(0.1)#防阻塞
                await execute(f"UPDATE amazon_index SET STATUS='FAILURE',INFO =\'{error}\' where NODE=\'{shop_code}\'",pool)
                FAILURE.add(shop_code)
            except Exception as ee:
                print(f'Task {task_name}: {shop_code}'+'ERROR 入库出错 :'+ repr(ee))
        await browser.close()
        end = time.time()
        task_time = end - start
        print(f'****************************Task {task_name} has consumer time is {task_time:.2f} seconds****************************')
        shop_queue.task_done()#队列通知

async def main(mode,num,type_mode,coroutine_num,loop):
    global READY
    global SUCCESS
    global FAILURE
    global ALL

    start = time.time()
    #创建协程锁
    lock = asyncio.Lock()
    #启动数据库连接池
    pool = await aiomysql.create_pool(
        host=db_host,
        port=db_prot,
        user=db_user,
        password=db_password,
        db=db_db,
        loop=loop)

    shop_queue = asyncio.Queue()
    [ALL.add(ex_node[0]) for ex_node in await select(sql="select NODE from amazon_index ",pool=pool)] #提取数据库所有数据防止重复抓取

    if mode == 'Normal':
        shops = await select(sql=f'select NODE from amazon_index  where STATUS is NULL limit {num}',
                             pool=pool)  # 链接数据库取30个没有抓取过的数据
    elif mode == 'Retry':
        shops = await select(sql=f"select NODE from amazon_index  where STATUS = 'FAILURE' limit {num}", pool=pool)
    else:
        print('没有写什么模式，使用默认：正常中抓取30个商品')
        shops = await select(sql=f'select NODE from amazon_index  where STATUS is NULL limit 30',
                             pool=pool)  # 链接数据库取30个没有抓取过的数据

    for shop in shops:
        READY.add(shop[0])
        shop_queue.put_nowait(shop[0])#生成队列
    print(READY)
    print('长度:',len(READY))

    if coroutine_num <= 0:
        coroutine_num = 1
    # 生成任务组
    tasks = []
    for i in range(coroutine_num):
        task = asyncio.create_task(craw_consume(f'craw-{i}', shop_queue,pool,lock,type_mode))
        tasks.append(task)
    # 等待队列结束
    await shop_queue.join()
    print('队列执行完毕')
    # 取消任务
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    end = time.time()
    print('请求集合：', READY)
    print('请求成功集合：', SUCCESS)
    print('请求失败集合：', FAILURE)
    print(f'任务工作总时间{end-start:.2f} seconds')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(MODE,NUM,TYPE_MODE,COROUTINE_NUM,loop))
    loop.run_until_complete(asyncio.sleep(0.250))
    loop.close()

