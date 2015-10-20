#!/usr/bin/env python
import requests
#import mqlight
import rabbitpy
import threading
import uuid
import json
import os

#SUBSCRIBE_TOPIC = 'mqlight/audiodemo/audiofiles'
#PUBLISH_TOPIC = 'mqlight/audiodemo/subscribedtext'


if os.environ.get('VCAP_SERVICES'):
   vcap_services = os.environ.get('VCAP_SERVICES')
   decoded = json.loads(vcap_services)['mqlight'][0]
   service = str(decoded['credentials']['nonTLSconnectionLookupURI'])
   username = str(decoded['credentials']['username'])
   password = str(decoded['credentials']['password'])
   security_options = {
      'property_user': username,
      'property_password': password
   }


def subscribe(err):
    client.subscribe(
        topic_pattern=SUBSCRIBE_TOPIC,
        #share=SHARE_ID,
        on_message=process_message)
    send_message()

client = mqlight.Client(
    service=service,
    client_id=CLIENT_ID,
    security_options=security_options,
    on_started=subscribe)
  
def process_message(message_type, data, delivery):
   if message_type == mqlight.MESSAGE:
      print('Received a message: {0}'.format(data))
         recv_queue.append({
            'data': data,
            'delivery': delivery
         })  
  


#audiofile = str(sys.argv[1])
authuser = '2adab6f5-5733-4c04-9e3b-278b74b63504'
authpass = '5TqVJL1XU2W3'
url = 'https://stream.watsonplatform.net/speech-to-text/api/v1/recognize?continuous=true&model=en-US_NarrowbandModel'
data = open(audiofile, 'rb').read()
results = requests.post(url=url, data=data, auth=(authuser, authpass), headers={'Content-Type': 'audio/wav'})

text = ""
for result in results.json()['results']:
  text += result['alternatives'][0]['transcript']

print text
