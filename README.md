Chess.py
===
A simple Chess engine.

## Develop

### Setup
Create virtual environment.
```bash
pip install virtualenv
virtualenv .venv
```

Install packages.
```bash
make install
```

### Build / Run
Run the game.
```bash
make run
```

#### Visual Studio Code
From the **_Run and Debug_** panel, with **_Python Debugger: Current File_** selected, press **_Start Debugging_** or **_[F5]_** from any project root Python file (i.e. `~/CLI.py` or `~/Chess.py`).

### Test
Run all tests.
```bash
make test
```

Generate coverage reports.
```bash
make report
```

### Commit
Format code.
```bash
make format
```