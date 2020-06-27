#!/usr/bin/env python2.7
import os, subprocess, sys, shutil

SCRIPT_DIR = os.getcwd()
ROBOT_DIR = os.path.join(SCRIPT_DIR, "..", "..", "..", "..", "..", "robot")
SUITES_DIR = os.path.join(ROBOT_DIR, "implementation", "testsuites")

def main():

    if (len(sys.argv) != 2):
        print  "Usage: " + sys.argv[0] + " <Test suite name>"
        print  "Where suites are either of : "
        print_suites(SUITES_DIR)
        exit(1)
    else:
        SUITE = sys.argv[1]
        generate_tests(SUITE)


def generate_tests(suites):
    for suite in suites.split(','):
        print "generating tests for suite: ", suite
        suite_dir = os.path.join(SUITES_DIR, suite)
        generated_dir = os.path.join(suite_dir, 'generated')
        # clean directory for generated test cases
        if (os.path.exists(generated_dir)):
            shutil.rmtree(generated_dir)

        # iterate through test suite directories to find all robomachine tests
        for root, dirnames, filenames in os.walk(suite_dir, False) :
            for filename in filenames :
                if filename.endswith(".robomachine") :
                    # create directory for generated tests
                    dir = os.path.join(generated_dir, os.path.relpath(root, suite_dir))
                    if (not os.path.exists(dir)):
                        os.makedirs(dir)

                    # generate test cases from robomachine tests
                    subprocess.call(["robomachine", "--output", os.path.join(dir, os.path.splitext(filename)[0]) + ".robot", "--do-not-execute", os.path.join(root, filename)])


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
