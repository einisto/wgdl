#!/usr/bin/env python3
import sys
import os
import requests
import json
import shutil
import platform
from getopt import GetoptError, getopt
from json.decoder import JSONDecodeError

DEFAULT_PATH = "/path/to/your/dir/"
TERMINAL_RED = "\x1b[38;2;255;0;0m"
TERMINAL_NC = "\033[0m"
OS_TYPE = platform.system()


def print_usage():
    print('''
    
    Usage: wgdl.py [-o | -x] [-t | -b | -q] [config]

    General:
        -o Set output folder name (final download location will be DEFAULT_PATH + folder)
        -x Override DEFAULT_PATH (use defined path instead)

    4chan:
        -t Enter 4chan thread url (simple)
        -b Enter 4chan board url (hoard, ignores sticky)
        -l Enable logging, allows downloading the same thread again without getting duplicates

    Wallhaven:
        -q Define wallhaven search query (use quotes with spaces)
        -r Set minimum resolution (e.g. "1920x1080")
        -s Set sorting method for results (date_added*, relevance, random, views, favorites)
        -p Define the amount of pages included in results

    * Default option

    ''')


def parse_arguments(args):
    output = None
    method = None
    param = ""
    config = {}
    pages = 1
    override = False
    logging = False

    try:
        opts, args = getopt(args[1:], "hlo:t:b:q:r:s:p:x:",
                            ["output=", "thread=", "board=",
                             "query=", "res=", "sorting=",
                             "pages=", "override="])
    except GetoptError:
        print_usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "-h":
            print_usage()
            sys.exit()
        elif opt in ("-o", "--output"):
            output = arg
        elif opt in ("-l", "--logging"):
            logging = True
        elif opt in ("-x", "--override"):
            override = True
            output = arg
        elif opt in ("-t", "--thread"):
            method = 0
            param = arg
        elif opt in ("-b", "--board"):
            method = 1
            param = arg
        elif opt in ("-q", "--query"):
            method = 2
            param = arg
        elif opt in ("-r", "--res"):
            config["resolutions"] = arg
        elif opt in ("-s", "--sorting"):
            config["sorting"] = arg
        elif opt in ("-p", "--pages"):
            pages = int(arg)

    if method is None or output is None:
        print(f"{TERMINAL_RED}Missing at least one of the required parameters. Please try again.{TERMINAL_NC}")
        sys.exit(1)

    return output, method, param, config, pages, override, logging


def create_folder(folder, override):
    if override:
        if os.path.isdir(folder):
            print(f"Folder {folder} already exists.")
        else:
            os.mkdir(folder)
            print(f"Folder {folder} created.")
    else:
        if os.path.isdir(DEFAULT_PATH + folder):
            print(f"Folder {DEFAULT_PATH + folder} already exists.")
        else:
            os.mkdir(DEFAULT_PATH + folder)
            print(f"Folder {DEFAULT_PATH + folder} created.")


def create_log(thread_id, ids):
    with open(DEFAULT_PATH + thread_id + ".log", "w") as f:
        for id in ids:
            f.write(id + "\n")


def read_log(thread_id):
    try:
        with open(DEFAULT_PATH + thread_id + ".log", "r") as f:
            log = set(f.read().splitlines())
    except IOError:
        print("Current thread does not have previous logs.")
        return set()

    return log


def make_json_request(url, config={}):
    for _ in range(5):
        req = requests.get(url, params=config)
        if req.status_code == 200:
            print(f"Request successful, {req.status_code} ({url})")
            return req.text
        else:
            print(f"Request unsuccessful, {req.status_code} ({url})")

    print(f"{TERMINAL_RED}Abandoning: {url} failed after 5 tries.{TERMINAL_NC}")
    sys.exit(1)


def get_image(url, filename):
    # stream=True to be memory efficient
    req = requests.get(url, stream=True)
    with open(filename, "wb") as f:
        shutil.copyfileobj(req.raw, f)

    print(f"{filename} done.")


def wallhaven_dl(query, folder, config, pages, override):
    path = folder if override else DEFAULT_PATH + folder
    config["q"] = query

    filecount = 0
    for pn in range(1, pages+1):
        config["page"] = pn
        print(f"Requesting page {pn}...")
        json_dump = make_json_request("https://wallhaven.cc/api/v1/search", config)
        parse_json = json.loads(json_dump)
        for d in parse_json["data"]:
            url = d["path"]
            get_image(url, path + url.split("/")[-1])
            filecount += 1

    print(f"Download finished. Total of {filecount} files were downloaded.")


def chan_dl(parse_json, folder, board, thread_id, logging):
    if logging:
        logs = read_log(thread_id)

    filecount = 0
    for p in parse_json["posts"]:
        try:
            img, ext = str(p["tim"]), p["ext"]
            if logging:
                if img in logs:
                    print(f"{img}{ext} skipped (found in logs).")
                    continue
                else:
                    logs.add(img)
        except KeyError:
            continue

        filename = folder + img + ext
        get_image(f"https://i.4cdn.org/{board}/{img}{ext}", filename)
        filecount += 1

    if logging:
        create_log(thread_id, logs)

    return filecount


def chan_basic(url, folder, override, logging):
    board, thread_id = url.split("/")[-3], url.split("/")[-1]
    json_dump = make_json_request(f"https://a.4cdn.org/{board}/thread/{thread_id}.json")
    parse_json = json.loads(json_dump)
    filecount = chan_dl(parse_json, folder if override else DEFAULT_PATH + folder, board, thread_id, logging)

    print(f"Download finished. Total of {filecount} files were downloaded.")


def chan_hoard(url, folder, override, logging):
    if "catalog" in url:
        board = url.split("/")[-2]
    else:
        board = url.split("/")[-1]

    board_json_dump = make_json_request(f"https://a.4cdn.org/{board}/catalog.json")
    parse_board_json = json.loads(board_json_dump)

    filecount_total = 0
    for page in parse_board_json:
        for t in page["threads"]:
            try:
                sticky = t["sticky"]
                print("Sticky skipped.")
                continue
            except KeyError:
                thread_id = t["no"]
                json_dump = make_json_request(f"https://a.4cdn.org/{board}/thread/{thread_id}.json")

                try:
                    parse_json = json.loads(json_dump)
                except JSONDecodeError:
                    print(f"Failed parsing json. Skipping thread {thread_id}.")
                    continue

                print(f"Downloading from thread {board}/{thread_id}.")
                filecount = chan_dl(parse_json, folder if override else DEFAULT_PATH + folder, board, thread_id, logging)

            filecount_total += filecount

    print(f"Download finished. Total of {filecount_total} files were downloaded.")


def main(folder, method, param, config, pages, override, logging):
    global DEFAULT_PATH

    if OS_TYPE == "Windows":
        folder = folder + "\\"
        if DEFAULT_PATH[-1] != "\\":
            DEFAULT_PATH += "\\"
    elif OS_TYPE == "Linux" or OS_TYPE == "Darwin":
        folder = folder + "/"
        if DEFAULT_PATH[-1] != "/":
            DEFAULT_PATH += "/"

    create_folder(folder, override)

    if method == 0:
        # 4chan basic
        chan_basic(param, folder, override, logging)
    elif method == 1:
        # 4chan hoard
        chan_hoard(param, folder, override, logging)
    elif method == 2:
        # wallhaven
        wallhaven_dl(param, folder, config, pages, override)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] == "-h":
        print_usage()
        sys.exit(1)

    output, method, param, config, pages, override, logging = parse_arguments(sys.argv)
    main(output, method, param, config, pages, override, logging)
