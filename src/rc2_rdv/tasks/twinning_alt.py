# + tags=["parameters"]
upstream = ["twinning_intensity_normalization"]
product = None
probe: None
spectrum_to_correct: None
spectrum_corrected_column: None
baseline_after_ledcorrection: None

# -

# Alternative twinning workflow
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from pandas.plotting import scatter_matrix
from sklearn.ensemble import RandomForestRegressor

devices_h5file= upstream["twinning_intensity_normalization"]["data"]
print(devices_h5file)
devices = pd.read_hdf(devices_h5file, "devices")
devices.head()

reference_condition = (devices["reference"]) & (devices["probe"] == probe)
twinned_condition = (~devices["reference"]) & (devices["probe"] == probe)
A = devices.loc[reference_condition]
B = devices.loc[twinned_condition]

spectra2process = "{}_baseline".format(spectrum_corrected_column)  if baseline_after_ledcorrection else spectrum_corrected_column


# Create empty lists to store the data
def train_model(M,plot=True):
    x_values = []
    y_values = []
    laser_power_values = []
    for index, row in M.iterrows():
        spe = row[spectra2process]
        try:
            spe = spe.trim_axes(method='x-axis', boundaries=(144-50, 144+50))
            x_values.extend(spe.x)
            y_values.extend(spe.y)
            laser_power_values.extend([row["laser_power"]] * len(spe.x))
        except Exception as err:
            print(err)
    vars_array = np.array([x_values, laser_power_values]).T 
    target_array = np.array(y_values) 
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(vars_array, target_array)
    predicted_target = model.predict(vars_array)
    if plot:
        # Plot the predicted values and the regression line
        plt.figure(figsize=(4,4))
        plt.scatter(target_array, predicted_target, alpha=0.5)
        plt.plot([min(target_array), max(target_array)], [min(target_array), max(target_array)], color='red', linestyle='--', lw=2)
        plt.xlabel("Actual ")
        plt.ylabel("Predicted ")
        plt.title("Actual vs. Predicted ")
        plt.grid(True)
        plt.show()

        # Create a DataFrame with the arrays
        data = {
            'x': vars_array[:, 0],
            'laser_power': vars_array[:, 1],
            'y': target_array,
            'y_predicted': predicted_target,
        }
        df = pd.DataFrame(data)
        # Create a Scatter Plot Matrix (SPLOM) with the specified columns
        columns_to_plot = ['x', 'laser_power', 'y', 'y_predicted']
        scatter_matrix(df[columns_to_plot], alpha=0.8, figsize=(10, 10), diagonal='hist', c=vars_array[:, 1])
        # Show the plot
        plt.show()        

    # Model statistics
    mse = mean_squared_error(target_array, predicted_target)
    r_squared = r2_score(target_array, predicted_target)
    return (model,mse,r_squared)

model_A, mse_A,r_squared_A = train_model(A)
#print("Model Coefficients:", coefficients)
#print("Model Intercept:", intercept)
print("Mean Squared Error (MSE) (A):", mse_A)
print("R-squared (A):", r_squared_A)

model_B, mse_B,r_squared_B = train_model(B)
#print("Model Coefficients:", coefficients)
#print("Model Intercept:", intercept)
print("Mean Squared Error (MSE) (B):", mse_B)
print("R-squared (B):", r_squared_B)

def correct_by_model(B,model_A,model_B,plot=True):
    for index, row in B.iterrows():
        spe = row[spectra2process]
        laser_power = row["laser_power"]
        spe = spe.trim_axes(method='x-axis', boundaries=(144-50, 144+50))
        ax = spe.plot(label="{}".format(row["laser_power_percent"]))
        data_2d = np.column_stack((spe.x, np.full_like(spe.x, laser_power)))
        predicted_B = model_B.predict(data_2d)
        predicted_A = model_A.predict(data_2d)
        ax.plot(spe.x,predicted_B,'.')
        ax.plot(spe.x,predicted_A,'+')
        #ax.plot(spe.x,spe.y+(predicted_A-predicted_B))
        ax.twinx().plot(spe.x,np.divide(predicted_A,predicted_B,out=np.zeros_like(predicted_A), where=predicted_B != 0),c='r')
plt.legend()
correct_by_model(B,model_A,model_B)        