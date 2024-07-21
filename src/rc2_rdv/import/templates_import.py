# + tags=["parameters"]
upstream = ["createinvestigation","templates_read"]
product = None
ramandb_api = None
dry_run = None
keycloak_server_url = None
keycloak_client_id = None
keycloak_realm_name = None
hs_username = None
hs_password = None
config_root= None
hsds_investigation = None
# -

import logging
import os.path


from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from keycloak import KeycloakOpenID

from pynanomapper.clients.authservice import TokenService
from pynanomapper.clients.service_import import ImportService

import traceback
import pandas as pd


# Set up basic configuration for logging to a file
logger = logging.getLogger('templates_import')
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

    importservice = providers.Factory(
        ImportService,
        tokenservice = tokenservice,
        ramandb_api = ramandb_api,
        hsds_investigation = hsds_investigation,
        dry_run = dry_run
    )

def import_template(config_root,metadata,importservice):
    for index, row in metadata.iterrows():
        try:
            filename = os.path.join(config_root,row["filename"])
           
            hsds_instrument="{}_{}".format(row["instrument_make"],row["instrument_model"])
            with open(filename) as _f:
                
                logger.debug(filename,row["provider"],hsds_instrument,row["wavelength"],row["optical_path"],row["sample"],row["laser_power_percent"])
                if dry_run:
                    logger.info(filename)
                else:
                    logger.info(filename)
                    response = importservice.submit2hsds(_f,
                        hsds_provider= row["provider"],
                        hsds_instrument=hsds_instrument,
                        hsds_wavelength=row["wavelength"],
                        optical_path=row["optical_path"],
                        sample=row["sample"],
                        laser_power=row["laser_power_percent"])
                    logger.debug(filename,response)
        except Exception as err:        
            logger.error(filename,err)

@inject
def main(importservice = Provide[Container.importservice] ):
    importservice.login(hs_username,hs_password)
    try:
        metadata = pd.read_hdf(upstream["templates_read"]["h5"], key="templates_read")
        import_template(config_root,metadata, importservice)

    except Exception as err:
        print(err)
    finally:
        importservice.logout()



print(__name__)
container = Container()
container.init_resources()
container.wire(modules=[__name__])
main()
