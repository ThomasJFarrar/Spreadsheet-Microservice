# Spreadsheet Microservice
## Introduction
This spreadsheet microservice is developed for the 2024 Continous Assessment for the ECM3408 Enterprise Computing module at the University of Exeter. See `specification.pdf` for the full specification. The program runs a flask web server with a RESTful interface and has the ability to create, read, update, and delete cells with data. These are stored in either a SQLite database, or Firebase Realitime Database depending on the flag on startup.
## Prerequisites
**python 3.12** was used for the development of the spreadsheet microservice. You will also need to have installed the requests and flask libraries.
## Getting Started
To get started with the spreadsheet microservice, run `sc.py` from the terminal with a flag to indicate which database to use. For example: `python3 sc.py -r sqlite` or `python3 sc.py -r firebase`. If you are using firebase, you will need to create an environment variable with your firebase database name, for example: `export FBASE=toybase-3d1c1`. Your firebase database will nee to have europe-west1 set as the location, and be run in locked mode or test mode.
## Example Usage
The following command creates a cell with the id B2 with the value 6:
`curl -X PUT -H "Content-Type: application/json -d "{\"id\":"\B2,\"formula\":\"6\"}" localhost:3000/cells/B2`
## Testing
No testing was required for this continuous assessment, however it was marked using a shell script which carried out a series of tests to see if the spreadsheet microservice could sucessfully create, read, update, and delete cells. After starting the microservice, run `test10.sh`.
## Known Issues
* Deleting cells with firebase not working correctly.
