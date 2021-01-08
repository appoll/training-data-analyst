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
    users = datastore.list_users()
    payload = {'users': list(users)}
    payload = json.dumps(payload, indent=2, sort_keys=True, default=str)
    response = Response(payload)
    response.headers['Content-Type'] = 'application/json'
    return response


