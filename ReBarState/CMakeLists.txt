cmake_minimum_required(VERSION 3.30)

# Enable CMake's native `import std` support before the compiler is probed.
# The gate token is specific to the CMake version in use (4.4 here).
if(NOT DEFINED CMAKE_EXPERIMENTAL_CXX_IMPORT_STD)
    set(CMAKE_EXPERIMENTAL_CXX_IMPORT_STD "f35a9ac6-8463-4d38-8eec-5d6008153e7d")
endif()

# Select libc++ before the compiler is probed, so `import std` metadata detection
# (which runs during project()) resolves to libc++.modules.json rather than libstdc++.
if(NOT CMAKE_HOST_WIN32)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -stdlib=libc++")
endif()

project("NvStrapsReBar" LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_SCAN_FOR_MODULES ON)

include(cmake/LocalModulePath.cmake)

if(WIN32)
    include(CxxStdModule)            # header-module (Clang) / std.ixx (MSVC) provider
else()
    set(CMAKE_CXX_MODULE_STD ON)     # Linux: use CMake's built-in `import std` (libc++)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(PCI REQUIRED IMPORTED_TARGET libpci)   # human-readable GPU names
endif()

if(NOT REBAR_DXE_DIRECTORY)
    cmake_path(SET REBAR_DXE_DIRECTORY NORMALIZE "${CMAKE_CURRENT_SOURCE_DIR}/../ReBarDxe")
endif()

add_executable(NvStrapsReBar
        "${REBAR_DXE_DIRECTORY}/include/LocalAppConfig.h"
        "${REBAR_DXE_DIRECTORY}/include/DeviceRegistry.h"
        "${REBAR_DXE_DIRECTORY}/DeviceRegistry.c"
        "${REBAR_DXE_DIRECTORY}/include/EfiVariable.h"
        "${REBAR_DXE_DIRECTORY}/EfiVariable.c"
        "${REBAR_DXE_DIRECTORY}/include/NvStrapsConfig.h"
        "${REBAR_DXE_DIRECTORY}/NvStrapsConfig.c"
        "${REBAR_DXE_DIRECTORY}/include/StatusVar.h"
        "${REBAR_DXE_DIRECTORY}/StatusVar.c"
        "ReBarState.cc")

set_property(SOURCE
	"${REBAR_DXE_DIRECTORY}/DeviceRegistry.c"
	"${REBAR_DXE_DIRECTORY}/EfiVariable.c"
	"${REBAR_DXE_DIRECTORY}/NvStrapsConfig.c"
	"${REBAR_DXE_DIRECTORY}/StatusVar.c"

	# for clang to compile as C++, but not include C++ headers and libraries
	APPEND PROPERTY COMPILE_DEFINITIONS "NVSTRAPS_DXE_DRIVER")

# The shared DXE C sources are compiled as C++ (matching the upstream build) so
# the module TUs that call them see consistent C++ linkage.
set_source_files_properties(
	"${REBAR_DXE_DIRECTORY}/DeviceRegistry.c"
	"${REBAR_DXE_DIRECTORY}/EfiVariable.c"
	"${REBAR_DXE_DIRECTORY}/NvStrapsConfig.c"
	"${REBAR_DXE_DIRECTORY}/StatusVar.c"
	PROPERTIES LANGUAGE CXX)

# Cross-platform C++ module interface units.
target_sources(NvStrapsReBar
	PRIVATE FILE_SET CXX_MODULES BASE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}" FILES
	"LocalAppConfig.ixx"
	"StatusVar.ixx"
	"DeviceRegistry.ixx"
        "DeviceList.ixx"
        "TextWizardPage.ixx"
        "NvStrapsConfig.ixx"
        "TextWizardMenu.ixx"
        "ConfigurationWizard.ixx"
    )

# Windows-only modules (WinAPI / DXGI / SetupAPI wrappers).
if(WIN32)
    target_sources(NvStrapsReBar
	PRIVATE "cxx_std_lib.hh"
	PRIVATE FILE_SET CXX_MODULES FILES
        "NvStrapsWinAPI.ixx"
        "NvStrapsDXGI.ixx"
        "WinApiError.ixx"
        "ConfigManagerError.ixx"
    )
else()
    # Linux: libpci-backed device-name lookup (non-module translation unit).
    target_sources(NvStrapsReBar PRIVATE "PciNames.cc")
endif()

target_compile_features(NvStrapsReBar PRIVATE c_std_17 cxx_std_23)
target_include_directories(NvStrapsReBar PRIVATE "${REBAR_DXE_DIRECTORY}/include" "${NvStrapsReBar_SOURCE_DIR}")

if(WIN32)
    target_link_libraries(NvStrapsReBar PRIVATE CxxModule::Std)
    target_link_libraries(NvStrapsReBar PRIVATE "DXGI" "SetupAPI" "CfgMgr32")

    if(MSVC)
        set_target_properties(NvStrapsReBar PROPERTIES LINK_FLAGS " /MANIFESTUAC:\"level='requireAdministrator' uiAccess='false'\" ")
    endif()
else()
    target_link_libraries(NvStrapsReBar PRIVATE PkgConfig::PCI)
endif()

# The libpci wrapper is plain C++ (classic headers), not a module consumer.
if(NOT WIN32)
    set_source_files_properties("PciNames.cc" PROPERTIES CXX_SCAN_FOR_MODULES OFF)
endif()

if(ENABLE_TESTING)
    enable_testing()
    add_subdirectory(test)
endif()
