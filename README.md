# honeybadger-python-aws-lambda
Send errors to Honeybadger from AWS Lambda functions written in Python

[Honeybadger](https://www.honeybadger.io/) is an awesome error tracking system that supports multiple programming languages out of the box, python being one of them. They offer a [python package](https://github.com/honeybadger-io/honeybadger-python) to easily report errors, uncaught exceptions and send manual notifications. Unfortunately one cannot import any package from AWS Lambda.

So I went through their package, copied and pasted some code and created a single class with the basic code to send notifications to honeybadger.

In [lamba.py](lambda.py) you can find an example of a Lambda function triggered by AWS API Gateway that reports a manual notification and an exception.
It uses the `event` and `context` objects provided by AWS Lambda to populate the honeybadger's context. The environmente is set to `lambda`.

However all this can easily be changed, just look at the functions `context_from_lambda` and `server_payload`.

Happy reporting!
