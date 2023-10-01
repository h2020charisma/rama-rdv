# + tags=["parameters"]
upstream = ["twinning_intensity_normalization","load_spectra"]
product = None
probe: None

# -

import pandas as pd

def calc_peak_amplitude(spe,peak=144,prominence=0.01):
    try:
        spe = spe.trim_axes(method='x-axis', boundaries=(65, 300))
        candidates = spe.find_peak_multipeak(prominence=prominence)
        print(candidates)
        fit_res = spe.fit_peak_multimodel(profile='Voigt', candidates=candidates)
        df = fit_res.to_dataframe_peaks()
        df["sorted"] = abs(df["center"] - peak) #closest peak to 144
        df_sorted = df.sort_values(by='sorted')
        print(df_sorted["amplitude"][0],df_sorted["center"][0])
        return df_sorted["amplitude"][0]
    except:
        return None

devices_h5file= upstream["load_spectra"]["data"]
devices = pd.read_hdf(devices_h5file, "devices")
devices.head()

#peaks
reference_condition = (devices["reference"]) & (devices["probe"] == probe)
devices.loc[(devices["reference"]) ,"amplitude"] = devices.loc[(devices["reference"]) ]["spectrum_corrected"].apply(calc_peak_amplitude)

twinned_condition = (~devices["reference"]) & (devices["probe"] == probe)
devices.loc[twinned_condition,"amplitude"] = devices.loc[twinned_condition]["spectrum_corrected"].apply(calc_peak_amplitude)


devices[["device","amplitude"]]