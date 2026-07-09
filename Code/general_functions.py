# This file contains general functions

import pandas as pd


from class_definitions import *

def filter_dataframe(df, column_name, value):
    """
    Copy a dataframe and return only the rows that have a specific value in a predefined column.
    :param df: The original dataframe.
    :param column_name: The name of the column to filter on.
    :param value: The value to filter on.
    :return: The filtered dataframe.
    """
    filtered_df = df.copy()
    filtered_df = filtered_df[filtered_df[column_name] == value]
    return filtered_df

def remove_rows_by_value(df, col_name, value_to_remove):
    return df[df[col_name] != value_to_remove]

def add_to_event_list(event, object, time, index, p):

    new_row = {"event": event, "object": object, "time": time, "counter": index}

    new_df = pd.DataFrame([new_row])

    p.b_events = pd.concat([p.b_events, new_df], ignore_index=True)
    p.b_events['time'] = p.b_events['time'].astype(float)

    p.b_events = p.b_events.reset_index(drop=True)