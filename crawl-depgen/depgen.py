#!/usr/bin/python

import sys
import os
import time
import getopt

"""Depgen - A C/C++ header file dependancy generator that ouputs a graph in
the DOT graph description language.

Usage should be to initialize App with the command line arguments obtained by
syst.argv. This is because the usage depends on the first argument being the
filename called to run the script.  Basically it reads .h files in order

Written by Chris Galardi ~5/2010
"""

# "Constants"
SILENT = -10        # Tell us nothing
QUIET = -5          # Errors only
NOT_VERBOSE = 0     # Softspoken
VERBOSE = 5         # Lots of messages
DEBUG = 10          # Tell us everything

# Application State
class AppState:
    
    """Application object.
    Should probably only be instantiated once in main, and should store all of
    the application data for the script
    """
    
    # Our 'private' data members: These are subject to change without notice
    _source_dir = ""
    _output_path = ""
    _output_file = None
    _writeout_messages = False
    _options = {    "v": "verbose",
                    "q": "quiet",
                    "d": "debug",
                    "s": "silent",
                    "l": "writeout-messages"  }
    _verbosity = NOT_VERBOSE
    
    # Member function definitions
    def __init__(self, argv):
        
        """Class init method.  Expects command line arguments from execution."""
        
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
            else:
                self.log("Unknown option '" + option +"'.", QUIET)
                self.usage(argv[0])
                sys.exit(2)
        
        # Expect the value for _source_dir
        if len(args) < 1:
            self.log("Not enough arguments provided.", QUIET)
            self.usage(argv[0])
        
        self.log("AppState initialized.", DEBUG)
    
    def usage(self, scriptname):
        
        """Prints usage information for depgen.  The first argument is the file
        name of this script.  Usually best to pass sys.argv[0].
        """
        
        opt = ""
        for o in self._options.keys():
             opt += o
        self.log(  scriptname + " [-" + opt +
                "] <source dir> [<target dir>]", QUIET)
    
    def log(self, message, verb = 0):
        
        """Print to stdout and append // so that our output is always
        a valid DOT file.
        """
        
        if self.verbosity() >= verb and self.verbosity() > SILENT:
            print str(message)
        
        if self.verbosity() == DEBUG and self._output_file != None:
            self.emit_to_file("// " + message)
    
    def source_directory(self):
        
        """Return the current source directory."""
        
        return self._source_dir
    
    def output_path(self):
        
        """Return the current output path."""
        
        return self._output_path
    
    def verbosity(self):
        
        """Return the current verbosity."""
        
        return self._verbosity



if __name__ == "__main__":
     app = AppState(sys.argv)
