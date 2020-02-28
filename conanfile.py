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
            self.requires("boost_smart_ptr/1.69.0@bincrafters/stable")

        # Cannot model mnmlstc (not packaged, is pulled dynamically) or
        # std::experimental (how to check availability in stdlib?) polyfill
        # dependencies

    def configure(self):
        tools.check_min_cppstd(self, "11")

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

        if self.settings.compiler == "Visual Studio":
            conan_magic_lines += "add_definitions(-D_ENABLE_EXTENDED_ALIGNED_STORAGE)"

        cmake_file = os.path.join(self._source_subfolder, "CMakeLists.txt")
        tools.replace_in_file(cmake_file, "project(MONGO_CXX_DRIVER LANGUAGES CXX)", conan_magic_lines)
        cmake = CMake(self)
        cmake.definitions["BSONCXX_POLY_USE_MNMLSTC"] = self.options.polyfill == "mnmlstc"
        cmake.definitions["BSONCXX_POLY_USE_STD_EXPERIMENTAL"] = self.options.polyfill == "experimental"
        cmake.definitions["BSONCXX_POLY_USE_BOOST"] = self.options.polyfill == "boost"
        cmake.configure(source_dir=self._source_subfolder)
        cmake.build()

    def package(self):
        # Do not reconfigure because that causes a full rebuild
        CMake(self).install()

    def package_info(self):
        # Need to ensure mongocxx is linked before bsoncxx
        self.cpp_info.libs = sorted(tools.collect_libs(self), reverse=True)
        self.cpp_info.includedirs.extend([os.path.join("include", x, "v_noabi") for x in ["bsoncxx", "mongocxx"]])

        if self.options.polyfill == "mnmlstc":
            self.cpp_info.includedirs.append(os.path.join("include", "bsoncxx", "third_party", "mnmlstc"))

        if not self.options.shared:
            self.cpp_info.defines.extend(["BSONCXX_STATIC", "MONGOCXX_STATIC"])

