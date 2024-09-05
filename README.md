# Digital twin for accelerators

This Digital Twin framework is designed based on `EPICS` (Experimental Physics and Industrial Control System)  to simulate and monitor the performance of accelerators 
by integrating real-world machine data into a virtual representation. 
The system is designed in a way that it can use either `AT` or `Thor scsi lib` as back engine.
The system manages EPICS Process Variables (PVs) to control and simulate the behavior of various accelerator 
components like quadrupoles and sextupoles. 
It calculates twiss parameters, orbits, and BPM (Beam Position Monitor) 
results in response to changes in the machine's power converter values, and publishes these results as PVs.
## Requirements

* thor scsi lib: with its further requirements
    see https://github.com/jbengtsson/thor-scsi-lib for
    details

* AT: https://github.com/atcollab/at
* Epics:    https://github.com/epics-base/epics-base

* Installation:
    * pymongo
    * asyncio
    * numpy
    * p4p
    * bact-math-utils https://github.com/hz-b/bact-math-utils
    * See pyproject.toml for full details.

* Key Features:
    * Twiss and Orbit Calculations: Automatically triggers recalculations of twiss and orbit parameters when power converter values (e.g., quadrupoles) are updated. The results are published to specific PVs.
    * Real-Time BPM Monitoring: Beam Position Monitor (BPM) results are published to the PVs in real-time as the machine runs.
    * MongoDB Integration: Stores information about magnets and quadrupoles, including hardware-to-physics conversion (hw2phys) values, in MongoDB.
    * EPICS PV Management: Uses p4p (Python support for EPICS7 PVAccess) for creating and managing PVs, handling real-time updates.
    * Shadow Client: A client that reads power converter values from the real machine and synchronizes the corresponding Digital Twin PVs with the real-time data.
    * Element Proxy: Manages the updates and event-driven communication between machine elements (magnets) and their corresponding PVs, ensuring smooth data flow.
    * Event-Driven Updates: Uses an event-based system to trigger PV updates, ensuring efficient handling of changes and recalculations.

* Architectural Design Patterns

    The architecture of DT4ACC incorporates several best practices in software design patterns, allowing for a flexible, maintainable, and scalable system.

1. Command Pattern

At the heart of the architecture is the Command Pattern which is implemented in command.py. 
This pattern is used to encapsulate requests to update Process Variables (PVs) and decouple the update logic from the request handler. 
This pattern helps manage and execute the updates, events, and interactions between accelerator components and their corresponding PVs.
    * Key Features of Command Pattern:

  Encapsulates Update Logic: When a PV (e.g., Cm:set or im:I) is updated, command.py determines the appropriate action to process the update. It triggers recalculations for twiss, orbit, and BPM results as needed.
  Supports Bulk and Individual Updates: The command pattern is flexible enough to support 
  both individual PV updates and bulk updates, using the update() method.

2. Dependency Injection

    DT4ACC allows the use of multiple calculation engines (such as pyAT and thor_scsi) by leveraging the Dependency Injection pattern. 
    This pattern decouples the instantiation of specific calculation engines from the core logic, 
    allowing easy swapping or adding new engines.
    * How Dependency Injection Works:

       Flexible Calculation Engines: Different calculation engines, such as pyAT and thor_scsi, 
       can be used interchangeably thanks to this pattern. For example, pyat_accelerator.py and pyat_calculator.py 
       use this pattern to inject specific calculation logic into the broader workflow.
   * Ease of Adding New Engines: The architecture allows for easily adding more calculation engines in the future, 
   as they can be injected at runtime without needing to change the core logic.

3. Accelerator Setup Pattern

The Accelerator Setup Pattern is a novel approach for initializing the accelerator using data stored in MongoDB. 
This pattern has been specifically implemented for this project and was recently workshopped 
in the EUROplop 2024 conference (soon to be published).
    * Key Features:
        * MongoDB Integration: Accelerator components such as quadrupoles and sextupoles are initialized from the database, 
        which contains information like hw2phys values, and relevent power converter (as as it is structured in machine)
        making the setup process dynamic and database-driven.
        * P4P and EPICS Integration: The pattern utilizes p4p (Python support for EPICS7 PVAccess) 
        to create and manage PVs corresponding to each accelerator component, ensuring smooth communication 
        between the digital twin and real-world machine.

4. Twin State Synchronization Pattern

    The Twin State Synchronization Pattern is used to synchronize the state of the Digital Twin with the real machine. 
    This pattern is partially implemented through the shadow client, 
    which reads real-time power converter values from the machine and updates the corresponding Digital Twin PVs.
    This pattern has been specifically implemented for this project and was recently workshopped 
    in the EUROplop 2024 conference (soon to be published).
   * How It Works:
       * Real-Time Synchronization: The shadow client continuously monitors the real machine’s state 
       by reading power converter PVs and updating the corresponding PVs in the Digital Twin.
       * Ensures Consistency: The twin state synchronization ensures that the Digital Twin reflects
       the real-time behavior of the machine, providing a highly accurate virtual model.

5. Update Pattern

    The Update Pattern is closely integrated with the Command Pattern to handle PV updates in a structured and event-driven manner. 
    This pattern ensures that when a PV is updated (e.g., power converter values), 
    all related recalculations (twiss, orbit, BPM) are triggered efficiently.
    This pattern has been specifically implemented for this project and was recently workshopped 
    in the EUROplop 2024 conference (soon to be published).
   * Key Features:

       * Event-Driven Updates: Each time a PV value is updated, events are triggered to handle 
       recalculations of twiss parameters, orbits, and BPM results. 
       These events are managed asynchronously, ensuring smooth and responsive updates.
       * Optimized for Bulk Updates: In bulk update scenarios, the pattern ensures that events 
       are queued and processed efficiently without overloading the system.

* Main Components:
    * src/dt4acc/: The main folder containing the core modules of the Digital Twin framework.
        * setup_configuration/: Contains scripts related to setting up the PVs, server, and client configuration.
        * accelerators/: Modules handling the calculation engines.
        * calculator/: Modules handling various calculations.
        * bl/: Business logic that handles events and communication between different modules.
        * view/: Handles the presentation and output of the calculations (twiss, orbit, BPM) to the PVs.
        * scripts/: Contains scripts for database initialization, data import, and other utility functions.
* Key Files:
    * server.py: The main entry point for running the EPICS PV server, which initializes PVs and listens for changes.
    * shadow_client.py: A client that synchronizes the real machine’s power converter values with the corresponding Digital Twin PVs.
    * import_accelerator_data.py: A script for loading accelerator data, such as the hardware-to-physics conversion values, into MongoDB.
    * commmand.py: JSON file containing quadrupole-specific hardware-to-physics conversion values.

* Core Calculations: The calculations are triggered through events whenever there are any updates or changes in one or more power converter currents.
    * Twiss Calculation:
        * Twiss parameters are recalculated when the power converter PVs are updated. These include parameters such as alpha, beta, and nu for both x and y planes. The results are then published as PVs (e.g., twiss:alpha:x, twiss:beta:y).
    * Orbit Calculation:
        * Orbit calculation is triggered on updates to power converter values. Results are published as PVs (e.g., orbit:x, orbit:y, orbit:fixed_point).
    * BPM Data publishing:
        * Beam Position Monitors (BPM) record the beam’s x and y positions in the accelerator. This data is processed and published to corresponding PVs.
# Building the twin

1. clone the repository from HZB's gitlab e.g:

   ```shell
   git clone https://gitlab.helmholtz-berlin.de/acc-tools/dt4cc.git dt4acc
   ```

2. Install the project
   development installation 
   pip3 install -e .

3. Mongodb setup
   Ensure MongoDB is running and available. 
   Ensure lattice file is imported through lat2db project and your mongoDB contains the accelerator. 
   see (https://github.com/hz-b/lat2db)
   Import the quadrupole (at the moment only quad data is there)
   data from the JSON file into MongoDB using the import_accelerator_data.py script:

     ```shell
     python3 import_accelerator_data.py
     ```
4. Run the Server
   Start the EPICS PV server:

     ```shell
     python3 src/dt4acc/setup_configuration/server.py
     ```
   
5. Run the Shadow Client
   Run the shadow client to synchronize the real machine’s power converter values with the Digital Twin:

     ```shell
     python3 src/dt4acc/setup_configuration/shadow_client.py
     ```
   
6. Accessing the PVs
   You can use EPICS command-line tools like pvlist, pvget, and pvput to interact with the PVs exposed by the server:

     ```shell
     pvlist
     pvlist <list Hash>
     pvget pv_name
     pvput pv_name value (mainly pvs enging im:I are power converters)
     ```