#! /usr/bin/env python3
"""
account_details.py

creates a CSV with members of an AWS billing org:

AWS email, name, project (ou), parent (ou), date joined, spend
"""
import argparse
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
        print("unable to find billing data! please check aws_id (%s), billing_bucket \
        (%s) or billing_file_path (%s)." %
              aws_id, billing_bucket, billing_filename)
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


def generate_report(spend_data, outfile='OUT'):
    """
    generates a csv
    """

    fields = ['AWS email', 'account id', 'name', 'project', 'parent',
              'date joined', 'spend']

    c = boto3.client('organizations')
    r = c.list_accounts()

    with open(outfile, 'w') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(fields)

        while True:
            for acct in r['Accounts']:
                if acct['Status'] == 'ACTIVE':
                    ou_r = c.list_parents(ChildId=acct['Id'])
                    ou_id = ou_r['Parents'][0]['Id']

                    ou_r = c.describe_organizational_unit(
                        OrganizationalUnitId=ou_id
                    )
                    ou_name = ou_r['OrganizationalUnit']['Name']

                    ou_r = c.list_parents(ChildId=ou_id)
                    ou_parent_id = ou_r['Parents'][0]['Id']

                    if ou_parent_id == 'r-43a5':
                        ou_parent_name = 'ROOT'
                    else:
                        ou_r = c.describe_organizational_unit(
                            OrganizationalUnitId=ou_parent_id
                        )
                        ou_parent_name = ou_r['OrganizationalUnit']['Name']

                    date_joined = '/'.join([str(acct['JoinedTimestamp'].month),
                                            str(acct['JoinedTimestamp'].day),
                                            str(acct['JoinedTimestamp'].year)])

                    acct_id = acct['Id']
                    if spend_data[acct_id]:
                        spend = spend_data.get(acct_id)['total']
                        spend = str(spend)
                    else:
                        spend = '0'

                    row = [
                        acct['Email'], acct_id, acct['Name'], ou_name,
                        ou_parent_name, date_joined, spend
                        ]
                    csv_writer.writerow(row)

                else:
                    print('suspended/other:', acct['Email'], acct['Id'])

            if 'NextToken' in r:
                r = c.list_accounts(NextToken=r['NextToken'])
            else:
                break

def parse_args():
    """
    parse args
    """

    desc = """
    desc
    """
    parser = argparse.ArgumentParser(description=desc)

    # AWS settings
    parser.add_argument("-i",
                        "--id",
                        help="""
AWS account ID for consolidated billing.  Required unless using the --local
argument.
                        """,
                        type=str,
                        metavar="AWS_ID")
    parser.add_argument("-b",
                        "--bucket",
                        help="""
S3 billing bucket name.  Required unless using the --local argument.
                        """,
                        type=str,
                        metavar="S3_BILLING_BUCKET")
    parser.add_argument("-L",
                        "--local",
                        help="""
Read a consolidated billing CSV from the filesystem and bypass
downloading from S3.
                        """,
                        type=str,
                        metavar="LOCAL_BILLING_CSV")
    parser.add_argument("-o",
                        "--out",
                        help="""
Filename for CSV output.
                        """,
                        type=str,
                        metavar="FILENAME")

    args = parser.parse_args()

    return args


def main():
    """
    main
    """

    args = parse_args()

    if args.id is None and args.local is None:
        print("Please specify an AWS account id with the --id argument, " +
              "unless reading in a local billing CSV with --local <filename>.")
        sys.exit(-1)

    if args.bucket is None and args.local is None:
        print("Please specify a S3 billing bucket name with the --bucket " +
              "argument, unless reading in a local billing CSV with --local " +
              "<filename>.")
        sys.exit(-1)


    # billing_data = get_latest_bill('117716615155', 'amp_billing_bucket')
    detailed_bill = get_latest_bill(
        args.id,
        args.bucket,
        args.local
    )

    spend_data = parse_billing_data(detailed_bill)

    generate_report(spend_data, args.out)


if __name__ == "__main__":
    main()
