## Tally System Design Documentation

### Objective

Record, verify, and report data concerning election results.

* Record election results and reconcilliation data.
* Allow for verification and confirmation of election data.
* Produce reports and statistics regarding the election outcome.

### System Modules

#### Data entry interface

Support the entry of results and reconciliation forms

* Match entered serial number to stored form serial numbers.
* When reviewing this can be used to store an updated record.

#### Records
    
Store the form data entered into the system.

* State: store the current progress of the record through validation steps.
    * Intake
    * Clearance
    * Data Entry 1
    * Data Entry 2
    * Corrections
    * Quality Control
    * Auditing: failed quarantine checks
    * Archiving: passed quality control and quarantine checks but cover sheet not yet printed
    * Archived: final state
* Transitions: the possible transitions from the current state.
* Actions: the actions a user can perform.
    * Transitioning the form to a new state.
    * Updating the record by entering new data.
    * Printing a cover sheet for the record.

#### User permissions system

Assign roles for all users limiting their actions.

* All users must login with a name and password to access the tally system.
    * Each user is assigned a role.
    * Admins can reassign roles.
    * Admins can reset passwords to temporary passwords.
* Roles determine the actions that a user can perform.
* There are a fixed set of roles with predetermined actions.

#### Alerts
    
Run "quarantine checks" to ensure that entered data is credible.

* The system runs checks after a record passes the "quality control" state.
* If the quarantine checks fail a record goes to auditing.
* Admins can modify the quarantine checks.

#### Reporting

Display entry progress and the tally results.

* Display the percentage of forms entered to form expected.
    * Group by region and other metadata?
* Display the current state of all entered forms.
    * Group by region and other metadata?
* Display the sum of votes for each candidate in each election.
    *  Display the percentage of votes. 
