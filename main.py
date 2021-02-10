import re
import json
import traceback

from gethours import handleGetHoursEndpoint
from sethours import handleSetHoursEndpoint
from getcurrentstate import handleGetCurrentStateEndpoint

from constants import APIError

# Main program entry point
def main(event, context):
	print(event)

	if event.get("Name") == "ContactFlowEvent":
		return handleContactFlowEvent(event)
	else:
		return handleAPIEvent(event)

# Called when the lambda function is invoked from the API Gateway
def handleAPIEvent(event):
	stage = event["requestContext"]["stage"]
	path = event["requestContext"]["http"]["path"]
	method = event["requestContext"]["http"]["method"]

	endpoint = re.sub(f"^/{stage}/", "", path)

	headers = event.get("headers")
	query = event.get("queryStringParameters")
	body = event.get("body")

	if headers is None:
		headers = {}
	if query is None:
		query = {}

	# Pass the data to the correct endpoint handler. Catch and log any errors that occur.
	try:
		if endpoint == "get-hours-of-operation" and method == "GET":
			return _buildSuccess(handleGetHoursEndpoint(headers, query, body))
		elif endpoint == "get-current-operation-state" and method == "GET":
			return _buildSuccess(handleGetCurrentStateEndpoint(headers, query, body))
		elif endpoint == "set-hours-of-operation" and method == "POST":
			return _buildSuccess(handleSetHoursEndpoint(headers, query, body))
		else:
			raise APIError(404, "Endpoint not found")

	except Exception as err:
		traceback.print_exc()

		if isinstance(err, APIError):
			return _buildError(err.status, err.message)
		else:
			return _buildError(500, "An unexpected error occurred")

# Called when the lambda function is invoked from an Amazon Connect contact flow
def handleContactFlowEvent(event):
	query = {"service": event["Details"]["Parameters"].get("service")}

	try:
		result = handleGetCurrentStateEndpoint({}, query, None, connect=True)
		result["hasError"] = False

		# Convert all values to strings
		for key, val in result.items():
			if val is None:
				result[key] = "null"
			elif type(val) is bool:
				result[key] = str(val).lower()
			else:
				result[key] = str(val)

		print("Connect result:", result)
		return result

	except Exception as err:
		traceback.print_exc()

		if isinstance(err, APIError):
			return {"hasError": "true", "errorCode": str(err.status), "errorMsg": str(err.message)}
		else:
			return {"hasError": "true", "errorCode": str(500), "errorMsg": "An unexpected error occurred"}

######

def _buildSuccess(data):
	return _buildResponse(200, {"hasError": False, "content": data})

def _buildError(status, message):
	return _buildResponse(status, {"hasError": True, "content": message})

def _buildResponse(status, body):
	return {
		"statusCode": status,
		"isBase64Encoded": False,
		"body": json.dumps(body),
		"headers": {
			"Content-Type": "application/json; charset=utf-8"
		}
	}