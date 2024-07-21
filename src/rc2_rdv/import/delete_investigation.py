# + tags=["parameters"]
upstream = []
product = None
domain_to_delete = None
hs_admin_username = None
hs_admin_password = None
keycloak_server_url = None
keycloak_client_id = None
keycloak_realm_name = None
remove_files=None
# -

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from keycloak import KeycloakOpenID
import traceback 
import os.path

from pynanomapper.clients.authservice import TokenService
from pynanomapper.clients.service_charisma import H5Service

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

def delete_folder(h5service,domain,remove_files=False):
    try:
        with h5service.Folder(domain, 'a') as _folder:
            dparent = _folder.parent
            #print(_folder)
            n = _folder._getSubdomains()
            if n>0:
                for item in _folder._subdomains:
                    if item["class"] == "folder":
                        delete_folder(h5service,"{}/".format(item["name"]))
                    elif item["class"] == "domain":
                        if remove_files:
                            base_name = os.path.basename(item["name"])    
                            del _folder[base_name]
        
        try:
            if dparent == '//':
                dparent = '/'
            with h5service.Folder(dparent, mode='a') as _folder:
                _basename = os.path.basename(domain.strip('/'))
                _folder.delete_item(_basename)
        except Exception as err:
            print(f"Error deleting (nonempty) folder {dparent}[{_basename}]: {err}. remove_files is {remove_files}")

    except Exception as e:
        traceback.print_exc()
        print(f"Error deleting folder {domain}: {e}")

@inject
def main(ts = Provide[Container.h5service]):
    ts.login(hs_admin_username,hs_admin_password)
    print("logged in")
    try:
        delete_folder(ts,domain_to_delete,remove_files)
       
    except Exception as err:
        print(err)
    finally:
        ts.logout()



print(__name__)
container = Container()
container.init_resources()
container.wire(modules=[__name__])
main()
