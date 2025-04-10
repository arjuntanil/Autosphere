@echo off
echo Starting document expiry check at %date% %time% >> logs\document_expiry.log
cd /d D:\AutoSphere
call .\autosphere\Scripts\activate.bat

rem This command checks for documents expiring in 3 days and sends notifications to users
python manage.py check_document_expiry >> logs\document_expiry.log 2>&1

echo Document expiry check completed at %date% %time% >> logs\document_expiry.log
echo. >> logs\document_expiry.log
