import yaml
import os
import numpy as np
import datetime
import matplotlib.pyplot as plt
from utils import OOINet
import warnings
warnings.filterwarnings("ignore")


def plot_ts(x1, y1, c1, x2, y2, c2, title=None):
    """Plot two label figures."""
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(x1, y1, c=c1)

    # ===============================
    # Plot the second axis
    ax2 = ax1.twinx()

    ax2.plot(x2, y2, c=c2)

    # ===============================
    # Add in labels
    # X-axis
    if "long_name" in x1.attrs:
        ax1.set_xlabel(x1.attrs["long_name"], fontsize=12)
    elif "standard_name" in x1.attrs:
        ax1.set_xlabel(x1.attrs["standard_name"], fontsize=12)
    else:
        pass
    # Format first y-axis
    if "long_name" in y1.attrs:
        ax1.set_ylabel(y1.attrs["long_name"], fontsize=12)
    elif "standard_name" in y1.attrs:
        ax1.set_ylabel(y1.attrs["standard_name"], fontsize=12)
    else:
        pass
    # Format second y-axis
    if "long_name" in y2.attrs:
        ax2.set_ylabel(y2.attrs["long_name"], fontsize=12)
    elif "standard_name" in y2.attrs:
        ax2.set_ylabel(y2.attrs["standard_name"], fontsize=12)
    else:
        pass

    # Add in a grid
    # ax1.grid()

    # Add in units
    if "units" in y1.attrs:
        ylabel = ax1.get_ylabel()
        ylabel = ylabel + "\n" + y1.attrs["units"]
        ax1.set_ylabel(ylabel, fontsize=12, color=c1)
    if "units" in y2.attrs:
        ylabel = ax2.get_ylabel()
        ylabel = ylabel + "\n" + y2.attrs["units"]
        ax2.set_ylabel(ylabel, fontsize=12, color=c2)
    if "units" in x1.attrs:
        xlabel = ax1.get_xlabel()
        xlabel = xlabel + "\n" + x1.attrs["units"]
        ax1.set_xlabel(xlabel, fontsize=12)

    # Add in title
    if title is not None:
        ax1.set_title(title)

    # Check if the x-axis is time. If it is, autoformat
    if x1.attrs["standard_name"] == "time":
        fig.autofmt_xdate()

    # Return the figure
    return fig


if __name__ == '__main__':

    # Set the basepath (this is because cron fucking sucks)
    basePath = "/home/andrew/Documents/OOI-CGSN/QAQC_Sandbox/Hurricane_Isaias/Isaias"

    # Import user info for accessing UFrame
    userinfo = yaml.load(open('../user_info.yaml'))
    username = userinfo['apiname']
    token = userinfo['apikey']

    # Initialize the OOINet Tool with username and token
    OOI = OOINet(username, token)

    # List the datasets that I need
    beginDT = datetime.datetime.now() - datetime.timedelta(hours=48)

    ISSM_METBK = {
        "refdes": "CP03ISSM-SBD11-06-METBKA000",
        "method": "telemetered",
        "stream": "metbk_a_dcl_instrument"
    }
    OSSM_METBK = {
        "refdes": "CP04OSSM-SBD11-06-METBKA000",
        "method": "telemetered",
        "stream": "metbk_a_dcl_instrument"
    }
    CNSM_METBK = {
        "refdes": "CP01CNSM-SBD11-06-METBKA000",
        "method": "telemetered",
        "stream": "metbk_a_dcl_instrument"
    }
    CNSM_WAVSS = {
        "refdes": "CP01CNSM-SBD12-05-WAVSSA000",
        "method": "telemetered",
        "stream": "wavss_a_dcl_statistics"
    }

    # ==========================================================
    # Download the CP01CNSM METBK dataset
    refdes = CNSM_METBK["refdes"]
    method = CNSM_METBK["method"]
    stream = CNSM_METBK["stream"]

    # Request the desired datasets
    thredds_url = OOI.get_thredds_url(refdes=refdes, method=method,
                                      stream=stream, beginDT=beginDT)
    # Get the datasets
    catalog = OOI.get_thredds_catalog(thredds_url)
    catalog = OOI.parse_catalog(catalog, exclude=["ENG", "gps", "velpt"])
    # Load the dataset
    cnsm_metbk = OOI.load_netCDF_files(catalog)

    # Calculate the wind speed from the component vectors
    cnsm_metbk = cnsm_metbk.assign(wind_speed=lambda x: np.sqrt(
                                   np.square(x.northward_wind_velocity) +
                                   np.square(x.eastward_wind_velocity)))
    cnsm_metbk.wind_speed.attrs["long_name"] = "Wind Speed"
    cnsm_metbk.wind_speed.attrs["units"] = "m s-1"

    # ===========================================================
    # Download the CP01CNSM WAVSS dataset
    refdes = CNSM_WAVSS["refdes"]
    method = CNSM_WAVSS["method"]
    stream = CNSM_WAVSS["stream"]

    # Request the desired datasets
    thredds_url = OOI.get_thredds_url(refdes=refdes, method=method,
                                      stream=stream, beginDT=beginDT)
    # Get the datasets
    catalog = OOI.get_thredds_catalog(thredds_url)
    catalog = OOI.parse_catalog(catalog, exclude=["ENG", "gps", "velpt"])
    # Load the dataset
    cnsm_wavss = OOI.load_netCDF_files(catalog)

    # ==========================================================
    # Download the CP03ISSM METBK dataset
    refdes = ISSM_METBK["refdes"]
    method = ISSM_METBK["method"]
    stream = ISSM_METBK["stream"]

    # Request the desired datasets
    thredds_url = OOI.get_thredds_url(refdes=refdes, method=method,
                                      stream=stream, beginDT=beginDT)
    # Get the datasets
    catalog = OOI.get_thredds_catalog(thredds_url)
    catalog = OOI.parse_catalog(catalog, exclude=["ENG", "gps", "velpt"])
    # Load the dataset
    issm_metbk = OOI.load_netCDF_files(catalog)

    # Calculate the wind speed
    issm_metbk = issm_metbk.assign(wind_speed=lambda x: np.sqrt(
                                   np.square(x.northward_wind_velocity) +
                                   np.square(x.eastward_wind_velocity)))
    issm_metbk.wind_speed.attrs["long_name"] = "Wind Speed"
    issm_metbk.wind_speed.attrs["units"] = "m s-1"

    # =========================================================
    # Download the CP04OSSM METBK dataset
    refdes = OSSM_METBK["refdes"]
    method = OSSM_METBK["method"]
    stream = OSSM_METBK["stream"]

    # Request the desired datasets
    thredds_url = OOI.get_thredds_url(refdes=refdes, method=method,
                                      stream=stream, beginDT=beginDT)
    # Get the datasets
    catalog = OOI.get_thredds_catalog(thredds_url)
    catalog = OOI.parse_catalog(catalog, exclude=["ENG", "gps", "velpt"])
    # Load the dataset
    ossm_metbk = OOI.load_netCDF_files(catalog)

    # Calculate the wind speed
    ossm_metbk = ossm_metbk.assign(wind_speed=lambda x: np.sqrt(
                                   np.square(x.northward_wind_velocity) +
                                   np.square(x.eastward_wind_velocity)))
    ossm_metbk.wind_speed.attrs["long_name"] = "Wind Speed"
    ossm_metbk.wind_speed.attrs["units"] = "m s-1"

    # =========================================================
    # Plot and save the figures. Will save to a local "plots" directory
    if not os.path.exists(f"{basePath}/plots"):
        os.makedirs("plots")

    # Plot the CNSM sea surface temps and salinity
    cnsm_sst_sss = plot_ts(cnsm_metbk.time, cnsm_metbk.sea_surface_temperature,
                           "tab:red", cnsm_metbk.time, cnsm_metbk.met_salsurf,
                           "tab:blue", cnsm_metbk.attrs["Location_name"])
    cnsm_sst_sss.savefig(f"{basePath}/plots/cnsm_sst_sss.png", dpi=300)

    # Plot the CNSM wave height and wind Speed
    cnsm_wh_ws = plot_ts(cnsm_metbk.time, cnsm_metbk.wind_speed, "tab:blue",
                         cnsm_wavss.time, cnsm_wavss.significant_wave_height,
                         "tab:red", cnsm_metbk.attrs["Location_name"])
    cnsm_wh_ws.savefig(f"{basePath}/plots/cnsm_wh_ws.png", dpi=300)

    # Plot the ISSM sea surface temps and salinity
    issm_sst_sss = plot_ts(issm_metbk.time, issm_metbk.sea_surface_temperature,
                           "tab:red", issm_metbk.time, issm_metbk.met_salsurf,
                           "tab:blue", issm_metbk.attrs["Location_name"])
    issm_sst_sss.savefig(f"{basePath}/plots/issm_sst_sss.png", dpi=300)

    # Plot the OSSM sea surface temps and salinity
    ossm_sst_sss = plot_ts(ossm_metbk.time, ossm_metbk.sea_surface_temperature,
                           "tab:red", ossm_metbk.time, ossm_metbk.met_salsurf,
                           "tab:blue", ossm_metbk.attrs["Location_name"])
    ossm_sst_sss.savefig(f"{basePath}/plots/ossm_sst_sss.png", dpi=300)
