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
from scipy.interpolate import CubicSpline
import traceback

class Spectra2Ambit(Nexus2Ambit):
        
    def __init__(self,domain : str, index_only : bool = True, dim = 2048, xoffset=128):
        super().__init__(domain, index_only)
        self.dim = dim
        self.xoffset = xoffset
        self.x4search = np.linspace(xoffset,3*1024+xoffset,num=self.dim)

    def parse_studies(self,nxroot : nx.NXroot, relative_path : str):
        super().parse_studies(nxroot, relative_path)
        
    @staticmethod
    def resample(spe :  rc2.spectrum.Spectrum, x4search : npt.NDArray):
        (spe,hist_dist,index) = Spectra2Ambit.spectra2dist(spe,xcrop = [x4search[0],x4search[-1]])
        spe_dist_resampled = np.zeros_like(x4search)
        within_range = (x4search >= min(spe.x)) & (x4search <= max(spe.x))
        spe_dist_resampled[within_range] =  hist_dist.pdf(x4search[within_range])    
        return spe_dist_resampled

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
        fig, axs = plt.subplots(1, 3, figsize=(15, 4))  
        spe.plot(ax=axs[0],label = relative_path)
        x_range=(min(self.x4search), max(self.x4search))
        spe_trimmed = spe.trim_axes(method='x-axis',boundaries=x_range)
        spe_trimmed.plot(ax=axs[0],label = "trimmed")
        spe_nospikes = spe_trimmed.drop_spikes()
        spe_nospikes.plot(ax=axs[0],label = "no spikes")

        if np.min(spe_nospikes.y) > 0:
            spe_transformed = rc2.spectrum.Spectrum(x=spe_nospikes.x, y = spe_nospikes.y - np.min(spe_nospikes.y))
            spe_transformed.plot(ax=axs[0],label = "no pedestal")
        else:
            spe_transformed = spe_nospikes

        kwargs = {"niter" : 40 }
        spe_transformed = spe_transformed.subtract_baseline_rc1_snip(**kwargs)  
        spe_transformed.plot(ax=axs[0],label = "SNIP baseline")

        try:
            _newdim = np.round(2  * len(spe_transformed.x))
        
            spe_resampled = spe_transformed.resample_NUDFT_filter(xnew_bins=_newdim, x_range=x_range)
            spe_resampled.plot(ax=axs[1],label = "2. len/dim={:.4f} len={}".format(len(spe_transformed.x)/(_newdim), len(spe_transformed.x)))
            spe_resampled = spe_resampled.resample_NUDFT_filter(xnew_bins=self.dim, x_range=x_range)
            spe_resampled.plot(ax=axs[1],label = "2. len/dim={:.4f}".format(_newdim/self.dim),linestyle='--')
        except Exception as err:
            print(err)


        spline = CubicSpline(spe_transformed.x, spe_transformed.y)
        # Step 2: Initialize the array to store the spline values
        spe_spline = np.zeros_like(self.x4search)
        xmin, xmax = spe_transformed.x.min(), spe_transformed.x.max()
        within_range = (self.x4search >= xmin) & (self.x4search <= xmax)
        spe_spline[within_range] = spline(self.x4search[within_range])
        l2_norm = np.linalg.norm(spe_spline)

        rc2.spectrum.Spectrum(x=self.x4search,y=spe_spline/l2_norm).plot(ax=axs[2],label = "spline")

       
        spe_dist_resampled = Spectra2Ambit.resample(spe_transformed,self.x4search)
        l2_norm = np.linalg.norm(spe_dist_resampled)
        rc2.spectrum.Spectrum(x=self.x4search,y=spe_dist_resampled/l2_norm).plot(ax=axs[2],label = "rv_histogram", linestyle='--')


        axs[0].set_title('Original')
        axs[1].set_title('NUDFT')
        axs[2].set_title('CubicSpline & stats.rv_histogram')
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
                    print(traceback.format_exc())
                    print(item,err)
            #break
        substances : Substances = parser.get_substances()    

    except Exception as err:
        print(err)

main()        

#cos_sim_matrix_original =  cosine_similarity(spe_y_original)
#    cos_sim_matrix =  cosine_similarity(spe_calibrated)