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
                    "emit_to_stdout": False,
                    "include_orphans": False,
                    "filename_regex": None,
                    "ranksep": 3,
                    "recursive": False
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
                    "w": ("writeout",
                        "Write messages to output file."),
                    "n": ("noheader",
                        "Do not include a header in the output file."),
                    "t": ("stdout",
                        "Force messages to stdout to be valid DOT."),
                    "f:": ("regex",
                        "Specify the regex for '#include' statement."),
                    "i": ("orphans",
                        "Explicitly include nodes that have no children."),
                    "u": ("usage",
                        "Print this usage information."),
                    "r:": ("ranksep",
                        "Explicitly set GraphViz 'ranksep' value."),
                    "R:": ("recursive",
                        "Searches source directory recursively for X files.")
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
            if self.handle_arguments(option, value) != True:
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
    
    def handle_arguments(self, option, value):
        """Support function for handling cl arguments."""
        
        if option in ("-v", self._options["v"]):
            self.options["verbosity"] = VERBOSE
            return True
        elif option in ("-q", self._options["q"]):
            self.options["verbosity"] = QUIET
            return True
        elif option in ("-d", self._options["d"]):
            self.options["verbosity"] = DEBUG
            self.log("Verbosity set to DEBUG.", DEBUG)
            return True
        elif option in ("-s", self._options["s"]):
            self.options["verbosity"] = SILENT
            return True
        elif option in ("-w", self._options["w"]):
            # Write log messages at the current verbosity to the output file
            self.options["writeout"] = True
            self.log("Writing messages to output file.", DEBUG)
            return True
        elif option in ("-n", self._options["n"]):
            self.options["output_header"] = False
            self.log("Not emitting file header.", DEBUG)
            return True
        elif option in ("-t", self._options["t"]):
           self.options["emit_to_stdout"] = True
           self.log("Emitting DOT code to stdout.", DEBUG)
           return True
        elif option in ("-f", self._options["f:"]):
            self.options["filename_regex"] = re.compile(value);
            self.log("Parsing files that match '" + value + "'.", DEBUG)
            return True
        elif option in ("-u", self._options["u"]):
            # Print usage
            self.usage(argv[0])
            sys.exit(0)
            return True
        elif option in ("-i", self._options["i"]):
            # Include orphan nodes (no connections in or out)
            self.options["include_orphans"] = True
            self.log("Including orphan nodes in output graph.", DEBUG)
            return True
        elif option in ("-r", self._options["r:"]):
            self.options["ranksep"] = value
            self.log("Ranksep set to " + value, DEBUG)
            return True
        elif option in ("-R", self._options["R:"]):
            if int(value) < 0:
                self.log("Bad value for --recursive: %s" % value, QUIET)
                return False
            self.options["recursive"] = int(value)
            self.log("Recursively searching up to %s directories." % value,
                     DEBUG)
            return True
        else:
            return False
    
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
        self.log("USEAGE: " + scriptname + " [-" + opt +
                 "] <source dir> [<target dir>]")
        for key in self._options.keys():
            self.log("-%s  --%s\t%s" % (
                key[0], self._options[key][0], self._options[key][1]))
    
    def log(self, message, verb = 0, newline = True):
        
        """Print to stdout and append // so that our output is always
        a valid DOT file.
        """
        
        if self.options["verbosity"] == SILENT:
            # -sw should emit messages to file at normal verbosity
            if self.options["writeout"] == True:
                if verb <= NOT_VERBOSE:
                    self.emit(message, True)
            return
        
        if self.options["verbosity"] >= verb:
            if self.options["emit_to_stdout"] == True:
                sys.stdout.write(self.dot(str(message), True))
            else:
                sys.stdout.write(str(message))
            if newline == True:
                sys.stdout.write('\n')
            if self.options["writeout"] == True:
                self.emit(message, True, newline)
    
    def source_path(self):
        
        """Return the current source directory."""
        
        return self._source_path
    
    def output_path(self):
        
        """Return the current output path."""
        
        return self._output_path
    
    def dot(self, message, comment = False):
        """Return a line of valid DOT code which respects the current indent
        value and structures comments correctly.
        
        Does not syntax check code, though this might be an interesting feature
        to support one day.
        """
        
        out = ""
        for x in range(self.indent):
            out += '\t'
        if comment == True:
            out += "// "
        return out + message
    
    def emit(self, message, comment = False, newline = True):
        
        """Emit a string to the output file.
        
        If comment = True, then prefix with // as per DOT language specs.
        """
        
        vd = self.dot(message, comment)
        
        if self.options["emit_to_stdout"] == True:
            sys.stdout.write(vd)
            if newline == True:
                sys.stdout.write('\n')
        
        if self._output_file == None:
            return
        
        self._output_file.write(vd)
        if newline == True:
            self._output_file.write('\n')
    
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
    
    # Make sure we don't go on forever
    _current_depth = 0
    
    _total_file_count = 0
    
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
        self.included_re = re.compile('([^\"]+)')
        
        self.app.log("Include statement regex: %s " % self.include_re.pattern,
                     DEBUG)
        self.app.log("Filename regex: %s" % self.path_re.pattern, DEBUG )
        
    
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
                self.app.emit('"%s";' % name)
        
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
            # Make sure we reinit recursion max depth
            self._current_depth = 0
            self.parse_directory(self.app.source_path())
        else:
            if self.app.options["filename_regex"] != None:
                self.app.log("Source is a file, but filename regex is defined.")
            self.parse_file(app.source_path())
        
        # Emit graph
        self.emit_graph()
        
        # Print statistics
        self.app.log("Parsed %s files." % self._total_file_count, VERBOSE)
    
    def parse_directory(self, dirpath):
        
        """Parse a directory using the regex, sending each matching filename
        to parse_file
        
        Dirpath needs to be absolute or relative to the cdw.
        """
        
        self.app.log("Searching directory '%s'." % dirpath, DEBUG)
        
        # List directories
        files = os.listdir(dirpath)
        matches = []
        for f in files:
            # If directories exist, check the max depth and recurse
            full = os.path.join(dirpath, f)
            if os.path.isdir(full) == True:
                self._current_depth += 1
                if self._current_depth < self.app.options["recursive"]:
                    self.app.log("Recursing on '%s'. Depth: %i" %
                                (full, self._current_depth), DEBUG)
                    self.parse_directory(full)
                else:
                    if self.app.options["recursive"] > 0:
                        self.app.log("Maximum recursion depth reached.  \
                                     Not searching '%s'." % f, DEBUG)
                self._current_depth -= 1
            
            # If not, process the directory
            if self.path_re.search(full) != None:
                matches.append(full)
        
        # Now parse the files we found
        for match in matches:
            self.parse_file(match)
        
    
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
        self.app.log("Parsing '" + shortname + "': ", DEBUG, False)
        
        matches = []
        for line in source_file:
            if self.include_re.match(line) != None:
                matches.append(self.included_re.split(line)[3])
        if len(matches) > 0:
            self.graph.append((shortname, matches))
        else:
            self.sterile.append(shortname)
        
        self.app.log(str(len(matches)) + " files #included.", DEBUG)
        
        # Clean up
        source_file.close()
        
        # Add to the count
        self._total_file_count += 1


if __name__ == "__main__":
     app = AppState(sys.argv)
     p = Parser(app)
     p.parse()
     del p
     del app #if we don't do this, it cleans up the globals before deleting
