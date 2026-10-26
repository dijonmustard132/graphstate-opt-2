#!/bin/sh
python3 run_experiments.py test 10 > ../results/run_test.out 2>&1
python3 run_experiments.py val 10 > ../results/run_val.out 2>&1
python3 run_experiments.py train 10 > ../results/run_train.out 2>&1
echo finished > ../results/ALLDONE
