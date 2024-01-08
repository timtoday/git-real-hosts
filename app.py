import os
import re
import subprocess
import sys
import time
from datetime import datetime
from tcping import Ping

import requests

hosts_map = {}

hosts_start_tag = "###### start tim github hosts"
hosts_end_tag = "###### end tim github hosts ######"


def check_ip_delay(ip):
    # -c 选项表示发送的请求次数，1 表示发送一次
    # -W 选项表示等待每次回复的超时时间，这里设置为 1000 毫秒
    my_timeout = 5
    start_time = time.time()
    p = subprocess.Popen(['ping', ip])
    try:
        p.wait(my_timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        return 666666
    end_time = time.time()
    delay = end_time - start_time
    return delay


def pingip(ipAddress, request_nums):
    """
    ping ip
    :param ipAddress:
    :param request_nums: 请求次数
    :return: 丢包率loss和统计结果res
    """
    ping = Ping(ipAddress, timeout=1)
    ping.ping(request_nums)
    res = ping.result.table
    ret = ping.result.raw
    retlist = list(ret.split('\n'))
    ttl = retlist[3].split(',')[2].split('average =')[1].replace("ms", "")
    if "time out" in ttl:
        ttl = 0
    return float(ttl), res


def getip(website: str):
    """
    # 获取IP地址
    """
    # request = requests.get('https://ipaddress.com/website/' + website)
    request = requests.get('https://sites.ipaddress.com/%s/' % website)
    if request.status_code == 200:
        ips = re.findall(r"<strong>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}?)</strong>", request.text)
        min_ttl = 500
        fast_ip = ""
        c = 0
        print("start check :" + website)
        print("found (" + str(len(ips)) + ") ips")
        for ip_item in ips:
            if c > 5:
                break
            c = c + 1
            ttl, res = pingip(ip_item, 3)
            if min_ttl > ttl > 0:
                fast_ip = ip_item
                min_ttl = ttl

        if fast_ip is not "":
            print("fast ip is:" + fast_ip)
            hosts_map[website] = fast_ip
        else:
            print("ip can't connect")


def auto_hosts():
    host_file = "/etc/hosts"
    if sys.platform.startswith('win'):
        host_file = "C:\Windows\System32\drivers\etc\hosts"
    f = open(host_file, "r")
    old_hosts = f.read()
    f.close()
    if hosts_start_tag in old_hosts:
        old_path = old_hosts.split(hosts_start_tag)[1].split(hosts_end_tag)[0]
        old_hosts = old_hosts.replace(old_path, "").replace("\n" + hosts_start_tag, "").replace(hosts_end_tag, "")

    old_hosts = old_hosts + "\n"
    old_hosts = old_hosts + hosts_start_tag + " AT %s ###### \n" % str(datetime.now())

    for key, val in hosts_map.items():
        old_hosts = old_hosts + "%s    %s\n" % (val, key)
    old_hosts = old_hosts + hosts_end_tag

    file = open(host_file, 'w')
    file.write(old_hosts)
    file.close()
    print('hosts edit ok')


def reload_dns():
    # WINDOWS
    if sys.platform.startswith('win'):
        os.system('ipconfig /flushdns')

    # LINUX
    if sys.platform.startswith('linux'):
        os.system('sudo resolvectl flush-caches')

    # MAC
    if sys.platform.startswith('darwin'):
        os.system('sudo -S dscacheutil -flushcache')


def main():
    f = open("domains.txt", "r")
    domains = f.read().split("\n")
    f.close()
    for dd in domains:
        getip(dd)
    print(hosts_map)
    if hosts_map is not {}:
        auto_hosts()
        reload_dns()


if __name__ == '__main__':
    print("get new IP")
    main()
