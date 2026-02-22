
#include "atspi_engine.h"
#include <iostream>
#include <algorithm>
#include <cctype>

#ifdef HAVE_ATSPI
#include <atspi/atspi-constants.h>
#endif

namespace wechat_rpa {

ATSPIEngine::ATSPIEngine() : initialized_(false) {
}

ATSPIEngine::~ATSPIEngine() {
    if (initialized_) {
        // 清理资源
    }
}

bool ATSPIEngine::initialize() {
#ifdef HAVE_ATSPI
    try {
        // 初始化ATSPI
        initialized_ = true;
        std::cout << "[DEBUG] ATSPI引擎初始化成功" << std::endl;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] ATSPI引擎初始化失败: " << e.what() << std::endl;
        return false;
    }
#else
    std::cout << "[INFO] ATSPI支持未编译，使用空实现" << std::endl;
    initialized_ = false;
    return false;
#endif
}

AtspiAccessible* ATSPIEngine::get_wechat_application() {
#ifdef HAVE_ATSPI
    if (!initialized_) {
        std::cerr << "[ERROR] ATSPI引擎未初始化" << std::endl;
        return nullptr;
    }
    
    GError *error = nullptr;
    
    // 获取桌面
    AtspiAccessible* desktop = atspi_get_desktop(0);
    if (!desktop) {
        std::cerr << "[ERROR] 无法获取桌面" << std::endl;
        return nullptr;
    }
    
    // 遍历应用
    gint child_count = atspi_accessible_get_child_count(desktop, &error);
    if (error) {
        g_error_free(error);
        error = nullptr;
        return nullptr;
    }
    
    AtspiAccessible* best_app = nullptr;
    gint best_child_count = -1;

    for (gint i = 0; i < child_count; i++) {
        AtspiAccessible* app = atspi_accessible_get_child_at_index(desktop, i, &error);
        if (error) {
            g_error_free(error);
            error = nullptr;
            continue;
        }
        
        if (app) {
            gchar* name = atspi_accessible_get_name(app, &error);
            if (error) {
                g_error_free(error);
                error = nullptr;
                g_object_unref(app);
                continue;
            }
            
            std::string app_name = name ? std::string(name) : "";
            std::string app_name_lower = app_name;
            std::transform(app_name_lower.begin(), app_name_lower.end(), app_name_lower.begin(),
                          [](unsigned char c) { return static_cast<char>(std::tolower(c)); });

            bool is_wechat = app_name_lower.find("wechat") != std::string::npos
                || app_name_lower.find("weixin") != std::string::npos
                || app_name.find("微信") != std::string::npos;

            if (name && is_wechat) {
                gint app_children = atspi_accessible_get_child_count(app, &error);
                if (error) {
                    g_error_free(error);
                    error = nullptr;
                    app_children = 0;
                }

                if (app_children > best_child_count) {
                    if (best_app) {
                        g_object_unref(best_app);
                    }
                    best_app = app;
                    best_child_count = app_children;
                    std::cout << "[DEBUG] 候选微信应用: " << app_name
                              << ", child_count=" << app_children << std::endl;
                } else {
                    g_object_unref(app);
                }
                g_free(name);
                continue;
            }
            g_free(name);
            g_object_unref(app);
        }
    }
    
    g_object_unref(desktop);
    if (best_app) {
        std::cout << "[DEBUG] 选择微信应用节点, child_count=" << best_child_count << std::endl;
    }
    return best_app;
#else
    std::cerr << "[ERROR] ATSPI支持未编译" << std::endl;
    return nullptr;
#endif
}

std::vector<AtspiAccessible*> ATSPIEngine::get_all_controls(AtspiAccessible* root) {
    std::vector<AtspiAccessible*> controls;
    
    if (!root) {
        return controls;
    }
    
#ifdef HAVE_ATSPI
    GError *error = nullptr;
    
    // 递归获取所有控件
    gint child_count = atspi_accessible_get_child_count(root, &error);
    if (error) {
        g_error_free(error);
        return controls;
    }
    
    for (gint i = 0; i < child_count; i++) {
        AtspiAccessible* child = atspi_accessible_get_child_at_index(root, i, &error);
        if (error) {
            g_error_free(error);
            error = nullptr;
            continue;
        }
        
        if (child) {
            controls.push_back(child);
            // 递归处理子控件
            std::vector<AtspiAccessible*> child_controls = get_all_controls(child);
            controls.insert(controls.end(), child_controls.begin(), child_controls.end());
        }
    }
#endif
    
    return controls;
}

std::vector<AtspiAccessible*> ATSPIEngine::find_controls_by_role(AtspiAccessible* root, const std::string& role) {
    std::vector<AtspiAccessible*> controls;
    
    if (!root) {
        return controls;
    }
    
#ifdef HAVE_ATSPI
    // 获取所有控件
    std::vector<AtspiAccessible*> all_controls = get_all_controls(root);
    
    GError *error = nullptr;
    
    // 按角色过滤
    for (auto* control : all_controls) {
        if (control) {
            gchar* control_role = atspi_accessible_get_role_name(control, &error);
            if (error) {
                g_error_free(error);
                error = nullptr;
                continue;
            }
            
            if (control_role && std::string(control_role) == role) {
                controls.push_back(control);
            }
            g_free(control_role);
        }
    }
#endif
    
    return controls;
}

std::vector<AtspiAccessible*> ATSPIEngine::find_controls_by_name(AtspiAccessible* root, const std::string& name) {
    std::vector<AtspiAccessible*> controls;
    
    if (!root) {
        return controls;
    }
    
#ifdef HAVE_ATSPI
    // 获取所有控件
    std::vector<AtspiAccessible*> all_controls = get_all_controls(root);
    
    GError *error = nullptr;
    
    // 按名称过滤
    for (auto* control : all_controls) {
        if (control) {
            gchar* control_name = atspi_accessible_get_name(control, &error);
            if (error) {
                g_error_free(error);
                error = nullptr;
                continue;
            }
            
            if (control_name && std::string(control_name).find(name) != std::string::npos) {
                controls.push_back(control);
            }
            g_free(control_name);
        }
    }
#endif
    
    return controls;
}

bool ATSPIEngine::click_control(AtspiAccessible* control) {
    if (!control || !initialized_) {
        return false;
    }
    
#ifdef HAVE_ATSPI
    try {
        GError *error = nullptr;
        
        // 获取组件接口
        AtspiComponent *comp = atspi_accessible_get_component_iface(control);
        if (comp) {
            // 获取组件边界
            AtspiRect *rect = atspi_component_get_extents(comp, ATSPI_COORD_TYPE_SCREEN, &error);
            if (error) {
                g_error_free(error);
                error = nullptr;
                g_object_unref(comp);
                return false;
            }
            
            // 尝试使用事件系统进行点击
            gboolean result = atspi_component_grab_focus(comp, &error);
            
            // 释放rect内存
            if (rect) {
                g_free(rect);
            }
            
            g_object_unref(comp);
            
            if (result) {
                std::cout << "[DEBUG] 控件焦点获取成功" << std::endl;
                return true;
            } else {
                std::cerr << "[ERROR] 控件焦点获取失败" << std::endl;
                return false;
            }
        } else {
            std::cerr << "[ERROR] 控件接口不可用" << std::endl;
            return false;
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] 控件点击异常: " << e.what() << std::endl;
        return false;
    }
#else
    return false;
#endif
}

bool ATSPIEngine::input_text(AtspiAccessible* control, const std::string& text) {
    if (!control || !initialized_) {
        return false;
    }
    
#ifdef HAVE_ATSPI
    try {
        GError *error = nullptr;
        
        // 检查控件是否支持文本接口
        AtspiEditableText *edit_text = atspi_accessible_get_editable_text_iface(control);
        if (edit_text) {
            // 设置文本内容
            gboolean clear_result = atspi_editable_text_set_text_contents(edit_text, text.c_str(), &error);
            
            g_object_unref(edit_text);
            
            if (clear_result) {
                std::cout << "[DEBUG] 文本输入成功: " << text << std::endl;
                return true;
            } else {
                std::cerr << "[ERROR] 文本输入失败" << std::endl;
                return false;
            }
        } else {
            // 如果不支持编辑文本接口，尝试值接口
            AtspiValue *value_iface = atspi_accessible_get_value_iface(control);
            if (value_iface) {
                gdouble dval = atof(text.c_str());
                gboolean set_result = atspi_value_set_current_value(value_iface, dval, &error);
                
                g_object_unref(value_iface);
                
                if (set_result) {
                    std::cout << "[DEBUG] 数值输入成功: " << text << std::endl;
                    return true;
                } else {
                    std::cerr << "[ERROR] 数值输入失败" << std::endl;
                    return false;
                }
            } else {
                std::cerr << "[ERROR] 控件不支持文本或值接口" << std::endl;
                return false;
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] 文本输入异常: " << e.what() << std::endl;
        return false;
    }
#else
    return false;
#endif
}

Region ATSPIEngine::get_control_region(AtspiAccessible* control) {
    Region region = {0, 0, 0, 0};
    
    if (!control || !initialized_) {
        return region;
    }
    
#ifdef HAVE_ATSPI
    try {
        GError *error = nullptr;
        
        // 获取控件位置和大小
        AtspiComponent* component = atspi_accessible_get_component_iface(control);
        if (component) {
            AtspiRect *rect = atspi_component_get_extents(component, ATSPI_COORD_TYPE_SCREEN, &error);
            if (error) {
                g_error_free(error);
                error = nullptr;
            } else if (rect) {
                region.x = rect->x;
                region.y = rect->y;
                region.width = rect->width;
                region.height = rect->height;
                
                g_free(rect);
            }
            
            g_object_unref(component);
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] 获取控件区域异常: " << e.what() << std::endl;
    }
#endif
    
    return region;
}

std::string ATSPIEngine::get_control_text(AtspiAccessible* control) {
    if (!control || !initialized_) {
        return "";
    }
    
#ifdef HAVE_ATSPI
    try {
        GError *error = nullptr;
        
        // 获取控件文本
        AtspiText *text_iface = atspi_accessible_get_text_iface(control);
        if (text_iface) {
            gint start_offset = 0;
            gint end_offset = atspi_text_get_character_count(text_iface, &error);
            if (error) {
                g_error_free(error);
                error = nullptr;
                end_offset = 0;
            }
            
            gchar* text_content = atspi_text_get_text(text_iface, start_offset, end_offset, &error);
            
            std::string result = text_content ? text_content : "";
            
            if (text_content) {
                g_free(text_content);
            }
            
            g_object_unref(text_iface);
            
            return result;
        } else {
            // 作为备选方案，尝试获取控件名称
            gchar* name = atspi_accessible_get_name(control, &error);
            if (error) {
                g_error_free(error);
                name = nullptr;
            }
            
            std::string result = name ? name : "";
            
            if (name) {
                g_free(name);
            }
            
            return result;
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] 获取控件文本异常: " << e.what() << std::endl;
        return "";
    }
#else
    return "";
#endif
}

std::string ATSPIEngine::get_control_name(AtspiAccessible* control) {
    if (!control || !initialized_) {
        return "";
    }

#ifdef HAVE_ATSPI
    try {
        GError *error = nullptr;
        gchar* control_name = atspi_accessible_get_name(control, &error);
        if (error) {
            g_error_free(error);
            return "";
        }

        std::string name = control_name ? std::string(control_name) : "";
        if (control_name) {
            g_free(control_name);
        }
        return name;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] 获取控件名称异常: " << e.what() << std::endl;
        return "";
    }
#else
    return "";
#endif
}

std::string ATSPIEngine::get_control_role(AtspiAccessible* control) {
    if (!control || !initialized_) {
        return "";
    }

#ifdef HAVE_ATSPI
    try {
        GError *error = nullptr;
        gchar* role_name = atspi_accessible_get_role_name(control, &error);
        if (error) {
            g_error_free(error);
            return "";
        }

        std::string role = role_name ? std::string(role_name) : "";
        if (role_name) {
            g_free(role_name);
        }
        return role;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] 获取控件角色异常: " << e.what() << std::endl;
        return "";
    }
#else
    return "";
#endif
}


bool ATSPIEngine::is_available() const {
    return initialized_;
}

std::vector<AtspiAccessible*> ATSPIEngine::find_all_controls_by_role(AtspiAccessible* root, int role_type) {
    std::vector<AtspiAccessible*> controls;
    
    if (!root) return controls;
    
    // 递归查找指定角色类型的控件
    int child_count = atspi_accessible_get_child_count(root, nullptr);
    for (int i = 0; i < child_count; ++i) {
        AtspiAccessible* child = atspi_accessible_get_child_at_index(root, i, nullptr);
        if (!child) continue;
        
        AtspiRole child_role = atspi_accessible_get_role(child, nullptr);
        if (child_role == role_type) {
            controls.push_back(child);
        }
        
        // 递归查找子节点
        auto sub_controls = find_all_controls_by_role(child, role_type);
        controls.insert(controls.end(), sub_controls.begin(), sub_controls.end());
        
        // 不立即释放child，让调用方负责清理
    }
    
    return controls;
}

AtspiRect ATSPIEngine::get_control_bounds(AtspiAccessible* control) {
    AtspiRect rect = {0, 0, 0, 0};
    
    if (!control) return rect;
    
#ifdef HAVE_ATSPI
    GError *error = nullptr;
    AtspiComponent* comp = atspi_accessible_get_component_iface(control);
    if (comp) {
        AtspiRect* rect_ptr = atspi_component_get_extents(comp, ATSPI_COORD_TYPE_SCREEN, &error);
        if (rect_ptr && !error) {
            rect.x = rect_ptr->x;
            rect.y = rect_ptr->y;
            rect.width = rect_ptr->width;
            rect.height = rect_ptr->height;
            
            // 释放rect指针
            g_free(rect_ptr);
        }
        
        g_object_unref(comp);
        
        if (error) {
            g_error_free(error);
        }
    }
#endif
    
    return rect;
}

} // namespace wechat_rpa