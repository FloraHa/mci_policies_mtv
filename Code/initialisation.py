import random
import numpy as np


from general_functions import *                 # File containing all the general functions
from class_definitions import *                 # File containing all the class definitions
from generation_functions import *
from schedule_events import *
from performance_metrics import *


def initialise_simulation(amb_red = 0, random_seed=None):

    params = Params()

    # Start of simulation: Initialise values:
    if params.print_bool == True: 
        print("Initialization")

    if random_seed != None:
        random.seed(random_seed)

    # Initialize time:
    time = 0

    # Generate initial resources

    # Disaster sites
    for i in params.triage_stat:
        generate_disaster_sites(i, params)

    if params.print_bool == True: 
        print(params.disaster_site_dict)

    # Transfer points
    for i in params.transfer_points:
        generate_transfer_points(i, params)

    if params.print_bool == True: 
        print(params.transfer_points_dict)

    # On-site staff
    for i in range(params.num_on_site_staff):
        if i < len(params.triage_stat):
            loc = params.triage_stat[i]
        else:
            loc = random.choices(params.triage_stat, params.triage_stat_prob)[0]
        generate_on_site_staff(i, loc, time, params)

    if params.print_bool == True: 
        for i in params.staff_dict:
            print(f"{i} is located at {params.staff_dict[i].location}")

    # Ambulances
    params.num_ambulances = int(np.floor(params.num_ambulances * (1 - amb_red)))
    print("The number of ambulances is: ", params.num_ambulances)
    for i in range(params.num_ambulances):
        if i < len(params.triage_stat):
            loc = params.triage_stat[i]
        else:
            loc = random.choices(params.triage_stat, params.triage_stat_prob)[0]
        generate_ambulances(i, loc, time, params)

    if params.print_bool == True: 
        for i in params.ambulance_dict:
            print(f"{i} is located at {params.ambulance_dict[i].location}")

    # Hospitals
    for i in params.hospitals:
        generate_hospitals(i, params)

    if params.print_bool == True: 
        print(params.hospital_dict)

    # Initialise events:
    for dis in params.triage_stat:
        generate_patient(params.patient_counter, dis, time, params)

    if params.print_bool == True: 
        for i in params.patient_dict:
            print(f"{i} is located at {params.patient_dict[i].location}")

    return time, params