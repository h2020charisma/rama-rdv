# + tags=["parameters"]
upstream = ["twinning_intensity_normalization"]
product = None
probe: None
spectrum_corrected_column: None
baseline_after_ledcorrection: None

# -

import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import ramanchada2 as rc2
import numpy as np

spectra2process = "{}_baseline".format(spectrum_corrected_column)  if baseline_after_ledcorrection else spectrum_corrected_column
print(spectra2process)

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

#slope
def calc_regression(x,y):
    model = LinearRegression().fit(x,y)
    #print("Intercept:", model.intercept_)
    #print("Slope (Coefficient):", model.coef_[0])    
    return  (model.intercept_,model.coef_[0])

devices_h5file= upstream["twinning_intensity_normalization"]["data"]
devices = pd.read_hdf(devices_h5file, "devices")
devices.head()

processing = pd.read_hdf(devices_h5file, "processing")
processing.head()

devices_h5file =product["data"]

#peaks
reference_condition = (devices["reference"]) & (devices["probe"] == probe)
devices.loc[reference_condition ,"amplitude"] = devices.loc[(devices["reference"]) ][spectra2process].apply(calc_peak_amplitude)
devices.to_hdf(devices_h5file, key='devices', mode='w')

#regression
A= devices.loc[reference_condition,["reference","laser_power","amplitude"]].dropna()
(intercept_A,slope_A) = calc_regression(A[["laser_power"]],A["amplitude"])
#devices.loc[reference_condition,"slope"]
#devices.to_hdf(devices_h5file, key='devices', mode='w')
devices.loc[reference_condition][["reference","device","laser_power","amplitude"]]

#peaks
twinned_condition = (~devices["reference"]) & (devices["probe"] == probe)
devices.loc[twinned_condition,"amplitude"] = devices.loc[twinned_condition][spectra2process].apply(calc_peak_amplitude)
devices.to_hdf(devices_h5file, key='devices', mode='w')

#regression
B= devices.loc[twinned_condition,["reference","laser_power","amplitude"]].dropna()
#devices.loc[twinned_condition,"slope"] = 
(intercept_B,slope_B) = calc_regression(B[["laser_power"]],B["amplitude"])
#devices.to_hdf(devices_h5file, key='devices', mode='w')
devices.loc[twinned_condition][["reference","device","laser_power","amplitude"]]


A = devices.loc[reference_condition]
B = devices.loc[twinned_condition]
plt.plot(A["laser_power"],A["amplitude"],'o',label=A["device"].unique())
plt.plot(B["laser_power"],B["amplitude"],'+',label=B["device"].unique())
plt.legend()

#Factor correction (FC) is obtained by dividing the slope of the reference equipment (spectrometer A) 
# by the slope of the equipment to be twinned (spectrometer B).

factor_correction = slope_A/slope_B
print(slope_A,slope_B,factor_correction)



def harmonization(row):
    try:
        spe = row[spectra2process]       
        return rc2.spectrum.Spectrum(spe.x, spe.y *factor_correction)
    except Exception as err:
        print(err)
        return None
#only twinned is multiplied
devices.loc[twinned_condition,"spectrum_harmonized"] = devices.loc[twinned_condition].apply(harmonization,axis=1)
processing.loc["harmonized"] = {"field" : "spectrum_harmonized"}    
devices.to_hdf(devices_h5file, key='devices', mode='w')


def spe_area(spe):
    try:
        sc = spe.trim_axes(method='x-axis', boundaries=(100, 1750))  
        return np.sum(sc.y * np.diff(sc.x_bin_boundaries))
    except Exception as err:
        print(err)
        return None

devices.loc[reference_condition,"area"] = devices.loc[reference_condition][spectra2process].apply(spe_area)
devices.loc[reference_condition][["reference","device","laser_power","area"]]

devices.loc[twinned_condition,"area"] = devices.loc[twinned_condition][spectra2process].apply(spe_area)   
devices.loc[twinned_condition,"area_harmonized"] = devices.loc[twinned_condition]["spectrum_harmonized"].apply(spe_area)   
devices.loc[twinned_condition][["reference","device","laser_power","area","area_harmonized"]]

devices.to_hdf(devices_h5file, key='devices', mode='w')

processing.to_hdf(devices_h5file, key='processing', mode='a')


pd.DataFrame({"twinned" : {"slope"  : slope_B, "intercept" : intercept_B},
              "reference" : {"slope"  : slope_A, "intercept" : intercept_A}
              }).T.to_hdf(devices_h5file, key='regression', mode='a')

pd.DataFrame({"result" : {"factor_correction" :factor_correction}
              }).to_hdf(devices_h5file, key='factor_correction', mode='a')

import matplotlib.pyplot as plt
def plot_spectra(row,boundaries=(100, 1750)):
    try:
        sc =row[spectra2process]
        if boundaries:
            sc = sc.trim_axes(method='x-axis', boundaries=boundaries)        
        sc.plot(ax=axes[0],label="{}%".format(row["laser_power_percent"]))
    except:
        pass
    try:
        sc =row["spectrum_harmonized"]
        if boundaries:
            sc = sc.trim_axes(method='x-axis', boundaries=boundaries)
        sc.plot(ax=axes[1],label="{}%".format(row["laser_power_percent"]))
    except:
        pass    
    axes[0].set_title("{} {}".format(row["device"],row["probe"]))

fig, axes = plt.subplots(2, 1, figsize=(15, 6))      
axes[1].set_title("harmonized")
devices.loc[twinned_condition].apply(plot_spectra, axis=1)

fig, axes = plt.subplots(2, 1, figsize=(15, 6))      
axes[1].set_title("harmonized")
devices.loc[reference_condition].apply(plot_spectra, axis=1)
 