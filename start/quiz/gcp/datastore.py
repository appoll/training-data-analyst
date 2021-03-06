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
import os
project_id = os.getenv('GCLOUD_PROJECT')

from flask import current_app
from google.cloud import ndb


# END TODO

# TODO: Create a Cloud Datastore client object
# The datastore client object requires the Project ID.
# Pass through the Project ID you looked up from the
# environment variable earlier



# END TODO

"""
Returns a list of question entities for a given quiz
- filter by quiz name, defaulting to gcp
- no paging
- add in the entity key as the id property 
- if redact is true, remove the correctAnswer property from each entity
"""
def list_entities(quiz='gcp', redact=True):
    return [{'quiz':'gcp', 'title':'Sample question', 'answer1': 'A', 'answer2': 'B', 'answer3': 'C', 'answer4': 'D', 'correctAnswer': 1, 'author': 'Nigel'}]

"""
Create and persist and entity for each question
The Datastore key is the equivalent of a primary key in a relational database.
There are two main ways of writing a key:
1. Specify the kind, and let Datastore generate a unique numeric id
2. Specify the kind and a unique string id
"""
def save_question(question):
# TODO: Create a key for a Datastore entity whose kind is Question
    pass
    

def get_users():
    query_all = User.query()
    results = query_all.fetch(limit=10)
    print(len(results))
    return results

def get_user_by_id(id):
    user = User.load_by_id(id)
    return user

def get_user_by_email(email):
    query = User.query(User.email == email)
    result = query.fetch()
    return result

def get_cycle_days_by_user_email(email):
    query = User.query(User.email == email)
    user = query.fetch()[0]
    query = CycleDay.query(ancestor=user.key)
    result = query.fetch(limit=10)
    return result

class Model(ndb.Expando):
    @classmethod
    def load_by_id(cls, id_):
        """Loads a model by it's url safe ID from the database.

        :return: Returns the model with the given id (urlsafe) or None.
        """
        key = ndb.Key(urlsafe=id_)
        if key.kind() != cls._get_kind():
            raise KeyError(f"Invalid kind {key.kind()}")
        return key.get()

# https://stackoverflow.com/questions/54900142/datastore-query-without-model-class
class CycleDay(Model):
    CERVICAL_MUCUS_ORDERING = ["t", "0", "f", "(S)", "S", "(S+)", "S+"]
    cervical_mucus = ndb.TextProperty("cxmucus", choices=CERVICAL_MUCUS_ORDERING)
    date = ndb.DateProperty()

class User(Model):
    email = ndb.StringProperty()