#!/usr/bin/env python2.7
import os, subprocess, sys, robot, shutil

SCRIPT_DIR = os.getcwd()
ROBOT_DIR = os.path.join(SCRIPT_DIR, "..", "..", "..", "..", "..", "robot")
OUTPUT_DIR = os.path.join(ROBOT_DIR, "output")
SUITES_DIR = os.path.join(ROBOT_DIR, "implementation", "testsuites")
PYTHONLIBS_DIR = os.path.join(ROBOT_DIR, "..", "pythonlibs")
RESOURCE_DIR = os.path.join(ROBOT_DIR, "implementation", "resources")
SETTINGS_DIR = os.path.join(ROBOT_DIR, "execution", "local", "settings")
GENERATED_DIR = os.path.join(SUITES_DIR, "generated")

def main():

     if (len(sys.argv) < 3) :
         print  "Usage: " + sys.argv[0] + " <Test suite name> <Environment name> [<Project> <Version> [cycle]]"
         print  "Where suites are either of : "
         print_suites(SUITES_DIR)
         print  "Environments are either of : "
         print_environments(SETTINGS_DIR)
         print  "if Project/Version/cycle are specified the results will be reported to JIRA"
         exit(1)
     else :
         SUITE = sys.argv[1]
         ENV =  sys.argv[2]
         PROJECT = ""
         VERSION = ""
         CYCLE = ""
         TAGS = ""

         if (len(sys.argv) > 3):
            PROJECT = sys.argv[3].replace(' ', '_')
            if (len(sys.argv) < 5):
                print "No Version specified for project " + sys.argv[3]
                exit(1)
            VERSION = sys.argv[4].replace(' ', '_')
         if len(sys.argv) > 5:
             CYCLE = sys.argv[5].replace(' ', '_')

     run(SUITE, ENV, PROJECT, VERSION, CYCLE)

def run(suite, env, project = "", version = "", cycle = ""):
     print "running tests using settings: ", env
     #rm -f ROBOT_DIR + "/output/*.*"
     if (os.path.exists(OUTPUT_DIR)):
         shutil.rmtree(OUTPUT_DIR)

     # generate robomachine tests for this suite
     subprocess.call(["python", os.path.join(SCRIPT_DIR, "generate_robomachine_tests.py"), suite])

     # robot arguments
     arg_list = ["--variablefile", os.path.join(SETTINGS_DIR, env +".py"),
                 "--pythonpath", PYTHONLIBS_DIR + ":" + RESOURCE_DIR + ":" + SETTINGS_DIR,
                 "--outputdir", OUTPUT_DIR,
                 "--exclude", "Draft",
#                 "--include", "RDC-647",
                 "--nostatusrc",
                 "--xunit", "xunit.xml"]

     # if project name is specified test run results will be reported to JIRA using Zephyr
     if project != "":
         arg_list.append("--listener")
         arg_list.append("realtest.zephyr.ZephyrLibrary")

         arg_list.append("--metadata")
         arg_list.append("Project:" + project)

     if version != "":
         arg_list.append("--metadata")
         arg_list.append("Version:" + version)

     if cycle != "":
         arg_list.append("--metadata")
         arg_list.append("Testcycle:" + cycle)

     # specify test suite
     arg_list.append(os.path.join(SUITES_DIR, suite))

     # append generated suite if exists
     if (os.path.isdir(GENERATED_DIR)):
         arg_list.append(os.path.join(SUITES_DIR, "generated"))

     # run tests
     robot.run_cli(arg_list)


def print_suites(directory):
    files = os.listdir(directory)
    files = [file for file in files if os.path.isdir(os.path.join(directory,file))]
    for filename in files:
            print "    " + filename

def print_environments(directory):
    files = os.listdir(directory)
    files = [file for file in files if os.path.splitext(file)[1] == '.py']
    files = [os.path.splitext(file)[0] for file in files]
    for filename in files:
            print "    " + filename


if __name__ == "__main__":
     main()
