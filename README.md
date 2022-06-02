## Imagescraper for 4chan and wallhaven

### Usage
* Change DEFAULT_PATH to match the folder you want to use as default output
* Single thread: insert a thread URL (e.g. https://boards.4channel.org/g/thread/85738921)
* All threads from a certain board: insert a catalog URL (e.g. https://boards.4channel.org/g/catalog)

```
    
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


```
