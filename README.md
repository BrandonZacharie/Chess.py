# Chess.py

A simple Chess engine.

## Develop

### Setup (MacOS)

Install Stockfish.

```bash
brew install stockfish
```

Create virtual environment.

```bash
pip install virtualenv
virtualenv .venv
```

Install packages.

```bash
make install
```

### Test

Run all tests.

```bash
make test
```

Generate coverage reports.

```bash
make report
```

### Debug (Visual Studio Code)

From the **_Run and Debug_** panel, with **_Python Debugger: Current File_**
selected, press **_Start Debugging_** or **_[F5]_** from any project root
Python file (i.e. `~/CLI.py` or `~/Chess.py`).

### Commit

Format code.

```bash
make format
```

## Run

Run the game.

```bash
make run
```
