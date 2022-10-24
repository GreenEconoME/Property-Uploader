# Import dependencies
import streamlit as st
import pandas as pd

from Utilities.create_properties import create_properties
from Utilities.create_workbook import create_workbook

# Set a title for the page
st.markdown("<h1 style = 'text-align: center; color: green;'>Green EconoME</h1>", unsafe_allow_html = True)
st.markdown("<h2 style = 'text-align: center; color: black;'>Property Uploader</h2>", unsafe_allow_html = True)

# Set the domain and headers for the API calls
domain = 'https://portfoliomanager.energystar.gov/ws'
headers = {'Content-Type': 'application/xml'}

# Load credentials for the API calls into the auth variable
credential_upload = st.file_uploader('Upload ESPM API Credentials')
if credential_upload:
    creds = []
    for line in credential_upload:
        creds.append(line.decode().strip())
    auth = (creds[0], creds[1])

st.caption('Upload the API credentials within a .txt file with the Username and Password on seperate lines. <br>' + 
            'The .txt file should be of the following format:<br>' + 
            'Username<br>' + 
            'Password', unsafe_allow_html = True)

# Add a file uploader to upload the building survey
building_survey = st.file_uploader('Upload the Building Survey Spreadsheet')

# Create a boolean to use to only call the download when the properties have finished uploading
complete_upload = False

# Check to make sure the required fields are populated
if credential_upload and building_survey is not None:
    if st.button('Upload Properties'):
        with st.spinner('Uploading Properties'):
            
        
            # Read in the worksheets containing the order form and the propery use details
            order_form = pd.read_excel(building_survey, 
                                        sheet_name = 'Order Form', 
                                        skiprows = 7)
            building_details = pd.read_excel(building_survey, 
                                         sheet_name = 'Building Details', 
                                         skiprows = 7)
            # Merge the two worksheets together
            property_df = order_form.merge(building_details, on = 'Property Name')

            # Drop the empty columns (inserted into the building survey for formatting)
            empty_cols = []
            for x in property_df.columns:
                if 'Unnamed' in x:
                    empty_cols.append(x)
            property_df.drop(columns = empty_cols, inplace = True)

            # Call the create_properties function to create each building and populate the property uses
            (created_props, props_failed_to_create, 
            props_failed_w_prop_uses, successful_uploads) = create_properties(property_df, domain, headers, auth)

            # Create a workbook containing the successful/unsuccessful uploads
            workbook = create_workbook(created_props, props_failed_to_create, props_failed_w_prop_uses, successful_uploads)

            # Update the complete_upload
            complete_upload = True

    # If the properties have finished uploading
    if complete_upload:
        
        st.download_button(label = 'Download Property Upload Results', 
                            data = workbook, 
                            file_name = 'Property Upload Results.xlsx')
        

