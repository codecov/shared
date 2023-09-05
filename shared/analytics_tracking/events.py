from enum import Enum


class Events(Enum):
    ACCOUNT_ACTIVATED_REPOSITORY_ON_UPLOAD = "Account Activated Repository On Upload"
    ACCOUNT_ACTIVATED_REPOSITORY = "Account Activated Repository"
    ACCOUNT_UPLOADED_COVERAGE_REPORT = "Account Uploaded Coverage Report"
    USER_SIGNED_IN = "User Signed In"
    USER_SIGNED_UP = "User Signed Up"
