#!/usr/bin/python3

import zeep, configparser, smtplib, pprint, datetime
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText

config = configparser.ConfigParser()
config.read('api.conf')
mail_content = ''

transport = zeep.Transport(verify = False)
if config.has_option('connection', 'proxy'):
	transport.session.proxies = {'http': config['connection']['proxy'], 'https': config['connection']['proxy']}

try:
	portal_wsdl = 'https://' + config['connection']['ien_server'] + '/portal/services/IsvWebService?wsdl'
	portal_client = zeep.Client(wsdl = portal_wsdl, transport = transport)

	ienc_wsdl = 'https://' + config['connection']['ien_server'] + '/ienc/services/IsvService?wsdl'
	ienc_client = zeep.Client(wsdl = ienc_wsdl, transport = transport)

	portal_result = portal_client.service.apiLogin(config['connection']['username'], config['connection']['password'], config['connection']['isv'])
	portal_root = ET.fromstring(portal_result)
	for element in portal_root.iter('AuthCode'):
		authcode = element.text

	check_from_date = datetime.date.today() - datetime.timedelta(days = int(config['DEFAULT']['days']))

	ienc_result = ienc_client.service.getAlarmReport(authcode, config['connection']['isv'], config['DEFAULT']['customerid'], [], check_from_date.strftime('%Y/%m/%d'), '', -1, -1)
	ienc_root = ET.fromstring(ienc_result)
	for element in ienc_root.iter('Data'):
		report = element.text
except Exception as e:
	mail_content = 'ERROR: failed to connect ' + config['connection']['ien_server']
	mail_content += '\n' + str(e)
else:
	report = report.split(';*')
	del(report[0])	#remove the title header
	for i in range(len(report)):
		report[i] = report[i].split(',*')
		report[i] = {'status': int(report[i][0]), 'eventid': report[i][1], 'source': report[i][2], 'time': report[i][3], 'severity': int(report[i][4]), 'subject': report[i][5]}

	for event in report:
		if event['status'] == int(config['DEFAULT']['status']) and event["severity"] <= int(config['DEFAULT']['severity']):
			mail_content += pprint.pformat(event) +'\n'
finally:
	msg = MIMEText(mail_content)
	msg['Subject'] = config['email']['subject']
	msg['From'] = config['email']['sender']
	msg['To'] = config['email']['recipient']
	smtp = smtplib.SMTP(config['email']['smtp_server'])
	smtp.send_message(msg)
	smtp.quit()
	print(mail_content)
