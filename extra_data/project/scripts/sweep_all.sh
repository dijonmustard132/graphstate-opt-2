#!/bin/sh
python3 run_budget_sweep.py train 5 > ../results/sweep_train.out 2>&1
python3 run_budget_sweep.py val 5 > ../results/sweep_val.out 2>&1
python3 run_budget_sweep.py test 10 > ../results/sweep_test.out 2>&1
echo finished > ../results/SWEEPDONE
