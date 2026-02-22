cmake_minimum_required(VERSION 3.12)
project(wechat_rpa)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 检查构建类型
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    message(STATUS "Debug build enabled")
    add_compile_definitions(DEBUG)
endif()

# 查找必要的包
find_package(OpenCV REQUIRED)
find_package(PkgConfig REQUIRED)

# 查找ATSPI库依赖
pkg_check_modules(ATSPI QUIET atspi-2)
# 在Manjaro/Arch中，atk-bridge是at-spi2-core的一部分
# 不需要单独的atk-bridge包

# 检查ATSPI是否可用
if(ATSPI_FOUND)
    add_definitions(-DHAVE_ATSPI)
    include_directories(${ATSPI_INCLUDE_DIRS})
    message(STATUS "ATSPI found, enabling ATSPI support")
    message(STATUS "ATSPI include dirs: ${ATSPI_INCLUDE_DIRS}")
else()
    message(STATUS "ATSPI not found, disabling ATSPI support")
endif()

if(NOT Tesseract_FOUND)
    message(STATUS "Tesseract not found via pkg-config, trying find_package...")
    find_package(Tesseract QUIET)
endif()

if(NOT Tesseract_FOUND)
    message(STATUS "Tesseract not found, trying to find manually...")
    # 手动查找Tesseract
    find_path(Tesseract_INCLUDE_DIR tesseract/baseapi.h
        PATHS /usr/include /usr/local/include
    )
    find_library(Tesseract_LIBRARY tesseract
        PATHS /usr/lib /usr/local/lib
    )
    if(Tesseract_INCLUDE_DIR AND Tesseract_LIBRARY)
        set(Tesseract_FOUND TRUE)
        set(Tesseract_INCLUDE_DIRS ${Tesseract_INCLUDE_DIR})
        set(Tesseract_LIBRARIES ${Tesseract_LIBRARY})
        message(STATUS "Found Tesseract manually: ${Tesseract_LIBRARY}")
    else()
        message(WARNING "Tesseract not found, OCR functionality will be disabled")
        set(Tesseract_FOUND FALSE)
    endif()
else()
    message(STATUS "Found Tesseract via pkg-config")
    message(STATUS "Tesseract include dirs: ${Tesseract_INCLUDE_DIRS}")
    message(STATUS "Tesseract libraries: ${Tesseract_LIBRARIES}")
endif()

# 尝试查找Leptonica
if(NOT Leptonica_FOUND)
    pkg_check_modules(Leptonica QUIET lept)
endif()

if(NOT Leptonica_FOUND)
    find_package(Leptonica QUIET)
endif()

if(NOT Leptonica_FOUND AND Tesseract_FOUND)
    message(STATUS "Leptonica not found, trying to find manually...")
    # 手动查找Leptonica
    find_path(Leptonica_INCLUDE_DIR leptonica/allheaders.h
        PATHS /usr/include /usr/local/include /usr/include/leptonica
    )
    find_library(Leptonica_LIBRARY 
        NAMES lept liblept
        PATHS /usr/lib /usr/local/lib
    )
    if(Leptonica_INCLUDE_DIR AND Leptonica_LIBRARY)
        set(Leptonica_FOUND TRUE)
        set(Leptonica_INCLUDE_DIRS ${Leptonica_INCLUDE_DIR})
        set(Leptonica_LIBRARIES ${Leptonica_LIBRARY})
        message(STATUS "Found Leptonica manually: ${Leptonica_LIBRARY}")
    else()
        message(WARNING "Leptonica not found, OCR functionality will be disabled")
        set(Leptonica_FOUND FALSE)
    endif()
else()
    message(STATUS "Found Leptonica via pkg-config or find_package")
    message(STATUS "Leptonica include dirs: ${Leptonica_INCLUDE_DIRS}")
    message(STATUS "Leptonica libraries: ${Leptonica_LIBRARIES}")
endif()

if(Tesseract_FOUND AND Leptonica_FOUND)
    add_definitions(-DENABLE_OCR)
    message(STATUS "OCR functionality enabled")
else()
    message(STATUS "OCR functionality disabled")
endif()

# 包含头文件目录
include_directories(include)

# 查找源文件
file(GLOB SOURCES 
    "src/*.cpp"
)

# 创建核心库
add_library(wechat_rpa_core STATIC ${SOURCES})
set_property(TARGET wechat_rpa_core PROPERTY POSITION_INDEPENDENT_CODE ON)

# 链接库
target_link_libraries(wechat_rpa_core
    ${OpenCV_LIBS}
    ${Tesseract_LIBRARIES}
    ${Leptonica_LIBRARIES}
)

# 如果ATSPI可用，链接ATSPI库
if(ATSPI_FOUND)
    target_link_libraries(wechat_rpa_core ${ATSPI_LIBRARIES})
endif()

# 查找pybind11
find_package(pybind11 REQUIRED)

# Python绑定
pybind11_add_module(wechat_rpa bindings/python_bindings.cpp)
target_link_libraries(wechat_rpa PRIVATE wechat_rpa_core)

# 安装配置
install(TARGETS wechat_rpa
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)

# 打印配置信息
message(STATUS "OpenCV version: ${OpenCV_VERSION}")
if(Tesseract_FOUND)
    message(STATUS "Tesseract version: ${Tesseract_VERSION}")
else()
    message(STATUS "Tesseract: Not found")
endif()
message(STATUS "pybind11 version: ${pybind11_VERSION}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "OCR functionality: ${Tesseract_FOUND}")

# 安装提示
if(NOT Tesseract_FOUND)
    message(WARNING "Tesseract not found, OCR functionality will be disabled")
endif()

if(NOT ATSPI_FOUND)
    message(WARNING "ATSPI not found, accessibility functionality will be limited")
endif()
