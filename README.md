# PythonServerHerd

Used the asyncio library to implement a server herd which receives location info
and responds to queries from clients. When updating a client's location, the
server with which the client communicated will flood the updates to the rest of
the servers so that all the servers in the herd will have up-to-date information.

NOTE: Please make sure to have a folder named logs/ in the same directory
as server.py so that the logging will run correctly. The logs/ folder in the
repository contains the resulting output from running all five servers and
sending the requests listed in command.txt using client.py.

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
