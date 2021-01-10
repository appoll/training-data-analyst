
from collections.abc import Mapping
import jsonschema
import inspect
import os
import pytz
import yaml
from flask import json, jsonify, request
from werkzeug.exceptions import BadRequest, InternalServerError
from collections import OrderedDict

URL_PREFIX = f'/api/v{1}'

class ValidationError(Exception):
    pass

class Swagger(object):
    def __init__(self, app=None, spec_endpoint='/swagger.json', **kwargs):
        self.app = None
        self.validator = None
        self.spec_endpoint = spec_endpoint

        if app is not None:
            self.init_app(app, **kwargs)

    def init_app(self, app, **kwargs):
        self.app = app

        self.app.swagger_spec = None
        self.app.before_first_request(self.initialize_spec)
        self.app.before_request(self.before_request)
        self.app.after_request(self.after_request)

        @app.route(self.spec_endpoint, methods=['GET'])
        def swagger_spec():
            spec = dict(app.swagger_spec)
            spec['host'] = request.host
            return jsonify(spec)

    def initialize_spec(self):
        self.app.swagger_spec = Spec(self.app)
        self.validator = Validator(self.app.swagger_spec)

    def before_request(self):
        spec = self.get_spec_for_request(request)
        print("before request")
        if spec:
            try:
                self.validator.validate_request(request, spec)
            except ValidationError as e:
                return self.exception_to_response(e, BadRequest)

    def after_request(self, response):
        spec = self.get_spec_for_request(request)
        print("after request")
        print(spec)
        if spec:
            try:
                self.validator.validate_response(response, spec)
            except ValidationError as e:
                return self.exception_to_response(e, InternalServerError)
        return response

    def get_spec_for_request(self, req):
        if req.url_rule:
            print("yes")
            view_function = self.app.view_functions[req.url_rule.endpoint]
            print("View Function")
            print(view_function)
            print(getattr(view_function, 'swagger_spec', None))
            return getattr(view_function, 'swagger_spec', None)
        print("will return none")
        return None

    def exception_to_response(self, active_exception, target_exception):
        # Hack to change the current-exception context.
        # Otherwise we would be unable to call Flask.handle_user_exception()
        try:
            raise target_exception(description=str(active_exception))
        except target_exception as e:
            return self.app.handle_exception(e)


def make_backwards_compatible(spec):
    for name, definition in spec.get('definitions', {}).items():
        make_definition_backwards_compatible(definition)
    return spec

def make_definition_backwards_compatible(definition):
    if definition.get('type') == 'object':
        for field in definition.get('properties', {}).values():
            if field.get('nullable', False):
                field['x-nullable'] = field['nullable']


def load_yaml(stream):
    # based on <http://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts>
    class OrderedLoader(yaml.Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return OrderedDict(loader.construct_pairs(node))

    OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    return yaml.load(stream, OrderedLoader)


def subdict(dct, include=None, exclude=None):
    return {k: v for k, v in dct.items() if (include is None or k in include) and (exclude is None or k not in exclude)}


class Spec(Mapping):
    def __init__(self, app):
        with open(os.path.join(os.path.dirname(__file__), 'swagger.yml')) as swaggerfile:
            self.spec = make_backwards_compatible(load_yaml(swaggerfile))
        self.spec['basePath'] = URL_PREFIX
        self.spec['paths'] = {}
        # if LOCAL_DEV:
        #     self.spec['schemes'] = ['http', 'https']

        for rule in app.url_map.iter_rules():
            self.add_path_from_rule(app, rule)

    def add_path_from_rule(self, app, rule):
        path = rule.rule.replace(self.spec['basePath'], '').replace('<', '{').replace('>', '}')
        view_function = app.view_functions[rule.endpoint]
        function_spec = self.parse_docstring(view_function)

        if function_spec:
            self.add_default_error(function_spec, 400, "The request doesn't conform to the specification")
            self.add_default_error(function_spec, 500, 'Internal Server Error')
            if getattr(view_function, 'requires_auth', False):
                self.add_default_error(function_spec, 401, 'Authentication header missing or invalid')

            view_function.swagger_spec = function_spec

            for method in set(rule.methods) - {'OPTIONS', 'HEAD'}:
                self.spec['paths'].setdefault(path, {})
                self.spec['paths'][path][method.lower()] = function_spec

    @staticmethod
    def parse_docstring(obj):
        spec = None
        docstring = inspect.getdoc(obj)
        if docstring:
            lines = docstring.split('\n')
            try:
                separator_index = lines.index('---')
                spec = load_yaml('\n'.join(lines[separator_index + 1:]))
                if 'description' not in spec:
                    spec['description'] = ' '.join(line.strip() for line in lines[:separator_index])
                for param in spec.get('parameters', []):
                    if 'schema' in param:
                        make_definition_backwards_compatible(param['schema'])
                for param in spec.get('responses', {}).values():
                    if 'schema' in param:
                        make_definition_backwards_compatible(param['schema'])
            except ValueError:
                pass

        return spec

    @staticmethod
    def add_default_error(spec, code, description):
        if code not in spec['responses']:
            spec['responses'][code] = {'description': description, 'schema': {'$ref': '#/definitions/ErrorResponse'}}

    def __getitem__(self, item):
        return self.spec.__getitem__(item)

    def __iter__(self):
        return self.spec.__iter__()

    def __len__(self):  # pragma: nocover
        return self.spec.__len__()


class Validator(object):
    def __init__(self, definitions):
        self.format_checker = FormatChecker()
        self.ref_resolver = jsonschema.RefResolver.from_schema(definitions)

    def validate_request(self, req, spec):
        self.validate_path(req, spec)
        self.validate_query(req, spec)
        self.validate_body(req, spec)

    def validate_path(self, req, spec):
        known_parameters = {p['name']: subdict(p, exclude=('name', 'required', 'in', 'description'))
                            for p in spec.get('parameters', []) if p['in'] == 'path'}
        # for arg, value in req.view_args.items():
        #     if arg not in known_parameters:
        #         raise ValidationError('Invalid path-parameter: {}'.format(arg))
        #     try:
        #         self.validate_against_schema(value, known_parameters[arg])
        #     except jsonschema.ValidationError as e:
        #         raise ValidationError(str(e))

    def validate_query(self, req, spec):
        known_parameters = {p['name']: subdict(p, exclude=('name', 'required', 'in', 'description'))
                            for p in spec.get('parameters', []) if p['in'] == 'query'}
        required_parameters = {p['name'] for p in spec.get('parameters', [])
                               if p['in'] == 'query' and p.get('required', False)}

        missing_required = required_parameters - set(req.args.keys())
        # if missing_required:
        #     raise ValidationError('Missing required query-parameters: {}'.format(''.join(missing_required)))

        # for arg, value in req.args.items():
        #     if arg not in known_parameters:
        #         raise ValidationError('Invalid query-parameter: {}'.format(arg))
        #     try:
        #         if (known_parameters[arg].get('type')) == 'boolean':
        #             value = str_to_bool(value)
        #         self.validate_against_schema(value, known_parameters[arg])
        #     except (jsonschema.ValidationError, ValueError) as e:
        #         raise ValidationError(str(e))

    def validate_body(self, req, spec):
        body_spec = None
        for parameter in spec.get('parameters', []):
            if parameter['in'] == 'body':
                body_spec = parameter
                break

        if body_spec and 'schema' in body_spec:
            try:
                with temporary_flask_config('DEBUG', True):
                    data = req.get_json(force=True)
            except BadRequest as e:
                raise ValidationError(e.message)

            if not data:
                raise ValidationError('Missing request-body')
            try:
                self.validate_against_schema(data, body_spec['schema'])
            except jsonschema.ValidationError as e:
                raise ValidationError(str(e))

    def validate_response(self, response, spec):
        try:
            print("validating response")
            if 'schema' in spec['responses'][response.status_code]:
                print(response.data)
                self.validate_against_schema(
                    json.loads(response.data), spec['responses'][response.status_code]['schema'])
        except jsonschema.ValidationError as e:
            raise ValidationError(str(e))
        except KeyError:
            raise ValidationError('Response `{}` not defined in schema'.format(response.status_code))

    def validate_against_schema(self, data, schema):
        jsonschema.validate(
            data, schema, cls=VendorDraft4Validator, resolver=self.ref_resolver, format_checker=self.format_checker)


class FormatChecker(jsonschema.FormatChecker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        members = inspect.getmembers(self, predicate=lambda m: callable(m) and m.__name__.startswith('check_'))
        for name, function in members:
            self.checkers[name[len('check_'):].replace('_', '-')] = (function, ValueError)

    def check(self, instance, format_):
        # JSON-schema itself says unknown formats have to be ignored and should be considered as being always valid.
        # Therefore, the library does exactly this. But in our case we control both the schema and the validation.
        # So we change this behaviour, to get errors when we have a typo in a format-name.
        if format_ not in self.checkers:
            raise TypeError('Unknown format `{}` in schema'.format(format_))
        return super().check(instance, format_)

    @staticmethod
    def check_password(instance):
        return isinstance(instance, str)

    @staticmethod
    def check_timezone(instance):
        if isinstance(instance, str):
            try:
                pytz.timezone(instance)
            except pytz.exceptions.UnknownTimeZoneError:
                raise ValueError('Invalid timezone {}'.format(instance))
        return True

class VendorDraft4Validator(jsonschema.validators.Draft4Validator):
    def __init__(self, *args, **kwargs):
        members = inspect.getmembers(self, predicate=lambda m: callable(m) and m.__name__.startswith('validate_'))
        for name, function in members:
            self.VALIDATORS[name[len('validate_'):]] = function
        super().__init__(*args, **kwargs)

    @staticmethod
    def validate_type(validator, types, instance, schema):
        if isinstance(types, list):
            yield jsonschema.ValidationError("Swagger 2.0 doesn't allow type-arrays")

        if not schema.get('nullable', False) or instance is not None:
            if not validator.is_type(instance, types):
                try:
                    yield jsonschema.ValidationError('{} is not of type {}'.format(instance, repr(types['name'])))
                except Exception:
                    yield jsonschema.ValidationError('{} is not of type {}'.format(instance, repr(repr(types))))

    @staticmethod
    def validate_enum(validator, enums, instance, schema):
        if not schema.get('nullable', False) or instance is not None:
            if instance not in enums:
                yield jsonschema.ValidationError('{} is not one of {}'.format(instance, enums))