# PythonServerHerd

Please make sure to have a folder named logs/ in the same directory as server.py
so that the logging will run correctly. The logs/ folder in the repository
contains the resulting output from running all five servers and sending the
requests listed in command.txt using client.py.

## Usage
### Start one server
```
python3 server.py Goloman
```
### Start all five servers
```
./run.sh
```

### Send preconfigured requests from client
```
cat command.txt | python3 client.py Goloman
```

## Types of requests
### IAMAT
Reports location of client to server.
#### Format
```
IAMAT {client-id} {ISO 6709 location} {POSIX/UNIX time}
```
### WHATSAT
Requests JSON list of locations within given radius of a specified client.
#### Format
```
WHATSAT {client-id} {radius} {info-limit}
```
