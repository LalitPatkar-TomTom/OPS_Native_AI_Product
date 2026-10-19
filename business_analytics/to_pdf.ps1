# Convert the business value report (.docx) to PDF with Word.
param([string]$Docx = (Get-ChildItem "$PSScriptRoot\..\..\OPS_NativeAI_OPSHub_Business_Value_Report_*.docx" | Sort-Object LastWriteTime | Select-Object -Last 1).FullName)
$pdf = [IO.Path]::ChangeExtension($Docx, ".pdf")
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$doc = $w.Documents.Open($Docx)
$doc.SaveAs2($pdf, 17)
$doc.Close(0)
$w.Quit()
"saved $pdf"
