# Contains functions to generate objects and lists

from statistics import mean
import simpy
import random
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd
import numpy as np
import math

from class_definitions import *
from general_functions import *

def generate_disaster_sites(id, p):

    dis = Disaster_Site(id)
    p.disaster_site_dict[id] = dis

def generate_transfer_points(id, p):

    tp = Transfer_Points(id)
    p.transfer_points_dict[id] = tp

def generate_on_site_staff(counter, location, time, p):

    # Create the staff's id
    id = f"St_{counter}"

    # Create the staff
    st = On_Site_Staff(id, location, time)
    p.staff_dict[id] = st

def generate_ambulances(counter, location, time, p):

    # Create the ambulance's id
    id = f"Amb_{counter}"

    # Create the ambulance
    amb = Ambulance(id, location, time)
    p.ambulance_dict[id] = amb

def generate_hospitals(id, p):

    hosp = Hospital(id, p)
    p.hospital_dict[id] = hosp

def generate_patient(counter, location, time, p):

    if p.patient_counter_loc[location] < p.num_patients * p.triage_stat_prob_dict[location]:
    
        # Create the patient's id
        id = f"P_{counter}"

        # Randomly sample the time until the patient arrives
        for time_steps in range(len(p.patient_arrival_rates_changes)):
            if time <= p.patient_arrival_rates_changes[time_steps]:
                arrival_rate = p.patient_arrival_rate[location][time_steps]
                break

        #sampled_interarrival = max(random.expovariate(1/arrival_rate), 0)
        sampled_interarrival = max(np.random.poisson(1/arrival_rate), 0)

        arrival_time = time + sampled_interarrival

        # Create the patient
        pat = Patient(id, location, arrival_time)
        p.patient_dict[id] = pat
        p.patient_counter += 1
        p.patient_counter_loc[location] += 1

        # Add the event to the b_events_list
        p.b_events.loc[len(p.b_events)] = ["pat_arrival", id, arrival_time, p.event_index]
        p.event_index += 1