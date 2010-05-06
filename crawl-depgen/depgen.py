#!/usr/bin/python

import sys
import os
import time
import getopt
import re

"""Depgen - A C/C++ header file dependancy generator that ouputs a graph in
the DOT graph description language.

Usage should be to initialize App with the command line arguments obtained by
syst.argv. This is because the usage depends on the first argument being the
filename called to run the script.  Basically it reads .h files in order

Written by Chris Galardi ~5/2010
"""

# "Constants"
SILENT = -10        # But deadly
QUIET = -5          # Errors only
NOT_VERBOSE = 0     # Softspoken: Warnings and errors
VERBOSE = 5         # Informative
DEBUG = 10          # Annoying

# Application State
class AppState:
    
    """Application object.
    Should probably only be instantiated once in main, and should store all of
    the application data for the script
    """
    
    # Our 'private' data members: These are subject to change without notice
    _source_path = ""
    _output_path = ""
    _output_file = None
    _writeout_messages = False
    _verbosity = NOT_VERBOSE
    _file_header = True
    _emit_to_stdout = True
    _filename_regex = None
    _locality = 0
    _options = {    "v": "verbose",
                    "q": "quiet",
                    "d": "debug",
                    "s": "silent",
                    "l": "writeout-messages",
                    "n": "no-header",
                    "f": "file-output-only",
                    "r:": "file-name-regex",
                    "u": "usage" }
    
    # Member function definitions
    def __init__(self, argv):
        
        """Expects command line arguments from execution."""
        
        try:
            opt = ""
            for o in self._options.keys():
                 opt += o
            opts, args = getopt.getopt(argv[1:], opt, self._options.values())
        except getopt.GetoptError, err:
            print str(err)
            self.usage(argv[0])
            sys.exit(2)
        
        for option, value in opts:
            if option in ("-v", self._options["v"]):
                self._verbosity = VERBOSE
            elif option in ("-q", self._options["q"]):
                self._verbosity = QUIET
            elif option in ("-d", self._options["d"]):
                self._verbosity = DEBUG
                self.log("Verbosity set to DEBUG.", DEBUG)
            elif option in ("-s", self._options["s"]):
                self._verbosity = SILENT
            elif option in ("-l", self._options["l"]):
                # Write out log messages at the current verbosity to the
                # Output file
                self._writeout_messages = True
                self.log("Writing messages to output file.", DEBUG)
            elif option in ("-n", self._options["n"]):
                self._file_header = False
                self.log("Not emitting file header.", DEBUG)
            elif option in ("-f", self._options["f"]):
                self._emit_to_stdout = False
                self.log("Not emitting DOT code to stdout.", DEBUG)
            elif option in ("-r", self._options["r:"]):
                self._filename_regex = re.compile(value);
                self.log("Parsing files that match '" + value + "'.", DEBUG)
            elif option in ("-u", self._options["u"]):
                self.usage(argv[0])
                sys.exit(0)
            else:
                self.log("Unknown option '" + option +"'.", QUIET)
                self.usage(argv[0])
                sys.exit(2)
        
        # Expect the value for _source_path
        if len(args) < 1:
            self.log("Not enough arguments provided.", QUIET)
            self.usage(argv[0])
            sys.exit(2)
        
        self._source_path = os.path.abspath(args[0])
        self.log("Set source file to: " + self.source_path(), DEBUG)
        # Test the source directory
        if os.path.exists(self._source_path) == False:
            self.log("Invalid source file given.", QUIET)
            self.usage(argv[0])
            sys.exit(2)
        
        # Optionally set _output_path
        if len(args) > 1:
            self._output_path = os.path.abspath(args[1])
            if os.path.exists(self.output_path()):
                if os.path.isdir(self.output_path()):
                    self.log("Output path is a directory.  Ignoring.", QUIET)
                    self._output_path = ""
                else:
                    self.log("Output path exists.  Clobbering.", VERBOSE)
            if self.output_path():
                #Open the path
                self.log("Outputting graph to file: " + self.output_path(), DEBUG)
                try:
                    self._output_file = open(self.output_path(), 'w')
                except IOError as err:
                    self.log("Could not open output file: " + str(err))
                    self.log("Aborting.", QUIET)
                    sys.exit(3)
                self.log("Successfully opened output file.", DEBUG)
                self.emit_file_header()
        
        self.log("Application context initialized.", DEBUG)
    
    def __del__(self):
        
        """Destructor."""
        
        self.log("Destroying application context.", DEBUG)
        if self._output_file != None:
            self.log("Closing output file.", DEBUG)
            self._output_file.close()
    
    def usage(self, scriptname):
        
        """Prints usage information for depgen.  The first argument is the file
        name of this script.  Usually best to pass sys.argv[0].
        """
        
        opt = ""
        for o in self._options.keys():
             opt += o[0]
        self.log( "USEAGE: " + scriptname + " [-" + opt +
                "] <source dir> [<target dir>]")
    
    def log(self, message, verb = 0):
        
        """Print to stdout and append // so that our output is always
        a valid DOT file.
        """
        
        if self.verbosity() == SILENT:
            return
        
        if self.verbosity() >= verb:
            print str(message)
            if self._writeout_messages and self._output_file != None:
                self.emit_to_file("// " + message)
    
    def source_path(self):
        
        """Return the current source directory."""
        
        return self._source_path
    
    def filename_regex(self):
        
        """Return the regex for matchin files in _source_file"""
        
        return self._filename_regex
    
    def output_path(self):
        
        """Return the current output path."""
        
        return self._output_path
    
    def verbosity(self):
        
        """Return the current verbosity."""
        
        return self._verbosity

    def locality(self):
        return self._locality

    def emit_to_file(self, message, comment = False):
        
        """Emit a string to the output file.
        
        If comment = True, then prefix with // as per DOT language specs.
        """
        
        if self._output_file == None:
            self.log("Tried to emit to file when one wasn't set.", DEBUG)
            return
        if comment == True:
            self._output_file.write("// ")
        self._output_file.write(str(message) + '\n')
        

    def emit_file_header(self):
        
        """Emit an informative file header."""
        
        self.log("Emitting file header.", DEBUG)
        
        basename = os.path.basename(self.output_path())
        self.emit_to_file("Dependancy graph of " + basename, True)

class Parser:
    app = None
    
    def __init__(self, a):
        a.log("Initializing parser context", DEBUG)
        app = a
    
    def __del__(self):
        app.log("Destroying parser context", DEBUG)
    
    def parse(self):
        
        """Parse the file at app.source_path().
        
        If the file is a directory, search through it's listing with the user-
        defined or default regexp and parse the results one by one.
        """
        
        app.log("Opening source file.", DEBUG)
        if os.path.isdir(app.source_path()) == True:
            regex = app.filename_regex()
            if regex == None:
                # Set default filename_regexp: Assume we're dealing with headers
                regex = re.compile(".*\.h")
            app.log("Searching directory for '" + regex.pattern +
                    "' matches.", DEBUG)
            files = os.listdir(app.source_path())
            matches = []
            for f in files:
                if regex.search(f) != None:
                    matches.append(os.path.join(app.source_path(), f))
            app.log("Parsing " + str(len(matches)) + " files.", VERBOSE)
            for match in matches:
                self.parse_file(match)
        else:
            if app.filename_regex() != None:
                app.log("Source is a file, but filename regex is defined.")
            self.parse_file(app.source_path())
        # Print dictionary in DOT language
    
    def parse_file(self, filename):
        
        """Parse a file and output the results to the open output file using
        app.
        
        Filename expects an absolute path.
        """
        
        try:
            source_file = open(filename, 'r')
        except IOError as err:
            app.log("Could not open source file: " + str(err), QUIET)
            return False
        app.log("Parsing file '" + str(filename) + "'.", DEBUG)
        # Read file into buffer
        # Search for include syntax based on app.locality()
        # Add files links to dictionary

if __name__ == "__main__":
     app = AppState(sys.argv)
     p = Parser(app)
     p.parse()
     del p
     del app #if we don't do this, it cleans up the globals before deleting
