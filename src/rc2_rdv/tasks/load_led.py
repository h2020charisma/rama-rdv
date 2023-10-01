# + tags=["parameters"]
upstream = []
product = None
root_data_folder: None
files_led_reference: None
files_led_twinned: None

# -
import os
import matplotlib.pyplot as plt
import re
import ramanchada2 as rc2


def load_led(root_led=root_data_folder,folder_path_led=[files_led_reference,files_led_twinned],filter_filename="r'^(LED|NIR)'",filter_probe="Probe"):
    led_spectra={}
    for subset in folder_path_led:
        ax=None
        plt.figure(figsize=(15, 2))
        for filename in os.listdir(os.path.join(root_led,subset)):
            if filename.endswith('.xlsx'): 
                continue
            if re.match(filter_filename, filename):
                if not filter_probe in filename:
                    continue
                result = re.split(r'[_().]+', filename)
                result = [s for s in result if s]            
                #print(result)            
                spe_led = rc2.spectrum.from_local_file(os.path.join(root_led,subset,filename))
                spe_led_y = spe_led.y
                spe_led_y[spe_led_y < 0] = 0
                spe_led.y = spe_led_y
                led_spectra[subset]=spe_led

                plt.subplot(131) 
                plt.plot(spe_led.x, spe_led.y, label=subset)
                plt.title("LED" +subset)
                #break
        plt.show()

load_led(root_led=root_data_folder,folder_path_led=[files_led_reference,files_led_twinned],filter_filename="r'^(LED|NIR)'",filter_probe="Probe")