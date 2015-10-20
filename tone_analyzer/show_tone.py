#!/usr/bin/env python
# Standard modules
import os, json
# Special modules requiring installation
#import bottle
from requests.auth import HTTPBasicAuth
import requests
import swiftclient.client as swift_client
from flask import Flask

port = int(os.getenv('VCAP_APP_PORT', 8080))

# Setup Swift Client
try:
    import swiftclient.client as swift_client
except ImportError:
    import swift.common.client as swift_client

if os.environ.get('VCAP_SERVICES'):
   vcap_services = os.environ.get('VCAP_SERVICES')
   decoded = json.loads(vcap_services)['Object Storage'][0]
   vcap_username = str(decoded['credentials']['username'])
   vcap_password = str(decoded['credentials']['password'])
   vcap_auth_url = str(decoded['credentials']['auth_url'])

   # Tone Analyzer Credentials
   decoded = json.loads(vcap_services)['tone_analyzer'][0]
   st_url = str(decoded['credentials']['url'])
   st_username = str(decoded['credentials']['username'])
   st_password = str(decoded['credentials']['password'])
   
else:
  exit("No object storage credentials")


# Get real Object Storage credentials
credentials = requests.get(url=vcap_auth_url, auth=HTTPBasicAuth(vcap_username, vcap_password))

auth_url = credentials.json()['CloudIntegration']['auth_url']
username = credentials.json()['CloudIntegration']['credentials']['userid']
password = credentials.json()['CloudIntegration']['credentials']['password']
swift_url = credentials.json()['CloudIntegration']['swift_url']
tenant_name = credentials.json()['CloudIntegration']['project']


# Create a global object storage client
os_client = swift_client.Connection(auth_url + '/v2.0', username, password, tenant_name=tenant_name, auth_version="2.0")

def get_object_meta(container, obj):
  os_client.head_object(container, obj)


# Get a list of containers that has some content
#container_list = []

def get_mailboxes():
  mailboxes = []
  headers, containers = os_client.get_account()
  for container in containers:
    if container['count'] > 0:
      mailbox={}
      mailbox['name'] = container['name']
      mailbox['voicemails'] = []
      
      headers, objects = os_client.get_container(container['name'])
      for obj in objects:
        vm_entry = {}
        vm_entry['filename'] = obj['name']
        
        #print 'retrieving %s from %s' % (obj['name'], container['name'])
        obj_meta = os_client.head_object(container['name'], obj['name'])
        vm_entry['from'] = obj_meta.get('x-object-meta-calldata-cidnum', 'Unknown')
        vm_entry['duration'] = obj_meta.get('x-object-meta-calldata-duration', 'Unknown')
        vm_entry['messageid'] = obj_meta.get('x-object-meta-calldata-messageid', 'Unknown')
        vm_entry['time'] = obj_meta.get('x-object-meta-calldata-date', 'Unknown')
        
        if obj_meta.get('x-object-meta-calldata-transcript'):
          vm_entry['transcript'] = obj_meta.get('x-object-meta-calldata-transcript')  
        elif obj_meta.get('x-object-meta-calldata-transcript-1'):
          vm_entry['transcript'] = ''
          i = 1
          while obj_meta.get('x-object-meta-calldata-transcript-%i' % i):
            vm_entry['transcript'] += obj_meta.get('x-object-meta-calldata-transcript-%i' % i)
            i += 1
        else:
          vm_entry['transcript'] = 'Unknown'
        
        mailbox['voicemails'].append(vm_entry)
        
      mailboxes.append(mailbox)
  
  return mailboxes


def do_analyse(text):
  response = requests.post(url=st_url + '/v1/tone', auth=HTTPBasicAuth(st_username, st_password), data=json.dumps({"scorecard":"email","text":text}), headers={"content-type": "application/json"})
  #response = requests.get(url=st_url + '/v1/tone?scorecard=email&text=justtesting', auth=HTTPBasicAuth(st_username, st_password))
  #return response.json())
  answer = {}
  for tone in response.json()['children']:
    for spec in tone['children']:
      answer[spec['id']] = {}
      answer[spec['id']]['name'] = spec['name']
      answer[spec['id']]['score'] = spec['normalized_score']
      
  return answer
  
def print_mailboxestable():
  mailboxes = get_mailboxes()
  text = '<html><link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css">' 
  text += '<h1>MailBoxes</h1>'
  text += '<p><table class="table table-striped" padding="5">'
  text += '<thead><tr><th>ID</th><th>From</th><th>Transcript</th><th>Tone Analysis</th></tr></thead>'
  text += '<tbody>'
  for mailbox in mailboxes:
    text += '<tr><td colspan="5"><h3><br /><br />Entries for mailbox ' + mailbox['name'] + '</h3></td></tr>'
    for message in mailbox['voicemails']:
      tone_analyse = do_analyse(message['transcript'])
      text += '<tr><th scope="row">%(messageid)s</th><td>%(from)s</td><td>%(transcript)s</td>' % message
      text += '<td>'
      for key, emotion in tone_analyse.iteritems():
        text += emotion['name'] + ': ' + str(int(float(emotion['score']) * 100)) + '% <br />'
      text += '</td></tr>'

      # print '%s: %i <br />' % (emotion['name'], float(emotion['score']) * 100)
      
  text += '</tbody></table></p></html>'
  
  return text


app = Flask(__name__)

@app.route("/")
def print_mailboxes():
  return print_mailboxestable()
  
  
@app.route("/hello")
def print_hello():
  return get_mailboxes()
  

app.run(host='0.0.0.0', port=port)

## Desired end result:
#Mailboxes:

#Mailbox - Username
#from  -  transcription
