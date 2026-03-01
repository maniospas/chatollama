# CHATOLLAMA

This is a simple chat interface for ollama models.
I have been mostly using it for simple searches when my internet connectivity is bad
(so I cannot look up documentation online) or writing private code sometimes.

There do exist similar chat frontends in the Ollama ecosystem. This one, however, aims
to bring some more controllable and extensible tooling than normal. I am not a believer
of the "thinking" approach and instead provide tools so that you, the user, can actually
think for yourself and help the model do something useful and under oversight.

This repo could be vibe-coded in an evening, but is released under MIT license anyway.
Would appreciate a star if you like it.

![Screenshot](screenshot.png)

## Capabilities

- [x] Chat
- [x] System context
- [x] Select your models
- [x] Code highlighting
- [x] File uploads
- [x] Controlled tooling
- [ ] Tools asking for user interaction
- [ ] Automatic discovery and integration of ollama models


## Instructions

Install ollama and pull some models. Link: [https://ollama.com/](https://ollama.com/)

Clone this repository, create a Python virtual environment, and install necessary dependencies:

```bash
python -m venv venv
source venv/bin/activate
(venv) pip install -r requirements.txt
```

Then launch the service and visit the printed localhost site from your browser:

```bash
(venv) python -m server
http://localhost:8088/
```

To have pdf processing and syntax highlighting offline, you can create a *link/* directory and
populate it with stuff that is normally retrieved from *cdnjs*. Look at the requirements in *index.html*,
which has both the online and offline version links. Not distributing those myself because I am worried
about violating some license. Perhaps will automatically hydrate that directory in the future.

## Tooling

You may notice that there is an option to add some tooling options. This is my own
take on the subject that tries to stay responsible by not modifying the machine without
permission; tools are there to help the answer with additional context or information.

If you want to execute commands automatically, sorry but I am not going to help you erase
your hard drive automatically. You can ask for commands and paste them in your console yourself.
Like an adult.

Syntax for tools is: `@toolname(arguments)`

You can ommit the parentheses if the rest of the sentence should be used as arguments.
Arguments can be the outputs of other tools too. That is, you can chain stuff.
If multiple are needed, they may be separated
by spaces or commas, though usually you would just write some more text in there.

Tools calls replace themselves with obtained text. For example, you can ask questions like the
following to pull information from wikipedia or the web and have the model summarize it:

```
what are some good recipes for @wiki bananas
what is @web python
```

If you do not want the model to answer on the tool outcome, use the `@print` tool like this:

```
@print @wiki ducks
```

# Contributing

You can easily add tools locally, or contribute to this repository through a PR.
AI-generated code is allowed, but I will immediately reject the following patterns in Python files:

- inline comments that are obvious from the code (e.g., "# read the file and split it into lines")
- more than four layers of nesting and excessive else statements: perform early break/continue/return
- excessive intermediate variables and excessive splitting into short functions that are not reused
- calls to ollama from the backend: the orchestrator is the frontend

If you are unsure about violations, just write a short description of why you left them in
(even for reasons like "too bored to simplify") and I will properly look into it.

**How to add your own tools?**

Open the file `tools.py` and implement your own tool. Annotate it with the `@tool` decorator
and return an html string given text input and the list of existing messages. Do not add inline
css but, if needed, create or reuse css classes from the frontend.

Do not forget to add a usage description docstring. This should be 1-2 lines long.
Example implementation of the *@wikishort* tool:

```python
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
```
