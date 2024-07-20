# + tags=["parameters"]
upstream = []
product = None
hs_username = None
hs_password = None
keycloak_server_url = None
keycloak_client_id = None
keycloak_realm_name = None
# -


from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from keycloak import KeycloakOpenID
from services.serviceclasses import TokenService
from services.service_h5 import H5Service
import hnswlib
import os.path
import pandas as pd
import pathlib
from scipy import signal
import pickle
import plotly.express as px

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

    exportservice = providers.Factory(
        H5Service,
        tokenservice = tokenservice
    )


@inject
def main(es = Provide[Container.exportservice]):
    es.login(hs_username,hs_password)
    try:
        metadata_path = os.path.join(product["data"],"metadata.h5")
        if os.path.exists(metadata_path):
            return pd.read_hdf(metadata_path,"metadata")
        else:
            results = []
            pathlib.Path(product["data"]).mkdir(parents=True, exist_ok=True)
            for investigation in  ["SANDBOX","Round_Robin_1","TEST","SILICON_STUDY"]:
                es.visit_domain("/{}/".format(investigation),
                    process_dataset=es.download2folder,kwargs= {"results" : results, "folder" : product["data"] })
            print(len(results))
            metadata = pd.DataFrame(results,columns=es.tags+["domain","tmpfile"])
            metadata.to_hdf(metadata_path,key="metadata")
            return metadata

    except Exception as err:
        print(err)
    finally:
        es.logout()



print(__name__)
container = Container()
container.init_resources()
container.wire(modules=[__name__])
results = main()
results.head()


from ramanchada2.spectrum import from_chada
import numpy as np
from services.datamodel import StudyRaman


def samplename(sample):
    tags = ['S0B','S0N','S0P','S1N']

    for tag in tags:
        if sample.startswith(tag):
            return tag
    if "Si111NoDope" == sample:
        return "S1N"
    if "Si100NoDope" == sample:
        return "S1N"
    if "Si100PhDope" == sample:
        return "S0P"
    if "Si100BoDope" == sample:
        return "S0B"

    return sample


def index_spe(domain,dim=1024,remove_baseline=True,window=16,cdf=[],pdf=[],cpdf=[],nufdt=[],sf=[]):
    spe = from_chada(domain)
    xlinspace = np.linspace(140,1024*3+140,num=dim)
    if window > 0:
        newspe = spe - spe.moving_minimum(window)
    else:
        newspe = spe
    x_uniform, y_cum = newspe.resample_NUDFT(x_range=(xlinspace[0],xlinspace[-1]), xnew_bins=dim, window=signal.windows.hann, cumulative=True)
    if len(y_cum) != dim:
        print(domain,len(y_cum))
    nufdt.append(y_cum)
    (spe,hist_dist,index) = StudyRaman.spectra2dist(spe,xcrop = [xlinspace[0],xlinspace[-1]],remove_baseline=remove_baseline,window=window)
    #spe.plot()
    v = hist_dist.cdf(xlinspace)
    normalized_vc = v / np.sqrt(np.sum(v**2))
    cdf.append(normalized_vc)
    v = hist_dist.sf(xlinspace)
    normalized_vc = v / np.sqrt(np.sum(v**2))
    sf.append(normalized_vc)
    v = hist_dist.pdf(xlinspace)
    normalized_vp = v / np.sqrt(np.sum(v**2))
    pdf.append(normalized_vp)
    #,hist_dist.pdf(xlinspace))
    cpdf.append(np.append(normalized_vc,normalized_vp))


def load_index(dims = [1024,2048,4096],distances = ["ip","l2","cosine"],windows=[0,16,128,256,512],methods=["cdf","pdf","nudft","cpdf","sf"]):
    missing = 0
    hnsw_index = {}
    runs = []
    qrel = None
    for dim in dims:
        for window in windows:
            for distance in distances:
                for val in methods:
                    _dim = dim*2 if val =="cpdf" else dim
                    p = hnswlib.Index(space = distance, dim = _dim)
                    key = "{}_{}_{}_{}".format(val,distance,dim,window)
                    file = os.path.join(product["data"],"{}.hnsw.index".format(key))
                    if os.path.exists(file):
                        p.load_index(file)
                        hnsw_index[key] = p
                    else:
                        print("missing {}".format(file))
                        missing = missing + 1
                    file = os.path.join(product["data"],"{}.json".format(key))
                    if os.path.exists(file):
                        run = Run.from_file(file)
                        run.name = key
                        runs.append(run)
    file = os.path.join(product["data"],"qrel.json")
    if os.path.exists(file):
        qrel = Qrels.from_file(file)

    return hnsw_index,missing,qrel,runs

def build_index(dims = [1024,2048,4096],distances = ["ip","l2","cosine"],windows=[0,16,128,256,512],methods=["cdf","pdf","nudft","sf","cpdf"]):
    hnsw_index = {}
    for dim in dims:
        for window in windows:
            cdf = []
            pdf = []
            cpdf = []
            nufdt = []
            sf = []
            remove_baseline = window > 0
            results.apply(lambda row: index_spe(row["tmpfile"],dim=dim,remove_baseline=remove_baseline,window=window,cdf=cdf,pdf=pdf,cpdf=cpdf,nufdt=nufdt,sf=sf),axis=1)
            print("building index {}_{}".format(dim,window))
            for distance in distances:
                for val in methods:
                    if  val=="cpdf":
                        p = hnswlib.Index(space = distance, dim = dim*2)
                    else:
                        p = hnswlib.Index(space = distance, dim = dim) # possible options are l2, cosine or ip
                    p.init_index(max_elements = len(cdf), ef_construction = 200, M = 16)
                    if val == "cdf":
                        p.add_items(cdf,results.index.values)
                    elif val == "sf":
                        p.add_items(sf,results.index.values)
                    elif val == "pdf":
                        p.add_items(pdf,results.index.values)
                    elif val == "cpdf":
                        p.add_items(cpdf,results.index.values)
                    elif val == "nudft":
                        try:
                            p.add_items(nufdt,results.index.values)
                        except Exception as err:
                            print(err,nufdt)
                    p.set_ef(50)
                    key = "{}_{}_{}_{}".format(val,distance,dim,window)
                    hnsw_index[key] = p
                    p.save_index(os.path.join(product["data"],"{}.hnsw.index".format(key)))


    return hnsw_index


from sklearn.metrics import accuracy_score,confusion_matrix,ConfusionMatrixDisplay

from ranx import Qrels, Run
from ranx import evaluate,compare

def get_qrels(results,tag="tag"):
    tags = results[tag].unique()
    qrel_df = pd.DataFrame(list(zip(tags,tags,np.repeat(1,len(tags)))),columns=["q_id","doc_id","score"])
    qrel_df["score"] = qrel_df["score"].astype("int")
    return  Qrels.from_df(
        df=qrel_df,  q_id_col="q_id",  doc_id_col="doc_id",  score_col="score")

def get_run(results,labels,_distances,tag="tag",name="run"):
    t = list()
    for query_index in np.arange(0,results.shape[0]):
        query=results.iloc[query_index][tag]
        t1 = zip(np.repeat(query,len(labels[query_index])),results.iloc[labels[query_index]][tag].values,1-_distances[query_index])
        t.extend(list(t1))

    run_df = pd.DataFrame(t,columns=["q_id","doc_id","score"])
    run_df["score"] = run_df["score"].astype("float")
    #display(run_df.head())
    run = Run.from_df(df=run_df,q_id_col="q_id", doc_id_col="doc_id",  score_col="score")
    run.name = name
    return run



def evaluate_index(dims = [1024,2048,4096],distances = ["ip","l2","cosine"],windows=[0,16,128,256,512],methods=["cdf","pdf","cpdf","nudft","sf"],knn=10,tag="tag"):
    print("evaluation\n")
    evaluation = []
    runs = []
    for dim in dims:
        for window in windows :
            cdf = []
            pdf = []
            cpdf = []
            nufdt = []
            sf = []
            remove_baseline = window > 0
            results.apply(lambda row: index_spe(row["tmpfile"],dim=dim,remove_baseline=remove_baseline,window=window,cdf=cdf,pdf=pdf,cpdf=cpdf,nufdt=nufdt,sf=sf),axis=1)

            for distance in distances:
                for val in methods:
                    key = "{}_{}_{}_{}".format(val,distance,dim,window)
                    if not key in hnsw_index:
                        print("evaluation: Missing {}".format(key))
                        continue
                    p = hnsw_index[key]
                    p.set_ef(50)
                    try:
                        if val=="cdf":
                            labels, _distances = p.knn_query(cdf, k = knn)
                        elif val=="pdf":
                            labels, _distances = p.knn_query(pdf, k = knn)
                        elif val=="sf":
                            labels, _distances = p.knn_query(sf, k = knn)
                        elif val=="nudft":
                            labels, _distances = p.knn_query(nufdt, k = knn)
                        else:
                            labels, _distances = p.knn_query(cpdf, k = knn)
                        run = get_run(results,labels,_distances,name=key)
                        run.save(os.path.join(product["data"],"{}.json".format(key)))
                        runs.append(run)
                        for i in np.arange(0,knn):
                            evaluation.append((val,window,distance,dim,i,accuracy_score(results[tag].values,results.iloc[labels[:,i]][tag].values),
                            accuracy_score(results.index.values,results.iloc[labels[:,i]].index.values)))
                    except Exception as err:
                        print(key,err)
    return evaluation,runs

def run_ranx(qrel,runs):
    print("ranx .. {}".format(len(runs)))
    report = compare(
        qrels=qrel,
        runs=runs,
        metrics=["hits","hit_rate","precision","recall","f1","r-precision","map","ndcg", "map","map@5", "mrr","bpref"],
        max_p=0.01  # P-value threshold
    )
    with open(os.path.join(product["data"],"report.pkl"),"wb") as file:
        pickle.dump(report,file)

    return report

results["tag"] =  results["sample"].apply(lambda x : samplename(x))

dims = [256,512,1024,2048]
windows = [16,32,64,128,256,512]
methods = ["cdf","pdf","cpdf","nudft","sf"]
#methods = ["sf"]

hnsw_index,missing,qrel,runs = load_index(dims = dims,distances = ["cosine"],windows=windows,methods=methods)
if missing>0:
    print("building index")
    hnsw_index = build_index(dims = dims,distances = ["cosine"],windows=windows,methods=methods)


evaluation_file= os.path.join(product["data"],"evaluation.csv")
report_file= os.path.join(product["data"],"report.pkl")
if os.path.exists(report_file):
    #ev = pd.read_csv(evaluation_file)
    with open(report_file,'rb') as f:
        report= pickle.load(f)
#elif len(runs) == len(hnsw_index):
#    report = run_ranx(qrel,runs)
else:
    tmp,runs = evaluate_index(dims = dims,distances = ["cosine"],windows=windows,methods=methods,knn=10)
    ev = pd.DataFrame(tmp,columns=["values","window","distance","dim","knn","accuracy_labels","accuracy_index"])
    ev.to_csv(evaluation_file,index=False)
    #https://amenra.github.io/ranx/metrics/
    qrel = get_qrels(results)
    qrel.save(os.path.join(product["data"],"qrel.json"))
    report = run_ranx(qrel,runs)

df = pd.DataFrame(report.results).T
df.reset_index(inplace=True)
df[['method', 'distance','number_of_bins','window']] = df['index'].str.split('_', 4, expand=True)
df.to_csv(os.path.join(product["data"],"report.csv"),index=True)
for metric in report.metrics:
    fig = px.bar(df, x="number_of_bins", y=metric, color="method",height=300, facet_row="distance",facet_col="window",title=metric,barmode="group")
    fig.show()



#tbd  10.1039/c1an15636e
#Acetaminophen
#Acetylsalicylic Acid 1
#Benzyl Alcohol 1
#Caffeine 1
#Calcium Phosphate Dibasic
#Diclofenac
#Diethylene Glycol
#Ethylene Glycol
#Glycerin
#Ibuprofen
#Lactose
#Magnesium Stearate
#Melamine
#Metformin
#Naproxen Sodium
#Pregelatinized Starch
#Propylene Glycol
#Sorbitol
#Sulfanilamide
#Tinidazole
