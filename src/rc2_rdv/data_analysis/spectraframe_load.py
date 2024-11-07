# + tags=["parameters"]
upstream = []
product = None
config_templates = None
config_root = None
key = None
# -

from ramanchada2.protocols.spectraframe import SpectraFrame
from ramanchada2.spectrum import Spectrum
from utils import read_template, load_config, is_in_skip, get_config_excludecols
import os.path
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

_config = load_config(os.path.join(config_root, config_templates))
Path(os.path.dirname(product["h5"])).mkdir(parents=True, exist_ok=True)

entry = _config["templates"][key]
_path_excel = os.path.join(config_root, entry["template"])
df = read_template(_path_excel, path_spectra=os.path.join(config_root, entry["path"]))
df['background'] = df['background'].str.upper() 
df["source"] = str(entry)


# this likely will need to be configurable
exclude_cols = get_config_excludecols(_config, key)

print(exclude_cols)
# ["date", "time", "measurement", "source", "file_name", "notes", "laser_power_percent",  "laser_power_mW", "background"]
# ['date', 'time', 'measurement', 'source', 'file_name', 'notes', 'laser_power_percent', 'integration_time_ms', 'humidity' ,'laser_power_mW', 'background']
# Get columns to group by
groupby_cols = [col for col in df.columns if col not in exclude_cols]
print(groupby_cols)

df["background_file"] = None

grouped_df = df.groupby(groupby_cols, dropna=False)

# figure out background files
for group_keys, sample_data in grouped_df:
    print(sample_data.shape, group_keys)
    fig, ax = plt.subplots(1, 1, figsize=(15,3))
    sample_data["spectrum"] = sample_data.apply(lambda row: Spectrum.from_local_file(row["file_name"]) if os.path.isfile(row["file_name"]) else None, axis=1)
    try:
        sample_data.apply(lambda row: None if row["spectrum"] is None else row["spectrum"].plot(ax=ax,label="{} {} ({})".format(os.path.basename(row["file_name"]), row["background"], row["overexposed"])),axis=1)
    except Exception as err:
        print(err)
    if sample_data.shape[0] < 2:
        continue
    background_only_file = sample_data.loc[sample_data["background"] == "BACKGROUND_ONLY", "file_name"]
    if not background_only_file.empty:
        if sample_data[sample_data["background"] == "BACKGROUND_NOT_SUBTRACTED"].empty:
            print("No rows found with 'BACKGROUND_NOT_SUBTRACTED'.")
        else:
            # Assign the first "Background_Only" file_name to rows where background is "Background_Not_Subtracted"
            df.loc[
                (df["file_name"].isin(sample_data["file_name"])) & 
                (df["background"] == "BACKGROUND_NOT_SUBTRACTED"), 
                "background_file"
            ] = background_only_file.iloc[0]

            print(background_only_file.iloc[0])
    else:
        print("No rows found with 'Background_Only'.")

df.to_hdf(product["h5"], key='templates_read', mode='w')
df.to_excel(product["xlsx"], sheet_name='templates_read', index=False)    

df_bkg_notsubtracted = df.loc[df["background"] == "BACKGROUND_NOT_SUBTRACTED"]

new_rows = []
for index, row in df_bkg_notsubtracted.iterrows():
    if row["background_file"] is None:
        continue
    fig, (ax, tax) = plt.subplots(2, 1, figsize=(15, 5))    
    print(row["file_name"], row["background_file"])    
    new_row = row.copy()
    if os.path.isfile(row["background_file"]):
        spe_bkg = Spectrum.from_local_file(row["background_file"])
        spe_bkg.plot(label="BACKGROUND_ONLY", ax=tax, linestyle='-', color='red')
        spe_bkg_nospikes = spe_bkg.recover_spikes()
        spe_bkg_nospikes.plot(label="Background_only_nospikes", ax=tax, linestyle='--', color='gray')
    else:
        spe_bkg_nospikes = None
    if not os.path.isfile(row["file_name"]):
        continue
    spe = Spectrum.from_local_file(row["file_name"])
    spe.plot(label="BACKGROUND_NOT_SUBTRACTED {}".format(row["sample"]), ax=ax)    

    new_spe = spe if is_in_skip(_config, key, filename=os.path.basename(row["background_file"])) or spe_bkg_nospikes is None else spe - spe_bkg_nospikes
    # new_spe.y[new_spe.y < 0] = 0
    # remove pedestal
    #new_spe.y = new_spe.y - np.min(new_spe.y)
    #new_spe = new_spe.recover_spikes()

    new_row["spectrum"] = new_spe
    new_spe.plot(label="Background_Substracted {}".format(row["sample"]), ax = ax,linestyle='--')
    new_row["background"] = "BACKGROUND_SUBTRACTED"
    new_rows.append(new_row)

if new_rows:  # Only concatenate if there are new rows to add
    new_df = pd.DataFrame(new_rows)  # Convert list of rows to DataFrame
    df = pd.concat([df, new_df], ignore_index=True)  # Append all at once

df.to_hdf(product["h5"], key='templates_read', mode='w')
df.to_excel(product["xlsx"], sheet_name='templates_read', index=False)    

