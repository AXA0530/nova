import re
import time
import random
import logging
import threading
import json
import os
import signal
import sys
from urllib.parse import urljoin, urlparse, parse_qs, urlunparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from lxml import etree
import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Set, Tuple, Any

HEADERS_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36 OPR/111.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_7_10) AppleWebKit/605.1.15 Version/15.6.4 Safari/605.1.15"
]
COOKIE_POOL = []
REQUEST_TIMEOUT = 18
MAX_RETRY = 5
SLEEP_MIN = 0.15
SLEEP_MAX = 2.2
THREAD_NUM = 12
SAVE_CSV = True
SAVE_JSON = True
SAVE_HTML = False
SAVE_LOG_FILE = True
OUTPUT_CSV = "spider_result.csv"
OUTPUT_JSON = "spider_result.json"
HTML_SAVE_DIR = "html_cache"
CHECKED_URL_FILE = "visited_urls.txt"
FAILED_URL_FILE = "failed_urls.txt"
QUEUE_SAVE_FILE = "crawl_queue.txt"
PROXY_LIST = []
USE_PROXY = False
MAX_DEPTH = 3
ALLOW_DOMAIN = None
DENY_SUFFIX = (".jpg",".jpeg",".png",".bmp",".gif",".webp",".mp4",".mp3",".m4a",".zip",".rar",".7z",".tar",".gz",".exe",".apk",".pdf",".doc",".docx",".xls",".xlsx")
DENY_KEYWORD = ["#","javascript:","mailto:","tel:","weixin:"]
MAX_BODY_LENGTH = 2000
PAUSE_FLAG = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y‑%m‑%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
if SAVE_LOG_FILE:
    file_handler = logging.FileHandler("spider_run.log",encoding="utf‑8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s","%Y‑%m‑%d %H:%M:%S"))
    logging.getLogger().addHandler(file_handler)

def signal_handler(sig,frame):
    global PAUSE_FLAG
    logging.warning("收到停止信号，准备安全退出，正在保存缓存数据...")
    PAUSE_FLAG = True

signal.signal(signal.SIGINT,signal_handler)

class PowerfulSpider:
    def __init__(self):
        self.result_list:List[Dict[str,Any]] = []
        self.visited:Set[str] = set()
        self.failed_set:Set[str] = set()
        self.waiting_urls:Set[str] = set()
        self.depth_map:Dict[str,int] = dict()
        self.lock = threading.Lock()
        self.load_visited()
        self.load_failed()
        self.load_wait_queue()
        if SAVE_HTML and not os.path.exists(HTML_SAVE_DIR):
            os.makedirs(HTML_SAVE_DIR)

    def url_normalize(self,url:str)->str:
        try:
            parse = urlparse(url)
            query = parse_qs(parse.query)
            new_query = []
            for k,v in sorted(query.items()):
                for val in v:
                    new_query.append(f"{k}={val}")
            new_query_str = "&".join(new_query)
            new_url = urlunparse((parse.scheme,parse.netloc,parse.path,parse.params,new_query_str,""))
            return new_url.rstrip("/")
        except:
            return url.strip()

    def load_visited(self):
        if not os.path.exists(CHECKED_URL_FILE):
            return
        with open(CHECKED_URL_FILE,"r",encoding="utf‑8") as f:
            for line in f:
                url = line.strip()
                if url:
                    norm_url = self.url_normalize(url)
                    self.visited.add(norm_url)

    def load_failed(self):
        if not os.path.exists(FAILED_URL_FILE):
            return
        with open(FAILED_URL_FILE,"r",encoding="utf‑8") as f:
            for line in f:
                url = line.strip()
                if url:
                    self.failed_set.add(url)

    def load_wait_queue(self):
        if not os.path.exists(QUEUE_SAVE_FILE):
            return
        with open(QUEUE_SAVE_FILE,"r",encoding="utf‑8") as f:
            for line in f:
                line = line.strip()
                if not line or "||" not in line:
                    continue
                url,depth_str = line.split("||")
                try:
                    d = int(depth_str)
                    norm_link = self.url_normalize(url)
                    self.waiting_urls.add(norm_link)
                    self.depth_map[norm_link] = d
                except:
                    continue

    def save_visited(self,url:str):
        norm_url = self.url_normalize(url)
        with self.lock:
            if norm_url not in self.visited:
                self.visited.add(norm_url)
                with open(CHECKED_URL_FILE,"a",encoding="utf‑8") as f:
                    f.write(norm_url+"\n")

    def save_failed(self,url:str):
        with self.lock:
            if url not in self.failed_set:
                self.failed_set.add(url)
                with open(FAILED_URL_FILE,"a",encoding="utf‑8") as f:
                    f.write(url+"\n")

    def save_wait_queue(self):
        with self.lock:
            with open(QUEUE_SAVE_FILE,"w",encoding="utf‑8") as f:
                for u in self.waiting_urls:
                    d = self.depth_map.get(u,0)
                    f.write(f"{u}||{d}\n")

    def get_random_header(self):
        return {
            "User‑Agent":random.choice(HEADERS_POOL),
            "Accept‑Language":"zh‑CN,zh;q=0.9,en;q=0.8",
            "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept‑Encoding":"gzip, deflate",
            "Connection":"keep‑alive",
            "Referer":"https://www.baidu.com/"
        }

    def get_cookie(self):
        if len(COOKIE_POOL) == 0:
            return {}
        c = random.choice(COOKIE_POOL)
        return {"Cookie":c}

    def get_proxy(self):
        if not USE_PROXY or len(PROXY_LIST)==0:
            return None
        p = random.choice(PROXY_LIST)
        return {"http":p,"https":p}

    def url_filter(self,url:str)->bool:
        if not url.startswith("http"):
            return False
        if url.endswith(DENY_SUFFIX):
            return False
        for kw in DENY_KEYWORD:
            if kw in url:
                return False
        if ALLOW_DOMAIN is not None and ALLOW_DOMAIN not in url:
            return False
        return True

    def url_join_full(self,base:str,href:str)->str:
        try:
            full = urljoin(base,href)
            return self.url_normalize(full)
        except:
            return href

    def http_request(self,url:str)->Optional[str]:
        retry = 0
        proxies = self.get_proxy()
        while retry < MAX_RETRY and not PAUSE_FLAG:
            try:
                time.sleep(random.uniform(SLEEP_MIN,SLEEP_MAX))
                headers = {**self.get_random_header(),**self.get_cookie()}
                resp = requests.get(
                    url,
                    headers=headers,
                    proxies=proxies,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True
                )
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding
                html_text = resp.text
                if SAVE_HTML:
                    name = str(hash(url))+".html"
                    path = os.path.join(HTML_SAVE_DIR,name)
                    with open(path,"w",encoding="utf‑8") as fw:
                        fw.write(html_text)
                return html_text
            except requests.exceptions.HTTPError as e:
                retry +=1
                code = e.response.status_code if e.response else 0
                logging.warning(f"HTTP {code} | {url[:65]} 重试 {retry}/{MAX_RETRY}")
            except requests.exceptions.Timeout:
                retry +=1
                logging.warning(f"请求超时 | {url[:65]} 重试 {retry}/{MAX_RETRY}")
            except Exception as e:
                retry +=1
                logging.warning(f"网络异常 | {url[:65]} 重试 {retry}/{MAX_RETRY} err:{str(e)[:55]}")
        logging.error(f"请求彻底失败：{url[:80]}")
        self.save_failed(url)
        return None

    def parse_xpath(self,html:str,xpath_exp:str):
        tree = etree.HTML(html)
        if not tree:
            return []
        return tree.xpath(xpath_exp)

    def parse_css_selector(self,html:str,selector:str):
        soup = BeautifulSoup(html,"lxml")
        res = soup.select(selector)
        return [x.get_text(strip=True) for x in res]

    def extract_all_links(self,html:str,base_url:str)->List[str]:
        link_set = set()
        tree = etree.HTML(html)
        if not tree:
            return []
        raw_links = tree.xpath("//a/@href")
        for raw in raw_links:
            full = self.url_join_full(base_url,raw)
            if self.url_filter(full):
                link_set.add(full)
        return list(link_set)

    def extract_text_by_xpath(self,html:str,exp:str)->str:
        res = self.parse_xpath(html,exp)
        if len(res)>0:
            return str(res[0]).strip()
        return ""

    def clean_full_text(self,text:str,limit=MAX_BODY_LENGTH):
        if not text:
            return ""
        text = re.sub(r"\n+"," ",text)
        text = re.sub(r"\r+"," ",text)
        text = re.sub(r"\s+"," ",text)
        text = re.sub(r"\t+"," ",text)
        return text.strip()[:limit]

    def task_handler(self,url:str,depth:int):
        global PAUSE_FLAG
        if PAUSE_FLAG:
            return
        norm_url = self.url_normalize(url)
        if norm_url in self.visited:
            return
        if depth>MAX_DEPTH:
            return
        html = self.http_request(url)
        if not html:
            self.save_visited(url)
            return
        title_str = self.extract_text_by_xpath(html,"//title/text()")
        keyword_str = self.extract_text_by_xpath(html,"//meta[@name='keywords']/@content")
        desc_str = self.extract_text_by_xpath(html,"//meta[@name='description']/@content")
        h1_str = self.extract_text_by_xpath(html,"//h1//text()")
        h2_str_list = self.parse_xpath(html,"//h2//text()")
        h2_text = " | ".join([x.strip() for x in h2_str_list if x.strip()])
        body_raw_list = self.parse_xpath(html,"//body//text()")
        body_raw = "".join(body_raw_list)
        body_clean = self.clean_full_text(body_raw)
        sub_links = self.extract_all_links(html,url)
        item = {
            "url":url,
            "norm_url":norm_url,
            "depth":depth,
            "title":title_str,
            "h1":h1_str,
            "h2_list":h2_text,
            "keywords":keyword_str,
            "description":desc_str,
            "body_preview":body_clean,
            "sub_link_count":len(sub_links),
            "crawl_timestamp":time.time(),
            "crawl_time":time.strftime("%Y‑%m‑%d %H:%M:%S")
        }
        with self.lock:
            self.result_list.append(item)
        self.save_visited(url)
        logging.info(f"深度{depth} 采集成功 {url[:72]}")
        next_depth = depth + 1
        if next_depth <= MAX_DEPTH and not PAUSE_FLAG:
            for link in sub_links:
                link_norm = self.url_normalize(link)
                if link_norm not in self.visited and link_norm not in self.waiting_urls:
                    self.waiting_urls.add(link_norm)
                    self.depth_map[link_norm] = next_depth

    def start_crawl(self,seed_list:List[str]):
        global PAUSE_FLAG
        for s in seed_list:
            s_norm = self.url_normalize(s)
            if self.url_filter(s) and s_norm not in self.visited:
                self.waiting_urls.add(s_norm)
                self.depth_map[s_norm] = 0
        total_init = len(self.waiting_urls)
        logging.info(f"爬虫启动，初始任务:{total_init}，最大深度:{MAX_DEPTH}，并发数:{THREAD_NUM}")
        while len(self.waiting_urls)>0 and not PAUSE_FLAG:
            batch = list(self.waiting_urls)[:THREAD_NUM*4]
            for u in batch:
                self.waiting_urls.discard(u)
            self.save_wait_queue()
            with ThreadPoolExecutor(max_workers=THREAD_NUM) as pool:
                task_dict = {}
                for u in batch:
                    d = self.depth_map.get(u,0)
                    task = pool.submit(self.task_handler,u,d)
                    task_dict[task] = u
                for future in as_completed(task_dict):
                    if PAUSE_FLAG:
                        pool.shutdown(wait=False,cancel_futures=True)
                        break
                    try:
                        future.result()
                    except Exception as err:
                        logging.error(f"线程任务异常 {str(err)}")
        self.save_wait_queue()
        if PAUSE_FLAG:
            logging.warning("爬虫被手动中断，队列状态已保存")
        else:
            logging.info("全部URL队列处理完成")

    def export_data(self):
        if len(self.result_list)==0:
            logging.info("无采集数据，跳过导出")
            return
        if SAVE_CSV:
            df = pd.DataFrame(self.result_list)
            df.to_csv(OUTPUT_CSV,index=False,encoding="utf‑8‑sig")
        if SAVE_JSON:
            with open(OUTPUT_JSON,"w",encoding="utf‑8") as f:
                json.dump(self.result_list,f,ensure_ascii=False,indent=2)
        logging.info(f"数据导出完成，总共 {len(self.result_list)} 条网页数据")

    def print_statistics(self):
        logging.info("==========爬取统计报表==========")
        logging.info(f"已访问链接总数：{len(self.visited)}")
        logging.info(f"成功解析页面：{len(self.result_list)}")
        logging.info(f"请求失败页面：{len(self.failed_set)}")
        logging.info(f"剩余待爬队列：{len(self.waiting_urls)}")
        logging.info("================================")

if __name__ == "__main__":
    spider = PowerfulSpider()
    seed_urls = [
        "https://www.baidu.com",
        "https://www.bing.com",
        "https://github.com",
        "https://www.bilibili.com",
        "https://www.csdn.net"
    ]
    spider.start_crawl(seed_urls)
    spider.export_data()
    spider.print_statistics()
    logging.info("爬虫全部任务执行完毕")