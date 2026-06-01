# Hyperbolic Chat

A simple browser chatbot that talks to open models on [Hyperbolic](https://hyperbolic.xyz) through their OpenAI-compatible API. A small Python server serves the web UI and proxies API requests so your API key stays on your machine.

## Requirements

- **Python 3** (3.10 or newer recommended)
- A **Hyperbolic account** with credits and an API key
- A modern web browser

No extra Python packages are required—the server uses only the standard library.

## Get an API key

1. Sign in at [app.hyperbolic.ai](https://app.hyperbolic.ai).
2. Open **Settings → API Keys** ([direct link](https://app.hyperbolic.ai/settings/api-keys)).
3. Click **Create API Key** and copy the key. Store it somewhere safe; you may not be able to view it again.

Keep this key private. Anyone with it can use your Hyperbolic account.

## Set up

Clone the repository:

```bash
git clone thomashikaru/basic-chatbot
cd basic-chatbot
```

Export your API key in the terminal session where you will run the server:

```bash
export HYPERBOLIC_API_KEY='your-api-key-here'
```

Quotes are optional unless your key contains shell-special characters. To confirm it is set:

```bash
echo "$HYPERBOLIC_API_KEY"
```

## Run the server

From the project directory:

```bash
python3 server.py
```

You should see:

```text
Open http://localhost:8000
```

The server listens on port **8000** by default. To use another port:

```bash
PORT=8001 python3 server.py
```

Leave this terminal window open while you use the chatbot. Stop the server with **Ctrl+C**.

### Port already in use

If you see `Address already in use`, another process (often a previous run of this server) is using the port. Either stop that process or start on a different port with `PORT=8001 python3 server.py`.

## Use the chatbot

1. Open [http://localhost:8000](http://localhost:8000) in your browser.
2. Choose a **model** from the dropdown at the top.
3. Type a message and click **Send** (or press Enter).

The assistant keeps conversation context until you click **Clear chat**, which starts a new thread while keeping the same model selection.

Responses support Markdown (headings, lists, links, and similar formatting) and fenced code blocks. Python and JavaScript snippets in triple-backtick blocks are syntax-highlighted when the language tag is included (for example, ` ```python `).

## Tips

- Set `HYPERBOLIC_API_KEY` in the **same terminal** before running `python3 server.py`. If you export the variable in a different window, the server will not see it.
- If requests fail, check that your Hyperbolic account has credits and that the selected model is available on your plan.
- Hard-refresh the page (**Cmd+Shift+R** on macOS, **Ctrl+Shift+R** on Windows/Linux) after pulling UI updates so the browser loads the latest `index.html`.

## Project layout

| File        | Purpose                                      |
| ----------- | ---------------------------------------------- |
| `server.py` | Local web server and Hyperbolic API proxy      |
| `index.html`| Chat UI (opened automatically via the server) |
