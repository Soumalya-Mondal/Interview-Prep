# define parent folder path
$parentFolderPath = (Resolve-Path ".").Path

# find all "__pycache__" folders
try {
    $pycacheFolders = Get-ChildItem -Path $parentFolderPath -Recurse -Directory -Filter "__pycache__"
}
catch {
    Write-Output "ERROR - $($_)"
}

# delete all the "__pycache__" folders
if ($pycacheFolders.Count -gt 0) {
    $pycacheFolders | ForEach-Object {
        try {
            Remove-Item -Path $_.FullName -Recurse -Force
        }
        catch {
            Write-Output "ERROR - $($_)"
        }
    }
}