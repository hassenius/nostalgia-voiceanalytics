import os, json
import requests

# Make sure debug is set
if not 'DEBUG_MODE' in globals():
  DEBUG_MODE=False

# Setup Swift Client
try:
  import swiftclient.client as swift_client
except ImportError:
  import swift.common.client as swift_client

# For Cloud Foundry based environments
if os.environ.get('VCAP_SERVICES'):
  if DEBUG_MODE:
    print 'Getting Object Storage Credentials from VCAP_SERVICES'

  services = json.loads(os.environ.get('VCAP_SERVICES'))
  if 'Object-Storage' in services:
    os_creds = services['Object-Storage'][0]['credentials']
  elif 'user-provided' in services:
    for service in services['user-provided']:
      if service['name'] == 'object-storage':
        os_creds = service['credentials']

# For Kubernetes based environments
if os.environ.get('OBJECT_STORAGE'):
  if DEBUG_MODE:
    print 'Getting Object Storage Credentials from OS ENV'

  os_creds = json.loads(os.environ.get('OBJECT_STORAGE'))
  userid      =   str( os_creds['userId']   )
  password    =   str( os_creds['password'] )
  auth_url    =   str( os_creds['auth_url'] )
  project_id  =   str( os_creds['projectId'])
  region      =   str( os_creds['region']   )



def get_token_and_endpoint(authurl, projectid, userid, password, region, endpoint_type='publicURL'):

  data={"auth": {"tenantId": projectid, "passwordCredentials": {"userId":  userid, "password": password} } }
  r = requests.post(authurl + '/v2.0/tokens', data=json.dumps(data), headers={"Content-Type": "application/json"})
  if r.status_code != 200:
    print 'Something went wrong while getting token'
    print 'Status code: %s and status text: " %s "'  % (r.status_code, r.text)

  token = r.json()['access']['token']['id']
  for service in r.json()['access']['serviceCatalog']:
    if service['type'] == 'object-store':
      for endpoint in service['endpoints']:
        if endpoint['region'] == region:
          os_endpoint = endpoint[endpoint_type]

  return (token, os_endpoint)

# Create a global object storage client
os_client = swift_client.Connection(key=password,authurl=auth_url + '/v3',auth_version='3',os_options={"project_id": project_id,"user_id": userid,"region_name": region})



def head_object(container, obj):
  global os_client
  try:
    meta = os_client.head_object(container, obj)
  except swift_client.ClientException as e:
    # Sometimes there's a timeout and it's sufficient to try again
    meta = os_client.head_object(container, obj)

  return meta


def get_account():
  global token, os_endpoint, os_client
  try:
    headers, containers = os_client.get_account()
  except swift_client.ClientException as e:
    # Sometimes there's a timeout and it's sufficient to try again
    headers, containers = os_client.get_account()

  return (headers, containers)

def head_container(name):
  global token, os_endpoint, os_client
  try:
    headers = os_client.head_container(name)
  except swift_client.ClientException as e:
    # Sometimes there's a timeout and it's sufficient to try again
    headers = os_client.head_container(name)

  return headers


def get_container(name):
  global token, os_endpoint, os_client
  try:
    headers, objects = os_client.get_container(name)
  except swift_client.ClientException as e:
    # Sometimes there's a timeout and it's sufficient to try again
    headers, objects = os_client.get_container(name)

  return (headers, objects)

def add_dict_to_object_metadata(container, obj, new_meta_dict):
  global token, os_endpoint, os_client
  new_headers = {}

  # Save existing headers
  existing_headers = head_object(container, obj)
  for key in existing_headers:
    if key.startswith('x-object-meta-'):
      new_headers[key] = existing_headers[key]

  # Add new headers
  for key in new_meta_dict:
    new_headers['x-object-meta-%s' % key] = new_meta_dict[key]

  # Post headers, reconnect if token is expired
  try:
    os_client.post_object(container, obj, new_headers)
  except swift_client.ClientException as e:
    # Sometimes there's a timeout and it's sufficient to try again
    os_client.post_object(container, obj, new_headers)

  return True


def add_object_metadata(container, obj, existing_headers, meta_key, meta_value):
  global token, os_endpoint, os_client
  new_headers = {}

    # Save existing headers
  for key in existing_headers:
    if key.startswith('x-object-meta-'):
      new_headers[key] = existing_headers[key]

  # Max length of metadata is 256 bytes. If longer, split up
  if len(meta_value) > 256:
    meta_parts = []
    while meta_value:
      meta_parts.append(meta_value[:256])
      meta_value = meta_value[256:]
    for i in range(0,len(meta_parts)):
      new_headers['x-object-meta-%s-%i' % (meta_key, int(i) + 1)] = meta_parts[int(i)]
  else:
    new_headers['x-object-meta-%s' % meta_key] = meta_value

  # Post headers, reconnect if token is expired
  try:
    os_client.post_object(container, obj, new_headers)
  except swift_client.ClientException as e:
    # Sometimes there's a timeout and it's sufficient to try again
    os_client.post_object(container, obj, new_headers)

  return True


def get_object(container, obj):
  global token, os_endpoint, os_client

  try:
    headers, content = os_client.get_object(container, obj)
  except swift_client.ClientException as e:
    # Sometimes there's a timeout and it's sufficient to try again
    headers, content = os_client.get_object(container, obj)
  return (headers, content)

def delete_object(container, obj):
  global token, os_endpoint, os_client
  try:
    os_client.delete_object(container, obj)
  except swift_client.ClientException as e:
    # Sometimes there's a timeout and it's sufficient to try again
    os_client.delete_object(container, obj)

def put_object(container, obj, file_data, headers):
  global token, os_endpoint, os_client
  try:
    etag = os_client.put_object(container, obj, file_data, headers=headers)
  except swift_client.ClientException as e:
    # Sometimes there's a timeout and it's sufficient to try again
    etag = os_client.put_object(container, obj, file_data, headers=headers)
  return etag

def put_container(container):
  global token, os_endpoint, os_client
  resp = {}
  try:
    os_client.put_container(container, response_dict = resp)
  except swift_client.ClientException as e:
    # Sometimes there's a timeout and it's sufficient to try again
    os_client.put_container(container, response_dict = resp)

  if 'status' in resp:
    if resp['status'] == (201 or 202):
      return True

  return False


def set_tempurl_key():
  global token, os_endpoint, os_client

  # conn.post_account(headers={"X-Account-Meta-Temp-URL-Key": "myKey"})
  try:
    os_client.post_account(container, obj)
  except swift_client.ClientException as e:
    # Sometimes there's a timeout and it's sufficient to try again
    os_client.delete_object(container, obj)
