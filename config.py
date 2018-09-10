API_KEY = 'AIzaSyCaJmfmSnqRCUXppfLwFCZ_OGvUqRYdPqI'
API_URL = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?'

SERVER_NAMES = ['Goloman', 'Hands', 'Holiday', 'Welsh', 'Wilkes']

SERVER_PORTS = {
    'Goloman': 12525,
    'Hands': 12526,
    'Holiday': 12527,
    'Welsh': 12528,
    'Wilkes': 12529
}

FLOODLIST = {
    'Goloman': ['Hands', 'Holiday', 'Wilkes'],
    'Hands': ['Goloman', 'Wilkes'],
    'Holiday': ['Goloman', 'Welsh', 'Wilkes'],
    'Welsh': ['Holiday'],
    'Wilkes': ['Goloman', 'Hands', 'Holiday']
}

LOG_PATHS = {
    'Goloman': './logs/goloman.log',
    'Hands': './logs/hands.log',
    'Holiday': './logs/holiday.log',
    'Welsh': './logs/welsh.log',
    'Wilkes': './logs/wilkes.log'
}

LOCALHOST = '127.0.0.1'
