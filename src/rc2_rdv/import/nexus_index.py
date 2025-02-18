# + tags=["parameters"]
upstream = []
product = None
domain = None
baseline_remove = None
dataset = None
# -


import logging
import traceback
from pathlib import Path
from pyambit.solr_writer import Ambit2Solr
from pyambit.nexus_parser import Nexus2Ambit
from typing import Dict
from pyambit.datamodel import Substances, EffectRecord, EffectResult, EffectArray, ValueArray, SubstanceRecord
import nexusformat.nexus as nx
import ramanchada2 as rc2 
import numpy as np
import scipy.stats as stats
import numpy.typing as npt
import os
from scipy.interpolate import Akima1DInterpolator
import matplotlib.pyplot as plt
import shutil

# Set up basic configuration for logging to a file
logger = logging.getLogger('nexus_index')
# Set the level of the logger
logger.setLevel(logging.DEBUG)
# Create a file handler with 'w' mode to overwrite the file each time
file_handler = logging.FileHandler(product["data"], mode='w')
# Create a formatter and set it for the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
# Add the file handler to the logger
# Ensure no console handlers are attached
logger.handlers.clear()
logger.addHandler(file_handler)


class Spectra2Ambit(Nexus2Ambit):
        
    def __init__(self,domain : str, index_only : bool = True, dim = 2048, xoffset=140):
        super().__init__(domain, index_only)
        self.dim = dim
        self.xoffset = xoffset
        self.x4search = np.linspace(xoffset,3*1024+xoffset,num=self.dim)

    @staticmethod
    def resample_hist(spe :  rc2.spectrum.Spectrum, x4search : npt.NDArray):
        (spe,hist_dist,index) = Spectra2Ambit.spectra2dist(spe,xcrop = [x4search[0],x4search[-1]])
        spe_dist_resampled = np.zeros_like(x4search)
        within_range = (x4search >= min(spe.x)) & (x4search <= max(spe.x))
        spe_dist_resampled[within_range] =  hist_dist.pdf(x4search[within_range])    
        return rc2.spectrum.Spectrum(x=spe.x, y = spe_dist_resampled)
    
    @staticmethod
    def resample_spline(spe :  rc2.spectrum.Spectrum, x4search : npt.NDArray):
  
        spline = Akima1DInterpolator(spe.x, spe.y)
        spe_spline = np.zeros_like(x4search)
        xmin, xmax = spe.x.min(), spe.x.max()
        within_range = (x4search >= xmin) & (x4search <= xmax)
        spe_spline[within_range] = spline(x4search[within_range])
        return rc2.spectrum.Spectrum(x=x4search, y = spe_spline)

    @staticmethod
    def preprocess(spe :  rc2.spectrum.Spectrum, x4search : npt.NDArray, baseline = True):
        spe_nopedestal = rc2.spectrum.Spectrum(x=spe.x, y = spe.y - np.min(spe.y))
        try:
            spe_resampled = Spectra2Ambit.resample_spline(spe_nopedestal,x4search)
        except Exception as err:
            print(err)
            spe_resampled = Spectra2Ambit.resample_hist(spe_nopedestal,x4search)
        # baseline 
        if baseline:
            spe_resampled = spe_resampled.subtract_baseline_rc1_snip(niter = 40)  
        # L2 norm for searching
        l2_norm = np.linalg.norm(spe_resampled.y)

        return rc2.spectrum.Spectrum(x4search,spe_resampled.y / l2_norm)

    @staticmethod
    def spectra2dist(spe,xcrop = None):
        #no need to normalize, we'll generate probability distribution, it will self normalize!
        counts = spe.y # a spectrum is essentially a histogram :)
        x = spe.x
        #crop
        xcrop_right = max(x) if xcrop is None else xcrop[1]
        xcrop_left = 100 if xcrop is None else xcrop[0]
        index = np.where((x>=xcrop_left) & (x<=xcrop_right))
        index = index[0]
        x = x[index]
        counts = counts[index]
        bins =  np.concatenate((
            [(3*x[0] - x[1])/2],
            (x[1:] + x[:-1])/2,
            [(3*x[-1] - x[-2])/2]
        ))
        #and now derive a probability distribution, from which we are going to sample
        hist_dist = stats.rv_histogram((counts,bins))
        return (spe,hist_dist,index)

    def parse_effect(self, endpointtype_name, data : nx.NXentry, relative_path : str) -> EffectRecord:
        if self.index_only:
            if len(data.nxaxes)==1:
                spe = rc2.spectrum.Spectrum(x = data.nxaxes[0].nxdata,y= data.nxsignal.nxdata)
            else:
                spe = rc2.spectrum.Spectrum(x = data.nxaxes[1].nxdata,y= np.mean(data.nxsignal.nxdata, axis=0))

            #ax = spe.plot(label="original")
            spe_resampled = Spectra2Ambit.preprocess(spe,self.x4search,baseline=baseline_remove)
            #spe_resampled.plot(label="processed",ax=ax.twinx(),color='red')
            #ax.set_title(relative_path)
            #plt.savefig(os.path.join(product["plots"],"{}.png".format(relative_path)))
            _embeddings = None if np.isnan(spe_resampled.y).any() else spe_resampled.y
            #print(len(y_resampled),type(y_resampled))
            return EffectArray(
                    endpoint="spectrum_p1024",
                    endpointtype="embeddings",
                    conditions={
                    },
                    result=EffectResult(
                            textValue="{}/{}#{}".format(self.domain,relative_path,data.nxpath)
                    ),                    
                    signal=ValueArray(
                        unit="units",
                        values=_embeddings,
                        errQualifier="Error",
                        errorValue=None
                        # auxiliary={"spectrum_c1024": _embeddings },
                    ),
                    axes={
                        "x": ValueArray(
                            unit="cm-1", values=self.x4search, errQualifier="Error_x"
                        )
                    },
                    axis_groups=None,
                    idresult=None,
                    endpointGroup=None,
                    endpointSynonyms=[],
                    sampleID=None,
                )            
        else:
            raise NotImplementedError("Not implemented")          
        
class Spectra2Solr(Ambit2Solr):

    def effectrecord2solr(self,effect: EffectRecord, solr_index = None ):
        if solr_index is None:
            solr_index = {}            
        if isinstance(effect,EffectArray):
            # tbd - this is new in pyambit, we did not have array results implementation            
            if effect.result is not None:  #EffectResult
                self.effectresult2solr(effect.result,solr_index)
            # e.g. vector search                
            if effect.endpointtype == "embeddings":
                if effect.signal.values is not None:
                    solr_index[effect.endpoint] = effect.signal.values.tolist()
                if effect.signal.auxiliary is not None:
                    for aux in effect.signal.auxiliary:
                        if effect.signal.auxiliary[aux] is not None:
                            solr_index[aux] = effect.signal.auxiliary[aux].tolist()
        elif isinstance(effect,EffectRecord):
            #conditions
            if effect.result is not None:  #EffectResult
                self.effectresult2solr(effect.result,solr_index)        

def main(max_substances=1000, nexus_folder2import=None):
    index_part = 1
    path = Path(nexus_folder2import)
    parser : Spectra2Ambit = Spectra2Ambit(domain="/{}".format(domain),index_only=True)        
    for item in path.rglob('*.nxs'):
        try:
            relative_path = item.relative_to(path)
            absolute_path = item.resolve() 
            if item.is_dir():
                pass
            elif item.name.endswith(".nxs"):
                try:
                    absolute_path = item.resolve() 
                    nexus_file = nx.nxload(absolute_path)
                    parser.parse(nexus_file,relative_path.as_posix())
                except Exception as err:
                    print(item,err)
                    print(item,traceback.format_exc())
        except Exception as err:
            print(item,traceback.format_exc())
        nsubstances = len(parser.substances)
        if nsubstances % 5 == 0:
            print(nsubstances)
        if nsubstances > max_substances:
            try: 
                substances : Substances = parser.get_substances()    

                with Spectra2Solr(prefix="CRMA") as writer:
                    writer.write(substances, os.path.join(product["solr_index"],"solr_{}.json".format(index_part)))

                #ambit_json = substances.model_dump_json(exclude_none=True,indent=4)
                #with open(product["ambit_json"], 'w') as file:
                #    file.write(ambit_json) 
            except Exception as err:
                print(traceback.format_exc())
            index_part = index_part + 1
            parser = Spectra2Ambit(domain="/{}".format(domain),index_only=True)   
            break


if os.path.exists(product["solr_index"]):
    shutil.rmtree(product["solr_index"])
os.mkdir(product["solr_index"])    

  

nexus_folder2import = upstream["raman_slopp_*"][f"raman_slopp_{dataset}"]["nexus"]
main(max_substances=100, nexus_folder2import=nexus_folder2import)      

file_handler.flush()
file_handler.close()