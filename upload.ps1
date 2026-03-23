$user = "u344917936"
$pass = "Popineo1@"
$ftpHost = "ftp://ftp.tuadministrativo.com/public_html/control_total_v2/"

foreach ($file in Get-ChildItem .) {
    if ($file.Attributes -ne "Directory" -and $file.Name -ne "upload.ps1") {
        $uriString = $ftpHost + $file.Name
        Write-Host "Uploading $($file.Name) to $uriString ..."
        try {
            $ftpRequest = [System.Net.FtpWebRequest]::Create($uriString)
            $ftpRequest.Credentials = New-Object System.Net.NetworkCredential($user, $pass)
            $ftpRequest.Method = [System.Net.WebRequestMethods+Ftp]::UploadFile
            $ftpRequest.UsePassive = $true
            $ftpRequest.UseBinary = $true
            
            $fileContent = [System.IO.File]::ReadAllBytes($file.FullName)
            $ftpRequest.ContentLength = $fileContent.Length
            
            $requestStream = $ftpRequest.GetRequestStream()
            $requestStream.Write($fileContent, 0, $fileContent.Length)
            $requestStream.Close()
            $requestStream.Dispose()
            
            $response = $ftpRequest.GetResponse()
            Write-Host "Success: $($file.Name) - Status: $($response.StatusDescription)"
            $response.Close()
        } catch {
            Write-Host "Error uploading $($file.Name): $($_.Exception.Message)"
        }
    }
}
