# Import dependencies
import requests
import xmltodict
import re
import pandas as pd
import streamlit as st
from Utilities.lookups import us_state_to_abbrev, prop_use_type_lookup, required_prop_uses

def create_properties(property_df, domain, headers, auth):
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
    # If the property was created, but failed to populate the property uses, save this information within this list
    props_failed_w_prop_uses = []
    # If the property was created and the property had a successful property use posting, save the information within this list
    successful_uploads = []
    
    # Loop through the property_df to upload each property
    for prop in property_df.index:
        #############
        # Create a dictionary that will contain the information from the order form
        # The order form data is stored in property_df
        building_data = {
            'name' : property_df.loc[prop, 'Property Name'],
            'primaryFunction' : property_df.loc[prop, 'Primary Function'], 
            'address1' : property_df.loc[prop, 'Street Address'], 
            'city' : property_df.loc[prop, 'City/Municipality'], 
            'postalCode' : property_df.loc[prop, 'Postal Code'], 
            'state' : us_state_to_abbrev[property_df.loc[prop, 'State/Province']], 
            'country' : 'US', 
            'yearBuilt' : int(property_df.loc[prop, 'Year Built']), 
            'constructionStatus' : 'Existing',
            'grossFloorArea' : int(property_df.loc[prop, 'Gross Floor Area']), 
            'occupancyPercentage' : int(property_df.loc[prop, 'Occupancy %']), 
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
        # Create a dicitonary of the current property that is being uploaded
        current_prop = dict(property_df.iloc[prop])
        try:
            create_prop = requests.post(domain + f'/account/{account_id}/property', 
                                        data = building_payload, 
                                        headers = headers, 
                                        auth = auth)

            # Parse the reponse
            creation_response = xmltodict.parse(create_prop.content)
            st.write(creation_response)
            # If the property creation request failed, then the id will not be retreivable and will exit the try block
            prop_id = creation_response['response']['id']

            # (DELETE AFTER TESTING) add prop to list to delete 
            props_created_during_testing.append(prop_id)

            # Add the ESPM ID to the building_data dictionary and add the dictionary to the list of created properties
            current_prop['ESPM ID'] = prop_id
            created_props.append(current_prop)
            
            ##########
            # Upload the property use details
            # If the property has been successfully created, begin uploading the property uses
            try:
                # Make the imported fields integers if they are populated
                for col in ['% Used for Cold Storage', '# of Walk-In Refrigerators', 
                            '% That Can Be Heated', '% That Can Be Cooled', 'Gross Floor Area', 
                            'Weekly Operating Hours', '# of Employees', '# of Computers', 
                            '# Of Bedrooms', '# Laundry Hookups All Units', 
                            '# Laundry Hookups in Common Area']:
                    if property_df.loc[prop, col] == property_df.loc[prop, col]:
                        property_df.loc[prop, col] = str(int(property_df.loc[prop, col]))

                # Check the clearheight to make and format it to be an integer
                if property_df.loc[prop, 'Clear Height'] == property_df.loc[prop, 'Clear Height']:
                    if type(property_df.loc[prop, 'Clear Height']) == str:
                        property_df.loc[prop, 'Clear Height'] = re.findall(r'\b\d+\b', property_df.loc[prop, 'Clear Height'])[0]
                    else:
                        property_df.loc[prop, 'Clear Height'] = int(property_df.loc[prop, 'Clear Height'])

                # Check if the property use type is an Office, if it is insert Office into the percentHeated and percentCooled keys
                if prop_use_type_lookup[property_df.loc[prop, 'Primary Function']] == 'office':
                    is_office = 'Office'
                    # Reformat the % heated columns based on accepted inputs
                    if int(property_df.loc[prop, '% That Can Be Heated']) >= 50:
                        property_df.loc[prop, '% That Can Be Heated'] = '50% or more'
                    elif int(property_df.loc[prop, '% That Can Be Heated']) == 0:
                        property_df.loc[prop, '% That Can Be Heated'] = 'Not Heated'
                    else:
                        property_df.loc[prop, '% That Can Be Heated'] = 'Less than 50%'
                    # Reformat the % cooled columns based on accepted inputs
                    if int(property_df.loc[prop, '% That Can Be Cooled']) >= 50:
                        property_df.loc[prop, '% That Can Be Cooled'] = '50% or more'
                    elif int(property_df.loc[prop, '% That Can Be Cooled']) == 0:
                        property_df.loc[prop, '% That Can Be Cooled'] = 'Not Air Conditioned'
                    else:
                        property_df.loc[prop, '% That Can Be Cooled'] = 'Less than 50%'
                else:
                    is_office = ''

                prop_use_dict = {
                                'useType' : prop_use_type_lookup[property_df.loc[prop, 'Primary Function']],
                                'totalGrossFloorArea' : property_df.loc[prop, 'Gross Floor Area'],
                                # 'numberOfResidentialLivingUnits' : property_df.loc[prop, 'Number of Units at the building'], 
                                'numberOfResidentialLivingUnits' : int(property_df.loc[prop, ['# Residential Units Low Rise', '# Residential Units Mid Rise', '# Residential Units High Rise']].fillna(0).sum()),
                                'weeklyOperatingHours' : property_df.loc[prop, 'Weekly Operating Hours'], 
                                'numberOfWorkers' : property_df.loc[prop, '# of Employees'], 
                                'numberOfComputers' : property_df.loc[prop, '# of Computers'], 
                                'percentUsedForColdStorage' : property_df.loc[prop, '% Used for Cold Storage'], 
                                'numberOfWalkInRefrigerationUnits' : property_df.loc[prop, '# of Walk-In Refrigerators'], 
                                'clearHeight' : property_df.loc[prop, 'Clear Height'], 
                                f'percent{is_office}Heated' : property_df.loc[prop, '% That Can Be Heated'], 
                                f'percent{is_office}Cooled' : property_df.loc[prop, '% That Can Be Cooled'],
                                'numberOfBedrooms' : property_df.loc[prop, '# Of Bedrooms'], 
                                'numberOfResidentialLivingUnitsMidRiseSetting' : property_df.loc[prop, '# Residential Units Low Rise'], 
                                'numberOfLaundryHookupsInAllUnits' : property_df.loc[prop, '# Laundry Hookups All Units'],
                                'numberOfLaundryHookupsInCommonArea' : property_df.loc[prop, '# Laundry Hookups in Common Area'], 
                                'numberOfResidentialLivingUnitsLowRiseSetting' : property_df.loc[prop, '# Residential Units Mid Rise'], 
                                'numberOfResidentialLivingUnitsHighRiseSetting' : property_df.loc[prop, '# Residential Units High Rise'], 
                                'residentPopulation' : property_df.loc[prop, 'Resident Population'], 
                                'governmentSubsidizedHousing' : property_df.loc[prop, 'Government Subsidized Housing'], 
                                'commonEntrance' : property_df.loc[prop, 'Common Entrance']
                            }
                           
                st.write(f"prop_use_dict for {property_df.loc[prop, 'Property Name']}")
                st.write(prop_use_dict)

                ##### Remove unused property uses by property type
                # Create a list to hold the keys of the available property uses
                all_prop_uses = list(prop_use_dict.keys())
                # Check to make sure the primary property type is within our required_prop_uses
                # If it is, remove the property uses that are not associated with the property type
                # If it is not, do not remove any uses (the error will say which property uses were expected)
                st.write(f'prop_use_dict["useType"] : {prop_use_dict["useType"]}')
                if prop_use_dict['useType'] in required_prop_uses.keys():
                    st.write('required prop uses: ' + f"{required_prop_uses[prop_use_type_lookup[property_df.loc[prop, 'Primary Function']]]}")
                    # Iterate through the property uses, if it is not a property use for that primary function, remove it, but do not remove the values required for the post
                    for prop_use in all_prop_uses:
                        if (prop_use not in required_prop_uses[prop_use_type_lookup[property_df.loc[prop, 'Primary Function']]]) and (prop_use not in ['totalGrossFloorArea', 'useType']):
                            del prop_use_dict[prop_use]

                # Create a list of the property uses that we will iterate through to create the xml payload for prop use population
                prop_uses = list(prop_use_dict.keys())
                prop_uses.remove('useType')

                # Create a list to append the portions of the xml strings to
                prop_use_payload = []

                # Append the static information to the prop_use_payload list
                prop_use_payload.append('<?xml version="1.0" encoding="UTF-8"?>')
                prop_use_payload.append(f'<{prop_use_dict["useType"]}>')
                prop_use_payload.append('<name>Building Use</name>')
                prop_use_payload.append('<useDetails>')

                # Iterate through the property uses and add them to the prop_use_payload list
                for use in prop_uses:
                    # Check to make sure the property use is not empty 
                    if prop_use_dict[use] == prop_use_dict[use]:
                        if use == 'clearHeight':
                            prop_use_payload.append(f'<{use} units = "Feet" temporary = "false">')
                        elif use == 'totalGrossFloorArea':
                            prop_use_payload.append(f'<{use} units = "Square Feet" temporary = "false">')
                        else:
                            prop_use_payload.append(f'<{use} temporary = "false">')
                        prop_use_payload.append(f'<value>{prop_use_dict[use]}</value>')
                        prop_use_payload.append(f'</{use}>')

                # Close out the static portions of the payload
                prop_use_payload.append('</useDetails>')
                prop_use_payload.append(f'</{prop_use_dict["useType"]}>')

                # Join the xml strings together with a newline 
                prop_use_payload = '\n'.join(prop_use_payload)

                # Post the property uses
                prop_use_post = requests.post(domain + f'/property/{prop_id}/propertyUse', 
                                              data = prop_use_payload, 
                                              headers = headers, 
                                              auth = auth)
                prop_use_response = xmltodict.parse(prop_use_post.content)

                # Check if the property uses were successfully posted
                if prop_use_post.status_code == 200 or prop_use_post.status_code == 201:
                    successful_uploads.append(current_prop)
                else:
                    st.write(prop_use_post.content)
                    # Save the Property use posting error to the dictionary
                    current_prop['Prop Uses Post Error'] = prop_use_response['response']['errors']['error']['@errorDescription']
                    # Remove the property from ESPM so it can be uploaded again with fixed property uses without creating a duplicate property
                    del_property = requests.delete(domain + f'/property/{prop_id}', 
                                                    headers = headers, 
                                                    auth = auth)
                    raise Exception(f"Property use post failure for property: {property_df.loc[prop, 'Property Name']}")
                    
            # If the property was created, but the property use post failed, add this information to the props_failed_w_prop_uses
            except Exception as e:
                st.write(e)
                # print(prop_use_response)
                
                props_failed_w_prop_uses.append(current_prop)
                
        # If the property creation post failed, append the building information to the list of properties that failed to be created
        except Exception as e:
            st.write(e)
            current_prop['Prop Creation Error'] = creation_response['response']['errors']['error']['@errorDescription']
            props_failed_to_create.append(current_prop)
    
    # (DELETE AFTER TESTING) print out the properties just created to delete
    st.write(props_created_during_testing)

    return pd.DataFrame(created_props), pd.DataFrame(props_failed_to_create), pd.DataFrame(props_failed_w_prop_uses), pd.DataFrame(successful_uploads)