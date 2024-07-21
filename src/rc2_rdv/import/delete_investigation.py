# + tags=["parameters"]
upstream = []
product = None
domain_to_delete = None
hs_admin_username = None
hs_admin_password = None
keycloak_server_url = None
keycloak_client_id = None
keycloak_realm_name = None
# -

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from keycloak import KeycloakOpenID
import h5pyd

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

def delete_folder(domain):
    print(domain)
    try:
        # Open the folder
        with h5pyd.Folder(domain, 'r') as f:
            n = f._getSubdomains()
            if n>0:
                for item in f._subdomains:
                    print(item)
                #item_path = f"{domain}/{item}"
                #print(item_path)
                #if isinstance(f[item], h5pyd.Group):
                #    delete_folder(item_path)  # Recursive call for subfolders
                #else:
                #    del f[item]  # Delete files
        # Close the folder before deletion
        #print("# Delete the folder itself")
        #f = h5pyd.Folder(domain, 'w')
        #f.delete()
        #print(f"Folder {domain} has been deleted.")
    except Exception as e:
        print(f"Error deleting folder {domain}: {e}")

@inject
def main(ts = Provide[Container.h5service]):
    ts.login(hs_admin_username,hs_admin_password)
    print("logged in")
    try:
        #_folder = ts.check_domain(investigation_to_delete)
        #delete_folder(investigation_to_delete)
        print(domain_to_delete)
        _folder = ts.Folder(domain_to_delete)
        dparent = _folder.parent
        if dparent == '//':
            dparent = '/'
        with ts.Folder(dparent, mode='a') as f:
            del f[domain_to_delete.strip('/')]
        
    except Exception as err:
        print(err)
    finally:
        ts.logout()



print(__name__)
container = Container()
container.init_resources()
container.wire(modules=[__name__])
main()
