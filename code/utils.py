import re
import os
import time
import requests
import datetime
import numpy as np
import pandas as pd
import xarray as xr
from xml.dom import minidom
from urllib.request import urlopen
from urllib.request import urlretrieve
import matplotlib.pyplot as plt


class OOINet():

    def __init__(self, USERNAME, TOKEN):

        self.username = USERNAME
        self.token = TOKEN
        self.urls = {
            'data': 'https://ooinet.oceanobservatories.org/api/m2m/12576/sensor/inv',
            'anno': 'https://ooinet.oceanobservatories.org/api/m2m/12580/anno/find',
            'vocab': 'https://ooinet.oceanobservatories.org/api/m2m/12586/vocab/inv',
            'asset': 'https://ooinet.oceanobservatories.org/api/m2m/12587',
            'deploy': 'https://ooinet.oceanobservatories.org/api/m2m/12587/events/deployment/inv',
            'preload': 'https://ooinet.oceanobservatories.org/api/m2m/12575/parameter',
            'cal': 'https://ooinet.oceanobservatories.org/api/m2m/12587/asset/cal'
        }

    def _get_api(self, url):
        """Request the given url from OOINet."""
        r = requests.get(url, auth=(self.username, self.token))
        data = r.json()
        return data

    def _ntp_seconds_to_datetime(self, ntp_seconds):
        """Convert OOINet timestamps to unix-convertable timestamps."""
        # Specify some constant needed for timestamp conversions
        ntp_epoch = datetime.datetime(1900, 1, 1)
        unix_epoch = datetime.datetime(1970, 1, 1)
        ntp_delta = (unix_epoch - ntp_epoch).total_seconds()

        return datetime.datetime.utcfromtimestamp(ntp_seconds - ntp_delta)

    def _convert_time(self, ms):
        if ms is None:
            return None
        else:
            return datetime.datetime.utcfromtimestamp(ms/1000)

    def get_metadata(self, refdes):
        """
        Get the OOI Metadata for a specific instrument specified by its
        associated reference designator.

            Args:
                refdes (str): OOINet standardized reference designator in the
                    form of <array>-<node>-<instrument>.

            Returns:
                results (pandas.DataFrame): A dataframe with the relevant
                    metadata of the given reference designator.
        """
        # First, construct the metadata request url
        array, node, instrument = refdes.split("-", 2)
        metadata_request_url = "/".join((self.urls["data"], array, node,
                                         instrument, "metadata"))

        # Request the metadata
        metadata = self._get_api(metadata_request_url)

        # Parse the metadata
        metadata = self.parse_metadata(metadata)

        # Add in the reference designator
        metadata["refdes"] = refdes

        # Return the metadata
        return metadata

    def parse_metadata(self, metadata):
        """
        Parse the metadata dictionary for an instrument returned by OOI into
        a pandas dataframe.
        """
        # Put the two keys into separate dataframes
        metadata_times = pd.DataFrame(metadata["times"])
        metadata_parameters = pd.DataFrame(metadata["parameters"])

        # Merge the two into a single dataframe
        results = metadata_parameters.merge(metadata_times, left_on="stream",
                                            right_on="stream")
        results.drop_duplicates(inplace=True)

        # Return the results
        return results

    def get_deployments(self, refdes, deploy_num="-1", results=pd.DataFrame()):
        """
        Get the deployment information for an instrument. Defaults to all
        deployments for a given instrument (reference designator) unless one is
        supplied.

        Args:
            refdes (str): The reference designator for the instrument for which
                to request deployment information.
            deploy_num (str): Optional to include a specific deployment number.
                Otherwise defaults to -1 which is all deployments.
            results (pandas.DataFrame): Optional. Useful for recursive
                applications for gathering deployment information for multiple
                instruments.

        Returns:
            results (pandas.DataFrame): A table of the deployment information
                for the given instrument (reference designator) with deployment
                number, deployed water depth, latitude, longitude, start of
                deployment, end of deployment, and cruise IDs for the
                deployment and recovery.

        """

        # First, build the request
        array, node, instrument = refdes.split("-", 2)
        deploy_url = "/".join((self.urls["deploy"], array, node, instrument,
                               deploy_num))

        # Next, get the deployments from the deploy url. The API returns a list
        # of dictionary objects with the deployment data.
        deployments = self._get_api(deploy_url)

        # Now, iterate over the deployment list and get the associated data for
        # each individual deployment
        while len(deployments) > 0:
            # Get a single deployment
            deployment = deployments.pop()

            # Process the dictionary data
            # Deployment Number
            deploymentNumber = deployment.get("deploymentNumber")

            # Location info
            location = deployment.get("location")
            depth = location["depth"]
            lat = location["latitude"]
            lon = location["longitude"]

            # Start and end times of the deployments
            startTime = self._convert_time(deployment.get("eventStartTime"))
            stopTime = self._convert_time(deployment.get("eventStopTime"))

            # Cruise IDs of the deployment and recover cruises
            deployCruiseInfo = deployment.get("deployCruiseInfo")
            recoverCruiseInfo = deployment.get("recoverCruiseInfo")
            if deployCruiseInfo is not None:
                deployID = deployCruiseInfo["uniqueCruiseIdentifier"]
            else:
                deployID = None
            if recoverCruiseInfo is not None:
                recoverID = recoverCruiseInfo["uniqueCruiseIdentifier"]
            else:
                recoverID = None

            # Put the data into a pandas dataframe
            data = np.array([[deploymentNumber, lat, lon, depth, startTime,
                              stopTime, deployID, recoverID]])
            columns = ["deploymentNumber", "latitude", "longitude", "depth",
                       "deployStart", "deployEnd", "deployCruise",
                       "recoverCruise"]
            df = pd.DataFrame(data=data, columns=columns)

            #
            results = results.append(df)

        return results

    def get_vocab(self, refdes):
        """
        Return the OOI vocabulary for a given url endpoint. The vocab results
            contains info about the reference designator, names of the

        Args:
            refdes (str): The reference designator for the instrument for which
                to request vocab information.

        Returns:
            results (pandas.DataFrame): A table of the vocab information for
                the given reference designator.

        """
        # First, construct the vocab request url
        array, node, instrument = refdes.split("-", 2)
        vocab_url = "/".join((self.urls["vocab"], array, node, instrument))

        # Next, get the vocab data
        data = self._get_api(vocab_url)

        # Put the returned vocab data into a pandas dataframe
        vocab = pd.DataFrame()
        vocab = vocab.append(data)

        # Finally, return the results
        return vocab

    def get_datasets(self, search_url, datasets=pd.DataFrame(), **kwargs):
        """Search OOINet for available datasets for a url."""
        # Check if the method is attached to the url
        flag = ("inv" == search_url.split("/")[-4])
        # inst = re.search("[0-9]{2}-[023A-Z]{6}[0-9]{3}", search_url)
        # inst = re.search("[0-9]{2}-", search_url)

        # This means you are at the end-point
        if flag is True:
            # Get the reference designator info
            array, node, instrument = search_url.split("/")[-3:]
            refdes = "-".join((array, node, instrument))

            # Get the available deployments
            deploy_url = "/".join((self.urls["deploy"], array, node,
                                   instrument))
            deployments = self._get_api(deploy_url)

            # Put the data into a dictionary
            info = pd.DataFrame(data=np.array([[array, node, instrument,
                                                refdes, search_url, deployments]]),
                                columns=["array", "node", "instrument",
                                         "refdes", "url", "deployments"])
            # add the dictionary to the dataframe
            datasets = datasets.append(info, ignore_index=True)

        else:
            endpoints = self._get_api(search_url)

            while len(endpoints) > 0:

                # Get one endpoint
                new_endpoint = endpoints.pop()

                # Build the new request url
                new_search_url = "/".join((search_url, new_endpoint))

                # Get the datasets for the new given endpoint
                datasets = self.get_datasets(new_search_url, datasets)

        # Once recursion is done, return the datasets
        return datasets

    def search_datasets(self, array=None, node=None, instrument=None,
                        English_names=False):
        """
        Wrapper around get_datasets to make the construction of the
        url simpler. Eventual goal is to use this as a search tool.

            Args:
                array (str): OOI abbreviation for a particular buoy on an array
                    (e.g. Pioneer Central Surface Mooring = CP01CNSM)
                node (str): Partial or full OOI abbreviation for a node on a
                    buoy to search for (e.g. Multi-Function Node = MFD)
                instrument (str): Partial or full OOI abbreviation for a
                    particular instrument type to search for (e.g. CTD)
                English_names (bool): Set to True if the descriptive names
                    associated with the given array/node/instrument are wanted.

            Returns:
                datasets (pandas.DataFrame): A dataframe of all the OOI
                    datasets which match the given search terms. If no search
                    terms are entered, will return every dataset available in
                    OOINet (slow).
        """

        # Build the request url
        dataset_url = f'{self.urls["data"]}/{array}/{node}/{instrument}'

        # Truncate the url at the first "none"
        dataset_url = dataset_url[:dataset_url.find("None")-1]

        print(dataset_url)
        # Get the datasets
        datasets = self.get_datasets(dataset_url)

        # Now, it node is not None, can filter on that
        if node is not None:
            mask = datasets["node"].apply(lambda x: True if node
                                          in x else False)
            datasets = datasets[mask]

        # If instrument is not None
        if instrument is not None:
            mask = datasets["instrument"].apply(lambda x: True if instrument
                                                in x else False)
            datasets = datasets[mask]

        # Check if they want the English names for the associated datasets
        if English_names:
            vocab = {
                "refdes": [],
                "array_name": [],
                "node_name": [],
                "instrument_name": []
            }

            # Iterate through the given reference designators
            for refdes in datasets["refdes"]:
                # Request the vocab for the given reference designator
                refdes_vocab = OOINet.get_vocab(refdes)

                # Check if it returns an empty dataframe - then fill with NaNs
                if len(refdes_vocab) == 0:
                    vocab["refdes"].append(refdes)
                    vocab["array_name"].append(None)
                    vocab["node_name"].append(None)
                    vocab["instrument_name"].append(
                        refdes_vocab["instrument"].iloc[0])

                # Parse the refdes-specific vocab
                vocab["refdes"].append(refdes)
                vocab["array_name"].append(refdes_vocab["tocL1"].iloc[0] + " "
                                           + refdes_vocab["tocL2"].iloc[0])
                vocab["node_name"].append(refdes_vocab["tocL3"].iloc[0])
                vocab["instrument_name"].append(
                    refdes_vocab["instrument"].iloc[0])

            # Merge the results with the datasets
            vocab = pd.DataFrame(vocab)
            datasets = datasets.merge(vocab, left_on="refdes",
                                      right_on="refdes")
            # Sort the datasets
            columns = ["array", "array_name", "node", "node_name", "instrument",
                       "instrument_name", "refdes", "url", "deployments"]
            datasets = datasets[columns]

        return datasets

    def get_datastreams(self, refdes):
        """Retrieve methods and data streams for a reference designator."""
        # Build the url
        array, node, instrument = refdes.split("-", 2)
        method_url = "/".join((self.urls["data"], array, node, instrument))

        # Build a table linking the reference designators, methods, and data
        # streams
        stream_df = pd.DataFrame(columns=["refdes", "method", "stream"])
        methods = self._get_api(method_url)
        for method in methods:
            if "bad" in method:
                continue
            stream_url = "/".join((method_url, method))
            streams = self._get_api(stream_url)
            stream_df = stream_df.append({
                "refdes": refdes,
                "method": method,
                "stream": streams
            }, ignore_index=True)

        # Expand so that each row of the dataframe is unique
        stream_df = stream_df.explode('stream').reset_index(drop=True)

        # Return the results
        return stream_df

    def get_parameter_data_levels(self, metadata):
        """
        Get the data levels associated with the parameters for a given
        reference designator.

            Args:
                metadata (pandas.DataFrame): a dataframe which contains the
                    metadata for a given reference designator.

            Returns:
                pid_dict (dict): a dictionary with the data levels for each
                    parameter id (Pid)
        """

        pdIds = np.unique(metadata["pdId"])
        pid_dict = {}
        for pid in pdIds:
            # Build the preload url
            preload_url = "/".join((self.urls["preload"], pid.strip("PD")))
            # Query the preload data
            preload_data = self._get_api(preload_url)
            data_level = preload_data.get("data_level")
            # Update the results dictionary
            pid_dict.update({pid: data_level})

        return pid_dict

    def filter_parameter_ids(self, pdId, pid_dict):
        """Filter for processed data products."""
        # Check if pdId should be kept
        data_level = pid_dict.get(pdId)
        if data_level == 1:
            return True
        else:
            return False

    def get_thredds_url(self, refdes, method, stream, **kwargs):
        """
        Return the url for the THREDDS server for the desired dataset(s).

            Args:
                refdes (str): reference designator for the instrument
                method (str): the method (i.e. telemetered) for the given
                              reference designator
                stream (str): the stream associated with the reference
                              designator and method

            Kwargs: optional parameters to pass to OOINet API to limit the
                    results of the query
                beginDT (str): limit the data request to only data after this
                    date.
                endDT (str): limit the data request to only data before this
                    date.
                format (str): e.g. "application/netcdf" (the default)
                include_provenance (str): 'true' returns a text file with the
                    provenance information
                include_annotations (str): 'true' returns a separate text file
                    with annotations for the date range

            Returns:
                thredds_url (str): a url to the OOI Thredds server which
                    contains the desired datasets
        """
        # Build the data request url
        array, node, instrument = refdes.split("-", 2)
        data_request_url = "/".join((self.urls["data"], array, node,
                                     instrument, method, stream))

        # Ensure proper datetime format for the request
        if 'beginDT' in kwargs.keys():
            kwargs['beginDT'] = pd.to_datetime(kwargs['beginDT']).strftime(
                '%Y-%m-%dT%H:%M:%S.%fZ')
        if 'endDT' in kwargs.keys():
            kwargs['endDT'] = pd.to_datetime(kwargs['endDT']).strftime(
                '%Y-%m-%dT%H:%M:%S.%fZ')

        # Build the query
        params = kwargs

        # Request the data
        r = requests.get(data_request_url, params=params, auth=(self.username,
                                                                self.token))
        if r.status_code == 200:
            data_urls = r.json()
        else:
            print(r.reason)
            return None

        # The asynchronous data request is contained in the 'allURLs' key,
        # in which we want to find the url to the thredds server
        for d in data_urls['allURLs']:
            if 'thredds' in d:
                thredds_url = d

        return thredds_url

    def _get_elements(self, url, tag_name, attribute_name):
        """Get elements from an XML file."""
        usock = urlopen(url)
        xmldoc = minidom.parse(usock)
        usock.close()
        tags = xmldoc.getElementsByTagName(tag_name)
        attributes = []
        for tag in tags:
            attribute = tag.getAttribute(attribute_name)
            attributes.append(attribute)
        return attributes

    def get_thredds_catalog(self, thredds_url):
        """
        Get the dataset catalog for the requested data stream.

            Args:
                thredds_url (str): the THREDDS server url for the
                    requested data stream

            Returns:
                catalog (list): the THREDDS catalog of datasets for
                    the requested data stream
        """
        # ==========================================================
        # Parse out the dataset_id from the thredds url
        server_url = 'https://opendap.oceanobservatories.org/thredds/'
        dataset_id = re.findall(r'(ooi/.*)/catalog', thredds_url)[0]

        # Check the status of the request until the datasets are ready
        # Will timeout if request takes longer than 10 mins
        status_url = thredds_url + '?dataset=' + dataset_id + '/status.txt'
        status = requests.get(status_url)
        start_time = time.time()
        while status.status_code != requests.codes.ok:
            elapsed_time = time.time() - start_time
            status = requests.get(status_url)
            if elapsed_time > 10*60:
                print(f'Request time out for {thredds_url}')
                return None
            time.sleep(5)

        # Parse the datasets from the catalog for the requests url
        catalog_url = server_url + dataset_id + '/catalog.xml'
        catalog = self._get_elements(catalog_url, 'dataset', 'urlPath')

        return catalog

    def parse_catalog(self, catalog, exclude=[]):
        """
        Parses the THREDDS catalog for the netCDF files. The exclude
        argument takes in a list of strings to check a given catalog
        item against and, if in the item, not return it.

        Args:
            catalog (list): the THREDDS catalog of datasets for
                the requested data stream
            exclude (list): keywords to filter files out of the THEDDS catalog

        Returns:
            datasets (list): a list of netCDF datasets which contain the
                associated .nc datasets
        """
        datasets = [citem for citem in catalog if citem.endswith('.nc')]
        if type(exclude) is not list:
            raise ValueError('arg exclude must be a list')
        for ex in exclude:
            if type(ex) is not str:
                raise ValueError(f'Element {ex} of exclude must be a string.')
            datasets = [dset for dset in datasets if ex not in dset]
        return datasets

    def download_netCDF_files(self, datasets, save_dir=None):
        """
        Download netCDF files for given netCDF datasets. If no path
        is specified for the save directory, will download the files to
        the current working directory.

            Args:
                datasets (list): the netCDF datasets to download
                save_dir (str): the path to the directory in which to save
                    the downloaded netCDF files
        """
        # Specify the server url
        server_url = 'https://opendap.oceanobservatories.org/thredds/'

        # Specify and make the relevant save directory
        if save_dir is not None:
            # Make the save directory if it doesn't exists
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
        else:
            save_dir = os.getcwd()

        # Download and save the netCDF files from the HTTPServer
        # to the save directory
        count = 0
        for dset in datasets:
            # Check that the datasets are netCDF
            if not dset.endswith('.nc'):
                raise ValueError(f'Dataset {dset} not netCDF.')
            count += 1
            file_url = server_url + 'fileServer/' + dset
            filename = file_url.split('/')[-1]
            print(f'Downloading file {count} of {len(datasets)}: {dset} \n')
            a = urlretrieve(file_url, '/'.join((save_dir, filename)))

    def load_netCDF_files(self, netCDF_datasets):
        """Open the netCDF files directly from the THREDDS opendap server."""
        # Get the OpenDAP server
        opendap_url = "https://opendap.oceanobservatories.org/thredds/dodsC"

        # Add the OpenDAP url to the netCDF dataset names
        netCDF_datasets = ["/".join((opendap_url, dset)) for dset in
                           netCDF_datasets]

        # Note: latest version of xarray and netcdf-c libraries enforce strict
        # fillvalue match, which causes an error with the implement OpenDAP
        # data mapping. Requires appending #fillmismatch to open the data
        netCDF_datasets = [dset+"#fillmismatch" for dset in netCDF_datasets]

        # Open the datasets into an xarray dataset, make time the main
        # dimension, and sort
        with xr.open_mfdataset(netCDF_datasets) as ds:
            ds = ds.swap_dims({"obs": "time"})
            ds = ds.sortby("time")

        # Add in the English name of the dataset
        refdes = "-".join(ds.attrs["id"].split("-")[:4])
        vocab = self.get_vocab(refdes)
        ds.attrs["Location_name"] = " ".join((vocab["tocL1"].iloc[0],
                                              vocab["tocL2"].iloc[0],
                                              vocab["tocL3"].iloc[0]))
        # Return the dataset
        return ds
