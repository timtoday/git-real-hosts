import os
import re
import ssl
import sys
from datetime import datetime
import asyncio
import aiohttp
import aioping
import chardet
import ctypes
import logging
import tempfile

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HOSTS_START_TAG = "###### start tim github hosts"
HOSTS_END_TAG = "###### end tim github hosts ######"

hosts_map = {}


def is_win_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        logging.error(f"Failed to check admin status: {e}")
        return False


def run_as_win_admin():
    script = sys.argv[0]
    params = ' '.join([script] + sys.argv[1:])
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    except Exception as e:
        logging.error(f"Failed to elevate privileges: {e}")


async def check_ip_delay(ip, timeout=5):
    try:
        delay = await aioping.ping(ip, timeout=timeout)
        return delay
    except Exception as e:
        logging.error(f"Error pinging {ip}: {e}")
        return 666666


async def ping_ip(ip_address):
    """
    Asynchronously ping IP address
    :param ip_address: IP address to ping
    :return: Average TTL and raw result
    """
    try:
        delay = await aioping.ping(ip_address, timeout=3) * 1000
        print("Ping response in %s ms" % delay)
        return delay
    except TimeoutError:
        print("Timed out")
    return 9999


async def get_ip(website):
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.get(f'https://sites.ipaddress.com/{website}', timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    pattern = r'<a href="https://www\.ipaddress\.com/ipv4/(\d+\.\d+\.\d+\.\d+)">\1</a>'
                    ips = re.findall(pattern, html)
                    min_ttl = 500
                    fast_ip = ""
                    c = 0
                    logging.info(f"start check: {website}")
                    logging.info(f"found ({len(ips)}) ips")
                    for ip_item in ips:
                        if c > 5:
                            break
                        c += 1
                        ttl = await ping_ip(ip_item)
                        if min_ttl > ttl > 0:
                            fast_ip = ip_item
                            min_ttl = ttl

                    if fast_ip:
                        logging.info(f"fast ip is: {fast_ip}")
                        hosts_map[website] = fast_ip
                    else:
                        logging.info("ip can't connect")
    except Exception as e:
        logging.error(f"Error fetching IP for {website}: {e}")


def str_mid(text, start_tag, end_tag):
    result = text
    start_pos = text.find(start_tag)
    if start_pos != -1:
        result = text[start_pos:]
        end_pos = result.find(end_tag)
        if end_pos != -1:
            result = result[:end_pos + len(end_tag)]
    return None


def auto_hosts():
    host_file = "/etc/hosts"
    if sys.platform.startswith('win'):
        host_file = "C:\\Windows\\System32\\drivers\\etc\\hosts"

    try:
        with open(host_file, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            logging.info(f"Detected encoding: {result['encoding']}")
            old_hosts = raw_data.decode(result['encoding'])

        old_content = str_mid(old_hosts, HOSTS_START_TAG, HOSTS_END_TAG)
        if old_content is not None:
            old_hosts = old_hosts.replace(old_content, "").strip()

        if not old_hosts.endswith("\n"):
            old_hosts += "\n"
        old_hosts += f"{HOSTS_START_TAG} AT {datetime.now()} ###### \n"

        for key, val in hosts_map.items():
            old_hosts += f"{val}    {key}\n"
        old_hosts += HOSTS_END_TAG

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(old_hosts)
            temp_path = temp_file.name

        os.replace(temp_path, host_file)
        logging.info('hosts edit ok')
    except Exception as e:
        logging.error(f"Error updating hosts file: {e}")


def reload_dns():
    try:
        if sys.platform.startswith('win'):
            os.system('ipconfig /flushdns')
        elif sys.platform.startswith('linux'):
            os.system('sudo resolvectl flush-caches')
        elif sys.platform.startswith('darwin'):
            os.system('sudo -S dscacheutil -flushcache')
    except Exception as e:
        logging.error(f"Error reloading DNS: {e}")


async def main():
    try:
        with open("domains.txt", "r") as f:
            domains = [line.strip() for line in f if not line.startswith("#")]

        tasks = [get_ip(domain) for domain in domains]
        await asyncio.gather(*tasks)

        logging.info(hosts_map)
        if hosts_map:
            auto_hosts()
            reload_dns()
    except Exception as e:
        logging.error(f"Error in main function: {e}")


if __name__ == '__main__':
    print("get new IP")
    if sys.platform.startswith('win'):
        if is_win_admin():
            asyncio.run(main())
        else:
            run_as_win_admin()
    else:
        asyncio.run(main())
