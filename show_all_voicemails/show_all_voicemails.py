#!/usr/bin/env python
# Standard modules
import os, json
# Special modules requiring installation
from requests.auth import HTTPBasicAuth
from flask import Flask
from flask import request, send_from_directory, url_for, redirect

DEBUG_MODE=True

## Bring in all the object storage stuff
# After this you can use call 
execfile('swift.py')

port = int(os.getenv('VCAP_APP_PORT', 8080))


# Get a list of containers that has some content
#container_list = []

def get_mailboxes():
  if DEBUG_MODE:
    print 'Getting mailboxes from object storage'
  mailboxes = []
  if DEBUG_MODE:
    print 'Getting container list'
  headers, containers = get_account()
  for container in containers:
    if head_container(container['name'])['x-container-object-count'] > 0:
      mailbox={}
      mailbox['name'] = container['name']
      mailbox['voicemails'] = []
      
      if DEBUG_MODE:
        print 'Getting list for container %s' % container['name']
      headers, objects = get_container(container['name'])
      for obj in objects:
        vm_entry = {}
        vm_entry['filename'] = obj['name']
        vm_entry['owner'] = container['name']
                
        #print 'retrieving %s from %s' % (obj['name'], container['name'])
        if DEBUG_MODE:
          print 'Getting metadata for object %s' % obj['name']
        obj_meta = head_object(container['name'], obj['name'])
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
          vm_entry['transcript'] = 'Transcribing - Refresh page to see updates...'
        
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
  #text += '<form method="post" action="/modify">'
  text += '<p><table class="table table-striped" padding="5">'
  text += '<thead><tr><th>messageid</th><th>From</th><th>Time</th><th>Duration</th><th>Delete</th><th>Transcript</th></tr></thead>'
  text += '<tbody>'
  for mailbox in mailboxes:
    text += '<tr><td colspan="5"><h3><br /><br />Entries for mailbox ' + mailbox['name'] + '</h3></td></tr>'
    for message in mailbox['voicemails']:
      text += '<tr><th scope="row">%(messageid)s</th> \
      <td>%(from)s</td><td>%(time)s</td> \
      <td>%(duration)s</td> \
      <td><form action="/modify" method="post"><input type="hidden" name="owner" value="%(owner)s" /><input type="hidden" name="filename" value="%(filename)s" /> <input type="image" src="/static/trash-300px.png" alt="Submit" width="30" height="30"></form></td> \
      <td>%(transcript)s</td></tr>' % message
      
  text += '</tbody></table></p></html>'
  
  if DEBUG_MODE:
    print 'Finished creating mailbox table'
  return text


app = Flask(__name__, static_url_path="/static")

@app.route("/")
def print_mailboxes():
  return print_mailboxestable()
  
@app.route("/modify", methods=['POST'])
def modify():
  if request.method == "POST":
    obj = request.form['filename']
    container = request.form['owner']
    print "wanted to delete %s from %s" % (obj, container)
    delete_object(container, obj)
  return redirect('/')

@app.route("/justfortest")
def testing():
  return "<html>This is really really just a test</html>"
  
@app.route("/hello")
def print_hello():
  return get_mailboxes()
  


app.run(host='0.0.0.0', port=port)

## Desired end result:
#Mailboxes:

#Mailbox - Username
#from  -  transcription
