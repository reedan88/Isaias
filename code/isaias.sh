#!/bin/bash
##!/bin/bash -xe

PATHBASE="/home/andrew/Documents/OOI-CGSN/QAQC_Sandbox/Hurricane_Isaias/Isaias"

plotPath="$PATHBASE/plot"
codePath="$PATHBASE/code"

# Activate the environment
source /home/andrew/anaconda3/bin/activate Isaias && python3 $codePath/pioneer_plots.py;
source /home/andrew/anaconda3/bin/deactivate Isaias
