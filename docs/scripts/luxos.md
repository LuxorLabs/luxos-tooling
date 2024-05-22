# luxos

This script can run commands on miners.

Input to this script is a `*.csv` file, one IP per line, comments are marked with a `#` and empty lines are ignored.

This will reboot all miners in the `miner.csv` file list:
```bash
   $> luxos --ipfile miners.csv --cmd rebootdevice --timeout 2 --verbose
```

There's an `async` version that can work better on multiple miners, just use the `--async` flag:
```bash
   $> luxos --ipfile miners.csv --cmd version --timeout 2 --async --all
   > 10.206.1.153:4028
   | {
   |   "STATUS": [
   |     {
   |       "Code": 22,
   |       "Description": "LUXminer 2024.5.1.155432-f2badc0f",
```
This will reboot all miners in the `miner.csv` file list:
```bash
   $> luxos --ipfile miners.csv --cmd rebootdevice --timeout 2 --verbose
```

There's an `async` version that can work better on multiple miners, just use the `--async` flag:
```bash
   $> luxos --ipfile miners.csv --cmd version --timeout 2 --async --all
   > 10.206.1.153:4028
   | {
   |   "STATUS": [
   |     {
   |       "Code": 22,
   |       "Description": "LUXminer 2024.5.1.155432-f2badc0f",
```
