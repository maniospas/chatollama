import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote, unquote
import html
import re
import wikipedia
import tools

TOOLS = {}
def tool(func):
    TOOLS[func.__name__] = func
    return func


def parse_args(args):
    if "," in args: delim = ","
    else: delim = " "
    return [arg.strip() for arg in args.split(delim) if arg.strip()]

@tool
def tools(messages, arg):
    assert not arg, "No argument expected"
    items = []
    for key, func in TOOLS.items():
        doc = getattr(func, "__doc__", None)
        if not doc: continue
        doc = doc.strip()
        items.append(f"{doc}")
    ret = "coding tools <br><hr>@ask(text) to get an agent reply<br>@read(text) to get a user input given some text<br>@print(text) to print some text<br>"+"<br>".join(items)+"<br><hr>"
    return ret

@tool
def echo(messages, arg):
    """@echo(user) or @echo(system) or @echo(assistant) to get the last message of the respective role"""
    assert arg in ["user", "system", "assistant"], "Can only echo one of: user, system, assistant"
    users = [m["content"] for m in messages if m["role"] == arg]
    assert users, "No previous user message"
    return users[-1]

@tool
def add(messages, arg):
    """@add(num1,num2)"""
    arg = parse_args(arg)
    assert len(arg)==2, "Too many values to add: "+str(arg)
    return str(float(arg[0]) + float(arg[1]))

@tool
def web(messages, arg):
    """@web(query) – DuckDuckGo HTML scraper without bs4, returns clean final URLs."""
    api_url = "https://duckduckgo.com/html/?q=" + quote(arg)
    req = Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
    html = urlopen(req).read().decode("utf-8")
    results = []
    contents = dict()
    marker = 'class="result__a"'
    idx = 0
    while True:
        pos = html.find(marker, idx)
        if pos == -1: break
        start = html.rfind("<a", 0, pos)
        if start == -1:
            idx = pos + len(marker)
            continue
        href_pos = html.find('href="', start, pos + 200)
        if href_pos == -1:
            idx = pos + len(marker)
            continue
        href_start = href_pos + len('href="')
        href_end = html.find('"', href_start)
        if href_end == -1:
            idx = pos + len(marker)
            continue
        url = html[href_start:href_end]
        if url.startswith("//duckduckgo.com/l/?"):
            url = "https:" + url
        if "uddg=" in url:
            # extract target in uddg=
            after = url.split("uddg=", 1)[1]
            target = after.split("&", 1)[0]
            url = unquote(target)
        if url.startswith("http") and url not in results:
            content_start = html.find('class="result__snippet"', href_end)
            content_start = html.find(">", content_start)+1
            content_end = html.find("</a>", content_start)
            contents[url] = html[content_start:content_end]
            results.append(url)
            if len(results) == 10: break
        idx = pos + len(marker)
    out = f"<h3>Search results for: {arg}</h3>"
    for link in results:
        page = contents.get(link, "No preview")
        out += (
            "<details style='margin-bottom:10px;'>"
            "<summary>"
            f"<a href='{link}' target='_blank'>{link}</a>"
            "</summary>"
            f"<div style='padding:10px; border:1px solid #ccc; margin-top:5px; "
            f"white-space:pre-wrap; font-size:90%; max-height:400px; overflow:auto;'>"
            f"{page}"
            "</div>"
            "</details>"
        )
    return out

@tool
def wiki(messages, query):
    """@wiki(query) – Wikipedia search"""
    wikipedia.set_lang("en")
    results = wikipedia.search(query)[:10]
    output = "\n\n"
    for i, title in enumerate(results):
        try:
            page = wikipedia.page(title)
            summary = wikipedia.summary(title, sentences=3)
            output += f"# [{title}]({page.url})\n"
            output += f"## Summary\n{summary}\n\n"
            if i < 3:
                full_content = page.content
                output += f"## Full Content\n{full_content}\n\n"
        except:
            pass
    return output

@tool
def wikishort(messages, query):
    """wikishort(query) – Wikipedia search that only presents result summaries"""
    wikipedia.set_lang("en")
    results = wikipedia.search(query)[:10]
    output = "\n\n"
    for i, title in enumerate(results):
        try:
            page = wikipedia.page(title)
            summary = wikipedia.summary(title, sentences=3)
            output += f"# [{title}]({page.url})\n"
            output += f"{summary}\n\n"
        except:
            pass
    return output
