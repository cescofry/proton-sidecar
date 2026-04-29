# Product Requirements

- The user should be able to install proton-sidecar with a simple curl + bash 
- The installation checks for all the universal dependedencies, like protontricks, and asks to install them if missing (or at least explains the user how to)
- the command `proton-sidecar` with no arguments shows how to use the tool, and displays all available applications
- the list of available applications is compiled into a file using gihub actions during release.
- the command `proton-sidecar install <name>` install the application
- the command `proton-sidecar delete <name>` uninstalls the application
- the command `proton-sidecar init <repo URL>` creates a new folder for a new application. The folder is populated with the manifest.toml, install.py, launch.py, a README.md with additional instructions as well as a LLM.md with a prompt that can be given to an llm to help fill the files.
- the files that are created fore each new app should be copied from a template folder. Use templating for things that need to be replaced inside eahc file (ex:. repo URL, app name)
- the command `proton-sidedar launch <name>` launches the app, using the launch.py script + whatever arguments are needed.

---

## LLM.md
The documents contains the steps to help the user add a new application into the tool.
These are the steps that you need to rewrite to make them as a comprehensive plan to help the user install the tool
### Step 1 
clone the repo into /tmp so that it can be read and figured out.
The repo URL will be injected during the `proton-sidecar init` phase.

### Step 2
Understand how the tool works, what game is associated to (if any), what are the requirements, what is the name of the tool, how is it installed, how does it run.
Point to the ../Documentation/ folder for genral knowledge base on the tool as well as how to solve common issues.

### Step 3
Present the results to the user:
- Tool Name
- Associated Game
- Installation Requirements
- Launch Requirements
- Plan to create the scripts
- Ask for permissions to continue

### Step 4
Test if the tool works
- Review the code for style, make sure it is similar to other tools (where it makes sense)
- Can it be installed
- Does it launch
- Fill the README.md 

### Step 5
Guide the user on how to create a PR to submit the tool.

---

## README.md
This files contains informations about the tool that gets installed. It should contain
- Tool Name
- Associated Game
- What the tool does
- Tool original URL and author
- Author of the installation tool (the user running this)
- Installation Requirements
- Launch Requirements
- Additional informations that can help the user troubleshooting issues (like to install dependencies that cannot be automatically installed, common issues that could arise when installing/launching)

