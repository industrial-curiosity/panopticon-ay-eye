# Glossary

* Interface: a mechanism that can be produced to or consumed from, eg. REST endpoint, queue, gRPC endpoint, etc.
* Panopticon repo: a template repo that contains all the tools needed
* Master repo / Panopticon instance: a private forked repository that also includes its repository documentation and interface index

# New project

The org owner creates a private fork of the Panopticon repo. This will be used as the knowledge base for the organization’s repos, as well as for customizing its shared workflows and skills.

Workflows:

* PR evaluation
  * Check repo initialized with Panopticon
  * Check changes in PR reflected in documentation
  * Check interfaces\* for conflicts with master repo
* Merge to master
  * Copy repo docs to master repo
  * Merge local interfaces into interfaces index

# Local

## Initialize documentation

We initialize a repo by running a script that’s run directly from the instance fork.
The script does the following:

* Sets up the repo’s workflows to use the shared workflows. Each repo needs CI access to PANOPTICON\_LLM\_API\_KEY and PANOPTICON\_LLM\_ENDPOINT secrets which the agents will use.
* Uses Panopticon skills to generate documentation for the repository.
* Adds a file that indicates that the repo has been initialized.

## Plan

When planning a change, the agent should be able to read the interface\* index (with the github cli or mcp, using the developer’s personal GITHUB\_TOKEN) to verify whether any interface connections are affected.

# PR workflow

* Check repo documentation initialized (does flag file exist)
* Check if code or configuration changes have been made that should affect documentation
* Check if documentation updated accordingly
* Check if interface\* changes conflict with the master repo index

# Merge into master

* Copy docs into master repo’s docs/{repo} folders
* Read interface\* index
* Merge interface changes into the index

# The interfaces\* index

* Each repo includes its own index.
* The repo is the authoritative source for whatever interfaces it owns.
* The index is keyed on the interface name
  * A meaningful name based on its use or function
* Each index key is an array of interface objects
  * Owner (“null” if unknown or manually created infra, otherwise repo and component)
  * Consumer / Producer (booleans)
  * Type (eg. kafka, REST, gRPC, S3)
  * Source file array (creating the interface, configuring instances eg. prod/staging)
* Unknowns / conflicts
  * When a repo is a consumer of external interfaces but not the owner
    * Checks for existing entry, checks to see if its values make sense
    * If it finds a match, ensures its producer/consumer state set correctly
    * If it’s not a clear match, adds a conflict entry
  * When a repo is the owner
    * Checks for existing entry
    * If it finds a match, checks for inaccuracies
    * If it’s not a clear match, adds a conflict entry
  * If there are conflicts, log and warn in the CI summary
