from email.utils import COMMASPACE
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from os.path import basename
from robot.libraries.BuiltIn import BuiltIn
import zipfile


class EmailLogListener:

    ROBOT_LISTENER_API_VERSION = 2
    paths_to_logs_and_reports = []

    def __init__(self):
        self.is_init = False

    def start_suite(self, name, attributes):
        '''
        Called when suite starts, set up all attributes from RT variable
        :param name:        suite name
        :param attributes:  dictionary, contains information about suite
        :return:            None
        '''
        BuiltIn().variable_should_exist('${EMAIL_LOG}')
        email_log = BuiltIn().replace_variables('${EMAIL_LOG}')
        self.zip_folder = BuiltIn().replace_variables('${TEMPDIR}')
        self.robot_dir = BuiltIn().replace_variables('${EXECDIR}')
        self.sender = email_log.sender
        self.password = email_log.password
        self.server = email_log.server
        self.recipient = email_log.recipient
        self.subject = email_log.subject
        self.text = email_log.text
        self.results_path = None
        self.without_logs = False
        if email_log.has_key('results_path'):
            self.results_path = email_log.results_path
        if email_log.has_key('without_logs'):
            if email_log.without_logs is True:
                self.without_logs = True
        self.is_init = True

    def log_file(self, path):
        '''
        Called after test log saved, add path to log in list
        :param path:    path to log file
        :return:        None
        '''
        if not self.is_init: return
        if not self.without_logs:
            print 'Email Log Listener saving log "%s"'%path
            self.paths_to_logs_and_reports.append(path)

    def report_file(self,path):
        '''
        Called after test report saved, add path to log in list
        :param path:    path to report file
        :return:        None
        '''
        if not self.is_init: return
        if not self.without_logs:
            print 'Email Log Listener saving report "%s"'%path
            self.paths_to_logs_and_reports.append(path)

    def _send_mail(self, send_from, password, send_to, subject, text, files=None, server="127.0.0.1"):
        '''
        Function for send email
        :param send_from: who send the email
        :param password:  required  for authorization
        :param send_to:   recipient or list of recipients
        :param subject:   mail subject
        :param text:      mail text body
        :param files:     path to files, for attach
        :param server:    SMTP server address with port after colon
        :return:
        '''
        msg = MIMEMultipart()
        msg['From'] = send_from
        #msg['To'] = send_to
        if isinstance(send_to, str) or isinstance(send_to,unicode):
            send_to = [send_to]
        if isinstance(files, str) or isinstance(files,unicode):
            files = [files]
        msg['To'] = COMMASPACE.join(send_to)
        msg['Subject'] = subject

        msg.attach(MIMEText(text))

        for f in files or []:
            with open(f, "rb") as fil:
                attachment = MIMEApplication(fil.read())
                attachment.add_header('Content-Disposition', 'attachment; filename="%s"' % basename(f))
                msg.attach(attachment)

        smtp = smtplib.SMTP(server)
        try:
            smtp.starttls()
        except smtplib.SMTPException:
            print "TLS is not supported"
        try:
            smtp.login(send_from,password)
        except smtplib.SMTPException:
            print "SMTP AUTH is not supported"
        smtp.sendmail(send_from, send_to, msg.as_string())
        smtp.quit()

    def _zipdir(self, path, ziph):
        '''
        Add all files from path to zip archive with ziph zip handle
        :param path: path to the folder
        :param ziph: zip handle
        :return: None
        '''
        os.chdir(path)
        for root, dirs, files in os.walk(path):
            for current_file in files:
                ziph.write(os.path.join(os.path.relpath(root, path), current_file))

    def close(self):
        '''
        Called after test suite ended. Compress all reports and logs and send by email
        :return:        None
        '''
        if not self.is_init:
            return
        print 'Email Log Listener sends email to %s' % self.recipient
        ###################################
        #This code block sends files without compress
        ###################################
        # self._send_mail(
        #     send_from=self.sender,
        #     password=self.password,
        #     send_to=self.recipient,
        #     subject=self.subject,
        #     text=self.text,
        #     files=self.paths_to_logs_and_reports,
        #     server=self.server)
        ###################################
        #Code block bellow sends zip archive
        ###################################

        attach_list = []
        if not self.without_logs:
            path_to_zip = os.path.join(self.zip_folder, 'robot_log.zip')
            archive = zipfile.ZipFile(path_to_zip, 'w')
            with archive:
                for f in self.paths_to_logs_and_reports:
                    os.chdir(os.path.split(f)[0])
                    archive.write(os.path.split(f)[1])
            attach_list.append(path_to_zip)

        if self.results_path:
            if isinstance(self.results_path, str) or isinstance(self.results_path, unicode):
                self.results_path = [self.results_path]
            for current_dir in self.results_path:
                current_dir = os.path.join(self.robot_dir,current_dir)
                path_to_zip = os.path.join(self.zip_folder, os.path.split(current_dir)[1]+'.zip')
                archive = zipfile.ZipFile(path_to_zip, 'w')
                with archive:
                    self._zipdir(current_dir, archive)
                attach_list.append(path_to_zip)

        self._send_mail(
            send_from=self.sender,
            password=self.password,
            send_to=self.recipient,
            subject=self.subject,
            text=self.text,
            files=attach_list,
            server=self.server)

        for deleted_zip in attach_list:
            os.remove(deleted_zip)
        ##################################
        print 'Email Log Listener ends successfully'
