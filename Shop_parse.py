from parsel import Selector
import re
import json
from pymysql import escape_string



p_price = re.compile("(\d+)\.(\d+)")
def price_pipeline(PRICE):
    if PRICE !='':
        PRICE = PRICE[0].replace(",",'')
        p = p_price.findall(PRICE)[0]
        return p[0] + '.' + p[1]
    else:
        return PRICE

def feature_pipeline(FEATURE):
    rs = []
    dirty_stuff = ["\"", "\\", "/", "*", "'", "=", "-", "#", ";", "<", ">", "+", "%", "$", "(", ")", "%", "@", "!"]
    if FEATURE != '':
        for i in FEATURE:
            rs.append(i.replace(dirty_stuff,''))
    return rs



def parse(html):
    ShopInfo_sele_parsel = Selector(html)
    # 商品名
    SHOP_NAME = ShopInfo_sele_parsel.xpath("// *[ @ id = 'productTitle']/text()").get()
    #.replace(" ", "").replace("\n",'')
    #价格
    PRICE = ['0.0']
    if ShopInfo_sele_parsel.xpath('//*[@id="priceblock_ourprice"]'):
        PRICE = ShopInfo_sele_parsel.xpath('//*[@id="priceblock_ourprice"]/text()').getall()
    elif ShopInfo_sele_parsel.xpath('//*[@id="kindle-price"]'):
        PRICE = ShopInfo_sele_parsel.xpath('//*[@id="kindle-price"]/text()').getall()
    FEATURE_LIST = []
    # 产品说明
    if ShopInfo_sele_parsel.xpath("//*[@id='outer_postBodyPS']"):
        FEATURE_LIST = ShopInfo_sele_parsel.xpath('//*[@id="bookDescription_feature_div"]/noscript').getall()
    elif ShopInfo_sele_parsel.xpath("//*[@id='featurebullets_feature_div']"):
        FEATURE_LIST = ShopInfo_sele_parsel.xpath(
        "//div[@id='featurebullets_feature_div']/descendant::*//span[@class='a-list-item']/text()").getall()
    IMG_LIST = ShopInfo_sele_parsel.xpath(
        "//div[@class='a-text-center a-fixed-left-grid-col a-col-right']/descendant::*//img/@src").getall()
    TYPE_SET = set()
    if ShopInfo_sele_parsel.xpath("//*[@id='twister']"):
        TYPE = ShopInfo_sele_parsel.xpath("//*[@id='twister']/div/ul/li")
        [TYPE_SET.add(sin) for sin in TYPE.xpath("./@data-defaultasin").getall() if sin != '']  # defaultasin
        [TYPE_SET.add(re.findall("\/dp\/(.*?)\/", dp)[0]) for dp in TYPE.xpath("./@data-dp-url").getall() if
         dp != '']  # dp
    my_dict =  {
        "SHOP_NAME": escape_string(SHOP_NAME.replace('\n','')),
        'PRICE':price_pipeline(PRICE),
        "FEATURE": escape_string(json.dumps(FEATURE_LIST,ensure_ascii=False)),
        "IMG": IMG_LIST,
        "TYPE_SET":TYPE_SET
    }
    return my_dict

