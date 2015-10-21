#!/usr/bin/env python
# Standard modules
import os, json
# Special modules requiring installation
#import bottle
from requests.auth import HTTPBasicAuth
import requests
import swiftclient.client as swift_client
from flask import Flask

DEBUG_MODE=True

port = int(os.getenv('VCAP_APP_PORT', 8080))

# Setup Swift Client
try:
    import swiftclient.client as swift_client
except ImportError:
    import swift.common.client as swift_client

if os.environ.get('VCAP_SERVICES'):
  if DEBUG_MODE:
    print 'Loading credentials from VCAP_SERVICES'
  vcap_services = os.environ.get('VCAP_SERVICES')
  decoded = json.loads(vcap_services)['Object Storage'][0]
  vcap_username = str(decoded['credentials']['username'])
  vcap_password = str(decoded['credentials']['password'])
  vcap_auth_url = str(decoded['credentials']['auth_url'])

else:
  exit("No object storage credentials")


# Get real Object Storage credentials
if DEBUG_MODE:
  print 'Getting Keystone credentials for Object Storage'
credentials = requests.get(url=vcap_auth_url, auth=HTTPBasicAuth(vcap_username, vcap_password))

auth_url = credentials.json()['CloudIntegration']['auth_url']
username = credentials.json()['CloudIntegration']['credentials']['userid']
password = credentials.json()['CloudIntegration']['credentials']['password']
swift_url = credentials.json()['CloudIntegration']['swift_url']
tenant_name = credentials.json()['CloudIntegration']['project']
if DEBUG_MODE:
  print '...finished'

# Create a global object storage client
os_client = swift_client.Connection(auth_url + '/v2.0', username, password, tenant_name=tenant_name, auth_version="2.0")

def get_object_meta(container, obj):
  os_client.head_object(container, obj)


# Get a list of containers that has some content
#container_list = []

def get_mailboxes():
  if DEBUG_MODE:
    print 'Getting mailboxes from object storage'
  mailboxes = []
  if DEBUG_MODE:
    print 'Getting container list'
  headers, containers = os_client.get_account()
  for container in containers:
    if container['count'] > 0:
      mailbox={}
      mailbox['name'] = container['name']
      mailbox['voicemails'] = []
      
      if DEBUG_MODE:
        print 'Getting list for container %s' % container['name']
      headers, objects = os_client.get_container(container['name'])
      for obj in objects:
        vm_entry = {}
        vm_entry['filename'] = obj['name']
        
        #print 'retrieving %s from %s' % (obj['name'], container['name'])
        if DEBUG_MODE:
          print 'Getting metadata for object %s' % obj['name']
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
  
  if DEBUG_MODE:
    print 'Returning mailboxes'
  
  return mailboxes

  
def print_mailboxestable():
  if DEBUG_MODE:
    print 'Creating mailbox table'
  mailboxes = get_mailboxes()
  text = '<html><link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css">' 
  text += '<h1>MailBoxes</h1>'
  text += '<p><table class="table table-striped" padding="5">'
  text += '<thead><tr><th>messageid</th><th>From</th><th>Time</th><th>Duration</th><th>Transcript</th></tr></thead>'
  text += '<tbody>'
  for mailbox in mailboxes:
    text += '<tr><td colspan="5"><h3><br /><br />Entries for mailbox ' + mailbox['name'] + '</h3></td></tr>'
    for message in mailbox['voicemails']:
      text += '<tr><th scope="row">%(messageid)s</th><td>%(from)s</td><td>%(time)s</td><td>%(duration)s</td><td>%(transcript)s</td></tr>' % message
      
  text += '</tbody></table></p></html>'
  
  if DEBUG_MODE:
    print 'Finished creating mailbox table'
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
