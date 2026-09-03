Set ws = CreateObject("WScript.Shell")
ws.CurrentDirectory = "C:\xsmallappliance"
ws.Run """ & "C:\Users\Administrator\AppData\Roaming\Accio\pre-install\ab1f8a6ee51b\python\python.exe" & "" -m http.server 8080 --directory C:\xsmallappliance"", 0, False
