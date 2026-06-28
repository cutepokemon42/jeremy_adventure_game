# Jeremy Visual Adventure

This browser version keeps the Python game intact and turns the supplied
pixel-art concept into an interactive visual interface. It reads the same JSON
world, item, enemy, recipe, and dungeon files as the CLI game.

## Run

From the repository root:

```sh
python3 -m http.server 8000
```

Then open <http://localhost:8000/visual%20game/>.

The local server is required because the browser loads the shared JSON data
files. Progress saves automatically to browser LocalStorage. Number keys 1–9
activate the visible action buttons and Escape closes menus.

## Test

```sh
cd "visual game"
npm test
```

There are no npm runtime dependencies.
