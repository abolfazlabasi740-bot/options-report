Set-StrictMode -Version Latest

function Format-Integer {
    param([double]$Value)
    return $Value.ToString('#,##0',[Globalization.CultureInfo]::InvariantCulture)
}

function New-OptionsMarkdownReport {
    param(
        [Parameter(Mandatory=$true)][object]$Run,
        [Parameter(Mandatory=$true)][object[]]$Top,
        [AllowNull()][object]$Comparison,
        [AllowNull()][object]$Learning,
        [AllowNull()][object]$UnderlyingAnalysis,
        [AllowNull()][object]$SevenDayLearning,
        [Parameter(Mandatory=$true)][string]$OutputPath
    )
    $lines=[Collections.Generic.List[string]]::new()
    $lines.Add('<div dir="ltr">')
    $lines.Add('')
    $reportTitle=if($null -ne $Run.ReportVariant -and [string]$Run.ReportVariant -eq 'V4_CANDIDATE_LEVERAGE_GATE'){
        '# گزارش V4 کاندید تحلیل اختیار معامله'
    } else {
        '# گزارش موتور تحلیل اختیار معامله'
    }
    $lines.Add($reportTitle)
    $lines.Add('')
    $lines.Add('## مشخصات اجرا')
    $lines.Add('')
    $lines.Add('| مشخصه | مقدار |')
    $lines.Add('|---:|:---|')
    $lines.Add("| پروتکل | ``$($Run.Protocol)`` |")
    $lines.Add("| وضعیت نسخه | $(if($Run.ReportVariant -eq 'V4_CANDIDATE_LEVERAGE_GATE'){'V4 Candidate؛ عوامل V3 ثابت، فیلتر اهرم فعال'}else{'Baseline اجرایی V3؛ V4 فقط Candidate'}) |")
    if($Run.ReportVariant -eq 'V4_CANDIDATE_LEVERAGE_GATE'){
        $lines.Add("| فیلتر V4 | اهرم حداقل $($Run.MinLeverage.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) |")
    }
    $lines.Add("| نسخه پروژه | ``$($Run.Version)`` |")
    $lines.Add("| فایل داده | ``$($Run.FileName)`` |")
    $lines.Add("| زمان اجرا | ``$($Run.Timestamp)`` |")
    $lines.Add("| SHA-256 داده | ``$($Run.FileSha256)`` |")
    $lines.Add("| Digest قطعی رتبه‌بندی | ``$($Run.DeterministicDigest)`` |")
    $lines.Add("| مدل Risk | ``$($Run.RiskModel)`` |")
    $lines.Add("| هم‌ترازی Risk با Master | ``$($Run.RiskAlignmentStatus)`` |")
    $lines.Add("| ردیف‌های منبع | $(Format-Integer $Run.SourceRows) |")
    $lines.Add("| قراردادهای معتبر | $(Format-Integer $Run.ValidRows) |")
    $lines.Add("| ردیف‌های حذف‌شده | $(Format-Integer $Run.RemovedRows) |")
    $lines.Add('')
    $lines.Add('## رتبه‌بندی قراردادها')
    $lines.Add('')
    $lines.Add('| رتبه | نماد | اعمال | آخرین | سر به سری | پایه | اهرم | فاصله سر به سری | سررسید | باقی مانده روز | امتیاز |')
    $lines.Add('|:---:|:---|---:|---:|---:|---:|---:|---:|:---:|---:|---:|')
    $rank=0
    foreach($x in $Top){
        $rank++
        $lines.Add("| $rank | **$($x.Symbol)** | $(Format-Integer $x.Strike) | $(Format-Integer $x.Last) | $(Format-Integer $x.Breakeven) | $(Format-Integer $x.Underlying) | $($x.Leverage.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | $(($x.BEDistance*100).ToString('0.000',[Globalization.CultureInfo]::InvariantCulture))٪ | ``$($x.Expiration)`` | $($x.RemainingDays) | **$($x.FinalScore.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture))** |")
    }
    $lines.Add('')
    $lines.Add('## اجزای امتیاز و جریمه ریسک')
    $lines.Add('')
    $lines.Add('| رتبه | نماد | نقدشوندگی | ارزش‌گذاری | بازده | زمان | یونانی‌ها | بازار | پایه | جریمه ریسک | نهایی |')
    $lines.Add('|:---:|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    $rank=0
    foreach($x in $Top){
        $rank++
        $lines.Add("| $rank | **$($x.Symbol)** | $($x.BlockLiquidity.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | $($x.BlockValuation.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | $($x.BlockPayoff.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | $($x.BlockTime.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | $($x.BlockGreeks.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | $($x.BlockMarket.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | $($x.BaseScore.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | $($x.RiskPenalty.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | **$($x.FinalScore.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture))** |")
    }
    $lines.Add('')
    $lines.Add('## کیفیت داده رتبه‌های برتر')
    $lines.Add('')
    $lines.Add('| رتبه | نماد | اطمینان داده | داده مفقود | پرچم‌ها | نوع تصمیم | طبقه‌بندی |')
    $lines.Add('|:---:|:---|---:|:---|:---|:---|:---|')
    $rank=0
    foreach($x in $Top){
        $rank++
        $missing=if(@($x.MissingData).Count -gt 0){(@($x.MissingData) -join '، ')}else{'ندارد'}
        $flags=if(@($x.Flags).Count -gt 0){(@($x.Flags) -join '، ')}else{'ندارد'}
        $confidence=($x.DataConfidence*100).ToString('0',[Globalization.CultureInfo]::InvariantCulture)+'٪'
        $lines.Add("| $rank | **$($x.Symbol)** | $confidence | $missing | $flags | $($x.DecisionType) | $($x.Classification) |")
    }
    $avgLev=($Top|Measure-Object Leverage -Average).Average
    $avgDays=($Top|Measure-Object RemainingDays -Average).Average
    $near=@($Top|Where-Object{$_.RemainingDays-le7}).Count
    $missingIv=@($Top|Where-Object{$null-eq$_.IV}).Count
    $totalVolume=($Top|Measure-Object Volume -Sum).Sum
    $totalValue=($Top|Measure-Object TradeValue -Sum).Sum
    $avgPenalty=($Top|Measure-Object RiskPenalty -Average).Average
    $avgVolumePenalty=($Top|Measure-Object LiquidityVolumePenalty -Average).Average
    $lines.Add('')
    $lines.Add('## شاخص‌های خلاصه')
    $lines.Add('')
    $lines.Add('| شاخص | مقدار | توضیح |')
    $lines.Add('|---:|---:|:---|')
    $lines.Add("| جامعه رتبه‌بندی | $(Format-Integer $Run.ValidRows) | قرارداد معتبر |")
    $lines.Add("| میانگین اهرم گروه برتر | $($avgLev.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | برابر |")
    $lines.Add("| میانگین زمان باقی‌مانده | $($avgDays.ToString('0.0',[Globalization.CultureInfo]::InvariantCulture)) | روز |")
    $lines.Add("| سررسید حداکثر تا ۷ روز | $(Format-Integer $near) | قرارداد |")
    $lines.Add("| حجم تجمیعی معاملات | $(Format-Integer $totalVolume) | قرارداد |")
    $lines.Add("| ارزش تجمیعی معاملات | $(Format-Integer $totalValue) | واحد پولی فایل |")
    $lines.Add("| نوسان ضمنی ناموجود | $(Format-Integer $missingIv) | قرارداد؛ وزن در همان بلوک بازتوزیع شده است |")
    $lines.Add("| میانگین جریمه ریسک ترکیبی | $($avgPenalty.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | امتیاز |")
    $lines.Add("| میانگین جریمه حجم پایین | $($avgVolumePenalty.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | از امتیاز پایه؛ حداکثر طبق پیکربندی |")
    $lines.Add("| نگاشت Status | تأیید نشده | Status امتیاز ساختگی نگرفته و وزن آن داخل Market Structure بازتوزیع شده است |")
    $lines.Add('')
    $lines.Add('## ارزیابی عملکرد رتبه‌بندی قبلی')
    $lines.Add('')
    if($null -eq $Comparison -or $Comparison.Status -eq 'NO_PREVIOUS_RUN'){
        $lines.Add('برای اجرای قبلی داده‌ای وجود ندارد؛ ارزیابی بازده از اجرای بعدی آغاز می‌شود.')
    } elseif(@($Comparison.PreviousTopOutcomes).Count -eq 0){
        $lines.Add('برای پنج قرارداد برتر اجرای قبلی، قرارداد مشترک قابل ارزیابی در این اجرا پیدا نشد.')
    } else {
        $lines.Add('| رتبه قبلی | نماد | قیمت اجرای قبلی | قیمت اجرای جدید | تغییر قیمت | بازده فرضی | نتیجه |')
        $lines.Add('|---:|:---|---:|---:|---:|---:|:---|')
        foreach($o in @($Comparison.PreviousTopOutcomes)){
            $returnText=$o.ReturnPct.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)+'٪'
            $deltaText=$o.PriceDelta.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)
            $lines.Add("| $($o.PreviousRank) | **$($o.Symbol)** | $($o.PreviousLast.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | $($o.CurrentLast.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | $deltaText | $returnText | $($o.OutcomeStatus) |")
        }
        $summary=$Comparison.OutcomeSummary
        $avgText=if($null -eq $summary.AverageReturnPct){'N/A'}else{$summary.AverageReturnPct.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)+'٪'}
        $lines.Add('')
        $lines.Add("خلاصه ارزیابی پنج رتبه اول اجرای قبلی: $($summary.Positive) مثبت، $($summary.Negative) منفی، $($summary.Unchanged) بدون تغییر؛ میانگین بازده فرضی: $avgText.")
    }
    $lines.Add('')
    $lines.Add('این ارزیابی بر پایه تغییر قیمت آخرین ثبت‌شده بین دو اجرای متوالی است و کارمزد، اندازه قرارداد و نقدشوندگی واقعی را محاسبه نمی‌کند.')
    $lines.Add('')
    $lines.Add('## بحث آموزشی اجباری این اجرا')
    $lines.Add('')
    if ($null -eq $Learning -or $null -eq $Learning.Education) {
        $lines.Add('بحث آموزشی برای این اجرا تولید نشده است؛ این وضعیت خطای قرارداد گزارش است و نباید در گزارش نهایی رخ دهد.')
    } else {
        $education = $Learning.Education
        $lines.Add('این بخش برای یادگیری، نقد فرضیات و ثبت نقاط کور است؛ به‌تنهایی مجوز تغییر خودکار وزن‌ها یا Rules نیست.')
        $lines.Add('')
        $lines.Add('| ادعا/درس | شواهد | اطمینان | شاهد ردکننده | اقدام پیشنهادی |')
        $lines.Add('|:---|:---|:---:|:---|:---|')
        foreach ($lesson in @($education.Lessons)) {
            $lines.Add("| $($lesson.Claim) | ``$($lesson.Evidence)`` | $($lesson.Confidence) | $($lesson.Disconfirming) | $($lesson.Action) |")
        }
        if (@($education.Actions).Count -gt 0) {
            $lines.Add('')
            $lines.Add('اقدام‌های مشترک اتاق فکر:')
            foreach ($action in @($education.Actions)) {
                $lines.Add("- $action")
            }
        }
        $lines.Add('')
    $lines.Add("وضعیت ارتقای دانش: **$($education.KnowledgePromotion)**؛ تغییر خودکار مدل: **$($education.AutomaticModelChange)**.")
    }
    $lines.Add('')
    $lines.Add('## یادگیری هفت‌روزه و جهش‌های شارپ')
    $lines.Add('')
    if ($null -eq $SevenDayLearning -or [string]$SevenDayLearning.Status -eq 'NO_SNAPSHOTS') {
        $lines.Add('برای مقایسه‌ی فایل‌های روزانه‌ی Optionschool داده‌ی کافی در آرشیو موجود نیست.')
    } else {
        $lines.Add("| وضعیت پنجره | $($SevenDayLearning.Status) | از ``$($SevenDayLearning.WindowStart)`` تا ``$($SevenDayLearning.WindowEnd)`` |")
        $lines.Add('')
        $lines.Add('| رتبه | بازه | فاصله تقویمی | نماد | آخرین قبلی | آخرین جدید | تغییر | پایه | اهرم | حجم جدید | برچسب‌های علت احتمالی |')
        $lines.Add('|:---:|:---:|:---:|:---|---:|---:|---:|---:|---:|---:|:---|')
        $rank=0
        foreach($item in @($SevenDayLearning.DailyTop | Select-Object -First 25)){
            $rank++
            $ret=$item.ReturnPct.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)+'٪'
            $cause=if(@($item.CauseTags).Count -gt 0){@($item.CauseTags)-join '، '}else{'نامشخص'}
            $base=if($null -ne $item.UnderlyingLast){$item.UnderlyingLast.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)}else{'N/A'}
            $lev=if($null -ne $item.Leverage){$item.Leverage.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)}else{'N/A'}
            $vol=if($null -ne $item.Volume){Format-Integer $item.Volume}else{'N/A'}
            $gap=if($null -ne $item.CalendarGapDays){"$($item.CalendarGapDays) روز"}else{'N/A'}
            $lines.Add("| $rank | ``$($item.From)→$($item.To)`` | $gap | **$($item.Symbol)** | $($item.PrevLast.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | $($item.Last.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)) | $ret | $base | $lev | $vol | $cause |")
        }
        $lines.Add('')
        $lines.Add('### جهش‌های شارپ (حداقل ۲۰٪ بین دو فایل متوالی)')
        $lines.Add('')
        if(@($SevenDayLearning.SharpDaily).Count -eq 0){
            $lines.Add('در پنجره‌ی موجود، جهش حداقل ۲۰٪ بین دو فایل متوالی ثبت نشد.')
        } else {
            $lines.Add('| نماد | بازه | فاصله تقویمی | بازده | علت‌های احتمالی هم‌بسته |')
            $lines.Add('|:---|:---:|:---:|---:|:---|')
            foreach($item in @($SevenDayLearning.SharpDaily | Select-Object -First 25)){
                $gap=if($null -ne $item.CalendarGapDays){"$($item.CalendarGapDays) روز"}else{'N/A'}
                $lines.Add("| **$($item.Symbol)** | ``$($item.From)→$($item.To)`` | $gap | $($item.ReturnPct.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture))٪ | $(@($item.CauseTags)-join '، ') |")
            }
        }
        $lines.Add('')
        $lines.Add('هر ردیف، آخرین فایل یک روز معاملاتی موجود را با آخرین فایل روز معاملاتی موجودِ پیشین مقایسه می‌کند. اگر آرشیو یک روز کاری را نداشته باشد، فاصلهٔ تقویمی درج می‌شود؛ بنابراین ردیف با فاصلهٔ بیش از یک روز، جهش یک‌روزه تلقی نمی‌شود. این بخش برای یادگیری علت‌های محتمل جهش است؛ «هم‌بستگی» به‌عنوان علت قطعی گزارش نمی‌شود. حجم، IV، اهرم، فاصله سر‌به‌سر، سررسید و حرکت سهم پایه باید با bid/ask و رویداد خبری نقطه‌ای اعتبارسنجی شوند.')
    }
    $lines.Add('')
    if($null -ne $UnderlyingAnalysis){
        $lines.Add('## تحلیل سهم پایه و اخبار مرتبط')
        $lines.Add('')
        $lines.Add("وضعیت منبع: **$($UnderlyingAnalysis.SourceStatus)**؛ تاریخ بررسی: ``$($UnderlyingAnalysis.AsOf)``.")
        foreach($note in @($UnderlyingAnalysis.Notes)){ $lines.Add("- $note") }
        $lines.Add('')
        $lines.Add('| سهم پایه | قیمت | بازده ۵روزه | RSI14 | نسبت خرید حقیقی/فروش حقیقی | نسبت خرید حقوقی/فروش حقوقی | روند احتمالی | پیام‌ها |')
        $lines.Add('|:---|---:|---:|---:|---:|---:|:---:|---:|')
        foreach($u in @($UnderlyingAnalysis.Underlyings)){
            $price=if($null -ne $u.Price){$u.Price.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)}else{'N/A'}
            $ret=if($null -ne $u.Return5D){$u.Return5D.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)+'٪'}else{'N/A'}
            $rsi=if($null -ne $u.RSI14){$u.RSI14.ToString('0.0',[Globalization.CultureInfo]::InvariantCulture)}else{'N/A'}
            $ir=if($null -ne $u.IndividualBuySellVolumeRatio){$u.IndividualBuySellVolumeRatio.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)}else{'N/A'}
            $lr=if($null -ne $u.LegalBuySellVolumeRatio){$u.LegalBuySellVolumeRatio.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)}else{'N/A'}
            $msg=if($null -ne $u.MessageCount){[string]$u.MessageCount}else{'N/A'}
            $bias=if($null -ne $u.TrendBias){$u.TrendBias}else{'NOT_ASSESSED'}
            $lines.Add("| $($u.Symbol) | $price | $ret | $rsi | $ir | $lr | $bias | $msg |")
        }
        $lines.Add('')
        $lines.Add('## عناوین پیام‌های اخیر سهم‌های پایه')
        $lines.Add('')
        $lines.Add('| سهم پایه | تاریخ پیام | عنوان پیام |')
        $lines.Add('|:---|:---:|:---|')
        foreach($u in @($UnderlyingAnalysis.Underlyings)){
            foreach($m in @($u.Messages | Select-Object -First 3)){
                $date=if($null -ne $m.dEven){[string]$m.dEven}else{'N/A'}
                $title=if($null -ne $m.tseTitle){([string]$m.tseTitle).Replace('|','/')}else{'N/A'}
                $lines.Add("| $($u.Symbol) | $date | $title |")
            }
        }
        $lines.Add('')
        $lines.Add('داده‌های روند و حقیقی/حقوقی از TSETMC دریافت شده‌اند؛ داده کدال در این اجرا به‌صورت جداگانه متصل نیست. این بخش پیش‌بینی احتمالی است و سیگنال قطعی محسوب نمی‌شود.')
        $lines.Add('')
    }
    $lines.Add('## ملاحظات')
    $lines.Add('')
    $lines.Add('| موضوع | توضیح |')
    $lines.Add('|---:|:---|')
    $lines.Add('| حجم پایین | جریمه پیوسته بر اساس صدک حجم اعمال شده تا خروج اضطراری در قراردادهای کم‌معامله پرریسک‌تر نشود. |')
    $lines.Add('| داده مفقود | مطابق V3، داده مفقود امتیاز ثابت نگرفته و وزن آن در همان بلوک بازتوزیع شده است. |')
    $lines.Add('| Risk | آستانه‌های مدل پله‌ای ۰/۵/۱۰/۲۰ در Master کامل نشده‌اند؛ مدل جاری با برچسب Transitional در Audit ثبت شده است. |')
    $lines.Add('| V4 | این خروجی V4 Candidate است؛ وزن‌ها و فرمول‌های V3 ثابت مانده‌اند و V4 هنوز Production-approved نیست. |')
    $lines.Add('| ماهیت خروجی | این گزارش صرفاً رتبه‌بندی کیفیت قرارداد و تصمیم‌یار است و توصیه خرید یا فروش محسوب نمی‌شود. |')
    $lines.Add('')
    $lines.Add('</div>')
    [IO.File]::WriteAllLines($OutputPath,$lines,[Text.UTF8Encoding]::new($true))
    return [pscustomobject]@{Path=$OutputPath;Markdown=($lines-join"`r`n")}
}

Export-ModuleMember -Function *
