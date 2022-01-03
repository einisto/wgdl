#!/usr/bin/env python
from getopt import GetoptError, getopt
from json.decoder import JSONDecodeError
import sys, os, requests, json, shutil, platform

DEFAULT_PATH = "C:\\Users\\terry\\Pictures\\wallpapers\\"
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

    Wallhaven:
        -q Define wallhaven search query (use quotes with spaces)
        -r Set minimum resolution (e.g. "1920x1080")
        -s Set sorting method for results (date_added*, relevance, random, views, favorites)
        -p Define the amount of pages included in results

    * Default option

    ''')


def create_folder(folder, override):
    global DEFAULT_PATH

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


def wallhaven(query, folder, config, pages, override):
    global DEFAULT_PATH

    query = query.replace(" ", "%20")
    config["q"] = query

    count_img = 0
    for pn in range(1, pages+1):
        # using library's built-in parameter passing
        config["page"] = pn
        json_dump = requests.get("https://wallhaven.cc/api/v1/search", params=config).text
        parse_json = json.loads(json_dump)
        for d in parse_json["data"]:
            url = d["path"]
            if override:
                filename = folder + url.split("/")[-1]
            else:
                filename = DEFAULT_PATH + folder + url.split("/")[-1]
            # stream=True to be memory efficient
            resp = requests.get(url, stream=True)
            with open(filename, "wb") as f:
                shutil.copyfileobj(resp.raw, f)
            count_img += 1
            print(f"{filename} done.")

    print(f"Download finished. Total of {str(count_img)} files were downloaded.")


def chan_dl(parse_json, path, board):
    filecount = 0
    for p in parse_json["posts"]:
        try:
            img, ext = str(p["tim"]), p["ext"]
        except KeyError:
            continue
        
        filename = path + img + ext
        img_url = f"https://i.4cdn.org/{board}/{img}{ext}"
        resp = requests.get(img_url, stream=True)
        with open(filename, "wb") as f:
            shutil.copyfileobj(resp.raw, f)
        filecount += 1
        print(f"{filename} done.")

    return filecount


def chan_basic(url, folder, override):
    global DEFAULT_PATH

    board, id = url.split("/")[-3], url.split("/")[-1]
    json_url = f"https://a.4cdn.org/{board}/thread/{id}.json"
    json_dump = requests.get(json_url).text
    parse_json = json.loads(json_dump)
    if override:
        filecount = chan_dl(parse_json, folder, board)
    else:
        filecount = chan_dl(parse_json, DEFAULT_PATH + folder, board)

    print(f"Download finished. Total of {str(filecount)} files were downloaded.")


def chan_hoard(url, folder, override):
    global DEFAULT_PATH

    if "catalog" in url:
        board = url.split("/")[-2]
    else:
        board = url.split("/")[-1]

    board_url = f"https://a.4cdn.org/{board}/catalog.json"
    board_json_dump = requests.get(board_url).text
    parse_board_json = json.loads(board_json_dump)
    filecount_total = 0

    for page in parse_board_json:
        for t in page["threads"]:
            try:
                sticky = t["sticky"]
                print("Sticky skipped.")
                continue
            except KeyError:
                id = t["no"]
                json_url = f"https://a.4cdn.org/{board}/thread/{id}.json"
                json_dump = requests.get(json_url).text
                try:
                    parse_json = json.loads(json_dump)
                except JSONDecodeError:
                    print(f"Failed parsing json. Skipping thread {id}.")
                    continue
                print(f"Downloading from thread {board}/{str(id)}.")
                if override:
                    filecount = chan_dl(parse_json, folder, board)
                else:
                    filecount = chan_dl(parse_json, DEFAULT_PATH + folder, board)

            filecount_total += filecount
        
    print(f"Download finished. Total of {str(filecount_total)} files were downloaded.")


def main(folder, method, param, config, pages, override):
    if OS_TYPE == "Windows":
        folder = folder + "\\"
    elif OS_TYPE == "Linux" or OS_TYPE == "Darwin":
        folder = folder + "/"

    create_folder(folder, override)

    match method:
        case 0:
            # 4chan basic
            chan_basic(param, folder, override)
        case 1:
            # 4chan hoard
            chan_hoard(param, folder, override)
        case 2:
            # wallhaven
            wallhaven(param, folder, config, pages, override)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] == "-h":
        print_usage()
        sys.exit(2)
    
    # parsing flags
    output = None
    method = None
    param = ""
    config = {}
    pages = 1
    override = False

    try:
        opts, args = getopt(sys.argv[1:], "ho:t:b:q:r:s:p:x:",
                            ["output=", "thread=", "board=",
                             "query=", "res=", "sorting=",
                             "pages=", "override="])
    except GetoptError:
        print_usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt == "-h":
            print_usage()
            sys.exit()
        elif opt in ("-o", "--output"):
            output = arg
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
        print("Missing at least one of the required parameters. Please try again.")
        sys.exit(2)

    main(output, method, param, config, pages, override)
