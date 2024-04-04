# Develop

These are the developer's note, to develop luxos.

> **NOTE** We assume we're working inside the checked out
> `firmware-biz-tools` directory, and you have python (>=3.10)
> in your path.

## Setup

These instructions are useful for a quick start, and
you should be able to:

- **SETUP** the environment (this is done once)
  <details><summary>Windows</summary>

  ```shell
  python -m venv myenv
  .\myenv\Scripts\activate  

  pip install -r tests\requirements.txt
  pip install -e .
  ```
  </details>
  
  <details><summary>*NIX</summary>
  
  ```shell
  python -m venv myenv  
  source ./myenv/bin/activate
  
  pip install -r tests\requirements.txt
  pip install -e .
  ```
  
- **ACTIVATE** the environment (each time you start a new shell)
  <details><summary>Windows</summary>

  ```shell
  .\myenv\Scripts\activate
  ```
  </details>
  <details><summary>*NIX</summary>

  ```shell
  source ./myenv/bin/activate
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
