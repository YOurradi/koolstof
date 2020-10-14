import numpy as np
import pandas as pd
from matplotlib import dates as mdates


mapper_dbs = {
    "run type": "run_type",
    "i.s. temp.": "temperature_insitu",
    "sample mass": "mass_sample",
    "rep#": "rep",
    "CT": "dic",
    "factor CT": "dic_factor",
    "CV (µmol)": "cv_micromol",
    "CV (%)": "cv_percent",
    "last CRM CT": "lastcrm_dic_measured",
    "cert. CRM CT": "lastcrm_dic_certified",
    "CRM batch": "lastcrm_batch",
    "calc. mode": "mode_calculation",
    "integ. mode": "mode_integration",
    "Lat.": "latitude",
    "Long.": "longitude",
    "area#1": "area_1",
    "area#2": "area_2",
    "area#3": "area_3",
    "area#4": "area_4",
}


def read_dbs(filepath_or_buffer, encoding="unicode_escape", na_values="none", **kwargs):
    """Import the dbs file generated by a Marianda AIRICA as a pandas DataFrame.
    Any kwargs are passed to pandas.read_table.
    """
    dbs = pd.read_table(
        filepath_or_buffer, encoding=encoding, na_values=na_values, **kwargs
    )
    dbs.rename(mapper=mapper_dbs, axis=1, inplace=True)
    dbs.drop(columns="Unnamed: 32", inplace=True)
    dbs["datetime"] = pd.to_datetime(
        dbs.apply(lambda x: " ".join((x.date, x.time)), axis=1)
    )
    dbs["datenum"] = mdates.date2num(dbs.datetime)
    return dbs


mapper_LI7000 = {
    "Time": "datetime",
    "CO2B um/m": "x_CO2",
    "H2OB mm/m": "x_H2O",
    "T C": "temperature",
    "P kPa": "pressure",
    "RH %": "humidity_relative",
    "Flow V": "flow_voltage",
}


def get_licor_resolution(licor):
    """Determine the time resolution of data reported by a LI-COR, after it
    has been converted into a pandas DataFrame, and correct the 'datenum' and
    'datetime' column values in the DataFrame with second fractions.
    Input licor is generated with read_LI7000().
    """
    # Find resolution
    ldu = licor.datenum.unique()[1:-1]
    lda = licor[np.isin(licor.datenum, ldu)].datenum
    resolution = int(len(lda) / len(ldu))  # in Hz
    timestep = 1 / resolution
    # Apply correction
    start_iloc = np.where(licor.datenum == ldu[0])[0][0]
    second_fractions = np.linspace(0, 1 - timestep, resolution)
    second_fractions_start = second_fractions[-start_iloc:]
    second_fractions_middle = np.tile(second_fractions, len(ldu))
    tail_iloc = np.where(licor.datenum == ldu[-1])[0][-1] + 1
    tail_length = len(licor) - tail_iloc
    second_fractions_end = second_fractions[:tail_length]
    second_fractions = np.concatenate(
        (second_fractions_start, second_fractions_middle, second_fractions_end)
    )
    licor["datenum"] = licor.datenum + second_fractions / (60 * 60 * 24)
    licor["datetime"] = mdates.num2date(licor.datenum)
    return licor


def read_LI7000(filepath_or_buffer, skiprows=2, **kwargs):
    """Import the text files recorded by a LI-COR LI-7000 as a pandas DataFrame.
    Any kwargs are passed to pandas.read_table.
    """
    licor = pd.read_table(filepath_or_buffer, skiprows=skiprows, **kwargs)
    licor.rename(mapper=mapper_LI7000, axis=1, inplace=True)
    licor["datetime"] = pd.to_datetime(licor.datetime)
    licor["datenum"] = mdates.date2num(licor.datetime)
    return get_licor_resolution(licor)


def get_licor_samples(licor, dbs):
    """Identify different samples in a LI-COR dataset based on the dbs file,
    and remove data from before the first match.
    Assumes that both datasets are ordered with datetime ascending.
    """
    licor["dbs_ix"] = np.nan
    for dbs_ix in dbs.index:
        licor.loc[licor.datenum >= dbs.loc[dbs_ix].datenum, "dbs_ix"] = dbs_ix
    licor = licor[~np.isnan(licor.dbs_ix)]
    return licor