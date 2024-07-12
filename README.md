# Visual TOM JobAsCode
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE.md)&nbsp;
[![fr](https://img.shields.io/badge/lang-fr-yellow.svg)](README-fr.md)  

This repository provides a set of tools for implementing "JobAsCode" with Visual TOM.
As a reminder, the "JobAsCode" concept considers Jobs and related objects as code, following a version-controlled workflow.

The provided tools cover two aspects:
    * Generating code from an existing Visual TOM repository (extracting all objects in JSON format)
    * Updating the Visual TOM repository upon a commit

# Disclaimer
No Support and No Warranty are provided by Absyss SAS for this project and related material. The use of this project's files is at your own risk.

Absyss SAS assumes no liability for damage caused by the usage of any of the files offered here via this Github repository.

Consultings days can be requested to help for the implementation.

# Prerequisites

    * Visual TOM 7.1 or higher

For extracting the repository in JSON format:
    * Python 3

For updating the repository after a commit:
    * Github Actions
    * Open flow between Github and Visual TOM API server

# Instructions
Both parts are related to JobAsCode but can be used/setup independently.

## Extracting the repository in JSON format
When the repository already exists in Visual TOM, it is possible to extract it in JSON format and store it in a version control system.
    * Create an API token from Visual TOM interface with a strategy that has "Get" rights
    * Fill in the config.py file:
        * `FQDN_HOSTNAME`: server name with the API server port
        * `API_KEY`: previously created API key
        * `VERIFY_SSL`: Enable or disable HTTPS certificate verification (by default, the certificate is self-signed and not valid)
        * `ROOT_PATH`: path where the extracted files will be stored
    * Run the script
    ```python3 exportAsCode.py```
At the end of the execution, a summary will display any potential errors.
The directory structure follows the API URLs: objectType/objectName/subObjectType/subObjectName

The script does not delete files in the output directory before generating new files. This means that if objects have been deleted from the Visual TOM repository, the files will still be present. Depending on the needs, it may be necessary to add a preliminary step to empty the directory.

### Limitations
* In case of manual updates in the repository and modifications in the versioning tool, conflicts may arise between local repositories.

## Updating the repository after a commit
When the repository is integrated with a version control tool, the repository can be automatically updated based on code updates.
The following steps work for Github, but the reasoning remains the same with other versioning tools as long as they support "event-based actions".
* Create an API token from Visual TOM interface with a strategy that has "Post", "Put", and "Delete" rights on versioned objects
* Create a variable `VTOM_SERVER_NAME` in the Github repository (Settings / Secrets and variables / Actions / Variables / New repository variable) with the value as the Visual TOM server name with the port
* Create a secret `VTOM_TOKEN` in the Github repository (Settings / Secrets and variables / Actions / Secrets / New repository secret) with the value as the API token
* Place the YAML file `vtom-jobascode.yml` in a `.github/workflows` directory

From this point on, any action performed on the repository will trigger an action to update the repository (except changes in .github/workflows folder).

### Executing the repository update action
Once you have configured the previous steps, you can execute the repository update action by following these steps:

1. Commit the repository with the code changes.
2. The repository update action will be automatically triggered (creation, modification, and/or deletion).
3. The action will retrieve the modified files from the repository and send them to the Visual TOM server using the API.
4. The Visual TOM repository will be updated with the code changes.

Make sure to check the action results to ensure that the repository update was successful.

### Limitations
* JSON files must adhere to the structure expected by the API server
* Only "Domain" objects are considered
* Order constraints between objects are not taken into account (e.g., Agents before Submission Units)

# License
This project is licensed under the Apache 2.0 License - see the [LICENSE](license) file for details


# Code of Conduct
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-v2.1%20adopted-ff69b4.svg)](code-of-conduct.md)  
Absyss SAS has adopted the [Contributor Covenant](CODE_OF_CONDUCT.md) as its Code of Conduct, and we expect project participants to adhere to it. Please read the [full text](CODE_OF_CONDUCT.md) so that you can understand what actions will and will not be tolerated.
