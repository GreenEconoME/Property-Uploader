# Import dependencies
import pandas as pd
from io import BytesIO

## Old for reference
# # Create a function that will take in the dataframes and create an excel workbook
# def create_workbook(created_props, props_failed_to_create, props_failed_w_prop_uses, successful_uploads):
#     data = BytesIO()

#     with pd.ExcelWriter(data) as writer:
#         created_props.to_excel(writer, sheet_name = 'Properties Created', index = False)
#         props_failed_to_create.to_excel(writer, sheet_name = 'Properties Failed to Create', index = False)
#         props_failed_w_prop_uses.to_excel(writer, sheet_name = 'Created Props Failed Uses', index = False)
#         successful_uploads.to_excel(writer, sheet_name = 'Created Props W Uses', index = False)

#     workbook = data.getvalue()

#     return workbook


# Create a function that will take in the dataframes and create an excel workbook
def create_workbook(dict_of_created_dfs):
    data = BytesIO()

    with pd.ExcelWriter(data) as writer:
        for key in dict_of_created_dfs.keys():
            current_df = dict_of_created_dfs[key].dtypes.astype(str)
            current_df.to_excel(writer, sheet_name = key, index = False)
            # dict_of_created_dfs[key].to_excel(writer, sheet_name = key, index = False)

    workbook = data.getvalue()

    return workbook