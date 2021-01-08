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
Setup flask
"""
from flask import Flask
from google.cloud import ndb
import os
project_id = os.getenv('GCLOUD_PROJECT')

client = ndb.Client(project=project_id)

# https://cloud.google.com/appengine/docs/standard/python3/migrating-to-cloud-ndb#using_a_runtime_context_with_wsgi_frameworks
def ndb_wsgi_middleware(wsgi_app):
    def middleware(environ, start_response):
        with client.context():
            return wsgi_app(environ, start_response)

    return middleware


app = Flask(__name__, static_folder='static')
app.wsgi_app = ndb_wsgi_middleware(app.wsgi_app)  # Wrap the app in middleware.

"""
Register blueprints for api and quiz
"""
from quiz.api.routes import api_blueprint
from quiz.webapp.routes import webapp_blueprint

app.register_blueprint(api.routes.api_blueprint, url_prefix='/api')
app.register_blueprint(webapp.routes.webapp_blueprint, url_prefix='')