from config import *

import argparse
import requests # For API calls
import json     # For JSON manipulation
import time     # For timestamp
import os       # For directory tests
import shutil
from vtom_common import API_PATHS, EXPORT_ROOT_OBJECTS, parse_message, print_format, request_vtom

CRUD_URI = API_PATHS["crud"]
GRAPH_URI = API_PATHS["graph"]
SECURITY_URI = API_PATHS["security"]
INCLUDE_GRAPH_SNAPSHOTS = False

#####################################################
### Function to print messages to standard output
#####################################################
import sys, logging

logging.basicConfig(

      level=logging.INFO,
      format='%(asctime)s | %(levelname)s | %(message)s',
      stream=sys.stdout,
      force=True
)
logger = logging.getLogger(__name__)


def clear_output_directory(base_dir: str) -> None:
    # Keep git metadata when GIT_LOCAL is itself a repository root.
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        return
    for entry in os.listdir(base_dir):
        if entry in (".git", ".github", "README.md", "README-fr.md"):
            continue
        entry_path = os.path.join(base_dir, entry)
        if os.path.isdir(entry_path) and not os.path.islink(entry_path):
            shutil.rmtree(entry_path)
        else:
            os.unlink(entry_path)

#####################################################
### Function to extract data and save it to a file
#####################################################
def extractObject(typeApi : str,typeObject: str,attributes=False,sublevel=False):
    try:
        response = request_vtom(
            method="GET",
            url=URI + typeApi+'/'+typeObject,
            headers=HEADER_AUTH,
            verify_ssl=VERIFY_SSL,
            timeout=30
        )
    except requests.exceptions.ConnectionError as err:
        ERRORS_LIST.append(typeApi+'/'+typeObject)
        logger.error(
            'Connection failed for ' + typeObject +
            '. Check FQDN_HOSTNAME/URI in config.py. Details: ' + str(err)
        )
        return
    except requests.exceptions.Timeout:
        ERRORS_LIST.append(typeApi+'/'+typeObject)
        logger.error(
            'Timeout for ' + typeObject +
            '. API did not respond within 30s.'
        )
        return

    if (response.status_code == 200 or response.status_code == 201):

        for json_obj in response.json():
            # Handling file names based on specificities
            if (attributes):
                # Take the entire tree and remove the last member which will be the file name
                pathfile = os.path.join(GIT_LOCAL,typeObject.replace(typeObject.split('/')[-1],''))
                filename = typeObject.split('/')[-1]+'.json'

            else:
                pathfile = os.path.join(GIT_LOCAL,typeObject+'/')
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
                extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']+'/properties',True)
                if INCLUDE_GRAPH_SNAPSHOTS:
                    extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']) # Aggregated graph snapshot
                    extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']+'/nodes',True)
            elif (typeObject.split('/')[-1] == 'applications' and sublevel):
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/links',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/contexts',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/variables',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/jobs',sublevel=True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/alarms',True)
                extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']+'/properties',True)
                extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']+'/node',True)
                if INCLUDE_GRAPH_SNAPSHOTS:
                    extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']) # Aggregated graph snapshot
                    extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']+'/nodes',True)
            elif (typeObject.split('/')[-1] == 'jobs' and sublevel):
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/links',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/contexts',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/variables',True)
                extractObject(CRUD_URI,typeObject+'/'+json_obj['name']+'/alarms',True)
                extractObject(GRAPH_URI,typeObject+'/'+json_obj['name']+'/node',True)
            elif (typeObject == 'profiles'):
                extractObject(SECURITY_URI,typeObject+'/'+json_obj['name']+'/rights',True)

        if (len(response.json())>0 and not attributes): logger.info('Extraction of '+typeObject+' ('+str(len(response.json()))+' extracted)')
        elif (not attributes): logger.info('Extraction of '+typeObject+ ' (None)')
    elif (response.status_code == 500):
        ERRORS_LIST.append(typeApi+'/'+typeObject)
        logger.error('Extraction of '+typeObject+'. Message: Error 500 Internal Server Error')
    else:
        ERRORS_LIST.append(typeApi+'/'+typeObject)
        logger.error('Extraction of '+typeObject+'. Message: ' + parse_message(response))


#####################################################
### MAIN ###
#####################################################
# To avoid warnings on self-signed HTTPS
requests.packages.urllib3.disable_warnings()

parser = argparse.ArgumentParser(
    description="Export Visual TOM objects to JSON files.",
)
parser.add_argument(
    "--full-graph-snapshots",
    action="store_true",
    help="Also export aggregated graph snapshot files (graph.json, nodes.json). "
         "By default, export is import-friendly and skips them.",
)
args = parser.parse_args()

# Variables
ERRORS_LIST = []
INCLUDE_GRAPH_SNAPSHOTS = args.full_graph_snapshots

startTime = time.time()

logger.info('Starting export of VTOM configuration')
if INCLUDE_GRAPH_SNAPSHOTS:
    logger.info('Mode: full graph snapshots enabled')
else:
    logger.info('Mode: import-friendly (graph.json/nodes.json skipped)')
logger.info(f'Cleaning output directory: {GIT_LOCAL}')
clear_output_directory(GIT_LOCAL)
for object_name in EXPORT_ROOT_OBJECTS:
    extractObject(CRUD_URI, object_name)
extractObject(GRAPH_URI,'properties',True)
extractObject(SECURITY_URI,'profiles')

executionTime = (time.time() - startTime)
logger.info('Execution time: {:.2f} seconds'.format(executionTime))
if len(ERRORS_LIST) > 0:
    logger.error('The following API calls failed:')
    for error in ERRORS_LIST:
        print(error)
else:
    logger.info('All API calls were successful')
