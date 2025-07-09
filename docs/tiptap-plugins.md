# TipTap Plugin Development

This short guide explains how DocuFlow's editor wrappers work.

Plugins export a loader function that registers toolbar actions or text
transformations. Frontend code calls the REST endpoint `/api/plugins`
to discover available wrappers and then loads each script. See the
`editor_loader.load_plugins` helper for unit tests.

## Dynamic extension toggles

Open **Editors → Tiptap** in the dashboard to try the built‑in extensions.
A small checkbox list lets you enable or disable options like `StarterKit`
and `Underline`. When you flip a switch the editor reloads with the new
extension set. Your choices are saved in the browser so the same
configuration appears next time.

## Managing plugins via the API

TipTap wrappers can be added or removed at runtime. The `/plugins` endpoint
accepts a module path and registers any plugins exported by that module.

1. Send a JSON body like `{"module": "my_package.my_plugin"}` to
   `POST /plugins`.
2. Call `PUT /plugins/{name}/enable` to activate a disabled plugin.
3. Call `PUT /plugins/{name}/disable` to temporarily turn it off.
4. Retrieve the current list with `GET /plugins` to confirm the state.

### Example plugin

Create a small module that exports a `register` function. The example below adds
`demo-extension` which simply logs a message when loaded:

```python
def demo_extension(data: dict) -> dict:
    print("demo extension active")
    return data

def register(registry) -> None:
    registry.register("demo-extension", demo_extension)
```

Save this as `my_package/my_plugin.py` and register it with the steps above.
