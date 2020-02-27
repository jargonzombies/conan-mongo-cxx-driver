from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration
import os


class MongoCxxConan(ConanFile):
    name = "mongo-cxx-driver"
    version = "3.4.0"
    url = "http://github.com/bincrafters/conan-mongo-cxx-driver"
    description = "C++ Driver for MongoDB"
    license = "Apache-2.0"
    settings = "os", "compiler", "arch", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "polyfill": ["std", "boost", "mnmlstc", "experimental"]
    }
    default_options = {"shared": False, "fPIC": True, "polyfill": "boost"}
    requires = "mongo-c-driver/1.16.1@bincrafters/stable"
    generators = "cmake"

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def config_options(self):
        if self.settings.compiler == 'Visual Studio' and self.options.polyfill != "boost":
            raise ConanInvalidConfiguration("For MSVC, best to use the boost polyfill")

        if self.options.polyfill == "std":
            tools.check_min_cppstd(self, "17")

        if self.options.polyfill == "boost":
            self.requires("boost_optional/1.69.0@bincrafters/stable")

        # Cannot model mnmlstc (not packaged, is pulled dynamically) or
        # std::experimental (how to check availability in stdlib?) polyfill
        # dependencies

    def source(self):
        remote = "https://github.com/mongodb/mongo-cxx-driver/archive/r{0}.tar.gz"
        tools.get(remote.format(self.version))
        extracted_dir = "mongo-cxx-driver-r{0}".format(self.version)
        os.rename(extracted_dir, self._source_subfolder)

    def build(self):
        conan_magic_lines = '''project(MONGO_CXX_DRIVER LANGUAGES CXX)
        include(../conanbuildinfo.cmake)
        conan_basic_setup()
        '''

        cmake_file = os.path.join(self._source_subfolder, "CMakeLists.txt")
        tools.replace_in_file(cmake_file, "project(MONGO_CXX_DRIVER LANGUAGES CXX)", conan_magic_lines)

        cmake = CMake(self)
        if self.settings.compiler == 'Visual Studio':
            cmake.definitions["BSONCXX_POLY_USE_BOOST"] = 1

        cmake.definitions["BSONCXX_POLY_USE_MNMLSTC"] = self.options.polyfill == "mnmlstc"
        cmake.definitions["BSONCXX_POLY_USE_STD_EXPERIMENTAL"] = self.options.polyfill == "experimental"
        cmake.definitions["BSONCXX_POLY_USE_BOOST"] = self.options.polyfill == "boost"
        cmake.definitions["BSONCXX_POLY_USE_STD"] = self.options.polyfill == "std"
        cmake.configure(source_dir=self._source_subfolder)
        cmake.build()

    def package(self):
        self.copy(pattern="COPYING*", src=self._source_subfolder)
        self.copy(pattern="*.hpp", src=os.path.join(self._source_subfolder, "src", "bsoncxx"), dst=os.path.join("include", "bsoncxx"), keep_path=True)
        self.copy(pattern="*.hpp", src=os.path.join(self._source_subfolder, "src", "mongocxx"), dst=os.path.join("include", "mongocxx"), keep_path=True)
        self.copy(pattern="*.hpp", src="src/bsoncxx", dst="include/bsoncxx", keep_path=True)
        self.copy(pattern="*.hpp", dst="include/mongocxx", src="src/mongocxx", keep_path=True)
        self.copy(pattern="*.hpp", src="src/bsoncxx/third_party/EP_mnmlstc_core-prefix/src/EP_mnmlstc_core/include/core", dst="include/bsoncxx/third_party/mnmlstc/core", keep_path=False)

        try:
            os.rename("lib/libmongocxx-static.a", "lib/libmongocxx.a")
        except:
            pass
        try:
            os.rename("lib/libbsoncxx-static.a", "lib/libbsoncxx.a")
        except:
            pass
        try:
            os.rename("lib/libmongocxx-static.lib", "lib/libmongocxx.lib")
        except:
            pass
        try:
            os.rename("lib/libbsoncxx-static.lib", "lib/libbsoncxx.lib")
        except:
            pass

        self.copy(pattern="lib*cxx.lib", src="lib", dst="lib", keep_path=False)
        self.copy(pattern="lib*cxx.a", src="lib", dst="lib", keep_path=False)
        self.copy(pattern="lib*cxx.so*", src="lib", dst="lib", keep_path=False)
        self.copy(pattern="lib*cxx.dylib", src="lib", dst="lib", keep_path=False)
        self.copy(pattern="lib*cxx._noabi.dylib", src="lib", dst="lib", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ['mongocxx', 'bsoncxx']
        self.cpp_info.includedirs.append('include/bsoncxx/third_party/mnmlstc')
