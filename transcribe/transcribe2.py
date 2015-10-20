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
QUEUE = 'audiofiles'
ROUTING_KEY = 'audiofiles'

PUBLISH_EXCHANGE = 'audio_demo'
PUBLISH_ROUTING_KEY = 'transcripts'

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

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

   
   # Speech to text credentials
   decoded = json.loads(vcap_services)['speech_to_text'][0]
   st_url = str(decoded['credentials']['url'])
   st_username = str(decoded['credentials']['username'])
   st_password = str(decoded['credentials']['password'])

    # MQ Credentials
   decoded = json.loads(vcap_services)['cloudamqp'][0]
   mq_url = str(decoded['credentials']['uri'])
else:
  exit("No credentials")
  

def transcribe_audio(data):
  LOGGER.info('')
  #audiofile = str(sys.argv[1])
  url = st_url + '/v1/recognize?continuous=true&model=en-US_NarrowbandModel'
  # url = st_url + '/v1/recognize?continuous=true&model=en-US_NarrowbandModel&max_alternatives=3'
  # url = 'https://stream.watsonplatform.net/speech-to-text/api/v1/recognize?continuous=true&model=en-US_NarrowbandModel'
  # data = open(audiofile, 'rb').read()
  results = requests.post(url=url, data=data, auth=(st_username, st_password), headers={'Content-Type': 'audio/wav'})
  # results = requests.post(url=url, data=data, auth=(st_username, st_password), headers={'Content-Type': 'audio/l16; rate=8000; channels=1'})
  text = ""
  
  for result in results.json()['results']:
    text += result['alternatives'][0]['transcript']

  return text


def add_object_metadata(container, obj, existing_headers, meta_key, meta_value):
  LOGGER.info('')
  new_headers = {}
  
    # Save existing headers
  for key in existing_headers:
    if key.startswith('x-object-meta-'):
      new_headers[key] = existing_headers[key]
  
  # Max length of metadata is 256 bytes. If longer, split up    
  if len(meta_value) > 256:
    meta_parts = list(map(''.join, zip(*[iter(meta_value)]*256)))
    for i in range(0,len(meta_parts)):
      new_headers['x-object-meta-%s-%i' % (meta_key, int(i) + 1)] = meta_parts[int(i)]
  else:
    new_headers['x-object-meta-%s' % meta_key] = meta_value
  
  os_client.post_object(container, obj, new_headers)
  return True


# Create a global object Storage Client
os_client = swift_client.Connection(os_auth_url + '/v2.0', os_username, os_password, tenant_name=os_tenant_name, auth_version="2.0")

## Create a connection to Message Queue
for i in range(0,100):
    try:
      connection = pika.BlockingConnection(pika.URLParameters(mq_url))
    except pika.exceptions.ConnectionClosed:
      print "Attempt %i failedConnection closed, trying again" % i
      continue
    break
channel = connection.channel()
channel.exchange_declare(exchange=EXCHANGE)

#result = channel.queue_declare(QUEUE)
#queue_name = result.method.queue
channel.queue_bind(exchange=EXCHANGE,queue=QUEUE,routing_key=ROUTING_KEY)

print 'Waiting for messages. To exit press CTRL+C'


def callback(ch, method, properties, body):
  LOGGER.info('Received message: %s' % body)
    
  # Received a new message, where the body is a json string with container and filename
  file_details = json.loads(body)
  container = file_details['container']
  obj = file_details['object']

  # load the file
  headers, audio = os_client.get_object(container, obj)

  # Transcribe the audio
  text = transcribe_audio(audio)

  # Update the metadata for the object with the transcribed text
  add_object_metadata(container, obj, headers, 'calldata-transcript', text)

  # Build the message body
  file_details['call_data']['transcript'] = text

  # Send a message to the next component
  LOGGER.info('Preparing to send message %s to exchange %s with routing key %s' % (json.dumps(file_details), PUBLISH_EXCHANGE, PUBLISH_ROUTING_KEY ) )
  ch.basic_publish(exchange=PUBLISH_EXCHANGE, routing_key=PUBLISH_ROUTING_KEY, body=json.dumps(file_details))

  #print " [x] %r:%r" % (method.routing_key, body,)

    

channel.basic_consume(callback,
                      queue=QUEUE,
                      no_ack=True)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
    
connection.close()


