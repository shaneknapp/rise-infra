#! /usr/bin/env python3
import collections
import csv
import datetime
import sys
import boto3


def get_latest_bill(aws_id=None, billing_bucket=None, billing_file_path=None):
    """
    get the latest billing CSV from S3 (default) or a local file.
    args:
      aws_id:             AWS account number
      billing_bucket:     name of the billing bucket
      billing_file_path:  full path to consolidated billing file on a local
                        FS (optional)
      save:               save the CSV to disk with the default filename

    returns:
      csv object of billing data
    """
    if billing_file_path:
        f = open(billing_file_path, 'r')
        billing_data = f.read()
    else:
        today = datetime.date.today()
        month = today.strftime('%m')
        year = today.strftime('%Y')
        billing_filename = aws_id + '-aws-billing-csv-' + \
                           year + '-' + month + '.csv'

        s3 = boto3.resource('s3')
        b = s3.Object(billing_bucket, billing_filename)
        billing_data = b.get()['Body'].read().decode('utf-8')

    if not billing_data:
        print("unable to find billing data (%s) in your bucket!" %
              billing_filename)
        sys.exit(-1)

    return csv.reader(billing_data.split('\n'))


def parse_billing_data(billing_data):
    """
    parse the billing data and store it in a hash

    args:
      billing_data:  CSV object of billing data

    returns:
      user_dict:  dict, keyed by AWS ID, containing name, user total for all
                  services, and currency
      currency:   string, currency used (ie: USD)
      month:      billing month (for CSV output)
      year:       billing year  (for CSV output)
    """
    user_dict = collections.defaultdict(dict)
    currency = ''
    month = ''
    year = ''

    for row in billing_data:
        if len(row) < 4:
            continue
        if row[3] == 'AccountTotal':
            if not currency:
                currency = row[23]

            if not month or not year:
                date = row[6]
                month = date[5:7]
                year = date[0:4]

            acct_num = row[2]
            user_dict[acct_num]['name'] = row[9]
            user_dict[acct_num]['total'] = float(row[24])
            user_dict[acct_num]['currency'] = row[23]

    return user_dict


# billing_data = get_latest_bill('117716615155', 'amp_billing_bucket')
spend_data = parse_billing_data(
  get_latest_bill(aws_id='117716615155', billing_file_path='./mar-2022.csv')
  )

c = boto3.client('organizations')

r = c.list_accounts()
while True:
    for acct in r['Accounts']:
        if acct['Status'] == 'ACTIVE':
            ou_r = c.list_parents(ChildId=acct['Id'])
            ou_id = ou_r['Parents'][0]['Id']

            ou_r = c.describe_organizational_unit(OrganizationalUnitId=ou_id)
            ou_name = ou_r['OrganizationalUnit']['Name']

            ou_r = c.list_parents(ChildId=ou_id)
            ou_parent_id = ou_r['Parents'][0]['Id']

            if ou_parent_id == 'r-43a5':
                ou_parent_name = 'ROOT'
            else:
                ou_r = c.describe_organizational_unit(OrganizationalUnitId=ou_parent_id)
                ou_parent_name = ou_r['OrganizationalUnit']['Name']

            date_joined = '/'.join([str(acct['JoinedTimestamp'].month),
                                    str(acct['JoinedTimestamp'].day),
                                    str(acct['JoinedTimestamp'].year)])

            id = acct['Id']
            if spend_data[id]:
                spend = spend_data.get(id)['total']
                spend = str(spend)
            else:
                spend = '0'

            print(','.join([acct['Email'], acct['Name'], ou_name,
                            ou_parent_name, date_joined,
                            spend]))
        else:
            print('suspended/other:', acct['Email'], acct['Id'])
    if 'NextToken' in r:
        r = c.list_accounts(NextToken=r['NextToken'])
    else:
        break
