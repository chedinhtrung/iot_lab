
ORG = "wise2025"
TOKEN = "YenqrFRLhps7joE-y-utR7ElAzdIViNrCyVSTwsBHG1gNJKlNr8tQIg0ZRneJC4elg063tygS_d6d3RIyI811A=="
# Store the URL of your InfluxDB instance
URL="http://192.168.0.103:8086"

GENESIS_TIME = "2025-11-19T15:12:44.000Z"
default_cfg = {
    "MIN_STAY_DURATION":15,
    "MAX_IDLE_TIME":5,

    "MAX_AWAY_TIME":10,
    "AGGR_FREQ":30,
}

desk_cfg = {
    "MIN_STAY_DURATION":10,
    "MAX_IDLE_TIME":7,

    "MAX_AWAY_TIME":15,
    "AGGR_FREQ":30,
}

fish_cfg = {
    "MIN_STAY_DURATION":5,
    "MAX_IDLE_TIME":15,

    "MAX_AWAY_TIME":10,
    "AGGR_FREQ":30,
}

kitchen_cfg = {
    "MIN_STAY_DURATION":10,
    "MAX_IDLE_TIME":8,

    "MAX_AWAY_TIME":10,
    "AGGR_FREQ":30,
}