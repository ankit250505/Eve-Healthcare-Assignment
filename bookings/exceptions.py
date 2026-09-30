from rest_framework.exceptions import APIException


class Conflict(APIException):
    status_code = 409
    default_detail = "The request conflicts with the current resource state."
    default_code = "conflict"
