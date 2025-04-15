from w_sensor import Water_Sensor
from a_sensor import Air_Sensor
from db_config import db, user_collection, sensor_collection, settings_collection
from flask import jsonify
import json
from bson import json_util
import threading
import time
from datetime import datetime
from collections import deque
from app import Flask_App
from mail_server import mail_server
from sys_state import Sys_State
from random_test_sensor import Random_Test_Sensor
from pymongo import MongoClient
import requests

#----------------------------------------------------------------------------------------
#   Entry Point for the Aqualb Sensor system
#   See README file for system architecture

#   Summary of File
#   main.py serves as the control module for the backend.
#   it creates multiple threads: the webApp, the mail server and
#   a thread to read each sensor. Implementation is intended to 
#   avoid freezes while waiting on IO from the sensors
#   Data is communicated between threads primarily using the
#   sys_state class. In short it is a semaphore protected dictionary
#   see sys_state.py for details. main.py also contains the code
#   for sensor_proc, which is the function the sensor threads execute
#   in.  

#   Execution Flow (main):
#       Initialization:
#           Create system_state instance
#           Run app and mail threads
#           Get sensor and config info from the DB
#       Startup:
#           Connect to sensors on their Com ports
#           Compile all sensor information
#           Run threads for each sensor
#       Running State:
#           Checks for terminate flag
#               Moves to terminate
#           Checks for new settings flag
#               Kills all sensor threads
#               Repeats all startup steps with ne configs in DB
#           Repeat
#       Terminate:
#           Rejoin all other threads
#           Ends
#----------------------------------------------------------------------------------------

# Semaphore protected dictionary
system_state = Sys_State({
    # Contains the state of the system, placeholder is Initial, system goes between "waiting" and "running"
    "state": "Initial",
    
    # Hopefully can add another tank with minimal implementation
    # If changed, double check initialization in main to ensure correctness
    "Sensor Groups": 2,

    # Touple containing the raw data needed to create the sensors, unused outside
    # of Initialization, Startup, and resets
    # tuple = sensor object, sensor id, sensor name, high, low, db collection
    "raw_sensors": [],
    
    # Dictionary of sensors indexed by their names, contents are dictionaries
    # containing sensor information, see new_sensor_wrapper for details
    "Sensor List": {},
    
    # terminate flag
    "terminate": False,
    
    # instructs sensor threads to end
    "reset sensors": False,
    
    # signals main that changes have been made to sensor configs
    "New Settings": False,

    # Access point to the mail server
    "Mail Server": None,

    # how often to read the sensors (in seconds)
    "Read Frequency": 5
})

def main():
    #--------------------#
    # Initialize Section #
    #--------------------#

    # initialize app thread
    app_thread = threading.Thread(target=app_init, args=[system_state])
    app_thread.start()

    # pulls state values from db
    db_settings_cursor = settings_collection.find()
    db_settings_list = list(db_settings_cursor)
    system_state.set("state", db_settings_list[0]['system_state'])
    while system_state.get("state") == "waiting":
        print("waiting for system running")
        time.sleep(5)
        db_settings_cursor = settings_collection.find()
        db_settings_list = list(db_settings_cursor)
        system_state.set("state", db_settings_list[0]['system_state'])


    # Get and set the read frequency
    system_state.set("Read Frequency", db_settings_list[0]['read_frequency'])

    # initialize mail server
    mail_thread = threading.Thread(target=mail_init, args=[system_state])
    mail_thread.start()

    # initialize connection with host computer
    # should be the only connection in the setup phase
    # Flask takes user data and fills in the sensor collection, system state is updated here

    #--------------------#
    # Startup Section    #
    #--------------------#

    print("Looking for sensors")

    # Loops until all sensors are added
    # While loop should only run once, it confirms the correct sensor count
    # of tries again
    sensor_config = sensor_collection.find()
    settings = settings_collection.find()
    settings_list = list(settings)

    # This loops through all the sensors
    for sensor in sensor_config:
        # dynamically create a new collection and add to the tuple, this will read from sensor collection
        CO2_db_name = f"{sensor['name']}_CO2_collection_run{settings_list[0]['run_number']}"   # db for CO2
        DO_db_name = f"{sensor['name']}_DO_collection_run{settings_list[0]['run_number']}"   # db for DO
        CO2_db_collection = db[CO2_db_name]
        DO_db_collection = db[DO_db_name]
        CO2_db_collection.insert_one({"init": "collection created"})
        DO_db_collection.insert_one({"init": "collection created"})
        if sensor["connection"] == "COM3":
            water_sensor = Water_Sensor(sensor["connection"], sensor["baud_rate"])
            system_state.add_to_list("raw_sensors", (water_sensor, sensor["_id"], sensor["name"], "CO2", float(sensor["measures"]["CO2"]["range_high"]), float(sensor["measures"]["CO2"]["range_low"]), CO2_db_collection))
            system_state.add_to_list("raw_sensors", (water_sensor, sensor["_id"], sensor["name"], "DO", float(sensor["measures"]["DO"]["range_high"]), float(sensor["measures"]["DO"]["range_low"]), DO_db_collection))
        else:
            system_state.add_to_list("raw_sensors", (Random_Test_Sensor(), sensor["_id"], sensor["name"], "CO2", float(sensor["measures"]["CO2"]["range_high"]), float(sensor["measures"]["CO2"]["range_low"]), CO2_db_collection))
            system_state.add_to_list("raw_sensors", (Random_Test_Sensor(), sensor["_id"], sensor["name"], "DO", float(sensor["measures"]["DO"]["range_high"]), float(sensor["measures"]["DO"]["range_low"]), DO_db_collection))
        #system_state.add_to_list("raw_sensors", (Air_Sensor("COM5", 19200), "Sensor #" + str(number), 40000, 1, db_list[number]))
    
    print("sensors connected")

    # convert the raw sensor data to sensor wrappers
    # repackaging the sensor info into a more usable form
    for data_set in system_state.get("raw_sensors"):
        system_state.add_to_dict("Sensor List", f"{data_set[2]}-{data_set[3]}", new_sensor_wrapper(*data_set))

    print("sensors wrapped")

    # create list of threads for each sensor
    sensor_threads = []
    for sensor in system_state.get("Sensor List").values():
        sensor_threads.append(threading.Thread(target=sensor_proc, args=[sensor]))

    # begin threads
    # sleep prevents certain concurrency issues
    time.sleep(5)
    for thread in sensor_threads:
        thread.start()

    print("all threads active")
    # main state
    while not system_state.get("terminate"):
        # If the flag is True, reset sensors and apply updates
        if system_state.get("New Settings"):
            print("New Settings Detected!!!!")
            system_state.set("reset sensors", True)

            # all sensor threads stopped
            for thread in sensor_threads:
                thread.join()
            print("all sensor threads joined")

            # repeat the startup procedure

            # Empty raw sensors, sensor threads, and sensor list
            system_state.set("raw_sensors", [])
            sensor_threads = []
            system_state.set("Sensor List", {})

            # DB query to reset sensors
            sensor_config = sensor_collection.find()   # get all the sensors
            for sensor in sensor_config:
                # dynamically create a new collection and add to the tuple, this will read from sensor collection
                CO2_db_name = f"{sensor['name']}_CO2_collection_run{settings_list[0]['run_number']}"   # db for CO2
                DO_db_name = f"{sensor['name']}_DO_collection_run{settings_list[0]['run_number']}"   # db for DO
                CO2_db_collection = db[CO2_db_name]
                DO_db_collection = db[DO_db_name]
                #water_sensor = Water_Sensor(sensor["connection"], sensor["baud_rate"])
                system_state.add_to_list("raw_sensors", (Random_Test_Sensor(), sensor["_id"], sensor["name"], "CO2", float(sensor["measures"]["CO2"]["range_high"]), float(sensor["measures"]["CO2"]["range_low"]), CO2_db_collection))
                system_state.add_to_list("raw_sensors", (Random_Test_Sensor(), sensor["_id"], sensor["name"], "DO", float(sensor["measures"]["DO"]["range_high"]), float(sensor["measures"]["DO"]["range_low"]), DO_db_collection))

            for data_set in system_state.get("raw_sensors"):
                system_state.add_to_dict("Sensor List", f"{data_set[2]}-{data_set[3]}", new_sensor_wrapper(*data_set))

            print("sensors rewrapped")

            # create list of threads for each sensor
            for sensor in system_state.get("Sensor List").values():
                sensor_threads.append(threading.Thread(target=sensor_proc, args=[sensor]))

            system_state.set("reset sensors", False) # Reset 'reset sensors'

            # begin threads
            for thread in sensor_threads:
                thread.start()

            print("all threads active again")

            # reset the new settings flag
            system_state.set("New Settings", False) # Reset 'New Settings'

    # end main state while
    print(system_state.get("terminate"))
    
    stop_flask()   # Stop flask server

    # Join all threads
    app_thread.join()
    mail_thread.join()
    for thread in sensor_threads:
        thread.join()

    

    print("all threads closed")
    # ends program
    # data = w_sensor1.disconnect_port()    --- implement at end of run for sensors


# creates dictionary breakdown for sensor
# This is intended to make it easier to access the
# sensor parameters
def new_sensor_wrapper(sensor, id, name, measure, high, low, db):
    out = {
        "sensor": sensor,
        "id": id,
        "name": name,
        "measure": measure,
        "high": high,
        "low": low,
        "db": db,
        "current reading": {},
        "recent readings": deque()
    }
    print("wrapping sensor ", name, " of measure ", measure)
    return out


#   sensor_proc: Multithread entry point for each sensor

#   Summary:
#   Thread repeatedly reads sensor value and stores it.
#   Keeps a reccord of recent readings.
#   Because thread is directly modifying shared variables, 
#   most computation is in a semaphore lock.
#   CAUTION: uncaught exceptions in the semaphore lock will 
#   freeze all other threads since it never releases. That is
#   why there is a very broad try catch covering the lock.

#   Execution Flow (sensor_proc)
#       Check if terminate or reset flags have been flipped
#           End thread if either has
#       Read new value
#       Lock the semaphore
#       Store reading in que of this sensors recent readings
#       Store reading in DB
#       Release semaphore
#       Wait based on system configurations
def sensor_proc(sensor_wrapper):
    # will continuously update with the current value of
    # this sensor then sleep, shared storage needs protection

    # read sensor data
    while (not system_state.get("terminate")) and (not system_state.get("reset sensors")):
        # Lock the semaphore
        system_state.hard_lock()
        # get current sensor value
        current_reading = {"value":sensor_wrapper["sensor"].read_data(sensor_wrapper["measure"]), "time": datetime.now().timestamp()}

        # avoid freezing the entire system with an exception
        try:
            # store reading in the wrapper
            sensor_wrapper["current reading"] = current_reading
            sensor_wrapper["recent readings"].append(current_reading)

            # check if reading in range
            high = sensor_wrapper["high"]
            low = sensor_wrapper["low"]

            # if reading out of range, notify users
            if current_reading["value"] > high or current_reading["value"] < low:
                notification(sensor_wrapper)

            # limit length of recent readings
            while len(sensor_wrapper["recent readings"]) > 0:
                if len(sensor_wrapper["recent readings"]) > 100:
                    sensor_wrapper["recent readings"].popleft()
                else:
                    break

            # Creating a DB entry with the current reading
            sensor_wrapper["db"].insert_one({"value": current_reading["value"], "time": datetime.now(), "sensor_id": sensor_wrapper["id"]})
        except Exception as err:
            print("Error in sensor reading for " + sensor_wrapper["name"])
            print("\n" + str(err))

        # release semaphore
        system_state.hard_release()

        # sleep
        start_sleep = time.time()

        while ( (time.time() - start_sleep) < system_state.get("Read Frequency")) and (not system_state.get("reset sensors")):
            time.sleep(1)


#   Provides emails to the email server

#   Created email message to send to all addresses
#   Gives that email to each address in the mail server.
#   Occurs within sensor_proc semaphore lock, so no
#   concurrency protection in this method.
def notification(sensor):
    ms = system_state.parameters["mail server"]
    text = "Subject: Sensor Out of Range\n\n" + \
    "Sensor value out of range: " + \
    "\nsensor " + sensor["name"] +" read value " + str(sensor["recent readings"][-1]["value"]) + \
    "\nNot with " + str(sensor["low"]) + "-" + str(sensor["high"]) + " range"    
    users_cursor = user_collection.find()
    user_list = list(users_cursor)
    emails = []

    for user in user_list:
        print("email sent")
        ms.send_email(user["email"], text)

#   Create Flask App and hand it execution on this thread.
def app_init(state):
    my_app = Flask_App(state)
    my_app.run_app()
    pass

#   Stop the Flask App
def stop_flask():
    try:
        requests.post("http://localhost:5000/shutdown")
    except requests.exceptions.ConnectionError:
        print("Flask server already stopped or not reachable.")

#   Create mail server and hand it execution on this thread.
def mail_init(state):
    ms = mail_server()
    system_state.set("mail server", ms)
    ms.run(state)

# If main fails, try and shut down the other threads
try:
    main()
except Exception as err:
    print(err)
    system_state.set("terminate", True)
