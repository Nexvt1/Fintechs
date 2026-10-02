# Fintech Evolution para Android

Este projeto empacota `Fintch linha.html` como um aplicativo Android usando Capacitor.

## Gerar o APK de teste

Requisitos: Node.js, Android Studio, Android SDK e Java/JDK configurados.

```powershell
npm install
Copy-Item -Force "..\Fintch linha.html" "www\index.html"
npx cap add android
npx cap sync android
cd android
.\gradlew.bat assembleDebug
```

O APK será criado em `android/app/build/outputs/apk/debug/app-debug.apk`.

Para abrir no Android Studio:

```powershell
npx cap open android
```
