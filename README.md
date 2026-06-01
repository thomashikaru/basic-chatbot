# LLM Chat

A simple browser chatbot that talks to models through [Hyperbolic](https://hyperbolic.xyz) or [OpenRouter](https://openrouter.ai). A small Python server serves the web UI and proxies API requests so your API keys stay on your machine.

## Requirements

- **Python 3** (3.10 or newer recommended)
- At least one API key: **Hyperbolic**, **OpenRouter**, or both
- A modern web browser

No extra Python packages are required—the server uses only the standard library.

## API keys

### Hyperbolic

1. Sign in at [app.hyperbolic.ai](https://app.hyperbolic.ai).
2. Open **Settings → API Keys** ([direct link](https://app.hyperbolic.ai/settings/api-keys)).
3. Create and copy a key.

### OpenRouter

1. Sign in at [openrouter.ai](https://openrouter.ai).
2. Open [API Keys](https://openrouter.ai/keys) and create a key.

Keep keys private. Anyone with a key can use your account.

## Set up

Clone the repository:

```bash
git clone <your-repo-url>
cd basic-chatbot
```

Export one or both keys in the terminal where you will run the server:

```bash
export HYPERBOLIC_API_KEY='your-hyperbolic-key'
export OPENROUTER_API_KEY='your-openrouter-key'
```

Only providers with a configured key appear in the UI.

## Run the server

```bash
python3 server.py
```

Open [http://localhost:8000](http://localhost:8000). The default port is **8000**; use `PORT=8001 python3 server.py` to change it.

## Use the chatbot

1. Choose a **Provider** (Hyperbolic or OpenRouter).
2. Choose a **Model**. Hyperbolic uses a fixed list; OpenRouter loads available models from the API when you select that provider.
3. Type a message and click **Send**.

The assistant keeps conversation context until you click **Clear chat**. Provider and model choices are remembered in your browser.

Responses support Markdown and fenced code blocks. Python, JavaScript, and HTML snippets are syntax-highlighted when tagged (for example, ` ```python `).

## Tips

- Set API keys in the **same terminal** before running `python3 server.py`.
- Switching provider reloads the model list. OpenRouter exposes many more models than Hyperbolic.
- Hard-refresh the page after updates (**Cmd+Shift+R** / **Ctrl+Shift+R**).

## Project layout

| File         | Purpose                                |
| ------------ | -------------------------------------- |
| `server.py`  | Local web server and API proxy         |
| `index.html` | Chat UI                                |
