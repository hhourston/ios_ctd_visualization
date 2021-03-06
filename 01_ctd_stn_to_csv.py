import os
import glob
import numpy as np
import xarray as xr
import pandas as pd
import convert

# Ask James Hannah about searching files quickly by station on osd data archive

# ctd_file = 'C:\\Users\\HourstonH\\Documents\\ctd_visualization\\2002-001-0002.ctd.nc'
# ncdata = xr.open_dataset(ctd_file)

station = 'SI01'  # '59'  # '42'  # 'GEO1'  # 'LBP3'  # 'LB08'  # 'P1'
ctd_dir = 'C:\\Users\\HourstonH\\Documents\\ctd_visualization\\' \
          '{}\\'.format(station)
ctd_flist = glob.glob(ctd_dir + '*.nc')
ctd_flist.sort()

# Copied from James Hannah ios-inlets
# https://github.com/cyborgsphinx/ios-inlets/blob/main/inlets.py#L132


def get_var(ds, attr_names):
    # Search for all the available salinity and temperature variables
    # More than one code is used
    for attr in attr_names:
        if hasattr(ds, attr):
            return getattr(ds, attr)

    return None


def get_temperature_var(ds):
    temperature_names = [
        "TEMPRTN1",
        "TEMPST01",
        "TEMPPR01",
        "TEMPPR03",
        "TEMPS901",
        "TEMPS601"
    ]
    # Convert between temperature standards as well?
    return get_var(ds, temperature_names).data


def get_salinity_var(ds):
    salinity_names = [
        "PSLTZZ01",
        "ODSDM021",
        "SSALST01",
        "PSALST01",
        "PSALBST1",
        "sea_water_practical_salinity"
    ]
    # Convert units? PPT to PSS-78?
    sal_variable = get_var(ds, salinity_names)
    if sal_variable is not None:
        salinity, salinity_computed = convert.convert_salinity(
            sal_variable, sal_variable.units, 'ctd_logger.txt')
        return salinity.data
    else:
        # Oxygen data not present in netCDF file
        print('Warning: salinity data not found')
        return np.repeat(-99, len(ds.depth.data))


def get_oxygen_var(ds, temp_data, sal_data):
    # ds: xarray dataset
    oxygen_names = ["DOXYZZ01", "DOXMZZ01"]

    oxy_variable = get_var(ds, oxygen_names)

    if oxy_variable is not None:
        oxygen, oxygen_computed, density_assumed = convert.convert_oxygen(
            oxy_variable, oxy_variable.units, ds.longitude.data,
            ds.latitude.data, temp_data, sal_data, ds.PRESPR01.data,
            'ctd_logger.txt')
        return oxygen.data
    else:
        # Oxygen data not present in netCDF file
        print('Warning: oxygen data not found')
        return np.repeat(-99, len(temp_data))


def get_fluorescence_var(ds):
    # Fluorescence not in netCDF files only shell files
    fluorescence_names = []
    return


# Depth, range, gradient checks as in NEP climatology?
# Need to put all nc data in a csv table to make this easier
# as in the climatology project?
df_ctd = pd.DataFrame()

for i, f in enumerate(ctd_flist):
    print(os.path.basename(f))
    # Grab time, depth, TEMPS901, PSALST01
    ncdata = xr.open_dataset(f)

    nobs_in_cast = len(ncdata.depth.data)

    profile_number = np.repeat(i, nobs_in_cast)

    # Need to include lat/lon in order to check later
    lat_array = np.repeat(ncdata.latitude.data, nobs_in_cast)
    lon_array = np.repeat(ncdata.longitude.data, nobs_in_cast)

    # Need to convert time to string for csv files
    time_array = np.repeat(ncdata.time.data.astype('str'),
                           nobs_in_cast)

    # Convert temperature and salinity data as needed
    temp_var = get_temperature_var(ncdata)
    sal_var = get_salinity_var(ncdata)
    oxy_var = get_oxygen_var(ncdata, temp_var, sal_var)

    df_add = pd.DataFrame(
        np.array([profile_number, lat_array, lon_array, time_array,
                  ncdata.depth.data, temp_var, sal_var, oxy_var]
                 ).transpose(),
        columns=['Profile number', 'Latitude [deg N]', 'Longitude [deg E]',
                 'Time', 'Depth [m]', 'Temperature [C]',
                 'Salinity [PSS-78]', 'Oxygen [mL/L]'])

    df_ctd = pd.concat([df_ctd, df_add])

print(len(df_ctd))
print(sum(df_ctd.loc[:, 'Oxygen [mL/L]'] != '-99'))

df_name = 'C:\\Users\\HourstonH\\Documents\\ctd_visualization\\' \
          'csv\\{}_ctd_data.csv'.format(station)
df_ctd.to_csv(df_name, index=False)

