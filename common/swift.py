import requests
import swiftclient.client as swift_client

# Make sure debug is set
if not 'DEBUG_MODE' in globals():
  DEBUG_MODE=False

# Setup Swift Client
try:
    import swiftclient.client as swift_client
except ImportError:
    import swift.common.client as swift_client

if os.environ.get('VCAP_SERVICES'):
  if DEBUG_MODE:
    print 'Getting Object Storage Credentials'
  vcap_services = os.environ.get('VCAP_SERVICES')
  decoded = json.loads(vcap_services)['Object-Storage'][0]
  userid = str(decoded['credentials']['userId'])
  password = str(decoded['credentials']['password'])
  auth_url = str(decoded['credentials']['auth_url'])
  project_id = str(decoded['credentials']['projectId'])
  region = str(decoded['credentials']['region'])

else:
  exit("No object storage credentials")
if DEBUG_MODE:
  print '...finished'
  

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

token, endpoint = get_token_and_endpoint(auth_url, project_id, userid, password, region)

# Create a global object storage client
os_client = swift_client.Connection(preauthurl=endpoint, preauthtoken=token)


def head_object(container, obj):
  global token, os_endpoint, os_client
  try:
    meta = os_client.head_object(container, obj)
  except (OpenSSL.SSL.SysCallError, swiftclient.exceptions.ClientException) as e:
    # Try to re-authenticate
    
    token, endpoint = get_token_and_endpoint(auth_url, project_id, userid, password, region)
    os_client = swift_client.Connection(preauthurl=endpoint, preauthtoken=token)
    meta = os_client.head_object(container, obj)
    
  return meta
    
    
def get_account():
  global token, os_endpoint, os_client
  try:
    headers, containers = os_client.get_account()
  except (OpenSSL.SSL.SysCallError, swiftclient.exceptions.ClientException) as e:
    # Try to re-authenticate
    token, endpoint = get_token_and_endpoint(auth_url, project_id, userid, password, region)
    os_client = swift_client.Connection(preauthurl=endpoint, preauthtoken=token)
    headers, containers = os_client.get_account()
    
  return (headers, containers)
    
def get_container(name):
  global token, os_endpoint, os_client
  try:
    headers, objects = os_client.get_container(name)
  except (OpenSSL.SSL.SysCallError, swiftclient.exceptions.ClientException) as e:
    # Try to re-authenticate
    token, endpoint = get_token_and_endpoint(auth_url, project_id, userid, password, region)
    os_client = swift_client.Connection(preauthurl=endpoint, preauthtoken=token)
    headers, objects = os_client.get_container(name)
    
  return (headers, objects)
