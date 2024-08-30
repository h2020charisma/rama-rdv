# + tags=["parameters"]
upstream = []
product = None
domain = None
hs_endpoint = None
keycloak_server_url = None
keycloak_client_id = None
keycloak_realm_name = None
hs_username = None
hs_password = None
nexus_file2import = None
# -


import logging
import os.path
import traceback


from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from keycloak import KeycloakOpenID

from pynanomapper.clients.authservice import TokenService
from pynanomapper.clients.service_charisma import H5Service

import h5py
import time

# Set up basic configuration for logging to a file
logger = logging.getLogger('nexus_upload')
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

class Container(containers.DeclarativeContainer):
    kcclient = providers.Singleton(
        KeycloakOpenID,
        server_url=keycloak_server_url,
        client_id=keycloak_client_id,
        realm_name=keycloak_realm_name,
        client_secret_key="secret"
    )

    tokenservice = providers.Factory(
        TokenService,
        kcclient = kcclient
    )

    h5service = providers.Factory(
        H5Service,
        tokenservice = tokenservice
    )


def recursive_copy(h5service,src_group, dst_group,level=0):
    
    # Copy attributes of the current group
    for attr_name, attr_value in src_group.attrs.items():
        dst_group.attrs[attr_name] = attr_value    
    for index,key in enumerate(src_group):
        if level==0:
            logger.info(key)
            _diff = h5service.tokenservice.token_time_left()
            logger.info("Token to expire {}".format(_diff))
            if _diff < 180:
                logger.info("Refresh token")
                h5service.tokenservice.refresh_token() 
                logger.info(h5service.tokenservice.token)
                _diff = h5service.tokenservice.token_time_left()
                logger.info("Token to expire {}".format(_diff))
 
        try:
            item = src_group[key]
            if isinstance(item, h5py.Group):
                # Create the group in the destination file
                new_group = dst_group.create_group(key)
                recursive_copy(h5service, item, new_group,level+1)
            elif isinstance(item, h5py.Dataset):
                if item.shape == ():  # Scalar dataset
                    # Copy the scalar value directly
                    dst_dataset = dst_group.create_dataset(key, data=item[()])
                else:
                    # Copy the dataset to the destination file
                    dst_dataset = dst_group.create_dataset(key, data=item[:])
                for attr_name, attr_value in item.attrs.items():
                    dst_dataset.attrs[attr_name] = attr_value  
                #dst_dataset.flush()     
        except Exception as err:
            print(traceback.format_exc())
        #if level == 0 and index>25:
        #    break              


@inject
def main(h5service = Provide[Container.h5service] ):
    
    h5service.login(hs_username,hs_password)
    try:
        print(nexus_file2import)
        with h5py.File(nexus_file2import,'r') as fin:
            _output = os.path.basename(nexus_file2import)
            with h5service.File("/{}/{}".format(domain,_output),mode="w") as fout:
                _diff = h5service.tokenservice.token_time_left()
                logger.info("Token to expire {}".format(_diff))
                h5service.tokenservice.refresh_token() 
                _diff = h5service.tokenservice.token_time_left()
                logger.info("Token to expire {}".format(_diff))
                recursive_copy(h5service,fin,fout,0)

 

    except Exception as err:
        print(traceback.format_exc())
    finally:
        h5service.logout()



print(__name__)
container = Container()
container.init_resources()
container.wire(modules=[__name__])
main()

file_handler.flush()
file_handler.close()