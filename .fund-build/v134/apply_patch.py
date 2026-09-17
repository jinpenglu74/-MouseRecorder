from pathlib import Path
import base64, hashlib
root=Path('.')

def rw(path, old, new):
    p=root/path
    s=p.read_text(encoding='utf-8')
    if old not in s:
        raise SystemExit(f'expected pattern missing: {path}: {old[:80]!r}')
    p.write_text(s.replace(old,new),encoding='utf-8',newline='\n')

# version / packaging
rw('.github/workflows/windows-installer.yml','name: FundForecast-v1.3.3-Windows','name: FundForecast-v1.3.4-Windows')
rw('FundForecastApp.spec','    entitlements_file=None,\n)','    entitlements_file=None,\n    icon=\'assets/app.ico\',\n)')

p=root/'README.md'; s=p.read_text(encoding='utf-8')
anchor='面向普通投资者的 Windows 基金量化研判工具。支持按基金名称、代码、拼音简称批量添加基金，保存关注列表，并基于可取得的公开历史净值展示概率研判。数据不足、过期或置信度不足时会明确“暂不预测”。\n'
section='''\n\n## v1.3.4「软件图标接入版」\n\n- 全面接入基金预测专属图标：Windows 主程序 EXE、任务栏/窗口、安装器、桌面快捷方式、开始菜单与卸载入口统一使用同一品牌图标。\n- 顶部品牌区将原 M01 文字标识替换为图形 Logo，保留基金预测标题与版本号。\n- Windows 图标资源包含 16px 至 256px 多尺寸帧，兼顾资源管理器、快捷方式和高 DPI 显示。\n'''
if '## v1.3.4「软件图标接入版」' not in s:
    if anchor not in s: raise SystemExit('README anchor missing')
    s=s.replace(anchor,anchor+section,1)
s=s.replace('基金预测-安装程序-v1.3.3.exe','基金预测-安装程序-v1.3.4.exe')
p.write_text(s,encoding='utf-8',newline='\n')

p=root/'packaging/FundForecastApp.iss'; s=p.read_text(encoding='utf-8')
s=s.replace('#define MyAppVersion "1.3.3"','#define MyAppVersion "1.3.4"')
s=s.replace('WizardStyle=modern\n','WizardStyle=modern\nSetupIconFile=..\\assets\\app.ico\n',1)
s=s.replace('Name: "{autodesktop}\\基金预测"; Filename: "{app}\\{#MyAppExeName}"; WorkingDir: "{app}"','Name: "{autodesktop}\\基金预测"; Filename: "{app}\\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\\{#MyAppExeName}"')
s=s.replace('Name: "{userprograms}\\基金预测\\基金预测"; Filename: "{app}\\{#MyAppExeName}"; WorkingDir: "{app}"','Name: "{userprograms}\\基金预测\\基金预测"; Filename: "{app}\\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\\{#MyAppExeName}"')
s=s.replace('Name: "{userprograms}\\基金预测\\卸载基金预测"; Filename: "{uninstallexe}"','Name: "{userprograms}\\基金预测\\卸载基金预测"; Filename: "{uninstallexe}"; IconFilename: "{app}\\{#MyAppExeName}"')
p.write_text(s,encoding='utf-8',newline='\n')

rw('packaging/build-release.ps1','@("src", "tests", "packaging", "docs", ".github", "pyproject.toml", "README.md", "FundForecastApp.spec")','@("src", "tests", "packaging", "docs", ".github", "assets", "pyproject.toml", "README.md", "FundForecastApp.spec")')

p=root/'packaging/test-installed.ps1'; s=p.read_text(encoding='utf-8')
s=s.replace('$startMenuShortcut = Join-Path $startMenuDir "基金预测.lnk"\n','$startMenuShortcut = Join-Path $startMenuDir "基金预测.lnk"\n$uninstallShortcut = Join-Path $startMenuDir "卸载基金预测.lnk"\n',1)
needle='''if (-not (Test-Path $startMenuShortcut)) { throw "Start Menu shortcut missing: $startMenuShortcut" }\n'''
block='''if (-not (Test-Path $startMenuShortcut)) { throw "Start Menu shortcut missing: $startMenuShortcut" }\nif (-not (Test-Path $uninstallShortcut)) { throw "Uninstall shortcut missing: $uninstallShortcut" }\n\n$shell = New-Object -ComObject WScript.Shell\nforeach ($shortcutPath in @($desktopShortcut, $startMenuShortcut, $uninstallShortcut)) {\n    $shortcut = $shell.CreateShortcut($shortcutPath)\n    if (-not $shortcut.IconLocation -or $shortcut.IconLocation -notmatch 'FundForecastApp\\.exe') {\n        throw "Shortcut icon is not bound to FundForecastApp.exe: $shortcutPath -> $($shortcut.IconLocation)"\n    }\n}\n'''
if block not in s:
    if needle not in s: raise SystemExit('test-installed anchor missing')
    s=s.replace(needle,block,1)
p.write_text(s,encoding='utf-8',newline='\n')

rw('pyproject.toml','fund_platform = ["static/*.html", "static/*.css", "static/*.js", "static/*.mjs"]','fund_platform = ["static/*.html", "static/*.css", "static/*.js", "static/*.mjs", "static/*.png"]')
rw('src/fund_platform/__init__.py','__version__ = "1.3.3"','__version__ = "1.3.4"')

p=root/'src/fund_platform/static/app.css'; s=p.read_text(encoding='utf-8')
old='.brand{display:flex;align-items:center}.brand h1'
new='.brand{display:flex;align-items:center}.brand-logo{width:40px;height:40px;margin-right:9px;border-radius:10px;object-fit:cover;box-shadow:0 0 0 1px #298de244,0 4px 14px #1688ea28}.brand h1'
if old not in s: raise SystemExit('CSS anchor missing')
s=s.replace(old,new,1); p.write_text(s,encoding='utf-8',newline='\n')

p=root/'src/fund_platform/static/index.html'; s=p.read_text(encoding='utf-8')
old='<div class="brand"><span class="module-id">M01</span><div><h1>基金预测</h1>'
new='<div class="brand"><img class="brand-logo" src="/static/brand-logo.png" alt="基金预测"><div><h1>基金预测</h1>'
if old not in s: raise SystemExit('index anchor missing')
s=s.replace(old,new,1); p.write_text(s,encoding='utf-8',newline='\n')

p=root/'tests/e2e/test_api.py'; s=p.read_text(encoding='utf-8')
s=s.replace('    assert "M01" in response.text and "M06" in response.text\n','    assert "M06" in response.text\n    assert \'class="brand-logo"\' in response.text\n',1)
s=s.replace('基金预测 v1.3.3','基金预测 v1.3.4').replace('src="/static/app.js?v=1.3.3"','src="/static/app.js?v=1.3.4"')
p.write_text(s,encoding='utf-8',newline='\n')

for path in ['tests/test_health.py','tests/test_version.py']:
    p=root/path; s=p.read_text(encoding='utf-8').replace('1.3.3','1.3.4'); p.write_text(s,encoding='utf-8',newline='\n')

release='''# v1.3.4 软件图标接入版\n\n- 新增基金预测专属 Windows 多尺寸图标。\n- 主程序 EXE、任务栏/窗口、Inno 安装器、桌面/开始菜单/卸载快捷方式统一品牌图标。\n- 顶部品牌区使用新 Logo。\n- 不修改预测模型、数据同步、预测档案或运行日志业务逻辑。\n'''
(root/'docs/v1.3.4-release-notes.md').write_text(release,encoding='utf-8',newline='\n')

brand_test='''from pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\n\n\ndef test_brand_icon_assets_exist_and_are_packaged() -> None:\n    assert (ROOT / "assets" / "app.ico").is_file()\n    assert (ROOT / "src" / "fund_platform" / "static" / "brand-logo.png").is_file()\n    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")\n    assert '"static/*.png"' in pyproject\n    release_script = (ROOT / "packaging" / "build-release.ps1").read_text(encoding="utf-8")\n    assert '"assets"' in release_script\n\n\ndef test_pyinstaller_embeds_application_icon() -> None:\n    spec = (ROOT / "FundForecastApp.spec").read_text(encoding="utf-8")\n    assert "icon='assets/app.ico'" in spec\n\n\ndef test_inno_uses_application_icon_for_setup_and_shortcuts() -> None:\n    iss = (ROOT / "packaging" / "FundForecastApp.iss").read_text(encoding="utf-8")\n    assert "SetupIconFile=" in iss\n    assert "assets\\\\app.ico" in iss\n    assert 'IconFilename: "{app}\\\\{#MyAppExeName}"' in iss\n\n\ndef test_dashboard_uses_brand_logo_in_topbar() -> None:\n    html = (ROOT / "src" / "fund_platform" / "static" / "index.html").read_text(encoding="utf-8")\n    css = (ROOT / "src" / "fund_platform" / "static" / "app.css").read_text(encoding="utf-8")\n    assert 'src="/static/brand-logo.png"' in html\n    assert 'class="brand-logo"' in html\n    assert ".brand-logo" in css\n\n\ndef test_windows_smoke_checks_installed_shortcut_icons() -> None:\n    smoke = (ROOT / "packaging" / "test-installed.ps1").read_text(encoding="utf-8")\n    assert "IconLocation" in smoke\n    assert "卸载基金预测.lnk" in smoke\n    assert (ROOT / "packaging" / "test-icon-binaries.ps1").is_file()\n'''
(root/'tests/test_brand_icon.py').write_text(brand_test,encoding='utf-8',newline='\n')

icon_ps = r'''param(
    [Parameter(Mandatory = $true)]
    [string]$ExecutablePath,
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedIconPath
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

function Get-IconBitmap([System.Drawing.Icon]$Icon) {
    $source = $Icon.ToBitmap()
    try {
        $target = New-Object System.Drawing.Bitmap 32, 32
        $graphics = [System.Drawing.Graphics]::FromImage($target)
        try {
            $graphics.Clear([System.Drawing.Color]::Transparent)
            $graphics.DrawImage($source, 0, 0, 32, 32)
        }
        finally {
            $graphics.Dispose()
        }
        return $target
    }
    finally {
        $source.Dispose()
    }
}

function Assert-IconMatches([string]$Label, [System.Drawing.Icon]$Expected, [System.Drawing.Icon]$Actual) {
    $expectedBitmap = Get-IconBitmap $Expected
    $actualBitmap = Get-IconBitmap $Actual
    try {
        $sum = 0.0
        $count = 0
        for ($y = 0; $y -lt 32; $y++) {
            for ($x = 0; $x -lt 32; $x++) {
                $a = $expectedBitmap.GetPixel($x, $y)
                $b = $actualBitmap.GetPixel($x, $y)
                $sum += [Math]::Abs([int]$a.R - [int]$b.R)
                $sum += [Math]::Abs([int]$a.G - [int]$b.G)
                $sum += [Math]::Abs([int]$a.B - [int]$b.B)
                $count += 3
            }
        }
        $meanDifference = $sum / $count
        if ($meanDifference -gt 18.0) {
            throw "$Label icon differs from expected app icon (mean RGB difference $meanDifference)"
        }
        Write-Host "$Label icon mean RGB difference: $meanDifference"
    }
    finally {
        $expectedBitmap.Dispose()
        $actualBitmap.Dispose()
    }
}

foreach ($path in @($ExecutablePath, $InstallerPath, $ExpectedIconPath)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing icon validation input: $path" }
}

$expected = [System.Drawing.Icon]::new($ExpectedIconPath, [System.Drawing.Size]::new(32, 32))
$exeIcon = [System.Drawing.Icon]::ExtractAssociatedIcon((Resolve-Path $ExecutablePath).Path)
$setupIcon = [System.Drawing.Icon]::ExtractAssociatedIcon((Resolve-Path $InstallerPath).Path)
try {
    if ($null -eq $exeIcon) { throw "Executable has no associated icon" }
    if ($null -eq $setupIcon) { throw "Installer has no associated icon" }
    Assert-IconMatches "Application EXE" $expected $exeIcon
    Assert-IconMatches "Installer EXE" $expected $setupIcon
}
finally {
    $expected.Dispose()
    if ($exeIcon) { $exeIcon.Dispose() }
    if ($setupIcon) { $setupIcon.Dispose() }
}

Write-Host "WINDOWS_BINARY_ICONS_OK"
'''
(root/'packaging/test-icon-binaries.ps1').write_text(icon_ps,encoding='utf-8',newline='\n')
