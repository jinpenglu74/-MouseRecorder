#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply the MixCut Windows v0.16.3 top runtime-log viewer patch.

This patch intentionally changes ONLY:
  - src/MixCut/Views/MainWindow.xaml (adds one top runtime-log entry)
  - src/MixCut/Views/MainWindow.xaml.cs (opens the log window)
  - src/MixCut/Views/RuntimeLogWindow.cs (new window)

No business workflow, DB schema, prompts, AI parameters, export settings, or existing pages are changed.
"""
from pathlib import Path
import sys

MARKER = "MixCut Runtime Log Center Patch / official windows v0.16.3 base"

RUNTIME_LOG_CS = r'''using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using MixCut.Infrastructure;
using MixCut.Services.AI;
using MixCut.Utilities;
using Serilog;

namespace MixCut.Views;

/// <summary>
/// 顶部「运行日志」对应的实时日志中心。
/// 只读取应用现有 Serilog 日志，不改变业务流程；导出复用官方 DiagnosticExport，
/// 因此用户发回来的诊断包与设置 → 关于 → 导出诊断日志完全同源。
/// </summary>
public sealed class RuntimeLogWindow : Window
{
    private static readonly Regex HeaderRegex = new(
        @"^(?<time>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\[(?<level>[A-Z]{3})\]",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private readonly DispatcherTimer _timer;
    private readonly TextBox _logBox;
    private readonly TextBox _searchBox;
    private readonly ComboBox _levelBox;
    private readonly CheckBox _autoRefreshBox;
    private readonly TextBlock _statusText;
    private readonly TextBlock _pathText;
    private bool _refreshing;
    private DateTime _lastKnownWriteUtc = DateTime.MinValue;
    private long _lastKnownLength = -1;

    private static readonly Brush BorderBrushColor = new SolidColorBrush(Color.FromRgb(0xE0, 0xE0, 0xE2));
    private static readonly Brush MutedBrush = new SolidColorBrush(Color.FromRgb(0x77, 0x77, 0x7B));
    private static readonly Brush AccentBrush = new SolidColorBrush(Color.FromRgb(0x1D, 0x6B, 0xE5));
    private static readonly Brush ToolbarBrush = new SolidColorBrush(Color.FromRgb(0xF8, 0xF8, 0xFA));

    public RuntimeLogWindow()
    {
        Title = "运行日志 - MixCut";
        Width = 1100;
        Height = 720;
        MinWidth = 820;
        MinHeight = 520;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        Background = Brushes.White;
        try { Icon = System.Windows.Application.Current.MainWindow?.Icon; } catch { }

        var root = new DockPanel();
        Content = root;

        var header = new Grid { Height = 54, Background = Brushes.White, Margin = new Thickness(0) };
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        var title = new TextBlock
        {
            Text = "运行日志", FontSize = 16, FontWeight = FontWeights.SemiBold,
            Foreground = new SolidColorBrush(Color.FromRgb(0x1F, 0x1F, 0x23)),
            VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(16, 0, 12, 0),
        };
        _pathText = new TextBlock
        {
            Text = AppPaths.LogDirectory, FontSize = 11, Foreground = MutedBrush,
            TextTrimming = TextTrimming.CharacterEllipsis, VerticalAlignment = VerticalAlignment.Center,
            HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(12, 0, 16, 0),
        };
        _pathText.ToolTip = AppPaths.LogDirectory;
        Grid.SetColumn(title, 0); Grid.SetColumn(_pathText, 1);
        header.Children.Add(title); header.Children.Add(_pathText);
        DockPanel.SetDock(header, Dock.Top); root.Children.Add(header);

        var toolbarBorder = new Border
        {
            Background = ToolbarBrush, BorderBrush = BorderBrushColor,
            BorderThickness = new Thickness(0, 1, 0, 1), Padding = new Thickness(12, 8, 12, 8),
        };
        var toolbar = new DockPanel { LastChildFill = false };
        toolbarBorder.Child = toolbar;

        var left = new StackPanel { Orientation = Orientation.Horizontal };
        _levelBox = new ComboBox
        {
            Width = 112, Height = 28, Margin = new Thickness(0, 0, 8, 0),
            ItemsSource = new[] { "全部级别", "错误", "警告", "信息", "调试" }, SelectedIndex = 0,
        };
        _searchBox = new TextBox
        {
            Width = 270, Height = 28, Padding = new Thickness(7, 4, 7, 4),
            VerticalContentAlignment = VerticalAlignment.Center,
            ToolTip = "搜索模块名、错误码、文件名、任务 ID、FFmpeg/AI 关键字", Tag = "搜索日志",
        };
        _autoRefreshBox = new CheckBox
        {
            Content = "自动刷新", IsChecked = true, VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(10, 0, 0, 0),
        };
        left.Children.Add(_levelBox); left.Children.Add(_searchBox); left.Children.Add(_autoRefreshBox);
        DockPanel.SetDock(left, Dock.Left); toolbar.Children.Add(left);

        var right = new StackPanel { Orientation = Orientation.Horizontal };
        right.Children.Add(MakeButton("刷新", OnRefreshClick));
        right.Children.Add(MakeButton("复制当前", OnCopyClick));
        right.Children.Add(MakeButton("导出诊断包", OnExportClick, primary: true));
        right.Children.Add(MakeButton("打开日志目录", OnOpenFolderClick));
        DockPanel.SetDock(right, Dock.Right); toolbar.Children.Add(right);
        DockPanel.SetDock(toolbarBorder, Dock.Top); root.Children.Add(toolbarBorder);

        var statusBorder = new Border
        {
            Height = 32, Background = ToolbarBrush, BorderBrush = BorderBrushColor,
            BorderThickness = new Thickness(0, 1, 0, 0), Padding = new Thickness(12, 0, 12, 0),
        };
        _statusText = new TextBlock
        {
            Text = "正在读取日志…", FontSize = 11, Foreground = MutedBrush,
            VerticalAlignment = VerticalAlignment.Center,
        };
        statusBorder.Child = _statusText; DockPanel.SetDock(statusBorder, Dock.Bottom); root.Children.Add(statusBorder);

        _logBox = new TextBox
        {
            IsReadOnly = true, AcceptsReturn = true, AcceptsTab = true, TextWrapping = TextWrapping.NoWrap,
            FontFamily = new FontFamily("Consolas"), FontSize = 12,
            Foreground = new SolidColorBrush(Color.FromRgb(0x22, 0x22, 0x26)), Background = Brushes.White,
            BorderThickness = new Thickness(0), Padding = new Thickness(12),
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Auto, IsUndoEnabled = false,
        };
        root.Children.Add(_logBox);

        _levelBox.SelectionChanged += (_, _) => _ = RefreshAsync(force: true, scrollToEnd: false);
        _searchBox.TextChanged += (_, _) => _ = RefreshAsync(force: true, scrollToEnd: false);
        _timer = new DispatcherTimer(DispatcherPriority.Background) { Interval = TimeSpan.FromSeconds(1) };
        _timer.Tick += async (_, _) => { if (_autoRefreshBox.IsChecked == true) await RefreshAsync(false, true); };
        _timer.Start();
        Loaded += async (_, _) => { Log.Information("[RuntimeLog] 打开顶部运行日志中心"); await RefreshAsync(true, true); };
        Closed += (_, _) => { _timer.Stop(); Log.Information("[RuntimeLog] 关闭顶部运行日志中心"); };
    }

    private Button MakeButton(string text, RoutedEventHandler handler, bool primary = false)
    {
        var button = new Button
        {
            Content = text, Height = 28, Padding = new Thickness(10, 3, 10, 3), Margin = new Thickness(8, 0, 0, 0),
            Cursor = System.Windows.Input.Cursors.Hand, FontSize = 11,
            Background = primary ? AccentBrush : Brushes.White,
            Foreground = primary ? Brushes.White : new SolidColorBrush(Color.FromRgb(0x33, 0x33, 0x37)),
            BorderBrush = primary ? AccentBrush : BorderBrushColor, BorderThickness = new Thickness(1),
        };
        button.Click += handler; return button;
    }

    private async void OnRefreshClick(object sender, RoutedEventArgs e) => await RefreshAsync(true, true);
    private void OnCopyClick(object sender, RoutedEventArgs e)
    {
        try { Clipboard.SetText(_logBox.Text ?? string.Empty); _statusText.Text = $"已复制当前筛选后的日志 · {DateTime.Now:HH:mm:ss}"; }
        catch (Exception ex) { MessageBox.Show(this, $"复制失败：{ex.Message}", "运行日志", MessageBoxButton.OK, MessageBoxImage.Warning); }
    }
    private async void OnExportClick(object sender, RoutedEventArgs e)
    {
        try
        {
            _statusText.Text = "正在生成诊断包…";
            var path = await DiagnosticExport.ExportAsync();
            Log.Information("[RuntimeLog] 已从日志中心导出诊断包: {Path}", path);
            _statusText.Text = $"诊断包已生成：{path}";
            MessageBox.Show(this, $"诊断包已生成：\n{path}\n\n把这个 zip 文件发给开发者即可定位问题。", "导出诊断包", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            Log.Error(ex, "[RuntimeLog] 导出诊断包失败");
            MessageBox.Show(this, $"导出失败：{ex.Message}", "运行日志", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }
    private void OnOpenFolderClick(object sender, RoutedEventArgs e)
    {
        try
        {
            Directory.CreateDirectory(AppPaths.LogDirectory);
            Process.Start(new ProcessStartInfo { FileName = "explorer.exe", Arguments = $"\"{AppPaths.LogDirectory}\"", UseShellExecute = true });
        }
        catch (Exception ex) { MessageBox.Show(this, $"打开日志目录失败：{ex.Message}", "运行日志", MessageBoxButton.OK, MessageBoxImage.Warning); }
    }

    private async Task RefreshAsync(bool force, bool scrollToEnd)
    {
        if (_refreshing) return;
        _refreshing = true;
        try
        {
            Directory.CreateDirectory(AppPaths.LogDirectory);
            var latest = new DirectoryInfo(AppPaths.LogDirectory).GetFiles("mixcut-*.log").OrderByDescending(f => f.LastWriteTimeUtc).FirstOrDefault();
            if (latest is null) { _logBox.Text = "当前还没有生成运行日志。"; _statusText.Text = $"日志目录：{AppPaths.LogDirectory}"; return; }
            if (!force && latest.LastWriteTimeUtc == _lastKnownWriteUtc && latest.Length == _lastKnownLength) return;
            _lastKnownWriteUtc = latest.LastWriteTimeUtc; _lastKnownLength = latest.Length;
            var selectedLevel = _levelBox.SelectedIndex;
            var keyword = _searchBox.Text?.Trim() ?? string.Empty;
            var snapshot = await Task.Run(() => BuildSnapshot(latest.FullName, selectedLevel, keyword));
            var wasNearBottom = IsNearBottom();
            _logBox.Text = snapshot.Text;
            _statusText.Text = $"{latest.Name} · 原始 {snapshot.TotalEvents:N0} 条 · 当前显示 {snapshot.VisibleEvents:N0} 条 · ERR/FTL {snapshot.ErrorCount:N0} · WRN {snapshot.WarningCount:N0} · {DateTime.Now:HH:mm:ss}";
            if (scrollToEnd && (wasNearBottom || string.IsNullOrEmpty(keyword))) { _logBox.CaretIndex = _logBox.Text.Length; _logBox.ScrollToEnd(); }
        }
        catch (Exception ex) { _statusText.Text = $"读取日志失败：{ex.Message}"; }
        finally { _refreshing = false; }
    }
    private bool IsNearBottom() => _logBox.CaretIndex >= Math.Max(0, _logBox.Text.Length - 200);

    private static LogSnapshot BuildSnapshot(string path, int selectedLevel, string keyword)
    {
        var raw = LogSanitizer.Redact(ReadShared(path));
        var lines = raw.Replace("\r\n", "\n").Split('\n');
        var events = new List<LogEventBlock>();
        var current = new StringBuilder(); var currentLevel = "INF";
        void Flush() { if (current.Length == 0) return; events.Add(new LogEventBlock(currentLevel, current.ToString().TrimEnd())); current.Clear(); }
        foreach (var line in lines)
        {
            var match = HeaderRegex.Match(line);
            if (match.Success) { Flush(); currentLevel = match.Groups["level"].Value; current.AppendLine(line); }
            else if (current.Length > 0) current.AppendLine(line);
        }
        Flush();
        const int maxEventsInViewer = 8000;
        if (events.Count > maxEventsInViewer) events = events.Skip(events.Count - maxEventsInViewer).ToList();
        var errors = events.Count(e => e.Level is "ERR" or "FTL");
        var warnings = events.Count(e => e.Level == "WRN");
        bool LevelMatches(string level) => selectedLevel switch { 1 => level is "ERR" or "FTL", 2 => level == "WRN", 3 => level == "INF", 4 => level is "DBG" or "VRB", _ => true };
        var visible = events.Where(e => LevelMatches(e.Level) && (string.IsNullOrWhiteSpace(keyword) || e.Text.Contains(keyword, StringComparison.OrdinalIgnoreCase))).ToList();
        return new LogSnapshot(string.Join(Environment.NewLine, visible.Select(e => e.Text)), events.Count, visible.Count, errors, warnings);
    }
    private static string ReadShared(string path)
    {
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete, 64 * 1024, FileOptions.SequentialScan);
        using var reader = new StreamReader(stream, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        return reader.ReadToEnd();
    }
    private sealed record LogEventBlock(string Level, string Text);
    private sealed record LogSnapshot(string Text, int TotalEvents, int VisibleEvents, int ErrorCount, int WarningCount);
}
'''

XAML_ANCHOR = '''        <shared:UpdateBanner DockPanel.Dock="Top" x:Name="UpdateBannerHost" />\n\n    <Grid>'''
XAML_REPLACEMENT = '''        <shared:UpdateBanner DockPanel.Dock="Top" x:Name="UpdateBannerHost" />\n\n        <!-- 顶部详细运行日志：只增加诊断入口，不改变原有工作区/侧边栏/业务页面。 -->\n        <Border DockPanel.Dock="Top" Height="36" Background="#FAFAFB"\n                BorderBrush="#E0E0E2" BorderThickness="0,0,0,1">\n            <DockPanel LastChildFill="False">\n                <Button DockPanel.Dock="Right" x:Name="RuntimeLogButton"\n                        Margin="0,4,12,4" Padding="10,3"\n                        Background="Transparent" BorderBrush="#D8D8DB" BorderThickness="1"\n                        Cursor="Hand" Click="OnRuntimeLogClick"\n                        ToolTip="查看软件正在写入的详细运行日志">\n                    <StackPanel Orientation="Horizontal">\n                        <TextBlock Text="▤" FontSize="12" Foreground="#1D6BE5" Margin="0,0,6,0" />\n                        <TextBlock Text="运行日志" FontSize="11" Foreground="#333337" />\n                    </StackPanel>\n                </Button>\n            </DockPanel>\n        </Border>\n\n    <Grid>'''
FIELD_ANCHOR = '''    private WelcomeView? _welcome;\n    private readonly Dictionary<NavigationItem, FrameworkElement> _views = new();'''
FIELD_REPLACEMENT = '''    private WelcomeView? _welcome;\n    private RuntimeLogWindow? _runtimeLogWindow;\n    private readonly Dictionary<NavigationItem, FrameworkElement> _views = new();'''
METHOD_ANCHOR = '''    private void OnProjectSelected(object sender, SelectionChangedEventArgs e)\n    {'''
METHOD_REPLACEMENT = '''    /// <summary>顶部「运行日志」：单实例打开，避免重复开多个日志窗口。</summary>\n    private void OnRuntimeLogClick(object sender, RoutedEventArgs e)\n    {\n        if (_runtimeLogWindow is { IsLoaded: true })\n        {\n            if (_runtimeLogWindow.WindowState == WindowState.Minimized) _runtimeLogWindow.WindowState = WindowState.Normal;\n            _runtimeLogWindow.Activate();\n            return;\n        }\n        _runtimeLogWindow = new RuntimeLogWindow { Owner = this };\n        _runtimeLogWindow.Closed += (_, _) => _runtimeLogWindow = null;\n        _runtimeLogWindow.Show();\n    }\n\n    private void OnProjectSelected(object sender, SelectionChangedEventArgs e)\n    {'''

def replace_once(text: str, anchor: str, repl: str, name: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"{name}: expected anchor exactly once, found {count}. Baseline may not be official v0.16.3 or file was changed.")
    return text.replace(anchor, repl, 1)

def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    xaml = root / "src" / "MixCut" / "Views" / "MainWindow.xaml"
    code = root / "src" / "MixCut" / "Views" / "MainWindow.xaml.cs"
    new_file = root / "src" / "MixCut" / "Views" / "RuntimeLogWindow.cs"
    sln = root / "MixCut.sln"
    missing = [p for p in (sln, xaml, code) if not p.exists()]
    if missing:
        print("ERROR: not a MixCut Windows source root. Missing:")
        for p in missing: print("  -", p)
        return 2
    xaml_text = xaml.read_text(encoding="utf-8-sig")
    code_text = code.read_text(encoding="utf-8-sig")
    if "RuntimeLogButton" in xaml_text or "OnRuntimeLogClick" in code_text or new_file.exists():
        print("Patch is already applied; no files changed.")
        return 0
    required = ['Title="MixCut" Height="760" Width="1200"', '<shared:UpdateBanner DockPanel.Dock="Top" x:Name="UpdateBannerHost" />', 'ContentControl Grid.Column="1" x:Name="ContentArea"']
    for token in required:
        if token not in xaml_text: raise RuntimeError(f"Baseline validation failed: {token}")
    xaml_new = replace_once(xaml_text, XAML_ANCHOR, XAML_REPLACEMENT, "MainWindow.xaml")
    code_new = replace_once(code_text, FIELD_ANCHOR, FIELD_REPLACEMENT, "MainWindow.xaml.cs field")
    code_new = replace_once(code_new, METHOD_ANCHOR, METHOD_REPLACEMENT, "MainWindow.xaml.cs method")
    xaml.write_text(xaml_new, encoding="utf-8-sig", newline="\n")
    code.write_text(code_new, encoding="utf-8-sig", newline="\n")
    new_file.write_text(RUNTIME_LOG_CS, encoding="utf-8-sig", newline="\n")
    (root / "RUNTIME_LOG_PATCH.txt").write_text(MARKER + "\nBase: RoshanGH/mixcut-windows tag v0.16.3 / commit 03682083da22207802f9de82c3e11e34c4c5bce6\nChanged: MainWindow.xaml, MainWindow.xaml.cs; Added: RuntimeLogWindow.cs\nNo DB/schema/prompt/business workflow changes.\n", encoding="utf-8")
    print("SUCCESS: MixCut top runtime log center patch applied.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
