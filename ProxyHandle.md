# 简介

一个用来处理代理池的程序，整体框架使用的协程`asyncio`所以做了一些处理。

## 过滤函数

由于代理池的质量太差写了一个用来过滤的函数

```python
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
```

原理很简单，使用这个代理不断访问要爬取的`url`，然后设定访问时间，在访问时间内返回指定数量的代理。

