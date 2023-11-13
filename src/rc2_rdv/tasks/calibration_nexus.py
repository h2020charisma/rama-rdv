# + tags=["parameters"]
upstream = ["calibration_neon"]
product = None
calibration_file = None
input_file = None
# -

import os.path
from ramanchada2.spectrum import from_chada,from_local_file
import ramanchada2.misc.constants  as rc2const
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path
from ramanchada2.protocols.calibration import CalibrationModel
import numpy as np
from  pynanomapper.datamodel.nexus_writer import to_nexus
from  pynanomapper.datamodel.nexus_spectra import spe2ambit
from  pynanomapper.datamodel.ambit import Substances,SubstanceRecord,CompositionEntry,Component, Compound
import nexusformat.nexus.tree as nx

def calmodel2nexus(calmodel, nexus_file_path):
    substances = []
    for model in calmodel.components:
        spe = model.spe
        print(model)
        print(model.sample)
        papp = spe2ambit(spe.x,spe.y,spe.meta,
                            instrument = "instrument",
                            wavelength=calmodel.laser_wl,
                            provider="provider",
                            investigation="calibration",
                            sample=model.sample,
                            sample_provider = "sample_provider",
                            prefix = "TEST")                       
        substance = SubstanceRecord(name=model.sample,i5uuid=papp.owner.substance.uuid)
        substance.composition = list()
        composition_entry = CompositionEntry(component = Component(compound = Compound(name=model.sample),values={}))
        substance.composition.append(composition_entry)
        if substance.study is None:
            substance.study = [papp]
        else:
            substance.study.add(papp)
        
        substances.append(substance)
        #study = mx.Study(study=studies)
    nxroot = Substances(substance=substances).to_nexus(nx.NXroot())
    nxroot.save(nexus_file_path,mode="w")

calmodel = CalibrationModel.from_file(calibration_file)
calmodel2nexus(calmodel,product["nexus"])


spe_to_calibrate = from_local_file(input_file)
spe_to_calibrate.plot()
if min(spe_to_calibrate.x)<0:
    spe_to_calibrate = spe_to_calibrate.trim_axes(method='x-axis',boundaries=(0,max(spe_to_calibrate.x)))     
kwargs = {"niter" : 40 }
spe_to_calibrate = spe_to_calibrate.subtract_baseline_rc1_snip(**kwargs)
#spe_to_calibrate = spe_to_calibrate - spe_to_calibrate.moving_minimum(120)
#spe_to_calibrate = spe_to_calibrate.normalize()    
spe_to_calibrate.plot(label="moving min")  


spe_calibrated_ne_sil = calmodel.apply_calibration_x(spe_to_calibrate,spe_units="cm-1")

fig, ax = plt.subplots(1,1,figsize=(12,2))
spe_to_calibrate.plot(ax=ax,label = "original")
spe_calibrated_ne_sil.plot(ax=ax,label="Ne+Si calibrated",fmt=":")


def plot_peaks_stem(ref_keys,ref_values,spe_keys,spe_values,spe=None, label="calibrated"):
    fig, ax = plt.subplots(figsize=(12, 2))
    pst = rc2const.PST_RS_dict
    ref_stem = ax.stem(pst.keys(), pst.values(), linefmt='b-', label='reference')
    stem_plot = ax.twinx()
    calibrated_stem = stem_plot.stem(spe_keys, spe_values, linefmt='r-', markerfmt='ro', basefmt=' ')
    # Create custom legend elements
    legend_elements = [
        Line2D([0], [0], color='b', linestyle='-', label='reference'),
        Line2D([0], [0], color='r', linestyle='-', marker='o', label='calibrated')
    ]
    ax.legend(handles=legend_elements)
    ax.grid(True)
    if spe != None:
        spe.plot(ax=stem_plot,label=label)
    plt.show()

profile = "Voigt"
wlen = 100
width = 3

cand, init_guess, fit_res = calmodel.peaks(spe_calibrated_ne_sil,profile=profile,wlen=wlen,width=width)
fig, ax = plt.subplots(3,1,figsize=(12, 4))
data_list = [cand, init_guess, fit_res]
for data, subplot in zip(data_list, ax):
    spe_calibrated_ne_sil.plot(ax=subplot, fmt=':')
    data.plot(ax=subplot)

#original spectrum to be calibrated
cand_0, init_guess_0, fit_res_0 = calmodel.peaks(spe_to_calibrate,profile=profile,wlen=wlen,width=width)
fig, ax = plt.subplots(3,1,figsize=(12, 4))
data_list = [cand_0, init_guess_0, fit_res_0 ]
for data, subplot in zip(data_list, ax):
    spe_calibrated_ne_sil.plot(ax=subplot, fmt=':')
    data.plot(ax=subplot)

df_peaks = fit_res.to_dataframe_peaks()
df_peaks["Original file"] = spe_to_calibrate.meta["Original file"]
df_peaks[['group', 'peak']] = df_peaks.index.to_series().str.split('_', expand=True)
df_peaks["param_profile"] = profile
df_peaks["param_wlen"] = wlen
df_peaks["param_width"] = width
df_peaks["param_prominence"] = spe_calibrated_ne_sil.y_noise*calmodel.prominence_coeff
df_peaks.to_csv(os.path.join(upstream["calibration_neon"]["data"],spe_to_calibrate.meta["Original file"]+".csv"))

from ramanchada2.misc import utils as rc2utils

sample = "PST"
if sample=="PST":
    pst = rc2const.PST_RS_dict
    plot_peaks_stem(pst.keys(), pst.values(),df_peaks["center"], df_peaks["height"] , spe_calibrated_ne_sil ,label="calibrated")      
    plot_peaks_stem(pst.keys(), pst.values(),df_peaks["center"], df_peaks["height"] , spe_to_calibrate , label="original")        

    x_sample,x_reference,x_distance,df = rc2utils.match_peaks(cand_0.get_pos_ampl_dict(),pst)
    print(x_sample,x_reference)
    sum_of_distances = np.sum(x_distance) / len(x_sample)
    sum_of_differences = np.sum(np.abs(x_sample - x_reference)) / len(x_sample)
    print("original sum of diff",sum_of_differences,"original sum of distances",sum_of_distances,len(x_sample),list(zip(x_sample,x_reference)))    
    x_sample,x_reference,x_distance,df = rc2utils.match_peaks(cand.get_pos_ampl_dict(),pst)
    print(x_sample,x_reference)
    sum_of_differences = np.sum(np.abs(x_sample - x_reference)) / len(x_sample)
    sum_of_distances = np.sum(x_distance) / len(x_sample)
    print("calibrated sum of diff",sum_of_differences,"calibrated sum of distances",sum_of_distances,len(x_sample),list(zip(x_sample,x_reference)))

