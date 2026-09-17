"""应用配置"""
import os

# ====== 应用信息 ======
APP_NAME = "PDF2plus"  # 产品对外名称（标题栏 / 打包入口）
APP_BRAND_MARK = "PDF2+"  # 封面与字标用的展示名
APP_VERSION = "4.0.9"  # V4.0.9：文件操作与偏好拆成两行，特大字号不再叠「主题/历史」

APP_WIDTH = 1400  # 默认主窗宽度：给左侧偏好行与右侧英文长按钮留横向空间
APP_HEIGHT = 880  # 默认主窗高度：与加宽后的比例大致协调
# 制作人署名（不进入产品名）
APP_AUTHOR = "雪部湾扁橙"

# ====== 界面响应式缩放（相对设计稿） ======
UI_DESIGN_WIDTH = 1400  # 设计稿宽与默认打开宽度一致，首屏缩放约 1.0
UI_DESIGN_HEIGHT = 880  # 设计稿高与默认打开高度一致
UI_SCALE_MIN = 0.90
UI_SCALE_MAX = 1.35
UI_SCALE_EPSILON = 0.02  # 小于此变化不刷新，减轻拖拽闪烁
# 弹窗本地缩放：可比主窗口更高，方便最大化后字与控件变大
DIALOG_SCALE_MIN = 0.90
DIALOG_SCALE_MAX = 1.70
DIALOG_SCALE_EPSILON = 0.02
# 用户可选字号档位：窗口缩放 × 字号倍率 = 最终尺寸
UI_FONT_SIZE_DEFAULT = "default"
UI_FONT_SIZE_LARGE = "large"
UI_FONT_SIZE_XLARGE = "xlarge"
UI_FONT_SIZE_MULTIPLIERS = {
    UI_FONT_SIZE_DEFAULT: 1.00,  # 正文约 13px
    UI_FONT_SIZE_LARGE: 1.18,    # 正文约 15px
    UI_FONT_SIZE_XLARGE: 1.36,   # 正文约 18px
}
UI_FONT_SIZE_LABELS = {
    UI_FONT_SIZE_DEFAULT: "默认",
    UI_FONT_SIZE_LARGE: "大",
    UI_FONT_SIZE_XLARGE: "特大",
}
# 主窗口最小尺寸 ≈ 设计稿 × 下限，允许略缩小同时保持可读
UI_MIN_WIDTH = int(UI_DESIGN_WIDTH * UI_SCALE_MIN)
UI_MIN_HEIGHT = int(UI_DESIGN_HEIGHT * UI_SCALE_MIN)

# ====== 文件类型 ======
PDF_EXTENSION = ".pdf"
SUPPORTED_IMAGE_FORMATS = ["png", "jpg", "jpeg", "bmp", "tiff"]

# ====== DPI 设置 ======
DEFAULT_DPI = 300
HIGH_DPI = 600

# ====== 顺序文件 ======
ORDER_FILE_NAME = ".pdf_order.json"
