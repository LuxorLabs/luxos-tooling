# Develop

These are instructions for developers, to quickly start coding for `luxos`.


## Pre-requisites
There are essentially three pre-requisites.

We assume you **have installed a recent version of python (eg. >=3.10)** and the python binary
is in the path. If so the following should be verified:
```bash
$> python3 --version
Python 3.12.3
```

The code is from a **github checkout**:
```bash
git clone https://github.com/LuxorLabs/luxos-tooling.git
```

Also we assume **the current directory is the check out directory**:
```bash
cd luxos-tooling
```

## Setup

You need (only once) to [Create the python virtual environment](#create-the-python-virtual-environment),
[Setting up the repository](#setting-up-the-repository), 
then every time you restart a shell, you need to [Activate the virtual environment](#activate-the-virtual-environment).


### Create the python virtual environment

First you need to create a virtual environment and install all dependencies:

=== "Windows"

    ```bash
    $> python3 -m venv %CD%\venv

    $> .\venv\Scripts\activate.bat
    # on powershell
    $> .\venv\Scripts\activate.ps1
    
    $> pip install -r tests\requirements.txt
    $> pip install -e .
    ```

=== "*NIX"
  
    ```bash
    $> python3 -m venv $(pwd)/venv  
    $> source ./venv/bin/activate
    
    $> pip install -r tests\requirements.txt
    $> pip install -e .
    ```

### Setting up the repository

Luxos leverages [pre-commit](https://pre-commit.com/) to execute
checks on code commit, so the code can be checked for issues before being
submitted to the repo.

=== "Windows"
    ```bash
    $> .\venv\Scripts\activate  
    # on powershell
    $> .\venv\Scripts\activate.ps1

    $> pre-commit install
    ```

=== "*NIX"
    ```bash
    $> source ./venv/bin/activate
    $> pre-commit install
    ```


  
- **ACTIVATE** the environment (each time you start a new shell)
  <details><summary>Windows</summary>

  ```shell
  .\venv\Scripts\activate
  ```
  </details>
  <details><summary>*NIX</summary>

  ```shell
  source ./venv/bin/activate
  ```
  </details>
  
- **RUN** the tests
  
  (Windows & *NIX)
  ```shell
  pytest -vvs tests
  ```

## Coding

### Precommit
When it comes to coding, you can use [pre-commit](https://pre-commit.com/) hooks
to help you validate code at every git commit.

- **ENABLE** precommit:
  ```shell
  pre-commit install
  ```

- **DISABLE** precommit:
  ```shell
  pre-commit uninstall
  ```

- **SKIP CHECKS** during git commit:
  Use the `-n` flag:
  ```shell
  git commit -n ....
  ```



At every `git commit` code scanner [ruff](https://github.com/astral-sh/ruff) and
[mypy](https://mypy-lang.org) will run.

