import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urlparse
import fake_useragent
import os
import re
import sys
import threading
import queue
from dateutil.parser import parse

def get_input_with_timeout(prompt, timeout):
    q = queue.Queue()
    def target():
        q.put(input(prompt))
    thread = threading.Thread(target=target)
    thread.daemon = True # Allows thread to exit when main program exits
    thread.start()
    try:
        return q.get(timeout=timeout) # Wait for input with a timeout
    except queue.Empty:
        return None # No input received within the timeout

UserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'


def getUserAgent(fixed=False):
    if fixed:
        result = UserAgent
    else:
        ua = fake_useragent.UserAgent(fallback=UserAgent)
        result = ua.random

    return result

def getClearURL(url):
    newURL = url
    if url.startswith('http'):
        url = urlparse(url)
        path = url.path

        while '//' in path:
            path = path.replace('//', '/')

        newURL = '%s://%s%s' % (url.scheme, url.netloc, path)
        if url.query:
            newURL += '?%s' % url.query

    return newURL

def HTTPRequest(url, method='GET', **kwargs):
    url = getClearURL(url)
    method = method.upper()
    headers = kwargs.pop('headers', {})
    cookies = kwargs.pop('cookies', {})
    params = kwargs.pop('params', {})
    bypass = kwargs.pop('bypass', True)
    timeout = kwargs.pop('timeout', None)
    allow_redirects = kwargs.pop('allow_redirects', True)
    fixed_useragent = kwargs.pop('fixed_useragent', False)
    proxies = {}

    if 'User-Agent' not in headers:
        headers['User-Agent'] = getUserAgent(fixed_useragent)

    if params:
        method = 'POST'

    req = None
    try:
        req = requests.request(method, url, proxies=proxies, headers=headers, cookies=cookies, data=params, timeout=timeout, verify=False, allow_redirects=allow_redirects)
    except:
        req = ''

    req.encoding = 'UTF-8'
    
    return req

def get_file_paths_os_listdir(directory_path):
    """
    Returns a list of full file paths in the specified directory.
    """
    file_paths = []
    for filename in os.listdir(directory_path):
        full_path = os.path.join(directory_path, filename)
        if os.path.isfile(full_path):
            file_paths.append(full_path)
    return file_paths

def renameFile(file, newFilePath):
    try:
        os.rename(file, newFilePath)
        print(f"File '{file}' renamed to '{newFilePath}' successfully.")
    except FileNotFoundError:
        print(f"Error: The file '{file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

directory_path = ''
all_entries = os.listdir(directory_path)

files = get_file_paths_os_listdir(directory_path)

for file in files:
    filename = file.rsplit('\\', 1)[-1]

    slug = filename.split('lubed.', 1)[-1].split('.4k')[0].replace('.', '-').strip()

    headers = {'x-site': 'https://lubed.com'}

    url = 'https://lubed.com/api/releases/%s' % slug

    req = HTTPRequest(url, headers=headers)

    data = None
    if req.ok:
        data = req.json()

    if data:
        rawDate = data['releasedAt']
        date = parse(rawDate)
        parsedDate = date.strftime('%y.%m.%d')
        actorName = data['actors'][0]['name'].strip().lower().replace(' ', '.')
        newFilename = 'lubed.%s.%s.%s.4k.mp4' % (parsedDate, actorName, slug.replace('-', '.'))
        newFilePath = '%s\\%s' % (file.rsplit('\\', 1)[0], newFilename)

        user_input = get_input_with_timeout('Change filename to: %s' % newFilePath, None)

        if not user_input:
            renameFile(file, newFilePath)
        elif user_input == 'y':
            actorName = data['actors'][1]['name'].strip().lower().replace(' ', '.')
            newFilename = 'lubed.%s.%s.%s.4k.mp4' % (parsedDate, actorName, slug.replace('-', '.'))
            newFilePath = '%s\\%s' % (file.rsplit('\\', 1)[0], newFilename)
            user_input = get_input_with_timeout('Change filename to: %s' % newFilePath, None)
            if not user_input:
                renameFile(file, newFilePath)
            else:
                break
        else:
            break


# print(json.dumps(data, indent=2))