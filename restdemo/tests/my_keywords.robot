*** Settings ***
Documentation    Suite description    This suite will contain my keywords
Library          RequestsLibrary

*** Vaiables ***

${HOST}              https://my-host.com/api
${VALID_HEADERS}     Accept=application/json    Content-Type=application/json    charset=utf-8
${INVALID_HEADERS}   Accept=invalid    Content-Type=invalid    charset=invalid

*** Test Cases ***
setup my_api session
	Create Session    my_session    ${HOST}

set proper headers
	${my_headers}=    Set suite variable    ${VALID_HEADERS}

set invalid headers
	${my_headers}=    Set suite variable    ${INVALID_HEADERS}

send GET request
	${response}=    Get Request    my_session    my-endpoint    headers=${my_headers}
	[Return]    ${response}

api ${received_response} should be ${expected_response}
	Should be equal as strings    ${received_response.status_code}    ${expected_response}