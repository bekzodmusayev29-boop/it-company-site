# Stop all Python bot instances
Write-Host "🔍 Qidirilmoqda: Python jarayonlari..." -ForegroundColor Yellow

$processes = Get-Process -Name python* -ErrorAction SilentlyContinue

if ($processes) {
    Write-Host "⚠️ Topildi: $($processes.Count) ta Python jarayon" -ForegroundColor Red
    
    foreach ($proc in $processes) {
        Write-Host "  - PID: $($proc.Id) | Name: $($proc.Name)" -ForegroundColor Cyan
    }
    
    $confirm = Read-Host "`nBarchasi to'xtatilsinmi? (y/n)"
    
    if ($confirm -eq 'y' -or $confirm -eq 'Y') {
        foreach ($proc in $processes) {
            try {
                Stop-Process -Id $proc.Id -Force
                Write-Host "✅ To'xtatildi: PID $($proc.Id)" -ForegroundColor Green
            } catch {
                Write-Host "❌ Xato: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
        
        Write-Host "`n✅ Barcha Python jarayonlar to'xtatildi!" -ForegroundColor Green
        Write-Host "📝 Endi botni qayta ishga tushiring: python bot.py" -ForegroundColor Yellow
    } else {
        Write-Host "❌ Bekor qilindi" -ForegroundColor Red
    }
} else {
    Write-Host "✅ Hech qanday Python jarayon topilmadi" -ForegroundColor Green
}
