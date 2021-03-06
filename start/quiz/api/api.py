# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

from flask import Response

# """
# Import shared GCP helper modules
# """


from quiz.gcp import datastore




# """
# Gets list of all users from datastore
# - Create query
# - Filter on id
# - Call the datastore helper to get back JSON
# - Pretty print JSON
# - Set header and return the response
# """
def get_users():
    users = datastore.get_users()
    payload = {'users': list(users)}
    payload = json.dumps(payload, indent=2, sort_keys=True, default=str)
    response = Response(payload)
    response.headers['Content-Type'] = 'application/json'
    return response


def get_user_by_id(id):
    user = datastore.get_user_by_id(id)
    payload = json.dumps(user, indent=2, sort_keys=True, default=str)
    response = Response(payload)
    response.headers['Content-Type'] = 'application/json'
    return response

def get_user_by_email(id):
    user = datastore.get_user_by_email(id)
    payload = json.dumps(user, indent=2, sort_keys=True, default=str)
    response = Response(payload)
    response.headers['Content-Type'] = 'application/json'
    return response

def get_cycle_days_by_user_id(id):
    cycle_days = datastore.get_cycle_days_by_user_email(id)

    dict_days = [day.to_dict() for day in cycle_days]
    dict_days = [remove_empty_properties(day) for day in dict_days]

    # dict_days = [convert_date_to_str(day) for day in dict_days]

    response = {
        'count': len(cycle_days),
        'days': dict_days,
    }
    # payload = {'cycle_days': list(cycle_days)}
    # payload = json.dumps(payload, indent=2, sort_keys=True, default=str)
    # response = Response(payload)
    # response.headers['Content-Type'] = 'application/json'
    return response

def remove_empty_properties(day):
    return {
        k: val for k, val in day.items() if val is not None and val != [] and val != {}
    }

def convert_date_to_str(day):
    day["date"] = day["date"].strftime('%Y-%m-%d')
    return day