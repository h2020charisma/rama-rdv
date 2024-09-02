# + tags=["parameters"]
upstream = []
product = None
domain = None
nexus_folder2import = None
# -

import os.path
from pyambit.datamodel import Substances, EffectRecord
import nexusformat.nexus as nx
import ramanchada2 as rc2 
from pathlib import Path
from pyambit.nexus_parser import Nexus2Ambit
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity
import numpy.typing as npt
import scipy.stats as stats

class Spectra2Ambit(Nexus2Ambit):
        
    def __init__(self,domain : str, index_only : bool = True, dim = 2048, xoffset=140):
        super().__init__(domain, index_only)
        self.dim = dim
        self.xoffset = xoffset
        self.x4search = np.linspace(xoffset,3*1024+xoffset,num=self.dim)

    def parse_studies(self,nxroot : nx.NXroot, relative_path : str):
        super().parse_studies(nxroot, relative_path)
        
    @staticmethod
    def resample(spe :  rc2.spectrum.Spectrum, x4search : npt.NDArray):
        (spe,hist_dist,index) = Spectra2Ambit.spectra2dist(spe,xcrop = [x4search[0],x4search[-1]])
        return hist_dist.pdf(x4search)    

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
        result = super().parse_effect(endpointtype_name, data, relative_path)
        spe = rc2.spectrum.Spectrum(x = data.nxaxes[1].nxdata,y= np.mean(data.nxsignal.nxdata, axis=0))
        #how to set y_err
        #spe.y_err= np.std(data.nxsignal.nxdata, axis=0)
        fig, axs = plt.subplots(1, 3, figsize=(15, 5))  
        spe.plot(ax=axs[0],label = relative_path)
        x_range=(min(self.x4search), max(self.x4search))
        spe_trimmed = spe.trim_axes(method='x-axis',boundaries=x_range)
        spe_trimmed.plot(ax=axs[0],label = "trimmed")
        spe_resampled = spe_trimmed.resample_NUDFT_filter(xnew_bins=self.dim, x_range=x_range)
        spe_resampled.plot(ax=axs[1],label = relative_path)

        spe_dist_resampled = Spectra2Ambit.resample(spe_trimmed,self.x4search)
        rc2.spectrum.Spectrum(x=self.x4search,y=spe_dist_resampled).plot(ax=axs[2],label = relative_path)
        axs[0].set_title('Original')
        axs[1].set_title('NUDFT')
        axs[2].set_title('stats.rv_histogram')
        return result


def main():
    try:
        path = Path(nexus_folder2import)

        parser : Spectra2Ambit = Spectra2Ambit(domain="/{}".format(domain),index_only=True)        
        for item in path.rglob('*.nxs'):
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
            #break
        substances : Substances = parser.get_substances()    

    except Exception as err:
        print(err)

main()        

#cos_sim_matrix_original =  cosine_similarity(spe_y_original)
#    cos_sim_matrix =  cosine_similarity(spe_calibrated)