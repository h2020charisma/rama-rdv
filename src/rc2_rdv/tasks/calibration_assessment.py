# + tags=["parameters"]
upstream = ["calibration_nexus"]
product = None
input_files = None
model = None
# -

import os.path
from ramanchada2.spectrum import from_chada
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import ramanchada2.misc.constants  as rc2const
from ramanchada2.protocols.calibration import CalibrationModel
import ramanchada2.misc.utils as rc2utils
import numpy as np

def plot_peaks_stem(ref_keys,ref_values,spe_keys,spe_values,spe=None, label="calibrated"):
    fig, ax = plt.subplots(figsize=(12, 2))
    ref_stem = ax.stem(ref_keys, ref_values, linefmt='b-', label='reference')
    stem_plot = ax.twinx()
    calibrated_stem = stem_plot.stem(spe_keys, spe_values, linefmt='r-', markerfmt='ro', basefmt=' ')
    # Create custom legend elements
    legend_elements = [
        Line2D([0], [0], color='b', linestyle='-', label='reference'),
        Line2D([0], [0], color='r', linestyle='-', marker='o', label=label)
    ]
    ax.legend(handles=legend_elements)
    ax.grid(True)
    if spe != None:
        spe.plot(ax=stem_plot, fmt=':')
    plt.show()

calmodel = CalibrationModel.from_file(model)    

for input_file in input_files.split(","):
    input_folder = upstream["calibration_nexus"]["nexus"]
    cha_file = os.path.join(input_folder,"{}.cha".format(input_file))
    spe_raw = from_chada(cha_file, dataset="/raw")
    spe_calibrated = from_chada(cha_file, dataset="/calibrated")
    fig, ax = plt.subplots(1,1,figsize=(12,3))
    spe_raw.plot(label="original",ax=ax)
    spe_calibrated.plot(label="calibrated",ax=ax)
    ax.set_title(input_file)
    profile = "Voigt"
    wlen = 100
    width = 3
    cand, init_guess, fit_res = calmodel.peaks(spe_calibrated,profile=profile,wlen=wlen,width=width)
    peaks_calibrated = dict(zip(fit_res.locations, fit_res.amplitudes))
    fig, ax = plt.subplots(3,1,figsize=(12, 4))
    data_list = [cand, init_guess, fit_res]
    for data, subplot in zip(data_list, ax):
        spe_calibrated.plot(ax=subplot, fmt=':')
        data.plot(ax=subplot)    
    #original spectrum to be calibrated
    cand_0, init_guess_0, fit_res_0 = calmodel.peaks(spe_raw,profile=profile,wlen=wlen,width=width)
    peaks_original = dict(zip(fit_res_0.locations, fit_res_0.amplitudes))
    fig, ax = plt.subplots(3,1,figsize=(12, 4))
    data_list = [cand_0, init_guess_0, fit_res_0 ]
    for data, subplot in zip(data_list, ax):
        spe_raw.plot(ax=subplot, fmt=':')
        data.plot(ax=subplot)
    df_peaks = fit_res.to_dataframe_peaks()
    df_peaks["Original file"] = spe_raw.meta["Original file"]
    df_peaks[['group', 'peak']] = df_peaks.index.to_series().str.split('_', expand=True)
    df_peaks["param_profile"] = profile
    df_peaks["param_wlen"] = wlen
    df_peaks["param_width"] = width
    df_peaks["param_prominence"] = spe_calibrated.y_noise*calmodel.prominence_coeff
    df_peaks.to_csv(os.path.join(upstream["calibration_nexus"]["nexus"],spe_raw.meta["Original file"]+".csv"))
    if input_file.startswith("PST") or input_file.startswith("NMIJ") or input_file.startswith("NIST"):
        pst = rc2const.PST_RS_dict
        plot_peaks_stem(pst.keys(), pst.values(),df_peaks["center"], df_peaks["height"] , spe_calibrated ,label="calibrated")      
        plot_peaks_stem(pst.keys(), pst.values(),df_peaks["center"], df_peaks["height"] , spe_raw , label="original")  

        x_sample,x_reference,x_distance,df = rc2utils.match_peaks(peaks_original,pst)
        #print(x_sample,x_reference)
        sum_of_distances = np.sum(x_distance) / len(x_sample)
        sum_of_differences = np.sum(np.abs(x_sample - x_reference)) / len(x_sample)
        print("original sum of diff {:.4f} original sum of distances  {:.4f} len {}; {}".format(sum_of_differences,sum_of_distances,len(x_sample),list(zip(x_sample,x_reference))))

        x_sample,x_reference,x_distance,df = rc2utils.match_peaks(peaks_calibrated,pst)
        #print(x_sample,x_reference)
        sum_of_differences = np.sum(np.abs(x_sample - x_reference)) / len(x_sample)
        sum_of_distances = np.sum(x_distance) / len(x_sample)
        print("calibrated sum of diff {:.4f} calibrated sum of distances {:.4f} len {}; {}".format(sum_of_differences,sum_of_distances,len(x_sample),list(zip(x_sample,x_reference))))

