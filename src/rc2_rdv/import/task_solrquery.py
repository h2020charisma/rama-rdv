# + tags=["parameters"]
upstream = []
product = None
keycloak_server_url = None
keycloak_client_id = None
keycloak_realm_name = None
hs_username = None
hs_password = None
query_file = None
# -



from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from keycloak import KeycloakOpenID
from pynanomapper.clients.authservice import TokenService, QueryService

import numpy as np
import pandas as pd
import requests
from pynanomapper.clients.datamodel_simple import StudyRaman, Substance
import ramanchada2 as rc2
from pathlib import Path
import os.path
import matplotlib.pyplot as plt


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

    queryservice = providers.Factory(
        QueryService,
        tokenservice = tokenservice
    )

import glob
from ramanchada2 import spectrum

def query(qs,file,topk=5):
    try:
        spe = spectrum.from_local_file(file)
    except Exception as err:
        raise err
        #spectrum = rc2.spectrum.from_local_file(query_file)

    cdf,pdf = StudyRaman.xy2embedding(spe.x,spe.y)
        #url = "https://solr-kc.ideaconsult.net/solr/charisma/select?debugQuery=true"
    url = "https://solr-kc.ideaconsult.net/solr/charisma/select?rows=10"

    query = "!knn f=spectrum_c1024 topK={}".format(topk)
    data= {"query": "{"+query+"}[" + ','.join(map(str, cdf)) + "]", "filter" : ["type_s:study"], "fields" : "score,name_s,textValue_s,spectrum_p1024"}
        #data= {"query": "{!knn f=spectrum_p1024 topK=10}[" + ','.join(map(str, pdf)) + "]", "filter" : ["type_s:study"], "fields" : "score,name_s,textValue_s,spectrum_p1024"}

    rs =  requests.post(url, json = data, headers=qs.tokenservice.getHeaders())
    return rs,spe

def plot_results(rs,spe_query,elapsed_time):
    fig, [ax_query, ax] = plt.subplots(nrows=1, ncols=2,figsize=(24,6))
    #plt.legend(loc='upper right')
    #print("Searching for: ",spe_query.meta["query"])
    spe_query.plot(ax=ax_query,label="query")
    results = rs.json()["response"]
    #print(results["numFound"])
    docs = results["docs"]
    x = StudyRaman.x4search()
    print(len(x),x)
    i = len(docs)
    top = os.path.basename(docs[0]["textValue_s"])
    for r in reversed(docs):
        #print("{}.\t{}".format(i,r["textValue_s"]))
        y = np.array(r["spectrum_p1024"])
        print(len(y),y)
        spe = rc2.spectrum.Spectrum(x=x,y=y,metadata={})
        spe.plot(label= "{}.{}".format(i,r["textValue_s"]),ax=ax,fmt='r-' if i==1 else '.')
        #plt.plot(x,y,label=os.path.basename(r["textValue_s"]))
        i = i-1
    #plt.title("Searching for {}".format(spe_query.meta["query"]))
    ax_query.title.set_text("Searching for {}".format(spe_query.meta["query"]))
    ax.title.set_text("{} Found in {:.3} sec".format(top,elapsed_time))


from timeit import default_timer as timer
from matplotlib.pyplot import figure

@inject
def main(qs = Provide[Container.queryservice]):


    #plt.rcParams["figure.figsize"] = (20,6)
    try:
        qs.login(hs_username,hs_password)
        if os.path.isdir(query_file):
            query_files = glob.glob('{}/*.*'.format(query_file))
        else:
            query_files = [query_file]
        for filename in query_files:
            if os.path.basename(filename).lower().startswith("dark"):
                continue
            try:
                start = timer()
                rs,R = query(qs,filename,topk=2)
                end = timer()
                if rs.status_code == 200:
                    plot_results(rs,R,end-start)
            except Exception as err:
                #print(err)
                pass
    except Exception as err:
        print(err)
        raise(err)
    finally:
        qs.logout()



print(__name__)
container = Container()
container.init_resources()
container.wire(modules=[__name__])


try:
    print(query_file)
    main()
except Exception as err:
    print(err)
