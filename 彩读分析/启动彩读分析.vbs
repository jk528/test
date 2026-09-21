' ============================================================
'  ColorTxt Analysis launcher (彩读分析一键启动)
'  Mirrors the 红楼梦阅读分析 launcher structure:
'    1. checks the ColorTxt project exists
'    2. checks whether vite is already listening (port 5173)
'    3. otherwise starts `npm run dev` in a minimized window
'    4. waits until port 5173 is listening (max ~60s)
'    5. waits until an electron process appears (max ~30s)
'  Double-click this file (or the desktop shortcut) to run.
'  Encoding: pure ASCII (English only) to avoid codepage issues.
' ============================================================
Option Explicit

Dim objShell, objFSO
Dim baseDir, projectDir, viteBat, logFile, port
Dim startedVite, tries, ready, electronSeen

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' baseDir = folder of this script (彩读分析)
baseDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
' ColorTxt project lives at <彩读分析>\.temp\ColorTxt
projectDir = baseDir & "\.temp\ColorTxt"
viteBat = baseDir & "\start_colortxt.bat"
logFile = baseDir & "\.temp\colortxt_launcher.log"
port = "5173"
startedVite = False

' ---- sanity checks ----
If Not objFSO.FolderExists(projectDir) Then
    MsgBox "ColorTxt project not found:" & vbCrLf & projectDir, 16, "Launch failed"
    WScript.Quit 1
End If
If Not objFSO.FileExists(projectDir & "\node_modules\.bin\electron.cmd") Then
    MsgBox "Dependencies missing. Run `npm install` in:" & vbCrLf & projectDir, 16, "Launch failed"
    WScript.Quit 1
End If

If Not objFSO.FolderExists(baseDir & "\.temp") Then
    objFSO.CreateFolder baseDir & "\.temp"
End If
WriteLog "=== ColorTxt Analysis launcher ==="
WriteLog "Project: " & projectDir

' ---- 1) is vite already listening? ----
ready = CheckPort(port)
If ready Then
    WriteLog "vite already listening on port " & port & " - reuse it"
Else
    WriteLog "vite not running - starting dev server..."
    objShell.Run """" & viteBat & """", 2, False   ' 2 = minimized
    startedVite = True

    ' ---- 2) wait for port 5173 (max 60s) ----
    tries = 0
    Do While tries < 60
        WScript.Sleep 1000
        tries = tries + 1
        If CheckPort(port) Then
            WriteLog "vite listening after " & tries & "s"
            Exit Do
        End If
    Loop
    If Not CheckPort(port) Then
        WriteLog "WARNING: vite not listening after 60s, continuing..."
    End If
End If

' ---- 3) wait for electron window process (max 30s) ----
electronSeen = False
tries = 0
Do While tries < 30
    If IsElectronRunning() Then
        electronSeen = True
        WriteLog "electron process detected after " & tries & "s"
        Exit Do
    End If
    WScript.Sleep 1000
    tries = tries + 1
Loop
If Not electronSeen Then
    WriteLog "WARNING: no electron process detected within 30s"
    MsgBox "ColorTxt dev server started, but the app window did not appear." & vbCrLf & _
           "Check the minimized window / log: " & vbCrLf & logFile, 48, "ColorTxt Analysis"
End If

WriteLog "=== launcher finished ==="

' ============================================================
'  helpers
' ============================================================
Function WriteLog(msg)
    Dim fso, ts
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.OpenTextFile(logFile, 8, True)   ' 8 = append
    ts.WriteLine Now & "  " & msg
    ts.Close
End Function

Function CheckPort(portNum)
    Dim exec, output, lines, i, line
    Set exec = objShell.Exec("netstat -ano")
    output = exec.StdOut.ReadAll
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

Function IsElectronRunning()
    Dim exec, output
    Set exec = objShell.Exec("tasklist /FI ""IMAGENAME eq electron.exe""")
    output = exec.StdOut.ReadAll
    IsElectronRunning = InStr(output, "electron.exe") > 0
End Function
