import jsonschema
from flask import Flask, current_app, json, request
from google.protobuf.message import Message
from google.cloud import ndb
from collections.abc import Mapping
import re

class ModelResponses:
    def __init__(self, app=None, **kwargs):
        if app is not None:
            self.init_app(app, **kwargs)

    def init_app(self, app, **kwargs):
        app.request_class = create_request_class(app.request_class)


def create_request_class(base_class):
    class Request(base_class):
        def protobuf(self, protobuf_class):
            return parse_protobuf(self.data, protobuf_class)

    return Request


def parse_protobuf(raw_encoded, protobuf_class):
    result = protobuf_class()
    result.ParseFromString(raw_encoded)
    return result


def camel_to_snake(o):
    def transform(s):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    return _recursive_transform_keys(o, transform)


def _recursive_transform_keys(o, t):
    if isinstance(o, Mapping):
        return {_recursive_transform_keys(k, t): v for k, v in o.items()}
    elif isinstance(o, list):
        return [_recursive_transform_keys(v, t) for v in o]
    elif isinstance(o, str):
        return t(o)

    return o



class ResponseApp(Flask):
    def make_response(self, rv):
        data = rv[0] if isinstance(rv, tuple) else rv
        status = rv[1] if isinstance(rv, tuple) and len(rv) >= 2 and isinstance(rv[1], int) else 200
        mimetype = None
        if isinstance(data, Message):
            mimetype = 'application/x-protobuf'
            data = data.SerializeToString()
        elif isinstance(data, (dict, list, ndb.Model)):
            try:
                data = Transformer(status).transform(data)[1]
            except TypeError:
                pass
            mimetype = 'application/json'
            data = json.dumps(data)
        rv = (data,) + rv[1:] if isinstance(rv, tuple) else data
        response = super().make_response(rv)
        if mimetype is not None:
            response.mimetype = mimetype
        return response



class Transformer:
    UNDEFINED = object()

    def __init__(self, status):
        self.schema = self.get_current_schema(status)
        self.ref_resolver = jsonschema.RefResolver.from_schema(current_app.swagger_spec)

    def transform(self, data):
        return current_app.config['JSONIFY_MIMETYPE'], self.visit_node(self.schema, data)

    def visit_node(self, schema_node, data_node):
        if '$ref' in schema_node:
            _, schema_node = self.ref_resolver.resolve(schema_node['$ref'])

        if schema_node.get('type') == 'object':
            return self.visit_object(schema_node, data_node)
        if schema_node.get('type') == 'array':
            return self.visit_array(schema_node, data_node)

        return self.convert_format(schema_node, data_node)

    def visit_object(self, schema_node, data_node):
        response = {}

        for name, schema in schema_node.get('properties', {}).items():
            if isinstance(data_node, dict):
                value = data_node.get(camel_to_snake(name), self.UNDEFINED)
            else:
                value = getattr(data_node, camel_to_snake(name), self.UNDEFINED)

            if value != self.UNDEFINED:
                response[name] = self.visit_node(schema, value)

        return response

    def visit_array(self, schema_node, data_node):
        return [self.visit_node(schema_node['items'], m) for m in data_node]

    def convert_format(self, schema_node, data_node):
        if data_node and schema_node.get('format') == 'time':
            return data_node.strftime('%H:%M:%S')
        if data_node and schema_node.get('format') == 'timezone':
            return data_node.zone
        if data_node and schema_node.get('format') == 'date':
            return data_node.strftime('%Y-%m-%d')
        return data_node

    @staticmethod
    def get_current_schema(status):
        view_function = current_app.view_functions[request.url_rule.endpoint]
        spec = getattr(view_function, 'swagger_spec', None)

        if not spec:
            raise TypeError('Cannot implicitly serialize model, no spec known')

        return spec['responses'][status]['schema']
