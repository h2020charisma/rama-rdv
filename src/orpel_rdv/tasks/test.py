# + tags=["parameters"]
upstream = []
product = None
root_data_folder = None
input_files = None
standard_files = None
reference_files = None
calibration_files = None
# -

# https://github.com/mr-sheg/orpl/tree/main/demos

import json
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import scipy.io as sio
import os.path
from orpl.cosmic_ray import crfilter_multi
from orpl.calibration import compute_irf
from orpl.baseline_removal import imodpoly
from orpl.baseline_removal import bubblefill
from orpl.calibration import nm2icm, icm2nm
from orpl.calibration import find_npeaks


def reference_spectra(reference_files):
    from orpl.calibration import nm2icm, icm2nm

    # Loading reference tylenol
    data = np.genfromtxt(reference_files[0], delimiter=',')

    xaxis = data[1:, 0]
    ref_tylenol_x = nm2icm(xaxis, 785)
    ref_tylenol_r = data[1:, 2]

    # Loading reference nylon
    data = np.genfromtxt(reference_files[1], delimiter=',')

    xaxis = data[1:, 0]
    ref_nylon_x = nm2icm(xaxis, 785)
    ref_nylon_r = data[1:, 2]
 
    return [ (ref_tylenol_x,ref_tylenol_r),(ref_nylon_x,ref_nylon_r)] 

def calibration_spectra(calibration_files):
    #tbd demo5
    pass



input_files = os.path.abspath(os.path.join(root_data_folder,input_files))
assert(os.path.exists(input_files))
standard_files = os.path.abspath(os.path.join(root_data_folder,standard_files))
assert(os.path.exists(standard_files))
reference_file = []
for ref in reference_files.split(","):
    tmp = os.path.abspath(os.path.join(root_data_folder,ref))
    assert(os.path.exists(tmp))  
    reference_file.append(tmp) 
ref_spectra = reference_spectra(reference_file) 
plt.figure(figsize=[12, 2])
for idx, ref in enumerate(ref_spectra): 
    plt.subplot(1, 2, idx+1)
    plt.plot(ref[0], ref[1])
    plt.title('Ref {} Raman spectrum'.format(idx))
    plt.xlabel('Raman Shift [$cm^{-1}$]')
    plt.ylabel('I [au]')    
    ntarget = 7
    pid = find_npeaks(ref[1], ntarget)
    #plt.plot(ref[1], label=' spectrum')
    plt.plot(ref[0][pid], ref[1][pid], 'o', color='tab:red', label='Identified peaks')
    plt.legend()

plt.figure(figsize=[12, 2])
for idx, ref in enumerate(ref_spectra):     
    ax1 = plt.subplot(1, 2, idx+1)
    # Convert cm-1 to nm
    tylenol_x_nm = icm2nm(ref[0])
    # Convert nm to cm-1
    tylenol_x_icm = nm2icm(tylenol_x_nm)
    plt.title('xaxis')
    ax2 = ax1.twinx()
    ax1.plot(tylenol_x_nm, color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax1.set_xlabel('Camera Pixel')
    ax1.set_ylabel('[nm]')
    ax2.plot(tylenol_x_icm, color='tab:red')
    ax2.tick_params(axis='y', labelcolor='tab:red')
    ax2.set_ylabel('[$cm^{-1}$]');


# Loading NIST data
def irf(standard_files,crop_pos=50):
    try:
        with open(standard_files, encoding='utf8') as file:
            nist=json.load(file)
        nist = nist[10] # keeping only the 10th acquisition

        fig, (ax1, ax2, ax3) = plt.subplots(1, 3)
        fig.set_figheight(3)
        fig.set_figwidth(18)
        # Cropping nist
        nist['cropped'] = np.array(nist['RawSpectra'])
        nist['cropped'] = nist['cropped'][crop_pos:, :]

        ax1.plot(nist['RawSpectra']);
        ax2.plot(nist['cropped']);

        sys_response = compute_irf(nist['cropped'].mean(axis=1))
        ax3.plot(sys_response)
        return sys_response
    except Exception as err:
        print(err)



data = json.load(open(input_files))
crop_pos = 50
sys_response = irf(standard_files, crop_pos )
for idx, datum in enumerate(data):    
    if idx in [2,25,32,48]:
        fig, (ax1, ax2, ax3 ,ax4, ax5) = plt.subplots(1, 5)
        fig.set_figheight(2)
        fig.set_figwidth(18)
        #for key in datum.keys():
        #    print(key)
        spectra = np.array(datum['RawSpectra'])
        ax1.plot(spectra);
        plt.title("{}. {}".format(idx,datum["Comment"]));
        plt.xlabel('Camera pixels')
        plt.ylabel('Counts');   
        spectra_filtered = crfilter_multi(spectra.T) 
        datum['filtered'] = spectra_filtered.transpose()
        ax2.plot(datum['filtered'])
        datum['cropped'] = np.array(datum['filtered'])
        datum['cropped'] = datum['cropped'][crop_pos:, :]
        ax3.plot(datum['cropped'])
        datum['corrected'] = datum['cropped'].transpose()/sys_response
        datum['corrected'] = datum['corrected'].transpose()
        ax4.plot(datum['corrected'])

        fat_r = []
        fat_b = []
        for s in datum['corrected'].transpose():
            #r, b = imodpoly(s)
            r,b = bubblefill(s, min_bubble_widths=75)
            fat_r.append(r)
            fat_b.append(b)

        for s in fat_b:
            ax5.plot(s.T)

        datum['baseline_removed'] = np.array(fat_r)    
        datum['baseline_removed'] = datum['baseline_removed'].transpose()  
        ax5.plot(datum['baseline_removed'])
plt.legend()
plt.tight_layout()    