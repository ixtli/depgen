#!/usr/bin/python

import sys
import os
import time
import getopt
import re
import tokenize

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
    
    # Current indent in output file
    indent = 0
    
    # Dictionary of app options (state)
    options =   {   "verbosity": NOT_VERBOSE,
                    "output_header": True,
                    "writeout": False,
                    "emit_to_stdout": True,
                    "include_orphans": False,
                    "filename_regex": None,
                    "ranksep": 3
                }
    
    # Our 'private' data members: These are subject to change without notice
    _source_path = ""
    _output_path = ""
    _output_file = None
    
    # Dictionary of command line options.
    _options =  {   "v": ("verbose",
                        "Print informative messages."),
                    "q": ("quiet", 
                        "Print errors only."),
                    "d": ("debug",
                        "Print everything we know about what we're doing."),
                    "s": ("silent",
                        "Print nothing."),
                    "l": ("writeout",
                        "Emit DOT output to stdout."),
                    "n": ("no-output-header",
                        "Do not include a header in the output file."),
                    "t": ("stdout-only",
                        "Do not write an output file."),
                    "f:": ("filename-regex",
                        "Specify the regex for '#include' statement."),
                    "i": ("include-sterile",
                        "Explicitly include nodes that have no children."),
                    "u": ("usage",
                        "Print this usage information."),
                    "r:": ("ranksep",
                        "Explicitly set GraphViz 'ranksep' value.")
                }
    
    # Member function definitions
    def __init__(self, argv):
        
        """Expects command line arguments from execution."""
        
        opt = ""
        longopt = []
        for o in self._options.keys():
             opt += o
        for o in self._options.values():
            longopt.append(o[0])
        try:
            opts, args = getopt.getopt(argv[1:], opt, longopt)
        except getopt.GetoptError, err:
            print str(err)
            self.usage(argv[0])
            sys.exit(2)
        
        for option, value in opts:
            if option in ("-v", self._options["v"]):
                self.options["verbosity"] = VERBOSE
            elif option in ("-q", self._options["q"]):
                self.options["verbosity"] = QUIET
            elif option in ("-d", self._options["d"]):
                self.options["verbosity"] = DEBUG
                self.log("Verbosity set to DEBUG.", DEBUG)
            elif option in ("-s", self._options["s"]):
                self.options["verbosity"] = SILENT
            elif option in ("-l", self._options["l"]):
                # Write log messages at the current verbosity to the output file
                self.options["writeout"] = True
                self.log("Writing messages to output file.", DEBUG)
            elif option in ("-n", self._options["n"]):
                self.options["output_header"] = False
                self.log("Not emitting file header.", DEBUG)
            elif option in ("-t", self._options["t"]):
               self.options["emit_to_stdout"] = False
               self.log("Not emitting DOT code to stdout.", DEBUG)
            elif option in ("-f", self._options["f:"]):
                self.options["filename_regex"] = re.compile(value);
                self.log("Parsing files that match '" + value + "'.", DEBUG)
            elif option in ("-u", self._options["u"]):
                # Print usage
                self.usage(argv[0])
                sys.exit(0)
            elif option in ("-o", self._options["o"]):
                # Include orphan nodes (no connections in or out)
                self.options["include_orphans"] = True
                self.log("Including orphan nodes in output graph.", VERBOSE)
            elif option in ("-r", self._options["r:"]):
                self.options["ranksep"] = value
                self.log("Ranksep set to " + value, DEBUG)
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
                self.log("Outputting graph to file: " + self.output_path(),
                         VERBOSE)
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
        
        if self.options["verbosity"] == SILENT:
            return
        
        if self.options["verbosity"] >= verb:
            print str(message)
            if self.options["writeout"] and self._output_file != None:
                self.emit("// " + message)
    
    def source_path(self):
        
        """Return the current source directory."""
        
        return self._source_path
    
    def output_path(self):
        
        """Return the current output path."""
        
        return self._output_path
    
    def emit(self, message, comment = False):
        
        """Emit a string to the output file.
        
        If comment = True, then prefix with // as per DOT language specs.
        """
        
        if self._output_file == None:
            self.log("Tried to emit to file when one wasn't set.", DEBUG)
            return
        
        tabs = ""
        for x in range(self.indent):
            tabs += '\t'
        self._output_file.write(tabs)
        
        if comment == True:
            self._output_file.write("// ")
        
        self._output_file.write(str(message) + '\n')
    
    def emit_file_header(self):
        
        """Emit an informative file header."""
        
        self.log("Emitting file header.", DEBUG)
        
        basename = os.path.basename(self.source_path())
        self.emit("Dependancy graph of '" + basename + "'", True)


class Parser:
    
    """Parser class.
    
    Given an Application object, it parses the source file and generates an
    input dep graph based on it.
    """
    
    app = None
    path_re = None
    include_re = None
    included_re = None
    
    graph = []
    sterile = []  # nodes with no children
    
    def __init__(self, a):
        a.log("Initializing parser.", DEBUG)
        self.app = a
        self.app.log("Compiling regexp parsers.", DEBUG)
        path_re = self.app.options["filename_regex"]
        if self.path_re == None:
            # Set default filename_regexp: Assume we're dealing with headers
            self.path_re = re.compile(".*\.h")
        self.include_re = re.compile('^\s*\#include \"[^\"]+\"')
        self.app.log("Include statement regex: '"+self.include_re.pattern+"'.",
                     DEBUG)
        self.included_re = re.compile('([^\"]+)')
    
    def __del__(self):
        self.app.log("Destroying parser context.", DEBUG)
    
    def emit_graph_prologue(self):
        self.app.emit("digraph g {")
    
    def emit_graph_epilogue(self):
        self.app.emit("}\n")
    
    def emit_graph_options(self):
        self.app.emit("Graph Settings", True)
        self.app.emit("ranksep=%i;" % self.app.options["ranksep"])
    
    def emit_graph_content(self):
        self.app.log("Emitting graph contents.", DEBUG)
        # Optionally include orphan nodes first
        # TODO: Make this check to see if it's really an orphan.
        if app.options["include_orphans"] == True:
            self.app.emit("Orphan nodes:", True)
            for name in self.sterile:
                self.app.emit("'%s';" % name)
        
        # Print the rest
        for include in self.graph:
            self.app.emit("Files included by " + include[0], True)
            for included in include[1]:
                self.app.emit('"%s" -> "%s";' % (include[0], included))
    
    def emit_graph(self):
        self.app.log("Emitting graph.", DEBUG)
        # Start file
        self.emit_graph_prologue()
        
        # Print dictionary in DOT language
        self.app.indent = 1
        self.emit_graph_options()
        self.emit_graph_content()
        self.app.indent = 0
        
        # Finish file
        self.emit_graph_epilogue()
    
    def parse(self):
        
        """Parse the file at app.source_path().
        
        If the file is a directory, search through it's listing with the user-
        defined or default regexp and parse the results one by one.
        """
        
        self.app.log("Opening source file.", DEBUG)
        if os.path.isdir(self.app.source_path()) == True:
            self.app.log("Searching directory for '" + self.path_re.pattern +
                    "' matches.", DEBUG)
            files = os.listdir(self.app.source_path())
            matches = []
            for f in files:
                if self.path_re.search(f) != None:
                    matches.append(os.path.join(self.app.source_path(), f))
            self.app.log("Parsing " + str(len(matches)) + " files.", VERBOSE)
            for match in matches:
                self.parse_file(match)
        else:
            if self.app.options["filename_regex"] != None:
                self.app.log("Source is a file, but filename regex is defined.")
            self.parse_file(app.source_path())
        
        # Emit graph
        self.emit_graph()
    
    def parse_file(self, filename):
        
        """Parse the file at filename and output the results to the output file
        app has open.
        
        Filename expects an absolute path.
        """
        
        try:
            source_file = open(filename, 'r')
        except IOError as err:
            self.app.log("Could not open source file: " + str(err), QUIET)
            return False
        
        shortname = os.path.basename(str(filename))
        self.app.log("Parsing '" + shortname + "'.", DEBUG)
        
        matches = []
        for line in source_file:
            if self.include_re.match(line) != None:
                matches.append(self.included_re.split(line)[3])
        if len(matches) > 0:
            self.app.log(str(len(matches)) + " files #included in: "
                         + shortname, DEBUG)
            self.graph.append((shortname, matches))
        else:
            self.app.log("No #include statements found in file: " + 
                         shortname, DEBUG)
            self.sterile.append(shortname)
        
        # Clean up
        source_file.close()


if __name__ == "__main__":
     app = AppState(sys.argv)
     p = Parser(app)
     p.parse()
     del p
     del app #if we don't do this, it cleans up the globals before deleting
