from config import *

import requests # For API calls
import json     # For JSON manipulation
import time     # For timestamp
import os       # For directory tests
import argparse # For command line arguments

#####################################################
### Function to print messages to standard output
#####################################################
def printFormat(typeMessage: str, Content:str):
    timestamp=(time.strftime("%H:%M:%S", time.localtime()))
    print(timestamp + ' | ' + typeMessage.ljust(7) + ' | ' + Content)
    return;

#####################################################
### Function to extract data and save it to a file
#####################################################
def extractObject(typeApi : str,typeObject: str,attributes=False,sublevel=False):

    response = requests.get(URI + typeApi+'/'+typeObject,headers=HEADER_AUTH,verify=VERIFY_SSL)

    if (response.status_code == 200 or response.status_code == 201):

        for json_obj in response.json():
            # Handling file names based on specificities
            if (attributes):
                # Take the entire tree and remove the last member which will be the file name
                pathfile = os.path.join(ROOT_PATH,typeObject.replace(typeObject.split('/')[-1],''))
                filename = typeObject.split('/')[-1]+'.json'

            else:
                pathfile = os.path.join(ROOT_PATH,typeObject+'/')
                if (typeObject == "calendars"):
                    filename = json_obj['name']+'-'+str(json_obj['year'])+'.json'
                elif (typeApi == GRAPH_URI and not attributes):
                    filename = 'graph.json'
                else:
                    filename = json_obj['name']+'.json'

            # Creating file only if result is not empty
            if (len(response.json()) > 0):
                if not (os.path.exists(pathfile)): # Create folder if not present
                    os.makedirs(pathfile)
                with open(pathfile+filename, 'w') as out_json_file:
                    if(attributes or (typeApi == GRAPH_URI and not attributes)): # If attributes or graph definitions then dump the content otherwise dump just the node
                        json.dump(response.json(), out_json_file, indent=4)
                    else:
                        json.dump(json_obj, out_json_file, indent=4)

            # Nested calls for dependent information or sublevels
            if (typeObject == 'agents'):
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/variables',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/alarms',True)
            elif (typeObject == 'dates'):
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/alarms',True)
            elif (typeObject == 'submitUnits'):
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/variables',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/agents',True)
            elif (typeObject == 'environments'):
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/dates',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/calendars',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/users',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/queues',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/submitUnits',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/contexts',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/variables',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/applications',sublevel=True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/alarms',True)
                extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']) # This call contains /properties + /nodes + link style
                extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']+'/properties',True)
                extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']+'/nodes',True)
            elif (typeObject.split('/')[-1] == 'applications' and sublevel):
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/links',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/contexts',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/variables',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/jobs',sublevel=True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/alarms',True)
                extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']) # This call contains /properties + /nodes + link style
                extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']+'/properties',True)
                extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']+'/nodes',True)
                extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']+'/node',True)
            elif (typeObject.split('/')[-1] == 'jobs' and sublevel):
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/links',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/contexts',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/variables',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/alarms',True)
                extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']+'/node',True)
            elif (typeObject == 'profiles'):
                extractObject(SECURITY_URI,typeObject+'/'+json_obj['name']+'/rights',True)

        if (len(response.json())>0 and not attributes): printFormat('SUCCESS','Extraction of '+typeObject+' ('+str(len(response.json()))+' extracted)')
        elif (not attributes): printFormat('SUCCESS','Extraction of '+typeObject+ ' (None)')
    elif (response.status_code == 500):
        ERRORS_LIST.append(typeApi+'/'+typeObject)
        printFormat('ERROR','Extraction of '+typeObject+'. Message: Error 500 Internal Server Error')
    else:
        ERRORS_LIST.append(typeApi+'/'+typeObject)
        printFormat('ERROR','Extraction of '+typeObject+'. Message: '+response.json()['message'])


#####################################################
### MAIN ###
#####################################################
# To avoid warnings on self-signed HTTPS
requests.packages.urllib3.disable_warnings()

# Variables
ERRORS_LIST = []

startTime = time.time()

printFormat('INFO','Starting export of VTOM configuration')
extractObject(CRUD_URI,'calendars')
extractObject(CRUD_URI,'users')
extractObject(CRUD_URI,'resources')
extractObject(CRUD_URI,'dates')
extractObject(CRUD_URI,'queues')
extractObject(CRUD_URI,'tokens')
extractObject(CRUD_URI,'agents')
extractObject(CRUD_URI,'submitUnits')
extractObject(CRUD_URI,'holidaysGroups')
extractObject(CRUD_URI,'holidays')
extractObject(CRUD_URI,'applicationServers/filesTransfers')
extractObject(CRUD_URI,'applicationServers/email')
extractObject(CRUD_URI,'applicationServers/amazonWebServices')
extractObject(CRUD_URI,'applicationServers/azure')
extractObject(CRUD_URI,'applicationServers/databases')
extractObject(CRUD_URI,'applicationServers/docker')
extractObject(CRUD_URI,'applicationServers/kubernetes')
extractObject(CRUD_URI,'applicationServers/m3')
extractObject(CRUD_URI,'applicationServers/dynamicsAx')
extractObject(CRUD_URI,'applicationServers/peopleSoft')
extractObject(CRUD_URI,'applicationServers/sapBo')
extractObject(CRUD_URI,'applicationServers/sapBw')
extractObject(CRUD_URI,'applicationServers/sapDs')
extractObject(CRUD_URI,'applicationServers/sapR3')
extractObject(CRUD_URI,'contexts')
extractObject(CRUD_URI,'environments')
extractObject(CRUD_URI,'alarms')
extractObject(GRAPH_URI,'properties',True)
extractObject(SECURITY_URI,'profiles')

executionTime = (time.time() - startTime)
printFormat('INFO','Execution time: {:.2f} seconds'.format(executionTime))
if len(ERRORS_LIST) > 0:
    printFormat('ERROR','The following API calls failed:')
    for error in ERRORS_LIST:
        print(error)
else:
    printFormat('SUCCESS','All API calls were successful')
