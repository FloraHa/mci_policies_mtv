from general_functions import *                 
from class_definitions import *                 
from generation_functions import *
from schedule_events import *

# Calcualte the patients' waiting times:
def calculate_patients_performance_metrics(p):
    for pat_id in p.patient_dict:
        pat = p.patient_dict[pat_id]
        if pat.deceased == False:
            pat.calculate_metrics()
