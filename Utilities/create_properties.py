# Import dependencies
import requests
import xmltodict
import pandas as pd
import streamlit as st
from Utilities.lookups import us_state_to_abbrev, prop_use_type_lookup, required_prop_uses, epa_ids
from Utilities.check_value_exists import check_value_exists

def create_properties(order_form, auto_delete, reference_dict):
    # Create variables to hold the espm credentials
    auth = tuple(reference_dict['espm_config']['auth'])
    domain = reference_dict['espm_config']['domain']
    headers = reference_dict['espm_config']['headers']

    # (DELETE AFTER TESTING) Creating a list to hold the property ids of the buildings created to delete while testing
    props_created_during_testing = []

    ##############
    # Make a call to get the account id for the ESPM account
    response = requests.get(domain + '/account', 
                            auth = auth)
    response_dict = xmltodict.parse(response.content)
    # Save the ESPM account id as account_id
    account_id = response_dict['account']['id']
    
    #############
    # Create variables to track what was accomplished
    # Create created_props to contain the data that we used to create the property, with the new ESPM id
    created_props = []
    # If the property failed to be created, store this information within this list
    props_failed_to_create = []
    # Create a list to hold the pre-existing properties that will not be created
    pre_existing_properties = []
    # Create a list to hold the zoho building upload data
    zoho_buildings = []


    # Loop through the order_form to upload each property
    for prop in order_form.index:
        #############
        # Create a dicitonary of the current property that is being uploaded
        current_prop = dict(order_form.iloc[prop])

        # Check to see if the property is pre-exisisting if it is then add it to the pre_existing_properties list
        if check_value_exists(current_prop, 'N/A - Existing Bldg'):
            pre_existing_properties.append(current_prop)

        # If the property has not already been created, create the property
        else:
            # Create a dictionary that will contain the information from the order form using the ESPM values as keys
            # The order form data is stored in order_form
            building_data = {
                'name' : order_form.loc[prop, 'Property Name'],
                'primaryFunction' : order_form.loc[prop, 'Primary Property Use'].strip(), 
                'address1' : order_form.loc[prop, 'Street Address'], 
                'city' : order_form.loc[prop, 'City/Municipality'], 
                'postalCode' : order_form.loc[prop, 'Postal Code'], 
                'state' : us_state_to_abbrev[order_form.loc[prop, 'State/Province']], 
                'country' : 'US', 
                'yearBuilt' : int(order_form.loc[prop, 'Year Built']), 
                'constructionStatus' : 'Existing',
                'grossFloorArea' : int(order_form.loc[prop, 'Gross Floor Area']), 
                'occupancyPercentage' : int(order_form.loc[prop, 'Occupancy %']), 
                'isFederalProperty' : 'false', 
            }

            #############
            # Since not all the features for the XML package are not formatted the same
            # Break apart the keys that have their own format for the XML
            added_alone = ['name', 'primaryFunction', 'yearBuilt', 
                        'constructionStatus', 'occupancyPercentage', 
                        'isFederalProperty']
            address_keys = ['address1', 'city', 'postalCode', 
                            'state', 'country']
            has_units = ['grossFloorArea']

            # Create the building payload to create this building
            # @TODO Should make this a function to take the three lists as input and return the xml payload
            building_payload = ''
            building_payload += '<?xml version="1.0" encoding="UTF-8"?><property>'
            # Add the properties that are justy the key
            for key in added_alone:
                building_payload += f'<{key}>{building_data[key]}</{key}>'
            # Add the address
            building_payload += '<address ' + ' '.join([f'{x}="{building_data[x]}"' for x in address_keys]) + '/>'
            # Add the metrics that need Square Foot
            for i in range(len(has_units)):
                building_payload += f'<{has_units[i]} temporary="false" units="Square Feet">'
                building_payload += f'<value>{building_data[has_units[i]]}</value>'
                building_payload += f'</{has_units[i]}>'
            building_payload += '</property>'

            #############
            # Make a Post to create the property
            
            try:
                create_prop = requests.post(domain + f'/account/{account_id}/property', 
                                            data = building_payload, 
                                            headers = headers, 
                                            auth = auth)

                # Parse the reponse
                creation_response = xmltodict.parse(create_prop.content)
                # st.write(creation_response)
                # If the property creation request failed, then the id will not be retreivable and will exit the try block
                if create_prop.status_code == 201:
                    st.write(f"Successful creation of property: {building_data['name']}")
                else:
                    st.write(f"Error creating property: {building_data['name']}")
                    st.write(creation_response)
                prop_id = creation_response['response']['id']

                # (DELETE AFTER TESTING) add prop to list to delete 
                props_created_during_testing.append(prop_id)

                # Add the ESPM ID to the building_data dictionary and add the dictionary to the list of created properties
                current_prop['ESPM ID'] = prop_id
                created_props.append(current_prop)
                
                    
            # If the property creation post failed, append the building information to the list of properties that failed to be created
            except Exception as e:
                st.write(e)
                current_prop['Prop Creation Error'] = creation_response['response']['errors']['error']['@errorDescription']
                props_failed_to_create.append(current_prop)

            # Add the Unique identifiers
            # Ensure the property was created by checking if the ESPM ID has been added to the current property
            if 'ESPM ID' in current_prop:
                # Post the LADBS ID as a unique identifier
                ladbs_id = order_form.loc[prop, 'LADBS ID']
                ladbs_id = str(ladbs_id).replace('.0', '')
                # Check if the LADBS ID is populated, if it is post it as a unique identifier
                if ladbs_id == ladbs_id:
                    # Create the XML to post the LADBS ID
                    la_id_payload = '<?xml version="1.0" encoding="UTF-8"?><additionalIdentifier>'
                    la_id_payload += f'<additionalIdentifierType ' + 'id="' + f"{epa_ids['Los Angeles Building ID']}" +'"/>'
                    la_id_payload += f'<value>{ladbs_id}</value>'
                    la_id_payload += '</additionalIdentifier>'
                    # Post the LADBS ID
                    la_id_req = requests.post(domain + f'/property/{prop_id}/identifier', 
                                                data = la_id_payload, 
                                                headers = headers, 
                                                auth = auth)
                    # st.write(f'la_id_req: {la_id_req.content}')

                # Post the Portfolio ID as Custom ID 1
                col_name = order_form.filter(like='Property Code').columns[0]
                portfolio_prop_code = order_form.loc[prop, col_name]
                if portfolio_prop_code == portfolio_prop_code:
                    # Create the XML to post the portfolio property ID
                    port_prop_payload = '<?xml version="1.0" encoding="UTF-8"?><additionalIdentifier>'
                    port_prop_payload += f'<additionalIdentifierType ' + 'id="' + f"{epa_ids['Custom ID 1']}" +'"/>'
                    port_prop_payload += f'<value>{portfolio_prop_code}</value>'
                    port_prop_payload += f'<description>{col_name}</description>'
                    port_prop_payload += '</additionalIdentifier>'
                    # Post the portfolio property ID
                    port_id_req = requests.post(domain + f'/property/{prop_id}/identifier', 
                                                data = port_prop_payload, 
                                                headers = headers, 
                                                auth = auth)
                    # st.write(f'port_id_req: {port_id_req.content}')

                # If the auto_delete checkbox is selected, delete the property
                if auto_delete:
                    requests.delete(domain + f'/property/{prop_id}', 
                                    headers = headers, 
                                    auth = auth)

                # Create the Zoho building upload data for this property
                zoho_dict = {}
                # Change nans to empty strings
                for key, value in current_prop.items():
                    if value != value:
                        current_prop[key] = ''
                reference_dict['who_pays'][''] = ''

                # Create a dictionary to hold the zoho data for the current building
                zoho_data = {
                            'Building Id': '',
                            'Building Name': current_prop['Property Name'],
                            'Building Owner': reference_dict['variables']['building_owner'],
                            'Building Owner ID': reference_dict['variables']['building_owner_id'],
                            'Email': reference_dict['emails'][current_prop['Property Manager']],
                            'Created By': '',
                            'Created by ID': '',
                            'Modified By': '',
                            'Modified by ID': '',
                            'Created Time': '',
                            'Modified Time': '',
                            'Last Activity Time': '',
                            'Tag': '',
                            'Primary Contact': reference_dict['emails'][current_prop['Property Manager']],
                            'Total Square Footage of the Building': current_prop['Gross Floor Area'],
                            'Who pays the electric bills?': reference_dict['who_pays'][current_prop['Who Pays Electric Bills?']],
                            'Year Built': current_prop['Year Built'],
                            'Property Use Type': current_prop['Primary Property Use'],
                            'Number of Units': current_prop['Number of Units at the building'],
                            'DBS Building ID': current_prop['LADBS ID'],
                            'Follow Up Date': '',
                            'Order Type': reference_dict['variables']['order_type'],
                            'Account (Building Owner)': reference_dict['variables']['account_id'],
                            'Current Energy Star Score': '',
                            'Current Benchmarking Year': '',
                            'Phase 2 Due Date': '',
                            'Source': '',
                            'Current Opportunity': '',
                            'Portfolio': reference_dict['variables']['portfolio'],
                            'Benchmark Group': '',
                            'Solar PVs': '',
                            'Owner Pays for Common Area': '',
                            'Who pays the gas bill?': reference_dict['who_pays'][current_prop['Who Pays Gas Bills?']],
                            'Who pays the water bill?': reference_dict['who_pays'][current_prop['Who Pays Water Bills?']],
                            'Unsubscribed Mode': '',
                            'Unsubscribed Time': '',
                            'Record Id': '',
                            'Gas Utility Provider': current_prop['Gas Utility Provider'],
                            'Water Utility Provider': current_prop['Water Utility Provider'],
                            'Electric Utility Provider': current_prop['Electric Utility Provider'],
                            'Benchmarking Contact': '',
                            'Current Water Score (MF)': '',
                            'Onsite Contact': '',
                            'Survey Submitted': '',
                            'Survey Submitted Due Time': '',
                            'ESPM Property ID': current_prop['ESPM ID'],
                            'AD Notes (MS)': '',
                            'Building Status': reference_dict['variables']['building_status']
                            }

                zoho_buildings.append(zoho_data)


    # (DELETE AFTER TESTING) print out the properties just created to delete
    st.write('ESPM IDs of successfully created properties:')
    st.write(props_created_during_testing)

    return pd.DataFrame(created_props), pd.DataFrame(props_failed_to_create), pd.DataFrame(pre_existing_properties), pd.DataFrame(zoho_buildings)