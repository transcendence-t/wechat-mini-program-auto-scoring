# 自动评分脚本——适用于“打分测评”微信小程序

这是一个用于微信小程序教师互评场景的 PyAutoGUI 自动化脚本。脚本会自动激活名为“打分测评”的小程序窗口，在选人页面查找目标人员，进入评分页后点击第一个评分输入框，再通过 Tab 顺序依次填写全部评分，最后查找并点击“填写完毕”按钮。

## 主要能力

- 自动查找 `target_person.png` 对应的被评分人。
- 评分填写改为 Tab 顺序切换，减少第二、第三个评分漏填的问题。
- 启动时优先自动激活标题包含“打分测评”的窗口，脚本控制台可以放在后台。
- 找不到待评价人时，会在目标窗口内部滚动，不再依赖固定屏幕坐标。
- 提交按钮查找带重试，找不到时会向下滚动后继续查找。
- 支持通过环境变量调整评分值、评分数量和最大处理轮数。

## 使用方法

1. 打开微信小程序并停留在选人页面。
2. 保持微信小程序窗口可见，不要最小化。
3. 在本目录运行源码版：

```powershell
python 1.py
```

如果本机 `python` 是 Microsoft Store 应用别名，请换成实际安装的 Python 路径运行。

也可以从 [GitHub Releases](https://github.com/q634875942/wechat-mini-program-auto-scoring/releases/latest) 下载 Windows 版 `teacher-review-tool.exe` 并直接运行。若本地已打包，也可以运行：

```powershell
dist\教师互评工具.exe
```

检查 exe 内置资源是否正常，不执行点击/滚动：

```powershell
dist\教师互评工具.exe --check
```

## 可配置项

- `REVIEW_SCORE`：填写的评分值，默认 `20`。
- `REVIEW_SCORE_COUNT`：每个表单需要填写的评分数量，默认 `5`。
- `REVIEW_MAX_ROUNDS`：最多处理多少轮，默认 `0` 表示一直循环直到找不到目标或提交失败。
- `REVIEW_WINDOW_TITLE`：自动激活的小程序窗口标题，默认 `打分测评`。
- `REVIEW_SCROLL_METHOD`：滚动方式，默认 `auto`，会在滚轮和拖拽之间交替尝试；也可设为 `wheel`、`drag` 或 `pagedown`。

示例：

```powershell
$env:REVIEW_SCORE="18"
$env:REVIEW_SCORE_COUNT="5"
$env:REVIEW_MAX_ROUNDS="10"
python 1.py
```

## 注意事项

- 脚本仍依赖屏幕截图、鼠标和键盘事件，所以微信窗口不能最小化，也不能被其他窗口完全遮挡。
- 如果 Tab 顺序与表单实际顺序不一致，需要先手动确认第一个输入框获得焦点后，按 Tab 是否能依次切到后续评分框。
- 把鼠标移动到屏幕左上角可以触发 PyAutoGUI 的安全停止。
- exe 已内置 `target_person.png`、`input_box.png`、`submit_button.png` 三张模板图；如果小程序样式变化，需要重新替换模板并重新打包。

## 重新打包

```powershell
python -m PyInstaller --noconfirm --onefile --name "教师互评工具" --add-data "target_person.png;." --add-data "input_box.png;." --add-data "submit_button.png;." "1.py"
```
