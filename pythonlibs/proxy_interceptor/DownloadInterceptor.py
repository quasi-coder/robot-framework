#!/usr/bin/env python2.7

from proxy import RequestInterceptorPlugin, ResponseInterceptorPlugin, AsyncMitmProxy, ProxyHandler
import re
import os
import sys
import logging
import zlib

logger = logging.getLogger('download_interceptor_logger')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr = logging.StreamHandler(sys.stdout)
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

download_dir = sys.argv[3]
ff_profile_dir = sys.argv[4]
profile_template_file = sys.argv[5]


class DownloadInterceptor(RequestInterceptorPlugin, ResponseInterceptorPlugin):
    def do_request(self, data):
        return data

    def do_response(self, data):
        if "Content-Disposition: attachment" in data or "content-disposition: attachment" in data or "Content-disposition: attachment" in data:
            try:
                logger.info("Attachment founded")
                headers = dict(re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", data))
                logger.info(headers)
                if headers.has_key('Content-Disposition'):
                    content = repr(headers['Content-Disposition'])
                elif headers.has_key('content-disposition'):
                    content = repr(headers['content-disposition'])
                elif headers.has_key('Content-disposition'):
                    content = repr(headers['Content-disposition'])
                else:
                    logger.error("Content-Disposition header was not found")
                    return 'Attachment was not downloaded, check Content-Disposition header'
                filename = re.search('.*filename="(.*)"', content).group(1)
                filename = filename.replace('/', '_')
                logger.info("Attachment: " + content)
                body = self.strip_http_headers(data)

                filepath = download_dir + filename
                if not os.path.exists(download_dir):
                    os.makedirs(download_dir)

                if 'Content-Encoding' in headers and headers['Content-Encoding'] == 'gzip':
                    body = zlib.decompress(body, 16+zlib.MAX_WBITS)

                file = open(filepath, "wb")
                file.write(body)
                file.close()
                logger.info("Attachment was downloaded by path: " + filepath)
                return 'Attachment was successfully downloaded by path: ' + filepath + '. You can close your browser'
            except:
                logger.error(sys.exc_info()[0])
        return data

    def strip_http_headers(self, http_reply):
        '''
        helper function for getting content of response.

        :param http_reply:
        :return:
        '''
        p = http_reply.find('\r\n\r\n')
        if p >= 0:
            return http_reply[p+4:]
        return http_reply

#function for generating temp firefox profile with specified proxy host and port
def generate_firefox_profile(profile_template_path, host, port):

    '''
    Function for generating temp firefox profile with specified proxy host and port
    :param profile_template_path:
    :param host:
    :param port:
    :return:
    '''
    profile_path = ff_profile_dir + 'prefs.js'
    if not os.path.exists(ff_profile_dir):
        os.makedirs(ff_profile_dir)

    if os.path.exists(profile_path):
        os.remove(profile_path)

    open(profile_path, 'a').close()
    template = open(profile_template_path)
    profile = open(profile_path, 'r+')

    for line in template:
        line = line.replace('${host}', host)
        line = line.replace('${port}', port)
        profile.write(line)


    profile.close()
    template.close()
    logger.info("Firefox profile was generated: " + profile_path)
    return


if __name__ == '__main__':
    proxy = AsyncMitmProxy()
    try:
        logger.info("Generating firefox profile")
        generate_firefox_profile(profile_template_file, sys.argv[1], sys.argv[2])
        logger.info("Starting download interceptor")
        proxy.__init__(server_address=(sys.argv[1], int(sys.argv[2])), RequestHandlerClass=ProxyHandler, bind_and_activate=True, ca_file='ca.pem')
        proxy.register_interceptor(DownloadInterceptor)
        proxy.serve_forever()
        logger.info("Download interceptor is started")
        logger.info("Temp download directory: " + download_dir)
        logger.info("Firefox profile location: " + ff_profile_dir)
    except KeyboardInterrupt:
        proxy.server_close()




