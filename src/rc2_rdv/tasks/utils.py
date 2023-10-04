import matplotlib.pyplot as plt

def baseline_spectra(spe, algo="als", **kwargs):
    if algo == "snip":
        del kwargs["window"]
        kwargs["niter"]  = 1000
        return spe.subtract_baseline_rc1_snip(**kwargs)
    elif algo == "als":
        del kwargs["window"]
        kwargs["niter"]  = 1000
        kwargs["p"]  = 0.1
        kwargs["lam"]  = 1e3
        #lam: float = 1e5, p: float = 0.001, niter: PositiveInt = 100,#
        return spe.subtract_baseline_rc1_als(**kwargs)
    else:  # movingmin
        window = kwargs.get("window", 10)
        return spe - spe.moving_minimum(window)

def plot_spectra(row, axes,column=0, reference=True,match_led= None,leds = None, cmap=None, norm = None, fc= None):
    _left = 100
    _color = cmap(norm(row["laser_power_percent"]))
    _baseline_when = row["baseline_removed"]
    try:
        sc=row["spectrum"]
        sc.plot(ax=axes[0][column],label="{}%".format(row["laser_power_percent"]),c=_color)
        sc = sc.trim_axes(method='x-axis', boundaries=(_left, 250))        
        sc.plot(ax=axes[1][column],label="{}%".format(row["laser_power_percent"]),c=_color)
    except:
        pass


    index=2
    step = 1
    for _tag in ["spectrum_normalized","spectrum_normalized_baseline","spectrum_corrected","spectrum_corrected_baseline","spectrum_harmonized"]:
        try:
            #if _baseline_when=="before LED correction":
            sc=row[_tag]

            _fc = ""
            boundaries =  [(_left, 250)]
            if (_tag == "spectrum_harmonized") :
                _fc = "FC {:.3e}".format(fc)
                boundaries = [(_left, 250),(_left, 1750)]
            if (_tag in ["spectrum_corrected_baseline"]) :
                boundaries = [(_left, 250),(_left, 1750)]      
            if (_tag in ["spectrum_corrected"]) & reference :
                boundaries = [(_left, 250),(_left, 1750)]                             
            for b in boundaries:
                sc1 = sc.trim_axes(method='x-axis', boundaries=b)
                sc1.plot(ax=axes[index][column],label="{}%".format( row["laser_power_percent"]),c=_color)
                axes[index][column].set_title("{}. {} {}".format(step,_tag.replace("_"," "),_fc))
                index =index+1  
            step = step+ 1          
        except Exception as err:
            print(err)
            pass    
       

    try:
        device=row["device"]
       
        led = match_led.loc[device]["led_spectra"]
        sc = leds.loc[led]["spectrum"]
        sc.plot(ax=axes[0][column],label='_nolegend_',c="gray")
        sc = sc.trim_axes(method='x-axis', boundaries=(_left, 250))        
        sc.plot(ax=axes[1][column],label='_nolegend_',c="gray")
        sc.plot(ax=axes[2][column],label='_nolegend_',c="gray")
    except Exception as err:
        print(err)
        pass   


    axes[0][column].set_title("0. {} {} {}".format(row["device"],row["probe"],"(reference)" if reference else ""))
    axes[1][column].set_title("0. (cropped)")

    #plt.legend(loc='upper left', bbox_to_anchor=(1, 1))