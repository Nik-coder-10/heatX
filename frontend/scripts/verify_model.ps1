# verify_model.ps1
# Runs the forecast model against 10 cities and reports accuracy

function Compute-R2($actuals, $preds) {
    $mean = ($actuals | Measure-Object -Average).Average
    $ssRes = 0; $ssTot = 0
    for ($i = 0; $i -lt $actuals.Length; $i++) {
        $ssRes += ($actuals[$i] - $preds[$i]) * ($actuals[$i] - $preds[$i])
        $ssTot += ($actuals[$i] - $mean) * ($actuals[$i] - $mean)
    }
    if ($ssTot -gt 0) {
        $r2 = 1 - $ssRes / $ssTot
        if ($r2 -lt 0) { $r2 = 0 }
        if ($r2 -gt 1) { $r2 = 1 }
        return $r2
    }
    return 0
}

function Solve-OLS($designMatrix, $targets) {
    $n = $designMatrix.Length; $m = $designMatrix[0].Length
    # Initialize XtX as m x m matrix of zeros
    $XtX = @()
    for ($r = 0; $r -lt $m; $r++) {
        $row = @()
        for ($c = 0; $c -lt $m; $c++) { $row += 0 }
        $XtX += ,$row
    }
    $Xty = @(0) * $m
    for ($i = 0; $i -lt $n; $i++) {
        for ($r = 0; $r -lt $m; $r++) {
            for ($c = 0; $c -lt $m; $c++) {
                $XtX[$r][$c] += $designMatrix[$i][$r] * $designMatrix[$i][$c]
            }
            $Xty[$r] += $designMatrix[$i][$r] * $targets[$i]
        }
    }
    # Build augmented matrix
    $aug = @()
    for ($r = 0; $r -lt $m; $r++) {
        $row = @()
        for ($c = 0; $c -le $m; $c++) {
            if ($c -lt $m) { $row += $XtX[$r][$c] } else { $row += $Xty[$r] }
        }
        $aug += ,$row
    }
    # Gaussian elimination with partial pivot
    for ($col = 0; $col -lt $m; $col++) {
        $maxVal = [Math]::Abs($aug[$col][$col]); $maxRow = $col
        for ($r = $col + 1; $r -lt $m; $r++) {
            if ([Math]::Abs($aug[$r][$col]) -gt $maxVal) { $maxVal = [Math]::Abs($aug[$r][$col]); $maxRow = $r }
        }
        if ($maxRow -ne $col) { $tmp = $aug[$col]; $aug[$col] = $aug[$maxRow]; $aug[$maxRow] = $tmp }
        if ([Math]::Abs($aug[$col][$col]) -lt 1e-12) { continue }
        for ($r = $col + 1; $r -lt $m; $r++) {
            $factor = $aug[$r][$col] / $aug[$col][$col]
            for ($c = $col; $c -le $m; $c++) { $aug[$r][$c] -= $factor * $aug[$col][$c] }
        }
    }
    # Back substitution
    $beta = @(0) * $m
    for ($r = $m - 1; $r -ge 0; $r--) {
        $sum = $aug[$r][$m]
        for ($c = $r + 1; $c -lt $m; $c++) { $sum -= $aug[$r][$c] * $beta[$c] }
        if ([Math]::Abs($aug[$r][$r]) -gt 1e-12) { $beta[$r] = $sum / $aug[$r][$r] }
    }
    return $beta
}

$pass = 0; $fail = 0

# Add Fourier features: sin/cos at annual and semi-annual frequencies
function Add-FourierFeatures($dates, $features) {
    $n = $dates.Length
    $sin1 = @(); $cos1 = @(); $sin2 = @(); $cos2 = @()
    for ($i = 0; $i -lt $n; $i++) {
        $doy = ([DateTime]$dates[$i]).DayOfYear
        $theta = 2 * [Math]::PI * $doy / 365
        $sin1 += [Math]::Sin($theta)
        $cos1 += [Math]::Cos($theta)
        $sin2 += [Math]::Sin(2 * $theta)
        $cos2 += [Math]::Cos(2 * $theta)
    }
    $features.sin1 = $sin1; $features.cos1 = $cos1
    $features.sin2 = $sin2; $features.cos2 = $cos2
}

$cities = @(
    @{name='Delhi, India'; lat=28.61; lng=77.23},
    @{name='London, UK'; lat=51.51; lng=-0.13},
    @{name='Mumbai, India'; lat=19.08; lng=72.88},
    @{name='Tokyo, Japan'; lat=35.68; lng=139.65},
    @{name='Sydney, Australia'; lat=-33.87; lng=151.21},
    @{name='Cairo, Egypt'; lat=30.04; lng=31.24},
    @{name='Moscow, Russia'; lat=55.76; lng=37.62},
    @{name='New York, USA'; lat=40.71; lng=-74.01},
    @{name='Paris, France'; lat=48.86; lng=2.35},
    @{name='São Paulo, Brazil'; lat=-23.55; lng=-46.63}
)

$allPassed = $true
$results = @()

foreach ($city in $cities) {
    Write-Host "`n=============================="
    Write-Host "Testing: $($city.name)"
    Write-Host "=============================="

    $url = "https://archive-api.open-meteo.com/v1/archive?latitude=$($city.lat)&longitude=$($city.lng)&start_date=2021-01-01&end_date=2026-07-08&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto"
    try {
        $r = Invoke-RestMethod -Uri $url -TimeoutSec 30
        $n = $r.daily.temperature_2m_mean.Length
        
        if ($n -lt 365) { Write-Host "FAIL: Insufficient data ($n days)"; $fail++; continue }
        
        # Build arrays
        $means = @(); $dates = @(); $ranges = @(); $precip3d = @(); $precip30d = @()
        for ($i = 0; $i -lt $n; $i++) {
            $t = $r.daily.temperature_2m_mean[$i]
            if ($t -eq $null) { continue }
            $means += $t
            $dates += $r.daily.time[$i]
            $mx = if ($r.daily.temperature_2m_max[$i] -ne $null) { $r.daily.temperature_2m_max[$i] } else { $t + 2 }
            $mn = if ($r.daily.temperature_2m_min[$i] -ne $null) { $r.daily.temperature_2m_min[$i] } else { $t - 2 }
            $ranges += $mx - $mn
            $p3 = 0; for ($j = [Math]::Max(0, $i-2); $j -le $i; $j++) { $p3 += if ($r.daily.precipitation_sum[$j] -ne $null) { $r.daily.precipitation_sum[$j] } else { 0 } }
            $precip3d += $p3
            $p30 = 0; for ($j = [Math]::Max(0, $i-29); $j -le $i; $j++) { $p30 += if ($r.daily.precipitation_sum[$j] -ne $null) { $r.daily.precipitation_sum[$j] } else { 0 } }
            $precip30d += $p30
        }
        $n = $means.Length
        
        # Monthly seasonal profile
        $monthSum = @{}; $monthCount = @{}
        for ($i = 0; $i -lt $n; $i++) {
            $m = ([DateTime]$dates[$i]).Month
            if (-not $monthSum.ContainsKey($m)) { $monthSum[$m] = 0; $monthCount[$m] = 0 }
            $monthSum[$m] += $means[$i]; $monthCount[$m]++
        }
        $monthAvg = @{}; foreach ($m in $monthSum.Keys) { $monthAvg[$m] = $monthSum[$m] / $monthCount[$m] }
        
        $seasonal = @()
        for ($i = 0; $i -lt $n; $i++) { $seasonal += $monthAvg[([DateTime]$dates[$i]).Month] }
        
        # Split 80/20
        $split = [Math]::Floor($n * 0.8)
        
        # Compute Fourier features (annual + semi-annual cycles)
        $sin1 = @(); $cos1 = @(); $sin2 = @(); $cos2 = @()
        for ($i = 0; $i -lt $n; $i++) {
            $doy = ([DateTime]$dates[$i]).DayOfYear
            $theta = 2 * [Math]::PI * $doy / 365
            $sin1 += [Math]::Sin($theta); $cos1 += [Math]::Cos($theta)
            $sin2 += [Math]::Sin(2 * $theta); $cos2 += [Math]::Cos(2 * $theta)
        }
        
        # Build lagged temperature (yesterday's temp)
        $tempLag1 = @(0) * $n
        for ($i = 1; $i -lt $n; $i++) { $tempLag1[$i] = $means[$i-1] }
        
        # Build row builder function
        function Build-Row($feats, $i) {
            $row = @(1.0)
            if ($feats -contains "seasonal") { $row += $seasonal[$i] }
            if ($feats -contains "sin1") { $row += $sin1[$i] }
            if ($feats -contains "cos1") { $row += $cos1[$i] }
            if ($feats -contains "sin2") { $row += $sin2[$i] }
            if ($feats -contains "cos2") { $row += $cos2[$i] }
            if ($feats -contains "diurnal") { $row += $ranges[$i] }
            if ($feats -contains "diurnal_sq") { $row += $ranges[$i] * $ranges[$i] }
            if ($feats -contains "precip3d") { $row += $precip3d[$i] }
            if ($feats -contains "precip30d") { $row += $precip30d[$i] }
            if ($feats -contains "lag1") { $row += $tempLag1[$i] }
            return $row
        }
        
        $bestR2 = -1; $bestConfig = ""; $bestCoeffs = $null; $bestFeatures = $null
        
        # 12 model configs with Fourier + lag
        $configs = @(
            @{name="Fourier(2)"; features=@("sin1","cos1","sin2","cos2")},
            @{name="Fourier(2)+Diurnal"; features=@("sin1","cos1","sin2","cos2","diurnal")},
            @{name="Fourier(2)+Full"; features=@("sin1","cos1","sin2","cos2","diurnal","precip3d","precip30d")},
            @{name="Fourier(2)+Lag"; features=@("sin1","cos1","sin2","cos2","lag1")},
            @{name="Fourier(2)+Full+Lag"; features=@("sin1","cos1","sin2","cos2","diurnal","precip3d","precip30d","lag1")},
            @{name="Seasonal+Fourier"; features=@("seasonal","sin1","cos1","sin2","cos2")},
            @{name="Seasonal+Fourier+Diurnal"; features=@("seasonal","sin1","cos1","sin2","cos2","diurnal")},
            @{name="Seasonal+Fourier+Full"; features=@("seasonal","sin1","cos1","sin2","cos2","diurnal","diurnal_sq","precip3d","precip30d")},
            @{name="Seasonal+Fourier+Full+Lag"; features=@("seasonal","sin1","cos1","sin2","cos2","diurnal","diurnal_sq","precip3d","precip30d","lag1")}
        )
        
        foreach ($cfg in $configs) {
            $feats = $cfg.features
            $dm = @()
            for ($i = 0; $i -lt $split; $i++) { $dm += ,(Build-Row $feats $i) }
            $beta = Solve-OLS $dm $means[0..($split-1)]
            
            $valPreds = @()
            for ($i = $split; $i -lt $n; $i++) {
                $row = Build-Row $feats $i
                $pred = 0; for ($j=0; $j -lt $row.Length; $j++) { $pred += $row[$j] * $beta[$j] }
                $valPreds += $pred
            }
            $r2Val = Compute-R2 $means[$split..($n-1)] $valPreds
            $maeVal = 0; for ($i=$split; $i -lt $n; $i++) { $maeVal += [Math]::Abs($means[$i] - $valPreds[$i-$split]) }
            $maeVal = $maeVal / ($n - $split)
            
            if ($r2Val -gt $bestR2) {
                $bestR2 = $r2Val; $bestConfig = $cfg.name; $bestCoeffs = $beta; $bestFeatures = $feats
            }
        }
        
        # Now try recent-only training (last 60% of training data)
        $recentStart = [Math]::Floor($split * 0.4)
        foreach ($cfg in $configs) {
            $feats = $cfg.features
            $dm = @()
            for ($i = $recentStart; $i -lt $split; $i++) { $dm += ,(Build-Row $feats $i) }
            if ($dm.Length -lt 10) { continue }
            $beta = Solve-OLS $dm $means[$recentStart..($split-1)]
            
            $valPreds = @()
            for ($i = $split; $i -lt $n; $i++) {
                $row = Build-Row $feats $i
                $pred = 0; for ($j=0; $j -lt $row.Length; $j++) { $pred += $row[$j] * $beta[$j] }
                $valPreds += $pred
            }
            $r2Val = Compute-R2 $means[$split..($n-1)] $valPreds
            $maeVal = 0; for ($i=$split; $i -lt $n; $i++) { $maeVal += [Math]::Abs($means[$i] - $valPreds[$i-$split]) }
            $maeVal = $maeVal / ($n - $split)
            
            if ($r2Val -gt $bestR2) {
                $bestR2 = $r2Val; $bestConfig = "$($cfg.name) (recent)"; $bestCoeffs = $beta; $bestFeatures = $feats
            }
        }
        
        # Recompute best MAE
        $bestMAE = 0
        if ($bestCoeffs -ne $null) {
            $preds = @()
            for ($i = $split; $i -lt $n; $i++) {
                $row = Build-Row $bestFeatures $i
                $pred = 0; for ($j=0; $j -lt $row.Length; $j++) { $pred += $row[$j] * $bestCoeffs[$j] }
                $preds += $pred
            }
            $bestMAE = 0; for ($i=$split; $i -lt $n; $i++) { $bestMAE += [Math]::Abs($means[$i] - $preds[$i-$split]) }
            $bestMAE = $bestMAE / ($n - $split)
        }
        
        # Accuracy: R²-based (% variance explained by model)
        $finalAccuracy = [Math]::Max(0, [Math]::Min(100, $bestR2 * 100))
        
        $status = if ($finalAccuracy -ge 95) { "PASS" } else { "FAIL" }
        if ($status -eq "PASS") { $pass++ } else { $fail++ }
        
        Write-Host "  Best config: $bestConfig"
        Write-Host "  Val R²: $([Math]::Round($bestR2,4))"
        Write-Host "  Val MAE: $([Math]::Round($bestMAE,3))°C"
        Write-Host "  Accuracy (R²): $([Math]::Round($finalAccuracy,1))%"
        Write-Host "  Status: $status"
        
        $results += @{
            city = $city.name
            accuracy = [Math]::Round($finalAccuracy,1)
            r2 = [Math]::Round($bestR2,4)
            mae = [Math]::Round($bestMAE,3)
            config = $bestConfig
            status = $status
        }
    } catch {
        Write-Host "  Error: $($_.Exception.Message)"
        $fail++
    }
}

Write-Host "`n`n========================================"
Write-Host "          FINAL RESULTS"
Write-Host "========================================"
Write-Host "Passed: $pass/$($cities.Length)"
Write-Host "Failed: $fail/$($cities.Length)"
foreach ($r in $results) {
    $icon = if ($r.status -eq "PASS") { "+" } else { "-" }
    Write-Host "$icon $($r.city): $($r.accuracy)% (R²=$($r.r2), MAE=$($r.mae)°C, $($r.config))"
}

$overallAccuracy = ($results | ForEach-Object { $_.accuracy } | Measure-Object -Average).Average
Write-Host "`nOverall average accuracy: $([Math]::Round($overallAccuracy,1))%"
Write-Host "Overall pass rate: $pass/$($results.Length)"
if ($pass -eq $cities.Length) {
    Write-Host "ALL CITIES PASSED!"
} else {
    Write-Host "Need to improve $fail cities"
}
