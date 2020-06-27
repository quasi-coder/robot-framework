*** Settings ***
Documentation     A test suite with a single Gherkin style test.
...
...               Test Crud Operations

Library       Collections
Library       String
Library       HttpLibrary.HTTP
Library       RequestsLibrary
Resource      ../keywords/my_keywords.robot

*** Variables ***
${HOST}    https://my-host.com/api

*** Test Cases ***
GET Example
	# Arrange
	Create Session    my_session    ${HOST}
	${headers}=    Create Dictionary    Accept=application/json    Content-Type=application/json    charset=utf-8

	# Act
	${response}=    Get Request    my_session    my-endpoint    headers=${headers}

	# Assert
	Should be equal as strings    ${response.status_code}    200

POST Example
	Create Session    my_session    ${HOST}
	${headers}=    Create Dictionary    Accept=application/json    Content-Type=application/json    charset=utf-8

	# POST request with params
	${params}=    Create dictionary    field_1=value_1    field_2=value_2
	${response}=    Post Request    my_session    my-endpoint    headers=${headers}    params=${params}

	# POST request with data
	${data}=    Create dictionary    field_1=value_1    field_2=value_2
	${response}=    Post Request    my_session    my-endpoint    headers=${headers}    data=${data}

*** Keywords ***
Browser is opened to login page
    Open browser to login page

User "${username}" logs in with password "${password}"
    Input user name    ${username}
    Input password    ${password}
    Submit credentials