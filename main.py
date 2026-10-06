import math
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# STEP 1
# Note to self: ctrl + / to mass comment or uncomment code cause I keep forgetting this lmao

# Setup options for the table
pd.options.display.min_rows = 25
pd.options.display.max_rows = 999
pd.options.display.max_columns = 999
pd.options.display.width = 300
# Print and foreward fill the paraquet
table = pq.read_pandas('software-data.parquet')
rawData = table.to_pandas()
filledTable = rawData.ffill()
# print(filledTable)
# print("NaN counts per column:")  # Check if the forward fill was functioning correctly and if any NaNs remain
# print(filledTable.isna().sum()) 


# STEP 2 & 3

# Defining the parameters (?) idk what to call them so it's parameters
wheelRad = 0.2
gearRatio = (12/41)
filledTable["Velocity"] = filledTable["SME_TRQSPD_Speed"] * wheelRad * (2 * math.pi / 60) * gearRatio # Makes a new row in the table that is the velocity
filledTable["VelocitySmooth"] = filledTable["Velocity"].rolling(200).mean() # Smooths the velocity function with Pandas rolling average
filledTable["Acceleration"] = filledTable["VelocitySmooth"].diff() / filledTable["Time"].diff() # Calculates acclration by dividing the smoothed velocity over time.
time = filledTable["Time"] # Yeah as many iterations as I've gone through of this shit, its still time

# Graphing Section

# graph, axes = plt.subplots(2, 2, sharex=True) # Create figure in matplotlib with 4 seperate graphs in a 2x2 grid with a shared X axis.

# # Grahp 1: Velocity
# axes[0,0].plot(time, filledTable["Velocity"])
# axes[0,0].set_ylabel("Car Velocity (m/s)")
# axes[0,0].set_xlabel("Time (seconds)")

# # Graph 2: Acceleration
# axes[0,1].plot(time, filledTable["Acceleration"])
# axes[0,1].set_ylabel("Car Acceletation (m/s/s)")
# axes[0,1].set_xlabel("Time (seconds)")

# # Graph 3: Throttle Travel
# axes[1,0].plot(time, filledTable["ETC_STATUS_PEDAL_TRAVEL"])
# axes[1,0].set_ylabel("Throttle Pedal Travel (%)")
# axes[1,0].set_xlabel("Time (seconds)")

# # Graph 4: Brake Voltage
# axes[1,1].plot(time, filledTable["ETC_STATUS_BRAKE_SENSE_VOLTAGE"] - 350)
# axes[1,1].set_ylabel("Brake Voltage (V)")
# axes[1,1].set_xlabel("Time (seconds)")

# graph.suptitle("Car Velocity and Driver Input")
# plt.tight_layout()
# plt.show()

# for index, mRPM in enumerate(filledTable["SME_TRQSPD_Speed"]): # Old printed version for testing
#    time = filledTable["Time"][index]
#    # wRPM = mRPM * 12 / 41     # Only here for testing lol
#    vel = mRPM * wheelRad * (2 * math.pi / 60) * gearRatio
#    print(time, vel)

# Defining parameters for each state of the car
driving = filledTable["Velocity"] > 0.1
accelerating = filledTable["ETC_STATUS_PEDAL_TRAVEL"] > 1
braking = filledTable["ETC_STATUS_BRAKE_SENSE_VOLTAGE"] - 350 > 10 & driving
coasting = ~accelerating & ~braking & driving

# STEP 4

# Creating the plotted map of the track from GPS Data
# plt.figure()
# plt.scatter(filledTable["VDM_GPS_Longitude"], filledTable["VDM_GPS_Latitude"], c=time, s=1) # Scatterplot of Longitude on X, Latitude on Y (yeah I got that wrong first), with the color change representing time
# plt.colorbar(label="Time (s)")
# plt.gca().set_aspect('equal') # Leaves the track shape undistorted
# plt.xlabel("Longitude")
# plt.ylabel("Latitude")
# plt.title("Map of the Car's Position Relative to Time")
# plt.show()

# lap Times
throttle = filledTable["ETC_STATUS_PEDAL_TRAVEL"]
launchLevel = 30 # Threshold to count a launch

# print("Start Times:")
lapStart = (throttle.shift(1) < launchLevel) & (throttle >= launchLevel) # Defines the launch as the moment the throttle goes from below 30 to above 30
# print(filledTable[lapStart]["Time"]) # Print the time of each launch (in seconds)

# print("End Times:")
lapEnd = (filledTable["Velocity"].shift(1) > 0.1) & (filledTable["Velocity"] < 0.1) # Defines the lap end as the moment the velocity goes from more than to less than 0.1 m/s
# print(filledTable[lapEnd]["Time"]) # Print the time of each end (in seconds)

# STEP 5

laps = [(22.105, 51.024), (51.024, 77.349), (97.526, 132.969)] # Start and end times of each lap
filledTable["deltaT"] = filledTable["Time"].diff() # Delta time is difference between previous and curent time (I gotta keep labeling how pandas stuff works otherwise I'm forgetting instantly)

for lapNumber, (start, end) in enumerate(laps, start=1): # For eveyr lap number, starting with lap 1 instead of 0
	inLap = (filledTable["Time"] >= start) & (filledTable["Time"] < end) # In lap is when time is between start and end. shocker
	lapRows = filledTable[inLap]
	# I feel like these are all pretty self explanitory
	maxSpeed = lapRows["Velocity"].max()
	maxAccel = lapRows["Acceleration"].max()
	timeAccel = filledTable[inLap & accelerating]["deltaT"].sum() # Sum of the total time that acelerating happens in laps
	timeCoast = filledTable[inLap & coasting]["deltaT"].sum() # Sum of the total time coasting happens in laps

	# print(lapNumber, maxSpeed, maxAccel, timeAccel, timeCoast)

# STEP 6

coastDown = coasting & (filledTable["Velocity"] >= 5)  # Gather times where the car is coasting at 5 m/s or faster
coastId = (coastDown != coastDown.shift()).cumsum()  # ID each coasting segment
cdLapDuration = filledTable.groupby(coastId)["deltaT"].transform("sum")  # Labels the rows with the coasting time
coastData   = filledTable[coastDown & (cdLapDuration >= 1)]  # Only keep data that lasts over 1 second

# Graph coasting segments on top of the velocity
plt.figure()
plt.plot(time, filledTable["Velocity"], alpha=0.3)
plt.plot(coastData["Time"], coastData["Velocity"], marker='.', linestyle='', markersize=2)
plt.xlabel("Time (seconds)")
plt.ylabel("Velocity (m/s)")
plt.title("Coasting Segments and Velocity Over Time")
plt.show()

# print(coastId[coastData.index].unique()) # Coasting segment IDs
# print(coastData["deltaT"].sum()) # Total seconds of coast data

# STEP 7

