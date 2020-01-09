#! /usr/bin/env python

import requests
from urllib.error import HTTPError
import csv
import argparse

# Setup arguments
parser = argparse.ArgumentParser("csv2GitlabIssues")
(parser.add_argument("secret",
                     help="API Access Secret for uploading to gitlab",
                     type=str))
(parser.add_argument("url",
                     help="Gitlab instance url. Especially useful for self hosted setups.",
                     type=str))
parser.add_argument("input_file", help="Input CSV with issues to upload", type=str)
args = parser.parse_args()

# Get Arguments
api_secret = args.secret
input_file = args.input_file
url = args.url

# Set some required variables
ERROR = -1
OK = 0
base_url = url + "/api/v4/projects"
issues_endpoint = "issues"
header = {'PRIVATE-TOKEN':api_secret}


# Function to query by project name and return a project ID for API use
def get_project_id(url, headers, project):
    try:
        r = requests.get(url, headers=headers, params={'search': project})
        r.raise_for_status()
    except HTTPError as http_error:
        print("HTTP error occurred: {}".format(http_error))
    except Exception as error:
        print("Other error occurred: {}".format(error))
    else:
        if r.status_code == requests.codes.ok():
            json_response = r.json()
            result = json_response[0]['id']
        else:
            result = ERROR
        return result


# Function creates new issue.
# Return 0 on success else -1
# url          : path, should contain project to add issue too.
# headers      : should contain authentication or access token.
# issue_params : Dictionary of parameters to set
def post_issue(url, headers, issue_params):
    try:
        r = requests.post(url, headers=headers, params=issue_params)
        r.raise_for_status()
    except HTTPError as http_error:
        print("HTTP error occurred: {}".format(http_error))
    except Exception as error:
        print("Other error occurred: {}".format(error))
    else:
        if r.status_code == requests.codes.created():
            result = OK
        else:
            print("Failed to create issue {}, status code: {}"
                  .format(issue_params['iid'], r.status_code))
            result = ERROR
        return result


# Function to update an issue to be closed since issues can't be declared closed at creation
# Return 0 on success else -1
# url          : path, should contain project to add issue too.
# headers      : should contain authentication or access token.
# issue (int)  : id of issue to update
# project (int): id of project for error/printing info
def close_issue(url, headers, issue, project):
    try:
        r = requests.put(url, headers=headers, params={'state_event': 'close'})
        r.raise_for_status()
    except HTTPError as http_error:
        print("HTTP error occurred: {}".format(http_error))
    except Exception as error:
        print("Other error occurred: {}".format(error))
    else:
        if r.status_code == requests.codes.ok():
            result = OK
        else:
            print("Failed to close issue {}, project {}, status code: {}"
                  .format(issue, project,  r.status_code))
            result = ERROR
        return result


with open(input_file, mode='r') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    line_count = 1
    for row in csv_reader:
        # Assign variables from line in csv
        project = row["project"]
        title = row['title']
        descr = row['description']
        iid = row['scr']
        label = row['label']
        status = row['complete']
        date = row['date']

        # Project id
        project_id = get_project_id(base_url, header, project)
        if project_id == ERROR:
            print("Failed to lookup project ID for {}".format(project))
            continue

        # build and create issue
        issue_url = base_url + "/" + str(project_id) + "/" + issues_endpoint
        issue_params = {'title': title, 'iid': iid, 'description': descr, 'labels': label, 'created_at': date}
        r = post_issue(issue_url, header, issue_params)
        if r == ERROR:
            print("Failed to create issue {}, continuing to next issue".format(iid))
            continue

        # Check to see if we need to close the issue
        if status == 't':
            update_url = issue_url + "/" + str(iid)
            r = close_issue(update_url, header, iid, project_id)
            if r == ERROR:
                continue
