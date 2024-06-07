# Installation

:::{note}
If you're familiar with the python ecosystem that's all you need.
```bash
$> pip install luxos
```
:::


These are detailed end-to-end instructions how to:
- install a python interpreter
- create a *virtual* envioronment
- install luxos


## Install a python interpreter

Here there are many choices, depending on the platform.

::::{tabs}
:::{tab} Windows
Head to [python](https://www.python.org/downloads) and download the 
most recent installer following the on-screen instructions.
:::
:::{tab} Mac OS native
MacOS comes pre-installed with python (3.9 under /usr/bin/python), which is supported.. just.

You'd better off installing an updated version from [python](https://www.python.org/downloads),
and follow the instructions.
:::
:::{tab} Mac OS brew
[Brew](https://brew.sh) is a very popular tool to install packages, including python. Once brew is setup 
(please follow the instructions on their website), it should be possible to install python just typing:

```bash
brew install python
```
:::
:::{tab} Linux
You can use the distro package manager to install your python interpter, something like:

```bash
$> yum install python
(or)
$> zypper install python
(or)
$> apt install python
```
:::
:::{tab} Conda
Conda is a multiplatform package manager, like brew but supporting environments.

You might consider using conda for an advanced way to maintain python stacks, see details
[here](https://conda.io/projects/conda/en/latest/user-guide/install/index.html).

It allows to use pip to install packages in an environment, as well the conda install command.

It has support for cross toolchains as well.
:::
::::


Once you have your system wide python installed, you can work creating a virtual env.

:::{hint}

No matter how you installed your main python interpreter, 
just make sure you're installing python3.x and not python2.x, this command should show something 
reasonable:

```bash
$> python3 --version
Python 3.12.3
```
:::


## Virtual environments

A **virtual environment** is a filesystem directory holding executable, libraries and 
all sort of ancillary files ("*data*"): it is initially created using the python 
interpreter itself, activated using an **activate** script (that sets the PATH 
to the directory) and files are installed using a **package manager** that installs
a **package**.

In case of python:
- a **package manager** could be `pip` or `conda`
- a **package** can be a python wheel `.whl` file or a conda file (`.conda`)
 
In general you can have multiple **virtual environments** with different installed **packages**
like an *environment* to run tests, another to create documentation and so on.

The lifecycle of a **virtual environment** is pretty simple once a python interpreter is installed:

1. **create** a new environment in a directory (this is usually done once per environment)
2. **activate** the newly create environmen (this step is needed every time you start a new shell process)
3. install/remove packages using the **package manager**

### Create a new environment

This will create a new *environment* under **venv** under the current directory 

::::{tabs}
:::{tab} *NIX
This will create a new venv directory in the current working dir:
``` bash
$> python3 -m venv $(pwd)/venv
```
:::
:::{tab} Windows
This will create a new venv directory in the current working dir:
``` cmd
$> python3 -m venv %CD%\venv
```
:::
::::

### Activate the environment
Once the environment has been created, every time a new shell is started, some configuration has
to be done in order to set the correct environmnetal variables as `PATH`.

This configuration is called **activate the environment**.
::::{tabs}
:::{tab} *NIX
``` bash
$> source $(pwd)/venv/bin/activate
```
:::
:::{tab} Windows
``` cmd
$> %CD%\venv\Scripts\activate.bat
```
:::
::::

### Uisng the newly creating environemn

Once activate an environment you can  use the **packages manager** to install/uninstall/update 
the packages in such environment: changes will happen only in the environment directory (in our case
`$(pwd)/venv` or `%CD%\venv`).


**to list currently installed packages**
```
pip list
```

**to install a package**
```
pip install luxos
```

**to upgrade a package**
```
pip install --upgrade luxos
```

**to remove a package**
```
pip uninstall luxos
```

