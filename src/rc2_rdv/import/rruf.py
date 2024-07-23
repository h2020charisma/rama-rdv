# + tags=["parameters"]
upstream = []
product = None
rruf_folder = None
keycloak_server_url = None
keycloak_client_id = None
keycloak_realm_name = None
hs_username = None
hs_password = None
# -

import os
#import ramanchada2 as rc2
from ramanchada.classes import RamanChada
import glob
import numpy as np

def write_chada(h5service,file_path, dset_name, x, y, metadata, mode='a', x_label = 'Raman shift [1/cm]', y_label = 'raw counts [1]'):
    # Create HDF5 file
    with h5service.File(file_path, mode) as f:
        # Store Raman dataset + label
        xy = f.create_dataset(dset_name, data=np.vstack((x, y)))
        xy.dims[0].label = x_label
        xy.dims[1].label = y_label
        # Store metadata
        for key in metadata:
            if key in ["DIMENSION_LABELS"]:
                continue
            try:
                xy.attrs.create(key.replace("##",""),metadata[key])
            except Exception as err:
                print(key)
                traceback.print_exc()
        _group_study = f.require_group("annotation_study")
        _group_sample = f.require_group("annotation_sample")
      
        for p in metadata:
            #print(p)
            if p in ["wavelength","instrument","provider","investigation","scan_type","data_type","file_id"]:
                try:
                    _group_study.attrs.create(p.replace("##",""), metadata[p])
                except Exception as err:
                    print("study",p,err)
            if p in ["sample"
                     ,"RRUF_id","orientation","orientation_desc","scan_type",
                     "##DESCRIPTION","##IDEAL CHEMISTRY","##LOCALITY","##MEASURED CHEMISTRY","##NAMES",
                     "##OWNER","##RRUFFID","##SOURCE","##STATUS","##URL"
                     ]:
                try:
                    _group_sample.attrs.create(p.replace("##",""),metadata[p])
                except Exception as err:
                    print("sample",p,err)   

import matplotlib.pyplot as plt
def write_chada_multi(h5service,file_path, cha_file, metadata, mode='a', x_label = 'Raman shift [1/cm]', y_label = 'raw counts [1]',plot=False):
    # Create HDF5 file
    with h5service.File(file_path, mode) as f:
        # Store Raman dataset + label
        if plot:
            plt.figure()
        for dset_name in ["/raw"]:
            R = RamanChada(cha_file,dset_name)
            xy = f.create_dataset(dset_name, data=np.vstack((R.x, R.y)))
            xy.dims[0].label = x_label
            xy.dims[1].label = y_label
            if plot:
                plt.plot(R.x,R.y,label="raw")
            if dset_name=="/raw":
                # Store metadata
                for key in metadata:
                    if key in ["DIMENSION_LABELS"]:
                        continue
                    try:
                        xy.attrs.create(key.replace("##",""),metadata[key])
                    except Exception as err:
                        print(key)
                        traceback.print_exc()
            #R.normalize('minmax')
            #R.commit("normalized_minmax")
            R.x_crop(100, max(R.x))
            R.fit_baseline()
            R.remove_baseline()
            #R.smooth()
            #R.normalize()
            if plot:            
                plt.figure()
                plt.plot(R.x,R.y,label="baseline_removed")
            xy = f.create_dataset("/baseline_removed", data=np.vstack((R.x, R.y)))
            xy.dims[0].label = x_label
            xy.dims[1].label = y_label            
            #R.commit("baseline_removed")                           
        _group_study = f.require_group("annotation_study")
        _group_sample = f.require_group("annotation_sample")
      
        for p in metadata:
            if p in ["wavelength","instrument","provider","investigation","scan_type","data_type","file_id",
                     "orientation","orientation_desc",
                     "##DESCRIPTION","##IDEAL CHEMISTRY","##LOCALITY","##MEASURED CHEMISTRY","##NAMES",
                     "##OWNER","##RRUFFID","##SOURCE","##STATUS","##URL"]:
                try:
                    _group_study.attrs.create(p.replace("##",""), metadata[p])
                except Exception as err:
                    print("study",p,err)
            if p in ["sample","sample_id"]:
                try:
                    _group_sample.attrs.create(p.replace("##",""),metadata[p])
                except Exception as err:
                    print("sample",p,err) 

# Function to parse filename
def parse_filename(filename,meta):
    name, ext = os.path.splitext(filename)
    components = name.split('__')
    _tmp =  {
        'sample': components[0],
        'RRUF_id': components[1],
        'scan_type': components[2],
        'wavelength': components[3],
        'sample_orientation': components[4],
        'sample_orientation_desc': components[5],
        'data_type': components[6],
        'file_id': components[7],
        'investigation' : "RRUF",
        "instrument" : "RRUF",
        "provider" : components[1]
    }
    for p in meta:
        _tmp[p] = meta[p]
    return _tmp                                        

import traceback
def iterate_rruf(h5service,rruf_folder,pattern = "P*.txt",maxrecords = 10000):
    full_pattern = os.path.join(rruf_folder, pattern)
    files = glob.glob(full_pattern)
    n = 0
    for file_path in files:
        if os.path.isfile(file_path):
            filename = os.path.basename(file_path)
            try:
                print(f"File: {file_path}")
                R = RamanChada(file_path)

                #R.plot()             
                meta = parse_filename(filename,R.meta)
                cha_file = file_path.replace(".txt",".cha")
                
                path = "/RRUF/{}".format(filename.replace(".txt",".cha"))
                
                #R.plot()
               
                #write_chada(h5service,path, "/raw", R.x, R.y, meta, mode='w', x_label = 'Raman shift [1/cm]', y_label = 'raw counts [1]')
                write_chada_multi(h5service,path,  cha_file, meta, mode='w', x_label = 'Raman shift [1/cm]', y_label = 'raw counts [1]')
                os.remove(cha_file)
            except Exception as err:
                traceback.print_exc()
            n = n+1
        if n>maxrecords:
            break

import logging
import os.path


from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from keycloak import KeycloakOpenID

from pynanomapper.clients.authservice import TokenService
from pynanomapper.clients.h5service import H5BasicService

import traceback
import pandas as pd

from pynanomapper.clients.authservice import TokenService,  get_kcclient
from pynanomapper.clients.h5service import H5BasicService

kcclient = get_kcclient (keycloak_server_url,keycloak_client_id,keycloak_realm_name,"secret")

tokenservice = TokenService(kcclient)
h5service = H5BasicService(tokenservice)

h5service.login(hs_username,hs_password)
try:
    iterate_rruf(h5service)
    #pass
except Exception as err:
    print(err)
finally:
    h5service.logout()
