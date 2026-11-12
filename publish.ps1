# 声搭 Demo 一键发布到 GitHub Pages
# 用法（先开代理/VPN，确保能访问 github.com）：
#   pwsh -File "D:\DeepSeek harness\github\shengda\publish.ps1" -User 你的GitHub用户名
# 可选：-Repo shengda-demo（仓库名，默认）  -Name "Yao Hanqi"  -Email "you@example.com"
param(
  [Parameter(Mandatory = $true)][string]$User,
  [string]$Repo = "shengda-demo",
  [string]$Branch = "main",
  [string]$Name = "Yao Hanqi",
  [string]$Email = ""
)
$ErrorActionPreference = "Stop"
if (-not $Email) { $Email = "$User@users.noreply.github.com" }
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $dir

Write-Host "== 1/4 检查网络 ==" -ForegroundColor Cyan
$ok = $false
try { $ok = Test-NetConnection -ComputerName github.com -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue } catch { $ok = $false }
if (-not $ok) {
  Write-Host "[x] 连不上 github.com:443。" -ForegroundColor Red
  Write-Host "    这台机器当前所有外网 HTTPS 都被重置（github / gitee / bing 均失败，未配置代理）。"
  Write-Host "    请先打开代理或 VPN，再重新运行本脚本。"
  Pop-Location; exit 1
}

Write-Host "== 2/4 初始化本地仓库 ==" -ForegroundColor Cyan
if (-not (Test-Path ".git")) { & git init -b $Branch | Out-Null }
& git config user.name $Name
& git config user.email $Email
& git add -A
& git commit -m "Add 声搭 AI短视频配乐助手 demo" 2>$null | Out-Null
$remote = "https://github.com/$User/$Repo.git"
$remotes = @(& git remote)
if ($remotes -contains "origin") { & git remote set-url origin $remote } else { & git remote add origin $remote }
& git branch -M $Branch

Write-Host "== 3/4 推送到 $remote ==" -ForegroundColor Cyan
& git push -u origin $Branch
if ($LASTEXITCODE -ne 0) {
  Write-Host "[x] push 失败。请先在 GitHub 网页新建一个空仓库：$User/$Repo（不要勾选 README/.gitignore），然后重跑本脚本。" -ForegroundColor Red
  Pop-Location; exit 1
}

$url = "https://$User.github.io/$Repo/"
Write-Host "== 4/4 等待 Pages 构建：$url ==" -ForegroundColor Cyan
Write-Host "    首次需要在仓库 Settings → Pages → Source 选 Deploy from a branch → $Branch → / (root) → Save" -ForegroundColor Yellow
for ($i = 1; $i -le 40; $i++) {
  Start-Sleep -Seconds 6
  try {
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -eq 200) {
      Write-Host "[ok] 已上线：$url" -ForegroundColor Green
      Write-Host "     把这个链接写进 PDF 第 2 页 Demo 一行和邮件正文即可。" -ForegroundColor Green
      Pop-Location; exit 0
    }
  } catch { }
  Write-Host "     ...第 $i 次检查（Pages 首次构建一般 30—120 秒）"
}
Write-Host "[!] 3 分钟内没返回 200。稍后手动打开：$url" -ForegroundColor Yellow
Pop-Location
