import distutils.core
import getopt
import glob
import os
import os.path
import py2exe
import re
import shutil
import sys
import types
import _winreg

from appsnaplib import defines, strings, version

# Class to build application
class build:
    # Constructor
    def __init__(self):
        # Set source directory
        path = os.path.dirname(sys.argv[0])
        if path == os.getcwd(): self.path = ''
        else: self.path = path + os.path.sep
        
        # Set appname
        self.appname = version.APPNAME.lower()
        
        [p, r, u, z, n] = self.parse_arguments()

        self.setup()
        self.get_dependencies()
        
        if p: self.build_executable()
        if r: self.rezip_shared_library()
        if u: self.upx_compress()
        if z and n: self.delete_older_packages()
        if z: self.build_zip_package()
        if n: self.build_nsis_package()
        
    # Setup the build
    def setup(self):
        # Initialize
        self.py2exe = {}
        
        # Files to add in zip package
        self.zip_package_files = ['*.py',
                                  'db.ini',
                                  'config.ini',
                                  'appsnap.ico',
                                  'appsnapsetup.nsi',
                                  'appsnap.html',
                                  'locale' + os.path.sep + '*' + os.path.sep + 'LC_MESSAGES' + os.path.sep + 'appsnap.*',
                                  'appsnaplib' + os.path.sep + '*.py'
                                  ]
        
        # Create manifest
        manifest = """
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <assembly xmlns="urn:schemas-microsoft-com:asm.v1"
            manifestVersion="1.0">
            <assemblyIdentity
                version="0.64.1.0"
                processorArchitecture="x86"
                name="Controls"
                type="win32"
            />
            <description>myProgram</description>
            <dependency>
                <dependentAssembly>
                    <assemblyIdentity
                        type="win32"
                        name="Microsoft.Windows.Common-Controls"
                        version="6.0.0.0"
                        processorArchitecture="X86"
                        publicKeyToken="6595b64144ccf1df"
                        language="*"
                    />
                </dependentAssembly>
            </dependency>
            </assembly>
        """
        
        # Console executable
        self.py2exe['console'] = [{
                         "script"          : self.path + "appsnap.py",
                         "icon_resources"  : [(1, self.path + "appsnap.ico")]
               }]
        
        # GUI executable
        self.py2exe['windows'] = [{
                         "script"          : self.path + "appsnapgui.py",
                         "icon_resources"  : [(1, self.path + "appsnap.ico")],
                         "other_resources" : [(24, 1, manifest)]
                         }]
        
        # Py2Exe options
        self.py2exe['options'] = {
                        "py2exe": {
                                   "packages" : ["encodings"],
                                   "optimize" : 2,
                                   "compressed" : 0,
                                   }
                       }
        
        # Resource files to include
        self.py2exe['data_files'] = [(
                            "" , 
                            [self.path + "appsnap.ico",
                             self.path + "db.ini",
                             self.path + "config.ini",
                             self.path + "appsnap.html", 
                             os.path.join(os.getenv("systemroot"), "system32", "msvcp71.dll")]
                            )]
        
        # Name of zip file to generate
        self.py2exe['zipfile'] = "shared.lib"
        
        # Specify py2exe as a command line option
        sys.argv = [sys.argv[0], 'py2exe']
        
    # Parse arguments
    def parse_arguments(self):
        help = """
%s:
  build.py [%s]
  -p    %s
  -r    %s
  -u    %s
  -z    %s
  -n    %s""" % (
                 strings.USAGE,
                 strings.OPTIONS,
                 strings.BUILD_EXECUTABLE_USING_PY2EXE,
                 strings.REZIP_USING_SEVENZIP,
                 strings.COMPRESS_USING_UPX,
                 strings.CREATE_ZIP_PACKAGE,
                 strings.CREATE_NSIS_PACKAGE
                 )
    
        # Set defaults
        if len(sys.argv) == 1:
            p = r = u = z = n = True
        else:
            p = r = u = z = n = False
            try:
                opts, args = getopt.getopt(sys.argv[1:], 'pruznh')
            except getopt.GetoptError:
                print help
                sys.exit(defines.ERROR_GETOPT)
    
            for o, a in opts:
                if o == '-p': p = True
                if o == '-r': r = True
                if o == '-u': u = True
                if o == '-z': z = True
                if o == '-n': n = True
                if o == '-h':
                    print help
                    sys.exit(defines.ERROR_HELP)
            
        return [p, r, u, z, n]
            
    # Get build dependencies
    def get_dependencies(self):
        self.sevenzip = self.get_registry_key(_winreg.HKEY_LOCAL_MACHINE,
                                              'SOFTWARE\\7-Zip',
                                              'Path'
                                              ) + os.path.sep + '7z.exe'
        if self.sevenzip == os.path.sep + '7z.exe' or not os.path.exists(self.sevenzip):
            self.error_out(strings.SEVENZIP_NOT_AVAILABLE)
            
        self.upx = os.path.expandvars('${systemroot}\\upx.exe')
        if not os.path.exists(self.upx):
            self.error_out(strings.UPX_NOT_AVAILABLE)
            
        self.nsis = self.get_registry_key(_winreg.HKEY_LOCAL_MACHINE,
                                          'SOFTWARE\\NSIS',
                                          '') + os.path.sep + 'makensis.exe'
        if self.nsis == os.path.sep + 'makensis.exe' or not os.path.exists(self.nsis):
            self.error_out(strings.NSIS_NOT_AVAILABLE)
            
    # Execute Py2Exe to generate executables
    def build_executable(self):
        command = 'distutils.core.setup('
        for key in self.py2exe:
            if type(self.py2exe[key]) is types.StringType:
                command += key + ' = "' + self.py2exe[key] + '", '
            else:
                command += key + ' = ' + self.py2exe[key].__str__() + ', '
        command = command[:-2] + ')'
        eval(command)
        os.system('rd build /s /q')
        
    # Rezip shared library
    def rezip_shared_library(self):
        if self.py2exe.has_key('zipfile'):
            os.system('""' + self.sevenzip + '" -aoa x -y "dist' + os.path.sep + self.py2exe['zipfile'] + '" -o"dist' + os.path.sep + 'shared""')
            os.chdir('dist' + os.path.sep + 'shared')
            os.system('""' + self.sevenzip + '" a -tzip -mx9 -r "..' + os.path.sep + self.py2exe['zipfile'] + '""')
            os.chdir('..')
            os.system('rd shared /s /q')
            os.chdir('..')
    
    # Compressing executables with UPX
    def upx_compress(self):
        os.system('""' + self.upx + '" --best "dist' + os.path.sep + '*')
    
    # Delete older packages
    def delete_older_packages(self):
        files = glob.glob(self.appname + 'setup-*.exe')
        files.extend(glob.glob(self.appname + '-*.zip'))
        for file in files:
            print file
            os.remove(file)
    
    # Create ZIP package
    def build_zip_package(self):
        if self.path != '':
            pwd = os.getcwd()
            os.chdir(self.path)

        zipfile = self.appname + '-' + version.APPVERSION + '.zip'
        command = '""' + self.sevenzip + '" a -tzip -mx9 ' +  zipfile + ' '
        for file in self.zip_package_files:
            command += file + ' '
        command += '"'
        os.system(command)

        if self.path != '':
            os.chdir(pwd)
            os.rename(self.path + zipfile, zipfile)
    
    # Package with NSIS
    def build_nsis_package(self):
        lines = open(self.path + self.appname + 'setup.nsi').read()
        lines = re.sub('#VERSION#', version.APPVERSION, lines)
        lines = re.sub('#SRC_PATH#', re.sub('\\\\', '\\\\\\\\', self.path), lines)
        o = open('temp.nsi', 'w')
        o.write(lines)
        o.close()
        os.system('""' + self.nsis + '" temp.nsi"')
        os.remove('temp.nsi')
        
    # Die on error
    def error_out(self, text):
        print text + '. ' + strings.BUILD_FAILED
        sys.exit(defines.ERROR_BUILD_FAILED)

    # Get data from the registry
    def get_registry_key(self, database, key, value):
        try:
            key = _winreg.OpenKey(database, key)
            data, temp = _winreg.QueryValueEx(key, value)
            _winreg.CloseKey(key)
        except WindowsError:
            data = ''
            
        return data
    
if __name__ == '__main__':
    build()