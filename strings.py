"""
User-facing text, in one place.

The original was Chinese-only with copy written for one person's situation
("有篇稿子躺 136 天了"). The phrasing is deliberate and worth keeping — a
system alert phrased as a system alert gets ignored by the second week — so
the strings stay conversational in both languages rather than becoming
neutral UI labels in translation.

Templates use str.format with named fields.
"""

ZH = {
    # menu
    "menu_header": "瞭望鸡 · 替你盯着该发什么",
    "menu_note": "随手记一条  {key}",
    "menu_clipboard": "丢剪贴板上来",
    "menu_widget_on": "放个桌面组件",
    "menu_widget_off": "关掉桌面组件",
    "menu_shelf": "打开搁板",
    "menu_shelf_n": "打开搁板  ({n} 条待处理)",
    "menu_open": "打开主界面",
    "menu_ax": "⚠️ 开启快捷键权限",
    "menu_quit": "退出",
    "menu_pick_folder": "选择笔记文件夹…",
    "config_broken": "配置文件读不了，现在显示的是示例数据。\n{err}",
    "none_no_files": "这个文件夹里没有 markdown 笔记 · 点我换一个",
    "none_no_states": "读到笔记了，但没有一篇标了完成状态 · 点我看怎么标",
    "pick_prompt": "就用这个",
    "pick_message": "选一个装着 markdown 笔记的文件夹。只读，不会动里面的文件。",
    "pick_done": "读到 {library} 篇笔记，其中 {ready} 篇写完没发。\n{path}",
    "pick_none": "这个文件夹里没找到写完的笔记。\n看看 README 里「它需要你的文件夹长什么样」。",
    "first_title": "指向你自己的笔记",
    "first_message": ("现在显示的是示例数字。\n\n"
                      "选一个你的 markdown 笔记文件夹，它就会开始数你自己的东西 —— "
                      "哪几篇写完了却一直没发出去。\n\n"
                      "只读，永远不写。"),
    "first_ok": "选文件夹",
    "first_skip": "先看示例",
    "menu_app_quit": "退出瞭望鸡",

    # edit menu
    "edit_undo": "撤销",
    "edit_redo": "重做",
    "edit_cut": "剪切",
    "edit_copy": "拷贝",
    "edit_paste": "粘贴",
    "edit_select_all": "全选",

    # notifications
    "notify_title": "瞭望鸡",
    "notify_hotkeys_live": "快捷键已生效：{keys}",
    "notify_clip_empty": "剪贴板是空的",
    "notify_on_shelf": "已经在搁板上了",
    "notify_shelved": "已放上搁板",
    "notify_no_backend": "连不上数据源",
    "notify_widget_failed": "组件打不开",
    "notify_ax_hint": "在列表里勾选本应用，权限会自动生效",

    # capture field
    "prompts": [
        "刚才想到什么？",
        "一句话就行",
        "不用想清楚",
        "什么让你停下来了？",
        "现在脑子里是什么？",
        "写下来就不会跑掉",
        "半句也算",
    ],
    "capture_ok": "记下了，接着忙",
    "capture_to": "写进 {where}",
    "capture_fail": "没存上：{err}",
    "shelved_short": "上搁板了 · 还没进你的笔记",
    "already_shelved": "已经在搁板上了",

    # widget body
    "distill_day": "蒸馏 Day {day}",
    "streak_done": "连续 {n} 天 · 今天写了",
    "streak_todo": "连续 {n} 天 · 今天还没写",
    "ready_count": "{n} 条写完了没发",
    "oldest_days": "最老的躺了 {n} 天",
    "sparks_hot": "{n} 个想法还热着",
    "library": "{n} 条素材在库",
    "shelf_suffix": " · 搁板 {n}",
    "collapse": "⌄ 收起",

    # island one-liners
    "island_oldest": "有篇稿子躺 {n} 天了",
    "island_ready": "{n} 条写完了还没发",
    "island_streak": "连了 {n} 天，今天还没写",
    "island_sparks": "{n} 个想法还热着",
    "island_shelf": "搁板上有 {n} 条",
    "island_done": "今天的写完了",
    "island_clear": "都清了，歇会儿",

    # hover popup
    "peek_today_done": "今天写完了",
    "peek_today_todo": "今天还没写",
    "peek_distill": "蒸馏 Day {day} · 连续 {n} 天",
    "peek_hint": "点一下展开 · {key} 随手记",
    "peek_sig": "瞭望鸡",
}

EN = {
    "menu_header": "Lookout Chicken · watching what you owe",
    "menu_note": "Jot something down  {key}",
    "menu_clipboard": "Take the clipboard",
    "menu_widget_on": "Show the widget",
    "menu_widget_off": "Hide the widget",
    "menu_shelf": "Open shelf",
    "menu_shelf_n": "Open shelf  ({n} waiting)",
    "menu_open": "Open dashboard",
    "menu_ax": "⚠️ Enable shortcuts",
    "menu_quit": "Quit",
    "menu_pick_folder": "Choose notes folder…",
    "config_broken": "Your config could not be read, so these are sample numbers.\n{err}",
    "none_no_files": "No markdown in that folder \u00b7 tap to pick another",
    "none_no_states": "Notes found, but none marked finished \u00b7 tap for how",
    "pick_prompt": "Use this folder",
    "pick_message": "Pick a folder of markdown notes. It is only read, never written to.",
    "pick_done": "Read {library} notes, {ready} finished but unpublished.\n{path}",
    "pick_none": "No finished notes found in that folder.\nSee \u201cWhat it needs from your folder\u201d in the README.",
    "first_title": "Point it at your own notes",
    "first_message": ("These are sample numbers.\n\n"
                      "Pick a folder of markdown notes and it will start counting yours "
                      "instead \u2014 which pieces you finished and never published.\n\n"
                      "Read only, always."),
    "first_ok": "Choose folder",
    "first_skip": "Keep the demo",
    "menu_app_quit": "Quit Lookout Chicken",

    "edit_undo": "Undo",
    "edit_redo": "Redo",
    "edit_cut": "Cut",
    "edit_copy": "Copy",
    "edit_paste": "Paste",
    "edit_select_all": "Select All",

    "notify_title": "Lookout Chicken",
    "notify_hotkeys_live": "Shortcuts are live: {keys}",
    "notify_clip_empty": "Clipboard is empty",
    "notify_on_shelf": "Already on the shelf",
    "notify_shelved": "On the shelf",
    "notify_no_backend": "Can't reach the data source",
    "notify_widget_failed": "Widget won't open",
    "notify_ax_hint": "Tick this app in the list — it takes effect right away",

    "prompts": [
        "What just crossed your mind?",
        "One line is enough",
        "No need to finish the thought",
        "What made you stop?",
        "What's in your head now?",
        "Write it down and it won't escape",
        "Half a sentence counts",
    ],
    "capture_ok": "Got it, carry on",
    "capture_to": "Wrote {where}",
    "capture_fail": "Didn't save: {err}",
    "shelved_short": "on the shelf \u00b7 not in your notes yet",
    "already_shelved": "already on the shelf",

    "distill_day": "Day {day}",
    "streak_done": "{n} day streak · done today",
    "streak_todo": "{n} day streak · not yet today",
    "ready_count": "{n} finished, unpublished",
    "oldest_days": "Oldest has waited {n} days",
    "sparks_hot": "{n} ideas still warm",
    "library": "{n} in the library",
    "shelf_suffix": " · shelf {n}",
    "collapse": "⌄ Collapse",

    "island_oldest": "One draft has waited {n} days",
    "island_ready": "{n} finished but unpublished",
    "island_streak": "{n} days running, nothing today",
    "island_sparks": "{n} ideas still warm",
    "island_shelf": "{n} on the shelf",
    "island_done": "Today's is done",
    "island_clear": "All clear, take a break",

    "peek_today_done": "Done today",
    "peek_today_todo": "Not yet today",
    "peek_distill": "Day {day} · {n} day streak",
    "peek_hint": "Click to expand · {key} to jot",
    "peek_sig": "Lookout Chicken",
}

_TABLES = {"zh": ZH, "en": EN}
_active = ZH


def use(language):
    global _active
    _active = _TABLES.get(language, ZH)


def t(name, /, **kw):
    """Look up a string, falling back to Chinese then to the name itself, so
    a missing translation degrades to something visible rather than a crash.

    The lookup name is positional-only: templates legitimately contain a
    {key} field, and a normal parameter would collide with it.
    """
    val = _active.get(name, ZH.get(name, name))
    if isinstance(val, str) and kw:
        try:
            return val.format(**kw)
        except (KeyError, IndexError):
            return val
    return val


def prompts():
    return _active.get("prompts") or ZH["prompts"]
