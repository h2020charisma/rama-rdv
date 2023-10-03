
def plot_spectra(row, axes,column=0, reference=True,match_led= None,leds = None, cmap=None, norm = None):
    _left = 65
    _color = cmap(norm(row["laser_power_percent"]))
    try:
        sc=row["spectrum"]
        sc.plot(ax=axes[0][column],label="{}%".format(row["laser_power_percent"]),c=_color)
        sc = sc.trim_axes(method='x-axis', boundaries=(_left, 300))        
        sc.plot(ax=axes[1][column],label="{}%".format(row["laser_power_percent"]),c=_color)
    except:
        pass

    try:
        sc=row["spectrum_normalized"]
        sc = sc.trim_axes(method='x-axis', boundaries=(_left, 300))
        sc.plot(ax=axes[2][column],label="{}%".format(row["laser_power_percent"]),c=_color)
    except:
        pass
    try:
        sc=row["spectrum_baseline"]
        sc = sc.trim_axes(method='x-axis', boundaries=(_left, 300))
        sc.plot(ax=axes[3][column],label="{}%".format(row["laser_power_percent"]),c=_color)
    except:
        pass    
    try:
        sc =row["spectrum_corrected"]
        sc = sc.trim_axes(method='x-axis', boundaries=(_left, 300))
        sc.plot(ax=axes[4][column],label="{}%".format(row["laser_power_percent"]),c=_color)
    except:
        pass  
    try:
        sc=row["spectrum_corrected_baseline"]
        sc = sc.trim_axes(method='x-axis', boundaries=(_left, 300))
        sc.plot(ax=axes[5][column],label="{}%".format(row["laser_power_percent"]),c=_color)
    except:
        pass     
    try:
        sc=row["spectrum_corrected_baseline"]
        if reference:
            sc = sc.trim_axes(method='x-axis', boundaries=(_left, 1500))
            sc.plot(ax=axes[7][column],label="{}%".format(row["laser_power_percent"]),c=_color)
    except:
        pass        

    sc=row["spectrum_harmonized"]
    try:
       sc = sc.trim_axes(method='x-axis', boundaries=(_left, 1500))
       sc.plot(ax=axes[7][column],label="{}%".format(row["laser_power_percent"]),c=_color)
    except:
        pass  

    try:
        sc = sc.trim_axes(method='x-axis', boundaries=(_left, 300))
        sc.plot(ax=axes[6][column],label="{}%".format(row["laser_power_percent"]),c=_color)
    except:
        pass  

    try:
        device=row["device"]
       
        led = match_led.loc[device]["led_spectra"]
        sc = leds.loc[led]["spectrum"]
        sc.plot(ax=axes[0][column],label='_nolegend_',c="gray")
        sc = sc.trim_axes(method='x-axis', boundaries=(_left, 300))        
        sc.plot(ax=axes[1][column],label='_nolegend_',c="gray")
        sc.plot(ax=axes[2][column],label='_nolegend_',c="gray")
    except Exception as err:
        print(err)
        pass   


    axes[0][column].set_title("{} {} {}".format(row["device"],row["probe"],"(reference)" if reference else ""))

    norm = "original" if reference else "normalized"
    axes[2][column].set_title(norm)
    axes[3][column].set_title("{} + baseline removed".format(norm))
    axes[4][column].set_title("{} + LED corrected".format(norm))
    axes[5][column].set_title("{} + LED corrected + baseline".format(norm))
    try:
        if reference:
            axes[6][column].set_title("{} + LED corrected + baseline (cropped)".format(norm))
        else:
            axes[6][column].set_title("harmonized (cropped)")
    except:
        pass
    try:
        if reference:
            axes[7][column].set_title("{} + LED corrected + baseline".format(norm))
        else:
            axes[7][column].set_title("harmonized")
    except:
        pass    
