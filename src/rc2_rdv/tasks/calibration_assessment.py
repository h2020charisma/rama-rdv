# + tags=["parameters"]
upstream = ["calibration_nexus"]
product = None
input_files = None
model = None
# -

import os.path
from ramanchada2.spectrum import from_chada
import matplotlib.pyplot as plt

for input_file in input_files.split(","):
    input_folder = upstream["calibration_nexus"]["nexus"]
    cha_file = os.path.join(input_folder,"{}.cha".format(input_file))
    spe_raw = from_chada(cha_file, dataset="/raw")
    spe_calibrated = from_chada(cha_file, dataset="/calibrated")
    fig, ax = plt.subplots(1,1,figsize=(12,3))
    spe_raw.plot(label="original",ax=ax)
    spe_calibrated.plot(label="calibrated",ax=ax)
    ax.set_title(input_file)