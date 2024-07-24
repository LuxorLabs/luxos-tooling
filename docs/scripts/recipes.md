# Recipes

This is a collection of recipes to use `luxos` cli command.

All requires a `miners.csv` file containing a list of machines. 

## Update

PYTHONPATH=src python -m luxos --ipfile miners.csv --cmd updateset --params "source=https://storage.googleapis.com/luxor-firmware/unstable/jpro-kpro-new-power-estimations" --verbose --async
PYTHONPATH=src python -m luxos --ipfile miners.csv --cmd updateset --params "source=https://storage.googleapis.com/luxor-firmware/unstable/jpro-kpro-new-power-estimations" --verbose --async

PYTHONPATH=src python -m luxos --ipfile miners.csv --cmd updaterun

PYTHONPATH=src python -m luxos --ipfile miners.csv --cmd config --async -a

PYTHONPATH=src python -m luxos --ipfile miners.csv --cmd profileget --params  355MHz --async -a


