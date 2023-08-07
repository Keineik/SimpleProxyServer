import json

def getconfig():
    fileConfig = open('fileconfig.json')
    configs = json.load(fileConfig) 
    return configs['cache_time'], configs['whitelist'], configs['time']
