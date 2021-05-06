import asyncio
import aiohttp
import time

#代理池处理
#记得写入自己的代理池访问地址，ip prot之类的


class Proxy:
    def __init__(self,host,prot):
        self._host = host
        self._prot = prot

    async def get(self):
        # start = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{self._host}:{self._prot}/get/") as response:
                json = await response.json()
                proxy = json.get('proxy')
        # end = time.time()
        # print(f'获取:{proxy},耗时{end - start:.2f} seconds')
        return proxy

    async def delete(self,proxy):
        # start = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{self._host}:{self._prot}//delete/?proxy={proxy}") as response:
                await response.text()
        # end = time.time()
        # print(f'{proxy},已经被杀了，耗时{end - start:.2f} seconds')

class FilterProxy(Proxy):
    def __init__(self,name,host,prot):
        #host:代理服务器的ip
        #port:代理服务器的端口
        #timeout:设置过滤超时的时间
        Proxy.__init__(self,host,prot)
        self._name = name

    async def filer(self,url,timeout,queue:asyncio.Queue()):
        # start = time.time()
        proxy = await Proxy.get(self)  # 获得一个proxy
        _proxy = "http://" + proxy
        Timeout = aiohttp.ClientTimeout(total=timeout)
        try:
            async with aiohttp.ClientSession(timeout=Timeout) as session:
                async with session.get(url, verify_ssl=False, proxy=_proxy) as response:
                    await response.test()
            print(f'{self._name}请求成功,{proxy}推入队列')
            await queue.put(proxy)
        except BaseException as e:
            # print(f"{self._name}出现错误{e}，这个{proxy}该杀了")
            await Proxy.delete(self, proxy)
        # end = time.time()
        # print(f'{self._name}使用:{proxy}请求,耗时{end - start:.2f} seconds')

    async def filer_num(self,url,timeout,queue:asyncio.Queue(),num):
        for _ in range(num):
            await self.filer(url,timeout,queue)

    async def filer_event(self,url,timeout,queue:asyncio.Queue(),event:asyncio.Event()):
        while True:
            if not event.is_set():
                print(self._name + '停止')
                break
            await self.filer(url,timeout,queue)

    async def filter_effective(self,url,timeout,num):
        #返回一个proxy的列表，指定长度
        #到达指定长度后停止循环返回这个列表
        proxys = []
        Timeout = aiohttp.ClientTimeout(total=timeout)
        while True:
            try:
                proxy = await Proxy.get(self)  # 获得一个proxy
                _proxy = "http://" + proxy
                async with aiohttp.ClientSession(timeout=Timeout) as session:
                    async with session.get(url, verify_ssl=False, proxy=_proxy) as resp:
                        # await response.text()
                        assert resp.status == 200
                print(f'{self._name}请求成功,{proxy}推入列表')
                proxys.append(proxy)
            except Exception as e:
                await asyncio.sleep(0.1)
                # print(f"{self._name}出现错误{repr(e)}了")
                # await Proxy.delete(self, proxy)
            if len(proxys) == num:
                break
        return proxys


