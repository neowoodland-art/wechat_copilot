
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "wechat_manager.h"
#include "image_processor.h"
#include "ocr_engine.h"
#include "humanization_engine.h"
#include "atspi_engine.h"
#include "window_manager.h"

namespace py = pybind11;

// 将cv::Mat转换为numpy数组的辅助函数
py::array_t<uint8_t> mat_to_numpy(const cv::Mat &mat) {
    if (mat.empty()) {
        return py::array_t<uint8_t>();
    }
    
    std::vector<size_t> shape = {static_cast<size_t>(mat.rows), static_cast<size_t>(mat.cols)};
    if (mat.channels() > 1) {
        shape.push_back(static_cast<size_t>(mat.channels()));
    }
    
    auto capsule = py::capsule(mat.data, [](void *v) {
        // Don't delete mat.data since it's owned by cv::Mat
    });
    
    return py::array_t<uint8_t>(
        shape,
        {sizeof(uint8_t) * mat.step[0], sizeof(uint8_t) * mat.step[1], sizeof(uint8_t) * mat.elemSize()},
        mat.data,
        capsule
    );
}

PYBIND11_MODULE(wechat_rpa, m) {
    m.doc() = "WeChat RPA Python binding";

    // 绑定Region结构
    py::class_<wechat_rpa::Region>(m, "Region")
        .def(py::init<>())
        .def_readwrite("x", &wechat_rpa::Region::x)
        .def_readwrite("y", &wechat_rpa::Region::y)
        .def_readwrite("width", &wechat_rpa::Region::width)
        .def_readwrite("height", &wechat_rpa::Region::height);

    // 绑定WindowInfo结构
    py::class_<wechat_rpa::WindowInfo>(m, "WindowInfo")
        .def(py::init<>())
        .def_readwrite("id", &wechat_rpa::WindowInfo::id)
        .def_readwrite("title", &wechat_rpa::WindowInfo::title)
        .def_readwrite("x", &wechat_rpa::WindowInfo::x)
        .def_readwrite("y", &wechat_rpa::WindowInfo::y)
        .def_readwrite("width", &wechat_rpa::WindowInfo::width)
        .def_readwrite("height", &wechat_rpa::WindowInfo::height)
        .def_readwrite("is_active", &wechat_rpa::WindowInfo::is_active);

    // 绑定Message结构
    py::class_<wechat_rpa::Message>(m, "Message")
        .def(py::init<>())
        .def_readwrite("id", &wechat_rpa::Message::id)
        .def_readwrite("sender", &wechat_rpa::Message::sender)
        .def_readwrite("content", &wechat_rpa::Message::content)
        .def_readwrite("confidence", &wechat_rpa::Message::confidence);

    // 绑定Contact结构
    py::class_<wechat_rpa::Contact>(m, "Contact")
        .def(py::init<>())
        .def_readwrite("id", &wechat_rpa::Contact::id)
        .def_readwrite("name", &wechat_rpa::Contact::name)
        .def_readwrite("wechat_id", &wechat_rpa::Contact::wechat_id)
        .def_readwrite("avatar", &wechat_rpa::Contact::avatar);

    // 绑定WeChatManager类
    py::class_<wechat_rpa::WeChatManager>(m, "WeChatManager")
        .def(py::init<>())
        .def("initialize", &wechat_rpa::WeChatManager::initialize)
        .def("activate_wechat", &wechat_rpa::WeChatManager::activate_wechat)
        .def("get_wechat_window", &wechat_rpa::WeChatManager::get_wechat_window)
        .def("is_wechat_active", &wechat_rpa::WeChatManager::is_wechat_active)
        .def("get_latest_messages", &wechat_rpa::WeChatManager::get_latest_messages)
        .def("send_message", &wechat_rpa::WeChatManager::send_message)
        .def("search_contact", &wechat_rpa::WeChatManager::search_contact)
        .def("get_contacts", &wechat_rpa::WeChatManager::get_contacts)
        .def("capture_message_area", [](wechat_rpa::WeChatManager &self) {
            return mat_to_numpy(self.capture_message_area());
        })
        .def("capture_full_window", [](wechat_rpa::WeChatManager &self) {
            return mat_to_numpy(self.capture_full_window());
        })
        .def("find_ui_elements", &wechat_rpa::WeChatManager::find_ui_elements)
        .def("get_element_region", &wechat_rpa::WeChatManager::get_element_region)
        .def("capture_base_interface", [](wechat_rpa::WeChatManager &self) {
            return mat_to_numpy(self.capture_base_interface());
        })
        .def("click_control_by_atspi", &wechat_rpa::WeChatManager::click_control_by_atspi)
        .def("input_text_by_atspi", &wechat_rpa::WeChatManager::input_text_by_atspi)
        .def("get_control_text_by_atspi", &wechat_rpa::WeChatManager::get_control_text_by_atspi)
        .def("get_atspi_control_snapshot", &wechat_rpa::WeChatManager::get_atspi_control_snapshot)
        .def("get_atspi_tree_snapshot", &wechat_rpa::WeChatManager::get_atspi_tree_snapshot)
        .def("humanized_click", &wechat_rpa::WeChatManager::humanized_click)
        .def("humanized_input", &wechat_rpa::WeChatManager::humanized_input)
        .def("ensure_wechat_available", &wechat_rpa::WeChatManager::ensure_wechat_available)
        .def("is_initialized", &wechat_rpa::WeChatManager::is_initialized)
        .def("analyze_ui_elements", &wechat_rpa::WeChatManager::analyze_ui_elements, py::call_guard<py::gil_scoped_release>())
        .def("find_all_buttons", &wechat_rpa::WeChatManager::find_all_buttons, py::call_guard<py::gil_scoped_release>())
        .def("capture_specific_element", &wechat_rpa::WeChatManager::capture_specific_element, py::call_guard<py::gil_scoped_release>())
        .def("capture_and_save_message_area", &wechat_rpa::WeChatManager::capture_and_save_message_area, py::call_guard<py::gil_scoped_release>())
        .def("capture_and_annotate_elements", [](wechat_rpa::WeChatManager &self, const std::vector<std::string>& element_names) {
            return mat_to_numpy(self.capture_and_annotate_elements(element_names));
        }, py::call_guard<py::gil_scoped_release>())
        .def("capture_and_annotate_all_elements", [](wechat_rpa::WeChatManager &self) {
            return mat_to_numpy(self.capture_and_annotate_all_elements());
        }, py::call_guard<py::gil_scoped_release>());

    // 绑定ImageProcessor类
    py::class_<wechat_rpa::ImageProcessor>(m, "ImageProcessor")
        .def(py::init<>());

    // 绑定OCRAEngine类（处理重载方法）
    py::class_<wechat_rpa::OCRAEngine>(m, "OCRAEngine")
        .def(py::init<>())
        .def("initialize", &wechat_rpa::OCRAEngine::initialize)
        .def("recognize_text", &wechat_rpa::OCRAEngine::recognize_text)
        .def("recognize_region_with_region", static_cast<std::vector<wechat_rpa::TextResult> (wechat_rpa::OCRAEngine::*)(const cv::Mat&, const wechat_rpa::Region&)>(&wechat_rpa::OCRAEngine::recognize_region))
        .def("recognize_region_with_coords", static_cast<std::vector<wechat_rpa::TextResult> (wechat_rpa::OCRAEngine::*)(const cv::Mat&, int, int, int, int)>(&wechat_rpa::OCRAEngine::recognize_region));

    // 绑定HumanizationEngine类
    py::class_<wechat_rpa::HumanizationEngine>(m, "HumanizationEngine")
        .def(py::init<>())
        .def("initialize", &wechat_rpa::HumanizationEngine::initialize)
        .def("get_random_delay", &wechat_rpa::HumanizationEngine::get_random_delay)
        .def("get_random_offset", &wechat_rpa::HumanizationEngine::get_random_offset)
        .def("simulate_typing", &wechat_rpa::HumanizationEngine::simulate_typing)
        .def("simulate_mouse_movement", &wechat_rpa::HumanizationEngine::simulate_mouse_movement)
        .def("should_execute_behavior", &wechat_rpa::HumanizationEngine::should_execute_behavior);

    // 绑定ATSPIEngine类
    py::class_<wechat_rpa::ATSPIEngine>(m, "ATSPIEngine")
        .def(py::init<>())
        .def("initialize", &wechat_rpa::ATSPIEngine::initialize)
        .def("get_wechat_application", &wechat_rpa::ATSPIEngine::get_wechat_application)
        .def("get_all_controls", &wechat_rpa::ATSPIEngine::get_all_controls)
        .def("find_controls_by_role", &wechat_rpa::ATSPIEngine::find_controls_by_role)
        .def("find_controls_by_name", &wechat_rpa::ATSPIEngine::find_controls_by_name)
        .def("click_control", &wechat_rpa::ATSPIEngine::click_control)
        .def("input_text", &wechat_rpa::ATSPIEngine::input_text)
        .def("get_control_region", &wechat_rpa::ATSPIEngine::get_control_region)
        .def("get_control_text", &wechat_rpa::ATSPIEngine::get_control_text)
        .def("get_control_name", &wechat_rpa::ATSPIEngine::get_control_name)
        .def("get_control_role", &wechat_rpa::ATSPIEngine::get_control_role);

    // 绑定WindowManager类
    py::class_<wechat_rpa::WindowManager>(m, "WindowManager")
        .def(py::init<>())
        .def("find_wechat_window", &wechat_rpa::WindowManager::find_wechat_window)
        .def("activate_window", &wechat_rpa::WindowManager::activate_window)
        .def("is_window_active", &wechat_rpa::WindowManager::is_window_active)
        .def("get_window_info", &wechat_rpa::WindowManager::get_window_info)
        .def("search_windows", &wechat_rpa::WindowManager::search_windows)
        .def("get_active_window", &wechat_rpa::WindowManager::get_active_window);
}