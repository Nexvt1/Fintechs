# ==============================================================================
# COMPILADOR NATIVO DO APK ANDROID FISTU (Fistu.apk)
# Gera o APK assinado e salva automaticamente na pasta Downloads
# ==============================================================================

$ErrorActionPreference = "Stop"

# Auto-detect Android SDK
$SdkDir = if (Test-Path "$env:LOCALAPPDATA\Android\Sdk") {
    "$env:LOCALAPPDATA\Android\Sdk"
} elseif (Test-Path "$env:LOCALAPPDATA\Programs\NexOS-Android-SDK") {
    "$env:LOCALAPPDATA\Programs\NexOS-Android-SDK"
} elseif ($env:ANDROID_HOME -and (Test-Path $env:ANDROID_HOME)) {
    $env:ANDROID_HOME
} else {
    throw "Android SDK não encontrado no sistema."
}

# Auto-detect JDK
$JavaBin = if (Test-Path "C:\Program Files\Java\jdk-23\bin\javac.exe") {
    "C:\Program Files\Java\jdk-23\bin"
} elseif ($env:JAVA_HOME -and (Test-Path "$env:JAVA_HOME\bin\javac.exe")) {
    "$env:JAVA_HOME\bin"
} else {
    $foundJavac = Get-ChildItem -Path "C:\Program Files\Java" -Filter "javac.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($foundJavac) { $foundJavac.DirectoryName } else { throw "JDK (javac.exe) não encontrado em C:\Program Files\Java." }
}

$env:JAVA_HOME = Split-Path -Parent $JavaBin
$env:PATH = "$JavaBin;$env:PATH"

# Auto-detect Android Build-Tools
$BtDir = Join-Path $SdkDir "build-tools"
$BtFolders = Get-ChildItem -LiteralPath $BtDir -Directory | Sort-Object Name -Descending
if (-not $BtFolders) { throw "Nenhuma pasta em build-tools encontrada." }
$BtBin = $BtFolders[0].FullName

$AsciiRoot = "C:\Users\Public\Fistu-APK-Build"
$WorkDir = Join-Path $AsciiRoot "project"
$DownloadsDir = Join-Path $env:USERPROFILE "Downloads"
$OutApkDownloads = Join-Path $DownloadsDir "Fistu.apk"
$ProjectDir = $PSScriptRoot
$OutApkProject = Join-Path $ProjectDir "Fistu.apk"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " [FISTU APK BUILDER] Iniciando compilacao do APK..." -ForegroundColor Cyan
Write-Host " SDK Android      : $SdkDir" -ForegroundColor Cyan
Write-Host " Build-Tools      : $BtBin" -ForegroundColor Cyan
Write-Host " Java JDK         : $JavaBin" -ForegroundColor Cyan
Write-Host " Destino Principal: $OutApkDownloads" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan

# 3. Android.jar
$AsciiAndroidJar = Join-Path $AsciiRoot "android.jar"
if (-not (Test-Path -LiteralPath $AsciiAndroidJar)) {
    $PlatDir = Join-Path $SdkDir "platforms"
    $AndroidJarOrig = Get-ChildItem -LiteralPath $PlatDir -Filter "android.jar" -Recurse | Select-Object -First 1
    if (-not $AndroidJarOrig) { throw "android.jar não encontrado em $PlatDir" }
    New-Item -ItemType Directory -Path $AsciiRoot -Force | Out-Null
    Copy-Item -LiteralPath $AndroidJarOrig.FullName -Destination $AsciiAndroidJar -Force
}

# 4. Criar estrutura de compilação limpa
Remove-Item -LiteralPath $WorkDir -Recurse -Force -ErrorAction SilentlyContinue
$SrcDir = Join-Path $WorkDir "src\br\com\fintech\evolution"
$ResDir = Join-Path $WorkDir "res"
$AssetsDir = Join-Path $WorkDir "assets"
$ObjDir = Join-Path $WorkDir "obj"
$DexDir = Join-Path $WorkDir "dex"

New-Item -ItemType Directory -Path $SrcDir, $ResDir, $AssetsDir, $ObjDir, $DexDir -Force | Out-Null

# Copiar os arquivos web (HTML/CSS/JS/LOGOS) para assets
Write-Host "[1/5] Empacotando interface Web Fistu em assets..." -ForegroundColor Cyan
Copy-Item -Path "$ProjectDir\www\*" -Destination $AssetsDir -Recurse -Force

# Copiar recursos do Android (mipmaps com a logo oficial Fistu)
Write-Host "[2/5] Copiando icones com a logo oficial Fistu..." -ForegroundColor Cyan
Get-ChildItem -Path "$ProjectDir\android\app\src\main\res" -Directory -Filter "mipmap-*" | Where-Object { $_.Name -ne "mipmap-anydpi-v26" } | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $ResDir -Recurse -Force
}

$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)

# Criar strings.xml se necessário
$ResValues = Join-Path $ResDir "values"
New-Item -ItemType Directory -Path $ResValues -Force | Out-Null
$StringsXml = @'
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Fistu</string>
</resources>
'@
[System.IO.File]::WriteAllText((Join-Path $ResValues "strings.xml"), $StringsXml, $Utf8NoBom)

# AndroidManifest.xml
$ManifestXml = @'
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="br.com.fintech.evolution"
    android:versionCode="2"
    android:versionName="2.0">

    <uses-sdk
        android:minSdkVersion="22"
        android:targetSdkVersion="34" />

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <supports-screens
        android:anyDensity="true"
        android:largeScreens="true"
        android:normalScreens="true"
        android:smallScreens="true"
        android:xlargeScreens="true" />

    <application
        android:label="@string/app_name"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:theme="@android:style/Theme.NoTitleBar.Fullscreen"
        android:hardwareAccelerated="true"
        android:usesCleartextTraffic="true">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|locale|smallestScreenSize|screenLayout|uiMode"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
'@
[System.IO.File]::WriteAllText((Join-Path $WorkDir "AndroidManifest.xml"), $ManifestXml, $Utf8NoBom)

# MainActivity.java (WebView nativa de alta performance carregando os assets locais da Fistu)
$MainActivityJava = @'
package br.com.fintech.evolution;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#000000"));

        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setDatabaseEnabled(true);
        ws.setAllowFileAccess(true);
        ws.setAllowContentAccess(true);
        ws.setLoadWithOverviewMode(true);
        ws.setUseWideViewPort(true);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient());

        setContentView(webView);
        webView.loadUrl("file:///android_asset/index.html");
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
'@
[System.IO.File]::WriteAllText((Join-Path $SrcDir "MainActivity.java"), $MainActivityJava, $Utf8NoBom)

# 5. Compilar com aapt2, javac, d8, zipalign e apksigner
Write-Host "[3/5] Compilando recursos e codigo Java..." -ForegroundColor Cyan

$CompiledResZip = Join-Path $WorkDir "compiled_res.zip"
$UnalignedApk   = Join-Path $WorkDir "unaligned.apk"
$AlignedApk     = Join-Path $WorkDir "aligned.apk"
$SignedApk      = Join-Path $AsciiRoot "Fistu-Release.apk"
$KeystoreFile   = Join-Path $AsciiRoot "fistu.keystore"

# Compilar recursos
& (Join-Path $BtBin "aapt2.exe") compile --dir $ResDir -o $CompiledResZip
if ($LASTEXITCODE -ne 0) { throw "Falha no aapt2 compile" }

# Linkar com AndroidManifest e incluir assets
& (Join-Path $BtBin "aapt2.exe") link -o $UnalignedApk `
    -I $AsciiAndroidJar `
    --manifest (Join-Path $WorkDir "AndroidManifest.xml") `
    --min-sdk-version 22 `
    --target-sdk-version 34 `
    -A $AssetsDir `
    --java (Join-Path $WorkDir "src") `
    $CompiledResZip
if ($LASTEXITCODE -ne 0) { throw "Falha no aapt2 link" }

# Compilar Java
& (Join-Path $JavaBin "javac.exe") -source 1.8 -target 1.8 -encoding UTF-8 `
    -bootclasspath $AsciiAndroidJar `
    -d $ObjDir `
    (Join-Path $SrcDir "MainActivity.java") `
    (Join-Path $SrcDir "R.java")
if ($LASTEXITCODE -ne 0) { throw "Falha no javac" }

# Gerar DEX
$ClassFiles = @(Get-ChildItem -LiteralPath $ObjDir -Filter "*.class" -Recurse | ForEach-Object { $_.FullName })
& (Join-Path $JavaBin "java.exe") -cp (Join-Path $BtBin "lib\d8.jar") com.android.tools.r8.D8 --lib $AsciiAndroidJar --output $DexDir $ClassFiles
if ($LASTEXITCODE -ne 0) { throw "Falha no D8" }

# Injetar classes.dex no APK
& (Join-Path $JavaBin "jar.exe") -uf $UnalignedApk -C $DexDir classes.dex
if ($LASTEXITCODE -ne 0) { throw "Falha ao injetar classes.dex" }

# Zipalign
& (Join-Path $BtBin "zipalign.exe") -f -p 4 $UnalignedApk $AlignedApk
if ($LASTEXITCODE -ne 0) { throw "Falha no zipalign" }

# Gerar Keystore se não existir
if (-not (Test-Path -LiteralPath $KeystoreFile)) {
    & (Join-Path $JavaBin "keytool.exe") -genkeypair -v `
        -keystore $KeystoreFile `
        -alias fistukey `
        -keyalg RSA -keysize 2048 -validity 10000 `
        -storepass fistu123 -keypass fistu123 `
        -dname "CN=Fistu, OU=Fintech, O=FistuTecnologia, L=RioDeJaneiro, S=RJ, C=BR"
}

# Assinar APK com apksigner (V1 + V2 + V3)
Write-Host "[4/5] Assinando digitalmente o APK..." -ForegroundColor Cyan
& (Join-Path $JavaBin "java.exe") -jar (Join-Path $BtBin "lib\apksigner.jar") sign `
    --ks $KeystoreFile `
    --ks-pass pass:fistu123 `
    --key-pass pass:fistu123 `
    --out $SignedApk `
    $AlignedApk
if ($LASTEXITCODE -ne 0) { throw "Falha no apksigner" }

# 6. Salvar na área de Download do Usuário!
Write-Host "[5/5] Enviando para a pasta Downloads..." -ForegroundColor Cyan
Copy-Item -LiteralPath $SignedApk -Destination $OutApkDownloads -Force
Copy-Item -LiteralPath $SignedApk -Destination $OutApkProject -Force

$SizeMB = [math]::Round((Get-Item -LiteralPath $OutApkDownloads).Length / 1MB, 2)
$SizeKB = [math]::Round((Get-Item -LiteralPath $OutApkDownloads).Length / 1KB, 1)

Write-Host "======================================================================" -ForegroundColor Green
Write-Host " SUCESSO! APK COMPILADO E SALVO NA PASTA DOWNLOADS!" -ForegroundColor Green
Write-Host " Arquivo : $OutApkDownloads" -ForegroundColor Yellow
Write-Host " Tamanho : $SizeMB MB ($SizeKB KB)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Green
