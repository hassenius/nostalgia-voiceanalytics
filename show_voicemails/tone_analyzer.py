#!/usr/bin/env python
# Standard modules
import sys, os, json
import logging
# special modules requiring installation
import pika
import requests
from requests.auth import HTTPBasicAuth
import swiftclient.client as swift_client
EXCHANGE = 'audio_demo'
QUEUE = 'devqueue'
ROUTING_KEY = 'audiofiles'

PUBLISH_EXCHANGE = 'audio_demo'
PUBLISH_ROUTING_KEY = 'transcripts'

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=LOG_FORMAT)

LOGGER.info('Starting application')

if os.environ.get('VCAP_SERVICES'):
   vcap_services = os.environ.get('VCAP_SERVICES')
   # Get Object Storage Credentials
   decoded = json.loads(vcap_services)['Object Storage'][0]
   vcap_username = str(decoded['credentials']['username'])
   vcap_password = str(decoded['credentials']['password'])
   vcap_auth_url = str(decoded['credentials']['auth_url'])
   credentials = requests.get(url=vcap_auth_url, auth=HTTPBasicAuth(vcap_username, vcap_password))
   os_auth_url = credentials.json()['CloudIntegration']['auth_url']
   os_username = credentials.json()['CloudIntegration']['credentials']['userid']
   os_password = credentials.json()['CloudIntegration']['credentials']['password']
   swift_url = credentials.json()['CloudIntegration']['swift_url']
   os_tenant_name = credentials.json()['CloudIntegration']['project']

   
   # Tone Analyzer Credentials
   decoded = json.loads(vcap_services)['tone_analyzer'][0]
   st_url = str(decoded['credentials']['url'])
   st_username = str(decoded['credentials']['username'])
   st_password = str(decoded['credentials']['password'])

    # MQ Credentials
   decoded = json.loads(vcap_services)['cloudamqp'][0]
   mq_url = str(decoded['credentials']['uri'])
else:
  exit("No credentials")



def do_analyse(text):
  response = requests.post(url=st_url + '/v1/tone', auth=HTTPBasicAuth(st_username, st_password), data=json.dumps({"scorecard":"email","text":text}), headers={"content-type": "application/json"})
  #response = requests.get(url=st_url + '/v1/tone?scorecard=email&text=justtesting', auth=HTTPBasicAuth(st_username, st_password))
  #return response.json())
  answer = {}
  for tone in response.json()['children']:
    for spec in tone['children']:
      answer[spec['id']] = spec['normalized_score']
  return answer



def callback(ch, method, properties, body):
  LOGGER.info('Received message: %s' % body)
    
  # Received a new message, where the body is a json string with container and filename
  message_details = json.loads(body)
  
  analysis = do_analyse(message_details['transcript'])



  # load the file
  headers, audio = os_client.get_object(container, obj)

  # Transcribe the audio
  text = transcribe_audio(audio)

  # Update the metadata for the object with the transcribed text
  add_object_metadata(container, obj, headers, 'calldata-transcript', text)

  # Build the message body
  file_details['call_data']['transcript'] = text

  # Send a message to the next component
  #LOGGER.info('Preparing to send message %s to exchange %s with routing key %s' % (json.dumps(file_details), PUBLISH_EXCHANGE, PUBLISH_ROUTING_KEY ) )
  #ch.basic_publish(exchange=PUBLISH_EXCHANGE, routing_key=PUBLISH_ROUTING_KEY, body=json.dumps(file_details))


channel.basic_consume(callback,
                      queue=QUEUE,
                      no_ack=True)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
    
connection.close()
