# Import dependencies
import requests
import xmltodict
import re
import pandas as pd
import streamlit as st
from Utilities.lookups import us_state_to_abbrev, prop_use_type_lookup, required_prop_uses

# @TODO Need to have ESPM ID added to the building details form
# @TODO Removed from the create properties function - refactor code to accomidate new format from returned building details forms

def upload_prop_uses(building_details, domain, headers, auth):

    # If the property was created, but failed to populate the property uses, save this information within this list
    props_failed_w_prop_uses = []
    # If the property was created and the property had a successful property use posting, save the information within this list
    successful_uploads = []

    for prop in building_details.index:
        current_prop = dict(building_details.iloc[prop])
        # Make the imported fields integers if they are populated
        try:
            for col in ['% Used for Cold Storage', '# of Walk-In Refrigerators', 
                        '% That Can Be Heated', '% That Can Be Cooled', 'Gross Floor Area', 
                        'Weekly Operating Hours', '# of Employees', '# of Computers', 
                        '# Of Bedrooms', '# Laundry Hookups All Units', 
                        '# Laundry Hookups in Common Area']:
                if building_details.loc[prop, col] == building_details.loc[prop, col]:
                    building_details.loc[prop, col] = str(int(building_details.loc[prop, col]))

            # Check the clearheight to make and format it to be an integer
            if building_details.loc[prop, 'Clear Height'] == building_details.loc[prop, 'Clear Height']:
                if type(building_details.loc[prop, 'Clear Height']) == str:
                    building_details.loc[prop, 'Clear Height'] = re.findall(r'\b\d+\b', building_details.loc[prop, 'Clear Height'])[0]
                else:
                    building_details.loc[prop, 'Clear Height'] = int(building_details.loc[prop, 'Clear Height'])

            # Check if the property use type is an Office, if it is insert Office into the percentHeated and percentCooled keys
            if prop_use_type_lookup[building_details.loc[prop, 'Primary Property Use']] == 'office':
                is_office = 'Office'
                # Reformat the % heated columns based on accepted inputs
                if int(building_details.loc[prop, '% That Can Be Heated']) >= 50:
                    building_details.loc[prop, '% That Can Be Heated'] = '50% or more'
                elif int(building_details.loc[prop, '% That Can Be Heated']) == 0:
                    building_details.loc[prop, '% That Can Be Heated'] = 'Not Heated'
                else:
                    building_details.loc[prop, '% That Can Be Heated'] = 'Less than 50%'
                # Reformat the % cooled columns based on accepted inputs
                if int(building_details.loc[prop, '% That Can Be Cooled']) >= 50:
                    building_details.loc[prop, '% That Can Be Cooled'] = '50% or more'
                elif int(building_details.loc[prop, '% That Can Be Cooled']) == 0:
                    building_details.loc[prop, '% That Can Be Cooled'] = 'Not Air Conditioned'
                else:
                    building_details.loc[prop, '% That Can Be Cooled'] = 'Less than 50%'
            else:
                is_office = ''

            prop_use_dict = {
                            'useType' : prop_use_type_lookup[building_details.loc[prop, 'Primary Property Use']],
                            'totalGrossFloorArea' : building_details.loc[prop, 'Gross Floor Area'],
                            # 'numberOfResidentialLivingUnits' : building_details.loc[prop, 'Number of Units at the building'], 
                            'numberOfResidentialLivingUnits' : int(building_details.loc[prop, ['# Residential Units Low Rise', '# Residential Units Mid Rise', '# Residential Units High Rise']].fillna(0).sum()),
                            'weeklyOperatingHours' : building_details.loc[prop, 'Weekly Operating Hours'], 
                            'numberOfWorkers' : building_details.loc[prop, '# of Employees'], 
                            'numberOfComputers' : building_details.loc[prop, '# of Computers'], 
                            'percentUsedForColdStorage' : building_details.loc[prop, '% Used for Cold Storage'], 
                            'numberOfWalkInRefrigerationUnits' : building_details.loc[prop, '# of Walk-In Refrigerators'], 
                            'clearHeight' : building_details.loc[prop, 'Clear Height'], 
                            f'percent{is_office}Heated' : building_details.loc[prop, '% That Can Be Heated'], 
                            f'percent{is_office}Cooled' : building_details.loc[prop, '% That Can Be Cooled'],
                            'numberOfBedrooms' : building_details.loc[prop, '# Of Bedrooms'], 
                            'numberOfResidentialLivingUnitsMidRiseSetting' : building_details.loc[prop, '# Residential Units Low Rise'], 
                            'numberOfLaundryHookupsInAllUnits' : building_details.loc[prop, '# Laundry Hookups All Units'],
                            'numberOfLaundryHookupsInCommonArea' : building_details.loc[prop, '# Laundry Hookups in Common Area'], 
                            'numberOfResidentialLivingUnitsLowRiseSetting' : building_details.loc[prop, '# Residential Units Mid Rise'], 
                            'numberOfResidentialLivingUnitsHighRiseSetting' : building_details.loc[prop, '# Residential Units High Rise'], 
                            'residentPopulation' : building_details.loc[prop, 'Resident Population'], 
                            'governmentSubsidizedHousing' : building_details.loc[prop, 'Government Subsidized Housing'], 
                            'commonEntrance' : building_details.loc[prop, 'Common Entrance']
                        }
                        
            st.write(f"prop_use_dict for {building_details.loc[prop, 'Property Name']}")
            st.write(prop_use_dict)

            ##### Remove unused property uses by property type
            # Create a list to hold the keys of the available property uses
            all_prop_uses = list(prop_use_dict.keys())
            # Check to make sure the primary property type is within our required_prop_uses
            # If it is, remove the property uses that are not associated with the property type
            # If it is not, do not remove any uses (the error will say which property uses were expected)
            st.write(f'prop_use_dict["useType"] : {prop_use_dict["useType"]}')
            if prop_use_dict['useType'] in required_prop_uses.keys():
                st.write('required prop uses: ' + f"{required_prop_uses[prop_use_type_lookup[building_details.loc[prop, 'Primary Property Use']]]}")
                # Iterate through the property uses, if it is not a property use for that Primary Property Use, remove it, but do not remove the values required for the post
                for prop_use in all_prop_uses:
                    if (prop_use not in required_prop_uses[prop_use_type_lookup[building_details.loc[prop, 'Primary Property Use']]]) and (prop_use not in ['totalGrossFloorArea', 'useType']):
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

            # Get the ESPM property ID to post the property use details
            prop_id = building_details.loc[prop, 'ESPM ID']

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
                raise Exception(f"Property use post failure for property: {building_details.loc[prop, 'Property Name']}")
                
        # If the property was created, but the property use post failed, add this information to the props_failed_w_prop_uses
        except Exception as e:
            st.write(e)
            
            props_failed_w_prop_uses.append(current_prop)

    return pd.DataFrame(props_failed_w_prop_uses), pd.DataFrame(successful_uploads)