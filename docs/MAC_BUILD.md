# Mac build guide — AR Floor Plan Visualizer

Context for Claude Code running on the Mac. This Mac has one job: sign the Xcode project that Unity
exports on Windows, and install it on the iPad or iPhone. No Unity runs here, and no source code is edited here.

## Background

- The app is a Unity 6 (6000.6.3f1) AR app. It is developed on a Windows laptop. Unity there writes an
  Xcode project (the folder containing `Unity-iPhone.xcodeproj`, about 1.4 GB). The user copies that
  folder into this Mac folder.
- Bundle id: `com.thecubestar.floorplanviz`. Minimum iOS 15. Devices: iPad Air 11-inch (M2) on
  iPadOS 17.6.1, and iPhone 12.
- Signing: a free Apple ID **Personal Team** with automatic signing. Builds expire after **7 days**.
  Re-run the build and install below to refresh one.
- The iPad is already paired, has Developer Mode on and trusts the developer profile. It installs over Wi-Fi
  when it is unlocked and on the same network as the Mac.
- The app talks to a Python backend on the Windows laptop (`http://<laptop-ip>:8000`, entered in the
  app's home screen). The backend's setup isn't needed here.

## Steps for a new export

Run these from the folder that contains `Unity-iPhone.xcodeproj` (call it `$IOS`).

### 1. Repair permissions (needed after every copy from Windows)

Windows strips the executable bits and macOS quarantines the files. Without this step, the UnityFramework build fails
with `Command PhaseScriptExecution failed with a nonzero exit code`.

```bash
cd "$IOS"
xattr -dr com.apple.quarantine .
chmod -R +x Il2CppOutputProject/IL2CPP
find . -name "*.sh" -exec chmod +x {} +
```

### 2. Find the signing team and the device

```bash
# Team ID = the OU field of the Apple Development certificate
security find-certificate -c "Apple Development" -p | openssl x509 -noout -subject

# Connected or wireless devices; note the iPad's identifier
xcrun devicectl list devices
```

### 3. Build and sign

```bash
xcodebuild \
  -project Unity-iPhone.xcodeproj \
  -scheme Unity-iPhone \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -derivedDataPath build \
  -allowProvisioningUpdates \
  DEVELOPMENT_TEAM=<TEAM_ID> \
  CODE_SIGN_STYLE=Automatic \
  build
```

The first IL2CPP build takes 5–15 min. Later builds are incremental. You can ignore the ~60 warnings (deprecated
APIs, umbrella headers); they are normal for Unity exports.

### 4. Install and launch

```bash
APP=$(find build/Build/Products/Release-iphoneos -maxdepth 1 -name "*.app" | head -1)
xcrun devicectl device install app --device <DEVICE_ID> "$APP"
xcrun devicectl device process launch --device <DEVICE_ID> com.thecubestar.floorplanviz
```

## Rules

- **Don't accept Xcode's "Update to recommended settings"** prompt, and don't change project settings in
  Xcode. Every Unity export overwrites them. Settings belong in the Unity project's `PlatformSetup.cs` on
  Windows. Tell the user if one is needed.
- Don't commit or upload the export anywhere. It's a build artifact.
- When a new export arrives, replace the old folder completely rather than merging. Delete `build/` too.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `PhaseScriptExecution failed` in UnityFramework | Step 1 was skipped, or a file is still not executable. Read the full log for `Permission denied`. |
| "Your team has no devices…" / "No profiles for …" | No device has been registered. Plug the device in by cable once (unlocked, tap Trust), then rebuild. |
| `errSecInternalComponent` or codesign hangs | The login keychain is locked (common in remote sessions). Ask the user to run `security unlock-keychain ~/Library/Keychains/login.keychain-db`. Never ask for or handle the password yourself. |
| Device missing from `devicectl list devices` | Unlock the iPad and check it's on the same Wi-Fi. If it's still missing, connect it by cable once. |
| App icon is there but won't open | The 7-day signature expired. Rebuild and reinstall (steps 3–4). |
| "Untrusted Developer" on the device | Settings → General → VPN & Device Management → the Apple ID → Trust. |
| Bundle id rejected as unavailable | Pass `PRODUCT_BUNDLE_IDENTIFIER=com.thecubestar.floorplanviz.dev` to xcodebuild and tell the user. |
