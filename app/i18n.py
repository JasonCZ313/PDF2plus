# -*- coding: utf-8 -*-
"""
界面中英文切换。

用法：
  set_language("zh" | "en")
  t("key") / t("key", name=...)
默认中文；语言偏好由 preferences 持久化。
"""
from __future__ import annotations

from typing import Any, Dict

# 当前界面语言：zh=中文，en=英文
_current_language = "zh"

# ---------------------------------------------------------------------------
# 中文文案（默认）
# ---------------------------------------------------------------------------
_ZH: Dict[str, str] = {
    # 通用
    "dialog.ok": "确定",
    "dialog.cancel": "取消",
    "dialog.close": "关闭",
    "dialog.tip": "提示",
    "dialog.error": "错误",
    "dialog.done": "完成",
    "dialog.confirm": "确认",
    "dialog.failed": "失败",
    "dialog.browse": "浏览...",
    "common.all_files": "所有文件 (*.*)",

    # 主窗壳
    "main.ready": "就绪 — 导入 PDF 后即可开始操作",
    "main.credit": "本程序由 <b style='color:{color};'>{author}</b> 编程制作，感谢您的使用！",
    "main.version_tip": "{app} 当前版本 V{version}",
    "main.cancel": "取消",
    "main.task_cancelled_status": "任务已取消",
    "startup.recover_title": "恢复提示",
    "startup.recover_body": (
        "检测到上次程序异常退出。\n\n"
        "是否保留上次上传的 PDF 文件？\n"
        "（选「否」将清空工作空间，选「是」保留文件）"
    ),

    # 路径栏
    "path.label": "默认保存路径：",
    "path.placeholder": "未设置则默认保存到桌面",
    "path.remember": "记住此路径（下次打开时自动恢复）",
    "path.unset": "未设置（将默认保存到桌面）",
    "path.valid": "✓ 路径有效",
    "path.invalid": "⚠ 路径不存在，请重新设置",
    "path.invalid_warn_title": "路径无效",
    "path.invalid_warn_body": "当前默认保存路径无效或不存在。\n请先设置一个有效的保存路径再试。",

    # 列表区
    "list.select_all": "全选 / 取消全选",
    "list.checked": "已勾选: {count}",
    "list.pages_suffix": "  ({pages} 页)",
    "list.drop_here": "📥 将插入此处",

    # 导入行
    "btn.import": "导入 PDF",
    "btn.remove": "移除选中",
    "btn.preview": "预览",
    "label.font": "字体：",
    "label.theme": "主题：",
    "label.language": "语言：",
    "theme.light": "浅色模式",
    "theme.dark": "深色模式",
    "lang.zh": "中文",
    "lang.en": "English",
    "font.default": "默认",
    "font.large": "大",
    "font.xlarge": "特大",
    "btn.history": "历史",
    "btn.history.tip": "查看历史记录：可下载以往的输出文件、打开源文件/输出文件所在文件夹",

    # 右侧分组与按钮
    "group.merge": "合并",
    "group.convert": "转换",
    "group.organize": "整理",
    "group.security": "安全",
    "group.create": "新建",
    "btn.merge": "合并勾选的 PDF",
    "btn.copy_original": "转换时保留原始PDF",
    "btn.split": "拆分 PDF",
    "btn.to_images": "PDF 转图片",
    "btn.to_word": "PDF 转 Word",
    "btn.compress": "PDF 压缩",
    "btn.pages": "页面管理",
    "btn.stamp": "水印与页码",
    "btn.encrypt": "加密 PDF",
    "btn.decrypt": "解除密码",
    "btn.images_to_pdf": "图片转 PDF",

    # 底部说明面板
    "desc.placeholder": "鼠标悬停功能按钮查看功能说明",
    "desc.idle": "&#128218; 鼠标悬停功能按钮可查看功能说明",
    "desc.offline": "完全离线，无需联网",
    "desc.online": "需要联网使用",
    "steps.placeholder": "鼠标悬停功能按钮查看使用方法",
    "steps.idle": "&#128196; 鼠标悬停功能按钮可查看使用方法",
    "steps.title": "{title} — 使用方法",

    # 拆分对话框
    "split.title": "PDF 拆分设置",
    "split.working_on": "📄 正在拆分：{name}",
    "split.info": "该 PDF 共 {pages} 页，请选择拆分方式：",
    "split.mode": "拆分方式",
    "split.by_pages": "按页数拆分：每",
    "split.pages_unit": "页为一个文件",
    "split.by_copies": "按份数拆分：拆成",
    "split.copies_unit": "份",
    "split.by_ranges": "自定义页范围",
    "split.ranges_group": "自定义页范围",
    "split.col_start": "起始页",
    "split.col_end": "结束页",
    "split.add_range": "+ 添加一份",
    "split.del_range": "- 删除选中行",
    "split.ranges_tip": (
        "每一行拆成一个文件。页码从 1 到总页数；"
        "点「添加一份」可拆多段，行多时可上下滚动查看。"
    ),

    # 图片导出
    "export.title": "图片导出设置",
    "export.params": "导出参数",
    "export.format": "输出格式",
    "export.dpi": "清晰度 (DPI)",
    "export.dpi_300": "300 (高清)",
    "export.dpi_600": "600 (超高精)",
    "export.dpi_custom": "自定义",
    "export.dpi_hint": (
        "范围 72～1200。日常打印建议 300，精细扫描可用 600；"
        "数字越大越清晰、文件也越大。"
        "超高 DPI 会按页面尺寸自动限制，避免导出全白图。"
    ),
    "export.dpi_spin_tip": "自定义清晰度，范围 72～1200 DPI；过大时将按页自动下调",

    # 历史
    "history.title": "历史记录（最多10条）",
    "history.col_time": "时间",
    "history.col_type": "类型",
    "history.col_sources": "源文件数",
    "history.col_output": "输出文件",
    "history.col_actions": "操作",
    "history.col_delete": "删除",
    "history.legend": (
        "按钮说明：<span style='color:{c1};'>●</span> 下载输出文件 ｜ "
        "<span style='color:{c2};'>●</span> 打开源文件夹 ｜ "
        "<span style='color:{c3};'>●</span> 打开输出文件夹 ｜ "
        "<span style='color:{c4};'>●</span> 删除此记录"
    ),
    "history.hover_hint": "鼠标悬停按钮查看功能说明",
    "history.dl_desc": "下载：将输出文件保存到指定位置",
    "history.dl_tip": "下载输出文件",
    "history.src_desc": "打开源文件夹：打开源文件所在的文件夹",
    "history.src_tip": "打开源文件夹",
    "history.out_desc": "打开输出文件夹：打开输出文件所在的文件夹",
    "history.out_tip": "打开输出文件夹",
    "history.del_desc": "删除：删除此条历史记录",
    "history.del_tip": "删除此记录",
    "history.save_as": "保存到",
    "history.dl_ok": "文件已下载到指定位置",
    "history.dl_fail": "下载失败，输出文件可能已被删除",
    "history.del_confirm": "确定删除这条历史记录？",
    "history.restore_name": "恢复_{id}{ext}",

    # 密码 / 加密 / 压缩
    "pwd.title": "输入 PDF 密码",
    "pwd.prompt": "该 PDF 已加密，请输入密码：",
    "encrypt.title": "加密 PDF",
    "encrypt.pwd_group": "打开密码",
    "encrypt.user_pwd": "用户密码",
    "encrypt.confirm_pwd": "确认密码",
    "encrypt.perm_group": "权限",
    "encrypt.allow_print": "允许打印",
    "encrypt.allow_copy": "允许复制文本",
    "encrypt.empty_pwd": "密码不能为空",
    "encrypt.pwd_mismatch": "两次输入的密码不一致",
    "compress.title": "PDF 压缩",
    "compress.level": "压缩方式",
    "compress.choose": "请选择压缩方式（全程离线）：",
    "compress.original": "原 PDF 体积：{size}（{bytes} 字节）",
    "compress.light": "轻度（尽量无损，体积下降有限）",
    "compress.standard": "标准（推荐，接近 PDF24 日常效果）",
    "compress.strong": "强力（体积更小，图片可能变糊）",
    "compress.target_mode": "按目标体积（填写后尽量接近，不能保证精确到字节）",
    "compress.target_label": "目标体积：",
    "compress.target_unit": "MB",
    "compress.target_hint": "必须小于原体积。扫描件较容易压到目标；纯文字/矢量 PDF 会有下限。",
    "compress.target_invalid_dialog": "目标体积必须大于 0 且小于原 PDF 体积。",
    "compress.target_disabled_tip": "无法读取原文件体积，不能使用「按目标体积」。请确认已选中有效 PDF。",
    "compress.rasterize": "仍超目标时，允许整页栅格化（文字将不可选，默认关闭）",
    "compress.rasterize_tip": "仅作为最后手段：把每一页打成图片再合成 PDF，体积可能再降，但文字不能复制。",
    "compress.msg.missing": "源文件不存在",
    "compress.msg.cancelled": "已取消",
    "compress.msg.failed": "压缩失败：{error}",
    "compress.msg.target_invalid": "目标体积必须大于 0 且小于原 PDF 体积",
    "compress.msg.ok": "原体积 {original} → {output}，约节省 {percent}%",
    "compress.msg.ok_target": "原体积 {original} → {output}（目标 {target}），约节省 {percent}%",
    "compress.msg.ok_target_floor": "原体积 {original} → {output}（目标 {target}）。已到画质下限，无法继续缩小。",
    "compress.msg.cannot_shrink": "原体积 {original}。当前文件已无法再缩小，已按原体积保存。",

    # 水印
    "stamp.title": "水印与页码",
    "stamp.text_group": "文字水印",
    "stamp.add_text": "添加文字水印",
    "stamp.default_text": "内部资料",
    "stamp.font_size": "字号",
    "stamp.rotate": "旋转°",
    "stamp.opacity": "透明度",
    "stamp.color": "颜色",
    "stamp.color_red": "红",
    "stamp.color_blue": "蓝",
    "stamp.color_black": "黑",
    "stamp.color_gray": "深灰",
    "stamp.color_orange": "橙",
    "stamp.custom_color": "自定义…",
    "stamp.custom_color_tip": "打开取色器，任选水印颜色",
    "stamp.swatch_tip": "当前水印颜色（点击可自定义）",
    "stamp.tile_text": "平铺文字水印（斜向铺满，合同/标书常用）",
    "stamp.image_group": "图片水印",
    "stamp.add_image": "添加图片水印",
    "stamp.image_placeholder": "选择 PNG/JPG 图片…",
    "stamp.browse": "浏览…",
    "stamp.image_scale": "图片缩放",
    "stamp.image_scale_tip": "相对页宽的比例，过大会挡住正文",
    "stamp.image_opacity": "图片透明度",
    "stamp.image_opacity_tip": "1 为不透明；建议 0.25～0.45",
    "stamp.tile_image": "平铺图片水印",
    "stamp.underlay": "衬于内容之下（扫描件或白底页面上可能看不见）",
    "stamp.page_group": "页码",
    "stamp.add_page_no": "添加页码",
    "stamp.page_template": "第 {page} / {total} 页",
    "stamp.page_format": "格式预设",
    "stamp.page_custom": "自定义模板",
    "stamp.page_custom_tip": "可改文字；页码用 {page}，总页数用 {total}",
    "stamp.tpl_full": "第 {page} / {total} 页",
    "stamp.tpl_compact_cn": "第{page}/{total}页",
    "stamp.tpl_slash_page": "{page}/{total} 页",
    "stamp.tpl_slash": "{page}/{total}",
    "stamp.tpl_spaced": "{page} / {total}",
    "stamp.tpl_page_only": "第 {page} 页",
    "stamp.tpln_full": "第 X / X 页",
    "stamp.tpln_compact_cn": "第X/X页",
    "stamp.tpln_slash_page": "X/X 页",
    "stamp.tpln_slash": "X/X",
    "stamp.tpln_spaced": "X / X",
    "stamp.tpln_page_only": "第 X 页",
    "stamp.tpl_custom": "自定义（用下面输入框）",
    "stamp.position": "快捷位置",
    "stamp.pos_bc": "下中",
    "stamp.pos_bl": "下左",
    "stamp.pos_br": "下右",
    "stamp.pos_tc": "上中",
    "stamp.pos_tl": "上左",
    "stamp.pos_tr": "上右",
    "stamp.unit": "单位",
    "stamp.unit_mm": "毫米",
    "stamp.unit_px": "像素",
    "stamp.offset_left": "距左边",
    "stamp.offset_bottom": "距下边",
    "stamp.offset_top": "距顶边",
    "stamp.box_width": "页码框宽",
    "stamp.box_height": "页码框高",
    "stamp.page_font": "字号",
    "stamp.page_font_effective": "实际绘制 {actual}（框过窄，设定 {requested} 装不下；可加宽页码框）",
    "stamp.preview": "预览",
    "stamp.preview_page": "预览页",
    "stamp.preview_empty": "无法预览（文件打不开或需要密码）",
    "stamp.preview_hint": "点击缩略图可放大查看页码位置",
    "stamp.preview_enlarge": "放大预览",
    "stamp.preview_large_title": "页码预览（可放大缩小）",
    "stamp.preview_full_title": "水印与页码预览（可放大缩小）",
    "stamp.preview_click_tip": "点击图片放大",
    "stamp.preview_watermark": "预览水印效果",
    "stamp.preview_watermark_tip": "按当前文字/图片水印与页码设置，打开可缩放预览",
    "stamp.preview_zoom": "缩放",
    "stamp.preview_zoom_reset": "100%",
    "stamp.preview_zoom_tip": "可用＋/－或 Ctrl+滚轮缩放；滚动条可拖动画看页角页码",
    "stamp.margin": "距页边",
    "stamp.margin_suffix": " 毫米",
    "stamp.margin_tip": "距页面左边与底边（或顶边）的距离，可与单位一起切换",
    "stamp.pick_color": "选择水印颜色",
    "stamp.pick_image": "选择水印图片",
    "stamp.image_filter": "图片 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;所有文件 (*.*)",
    "stamp.need_one": "请至少启用一种：文字水印 / 图片水印 / 页码",
    "stamp.need_image": "请选择有效的水印图片",
    "stamp.mm_sample": "40.0 毫米",

    # 图片转 PDF
    "img2pdf.title": "图片转 PDF",
    "img2pdf.order": "图片顺序",
    "img2pdf.order_tip": "可上移/下移调整页序：",
    "img2pdf.up": "上移",
    "img2pdf.down": "下移",
    "img2pdf.mode": "页面模式",
    "img2pdf.a4": "适应 A4（推荐）",
    "img2pdf.orig": "按原图像素尺寸",
    "img2pdf.insert_here": "将插入此处",

    # 页面预览 / 管理
    "preview.prev": "上一页",
    "preview.next": "下一页",
    "preview.zoom_out": "缩小",
    "preview.zoom_in": "放大",
    "preview.fit": "适应窗口",
    "preview.fail": "预览失败：{error}",
    "pages.title": "页面管理 — {name}",
    "pages.tip": "多选可删除、旋转；按住一页拖到两页之间，蓝竖线处松手即可重排。双击或点「预览」看大图。",
    "pages.delete": "删除选中页",
    "pages.rot_left": "左转 90°",
    "pages.rot_right": "右转 90°",
    "pages.preview": "预览选中页",
    "pages.extract": "仅提取选中页",
    "pages.save_all": "另存全部当前页",
    "pages.keep_one": "至少保留一页",
    "pages.need_preview": "请先选中一页再预览",
    "pages.need_extract": "请先选中要提取的页面",
    "pages.page_label": "原页{num}",

    # 主窗消息
    "msg.need_check_remove": "请先勾选要移除的文件",
    "msg.remove_confirm_title": "确认移除",
    "msg.remove_confirm_body": (
        "确定从列表中移除勾选的 {count} 个文件？\n\n"
        "此操作仅移除列表中的文件，不会删除您电脑上的原始 PDF。"
    ),
    "msg.need_select_preview": "请先点击选中一个 PDF 文件",
    "msg.need_select_pdf": "请先选中一个 PDF",
    "msg.bad_pdf_pwd": "无法读取该 PDF（密码错误或文件损坏）",
    "msg.bad_pdf": "无法打开该文件，可能不是有效 PDF",
    "msg.cannot_open_detail": "无法打开文件：{error}",
    "msg.split_ranges_empty": "没有有效的页范围。请填写 1～总页数 内、且起始页不大于结束页的区间。",
    "msg.pages_open_fail": "无法打开页面管理：\n{error}",
    "msg.pages_empty": "没有可保存的页面",
    "msg.cannot_open": "无法打开该文件",
    "msg.not_encrypted": "该 PDF 未加密，无需解除密码",
    "msg.task_cancelled": "任务已取消，半成品文件已清理",
    "msg.done_files": "{msg}\n共生成 {count} 个文件",
    "msg.convert_warn_title": "转换完成（有提示）",
    "msg.op_failed": "操作失败",
    "msg.op_failed_retry": "操作失败，请重试",
    "msg.op_failed_detail": "操作失败：\n{msg}",
    "msg.context_preview": "预览此 PDF",
    "msg.context_split": "拆分此 PDF",


    "msg.cannot_open_named": "无法打开文件：\n{name}",
    "msg.op_failed_console": "操作失败，请查看控制台输出",
    "msg.imported": "已导入 {count} 个 PDF 文件",

    "status.list_summary": "共 {count} 个 PDF — 勾选文件后拖拽右侧 ≡ 手柄调整顺序",
    "status.cancelling": "正在取消...",
    "status.error": "操作出错",

    "btn.merge_n": "合并勾选的 PDF ({count}个)",

    "path.invalid_warn_detail": "默认保存路径不存在，无法执行操作：\n{path}\n\n请先设置一个有效的保存路径再试。",

    "pwd.title_named": "输入密码 — {name}",
    "pwd.unlock_title": "输入打开密码以解除加密",

    "preview.offline_title": "页面预览（离线）",
    "preview.empty": "无可预览页面",
    "preview.info": "当前列表第 {current}/{total} 页（原页 {source}）  缩放 {zoom}%",

    "pages.gen_thumbs": "正在生成缩略图…",

    "task.merge": "正在合并 PDF，请稍候...",
    "task.merge_done": "合并完成！",
    "task.split": "正在拆分 PDF，请稍候...",
    "task.split_done": "拆分完成！",
    "task.to_images": "正在将 PDF 转为图片，请稍候...",
    "task.to_images_done": "转图片完成！",
    "task.to_word": "正在将 PDF 转为 Word（支持 OCR 识别图片文字）…",
    "task.to_word_done": "转 Word 完成！",
    "task.batch_progress": "（{current}/{total}）{msg}",
    "task.batch_queued": "已排队 {queued} 个任务（共 {total} 个）…",
    "task.batch_summary": "批量完成：共 {total} 个，成功 {ok}，失败 {fail}",
    "task.batch_ok": "✓",
    "task.batch_fail": "✗",
    "task.batch_unnamed": "未命名任务",
    "convert.missing_pdf2docx": "缺少 pdf2docx 组件，请重新安装程序。",
    "convert.word_fallback": "版式引擎转换失败，已改用纯文本提取生成 Word（内容仍可编辑，版式可能简化）。",
    "convert.ocr_used": "已使用 OCR 识别图片中的文字。\n",
    "convert.ocr_missing": (
        "（未检测到 OCR 引擎，图片页仅嵌入截图，无识别文字。\n"
        "完整版应已内置 RapidOCR；若仍无识别，请重新安装本程序。）\n"
    ),
    "convert.all_image_pages": "该 PDF 全部 {total} 页均为纯图片（扫描件）。\n{ocr}已将页面截图嵌入 Word 文档。",
    "convert.mixed_image_pages": "检测到第 {pages} 为纯图片页。\n{ocr}文字页已正常提取文本。",
    "convert.more_pages": " 等 {count} 页",
    "convert.error": "转换出错：{error}",
    "convert.word_worker_incomplete": "转 Word 子进程未能完成。",
    "convert.word_worker_crashed": (
        "转 Word 子进程异常退出（多为复杂 PDF 触发的底层组件崩溃）。"
        "主程序已保护未退出，请换文件重试或改用「转图片」后再处理。"
    ),
    "convert.word_worker_start_fail": "无法启动转 Word 子进程：{error}",
    "convert.images_error": "转图片出错：{error}",
    "convert.dpi_auto_reduced": (
        "请求清晰度为 {requested} DPI，部分页面因尺寸过大已自动降低，"
        "以免导出全白图：{notes}。内容应已正常导出；若仍偏白请改用 300～600 DPI。"
    ),
    "task.compress": "正在压缩 PDF，请稍候...",
    "task.compress_done": "压缩完成！",
    "task.pages": "正在保存页面整理结果…",
    "task.pages_done": "页面整理完成！",
    "task.stamp": "正在添加水印/页码…",
    "task.stamp_done": "水印/页码处理完成！",
    "msg.need_merge": "请至少勾选 2 个 PDF 文件才能合并\n\n提示：点击文件前面的复选框即可勾选",
    "file.import_title": "选择要导入的 PDF 文件",
    "file.filter_pdf": "PDF文件 (*.pdf)",
    "file.suffix_stamp_short": "_水印",
    "task.encrypt": "正在加密 PDF…",
    "task.encrypt_done": "加密完成！",
    "task.decrypt": "正在解除密码…",
    "task.decrypt_done": "已另存为无密码 PDF！",
    "task.img2pdf": "正在将图片转为 PDF…",
    "task.img2pdf_done": "图片转 PDF 完成！",

    "file.merge_default": "合并后的文件.pdf",
    "file.images_default": "图片合集.pdf",
    "file.pick_images": "选择要转为 PDF 的图片",
    "file.filter_images": "图片 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;所有文件 (*.*)",
    "file.split_dir": "选择拆分输出目录",
    "file.images_dir": "选择图片输出目录",
    "file.select_folder": "选择文件夹",
    "file.save_title": "选择保存位置",
    "file.filter_pdf_save": "PDF文件 (*.pdf)",
    # 输出文件名（随当前界面语言；{start}/{end}/{page} 为 1-based 展示）
    "out.image_page": "{base}_第{page}页.{fmt}",
    "out.split_by_pages": "{base}_第{index}部分_{start}-{end}页.pdf",
    "out.split_by_range": "{base}_第{index}份_{start}-{end}页.pdf",
    "file.suffix_pages": "_页面整理",
    "file.suffix_decrypt": "_解密",
    "file.suffix_compress": "_压缩",
    "file.suffix_stamp": "_水印页码",
    "file.suffix_encrypt": "_加密",

    "op.merge": "合并",
    "op.split": "拆分",
    "op.to_images": "转图片",
    "op.to_word": "转Word",
    "op.compress": "压缩",
    "op.pages": "页面管理",
    "op.stamp": "水印页码",
    "op.encrypt": "加密",
    "op.decrypt": "解密",
    "op.img2pdf": "图片转PDF",

    # 悬停帮助 — 导入
    "hover.import.title": "导入 PDF 文件",
    "hover.import.desc": "从电脑任意位置选择一个或多个 PDF 文件，导入到工具中进行处理。文件会被复制到程序内部工作空间，不会影响原始文件。",
    "hover.import.steps": (
        "1. 点击「导入 PDF」按钮（或直接从文件管理器拖入PDF）\n"
        "2. 在弹出的文件对话框中选择一个或多个 PDF 文件\n"
        "3. 选中的文件将出现在下方列表中，按导入顺序排列"
    ),
    "hover.remove.title": "移除选中的文件",
    "hover.remove.desc": "从列表中移除已勾选的文件。此操作仅删除程序工作空间中的副本，绝不会删除您电脑上的原始 PDF 文件。",
    "hover.remove.steps": (
        "1. 在文件列表中勾选要移除的文件\n"
        "2. 点击「移除选中」按钮\n"
        "3. 确认后文件将从列表中移除"
    ),
    "hover.preview.title": "预览 PDF 文件",
    "hover.preview.desc": "使用系统默认的 PDF 阅读器打开选中的 PDF 文件，方便查看内容。",
    "hover.preview.steps": (
        "1. 在文件列表中点击选中一个 PDF 文件\n"
        "2. 点击「预览」按钮（或直接双击文件）\n"
        "3. 系统默认 PDF 阅读器将打开该文件"
    ),
    "hover.merge.title": "合并 PDF 文件",
    "hover.merge.desc": "将多个 PDF 文件按列表中的排列顺序，无损合并为一个新的 PDF 文件。合并后完整保留原始清晰度、嵌入字体和图片质量。",
    "hover.merge.steps": (
        "1. 在文件列表中勾选要合并的 PDF（至少勾选2个）\n"
        "2. 使用右侧 ≡ 手柄拖拽调整文件排列顺序\n"
        "3. 点击「合并勾选的 PDF」按钮\n"
        "4. 在弹出的保存对话框中选择保存位置\n"
        "5. 等待进度条完成"
    ),
    "hover.split.title": "拆分 PDF 文件",
    "hover.split.desc": "将一个 PDF 拆分成多个文件。支持三种拆分方式：按页数拆分、按份数拆分、自定义页范围。拆分后保留原始清晰度。",
    "hover.split.steps": (
        "1. 在文件列表中选中一个 PDF\n"
        "2. 点击「拆分 PDF」按钮\n"
        "3. 选择拆分方式（按页数/按份数/自定义页范围）\n"
        "4. 自定义模式下可添加多份并填写每份的起止页\n"
        "5. 可使用预览按钮确认拆分结果\n"
        "6. 选择输出目录后开始拆分"
    ),
    "hover.to_images.title": "PDF 转图片",
    "hover.to_images.desc": "将 PDF 的每一页转换为高分辨率图片。支持 PNG/JPG/BMP/TIFF 格式，可调节 DPI 控制清晰度。DPI 越高越清晰，文件也越大。",
    "hover.to_images.steps": (
        "1. 在文件列表中选中一个 PDF\n"
        "2. 点击「PDF 转图片」按钮\n"
        "3. 选择输出格式和清晰度（推荐300 DPI）\n"
        "4. 选择输出目录\n"
        "5. 等待转换完成，每页生成一张图片"
    ),
    "hover.to_word.title": "PDF 转 Word (.docx)",
    "hover.to_word.desc": "将 PDF 转为可编辑 Word。文字型尽量保留版式；扫描件/图片页会嵌入截图，并用内置 RapidOCR（离线中英）识别文字。",
    "hover.to_word.steps": (
        "1. 在文件列表中选中一个 PDF\n"
        "2. 点击「PDF 转 Word」按钮\n"
        "3. 在弹出的保存对话框中选择保存位置\n"
        "4. 等待转换完成（扫描件会自动 OCR）"
    ),
    "hover.to_word.warn": "复杂表格/特殊排版可能无法完全还原；扫描件以「截图+OCR文字」方式写入 Word",
    "hover.compress.title": "PDF 压缩",
    "hover.compress.desc": "离线压缩 PDF 体积。可选轻度/标准/强力，或填写目标体积（如 10MB）自动逼近。完成后对比原体积；输出不会比原来更大。",
    "hover.compress.steps": (
        "1. 在文件列表中选中一个 PDF\n"
        "2. 点击「PDF 压缩」\n"
        "3. 选择档位，或勾选「按目标体积」并填写 MB\n"
        "4. 选择输出保存位置\n"
        "5. 等待完成并查看体积对比提示"
    ),
    "hover.compress.warn": "目标体积是近似值；纯文字/矢量文件可能压不到很小。强力或整页栅格化会降低清晰度",
    "hover.pages.title": "页面管理",
    "hover.pages.desc": "用缩略图整理整本 PDF：删除页、旋转、提取选中页、拖拽重排，另存为新文件，不覆盖原文件。",
    "hover.pages.steps": (
        "1. 选中一个 PDF 后点击「页面管理」\n"
        "2. 按住一页拖到两页之间，蓝竖线处松手重排；也可多选删除/旋转\n"
        "3. 双击或点「预览」离线查看大图；也可「仅提取选中页」\n"
        "4. 确定后选择另存路径"
    ),
    "hover.pages.warn": "操作结果始终另存，不会直接改坏工作区原文件",
    "hover.stamp.title": "水印与页码",
    "hover.stamp.desc": "为 PDF 叠加文字/图片水印，并可添加可自定义模板的页码，适合合同、标书、内部资料。",
    "hover.stamp.steps": (
        "1. 选中一个 PDF 后点击「水印与页码」\n"
        "2. 勾选文字水印（可平铺/选色），或添加半透明图片水印、页码\n"
        "3. 选择输出保存位置\n"
        "4. 等待处理完成"
    ),
    "hover.stamp.warn": "水印写入页面内容层，请确认后再分发",
    "hover.encrypt.title": "加密 PDF",
    "hover.encrypt.desc": "将 PDF 另存为 AES-256 加密文件，打开时需密码；可限制打印与复制文本。",
    "hover.encrypt.steps": (
        "1. 选中一个 PDF 后点击「加密 PDF」\n"
        "2. 设置并确认用户密码，勾选权限\n"
        "3. 若源文件已加密，先输入打开密码\n"
        "4. 选择加密后的保存位置"
    ),
    "hover.encrypt.warn": "请牢记密码；本工具无法找回遗忘密码",
    "hover.decrypt.title": "解除密码",
    "hover.decrypt.desc": "在验证正确打开密码后，将加密 PDF 另存为无密码版本，便于后续合并或转换。",
    "hover.decrypt.steps": (
        "1. 选中已加密的 PDF\n"
        "2. 点击「解除密码」并输入正确密码\n"
        "3. 选择无密码输出保存位置"
    ),
    "hover.decrypt.warn": "仅在您拥有合法权限时解除加密",
    "hover.img2pdf.title": "图片转 PDF",
    "hover.img2pdf.desc": "将多张 PNG/JPG 等图片按顺序合成一个 PDF，可适应 A4 或按原图像素建页。",
    "hover.img2pdf.steps": (
        "1. 点击「图片转 PDF」并多选图片\n"
        "2. 在对话框中调整顺序与页面模式\n"
        "3. 选择输出 PDF 保存位置\n"
        "4. 等待生成完成"
    ),
    "hover.path.title": "设置默认保存路径",
    "hover.path.desc": "设置一个文件夹作为默认保存路径。设置后，合并和转换操作保存文件时会优先定位到该路径。如未设置，默认使用桌面。",
    "hover.path.steps": (
        "1. 点击「浏览...」按钮\n"
        "2. 在弹出的对话框中选择一个文件夹\n"
        "3. 勾选「记住此路径」则下次打开程序时自动恢复\n"
        "4. 也可以在输入框中直接输入路径"
    ),
    "hover.history.title": "历史记录",
    "hover.history.desc": "查看之前所有操作的历史记录。可下载以往合并/拆分/转换的输出文件，或快速打开源文件所在的文件夹。最多保留最近10条记录。",
    "hover.history.steps": (
        "1. 点击「历史」按钮打开历史记录窗口\n"
        "2. 查看操作时间、类型、文件数量等信息\n"
        "3. 点击「下载」可将历史输出文件保存到本地\n"
        "4. 点击「源文件夹」打开源 PDF 所在目录\n"
        "5. 点击「输出文件夹」打开输出文件所在目录\n"
        "6. 点击「删除」可移除不再需要的历史记录"
    ),
    "hover.font.title": "字体大小",
    "hover.font.desc": "切换界面字号：默认 / 大 / 特大。字号会随窗口缩放一起适配，并记住你的选择。",
    "hover.font.steps": (
        "1. 在导入行右侧选择「字体」档位\n"
        "2. 界面字号、按钮与列表行高同步调整\n"
        "3. 下次启动自动恢复上次选择"
    ),
    "hover.font.warn": "特大字号下窗口过窄时请适当拉宽窗口",
    "hover.language.title": "界面语言",
    "hover.language.desc": "一键切换软件界面中文 / 英文。切换后主界面立即更新，新打开的对话框也会使用当前语言。",
    "hover.language.steps": (
        "1. 在「历史」右侧选择语言\n"
        "2. 界面文案立即切换\n"
        "3. 下次启动自动恢复上次语言"
    ),
}

# ---------------------------------------------------------------------------
# 英文文案（通顺产品用语）
# ---------------------------------------------------------------------------
_EN: Dict[str, str] = {
    "dialog.ok": "OK",
    "dialog.cancel": "Cancel",
    "dialog.close": "Close",
    "dialog.tip": "Notice",
    "dialog.error": "Error",
    "dialog.done": "Done",
    "dialog.confirm": "Confirm",
    "dialog.failed": "Failed",
    "dialog.browse": "Browse...",
    "common.all_files": "All files (*.*)",

    "main.ready": "Ready — import PDFs to get started",
    "main.credit": "Created by <b style='color:{color};'>{author}</b>. Thank you for using PDF2plus!",
    "main.version_tip": "{app} version V{version}",
    "main.cancel": "Cancel",
    "main.task_cancelled_status": "Task cancelled",
    "startup.recover_title": "Recover session",
    "startup.recover_body": (
        "The previous session did not exit cleanly.\n\n"
        "Keep the PDFs from last time?\n"
        "(No clears the workspace; Yes keeps the files.)"
    ),

    "path.label": "Default save folder:",
    "path.placeholder": "Leave empty to save to the Desktop",
    "path.remember": "Remember this folder for next launch",
    "path.unset": "Not set (files will save to the Desktop)",
    "path.valid": "✓ Folder is valid",
    "path.invalid": "⚠ Folder not found — please set again",
    "path.invalid_warn_title": "Invalid folder",
    "path.invalid_warn_body": "The default save folder is missing or invalid.\nPlease choose a valid folder first.",

    "list.select_all": "Select all / Clear",
    "list.checked": "Selected: {count}",
    "list.pages_suffix": "  ({pages} pages)",
    "list.drop_here": "📥 Drop here",

    "btn.import": "Import PDF",
    "btn.remove": "Remove",
    "btn.preview": "Preview",
    "label.font": "Font:",
    "label.theme": "Theme:",
    "label.language": "Language:",
    "theme.light": "Light",
    "theme.dark": "Dark",
    "lang.zh": "中文",
    "lang.en": "English",
    "font.default": "Default",
    "font.large": "Large",
    "font.xlarge": "Extra large",
    "btn.history": "History",
    "btn.history.tip": "Open history: download past outputs or open source/output folders",

    "group.merge": "Merge",
    "group.convert": "Convert",
    "group.organize": "Organize",
    "group.security": "Security",
    "group.create": "Create",
    "btn.merge": "Merge selected PDFs",
    "btn.copy_original": "Keep original PDF when converting",
    "btn.split": "Split PDF",
    "btn.to_images": "PDF to images",
    "btn.to_word": "PDF to Word",
    "btn.compress": "Compress PDF",
    "btn.pages": "Page manager",
    "btn.stamp": "Watermark && page numbers",
    "btn.encrypt": "Encrypt PDF",
    "btn.decrypt": "Remove password",
    "btn.images_to_pdf": "Images to PDF",

    "desc.placeholder": "Hover a feature button to see its description",
    "desc.idle": "&#128218; Hover a feature button to see its description",
    "desc.offline": "Fully offline — no internet required",
    "desc.online": "Requires an internet connection",
    "steps.placeholder": "Hover a feature button to see how to use it",
    "steps.idle": "&#128196; Hover a feature button to see how to use it",
    "steps.title": "{title} — How to use",

    "split.title": "Split PDF",
    "split.working_on": "📄 Splitting: {name}",
    "split.info": "This PDF has {pages} pages. Choose how to split:",
    "split.mode": "Split method",
    "split.by_pages": "By page count: every",
    "split.pages_unit": "pages per file",
    "split.by_copies": "Into equal parts:",
    "split.copies_unit": "parts",
    "split.by_ranges": "Custom page ranges",
    "split.ranges_group": "Custom page ranges",
    "split.col_start": "Start page",
    "split.col_end": "End page",
    "split.add_range": "+ Add range",
    "split.del_range": "- Remove selected",
    "split.ranges_tip": (
        "Each row becomes one file. Pages run from 1 to the total; "
        "use Add range for more segments, then scroll if the list grows."
    ),

    "export.title": "Export images",
    "export.params": "Export settings",
    "export.format": "Format",
    "export.dpi": "Resolution (DPI)",
    "export.dpi_300": "300 (High quality)",
    "export.dpi_600": "600 (Ultra sharp)",
    "export.dpi_custom": "Custom",
    "export.dpi_hint": (
        "Range 72–1200. Use 300 for everyday printing, 600 for fine scans. "
        "Higher is sharper and larger. "
        "Very high DPI is auto-capped per page to avoid blank white exports."
    ),
    "export.dpi_spin_tip": "Custom resolution, 72–1200 DPI; oversized values are auto-reduced per page",

    "history.title": "History (up to 10 items)",
    "history.col_time": "Time",
    "history.col_type": "Type",
    "history.col_sources": "Sources",
    "history.col_output": "Output",
    "history.col_actions": "Actions",
    "history.col_delete": "Delete",
    "history.legend": (
        "Buttons: <span style='color:{c1};'>●</span> Download output ｜ "
        "<span style='color:{c2};'>●</span> Open source folder ｜ "
        "<span style='color:{c3};'>●</span> Open output folder ｜ "
        "<span style='color:{c4};'>●</span> Delete this record"
    ),
    "history.hover_hint": "Hover a button for details",
    "history.dl_desc": "Download: save the output file to a location you choose",
    "history.dl_tip": "Download output",
    "history.src_desc": "Open source folder: open the folder that contains the source files",
    "history.src_tip": "Open source folder",
    "history.out_desc": "Open output folder: open the folder that contains the output file",
    "history.out_tip": "Open output folder",
    "history.del_desc": "Delete: remove this history record",
    "history.del_tip": "Delete record",
    "history.save_as": "Save as",
    "history.dl_ok": "File saved successfully",
    "history.dl_fail": "Download failed — the output file may have been deleted",
    "history.del_confirm": "Delete this history record?",
    "history.restore_name": "restore_{id}{ext}",

    "pwd.title": "PDF password",
    "pwd.prompt": "This PDF is encrypted. Enter the password:",
    "encrypt.title": "Encrypt PDF",
    "encrypt.pwd_group": "Open password",
    "encrypt.user_pwd": "Password",
    "encrypt.confirm_pwd": "Confirm password",
    "encrypt.perm_group": "Permissions",
    "encrypt.allow_print": "Allow printing",
    "encrypt.allow_copy": "Allow copying text",
    "encrypt.empty_pwd": "Password cannot be empty",
    "encrypt.pwd_mismatch": "Passwords do not match",
    "compress.title": "Compress PDF",
    "compress.level": "Compression method",
    "compress.choose": "Choose how to compress (fully offline):",
    "compress.original": "Original PDF size: {size} ({bytes} bytes)",
    "compress.light": "Light (mostly lossless; smaller size reduction)",
    "compress.standard": "Standard (recommended for everyday use)",
    "compress.strong": "Strong (smaller file; images may look softer)",
    "compress.target_mode": "Target size (get close; not exact to the byte)",
    "compress.target_label": "Target size:",
    "compress.target_unit": "MB",
    "compress.target_hint": "Must be smaller than the original. Scans usually shrink well; text/vector PDFs have a floor.",
    "compress.target_invalid_dialog": "Target size must be greater than 0 and smaller than the original PDF.",
    "compress.target_disabled_tip": "Original file size is unavailable, so Target size cannot be used. Select a valid PDF first.",
    "compress.rasterize": "If still too large, allow full-page rasterize (text becomes unselectable; off by default)",
    "compress.rasterize_tip": "Last resort: turn each page into an image. Size may drop further, but text cannot be copied.",
    "compress.msg.missing": "Source file not found",
    "compress.msg.cancelled": "Cancelled",
    "compress.msg.failed": "Compression failed: {error}",
    "compress.msg.target_invalid": "Target size must be greater than 0 and smaller than the original PDF",
    "compress.msg.ok": "{original} → {output} (about {percent}% saved)",
    "compress.msg.ok_target": "{original} → {output} (target {target}, about {percent}% saved)",
    "compress.msg.ok_target_floor": "{original} → {output} (target {target}). Quality floor reached; cannot shrink further.",
    "compress.msg.cannot_shrink": "Original {original}. This file cannot be made smaller; saved at the original size.",

    "stamp.title": "Watermark & page numbers",
    "stamp.text_group": "Text watermark",
    "stamp.add_text": "Add text watermark",
    "stamp.default_text": "Confidential",
    "stamp.font_size": "Size",
    "stamp.rotate": "Rotate °",
    "stamp.opacity": "Opacity",
    "stamp.color": "Color",
    "stamp.color_red": "Red",
    "stamp.color_blue": "Blue",
    "stamp.color_black": "Black",
    "stamp.color_gray": "Gray",
    "stamp.color_orange": "Orange",
    "stamp.custom_color": "Custom…",
    "stamp.custom_color_tip": "Open the color picker",
    "stamp.swatch_tip": "Current watermark color (click to customize)",
    "stamp.tile_text": "Tile text watermark diagonally (great for contracts)",
    "stamp.image_group": "Image watermark",
    "stamp.add_image": "Add image watermark",
    "stamp.image_placeholder": "Choose a PNG/JPG image…",
    "stamp.browse": "Browse…",
    "stamp.image_scale": "Image scale",
    "stamp.image_scale_tip": "Relative to page width — too large may cover content",
    "stamp.image_opacity": "Image opacity",
    "stamp.image_opacity_tip": "1 = opaque; 0.25–0.45 usually works well",
    "stamp.tile_image": "Tile image watermark",
    "stamp.underlay": "Place under content (may be hidden on scanned/white pages)",
    "stamp.page_group": "Page numbers",
    "stamp.add_page_no": "Add page numbers",
    "stamp.page_template": "Page {page} of {total}",
    "stamp.page_format": "Preset",
    "stamp.page_custom": "Custom template",
    "stamp.page_custom_tip": "Edit freely; use {page} and {total}",
    "stamp.tpl_full": "Page {page} of {total}",
    "stamp.tpl_compact_cn": "{page}/{total} pages",
    "stamp.tpl_slash_page": "{page}/{total} p.",
    "stamp.tpl_slash": "{page}/{total}",
    "stamp.tpl_spaced": "{page} / {total}",
    "stamp.tpl_page_only": "Page {page}",
    "stamp.tpln_full": "Page X of X",
    "stamp.tpln_compact_cn": "X/X pages",
    "stamp.tpln_slash_page": "X/X p.",
    "stamp.tpln_slash": "X/X",
    "stamp.tpln_spaced": "X / X",
    "stamp.tpln_page_only": "Page X",
    "stamp.tpl_custom": "Custom (edit the box below)",
    "stamp.position": "Shortcut",
    "stamp.pos_bc": "Bottom center",
    "stamp.pos_bl": "Bottom left",
    "stamp.pos_br": "Bottom right",
    "stamp.pos_tc": "Top center",
    "stamp.pos_tl": "Top left",
    "stamp.pos_tr": "Top right",
    "stamp.unit": "Units",
    "stamp.unit_mm": "mm",
    "stamp.unit_px": "px",
    "stamp.offset_left": "From left",
    "stamp.offset_bottom": "From bottom",
    "stamp.offset_top": "From top",
    "stamp.box_width": "Box width",
    "stamp.box_height": "Box height",
    "stamp.page_font": "Type size",
    "stamp.page_font_effective": "Drawn at {actual} (box too narrow for {requested}; widen the page-number box)",
    "stamp.preview": "Preview",
    "stamp.preview_page": "Page",
    "stamp.preview_empty": "Preview unavailable (file unreadable or password needed)",
    "stamp.preview_hint": "Click the thumbnail to enlarge",
    "stamp.preview_enlarge": "Enlarge",
    "stamp.preview_large_title": "Page-number preview (zoomable)",
    "stamp.preview_full_title": "Watermark & page-number preview (zoomable)",
    "stamp.preview_click_tip": "Click to enlarge",
    "stamp.preview_watermark": "Preview watermark",
    "stamp.preview_watermark_tip": "Open a zoomable preview with current text/image watermarks and page numbers",
    "stamp.preview_zoom": "Zoom",
    "stamp.preview_zoom_reset": "100%",
    "stamp.preview_zoom_tip": "Use +/− or Ctrl+wheel to zoom; scroll to check corners",
    "stamp.margin": "Margin",
    "stamp.margin_suffix": " mm",
    "stamp.margin_tip": "Distance from the left and from the bottom (or top); switch units anytime",
    "stamp.pick_color": "Choose watermark color",
    "stamp.pick_image": "Choose watermark image",
    "stamp.image_filter": "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;All files (*.*)",
    "stamp.need_one": "Enable at least one option: text watermark, image watermark, or page numbers",
    "stamp.need_image": "Please choose a valid watermark image",
    "stamp.mm_sample": "40.0 mm",

    "img2pdf.title": "Images to PDF",
    "img2pdf.order": "Image order",
    "img2pdf.order_tip": "Move images up/down to change page order:",
    "img2pdf.up": "Move up",
    "img2pdf.down": "Move down",
    "img2pdf.mode": "Page mode",
    "img2pdf.a4": "Fit to A4 (recommended)",
    "img2pdf.orig": "Use original pixel size",
    "img2pdf.insert_here": "Insert here",

    "preview.prev": "Previous",
    "preview.next": "Next",
    "preview.zoom_out": "Zoom out",
    "preview.zoom_in": "Zoom in",
    "preview.fit": "Fit window",
    "preview.fail": "Preview failed: {error}",
    "pages.title": "Page manager — {name}",
    "pages.tip": "Multi-select to delete or rotate. Drag a page between others and drop on the blue line to reorder. Double-click or use Preview for a larger view.",
    "pages.delete": "Delete selected",
    "pages.rot_left": "Rotate left 90°",
    "pages.rot_right": "Rotate right 90°",
    "pages.preview": "Preview selected",
    "pages.extract": "Extract selected only",
    "pages.save_all": "Save all current pages",
    "pages.keep_one": "Keep at least one page",
    "pages.need_preview": "Select a page first to preview",
    "pages.need_extract": "Select pages to extract first",
    "pages.page_label": "Page {num}",

    "msg.need_check_remove": "Select files to remove first",
    "msg.remove_confirm_title": "Confirm remove",
    "msg.remove_confirm_body": (
        "Remove {count} selected file(s) from the list?\n\n"
        "This only removes copies in the workspace — your original PDFs stay untouched."
    ),
    "msg.need_select_preview": "Select a PDF in the list first",
    "msg.need_select_pdf": "Select a PDF first",
    "msg.bad_pdf_pwd": "Cannot read this PDF (wrong password or damaged file)",
    "msg.bad_pdf": "Cannot open this file — it may not be a valid PDF",
    "msg.cannot_open_detail": "Cannot open file: {error}",
    "msg.split_ranges_empty": "No valid page ranges. Use pages from 1 to the total, with start ≤ end.",
    "msg.pages_open_fail": "Cannot open page manager:\n{error}",
    "msg.pages_empty": "There are no pages to save",
    "msg.cannot_open": "Cannot open this file",
    "msg.not_encrypted": "This PDF is not encrypted",
    "msg.task_cancelled": "Task cancelled. Temporary files were cleaned up.",
    "msg.done_files": "{msg}\nCreated {count} file(s)",
    "msg.convert_warn_title": "Finished (with notes)",
    "msg.op_failed": "Operation failed",
    "msg.op_failed_retry": "Operation failed. Please try again.",
    "msg.op_failed_detail": "Operation failed:\n{msg}",
    "msg.context_preview": "Preview this PDF",
    "msg.context_split": "Split this PDF",


    "msg.cannot_open_named": "Cannot open file:\n{name}",
    "msg.op_failed_console": "Operation failed. Check the console for details.",
    "msg.imported": "Imported {count} PDF file(s)",

    "status.list_summary": "{count} PDF(s) — check files, then drag the ≡ handle to reorder",
    "status.cancelling": "Cancelling...",
    "status.error": "An error occurred",

    "btn.merge_n": "Merge checked PDFs ({count})",

    "path.invalid_warn_detail": "Default save folder does not exist:\n{path}\n\nPlease set a valid folder first.",

    "pwd.title_named": "Password — {name}",
    "pwd.unlock_title": "Enter password to remove encryption",

    "preview.offline_title": "Page preview (offline)",
    "preview.empty": "No pages to preview",
    "preview.info": "List page {current}/{total} (source {source})  Zoom {zoom}%",

    "pages.gen_thumbs": "Generating thumbnails…",

    "task.merge": "Merging PDFs…",
    "task.merge_done": "Merge complete!",
    "task.split": "Splitting PDF…",
    "task.split_done": "Split complete!",
    "task.to_images": "Converting PDF to images…",
    "task.to_images_done": "Image export complete!",
    "task.to_word": "Converting PDF to Word (OCR for scanned pages)…",
    "task.to_word_done": "Word export complete!",
    "task.batch_progress": "({current}/{total}) {msg}",
    "task.batch_queued": "{queued} task(s) queued ({total} total)…",
    "task.batch_summary": "Batch finished: {total} total, {ok} succeeded, {fail} failed",
    "task.batch_ok": "OK",
    "task.batch_fail": "FAIL",
    "task.batch_unnamed": "Unnamed task",
    "convert.missing_pdf2docx": "pdf2docx is missing. Please reinstall the app.",
    "convert.word_fallback": (
        "Layout conversion failed; fell back to plain-text extraction "
        "(editable, but layout may be simplified)."
    ),
    "convert.ocr_used": "OCR was used to read text from image pages.\n",
    "convert.ocr_missing": (
        "(No OCR engine found; image pages were embedded as screenshots only.\n"
        "The full build should include RapidOCR; reinstall if recognition is missing.)\n"
    ),
    "convert.all_image_pages": (
        "All {total} pages are image-only (scans).\n{ocr}"
        "Page screenshots were embedded in the Word file."
    ),
    "convert.mixed_image_pages": (
        "Image-only pages detected: {pages}.\n{ocr}"
        "Text pages were extracted normally."
    ),
    "convert.more_pages": " and {count} more",
    "convert.error": "Conversion error: {error}",
    "convert.word_worker_incomplete": "The Word conversion worker did not finish.",
    "convert.word_worker_crashed": (
        "The Word conversion worker exited abnormally "
        "(often a native crash on complex PDFs). "
        "The main window was protected; try another file or export to images first."
    ),
    "convert.word_worker_start_fail": "Could not start the Word worker: {error}",
    "convert.images_error": "Image export error: {error}",
    "convert.dpi_auto_reduced": (
        "Requested {requested} DPI; some pages were auto-reduced to avoid blank white "
        "exports: {notes}. Content should be fine; use 300–600 DPI if results look soft."
    ),
    "task.compress": "Compressing PDF…",
    "task.compress_done": "Compression complete!",
    "task.pages": "Saving page edits…",
    "task.pages_done": "Page edits saved!",
    "task.stamp": "Adding watermark / page numbers…",
    "task.stamp_done": "Watermark / page numbers applied!",
    "msg.need_merge": "Select at least 2 PDFs to merge.\n\nTip: use the checkbox in front of each file.",
    "file.import_title": "Choose PDF files to import",
    "file.filter_pdf": "PDF files (*.pdf)",
    "file.suffix_stamp_short": "_stamped",
    "task.encrypt": "Encrypting PDF…",
    "task.encrypt_done": "Encryption complete!",
    "task.decrypt": "Removing password…",
    "task.decrypt_done": "Saved as an unencrypted PDF!",
    "task.img2pdf": "Converting images to PDF…",
    "task.img2pdf_done": "Images-to-PDF complete!",

    "file.merge_default": "merged.pdf",
    "file.images_default": "images.pdf",
    "file.pick_images": "Choose images to convert to PDF",
    "file.filter_images": "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;All files (*.*)",
    "file.split_dir": "Choose split output folder",
    "file.images_dir": "Choose image output folder",
    "file.select_folder": "Choose folder",
    "file.save_title": "Save as",
    "file.filter_pdf_save": "PDF files (*.pdf)",
    "out.image_page": "{base}_page{page}.{fmt}",
    "out.split_by_pages": "{base}_part{index}_{start}-{end}.pdf",
    "out.split_by_range": "{base}_part{index}_{start}-{end}.pdf",
    "file.suffix_pages": "_pages",
    "file.suffix_decrypt": "_decrypted",
    "file.suffix_compress": "_compressed",
    "file.suffix_stamp": "_stamped",
    "file.suffix_encrypt": "_encrypted",

    "op.merge": "Merge",
    "op.split": "Split",
    "op.to_images": "To images",
    "op.to_word": "To Word",
    "op.compress": "Compress",
    "op.pages": "Page manager",
    "op.stamp": "Stamp / numbers",
    "op.encrypt": "Encrypt",
    "op.decrypt": "Decrypt",
    "op.img2pdf": "Images to PDF",

    "hover.import.title": "Import PDFs",
    "hover.import.desc": "Choose one or more PDFs from your computer. Files are copied into the app workspace so your originals stay safe.",
    "hover.import.steps": (
        "1. Click Import PDF (or drag PDFs in)\n"
        "2. Select one or more PDF files\n"
        "3. They appear in the list in import order"
    ),
    "hover.remove.title": "Remove selected files",
    "hover.remove.desc": "Remove checked items from the list. Only workspace copies are deleted — never your original files.",
    "hover.remove.steps": (
        "1. Check the files to remove\n"
        "2. Click Remove\n"
        "3. Confirm to clear them from the list"
    ),
    "hover.preview.title": "Preview PDF",
    "hover.preview.desc": "Open the selected PDF in your system’s default reader.",
    "hover.preview.steps": (
        "1. Click a PDF in the list\n"
        "2. Click Preview (or double-click the file)\n"
        "3. Your default PDF reader opens it"
    ),
    "hover.merge.title": "Merge PDFs",
    "hover.merge.desc": "Combine checked PDFs in list order into one file, keeping clarity, fonts, and image quality.",
    "hover.merge.steps": (
        "1. Check at least two PDFs\n"
        "2. Drag the ≡ handle to reorder\n"
        "3. Click Merge selected PDFs\n"
        "4. Choose where to save\n"
        "5. Wait for the progress bar"
    ),
    "hover.split.title": "Split PDF",
    "hover.split.desc": "Split one PDF into multiple files by page count, equal parts, or custom ranges — without losing quality.",
    "hover.split.steps": (
        "1. Select a PDF\n"
        "2. Click Split PDF\n"
        "3. Choose a split method\n"
        "4. For custom ranges, add start/end pages\n"
        "5. Optionally preview results\n"
        "6. Choose an output folder"
    ),
    "hover.to_images.title": "PDF to images",
    "hover.to_images.desc": "Export each page as a high-resolution image (PNG/JPG/BMP/TIFF). Higher DPI means sharper images and larger files.",
    "hover.to_images.steps": (
        "1. Select a PDF\n"
        "2. Click PDF to images\n"
        "3. Choose format and DPI (300 is a good default)\n"
        "4. Pick an output folder\n"
        "5. Wait until every page is exported"
    ),
    "hover.to_word.title": "PDF to Word (.docx)",
    "hover.to_word.desc": "Convert a PDF into an editable Word file. Text PDFs keep layout as much as possible; scanned pages get screenshots plus offline RapidOCR text.",
    "hover.to_word.steps": (
        "1. Select a PDF\n"
        "2. Click PDF to Word\n"
        "3. Choose where to save\n"
        "4. Wait for conversion (OCR runs automatically for scans)"
    ),
    "hover.to_word.warn": "Complex tables/layouts may not match perfectly; scans are saved as screenshot + OCR text",
    "hover.compress.title": "Compress PDF",
    "hover.compress.desc": "Shrink PDFs offline with Light/Standard/Strong, or enter a target size (e.g. 10 MB). The result is never larger than the original.",
    "hover.compress.steps": (
        "1. Select a PDF\n"
        "2. Click Compress PDF\n"
        "3. Pick a preset, or Target size and enter MB\n"
        "4. Choose a save location\n"
        "5. Compare the before/after size"
    ),
    "hover.compress.warn": "Target size is approximate; text/vector PDFs may not shrink much. Strong or rasterize reduces sharpness",
    "hover.pages.title": "Page manager",
    "hover.pages.desc": "Reorder, delete, rotate, or extract pages with thumbnails, then save as a new PDF without overwriting the original.",
    "hover.pages.steps": (
        "1. Select a PDF and open Page manager\n"
        "2. Drag between pages to reorder, or multi-select to delete/rotate\n"
        "3. Double-click or Preview for a larger view; or Extract selected only\n"
        "4. Confirm and choose a save path"
    ),
    "hover.pages.warn": "Results are always saved as a new file — the workspace original stays intact",
    "hover.stamp.title": "Watermark & page numbers",
    "hover.stamp.desc": "Add text/image watermarks and optional page numbers — ideal for contracts and internal docs.",
    "hover.stamp.steps": (
        "1. Select a PDF and open Watermark & page numbers\n"
        "2. Enable text (tiled/color), image watermark, and/or page numbers\n"
        "3. Choose where to save\n"
        "4. Wait until processing finishes"
    ),
    "hover.stamp.warn": "Watermarks become part of the page content — review before sharing",
    "hover.encrypt.title": "Encrypt PDF",
    "hover.encrypt.desc": "Save an AES-256 encrypted copy that requires a password, with optional print/copy limits.",
    "hover.encrypt.steps": (
        "1. Select a PDF and click Encrypt PDF\n"
        "2. Set and confirm the password, then choose permissions\n"
        "3. If the source is already encrypted, enter its open password first\n"
        "4. Choose where to save the encrypted file"
    ),
    "hover.encrypt.warn": "Remember your password — this app cannot recover a forgotten one",
    "hover.decrypt.title": "Remove password",
    "hover.decrypt.desc": "After verifying the open password, save an unencrypted copy for merging or converting.",
    "hover.decrypt.steps": (
        "1. Select an encrypted PDF\n"
        "2. Click Remove password and enter the correct password\n"
        "3. Choose where to save the unlocked file"
    ),
    "hover.decrypt.warn": "Only remove encryption when you have the right to do so",
    "hover.img2pdf.title": "Images to PDF",
    "hover.img2pdf.desc": "Combine PNG/JPG images into one PDF in order — fit to A4 or keep original pixel size.",
    "hover.img2pdf.steps": (
        "1. Click Images to PDF and select images\n"
        "2. Reorder and choose page mode\n"
        "3. Choose where to save the PDF\n"
        "4. Wait until generation finishes"
    ),
    "hover.path.title": "Default save folder",
    "hover.path.desc": "Pick a default folder for save dialogs. If unset, the Desktop is used.",
    "hover.path.steps": (
        "1. Click Browse...\n"
        "2. Choose a folder\n"
        "3. Check Remember this folder to restore it next time\n"
        "4. Or type a path directly"
    ),
    "hover.history.title": "History",
    "hover.history.desc": "Review recent operations, download past outputs, or open related folders. Up to 10 records are kept.",
    "hover.history.steps": (
        "1. Click History\n"
        "2. Review time, type, and file counts\n"
        "3. Download to save an old output locally\n"
        "4. Open the source folder\n"
        "5. Open the output folder\n"
        "6. Delete records you no longer need"
    ),
    "hover.font.title": "Font size",
    "hover.font.desc": "Switch UI text size: Default / Large / Extra large. It scales with the window and is remembered.",
    "hover.font.steps": (
        "1. Choose a Font size on the import row\n"
        "2. Text, buttons, and list rows update together\n"
        "3. Your choice is restored next launch"
    ),
    "hover.font.warn": "With Extra large text, widen the window if controls feel cramped",
    "hover.language.title": "Language",
    "hover.language.desc": "Switch the entire UI between Chinese and English. The main window updates immediately; new dialogs follow the current language.",
    "hover.language.steps": (
        "1. Choose a language to the right of History\n"
        "2. UI text updates right away\n"
        "3. Your choice is restored next launch"
    ),
}

_CATALOGS = {
    "zh": _ZH,
    "en": _EN,
}


def get_language() -> str:
    """返回当前语言代码：zh 或 en。"""
    return _current_language


def set_language(language_code: str) -> str:
    """
    设置当前界面语言。
    非法值回落为 zh；返回实际生效的语言代码。
    """
    global _current_language
    normalized = (language_code or "zh").strip().lower()
    if normalized not in _CATALOGS:
        normalized = "zh"
    _current_language = normalized
    return _current_language


def t(message_key: str, **format_args: Any) -> str:
    """
    按当前语言取文案；缺 key 时回落中文，再缺则返回 key 本身。
    支持 format 占位符，如 t("list.checked", count=3)。
    """
    catalog = _CATALOGS.get(_current_language, _ZH)
    text = catalog.get(message_key)
    if text is None:
        text = _ZH.get(message_key, message_key)
    if format_args:
        try:
            return text.format(**format_args)
        except (KeyError, ValueError):
            return text
    return text


def is_english() -> bool:
    """当前是否英文界面。"""
    return _current_language == "en"



# 历史记录里存的中文类型 → 翻译键（兼容旧记录）
_OP_TYPE_KEYS = {
    "合并": "op.merge",
    "拆分": "op.split",
    "转图片": "op.to_images",
    "转Word": "op.to_word",
    "压缩": "op.compress",
    "页面管理": "op.pages",
    "水印页码": "op.stamp",
    "加密": "op.encrypt",
    "解密": "op.decrypt",
    "图片转PDF": "op.img2pdf",
}


def translate_op_type(stored_type: str) -> str:
    """
    把历史记录中保存的操作类型显示成当前语言。
    未知类型原样返回，避免旧数据丢失。
    """
    key = _OP_TYPE_KEYS.get(stored_type or "")
    if key:
        return t(key)
    return stored_type or ""

def apply_dialog_button_box(button_box) -> None:
    """
    把 QDialogButtonBox 的确定/取消/关闭按钮文字改成当前语言。
    对话框创建后调用一次即可。
    """
    from PyQt5.QtWidgets import QDialogButtonBox

    mapping = {
        QDialogButtonBox.Ok: "dialog.ok",
        QDialogButtonBox.Cancel: "dialog.cancel",
        QDialogButtonBox.Close: "dialog.close",
        QDialogButtonBox.Yes: "dialog.confirm",
        QDialogButtonBox.No: "dialog.cancel",
    }
    for role, key in mapping.items():
        button = button_box.button(role)
        if button is not None:
            button.setText(t(key))
