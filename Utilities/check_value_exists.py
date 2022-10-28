# Define function that will check if a value exists in a dictionary
def check_value_exists(current_dict, value):
    exists = False
    for key, val in current_dict.items():
        if val == value:
            exists = True
    return exists