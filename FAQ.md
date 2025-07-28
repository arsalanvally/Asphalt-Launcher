### Frequently Asked Questions

## Installation & Setup
1. **How do I install this launcher?**  
   - For users: Download the pre-built EXE from Releases  
   - For developers: Run `python main.py` from source

2. **Where does the launcher store data?**  
   - Config files: `%APPDATA%\AsphaltLauncher`  
   - Minecraft files: Standard `.minecraft` folder

3. **What Java versions are needed?**  
   | Minecraft Version | Required Java |
   |------------------|--------------|
   | 1.17+ | Java 17+ |
   | 1.12-1.16 | Java 8 |
   | Pre-1.12 | Java 7 |

## Offline Mode
4. **How does offline mode work?**  
   - Works without internet connection  
   - Enter any username (no authentication)  
   - Only shows already-downloaded versions  

5. **Why can't I see all versions offline?**  
   - Without internet, only locally installed versions appear  
   - Internet required to view/download new versions  
   - Click refresh (🔄) when back online to see full list

## Mod Support
6. **How to install mods?**  
   1. Manually install your mod loader (Fabric/Forge/Quilt)  
   2. Launch the modded profile once to set up  
   3. Add mods to `.minecraft/mods` folder  
   4. Select the profile in launcher

7. **Mod troubleshooting checklist**  
   - ✅ Mod loader matches MC version  
   - ✅ All mods match MC version  
   - ✅ No duplicate/conflicting mods  
   - ✅ Check `latest.log` for errors

## Common Issues
8. **Download stuck at 1% or 100%**  
   Fixes:  
   - Pause/resume download  
   - Restart launcher  
   - Delete `.minecraft/versions/[version]` folder  
   - Check antivirus blocking

9. **Game crashes on launch**  
   First steps:  
   - Verify Java version matches MC version  
   - Check RAM allocation (minimum 2GB recommended)  
   - Inspect `crash-reports` folder

## Advanced Features
10. **Custom Java setup**  
    Only needed if:  
    - Running multiple Java versions  
    - Using special JVM builds  
    Set path in Settings → "Select JRE"

11. **JVM argument tips**  
    Common uses:  
    - `-Xmx4G` - Set max RAM (adjust number)  
    - `-XX:+UseG1GC` - Better garbage collection  
    - `-Dfml.ignoreInvalidMinecraftCertificates=true` - Fix cert errors

## Future Development
12. **Planned features**  
    - Ely.by account integration (skin support)  
    - Built-in mod loader installation  
    - Better version management UI