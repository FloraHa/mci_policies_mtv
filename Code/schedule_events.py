import random
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd
import numpy as np
import math

from class_definitions import *
from general_functions import *
from generation_functions import *
from performance_metrics import *

def get_idle_resources(location, dict_res):
    idle_resources = []

    for i in dict_res:
        obj = dict_res[i]
        if obj.status == "idle":
            if obj.location == location:
                idle_resources.append(i)

    return idle_resources

# Queueing policies
def policy_ROG(df, p):

    if p.print_bool == True: 
        print(df)

    # Check if there is an entry with category "red"
    if "red" in df["category"].values:
        red_entries = df[df["category"] == "red"]
        red_entry_min_time = red_entries["time"].idxmin()
        pat_id = df.loc[red_entry_min_time, "patient"]
    # Check if there is an entry with category "orange"
    elif "orange" in df["category"].values:
        orange_entries = df[df["category"] == "orange"]
        orange_entry_min_time = orange_entries["time"].idxmin()
        pat_id = orange_entry_id = df.loc[orange_entry_min_time, "patient"]
    # If no red or orange entries, find the entry with category "green"
    elif "green" in df["category"].values:
        green_entry = df[df["category"] == "green"]
        green_entry_min_time = green_entry["time"].idxmin()
        pat_id = df.loc[green_entry_min_time, "patient"]

    return pat_id

def policy_FCFS(df, p):
    if p.print_bool == True: 
        print(df)
    min_time_index = df["time"].idxmin()
    pat_id = df.loc[min_time_index, "patient"]

    return pat_id

def policy_SPT(df, p):
    if p.print_bool == True:
        print(df)
    min_amb_time_index = df["amb_time"].idxmin()
    pat_id = df.loc[min_amb_time_index, "patient"]

    return pat_id

def policy_Mixed(df, p):
    if p.counter_mixed % p.prio_sum < p.prio_red:
        pat_id = policy_ROG(df, p)
    else:
        pat_id = policy_SPT(df, p)
    
    p.counter_mixed += 1
    return pat_id

# Hospital allocation policies:
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

def policy_Orange_remote(pat, p):
    cat = pat.category
    select_hosp = None
    min_dist = 10000

    if pat.category == "red":
        # if the patient is red, pick the closest hospital
        select_hosp = policy_Closest_first(pat, p)
    else:
        # select the closest hospital from the transfer point
        loc = p.transfer_points[0]
        # determine the closest hospital from the transfer point

        for h in p.hospitals:
            hosp_obj = p.hospital_dict[h]
            if hosp_obj.remaining_capacity > 0 and p.hospitals_access[h] == "distant":
                if p.distances[loc][h] < min_dist:
                    select_hosp = h
                    min_dist = p.distances[loc][h]

        if select_hosp == None:
            select_hosp = policy_Closest_first(pat)

    return select_hosp

# Transportation policy

def policy_red_direct_orange_indirect(pat, hosp_id, p):

    if pat.category == "red" or p.hospitals_access[hosp_id] == "local":
        return "direct"
    else:
        return "indirect"

# Hospital selection function
def select_hosp(pat, mode, time, p):

    cat = pat.category
    if p.print_bool == True: 
        print(f"The patient is of category: {cat}")

    if cat == "green":
        pat.completion_time = time
        #pat.check_update_category(time)
        p.patients_completed += 1
        p.patients_completed_rpm.append(pat.rpm)
        p.add_del_to_num_in_sys_history(time, "del")
    else:
        # Select the hospital
        if mode == "Closest_first":
            select_hosp = policy_Closest_first(pat, p)
        elif mode == "Distant_first":
            select_hosp = policy_Orange_remote(pat, p)
            
        # Allocate patient to selected hospital
        pat.hospital = select_hosp
        if p.print_bool == True: 
            print(f"The patient gets allocated to hospital {select_hosp}")

        # Update the hospitals capacity
        p.hospital_dict[select_hosp].remaining_capacity -= 1
        p.hospital_dict[select_hosp].update_capacity(time)
        if p.print_bool == True: 
            print(f"The new remaining capacity of hospital {select_hosp} is {p.hospital_dict[select_hosp].remaining_capacity}")

        # Select transportation mode: direct or indirect:
        trans_mode = policy_red_direct_orange_indirect(pat, select_hosp, p)

        # For patients being transported indirectly, select the transfer point
        if trans_mode == "indirect":
            tp = "TP"

        # Assign patient to ambulance queue
        dis = p.disaster_site_dict[pat.location]
        if trans_mode == "direct":
            dis.amb_queue.loc[len(dis.amb_queue)] = [pat.p_id, pat.category, time, p.distances[pat.location][pat.hospital], p.distances[pat.location][pat.hospital]]
            pat.amb_dest = select_hosp
        if trans_mode == "indirect":
            dis.amb_queue.loc[len(dis.amb_queue)] = [pat.p_id, pat.category, time, p.distances[pat.location][tp], p.distances[pat.location][tp] + p.distances[tp][pat.hospital]]
            pat.amb_dest = tp

        pat.join_amb_queue = time
        if p.print_bool == True: 
            print(f"The new ambulance queue: {dis.amb_queue}")
        dis.add_to_amb_queue_history(time)

# Deployment selection function:
def redeploy_amb(time, amb, mode, p):
    # update the ambulance location
    amb.location = amb.destination
    if p.print_bool == True: 
        print(f"The ambulance is currently located at {amb.location}")

    # Redeploy the ambulance
    if mode == "LQF":
        # Get largest queue:
        allocated_site = None
        max_cas = 0

        for dis_id in p.disaster_site_dict:
            dis = p.disaster_site_dict[dis_id]
            if p.print_bool == True: 
                print(f"Disaster site to evaluate: {dis} with queue length of {len(dis.amb_queue)}")
            if len(dis.amb_queue) > max_cas:
                allocated_site = dis_id
                max_cas = len(dis.amb_queue)

    if p.print_bool == True: 
        print(f"The selected disaster site to return to is {allocated_site}")

    # allocate ambulance to selected site
    if allocated_site == None:
        amb.destination = amb.origin
    else:
        amb.destination = allocated_site

    if p.print_bool == True:
        print(f"Amb: {amb.amb_id}, Amb destination: {amb.destination}, Amb location {amb.location}")

    fin_time = time + p.distances[amb.destination][amb.location]
    amb.return_time += p.distances[amb.destination][amb.location]

    # Add the event to the b_events_list
    p.b_events.loc[len(p.b_events)] = ["amb_arrival", amb.amb_id, fin_time, p.event_index]
    p.event_index += 1

def update_b_event_list(id, p):
    p.b_events = remove_rows_by_value(p.b_events, "agent", id)
    p.b_events.reset_index(drop=True, inplace=True)

def get_next_b_event(df):

    time = df['time'].min()

    return time

# B and C events
def execute_b_ev_pat_arr(time, p_id, p):

    # Get the patient's object
    pat = p.patient_dict[p_id]
    pat_loc = pat.location

    if p.print_bool == True: 
        print(f"The patients location is {pat_loc}")

    # Get the disaster site's object
    dis = p.disaster_site_dict[pat_loc]

    # Move patient to the triage queue
    dis.triage_queue.append(p_id)
    pat.join_triage_queue = time
    if p.print_bool == True: 
        print(f"The new triage queue at the location {pat_loc} is {dis.triage_queue}")
    dis.add_to_triage_queue_history(time)

    # Remove event from b_event_list
    update_b_event_list(p_id, p)

    # Add the patient to the num_in_system list
    p.add_del_to_num_in_sys_history(time, "add")

    if p.print_bool == True: 
        print(f"The b_event_list after update: {p.b_events}")

    # Generater the next patient:
    loc_new_pat = pat.location
    generate_patient(p.patient_counter, loc_new_pat, time, p)

    if p.print_bool == True: 
        print(f"The b_event list after creating a new patient: {p.b_events}")

def triage_patient(time, p):

    for dis_id in p.triage_stat:
        if p.print_bool == True: 
            print(f"Current disaster site: ", dis_id)

        # Get the locations object:
        dis = p.disaster_site_dict[dis_id]

        # Check if there are still patinets in the queue;
        if len(dis.triage_queue) > 0:
            if p.print_bool == True: 
                print(f"Current triage queue: {dis.triage_queue}")

            # Determine the next patient to be triaged:
            p_id = dis.triage_queue[0]
            if p.print_bool == True: 
                print(f"The next patient is: {p_id}")
            pat = p.patient_dict[p_id]
            pat.start_triage_time = time

            # Determine the patients category
            pat.determine_category(p)

            if p.print_bool == True: 
                print(f"The patients category is {pat.category}")

            # Remove patinet from the queue
            dis.triage_queue.pop(0)
            if p.print_bool == True: 
                print(f"Updated triage queue: {dis.triage_queue}")
            dis.add_to_triage_queue_history(time)

            # Calculate the end of the treatment time
            fin_time = time
            pat.finish_triage_time = fin_time
            if p.print_bool == True: 
                print(f"finish time: {fin_time}")

            # Schedule the next b_event
            p.b_events.loc[len(p.b_events)] = ["fin_triage", p_id, fin_time, p.event_index]
            p.event_index += 1

def execute_b_ev_fin_triage(time, p_id, p):

    # Get the patient's object
    pat = p.patient_dict[p_id]
    pat_loc = pat.location

    if p.print_bool == True: 
        print(f"The patient is located at {pat_loc}")

    # Get the disaster site's object
    dis = p.disaster_site_dict[pat_loc]

    # Move the patient to the treatment queue:
    dis.on_site_tr_queue.loc[len(dis.on_site_tr_queue)] = [p_id, pat.category, time]
    pat.join_ost_queue = time
    if p.print_bool == True: 
        print(f"New on site treatment queue: {dis.on_site_tr_queue}")
    dis.add_to_ost_queue_history(time)

    # Remove event from b_event_list
    update_b_event_list(p_id, p)

    if p.print_bool == True: 
        print(f"The b_event list after creating a new patient: {p.b_events}")

def on_site_treatment(time, mode, p):

    # Check all disaster sites
    for dis_id in p.triage_stat:
        if p.print_bool == True: 
            print(f"Current disaster site: ", dis_id)

        # Get the locations object:
        dis = p.disaster_site_dict[dis_id]

        # Check if there are idle resources:
        id_res = get_idle_resources(dis_id, p.staff_dict)
        if p.print_bool == True: 
            print(f"Idle resources are: {id_res}")

        if len(id_res) > 0:
                
            # Check if casualties are waiting: 
            if len(dis.on_site_tr_queue) > 0:
                while len(id_res) > 0 and len(dis.on_site_tr_queue) > 0:

                    if p.print_bool == True: 
                        print(f"Current treatment queue: {dis.on_site_tr_queue}")

                    # Get the resource:
                    ts_id = random.choice(id_res)
                    ts = p.staff_dict[ts_id]
                    if p.print_bool == True: 
                        print(f"Resource to be scheduled: {ts}")

                    # Get the patient to be treated: 
                    if mode == "FCFS":
                        pat_id = policy_FCFS(dis.on_site_tr_queue, p)
                    elif mode == "ROG":
                        pat_id = policy_ROG(dis.on_site_tr_queue, p)

                    pat = p.patient_dict[pat_id]
                    pat.check_update_category(time)
                    pat.start_ost_time = time

                    if pat.rpm > 0:

                        # Set the resource as busy
                        ts.status = "busy"
                        ts.busy_history.append((time, ts.status))

                        if p.print_bool == True: 
                            print(f"Patient to be treated: {pat_id}")

                        # Allocate the patient to the resource
                        pat.resource = ts_id
                        ts.patient = pat_id

                        # Remove patient from the queue:
                        dis.on_site_tr_queue = remove_rows_by_value(dis.on_site_tr_queue, "patient", pat_id)
                        dis.on_site_tr_queue.reset_index(drop=True, inplace=True)
                        if p.print_bool == True: 
                            print(f"New treatment queue: {dis.on_site_tr_queue}")
                        dis.add_to_ost_queue_history(time)

                        # Calculate the end onf the treatment time
                        mean_treatment_time = p.treatment_rates[dis_id][pat.category]
                        sampled_tr_time = min(max(np.random.poisson(mean_treatment_time), p.min_treatment_time), p.max_treatment_time)
                        if p.print_bool == True: 
                            print("Treatment time: ", sampled_tr_time)
                        fin_time = time + sampled_tr_time
                        pat.finish_ost_time = fin_time
                        if p.print_bool == True: 
                            print("Finish time: ", fin_time)

                        ts.busy_time += sampled_tr_time

                        # Schedule the next b_event
                        p.b_events.loc[len(p.b_events)] = ["fin_ost", pat_id, fin_time, p.event_index]
                        p.event_index += 1
                        if p.print_bool == True: 
                            print("Updated event list: ", p.b_events)
                    
                    else:
                        p.patients_deceased += 1
                        p.add_del_to_num_in_sys_history(time, "del")
                        pat.deceased = True

                        # Remove patient from the queue:
                        dis.on_site_tr_queue = remove_rows_by_value(dis.on_site_tr_queue, "patient", pat_id)
                        dis.on_site_tr_queue.reset_index(drop=True, inplace=True)
                        dis.add_to_ost_queue_history(time)

def execute_b_ev_fin_ost(time, p_id, mode, p):

    # Get the patient's object
    pat = p.patient_dict[p_id]

    # Get the resource
    res_id = pat.resource
    res = p.staff_dict[res_id]
    if p.print_bool == True: 
        print(f"The resource to be released is: {res_id}")

    # Release the resoure
    res.patient = None
    res.status = "idle"
    res.busy_history.append((time, res.status))
    pat.resource = None

    # Start with hospital allocation
    select_hosp(pat, mode, time, p)

    # Remove the event from the event list      
    update_b_event_list(p_id, p)    

    if p.print_bool == True: 
        print(f"The b_event list after creating a new patient: {p.b_events}")  

def ambulance_transportation(time, mode, p):
    
    for dis_id in p.triage_stat:
        if p.print_bool == True: 
            print(f"Current disaster site: ", dis_id)

        # Get the locations object:
        dis = p.disaster_site_dict[dis_id]

        # Check if there are idle resources:
        id_res = get_idle_resources(dis_id, p.ambulance_dict)
        if p.print_bool == True: 
            print(f"Idle resources are: {id_res}")

        if len(id_res) > 0:

            # Check if there are casualties waiting
            if len(dis.amb_queue) > 0:
                while len(id_res) > 0 and len(dis.amb_queue) > 0:

                    if p.print_bool == True: 
                        print(f"Current ambulance queue: {dis.amb_queue}")

                    # Get the resource: 
                    amb_id = random.choice(id_res)
                    amb = p.ambulance_dict[amb_id]
                    if p.print_bool == True: 
                        print(f"Ambulance to be scheduled: {amb_id}")

                    # Get the patinet to be treated:

                    if mode == "ROG":
                        pat_id = policy_ROG(dis.amb_queue, p)
                    elif mode == "SPT":
                        pat_id = policy_SPT(dis.amb_queue, p)
                    elif mode == "Mixed":
                        pat_id = policy_Mixed(dis.amb_queue, p)

                    pat = p.patient_dict[pat_id]
                    pat.check_update_category(time)
                    pat.update_transportation_mode(p)
                    if p.print_bool == True: 
                        print(f"Next patient to be transported: {pat_id}")

                    if pat.rpm > 0:

                        # Set the resource as busy:
                        amb.status = "busy"
                        amb.busy_history.append((time, amb.status))

                        pat.resource = amb_id
                        amb.patient = pat_id
                        amb.destination = pat.amb_dest
                        pat.start_amb_transportation_time = time

                        # Calculate the end of the transportation
                        transportation_time = p.distances[pat.location][pat.amb_dest]
                        fin_time = time + transportation_time
                        pat.finish_amb_transportation_time = fin_time
                        if p.print_bool == True: 
                            print(f"The transport will be done at {fin_time}")
                        
                        amb.transport_patients_time += transportation_time

                        # Remove the patient from the queue:
                        dis.amb_queue = remove_rows_by_value(dis.amb_queue, "patient", pat_id)
                        dis.amb_queue.reset_index(drop=True, inplace = True)
                        dis.add_to_amb_queue_history(time)
                        id_res.remove(amb_id)

                        # Schedule the next b_event
                        p.b_events.loc[len(p.b_events)] = ["fin_trans_amb", pat_id, fin_time, p.event_index]
                        p.event_index += 1
                        if p.print_bool == True: 
                            print("Updated event list: ", p.b_events)

                    else:
                        p.patients_deceased += 1
                        p.add_del_to_num_in_sys_history(time, "del")
                        pat.deceased = True

                        # Remove the patient from the queue:
                        dis.amb_queue = remove_rows_by_value(dis.amb_queue, "patient", pat_id)
                        dis.amb_queue.reset_index(drop=True, inplace = True)
                        dis.add_to_amb_queue_history(time)

def execute_b_ev_fin_trans_amb(time, p_id, mode_redeploy, p):

    # Get the patient's object
    pat = p.patient_dict[p_id]

    # Get the resource
    res_id = pat.resource
    res = p.ambulance_dict[res_id]
    if p.print_bool == True: 
        print(f"The resource to be released is: {res_id}")

    # Release the resoure
    res.patient = None
    pat.resource = None

    # Update the patients location:
    pat.location = pat.amb_dest
    if p.print_bool == True: 
        print(f"The current patients location is {pat.location}")

    # if the patient has arrived at a hospital:
    if pat.location in p.hospitals:
        pat.completion_time = time
        pat.check_update_category(time)
        p.patients_completed += 1
        p.patients_completed_rpm.append(pat.rpm)
        p.add_del_to_num_in_sys_history(time, "del")
    else:
        # Append patient to TP queue
        tp = p.transfer_points_dict[pat.location]
        tp.queue.loc[len(tp.queue)] = [p_id, pat.category, time, p.distances[pat.location][pat.hospital], p.distances[pat.origin][pat.location] + p.distances[pat.location][pat.hospital]]
        pat.join_mte_queue = time

        if p.print_bool == True: 
            print(f"The new queue at the transfer point is {tp.queue}")
        tp.add_to_queue_history(time)

    # Remove the event from the event list      
    update_b_event_list(p_id, p) 

    if p.print_bool == True: 
        print(f"The b_event list after creating a new patient: {p.b_events}")

    res.status = "return"
    res.busy_history.append((time, res.status))
    # Ambulances:
    redeploy_amb(time, res, mode_redeploy, p)

def execute_b_ev_amb_arrival(amb_id, time, p):
    
    # Get the ambulance's object
    amb = p.ambulance_dict[amb_id]

    amb.location = amb.destination
    amb.destination = None
    amb.status = "idle"
    amb.busy_history.append((time, amb.status))

    # Remove the event from the event list      
    update_b_event_list(amb_id, p)

    if p.print_bool == True: 
        print(f"The b_event list after creating a new patient: {p.b_events}")

def mte_transportation(time, p):

    for tp_id in p.transfer_points:
        if p.print_bool == True: 
            print(f"Current transfer point: ", tp_id)

        # Get the locations object:
        tp = p.transfer_points_dict[tp_id]

        # Check if there are still patinets in the queue;
        if len(tp.queue) > 0:
            if p.print_bool == True: 
                print(f"Current queue: {tp.queue}")

            # Determine the next patient to be moved to the hospital:
            pat_id = policy_FCFS(tp.queue, p)
            pat = p.patient_dict[pat_id]
            pat.start_mte_transportation_time = time

            if p.print_bool == True: 
                print(f"The patient to be moved to the hospital is {pat_id}")

            min_time_index = tp.queue["time"].idxmin()
            remaining_time = tp.queue.loc[min_time_index, "mte_time"]
            fin_time = time + remaining_time
            pat.finish_mte_transportation_time = time

            if p.print_bool == True: 
                print(f"The patient will reach the hospital at {fin_time}")

            # Remove the patient from the queue:
            tp.queue = remove_rows_by_value(tp.queue, "patient", pat_id)
            tp.queue.reset_index(drop=True, inplace = True)
            if p.print_bool == True: 
                print(f"Updated queue: {tp.queue}")
            tp.add_to_queue_history(time)

            # Schedule the next b_event
            p.b_events.loc[len(p.b_events)] = ["fin_trans_mte", pat_id, fin_time, p.event_index]
            p.event_index += 1
            if p.print_bool == True: 
                print("Updated event list: ", p.b_events)

def execute_b_ev_hosp_arrival(time, p_id, p):

    pat = p.patient_dict[p_id]

    pat.completion_time = time
    pat.location = pat.hospital
    pat.check_update_category(time)
    p.patients_completed += 1
    p.patients_completed_rpm.append(pat.rpm)
    p.add_del_to_num_in_sys_history(time, "del")

    # Remove the event from the event list      
    update_b_event_list(p_id, p)

    if p.print_bool == True: 
        print(f"The b_event list after creating a new patient: {p.b_events}")