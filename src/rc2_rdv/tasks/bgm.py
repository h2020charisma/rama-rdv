from operator import index
import h5pyd
import matplotlib.pyplot as plt
import numpy as np
from sklearn.mixture import BayesianGaussianMixture
import pandas as pd
import scipy.stats
from ramanchada2.spectrum import from_chada
import math, time
import scipy.stats as stats
import os.path
from pathlib import Path


def spectra2dist(spe,xcrop = None,remove_baseline=True,window=16):

    # else assume it's a Spectrum object for now
    #baseline removal is important
    #if remove_baseline:
    #    spe = spe - spe.moving_minimum(16)

    #no need to normalize, we'll generate probability distribution, it will self normalize!
    counts = spe.y # a spectrum is essentially a histogram :)
    x = spe.x
    #crop
    xcrop_right = max(x) if xcrop is None else xcrop[1]
    xcrop_left = 100 if xcrop is None else xcrop[0]
    index = np.where((x>=xcrop_left) & (x<=xcrop_right))
    index = index[0]
    #x = x[index]
    x = x[index]
    counts = counts[index]
    if remove_baseline:
        spe.x = x
        spe.y = counts
        spe = spe - spe.moving_minimum(window)
        x = spe.x
        counts = spe.y

    #y = counts[0:len(counts)-1]
    y = counts
    bin_width = (x[1]-x[0])/2
    x_bins = list(map(lambda a: a-bin_width, x))
    x_bins = np.append(x_bins,x[len(x)-1]+bin_width)
    #print(len(x),len(x_bins),len(y))
    #crop until wavenumber 100
    #and now derive a probability distribution, from which we are going to sample
    hist_dist = scipy.stats.rv_histogram((y,x_bins))
    return (spe,hist_dist,index)

def fit(hist_dist,n_samples,n_components=50,max_iter=10000):
    xsamples = hist_dist.rvs(size=math.floor(n_samples))
    X = list(map(lambda x: [x], xsamples))
    bgm = BayesianGaussianMixture(n_components=n_components, random_state=42,max_iter=10000).fit(X)
    return bgm,xsamples

def peaks(bgm):
    return pd.DataFrame(zip(map(lambda x: x[0],bgm.means_),map(lambda x: math.sqrt(x[0][0]),bgm.covariances_),bgm.weights_),
    columns=("mean","sigma","weight")).sort_values(by=['weight'],ascending=False)

def plotdist(bgm,spe,index_cropped,hist_dist,threshold=0.00001):
    fig, (ax1, ax2) = plt.subplots(1,2, figsize=(12,2))
    ax1.plot(spe.x[index_cropped],hist_dist.pdf(spe.x[index_cropped]),'-')
    for e in zip(bgm.means_,bgm.weights_,bgm.covariances_):
        weight = e[1]
        if weight>=threshold:
            mu = e[0][0]
            sigma = math.sqrt(e[2])
            gm = stats.norm(mu, sigma)

            ax1.scatter(e[0][0],weight*gm.pdf(e[0][0]),label=e[1])
            ax2.plot(spe.x[index_cropped], weight*gm.pdf(spe.x[index_cropped]))
    return (ax1,ax2)

def bgm_findpeaks(spe, xcrop = None, n_samples=None,n_components=20,max_iter=10000,sampling_coeff = None,plot=False,remove_baseline=True):
    spe, hist_dist,index_cropped = spectra2dist(spe,xcrop=xcrop,remove_baseline=remove_baseline)
    #spe.plot()
    # kind of guessing
    if n_samples is None:
        #the actual resolution

        n_samples = len(spe.x[index_cropped])
        n_samples = n_samples if sampling_coeff is None else math.ceil(n_samples * sampling_coeff)
        #print(len(spe.x[index_cropped]),min(spe.x[index_cropped]),max(spe.x[index_cropped]),n_samples)
        #n_samples = (max(spe.x[index_cropped]) - min(spe.x[index_cropped])) *4*6
        # ~5-12 points per Gaussian recommended , assuming .25 wavenumber resolution

    st = time.time()
    bgm,xsamples = fit(hist_dist,n_samples=n_samples,n_components=n_components,max_iter=max_iter)
    et = time.time() - st

    df = peaks(bgm)
    df["n_samples"] = n_samples
    df["min"] = min(spe.x)
    df["max"] = max(spe.x)
    df["time_s"] = et
    df["converged"] = bgm.converged_

    n_clusters = (np.round(bgm.weights_, 2) > 0).sum()
    if plot:
        plotdist(bgm,spe,index_cropped,hist_dist,df.iloc[n_clusters-1]["weight"])

    df["n_clusters"] = n_clusters

    return df,bgm,n_clusters,hist_dist,index_cropped,xsamples
