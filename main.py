import datetime
import re
import os
import requests
from config.headers import *
from config.cookies_config import cookie_list
import json
import threading
from queue import Queue
from threading import Lock

page_infos = Queue(maxsize=65535)
image_infos = Queue(maxsize=65535)
THREAD_NUM = 32
save_picture_path = "D:\ScrapyResult\pixiv"

gLock = Lock()
session = requests.Session()

if not os.path.exists(save_picture_path):
    os.mkdir(save_picture_path)
final_target_dir = os.path.join(save_picture_path, datetime.datetime.now().strftime('%Y-%m-%d'))
if not os.path.exists(final_target_dir):
    os.mkdir(final_target_dir)
    print(f'成功创建文件夹{final_target_dir}！！')

session.get('https://www.pixiv.net/artworks/84886149')
for cookie in cookie_list:
    session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
print('Login Successfully!')


def getAllImagePageUrls():
    global page_infos
    print("正在抓取json数据...")
    for i in range(65535):
        json_page_url = f'https://www.pixiv.net/ranking.php?p={i + 1}&format=json'
        r = session.get(json_page_url, headers=headers_of_pages)
        #  检测到接口返回的字符长度小于300时就说明已经爬取完毕
        if len(r.text) < 300:
            break
        json_result = json.loads(r.text)
        for content in json_result['contents']:
            info = {'url': 'https://www.pixiv.net/artworks/{}'.format(content['illust_id']), 'rank': content['rank']}
            print(info)
            page_infos.put(info)
    print("抓取json完毕... 共获得{}张图片或漫画的地址".format(page_infos.qsize()))


def parseImagePageForRealUrl():
    global page_infos, gLock, image_infos
    while not page_infos.empty():
        gLock.acquire()
        page_info = page_infos.get()
        gLock.release()
        to_parse_page_url = page_info['url']
        rank = page_info['rank']
        r = session.get(to_parse_page_url)
        try:
            image_url = \
                re.findall(r'","regular":"(https://i.pximg.net/img-master/img/\d+/\d+/\d+\d+/\d+/\d+/\d+.*?master1200\.jpg)","original"', r.text)[0]
        except Exception as e:
            image_url = ''
            print(e)
            print("获取图片URL失败", f'错误发生在{to_parse_page_url}')
        if image_url:
            info = {'url': image_url, 'rank': rank}
            print(info)
            gLock.acquire()
            image_infos.put(info)
            gLock.release()


def downloadPicture():
    global image_infos, gLock, final_target_dir
    while not image_infos.empty():
        gLock.acquire()
        image_info = image_infos.get()
        gLock.release()
        download_url = image_info['url']
        rank = image_info['rank']
        r = session.get(download_url, headers=headers_of_image)
        picture_path = final_target_dir + '/{}_{:0>4}_{}'.format(datetime.datetime.now().strftime("%Y-%m-%d"), rank,
                                                                 download_url.split('/')[-1])
        with open(picture_path, 'wb') as f:
            f.write(r.content)
        print(f'{picture_path} save successfully!')


def multiThreadParsePage():
    global THREAD_NUM
    threads = []
    for i in range(THREAD_NUM):
        t = threading.Thread(target=parseImagePageForRealUrl)
        threads.append(t)
        t.start()
        print(f'{i + 1}号线程成功启动，正在解析页面...')
    for i in range(THREAD_NUM):
        threads[i].join()
    print('页面解析完毕！')


def multiThreadDownloadImage():
    global THREAD_NUM
    threads = []
    for i in range(THREAD_NUM):
        t = threading.Thread(target=downloadPicture)
        threads.append(t)
        t.start()
        print(f'{i + 1}号线程成功启动，正在下载图片...')
    for i in range(THREAD_NUM):
        threads[i].join()
    print('图片下载完毕！')


if __name__ == '__main__':
    getAllImagePageUrls()
    multiThreadParsePage()
    multiThreadDownloadImage()