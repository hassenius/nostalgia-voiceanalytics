#!/usr/bin/env python
# Standard modules
import sys, os, json
import logging
# special modules requiring installation
import pika
import requests
from requests.auth import HTTPBasicAuth

DEBUG_MODE=True

# Servicename for voicemail storage
voicemailstore = 'voicemailstore'

EXCHANGE = 'audio_demo'
QUEUE = 'audiofiles'
ROUTING_KEY = 'audiofiles'

PUBLISH_EXCHANGE = 'audio_demo'
PUBLISH_ROUTING_KEY = 'transcripts'
WORKER_NAME='transcribe.py'

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

LOGGER.info('Starting application')

# Get RabbitMQ details
rabbitmqsvc = 'rabbitmq'
ruser = 'user'
rpass = os.environ.get('RABBIT_PASS')
rport = os.environ.get(rabbitmqsvc.upper().replace("-", "_") + '_SERVICE_PORT_AMQP')
rhost = rabbitmqsvc # We'll use kubedns to resolve the IP address of the service
rcredentials = pika.PlainCredentials(ruser, rpass)
parameters = pika.ConnectionParameters(rhost,
                                       rport,
                                       '/',
                                       rcredentials)

decoded = json.loads(os.environ.get('SPEECH_TO_TEXT'))
st_url = str(decoded['url'])
st_username = str(decoded['username'])
st_password = str(decoded['password'])


def transcribe_audio(data):
  LOGGER.info('')
  LOGGER.debug('Preparing to call watson API')
  #audiofile = str(sys.argv[1])
  # url = st_url + '/v1/recognize?continuous=true&model=en-US_NarrowbandModel'
  url = st_url + '/v1/recognize?continuous=true&model=en-US_BroadbandModel'
  # url = st_url + '/v1/recognize?continuous=true&model=en-US_NarrowbandModel&max_alternatives=3'
  # url = 'https://stream.watsonplatform.net/speech-to-text/api/v1/recognize?continuous=true&model=en-US_NarrowbandModel'
  # data = open(audiofile, 'rb').read()
  results = requests.post(url=url, data=data, auth=(st_username, st_password), headers={'Content-Type': 'audio/wav'})
  LOGGER.debug('Watson API returned status code %s ' % results.status_code )
  LOGGER.debug('Watson API returned the text %s ' % results.text )
  # results = requests.post(url=url, data=data, auth=(st_username, st_password), headers={'Content-Type': 'audio/l16; rate=8000; channels=1'})
  text = ""

  for result in results.json()['results']:
    text += result['alternatives'][0]['transcript'].replace('%HESITATION ', '')

  return text


## Create a connection to Message Queue
for i in range(0,100):
    try:
      connection = pika.BlockingConnection(parameters)
    except pika.exceptions.ConnectionClosed:
      print "Attempt %i failedConnection closed, trying again" % i
      continue
    break
channel = connection.channel()
channel.exchange_declare(exchange=EXCHANGE)

#result =
channel.queue_declare(QUEUE)
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
  LOGGER.debug('Calling get_object for container %s and object %s' % (container, obj) )
  audio = requests.get('http://%s/api/v1/mailboxes/%s/voicemails/%s/audio' % (voicemailstore, container, obj))

  # Transcribe the audio
  LOGGER.debug('Calling transcribe function')
  text = transcribe_audio(audio)
  LOGGER.debug('Received text from transcribe function: %s' % text)

  # Update the metadata for the object with the transcribed text
  LOGGER.debug('Calling add_object_meta function to update calldata-transcript metadata')
  data = {"transcript": text}
  requests.post('http://%s/api/v1/mailboxes/%s/voicemails/%s/transcript' % (voicemailstore, container, obj), headers={'content-type':'application/json'}, json=data)

  # Build the message body
  file_details['call_data']['transcript'] = text

  # Send a message to the next component
  LOGGER.info('Preparing to send message %s to exchange %s with routing key %s' % (json.dumps(file_details), PUBLISH_EXCHANGE, PUBLISH_ROUTING_KEY ) )
  ch.basic_publish(exchange=PUBLISH_EXCHANGE, routing_key=PUBLISH_ROUTING_KEY, body=json.dumps(file_details))
  LOGGER.debug('Finished sending message')

  #print " [x] %r:%r" % (method.routing_key, body,)



channel.basic_consume(callback,
                      queue=QUEUE,
                      no_ack=True,
                      consumer_tag=WORKER_NAME)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()

connection.close()
