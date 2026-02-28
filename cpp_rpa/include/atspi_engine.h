
#ifndef WECHAT_RPA_ATSPI_ENGINE_H
#define WECHAT_RPA_ATSPI_ENGINE_H

// 条件编译ATSPI支持
#ifdef HAVE_ATSPI
#include <atspi/atspi.h>
#else
// 提供空定义以避免编译错误
typedef void* AtspiAccessible;
typedef struct {
    int x, y;
} AtspiPoint;
typedef struct {
    int x, y, width, height;
} AtspiRect;
typedef void* AtspiComponent;
#endif

#include <vector>
#include <string>
#include <map>
#include "common.h"

namespace wechat_rpa {

struct ATSPINodeInfo {
    int index = -1;
    int depth = 0;
    int parent_index = -1;
    int sibling_index = 0;
    std::string path;
    std::string parent_path;
    std::string name;
    std::string role;
    std::string text;
    std::string parent_role;
    Region region{0, 0, 0, 0};
    bool visible = false;
    bool showing = false;
    bool editable = false;
    bool focusable = false;
    bool sensitive = false;
};

struct ATSPIQuery {
    std::string role_equals;
    std::string role_contains;
    std::string name_contains;
    std::string text_contains;
    std::string parent_role_equals;
    std::string path_contains;
    int expected_depth = -1;
    int min_depth = -1;
    int max_depth = -1;
    bool require_visible = false;
    bool require_showing = false;
    bool require_editable = false;
    bool require_focusable = false;
    bool require_sensitive = false;
    bool require_non_empty_name = false;
    bool require_non_empty_text = false;
    bool require_non_zero_rect = false;
    double min_x_ratio = -1.0;
    double max_x_ratio = -1.0;
    double min_y_ratio = -1.0;
    double max_y_ratio = -1.0;
};

struct ATSPIAtomicContainer {
    std::string key;
    std::vector<ATSPINodeInfo> items;
};

/**
 * ATSPI引擎 - Linux辅助功能API
 * 用于直接访问UI控件树，不依赖图像识别
 */
class ATSPIEngine {
public:
    ATSPIEngine();
    ~ATSPIEngine();
    
    /**
     * 初始化ATSPI引擎
     * @return 是否初始化成功
     */
    bool initialize();
    
    /**
     * 获取微信应用
     * @return 应用指针
     */
    AtspiAccessible* get_wechat_application();
    
    /**
     * 获取所有控件
     * @param root 根节点
     * @return 控件列表
     */
    std::vector<AtspiAccessible*> get_all_controls(AtspiAccessible* root);
    
    /**
     * 按角色查找控件
     * @param root 根节点
     * @param role 角色名称
     * @return 控件列表
     */
    std::vector<AtspiAccessible*> find_controls_by_role(AtspiAccessible* root, const std::string& role);
    
    /**
     * 按名称查找控件
     * @param root 根节点
     * @param name 名称
     * @return 控件列表
     */
    std::vector<AtspiAccessible*> find_controls_by_name(AtspiAccessible* root, const std::string& name);
    
    /**
     * 点击控件
     * @param control 控件
     * @return 是否成功
     */
    bool click_control(AtspiAccessible* control);
    
    /**
     * 输入文本到控件
     * @param control 控件
     * @param text 文本
     * @return 是否成功
     */
    bool input_text(AtspiAccessible* control, const std::string& text);
    
    /**
     * 获取控件区域
     * @param control 控件
     * @return 区域信息
     */
    Region get_control_region(AtspiAccessible* control);
    
    /**
     * 获取控件文本
     * @param control 控件
     * @return 控件文本
     */
    std::string get_control_text(AtspiAccessible* control);

    /**
     * 获取控件名称
     * @param control 控件
     * @return 控件名称
     */
    std::string get_control_name(AtspiAccessible* control);

    /**
     * 获取控件角色名称
     * @param control 控件
     * @return 角色名称
     */
    std::string get_control_role(AtspiAccessible* control);
    
    /**
     * 检查ATSPI引擎是否可用
     * @return 是否可用
     */
    bool is_available() const;
    
    /**
     * 按角色查找所有控件
     * @param root 根节点
     * @param role 角色类型
     * @return 控件列表
     */
    std::vector<AtspiAccessible*> find_all_controls_by_role(AtspiAccessible* root, int role_type);
    
    /**
     * 获取控件边界
     * @param control 控件
     * @return 边界矩形
     */
    AtspiRect get_control_bounds(AtspiAccessible* control);

    /**
     * 统一AT-SPI树快照抓取接口
     * @param root 根节点
     * @param max_nodes 最大节点数
     * @param max_depth 最大深度（-1表示不限）
     * @param include_text 是否采集文本
     * @param deduplicate 是否按基础几何与语义去重
     * @return 树节点快照
     */
    std::vector<std::map<std::string, std::string>> capture_tree_snapshot(
        AtspiAccessible* root,
        int max_nodes = 800,
        int max_depth = -1,
        bool include_text = true,
        bool deduplicate = false
    );

    std::vector<ATSPINodeInfo> capture_tree_nodes(
        AtspiAccessible* root,
        int max_nodes = 1200,
        int max_depth = -1,
        bool include_text = true
    );

    std::vector<ATSPINodeInfo> query_nodes(
        AtspiAccessible* root,
        const ATSPIQuery& query,
        int max_nodes = 1200,
        int max_depth = -1
    );

    std::vector<ATSPIAtomicContainer> build_atomic_containers(
        AtspiAccessible* root,
        const ATSPIQuery& query,
        const std::string& group_by = "parent_path",
        int max_nodes = 1600,
        int max_depth = -1
    );

private:
    bool initialized_;
};

} // namespace wechat_rpa

#endif // WECHAT_RPA_ATSPI_ENGINE_H
