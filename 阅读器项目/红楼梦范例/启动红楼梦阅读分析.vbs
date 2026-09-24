' ============================================================
'  红楼梦阅读分析一体化 — 无窗口启动器
'  用法：双击本文件即可启动
'  功能：
'    1. 检查 app.exe 是否存在
'    2. 检查 vite 是否已运行（端口 1420）
'    3. 未运行则静默启动 vite dev server
'    4. 等待 vite 就绪（最多 30 秒）
'    5. 启动应用窗口
'    6. 应用关闭后自动清理 vite（仅当本启动器启动了它）
'  优势：无黑色命令行窗口，体验和正规桌面软件一致
' ============================================================
Option Explicit

Dim objShell, objFSO
Dim projectDir, appDir, appExe, viteBat, logFile
Dim port, startedVite, tries, ready

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 项目根目录 = 脚本所在目录
projectDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
appDir = projectDir & "\app"
appExe = appDir & "\src-tauri\target\debug\app.exe"
viteBat = appDir & "\start_vite.bat"
logFile = appDir & "\.temp\launcher_vbs.log"
port = "1420"
startedVite = False

' 确保日志目录存在
If Not objFSO.FolderExists(appDir & "\.temp") Then
    objFSO.CreateFolder appDir & "\.temp"
End If

WriteLog "=== 启动红楼梦阅读分析 ==="
WriteLog "项目目录: " & projectDir

' ---- 检查 app.exe ----
If Not objFSO.FileExists(appExe) Then
    MsgBox "找不到 app.exe！" & vbCrLf & vbCrLf & _
           "请先构建应用：" & vbCrLf & _
           "  1. 打开命令行" & vbCrLf & _
           "  2. cd /d """ & appDir & """" & vbCrLf & _
           "  3. pnpm tauri dev", _
           16, "启动失败"
    WriteLog "ERROR: app.exe 不存在: " & appExe
    WScript.Quit 1
End If

' ---- 检查 vite 是否已运行 ----
ready = CheckPort(port)
If ready Then
    WriteLog "vite 已在运行，直接启动应用"
Else
    WriteLog "vite 未运行，正在启动..."
    ' 静默启动 vite（最小化，不显示窗口）
    objShell.Run """" & viteBat & """", 2, False
    startedVite = True
    
    ' 等待 vite 就绪（最多 30 秒）
    tries = 0
    Do While tries < 30
        WScript.Sleep 1000
        tries = tries + 1
        If CheckPort(port) Then
            WriteLog "vite 就绪，耗时 " & tries & " 秒"
            Exit Do
        End If
    Loop
    
    If Not CheckPort(port) Then
        WriteLog "WARNING: vite 超时（30秒），继续尝试启动"
    End If
End If

' ---- 启动应用（等待退出） ----
WriteLog "启动应用: " & appExe
objShell.Run """" & appExe & """", 1, True
WriteLog "应用已退出"

' ---- 清理 vite ----
If startedVite Then
    WriteLog "清理 vite 进程..."
    On Error Resume Next
    objShell.Run "taskkill /FI ""WINDOWTITLE eq honglou-vite*"" /T /F", 0, True
    On Error GoTo 0
    WriteLog "已清理"
End If

WriteLog "=== 启动器退出 ==="

' ============================================================
'  辅助函数
' ============================================================

Function WriteLog(msg)
    Dim fso, f, ts
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.OpenTextFile(logFile, 8, True) ' 8 = 追加
    ts.WriteLine Now & "  " & msg
    ts.Close
End Function

Function CheckPort(portNum)
    ' 通过 netstat 检查端口是否在监听
    Dim exec, line, output
    Set exec = objShell.Exec("netstat -ano")
    output = exec.StdOut.ReadAll
    
    ' 查找 LISTENING 状态的指定端口
    CheckPort = InStr(output, ":" & portNum & " ") > 0 And _
                InStr(output, "LISTENING") > 0
    
    ' 更精确的检查
    Dim lines, i
    lines = Split(output, vbCrLf)
    CheckPort = False
    For i = 0 To UBound(lines)
        line = lines(i)
        If InStr(line, ":" & portNum & " ") > 0 And InStr(line, "LISTENING") > 0 Then
            CheckPort = True
            Exit For
        End If
    Next
End Function
