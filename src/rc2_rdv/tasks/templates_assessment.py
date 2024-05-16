# + tags=["parameters"]
upstream = ["templates_load","templates_read","templates_calibration"]
product = None
neon_tag = None
si_tag = None
pst_tag = None
test_tags = None
# -

import pandas as pd
import matplotlib.pyplot as plt
import os.path
from ramanchada2.spectrum import from_chada

_source = upstream["templates_load"]["data"]
_calibrated = upstream["templates_calibration"]["data"]


metadata = pd.read_hdf(upstream["templates_read"]["h5"], key="templates_read")
unique_optical_paths = metadata['optical_path'].unique()

color_map = {}
for index, string in enumerate(set([neon_tag,si_tag,pst_tag])):
    color_map[string] = plt.cm.tab10(index) 

trim_left = 100
for op in unique_optical_paths:
    op_meta = metadata.loc[metadata["optical_path"] == op]
    if not op_meta['enabled'].unique()[0]:
        continue
    provider = op_meta['provider'].unique()[0]
    wavelength = op_meta['wavelength'].unique()[0]    
    _path_source = os.path.join(_source,str(int(wavelength)),op)
    _path_calibrated = os.path.join(_calibrated,op)

    fig, ax = plt.subplots(1, 2, figsize=(15,2))    
    fig.suptitle("{} {} {}".format(op,provider,wavelength))
    #ax[].set_title("normalized")
    #ax2.set_title("calibrated")
    for index, tag in enumerate([ si_tag, pst_tag]):
        ax[index].set_title(tag)
        try:
            spe = from_chada(os.path.join(_path_source,"{}.cha".format(tag)),dataset="/normalized")
            spe.plot(label=tag,ax=ax[index],color=color_map[tag])
        except Exception as err:
            print(err)
            pass        
        try:
            spe = from_chada(os.path.join(_path_calibrated,"{}.cha".format(tag)),dataset="/calibrated")
            spe.plot(label="{} calibrated".format(tag),ax=ax[index],color="#FF0000")
        except Exception as err:
            print(err)
            pass