# Hurrican Isaias Plotting

This repo hosts the code for processing and plotting the sea surface temperature, sea surface salinity, wind speed, and significant wave height for the Pioneer Array for Hurricane Isaias.

The purpose of this repo is to run and update the plots on whatever cron schedule is desired. Recommended is every two hours, since the buoy telemetery is set to transmit every two hours.

### Setup
#### 1. Create a directory structure under where you have installed this repo to be:

```
Isaias
├── code
├── plots
└── ooi_user_info.yaml
```

This may be done with the following commands:

```
mkdir -p "$PATH/Isaias/plots"
git clone https://github.com/reedan88/Isaias.git /$PATH/Isaias/code
```

#### 2. Copy the `ooi_user_info.yaml` file into the `Isaias` directory

#### 3. Setup the appropriate python environment (Isaias) from the `isaias_env.yaml` file

This requires that either Anaconda or Miniconda have been previously installed.

#### 4. Set up a bi-hourly cron job

```
# Generate the desired plots of SST, SSS, wave height, and wind speed
0 */2 * * * /$PATH/Isaias/code/isaias.sh >> /tmp/
