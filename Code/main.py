from general_functions import *
from class_definitions import *
from generation_functions import *
from schedule_events import *
from performance_metrics import *
from initialisation import *

def main(mode_alloc, mode_trans, amb_red):

    # Set policies
    mode_ost = "ROG"
    mode_redeploy = "LQF"

    time, params = initialise_simulation(amb_red)

    iter = 0

    while params.patients_completed + params.patients_deceased < params.num_patients:

        iter += 1

        # A phase: find next event and advance clock:
        ###########################################################

        if len(params.b_events) > 0:
            time = get_next_b_event(params.b_events)
        
        # B Phase: execute all b_events due
        ###########################################################

        # Get a list of all events at time t
        events_due = filter_dataframe(params.b_events, "time", time)
        
        while len(events_due) > 0:

            first_event_index = events_due["counter"].idxmin()
            counter = events_due.loc[first_event_index, 'counter']
            ev = events_due.loc[first_event_index, 'event']

            if ev == "pat_arrival":
                pat_id = events_due.loc[first_event_index, 'agent']
                execute_b_ev_pat_arr(time, pat_id, params)

            elif ev == "fin_triage":
                pat_id = events_due.loc[first_event_index, 'agent']
                execute_b_ev_fin_triage(time, pat_id, params)

            elif ev == "fin_ost":
                pat_id = events_due.loc[first_event_index, 'agent']
                execute_b_ev_fin_ost(time, pat_id, mode_alloc, params)

            elif ev == "fin_trans_amb":
                pat_id = events_due.loc[first_event_index, 'agent']
                execute_b_ev_fin_trans_amb(time, pat_id, mode_redeploy, params)

            elif ev == "amb_arrival":
                amb_id = events_due.loc[first_event_index, 'agent']
                execute_b_ev_amb_arrival(amb_id, time, params)

            elif ev == "fin_trans_mte":
                pat_id = events_due.loc[first_event_index, 'agent']
                execute_b_ev_hosp_arrival(time, pat_id, params)

            # Remove the current event from the event list
            events_due = remove_rows_by_value(events_due, "counter", counter)
        
        # C Phase: execute all c_events due
        ###########################################################

        triage_patient(time, params)
        on_site_treatment(time, mode_ost, params)        
        ambulance_transportation(time, mode_trans, params)
        mte_transportation(time, params)

    ####################################################################################################################
    
    print(f"The simulation ended at time {time}")


mode_alloc = "Closest_first"  # Alternatives: "Closest_first", "Distant_first"
mode_trans = "SPT" # Alternatives: ROG, SPT, Mixed
amb_red = 0     # Reduction of available ambulances

main(mode_alloc, mode_trans, amb_red)
