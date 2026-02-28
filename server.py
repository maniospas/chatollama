#!/usr/bin/env python3
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote, unquote
import html
import re
import wikipedia

TOOLS = {}
def tool(func):
    TOOLS[func.__name__] = func
    return func

class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_html_error(self, code, description):
        html = description.strip().encode("utf-8")

        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def do_GET(self):
        if self.path == "/tools":
            tool_list = list(TOOLS.keys())
            payload = json.dumps(tool_list).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def do_POST(self):
        if not self.path.startswith("/tool/"):
            return super().do_POST()
        name = self.path[len("/tool/"):]
        func = TOOLS.get(name)
        if func is None:
            self.send_html_error(404, f"<b>@{name}</b> not found - such as tool does not exist")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
        except Exception as e:
            self.send_html_error(400, f"Invalid JSON: {e}")
            return
        if not isinstance(data, dict):
            self.send_html_error(400, "JSON must be an object containing 'messages' and 'arg'")
            return
        if "messages" not in data or "arg" not in data:
            self.send_html_error(400, "JSON must contain both 'messages' and 'arg'")
            return
        messages = data["messages"]
        arg = data["arg"]
        try:
            result = func(messages, arg)
        except Exception as e:
            self.send_html_error(500, f"<b>@{name}</b> error - {e}")
            return
        if not isinstance(result, str):
            result = str(result)
        result_bytes = result.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(result_bytes)))
        self.end_headers()
        self.wfile.write(result_bytes)

# ----------------------------

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
    """@search(query) – DuckDuckGo HTML scraper without bs4, returns clean final URLs."""

    api_url = "https://duckduckgo.com/html/?q=" + quote(arg)
    req = Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
    html = urlopen(req).read().decode("utf-8")

    results = []
    contents = dict()
    marker = 'class="result__a"'
    idx = 0
    while True:
        pos = html.find(marker, idx)
        if pos == -1:
            break
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
            if len(results) == 10:
                break
        idx = pos + len(marker)
    out = f"<h3>Search results for: {arg}</h3>"
    for link in results:
        page = contents.get(link, "No preview")
        # try:
        #     req2 = Request(link, headers={"User-Agent": "Mozilla/5.0"})
        #     page = urlopen(req2, timeout=5).read().decode("utf-8", errors="ignore")
        #     page = re.sub(r'<script[\s\S]*?</script>', '', page, flags=re.IGNORECASE)
        #     page = re.sub(r'<head[\s\S]*?</head>', '', page, flags=re.IGNORECASE)
        #     page = re.sub(r'</div\s*>', '\n', page, flags=re.IGNORECASE)
        #     page = re.sub(r'<div\s*>', '\n', page, flags=re.IGNORECASE)
        #     page = re.sub(r'</p\s*>', '\n', page, flags=re.IGNORECASE)
        #     page = re.sub(r'<p\s*>', '\n', page, flags=re.IGNORECASE)
        #     page = re.sub(r'<br\s*/?>', '\n', page, flags=re.IGNORECASE)
        #     page = re.sub(r'<[^>]+>', '', page)
        #     page = html.unescape(page)
        #     page = re.sub(r'\n\s*\n+', '\n', page)   # collapse multiple blank lines
        #     page = page.strip()
        # except:
        #     page = "<i>No preview for bots</i>"
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

# def wiki(messages, arg):
#     """@wiki(query) – Wikipedia search"""
#     api_url = (
#         "https://en.wikipedia.org/w/api.php?"
#         f"action=query&list=search&srsearch={quote(arg)}&format=json"
#     )
#     req = Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
#     data = json.loads(urlopen(req).read().decode("utf-8"))
#     results = data["query"]["search"]
#     out = f"<h3>Wikipedia entries for: {arg}</h3><ul>"
#     for entry in results[:10]:
#         title = entry["title"]
#         page_url = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
#         req2 = Request(page_url, headers={"User-Agent": "Mozilla/5.0"})
#         page = urlopen(req2, timeout=5).read().decode("utf-8", errors="ignore")
#         page = page.replace("<h1", "\n# <h1")
#         page = page.replace("<h2", "\n## <h2")
#         page = page.replace("<h3", "\n### <h3")
#         page = page.replace("<h4", "\n#### <h4")
#         page = page.replace("<h5", "\n##### <h5")
#         page = re.sub(r'<script.*?</script>', '', page, flags=re.I | re.S)
#         page = re.sub(r'<style.*?</style>', '', page, flags=re.I | re.S)
#         page = re.sub(r'<head.*?</head>', '', page, flags=re.I | re.S)
#         page = re.sub(r'</(p|div|li|h[1-6]|tr|td)>', '\n', page, flags=re.I)
#         page = re.sub(r'<br\s*/?>', '\n', page, flags=re.I)
#         page = re.sub(r'<(p|div|li|h[1-6]|tr|td)[^>]*>', '', page, flags=re.I)
#         page = re.sub(r'<[^>]+>', '', page)
#         page = html.unescape(page)
#         page = re.sub(r'\n\s*\n+', '\n', page).strip()
#         out += (
#             "<details>"
#             "<summary>%s</summary>"
#             "<a href='%s'>%s</a><br>"
#             "<pre>%s</pre>"
#             "</details>"
#         ).format(title, page_url, page_url, page)
#
#     lines = out.split("\n")
#     new_lines = []
#     for line in lines:
#         if ("." in line and len(line)>=10) or line.lstrip().startswith("#"):
#             new_lines.append(line)
#     return "\n".join(new_lines)



# ----------------------------

if __name__ == "__main__":
    print("http://localhost:8088/")
    HTTPServer(("0.0.0.0", 8088), NoCacheHandler).serve_forever()
