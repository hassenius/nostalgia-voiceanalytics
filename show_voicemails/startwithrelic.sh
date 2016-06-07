#!/bin/sh
key=$(python -c 'import json,os; vcap=json.loads(os.environ.get("VCAP_SERVICES")); print str(vcap["newrelic"][0]["credentials"]["licenseKey"])')
export NEW_RELIC_APP_NAME=$(python -c 'import json,os; vcap=json.loads(os.environ.get("VCAP_APPLICATION")); print str(vcap["application_name"])')
newrelic-admin generate-config ${key} newrelic.ini

export NEW_RELIC_CONFIG_FILE=newrelic.ini 
echo "Set newrelic app name to ${NEW_RELIC_APP_NAME}"
echo "Set newrelic license key to ${key}"
echo "Set newrelic config file to ${NEW_RELIC_CONFIG_FILE}"
newrelic-admin run-program $@
