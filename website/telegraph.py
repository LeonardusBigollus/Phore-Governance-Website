from jinja2 import Environment, FileSystemLoader, select_autoescape
import requests
import json
import datetime
import urllib.request
from time import gmtime, strftime

def render_template(template_filename, context):
    return TEMPLATE_ENVIRONMENT.get_template(template_filename).render(context)


env = Environment(
    loader=FileSystemLoader('templates/'),
    autoescape=select_autoescape(['html', 'xml']),
)

def getphoreprice():
  r = requests.get('https://api.coinmarketcap.com/v1/ticker/phore/')
  result =  r.json()[0]
  price = float(result['price_usd'])
  return price

def getresponse(command):
  with open('config.json', 'r') as config_file:
    config_data = json.load(config_file)
    rpcuri = 'http://{}:{}'.format(config_data.get('rpchost'), config_data.get('rpcport'))
    data_to_request = '{"jsonrpc":"1.0","id":"curltext","method":"' + command + '","params":[]}'
    response = requests.get(rpcuri, headers={'content-type': 'application/json'}, data=data_to_request, auth=(config_data.get('rpcusername'), config_data.get('rpcpassword')))
    response = response.json().get('result')
    return response

def get_total_budget(nHeight):
  nSubsidy = float(0)
  if (nHeight > 200 and nHeight <= 250000):
   nSubsidy = 7.7
  else:
    nSubsidy = 5
  return float(((nSubsidy / 100) * 10) * 1440 * 30);

block_height_str = str(getresponse("getinfo").get('blocks'))
block_height = int(float( block_height_str))
monthly_phr = get_total_budget(block_height)
price_usd = getphoreprice()
monthly_usd = int(price_usd*monthly_phr)

next_superblock_str = str(getresponse("getnextsuperblock"))
next_superblock = int(float(next_superblock_str))
advance = 4320
deadline = next_superblock - advance

time_now = datetime.datetime.utcnow()
delta = next_superblock-block_height
delta = datetime.timedelta(minutes=delta)
time_next_superblock = time_now+delta
delta = deadline - block_height
delta = datetime.timedelta(minutes=delta)
time_deadline = time_now+delta

today = time_now.strftime("%A, %B %d, %Y")
next_superblock = time_next_superblock.strftime("%A, %B %d, %Y")
voting_deadline = time_deadline.strftime("%A, %B %d, %Y")

masternodecount = getresponse("getmasternodecount")
number_mn = masternodecount.get('total')

budgetinfo = getresponse("getbudgetinfo")

proposals_active = []
proposals_past = []
nb_proposals_this_month = 0
nb_proposals_this_month_projection = 0
nb_remaining_payments = 0
value_remaining_payments = 0
total_value_proposals_this_month = 0
total_value_proposals_this_month_projection = 0


for proposal in budgetinfo:
  delta = proposal['BlockStart']-block_height
  delta = datetime.timedelta(minutes=delta)
  time_start = time_now+delta
  delta = proposal['BlockEnd']-block_height
  delta = datetime.timedelta(minutes=delta)
  time_end = time_now+delta
  proposal['TotalPaymentUSD'] = "{:,}".format(int(proposal['TotalPayment']*price_usd))
  proposal['start'] = time_start.strftime("%B %d, %Y")
  proposal['end'] = time_end.strftime("%B %d, %Y")

  proposal_deadline = proposal['BlockStart'] - advance
  delta = proposal_deadline - block_height
  delta = datetime.timedelta(minutes=delta)
  time_proposal_deadline = time_now+delta
  proposal['deadline'] = time_proposal_deadline.strftime("%A, %B %d, %Y")

  if proposal['Yeas'] - proposal['Nays'] > 0.1*number_mn:
    proposal['passing'] = "Yes"
  else:
    proposal['passing'] = "No"

  if proposal['BlockStart'] > block_height:
    
    nb_proposals_this_month += 1
    total_value_proposals_this_month = total_value_proposals_this_month + proposal['MonthlyPayment']
    if ( proposal['passing'] == "Yes" ):
      nb_proposals_this_month_projection += 1
      total_value_proposals_this_month_projection = total_value_proposals_this_month_projection + proposal['MonthlyPayment']
    proposal['MonthlyPayment'] = "{:,}".format(proposal['MonthlyPayment'])
    proposal['TotalPayment'] = "{:,}".format(proposal['TotalPayment'])
    proposals_active.append(proposal)


  else:
    if proposal['RemainingPaymentCount'] > 0:
      value_remaining_payments = value_remaining_payments + proposal['MonthlyPayment']
      nb_remaining_payments += 1
    proposal['MonthlyPayment'] = "{:,}".format(proposal['MonthlyPayment'])
    proposal['TotalPayment'] = "{:,}".format(proposal['TotalPayment'])
    proposals_past.append(proposal)

total_value_proposals_projection = total_value_proposals_this_month_projection + value_remaining_payments

fname = "index.html"
context = {
  'today': today,
  'block_height': "{:,}".format(block_height),
  'phr_usd': "{:,}".format(price_usd),
  'monthly_phr': "{:,}".format(monthly_phr),
  'monthly_usd': "{:,}".format(monthly_usd),
  'voting_deadline': voting_deadline,
  'next_superblock': next_superblock,
  'number_mn': "{:,}".format(number_mn),
  'nb_proposals_this_month': "{:,}".format(nb_proposals_this_month),
  'nb_proposals_this_month_projection': "{:,}".format(nb_proposals_this_month_projection),
  'total_value_proposals_this_month': "{:,}".format(total_value_proposals_this_month),
  'value_remaining_payments': "{:,}".format(value_remaining_payments),
  'nb_remaining_payments': "{:,}".format(nb_remaining_payments),
  'total_value_proposals_this_month_projection': "{:,}".format(total_value_proposals_this_month_projection),
  'total_value_proposals_projection': "{:,}".format(total_value_proposals_projection),
  'proposals_active': proposals_active,
  'proposals_past': proposals_past
}

with open(fname, 'w') as f:
  html = env.get_template('telegraph.html').render(context)
  f.write(html)