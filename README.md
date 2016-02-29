Maestro is a tool used to create virtual machines either on single-case basis, or through bulk by uploading a csv whose columns matches the fields in the web form. Validation happens on submit and returns back on failure. If validation is successful, an iso is created and stored in /opt/isos, which vmware has mounted across all datastores (in theory).

This tool is and probably always will be a work in progress. 

The current state is:
1. Requires a webserver restart after every run in order to refresh the state of vmware. This is partially intentional, since reloading the state of vmware takes a while.  A fix would require either a service that holds the state of the environment (could take a lot of work), or have a data refresh thread. Not sure which is better.
2. The code's moderately messy still. Structurally it's okay, but it's not ideal. For example, the retrievers and validators.py can call each other, which creates odd multiple mysql connections. Blech.
3. Validation output is in the following form: Anything within the brackets are items that failed validation. 
4. Because of the order of the orchestrator workflow, DNS gets added after the VM starts the kickstart process. This is a problem because of #1, where if a VM kickstart fails, validation thinks the VM doesn't exist, when it does.
5. It does *not* write to ipplan yet. Hoping Joe could have a look at this part.

Workflow:
1. User submits data (csv of field input) through the maestro webserver at http://localhost:8080/
2. Validation occurs one at a time. Validations - DNS, VM object checks, basic IP, IPPlan, etc. 
3. The autoiso code is rsync'd locally to /opt/installmedia/autoiso (yeah.) and executed locally to create an ISO with #1's data.
4. Once validation is done, a SOAP message is sent to VMWare's Orchestrator to kickoff the "Linux Server Build Kickstart Simple" with #1's data.
5. Orchestrator runs through more validation steps, creates a blank VM with #1's data, then kicks off the actual OS kickstart process.
6. Once the vmtoolsd process reports to vmware (ie, OS/puppet/spacewalk = installed), the host is added to DNS and all's done and dusted.

Hints:
1. If a kickstart process fails, check what variables are sent from one item in the wofkflow to the next. The logs aren't very helpful, so with the assumption that the workflow works under normal conditions, the input will be the problem.
2. Restart the webserver after large runs, or where you'd expect a conflict of VM names, etc. 
3. Column names in the csv match the field names in the form. That includes lack-of spaces and capitalization.

To start:
  ./start_maestro
To stop:
  ./stop_maestro
