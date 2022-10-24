# Import dependencies
import pandas as pd
from io import BytesIO

# Create a function that will take in the dataframes and create an excel workbook
def create_workbook(created_props, props_failed_to_create, props_failed_w_prop_uses, successful_uploads):
    data = BytesIO()

    with pd.ExcelWriter(data) as writer:
        created_props.to_excel(writer, sheet_name = 'Properties Created', index = False)
        props_failed_to_create.to_excel(writer, sheet_name = 'Properties Failed to Create', index = False)
        props_failed_w_prop_uses.to_excel(writer, sheet_name = 'Created Props Failed Uses', index = False)
        successful_uploads.to_excel(writer, sheet_name = 'Created Props W Uses', index = False)

    workbook = data.getvalue()

    return workbook