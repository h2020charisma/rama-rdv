# + tags=["parameters"]
upstream = ["calibration_neon"]
product = None
input_folder = None
input_files = None
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

def calmodel2nexus(calmodel, spectra, tags, nexus_file_path):
    substances = []
    
    for model in calmodel.components:
        fig, ax = plt.subplots(1,2,figsize=(12,3))
        spe = model.spe
        #if model.sample=="Silicon":
        #    spe.trim_axes(method='x-axis',boundaries=(520-50,520+50)).plot(ax=ax[0],label=model.sample)
        #else:
        spe.plot(ax=ax[0],label=model.sample)

        ax[0].set_xlabel("cm-1")
        #print(model)
        print("sample {}, spe units {} reference units {} model units {}".format(model.sample,model.spe_units,model.ref_units,model.model_units))
        #this is the spectrum used to derive the calibration model, e.g. Ne or Si
        papp = spe2ambit(spe.x,spe.y,spe.meta,
                            instrument = "instrument",
                            wavelength=calmodel.laser_wl,
                            provider="provider",
                            investigation="calibration source",
                            sample=model.sample,
                            sample_provider = "sample_provider",
                            prefix = "MODEL", unit="cm-1")
                            #unit=model.spe_units)   
            
        #spe_calibrated_ne_sil = calmodel.apply_calibration_x(spe,spe_units="cm-1") 
        #spe_calibrated_ne_sil.plot(ax=ax[1],label=f"{model.sample} calibrated")                  
        #spe_new = calmodel.apply_calibration_x(spe,model.spe_units) 
        #if model.sample=="Silicon":
        #    spe_new.trim_axes(method='x-axis',boundaries=(520-50,520+50)).plot(ax=ax[1],label=f"{model.sample} calibrated")
        #else:
        #    spe_new.plot(ax=ax[1],label=f"{model.sample} calibrated")    
        # this is the Ne or Si spectrum after applying this particular calibration component  
        #spe2ambit(spe_new.x,spe_new.y,spe_new.meta,
        #                    instrument = "instrument",
        #                    wavelength=calmodel.laser_wl,
        #                    provider="provider",
        #                    investigation="calibration source",
        #                    sample=model.sample,
        #                    sample_provider = "sample_provider",
        #                    prefix = "MODEL",
        #                    #unit=model.spe_units,
        #                    unit="cm-1",
        #                    endpointtype="CALIBRATED",papp=papp) 
                                  
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

    papp = None
    fig, ax = plt.subplots(1,1,figsize=(12,4))
    
    for spe, label in zip(spectra, tags):
        #get sample name, instrument etc from metadata
        sample=spe.meta["Original file"]
        ax.set_title(sample)
        spe.plot(ax=ax,label=label)
        papp = spe2ambit(spe.x,spe.y,spe.meta,
                            instrument = "instrument",
                            wavelength=calmodel.laser_wl,
                            provider="provider",
                            investigation="calibrated spectra",
                            sample=sample,
                            sample_provider = "sample_provider",
                            prefix = "APPLY",unit="cm-1",endpointtype=label,papp=papp)
    substance = SubstanceRecord(name=sample,i5uuid=papp.owner.substance.uuid)
    substance.composition = list()
    composition_entry = CompositionEntry(component = Component(compound = Compound(name=sample),values={}))
    substance.composition.append(composition_entry)
    if substance.study is None:
        substance.study = [papp]
    else:
        substance.study.add(papp)
    substances.append(substance)

    nxroot = Substances(substance=substances).to_nexus(nx.NXroot())
    print(nexus_file_path)
    nxroot.save(nexus_file_path,mode="w")

Path(product["nexus"]).mkdir(parents=True, exist_ok=True)
# load calibration model
calibration_file = upstream["calibration_neon"]["model"]
print(calibration_file)
calmodel = CalibrationModel.from_file(calibration_file)
#calmodel2nexus(calmodel,[spe_to_calibrate,spe_trimmed,spe_baseline_removed],["RAW_DATA","1.TRIMMED","2.BASELINE_REMOVED"],product["nexus"])

# load the spectra to be calibrated
fig, ax = plt.subplots(1,1,figsize=(12,4))
for input_file in input_files.split(","):
    print(os.path.join(input_folder,input_file))
    spe_to_calibrate = from_local_file(os.path.join(input_folder,input_file))
    spe_to_calibrate.plot(label="original",ax=ax)
    if min(spe_to_calibrate.x)<40:
        spe_trimmed = spe_to_calibrate.trim_axes(method='x-axis',boundaries=(0,max(spe_to_calibrate.x)))    
        spe_trimmed.plot(label="trimmed",ax=ax)
    else:
        spe_trimmed = spe_to_calibrate 
    kwargs = {"niter" : 40 }
    spe_baseline_removed = spe_trimmed.subtract_baseline_rc1_snip(**kwargs)
    #spe_to_calibrate = spe_to_calibrate - spe_to_calibrate.moving_minimum(120)
    #spe_to_calibrate = spe_to_calibrate.normalize()    
    spe_baseline_removed.plot(label="baseline_snip",ax=ax)  
    spe_to_calibrate = spe_baseline_removed
    spe_calibrated_ne_sil = calmodel.apply_calibration_x(spe_to_calibrate,spe_units="cm-1")
    #spe_to_calibrate.plot(ax=ax,label = "original")
    spe_calibrated_ne_sil.plot(ax =ax, label="Ne+Si calibrated",fmt=":")
    ax.set_title(input_file)
    plt.show()

    calmodel2nexus(calmodel,
                   [spe_to_calibrate,spe_trimmed,spe_baseline_removed,spe_calibrated_ne_sil],
                   ["RAW_DATA","1.TRIMMED","2.BASELINE_REMOVED","CALIBRATED"],
                   os.path.join(product["nexus"],"{}-calibrated.nxs".format(os.path.basename(spe_to_calibrate.meta["Original file"]))),
                   )

