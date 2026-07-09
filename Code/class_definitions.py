import random
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import numpy as np
import math

class Params:

    def __init__(self):

        self.print_bool = False

        # Patient parameters:
        self.num_patients = 1500
        self.patient_counter = 0
        self.patient_counter_loc = {"D_1": 0, "D_2": 0}
        self.patient_arrival_rates_changes = [60, 120, 180, 10000]
        self.patient_arrival_rate = {"D_1": [60/(0.4*self.num_patients), 60/(0.3*self.num_patients), 60/(0.2*self.num_patients), 60/(0.1*self.num_patients)], 
                                "D_2": [60/(0.4*self.num_patients), 60/(0.3*self.num_patients), 60/(0.2*self.num_patients), 60/(0.1*self.num_patients)]}         # Arrival times per disaster scene, Interarrival time - a lower number indicates that patients are arriving closer to each other
        self.patients_completed = 0
        self.patients_deceased = 0
        self.patients_completed_rpm = []

        self.patient_categories = ["red", "orange", "green"]
        self.patient_probabilities = [0.2, 0.3, 0.5]                     # Konsensus Konferenz
        self.patient_priorities = {"red": 1, "orange": 2, "green": 3}

        # Disaster sites
        self.triage_stat = ["D_1", "D_2"]
        self.triage_stat_prob = [0.5, 0.5]
        self.triage_stat_prob_dict = {"D_1": 0.5, "D_2": 0.5}
        self.min_treatment_time = 5
        self.max_treatment_time = 25
        self.mean_treatment_time = 12
        self.treatment_rates = {"D_1": {"red": self.mean_treatment_time, "orange": self.mean_treatment_time, "green": self.mean_treatment_time}, 
                        "D_2": {"red": self.mean_treatment_time, "orange": self.mean_treatment_time, "green": self.mean_treatment_time}}          # Actually it is the treatment time

        # Tranfer points
        self.transfer_points = ["TP"]

        # On-site staff:
        self.num_on_site_staff = 22*2

        # Ambulance parameter:
        self.num_ambulances = int(21)        #82 ambulances - 20% for other tasks = 65 - 2* 22

        # Hospital parameters
        # hospitals
        self.hospitals = ["H_1", "H_2", "H_3", "H_4", "H_5"]
        self.hospitals_access = {"H_1": "local", "H_2": "local", "H_3": "local", "H_4": "distant", "H_5": "distant"}
        self.total_hosp_cap = 0.7*self.num_patients                   #1064
        self.hospital_capacities = {"H_1": math.floor(0.2425 * self.total_hosp_cap), 
                            "H_2": math.floor(0.155 * self.total_hosp_cap), 
                            "H_3": math.floor(0.082 * self.total_hosp_cap),
                            "H_4": math.floor(0.340 * self.total_hosp_cap),
                            "H_5": math.floor(0.180 * self.total_hosp_cap)}
        

        # Parameters for mixed hospital allocation policy
        self.prio_red = 1
        self.prio_orange = 1
        self.prio_sum = self.prio_red + self.prio_orange
        self.counter_mixed = 1

        # Distances
        self.added = 1.1
        self.offset = 5 # following Aringhieri et al 2022, service time for hospitals divided by 2
        self.distances = {"D_1": {"TP": int(np.ceil(10*self.added))+self.offset, "H_1": int(np.ceil(13*self.added))+self.offset, "H_2": int(np.ceil(11*self.added))+self.offset, "H_3": int(np.ceil(14*self.added))+self.offset, "H_4": int(np.ceil(47*self.added))+self.offset, "H_5": int(np.ceil(81*self.added))+self.offset}, 
                    "D_2": {"TP": int(np.ceil(2*self.added))+self.offset, "H_1": int(np.ceil(13*self.added))+self.offset, "H_2": int(np.ceil(8*self.added))+self.offset, "H_3": int(np.ceil(8*self.added))+self.offset, "H_4": int(np.ceil(48*self.added))+self.offset, "H_5": int(np.ceil(81*self.added))+self.offset},
                    "TP": {"H_4": int(np.ceil((36 + 7)*self.added)) +self.offset, "H_5": int(np.ceil((66 + 3)*self.added)) +self.offset}}

        # Dicts for agents:
        self.patient_dict = {}
        self.staff_dict = {}
        self.ambulance_dict = {}
        self.disaster_site_dict = {}
        self.transfer_points_dict = {}
        self.hospital_dict = {}

        # Dataframe for events
        self.b_events = pd.DataFrame(columns=["event", "agent", "time", "counter"])
        self.event_index = 0

        # Performance metrics
        self.num_in_system_history = [(0, 0)]
        self.integral = 0

    def add_del_to_num_in_sys_history(self, time, action):
        previous_entry = self.num_in_system_history[-1]
        previous_time, previous_num = previous_entry
        duration = time - previous_time
        self.integral += duration * previous_num

        if action == "add":
            new_num = previous_num + 1
        else:
            new_num = previous_num - 1

        self.num_in_system_history.append((time, new_num))

def get_max_casualties_in_system(history):
    max_cas = max(length for time, length in history)
    min_cas = min(length for time, length in history)
    
    return max_cas, min_cas

def policy_Closest_first(pat, p):
    loc = pat.location
    select_hosp = None
    min_dist = 10000

    for h in p.hospitals:
        hosp_obj = p.hospital_dict[h]
        if hosp_obj.remaining_capacity > 0:
            if p.distances[loc][h] < min_dist:
                select_hosp = h
                min_dist = p.distances[loc][h]

    return select_hosp

class Patient:
    def __init__(self, p_id, location, time):
        self.p_id = p_id
        self.arrival_time = time
        self.origin = location
        self.location = location
        self.initial_category = None
        self.category = None
        self.initial_rpm = None
        self.rpm = None
        self.resource = None
        self.hospital = None
        self.amb_dest = None
        self.completion_time = None
        self.deceased = False

        # Performance metrics
        self.join_triage_queue = None
        self.waiting_time_triage_queue = None
        self.start_triage_time = None
        self.finish_triage_time = None
        self.join_ost_queue = None
        self.waiting_time_ost_queue = None
        self.start_ost_time = None
        self.finish_ost_time = None
        self.join_amb_queue = None
        self.waiting_time_amb_queue = None
        self.start_amb_transportation_time = None
        self.finish_amb_transportation_time = None
        self.join_mte_queue = None
        self.waiting_time_mte_queue = None
        self.start_mte_transportation_time = None
        self.finish_mte_transportation_time = None

        # Service times
        self.service_time_triage = None
        self.service_time_ost = None
        self.service_time_amb = None
        self.service_time_mte = None
        self.time_in_system = None


    def determine_category(self, p):
        self.initial_category = random.choices(p.patient_categories, p.patient_probabilities)[0]
        if self.initial_category == "red":
            self.initial_rpm = int(random.uniform(1, 4))
        elif self.initial_category == "orange":
            self.initial_rpm = int(random.uniform(5, 8))
        elif self.initial_category == "green":
            self.initial_rpm = int(random.uniform(9, 12))

        self.rpm = self.initial_rpm
        self.category = self.initial_category

    def check_update_category(self, current_time):
        
        rand_num = random.random()
        
        if self.initial_category != "green" or rand_num <= 0.1:

            time_passed = current_time - self.arrival_time
            rpm_reduction = time_passed // 120
            self.rpm = max(self.initial_rpm - rpm_reduction, 0)

            if self.rpm <= 4:
                self.category = "red"
            elif self.rpm <= 8:
                self.category = "orange"
            else:
                self.category = "red"

    def update_transportation_mode(self, p):
        if self.hospital != self.amb_dest:
            if self.category == "red":
                prev_hosp = self.hospital
                closest_hosp = policy_Closest_first(self, p)
                if p.distances[self.location][closest_hosp] < p.distances[self.location][prev_hosp]:
                    self.hospital = closest_hosp

                    closest_hosp_obj = p.hospital_dict[closest_hosp]
                    prev_hosp_obj = p.hospital_dict[prev_hosp]

                    closest_hosp_obj.remaining_capacity -= 1
                    prev_hosp_obj.remaining_capacity += 1
            
                self.amb_dest = self.hospital

    def calculate_metrics(self):
        self.waiting_time_triage_queue = self.start_triage_time - self.join_triage_queue
        self.service_time_triage = self.finish_triage_time - self.start_triage_time

        self.waiting_time_ost_queue = self.start_ost_time - self.join_ost_queue
        self.service_time_ost = self.finish_ost_time - self.start_ost_time

        if self.category != "green":
            self.waiting_time_amb_queue = self.start_amb_transportation_time - self.join_amb_queue
            self.service_time_amb = self.finish_amb_transportation_time - self.start_amb_transportation_time

        if self.join_mte_queue != None:
            self.waiting_time_mte_queue = self.start_mte_transportation_time - self.join_mte_queue
            self.service_time_mte = self.finish_mte_transportation_time - self.start_mte_transportation_time

        self.time_in_system = self.completion_time - self.arrival_time

    def __iter__(self):
        return iter([self.p_id, self.category, self.origin, self.hospital, self.arrival_time, 
                    self.join_triage_queue, self.waiting_time_triage_queue, self.service_time_triage ,self.finish_triage_time, 
                    self.join_ost_queue, self.waiting_time_ost_queue, self.start_ost_time, self.service_time_ost, self.finish_ost_time,
                    self.join_amb_queue, self.waiting_time_amb_queue, self.start_amb_transportation_time, self.finish_amb_transportation_time,
                    self.join_mte_queue, self.waiting_time_mte_queue, self.start_mte_transportation_time, self.finish_mte_transportation_time,
                    self.completion_time])

class On_Site_Staff:
    def __init__(self, s_id, location, time):
        self.s_id = s_id
        self.patient = None
        self.location = location
        self.arrival_time = time
        self.status = "idle"

        # Performance metrics
        self.busy_time = 0
        self.busy_history = [(0, "idle")]

    def __iter__(self):
        return iter([self.s_id, self.location, self.busy_time, self.busy_history])

class Disaster_Site:
    def __init__(self, d_id):
        self.d_id = d_id
        self.triage_queue = []
        self.on_site_tr_queue = pd.DataFrame(columns = ["patient", "category", "time"])
        self.amb_queue = pd.DataFrame(columns = ["patient", "category", "time", "amb_time", "travel_time"])

        # Performance_metrics
        self.triage_queue_length_history = [(0, 0)]
        self.integral_triage = 0
        self.ost_queue_length_history = [(0, 0)]
        self.integral_ost = 0
        self.amb_queue_length_history = [(0, 0)]
        self.integral_amb = 0

    def add_to_triage_queue_history(self, time):
        previous_entry = self.triage_queue_length_history[-1]
        previous_time, previous_length = previous_entry
        duration = time - previous_time
        self.integral_triage += duration * previous_length

        self.triage_queue_length_history.append((time, len(self.triage_queue)))

    def add_to_ost_queue_history(self, time):
        previous_entry = self.ost_queue_length_history[-1]
        previous_time, previous_length = previous_entry
        duration = time - previous_time
        self.integral_ost += duration * previous_length

        self.ost_queue_length_history.append((time, len(self.on_site_tr_queue)))

    def add_to_amb_queue_history(self, time):
        previous_entry = self.amb_queue_length_history[-1]
        previous_time, previous_length = previous_entry
        duration = time - previous_time
        self.integral_amb += duration * previous_length

        self.amb_queue_length_history.append((time, len(self.amb_queue)))

    def get_max_queue_length(self, queue_name):
        queue_length_hist = getattr(self, f"{queue_name}_queue_length_history")
        max_length = max(length for time, length in queue_length_hist)
        return max_length

class Ambulance:
    def __init__(self, amb_id, location, time):
        self.amb_id = amb_id
        self.patient = None
        self.arrival_time = time
        self.origin = location
        self.location = location
        self.destination = None
        self.status = "idle"

        # Performance metrics:
        self.transport_patients_time = 0
        self.return_time = 0
        self.busy_history = [(0, "idle")]

    def __iter__(self):
        return iter([self.s_id, self.location, self.busy_time, self.busy_history])

class Transfer_Points:
    def __init__(self, tp_id):
        self.tp_id = tp_id
        self.queue = pd.DataFrame(columns = ["patient", "category", "time", "mte_time", "travel_time"])

        # Performance metrics
        self.queue_length_history = [(0, 0)]
        self.integral = 0

    def add_to_queue_history(self, time):
        previous_entry = self.queue_length_history[-1]
        previous_time, previous_length = previous_entry
        duration = time - previous_time
        self.integral += duration * previous_length

        self.queue_length_history.append((time, len(self.queue)))

    def get_max_queue_length(self):
        max_length = max(length for time, length in self.queue_length_history)
        return max_length
    
class Hospital:
    def __init__(self, hosp_id, p):
        self.hosp_id = hosp_id
        self.remaining_capacity = p.hospital_capacities[hosp_id]

        # Performance metrics
        self.capacity_history = [(0, self.remaining_capacity)]

    def update_capacity(self, time):
        self.capacity_history.append((time, self.remaining_capacity))
