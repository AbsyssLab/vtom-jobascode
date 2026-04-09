# Visual TOM JobAsCode
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE.md)&nbsp;
[![fr](https://img.shields.io/badge/lang-fr-yellow.svg)](README-fr.md)  

This repository provides a set of tools for implementing "JobAsCode" with Visual TOM.
As a reminder, the "JobAsCode" concept considers Jobs and related objects as code, following a version-controlled workflow.

The provided tools allow:
    * Preparing interaction settings for Visual TOM and Git
    * Generating code from an existing Visual TOM repository (extracting all objects in JSON format)
    * Updating the Visual TOM repository

# Disclaimer
No Support and No Warranty are provided by Absyss SAS for this project and related material. The use of this project's files is at your own risk.

Absyss SAS assumes no liability for damage caused by the usage of any of the files offered here via this Github repository.

Consultings days can be requested to help for the implementation.

# Prerequisites

    * Visual TOM 7.1 or higher
    * One VTOM server (source and/or target)
    * One local git repository (source and/or target)
    * (Recommended) A central Git repository (`origin`). Ex: GitHub, GitLab, Gitea...

For extracting the repository in JSON format in VCS (Git):
    * Python 3
    * Git

For updating the repository after a commit with Github:
    * Github Actions
    * Open flow between Github and Visual TOM API server

# Instructions
Both parts are related to JobAsCode but can be used/setup independently.

## Preparatory prerequisite validation
The `prepareJobAsCode.py` script prepares one side (`source` or `target`) at a time:
  * validation of selected VTOM server (API + Swagger/OpenAPI)
  * detection of available Domain API version (`/domain/x.y`)
  * local repository preparation (clone if missing, init if needed)
  * central `origin` remote alignment
  * `config.py` update (`config.py.template` is used if `config.py` is missing)
  * fallback to `config.py` values for `FQDN_HOSTNAME`, `API_KEY`, `GIT_ORIGIN`, `GIT_LOCAL`, `VERIFY_SSL`

Example (the script asks values interactively):
```bash
python3 prepareJobAsCode.py
```

Role (`source`/`target`) and all other values are prompted at runtime.
Defaults are prefilled from `config.py` when available.

Dry-run mode (no local write operations):
```bash
python3 prepareJobAsCode.py ... --dry-run
```

JSON summary output (for CI):
```bash
python3 prepareJobAsCode.py ... --output-json
```

JSON-only output (no log lines):
```bash
python3 prepareJobAsCode.py ... --json-only
```

## Extracting the repository in JSON format
When the repository already exists in Visual TOM, it is possible to extract it in JSON format and store it in a version control system.
  * Create an API token from Visual TOM interface with a strategy that has "Get" rights
  * `config.py` should already be prepared during the previous step, including:
    * `FQDN_HOSTNAME`: server name with the API server port
    * `API_KEY`: previously created API key
    * `VERIFY_SSL`: Enable or disable HTTPS certificate verification (by default, the certificate is self-signed and not valid)
    * `GIT_LOCAL`: local path used for extracted files and local repository
  * Run the script
    ```python3 exportAsCode.py```
    By default, export is import-friendly and skips aggregated graph snapshot files
    (`graph.json`, `nodes.json`) that are not needed for `importAsCode.py`.
    To include them (legacy/full graph export), use:
    ```bash
    python3 exportAsCode.py --full-graph-snapshots
    ```
  The output directory (`GIT_LOCAL`) is cleaned before extraction (the `.git` folder is preserved).
At the end of the execution, a summary will display any potential errors.
The directory structure follows the API URLs: objectType/objectName/subObjectType/subObjectName

### Limitations
* In case of manual updates in the repository and modifications in the versioning tool, conflicts may arise between local repositories.

## Updating the repository after a commit
When the repository is integrated with a version control tool, the repository can be automatically updated based on code updates.
The following steps work for Github, but the same approach applies to other versioning tools that support event-based actions.
* Create an API token from Visual TOM interface with a strategy that has "Post", "Put", and "Delete" rights on versioned objects
* Place the YAML file `vtom-jobascode-github.yml` in a `.github/workflows` directory
* The workflow calls `importAsCode.py` to process added/modified/deleted JSON files between commits and run POST/PUT/DELETE API operations

From this point on, any action performed on the repository will trigger an action to update the repository (except changes in .github/workflows folder).

### Executing the repository update action
Once you have configured the previous steps, you can execute the repository update action by following these steps:

1. Commit the repository with the code changes.
2. The repository update action will be automatically triggered (creation, modification, and/or deletion).
3. The action will retrieve the modified files from the repository and send them to the Visual TOM server using the API.
4. The Visual TOM repository will be updated with the code changes.

Make sure to check the action results to ensure that the repository update was successful.

### Running the import script manually
You can also run the import script outside Github Actions, for example for local tests (simulation mode by default):

```bash
python3 importAsCode.py --from <from-sha> --to <to-sha>
```

Real execution (API calls):

```bash
python3 importAsCode.py --from <from-sha> --to <to-sha> --run
```

### Limitations
* JSON files must adhere to the structure expected by the API server
* Domain, Graph, and Security objects are handled depending on the resource type
* Object order is defined in `config.py` (`IMPORT_ORDER_PREFIXES`)

# License
This project is licensed under the Apache 2.0 License - see the [LICENSE](license) file for details


# Code of Conduct
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-v2.1%20adopted-ff69b4.svg)](code-of-conduct.md)  
Absyss SAS has adopted the [Contributor Covenant](CODE_OF_CONDUCT.md) as its Code of Conduct, and we expect project participants to adhere to it. Please read the [full text](CODE_OF_CONDUCT.md) so that you can understand what actions will and will not be tolerated.
