import io
import os
import sys
import json
import traceback
from datetime import datetime
from six.moves.urllib import request
from six import b


def respond(err, res=None):
    '''Format the response in such a way so that API Gateway understands it
    '''
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def do_something(event, context):
    '''Your main function
    '''
    raise StandardError


def lambda_handler(event, context):
    '''AWS Lambda entry point
    '''
    honeybadger = Honeybadger(api_key='your_honeybadger_api_key', lambda_event=event, lambda_context=context)
    # manually send a notification to honeybadger
    honeybadger.notify(exception=None, error_class='ErrorClass', error_message='the message', context={'a_key': 'a_value'})

    try:
        do_something(event, context)
        return respond(None, {'status': 'OK'})
    except:
        exc = sys.exc_info()[1]
        # manually send an exception to honeybadger
        honeybadger.notify(exception=exc, context={'a_key': 'a_value'})
        raise(exc)


class Honeybadger(object):
    class StringReprJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            try:
                return repr(obj)
            except:
                return '[unserializable]'

    def __init__(self, api_key=None, lambda_event=None, lambda_context=None):
        self.api_key = api_key
        self.lambda_event = lambda_event
        self.lambda_context = lambda_context

    def notify(self, exception=None, error_class=None, error_message=None, context=None):
        if exception is None:
            exception = {
                'error_class': error_class,
                'error_message': error_message
            }
        if context is None:
            context = {}

        payload = self.create_payload(exception, context)
        self.send_notice(payload)

    def create_payload(self, exception, context):
        # sys.exc_info returns info about the about the exception that is currently being handled (if any)
        exc_traceback = sys.exc_info()[2]

        context.update(self.context_from_lambda())

        return {
            'notifier': {
                'name': "Honeybadger for Python in AWS Lambda",
                'url': "https://github.com/honeybadger-io/honeybadger-python",
                'version': '0.1'
            },
            'error':  self.error_payload(exception, exc_traceback),
            'server': self.server_payload(),
            'request': {'context': context},
        }

    def context_from_lambda(self):
        # check the AWS Lambda docs to see what else is in the context object
        # http://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html
        # maybe you are interested in something that is inside the event dictionary?
        # you can dump it with `respond(None, json.dumps(event))` to see what is inside
        context = {
            'log_group_name': self.lambda_context.log_group_name,
            'log_stream_name': self.lambda_context.log_stream_name,
            'function_name': self.lambda_context.function_name,
            'function_version': self.lambda_context.function_version,
            'invoked_function_arn': self.lambda_context.invoked_function_arn,
            'aws_request_id': self.lambda_context.aws_request_id,
        }
        return {'lambda_context': context}

    def server_payload(self):
        payload = {
            'project_root': "AWS Lambda.%s" % self.lambda_context.function_name,
            'environment_name': 'lambda',
            'hostname': 'aws_lambda',
            'time': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            'pid': os.getpid(),
            'stats': {}
        }

        return payload

    def error_payload(self, exception, exc_traceback):
        if exc_traceback:
            tb = traceback.extract_tb(exc_traceback)
        else:
            tb = [f for f in traceback.extract_stack()]

        payload = {
            'class': type(exception) is dict and exception['error_class'] or exception.__class__.__name__,
            'message': type(exception) is dict and exception['error_message'] or str(exception),
            'backtrace': [dict(number=f[1], file=f[0], method=f[2]) for f in reversed(tb)],
            'source': {}
        }

        source_radius = 3  # how much source code around the line that errored we want to display in honeybadger's web interface

        if len(tb) > 0:
            with io.open(tb[-1][0], 'rt', encoding='utf-8') as f:
                contents = f.readlines()

            index = min(max(tb[-1][1], source_radius), len(contents) - source_radius)
            payload['source'] = dict(zip(range(index-source_radius+1, index+source_radius+2), contents[index-source_radius:index+source_radius+1]))

        return payload

    def send_notice(self, payload):
        endpoint = 'https://api.honeybadger.io'
        api_url = "{}/v1/notices/".format(endpoint)
        request_object = request.Request(url=api_url, data=b(json.dumps(payload, cls=Honeybadger.StringReprJSONEncoder)))

        request_object.add_header('X-Api-Key', self.api_key)
        request_object.add_header('Content-Type', 'application/json')
        request_object.add_header('Accept', 'application/json')

        response = request.urlopen(request_object)

        status = response.getcode()
        if status != 201:
            print("ERROR: Received error response [{}] from Honeybadger API.".format(status))
        else:
            print("INFO: Error successfully sent to Honeybadger.")
