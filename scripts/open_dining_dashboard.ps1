param(
    [string]$RobotIp,
    [int]$Port = 0,
    [switch]$SshSession,
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($RobotIp)) {
    $RobotIp = Read-Host '输入机器人当前 Wi-Fi IP'
}
$RobotIp = $RobotIp.Trim()
$parsedAddress = $null
if (-not [System.Net.IPAddress]::TryParse($RobotIp, [ref]$parsedAddress) -or
    $parsedAddress.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
    throw '请输入机器人信息页当前显示的有效 IPv4 地址。'
}
$sshExe = (Get-Command ssh.exe -CommandType Application).Source

function Test-FeedbackPage([int]$CandidatePort) {
    $response = $null
    $reader = $null
    try {
        $request = [System.Net.HttpWebRequest]::Create("http://127.0.0.1:${CandidatePort}/")
        $request.Proxy = $null
        $request.Timeout = 1000
        $response = $request.GetResponse()
        $reader = New-Object System.IO.StreamReader($response.GetResponseStream(), [System.Text.Encoding]::UTF8)
        $body = $reader.ReadToEnd()
        return $response.StatusCode -eq 200 -and $body.Contains('社区食堂反馈表')
    } catch {
        return $false
    } finally {
        if ($reader) { $reader.Dispose() }
        if ($response) { $response.Dispose() }
    }
}

if ($Port -eq 0) {
    foreach ($candidate in 18765..18775) {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $candidate)
        try {
            $listener.Start()
            $Port = $candidate
            break
        } catch {
            # Leave existing programs alone; try another local port.
        } finally {
            $listener.Stop()
        }
    }
}
if ($Port -lt 1024 -or $Port -gt 65535) { throw '没有可用的网页端口。' }
$url = "http://127.0.0.1:${Port}/"
$remoteCommand = "cd /home/agi/eldercare-x2/eldercare_x2 && python3 -u feedback_dashboard.py --records data/dining_feedback_stage4_test.jsonl --port $Port"

if ($CheckOnly) {
    [pscustomobject]@{RobotIp=$RobotIp; BrowserUrl=$url; Records='data/dining_feedback_stage4_test.jsonl'; RemoteCommand=$remoteCommand}
    return
}

if ($SshSession) {
    $Host.UI.RawUI.WindowTitle = '食堂反馈表 SSH：请在此输入密码并保持窗口打开'
    Write-Host "正在连接机器人 $RobotIp；密码输入时不显示字符，这是正常的。"
    Write-Host '这个窗口负责网页和转发，请保持打开。结束时按 Ctrl+C。'
    & $sshExe -t -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 `
        -L "127.0.0.1:${Port}:127.0.0.1:${Port}" "agi@${RobotIp}" $remoteCommand
    if ($LASTEXITCODE -ne 0) {
        Write-Host "SSH/网页服务退出，返回码 $LASTEXITCODE。请保留上面的报错发给开发者。" -ForegroundColor Red
        Read-Host '按回车关闭这个窗口'
    }
    return
}

Write-Host "将打开一个 SSH 窗口。请在新窗口确认主机信息并自行输入密码。"
Write-Host "网页准备好后自动打开：$url"
$process = Start-Process -FilePath 'powershell.exe' -WindowStyle Normal -PassThru -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'),
    '-SshSession', '-RobotIp', $RobotIp, '-Port', $Port
)
for ($attempt = 0; $attempt -lt 90; $attempt++) {
    if (Test-FeedbackPage $Port) {
        Start-Process $url
        Write-Host "已连通食堂反馈表：$url" -ForegroundColor Green
        Write-Host '请保留 SSH 网页窗口，浏览器刷新即可看到新记录。'
        return
    }
    if ($process.HasExited) { throw 'SSH窗口已经退出，网页未启动。请查看窗口里的错误。' }
    Start-Sleep -Seconds 1
}
Write-Host '网页尚未连通。请查看新开的 SSH 窗口：是否还在等待密码、或提示端口/文件错误。' -ForegroundColor Yellow
Write-Host "连接成功后也可以手动访问：$url"
