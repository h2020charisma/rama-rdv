# + tags=["parameters"]
upstream = ["twinning_intensity_normalization","load_spectra"]
product = None
probe: None

# -

import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import ramanchada2 as rc2

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

devices_h5file= upstream["load_spectra"]["data"]
devices = pd.read_hdf(devices_h5file, "devices")
devices.head()

#peaks
reference_condition = (devices["reference"]) & (devices["probe"] == probe)
devices.loc[reference_condition ,"amplitude"] = devices.loc[(devices["reference"]) ]["spectrum_corrected"].apply(calc_peak_amplitude)
devices.to_hdf(devices_h5file, key='devices', mode='w')

#regression
A= devices.loc[devices["reference"],["reference","laser_power","amplitude"]]
(intercept_A,slope_A) = calc_regression(A[["laser_power"]],A["amplitude"])
#devices.loc[reference_condition,"slope"]
#devices.to_hdf(devices_h5file, key='devices', mode='w')
devices.loc[reference_condition][["reference","device","laser_power","amplitude"]]

#peaks
twinned_condition = (~devices["reference"]) & (devices["probe"] == probe)
devices.loc[twinned_condition,"amplitude"] = devices.loc[twinned_condition]["spectrum_corrected"].apply(calc_peak_amplitude)
devices.to_hdf(devices_h5file, key='devices', mode='w')

#regression
B= devices.loc[twinned_condition,["reference","laser_power","amplitude"]]
#devices.loc[twinned_condition,"slope"] = 
(intercept_B,slope_B) = calc_regression(B[["laser_power"]],B["amplitude"])
#devices.to_hdf(devices_h5file, key='devices', mode='w')
devices.loc[twinned_condition][["reference","device","laser_power","amplitude"]]


A = devices.loc[reference_condition]
B = devices.loc[twinned_condition]
plt.plot(A["laser_power"],A["amplitude"],'o',label="A")
plt.plot(B["laser_power"],B["amplitude"],'+',label="B")
plt.legend()

#Factor correction (FC) is obtained by dividing the slope of the reference equipment (spectrometer A) 
# by the slope of the equipment to be twinned (spectrometer B).

factor_correction = slope_A/slope_B
print(slope_A,slope_B,factor_correction)



def harmonization(row):
    try:
        spe = row["spectrum_corrected"]       
        return rc2.spectrum.Spectrum(spe.x, spe.y *factor_correction)
    except Exception as err:
        print(err)
        return None

devices.loc[twinned_condition,"spectrum_harmonized"] = devices.loc[twinned_condition].apply(harmonization,axis=1)
devices.to_hdf(devices_h5file, key='devices', mode='w')

import matplotlib.pyplot as plt
def plot_spectra(row):
    try:
        sc =row["spectrum_corrected"]
        sc = sc.trim_axes(method='x-axis', boundaries=(65, 1750))        
        sc.plot(ax=axes[0],label="{}%".format(row["laser_power_percent"]))
    except:
        pass
    try:
        sc =row["spectrum_harmonized"]
        sc = sc.trim_axes(method='x-axis', boundaries=(65, 1750))
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