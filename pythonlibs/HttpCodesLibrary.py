# !/usr/bin/env python2.7
# -*- coding: utf-8 -*-

__author__ = 'dwiveddi'

from robot.libraries.BuiltIn import BuiltIn
from Dotable import Dotable

class HttpCodesLibrary(object):
    def __init__(self):
        """
            Creates a dictionary with the HTTP CODES and sets it
            as a global Robot variable ${HTTP_CODE}.
            Usage example:
                Should Be Equal As Numbers  ${resp.status_code}  ${HTTP_CODE.OK}
                where the variable ${resp} is the response of a REST call.
        """

        http_codes = Dotable.parse({})

        # 1xx Informational
        http_codes['CONTINUE'] =                        100
        http_codes['SWITCHING_PROTOCOLS'] =             101
        http_codes['PROCESSING'] =                      102

        # 2xx Success
        http_codes['OK'] =                              200
        http_codes['CREATED'] =                         201
        http_codes['ACCEPTED'] =                        202
        http_codes['NON_AUTHORITATIVE_INFORMATION'] =   203
        http_codes['NO_CONTENT'] =                      204
        http_codes['RESET_CONTENT'] =                   205
        http_codes['PARTIAL_CONTENT'] =                 206
        http_codes['MULTI_STATUS'] =                    207
        http_codes['ALREADY_REPORTED'] =                208
        http_codes['IM_USED'] =                         226

        # 3xx Redirection
        http_codes['MULTIPLE_CHOICES'] =                300
        http_codes['MOVED_PERMANENTLY'] =               301
        http_codes['FOUND'] =                           302
        http_codes['SEE_OTHER'] =                       303
        http_codes['NOT_MODIFIED'] =                    304
        http_codes['USE_PROXY'] =                       305
        http_codes['SWITCH_PROXY'] =                    306
        http_codes['TEMPORARY_REDIRECT'] =              307
        http_codes['PERMANENT_REDIRECT'] =              308

        # 4xx Client Error
        http_codes['BAD_REQUEST'] =                     400
        http_codes['UNAUTHORIZED'] =                    401
        http_codes['PAYMENT_REQUIRED'] =                402
        http_codes['FORBIDDEN'] =                       403
        http_codes['NOT_FOUND'] =                       404
        http_codes['METHOD_NOT_ALLOWED'] =              405
        http_codes['NOT_ACCEPTABLE'] =                  406
        http_codes['PROXY_AUTHENTICATION_REQUIRED'] =   407
        http_codes['REQUEST_TIMEOUT'] =                 408
        http_codes['CONFLICT'] =                        409
        http_codes['GONE'] =                            410
        http_codes['LENGTH_REQUIRED'] =                 411
        http_codes['PRECONDITION_FAILED'] =             412
        http_codes['REQUEST_ENTITY_TOO_LARGE'] =        413
        http_codes['REQUEST_URI_TOO_LONG'] =            414
        http_codes['UNSUPPORTED_MEDIA_TYPE'] =          415
        http_codes['REQUEST_RANGE_NOT_SATISFIABLE'] =   416
        http_codes['EXPECTATION_FAILED'] =              417
        http_codes['AUTHENTICATION_TIMEOUT'] =          419
        http_codes['UNPROCESSABLE_ENTITY'] =            422
        http_codes['LOCKED'] =                          423
        http_codes['FAILED_DEPENDENCY'] =               424
        http_codes['UPGRADE_REQUIRED'] =                426
        http_codes['PRECONDITION_REQUIRED'] =           428
        http_codes['TOO_MANY_REQUESTS'] =               429
        http_codes['REQUEST_HEADER_FIELDS_TOO_LARGE'] = 431

        # 5xx Server Error
        http_codes['INTERNAL_SERVER_ERROR'] =           500
        http_codes['NOT_IMPLEMENTED'] =                 501
        http_codes['BAD_GATEWAY'] =                     502
        http_codes['SERVICE_UNAVAILABLE'] =             503
        http_codes['GATEWAY_TIMEOUT'] =                 504
        http_codes['HTTP_VERSION_NOT_SUPPORTED'] =      505
        http_codes['VARIANT_ALSO_NEGOTIATES'] =         506
        http_codes['INSUFFICIENT_STORAGE'] =            507
        http_codes['LOOP_DETECTED'] =                   508
        http_codes['NOT_EXTENDED'] =                    510
        http_codes['NETWORK_AUTHENTICATION_REQUIRED'] = 511

        BuiltIn().set_global_variable('${HTTP_CODE}', http_codes)