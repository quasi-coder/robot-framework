*** Settings ***
Documentation     Suite description
Suite Teardown    Update jira test
Library           zephyr.ZephyrLibrary
Library           String

*** Variables ***
${user}           dwiveddi
${password}       automation
#${baseUrl}       http://0.0.0.0/jira
${baseUrl}        http://0.0.0.0:48080
${issueCustomField}    10100
${proj}          divya
${projectKey}     TP
${versionId}      -1

*** Test Cases ***
Create jira issue
    print    hello

*** Keywords ***
Update jira test
    [Arguments]
    ${suiteRoot} =    Catenate    SEPARATOR=    realtest    ${/}
    ${issueCustomFieldVal} =    Fetch From Right    ${SUITE SOURCE}    ${suiteRoot}
    Zephyr tear down    ${baseUrl}    ${user}    ${password}    ${SUITE NAME}    ${SUITE DOCUMENTATION}    ${issueCustomField}
    ...    ${issueCustomFieldVal}    ${projectKey}    ${versionId}    ${SUITE STATUS}    ${SUITE MESSAGE}
