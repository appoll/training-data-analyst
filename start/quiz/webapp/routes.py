# Copyright 2017, Google, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
Set up Flask stuff
"""
from flask import Blueprint, render_template
from flask import send_from_directory
from flask import request, redirect

from quiz.webapp import questions
from quiz.api import api
"""
configure blueprint
"""
webapp_blueprint = Blueprint(
    'webapp',
    __name__,
    template_folder='templates',
)


@webapp_blueprint.route('/get-users')
def get_users():
    return api.get_users()

@webapp_blueprint.route('/get-user/<id>')
def get_user(id):
    print(id)
    return api.get_user_by_id(id)

@webapp_blueprint.route('/get-user-by-email/<email>')
def get_user_by_email(email):
    print(id)
    return api.get_user_by_email(email)

@webapp_blueprint.route('/get-cycle-days-by-user-id/<id>')
def get_cycle_days_by_user_id(id):
    """
    Get all-time stored days of the requesting user. This method provides paginated responses, i.e. only a limited
    number of days in each response. A page token can be used to request the next page of days, and a page size
    parameter can specify how many days should be retrieved on each page.
    ---
    tags: [v2]
    parameters:
    - in: query
      name: page_size
      type: string
      description: >
        The size of the paginated result (default is 10). If not specified, the default value will be used.
        This parameter should be in the interval (1, 1500]. Strictly greater than 1, smaller than 1500.
      required: false
      default: 10
    - in: query
      name: page_token
      type: string
      example: CjsSNWoIb3Z5LXRlc3RyKQsSBFVzZXIYgICAgICAgAoMCxIIQ3ljbGVEYXkiCjIwMjAtMTAtMTYMGAgAA==
      description: >
          The token of the next page.
          If requesting the first page, this parameter can be omitted.
          If requesting a subsequent page, this parameter is mandatory.
      required: false
    responses:
      200:
        description: Successful request
        schema:
          type: object
          properties:
            count:
                type: integer
                example: 100
                description: The number of entities returned on this page.
            next_page_token:
                type: string
                example: CjsSNWoIb3Z5LXRlc3RyKQsSBFVzZXIYgICAgICAgAoMCxIIQ3ljbGVEYXkiCjIwMjAtMTAtMTYMGAgAA==
                description: >
                    The token of the next page (Base64 string).
                    These tokens should not be stored in the client apps, since
                    they expire and are regenerated with every new request by the Datastore.
            more:
                type: boolean
                example: false
                description: If true, there should be more pages to query. If false, the current page is the last one.
            days:
              type: array
              description: The days of the user, in chronological order.
              items:
                $ref: '#/definitions/CycleDayModel'
      400:
        description: The given url parameters are not permitted (page_size or page_token are incorrect).
        schema:
          $ref: '#/definitions/ErrorResponse'
    """
    return api.get_cycle_days_by_user_id(id)


"""
Renders home page
"""
@webapp_blueprint.route('/')
def serve_home():
    return render_template('home.html')

"""
Serves static file with angular client app
"""
@webapp_blueprint.route('/client/')
def serve_client():
    return send_from_directory('webapp/static/client', 'index.html')

"""
Serves static files used by angular client app
"""
@webapp_blueprint.route('/client/<path:path>')
def serve_client_files(path):
    return send_from_directory('webapp/static/client', path)

"""
Handles definition and storage of new questions
- GET method shows question entry form
- POST method save question
"""
@webapp_blueprint.route('/questions/add', methods=['GET', 'POST'])
def add_question():
    if request.method == 'GET':
        return render_template('add.html', question={}, action='Add')
    elif request.method == 'POST':
        data = request.form.to_dict(flat=True)
        questions.save_question(data)
        return redirect('/', code=302)
    else:
        return "Method not supported for /questions/add"
